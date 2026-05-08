# Task 11.5: Feedback Collection — Progress

**Start**: 2026-05-08
**Complete**: 2026-05-08
**Status**: ✅ DONE

---

## Summary

User feedback (👍/👎) now:
1. Persists to PostgreSQL `feedbacks` table via `upsert_feedback()` data layer override
2. Appears in Arize Phoenix as a `user_feedback` span annotation (score=1.0 for thumbs up)
3. Phoenix dashboard shows **`user_feedback μ 1.00`** as a real-time metric

---

## Root Cause Analysis — Four Problems Solved

### Problem 1: `@cl.on_feedback` never triggered

**Symptom**: Clicking 👍 did nothing. No server logs.

**Root cause**: Chainlit's feedback buttons open a dialog ("افزودن نظر"). The button click
alone doesn't submit — the user must also click "ثبت نظر" to submit. Our Playwright test
was only clicking the button without completing the dialog.

**Fix**: Two-step click flow:
```python
# Step 1: click thumbs-up button at (398, 689)
await btn.click(force=True)
# Step 2: submit the dialog
submit_btn = await page.wait_for_selector('button:has-text("ثبت نظر")')
await submit_btn.click()
```

---

### Problem 2: `feedback.py` used wrong Phoenix endpoint

**Symptom**: `_feedback_client` was None at feedback time; `failed_to_initialize_observability` error.

**Root cause A** (Python logging incompatibility): `feedback.py` uses `import logging`
(standard Python logger), but called it with structlog-style keyword arguments:
```python
# ❌ Python logging doesn't accept arbitrary kwargs
logger.info("phoenix_feedback_client_initialized", endpoint=phoenix_endpoint)
```
This raised `Logger._log() got an unexpected keyword argument 'endpoint'`, causing
`initialize_feedback_client()` to fail, leaving `_feedback_client = None`.

**Fix**: Use standard Python logging format:
```python
logger.info("Phoenix feedback client initialized at %s", phoenix_endpoint)
```

**Root cause B** (wrong API endpoint): The existing code sent to `POST /api/feedback`
which doesn't exist in Phoenix. The correct endpoint is `POST /v1/span_annotations`.

**Fix**: Updated `PhoenixFeedbackClient.send_feedback()` to use:
```
POST http://localhost:6006/v1/span_annotations
{
  "data": [{ "span_id": "...", "name": "user_feedback",
             "annotator_kind": "HUMAN",
             "result": {"label": "thumbs_up", "score": 1.0} }]
}
```

---

### Problem 3: `cl.user_session.get("last_span_id")` returned None in feedback context

**Symptom**: `span_id` was None in `@cl.on_feedback` even after storing it in `@on_message`.

**Root cause**: `cl.user_session` is context-var based. The `@cl.on_feedback` coroutine
runs in a different async context than `@on_message`, so it can't read session vars set there.

**Fix**: Use a module-level dict keyed by session_id:
```python
# In app.py module scope:
_session_span_ids: dict[str, str] = {}

# In @on_message:
_session_span_ids[session_id] = format(span_ctx.span_id, "016x")

# In @cl.on_feedback:
span_id = _session_span_ids.get(session_id)
```

---

### Problem 4: Capturing a valid span_id from OpenTelemetry

**Symptom**: `span.get_span_context().is_valid` was False for the initial attempt.

**Root cause**: The OTel `get_tracer()` call used the global tracer provider, which IS
initialized by `initialize_tracing()` before the first request. The issue was the first
test ran BEFORE Phoenix was up, so the tracer provider used a no-op exporter. After
Phoenix was started and Chainlit restarted, spans became valid.

**Fix**: The approach is correct — create an explicit `"user_turn"` span around `agent.run()`:
```python
_tracer = otel_trace.get_tracer("law-agent-ui")
with _tracer.start_as_current_span("user_turn") as _span:
    _ctx = _span.get_span_context()
    if _ctx.is_valid:
        _session_span_ids[session_id] = format(_ctx.span_id, "016x")
    response_text, updated_history = await agent.run(...)
```

---

## Key Learnings for Future Developers

| # | Learning |
|---|---------|
| 1 | Chainlit feedback requires two clicks: button + dialog "ثبت نظر" |
| 2 | Never mix `structlog` and standard `logging` kwarg styles — use `%s` format with `logging` |
| 3 | `cl.user_session` is unreliable across coroutines — use a module-level dict instead |
| 4 | Phoenix annotation API: `POST /v1/span_annotations` with `span_id` (NOT trace_id) |
| 5 | Start Phoenix BEFORE Chainlit server so OTel traces connect properly |
| 6 | `upsert_feedback` in data layer → DB; `@cl.on_feedback` → Phoenix (both run on feedback) |

---

## Verification

### PostgreSQL:
```
feedbacks table:
  value=1 | forId=75deaa47... | threadId=def387d2...
  (value=1 = 👍, value=0 = 👎)
```

### Server logs:
```
feedback_persisted  value=1 label='👍 مفید' thread_id=...
upsert_feedback     feedback_id=...
feedback_received   value=1 label='مفید بود 👍' session_id=...
span_id_stored      span_id=6e388b5d8c182c2d
feedback_phoenix_attempt span_id=6e388b5d8c182c2d
Phoenix feedback sent span_id=6e388b5d8c182c2d label=thumbs_up
```

### Phoenix dashboard:
- `user_feedback μ 1.00` visible in project header stats
- See `screenshots/2_phoenix_user_feedback_metric.png`

---

## Screenshots

| File | Shows |
|------|-------|
| `1_feedback_submitted.png` | Response with 👍/👎 buttons visible at bottom |
| `2_phoenix_user_feedback_metric.png` | Phoenix header showing `user_feedback μ 1.00` |
| `3_phoenix_spans_with_metric.png` | Phoenix spans view with annotations column |
