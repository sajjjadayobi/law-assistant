# Share Conversations — Plan

## What I'm Building

A share button in the conversation sidebar that lets users generate a public read-only link to any of their past conversations. Any person with the link can view the full exchange without needing to log in.

## Why It Matters

Users often want to share a legal research conversation with a colleague or save a permanent reference link. This is task 11.6 from the deferred backlog.

## Key Design Decisions

### Decision: Use Chainlit's Native Thread Sharing (not a custom route)

**Chose**: Chainlit 2.11 has complete built-in sharing support. Two things activate it:
1. `allow_thread_sharing = true` in `.chainlit/config.toml`
2. `@cl.on_shared_thread_view` callback in `app.py`

**Why**: Zero custom frontend code. Chainlit handles the share button UI, the `PUT /project/thread/{thread_id}/share` toggle endpoint, the `GET /project/share/{thread_id}` read-only view route, the "copy link" button, and the share status in the sidebar — all already implemented in Chainlit 2.11. The Persian translations for every share-related UI string are already present in `fa-IR.json` (verified: all 7 strings exist).

**Alternatives rejected**:
- Custom middleware route + JS button — would duplicate work Chainlit already does, and the read-only thread view page would need significant frontend work.
- Custom share table in DB — unnecessary; Chainlit stores `is_shared: true` and `shared_at` in the existing `threads.metadata` JSON column via `update_thread()`.

---

### Decision: Callback Returns True When `is_shared` in Metadata

**Chose**: `@cl.on_shared_thread_view` returns `True` when `thread["metadata"]["is_shared"] == True`.

**Why**: The Chainlit server already checks `metadata["is_shared"]` and skips the callback when it's True (the `if (not user_can_view) and (not is_shared)` guard). The callback is the additional authorization hook — returning `True` for shared threads makes the logic consistent for any viewer (logged-in or anonymous).

**Alternatives rejected**:
- Always return `False` and rely only on `is_shared` metadata check — works but leaves the callback as a no-op stub, which is confusing.
- Per-user ACL — overkill for this use case; owner already controls share toggle.

---

### Decision: Share URL Format

**Chose**: Chainlit's built-in `/share/{thread_id}` — no config needed.

**Why**: The route already exists in Chainlit server. No custom route needed. The share link is copied by Chainlit's "copy link" button automatically.

---

## Files to Change

| File | Change |
|---|---|
| `.chainlit/config.toml` | `allow_thread_sharing = true` |
| `src/law_agent/ui/app.py` | Add `@cl.on_shared_thread_view` callback |
| `tests/ui/test_share_thread.py` | New test file for the callback |

No database migrations needed. No `config.yaml` changes needed. No new routes. No JS/CSS changes.

---

## Implementation Steps

1. `.chainlit/config.toml`: set `allow_thread_sharing = true`
2. `app.py`: add `@cl.on_shared_thread_view` callback after `@cl.on_feedback`:
   ```python
   @cl.on_shared_thread_view
   async def on_shared_thread_view(thread: ThreadDict, viewer: cl.User | None) -> bool:
       metadata = thread.get("metadata") or {}
       if isinstance(metadata, str):
           import json as _json
           try:
               metadata = _json.loads(metadata)
           except Exception:
               metadata = {}
       return bool(metadata.get("is_shared"))
   ```
3. Import `ThreadDict` from `chainlit.types` (already imported in data_layer.py)
4. Write `tests/ui/test_share_thread.py` with:
   - `test_shared_thread_is_viewable` — metadata `is_shared=True` → callback returns True
   - `test_unshared_thread_is_not_viewable` — metadata `is_shared=False` → callback returns False
   - `test_missing_metadata_returns_false` — `metadata=None` → callback returns False
   - `test_string_metadata_parsed_correctly` — stringified JSON → parsed and checked

---

## Verification

- **Command**: `.venv/bin/python -m pytest tests/ui/test_share_thread.py -v`
- **Visual check**: Start server → open sidebar → right-click a past conversation → "اشتراک‌گذاری" menu item should appear → click → "اشتراک‌گذاری لینک گفتگو" modal with copy-link button → copy link → open in incognito tab (not logged in) → full read-only conversation visible.
- **End-to-end**: User clicks share → link generated → open in incognito → conversation visible without login.

---

## Success Criteria

- [ ] Share option appears in conversation context menu in the sidebar
- [ ] Clicking share shows modal with a copyable link
- [ ] Link opens the conversation read-only in a new tab without login
- [ ] Unsharing removes public access (404 in incognito)
- [ ] All 4 unit tests pass
- [ ] `make all` passes (no regressions)

---

## Open Questions

- None — Chainlit behavior verified by reading server.py source code directly.
