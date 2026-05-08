# Task 11.5: Feedback Collection (👍/👎) — Plan

**Date**: 2026-05-08
**Reference**: `docs/development/v0.0.2-tasks.md` § Task 11.5

---

## What We're Building

Re-enable the commented-out feedback handler so users can rate responses with 👍/👎.
Feedback is stored to PostgreSQL AND sent to Arize Phoenix as a span annotation for
eval-driven development.

### User Flow
1. User reads the agent's response
2. Clicks 👍 or 👎 (visible below every response)
3. Chainlit opens a small dialog: "افزودن نظر" (optional comment)
4. User clicks "ثبت نظر" (Submit)
5. Feedback is persisted to the `feedbacks` DB table
6. Feedback is sent to Phoenix as a `user_feedback` span annotation

### Phoenix Integration Flow
```
User clicks 👍
  → @cl.on_feedback fires
    → upsert_feedback in data_layer → PostgreSQL
    → retrieve last_span_id from _session_span_ids dict
    → POST /v1/span_annotations → Phoenix
       payload: { span_id, name: "user_feedback", annotator_kind: "HUMAN",
                  result: { label: "thumbs_up", score: 1.0 } }
```

---

## Design Decisions

### 1. Two-layer feedback storage

| Layer | Where | What |
|-------|-------|------|
| DB persistence | `LawAgentDataLayer.upsert_feedback()` | Always persisted — works even if Phoenix is offline |
| Phoenix annotation | `@cl.on_feedback` handler | Best-effort — skipped silently if Phoenix unavailable |

Following the data-assistant pattern: `upsert_feedback` override for DB + extra analytics call.

### 2. Span-level Phoenix annotations (not trace-level)

Phoenix's annotation API requires a `span_id` (16-char hex), not a trace_id. We:
1. Create an explicit `"user_turn"` OTel span that wraps `agent.run()` in `@on_message`
2. Capture its `span_id` (from `span.get_span_context().span_id`) 
3. Store in a module-level dict `_session_span_ids[session_id]`
4. In `@cl.on_feedback`, look up the span_id and send `POST /v1/span_annotations`

### 3. Module-level dict instead of `cl.user_session`

`cl.user_session.get()` is unreliable in the feedback handler context (different coroutine,
potentially different context var scope). A simple `dict[session_id → span_id]` at module
level is always accessible.

### 4. Correct Phoenix API endpoint

The existing `feedback.py` was using `POST /api/feedback` (non-existent endpoint).
The correct endpoint is `POST /v1/span_annotations`.

Payload:
```json
{
  "data": [{
    "span_id": "6e388b5d8c182c2d",
    "name": "user_feedback",
    "annotator_kind": "HUMAN",
    "result": { "label": "thumbs_up", "score": 1.0, "explanation": null }
  }]
}
```

---

## Files Changed

| File | Change |
|------|--------|
| `src/law_agent/ui/app.py` | Uncomment `@cl.on_feedback`; add `_session_span_ids` dict; wrap `agent.run()` in OTel span |
| `src/law_agent/data/data_layer.py` | Add `upsert_feedback()` override with logging |
| `src/law_agent/observability/feedback.py` | Rewrite `PhoenixFeedbackClient` to use correct `/v1/span_annotations` endpoint; fix `logging` vs structlog incompatibility |
| `src/law_agent/observability/__init__.py` | Export `get_feedback_client` |

---

## Success Criteria

- [x] 👍/👎 buttons appear below every agent response
- [x] Clicking shows a dialog ("افزودن نظر") then "ثبت نظر" submits
- [x] Feedback persisted to PostgreSQL `feedbacks` table (value=1 for 👍, value=0 for 👎)
- [x] Phoenix receives span annotation (`user_feedback μ 1.00` visible in Phoenix dashboard)
- [x] Works when Phoenix is offline (feedback still stored in DB)
- [x] `@cl.on_feedback` handler logs: `feedback_received`, `feedback_persisted`
