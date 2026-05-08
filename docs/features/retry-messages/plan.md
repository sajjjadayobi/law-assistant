# Task 11.8: Retry Failed Messages — Plan

## What I'm Building

A "تلاش مجدد" (Retry) action button that appears on error messages in the chat UI. When a message fails due to any exception (network, database, agent error), the user sees the error message with a retry button. Clicking it re-sends the original user message and removes the failed response.

## Why This Matters

Without retry, users must manually retype or scroll up and copy their question when an error occurs. This is especially frustrating for long legal questions in Persian. The retry button provides a one-click recovery path, keeping users in the flow.

## Key Design Decisions

### Decision 1: Session-scoped retry actions via `cl.user_session`
**Decision**: Store the current session's retry actions in `cl.user_session` (not a module-level dict).
**Why**: `cl.user_session` is per-user-session and survives the duration of a session correctly. Module-level globals would be shared across all concurrent sessions, causing cross-session interference.
**Alternatives Considered**:
- Module-level `dict[session_id, list[cl.Action]]` — rejected: requires manual cleanup, risk of memory leak
- Class-based approach like data-assistant's `BaseProfile.retry_actions` — rejected: law agent uses function-based handlers, not a class
**Trade-offs**: Slightly more verbose to access (`cl.user_session.get("retry_actions", [])`), but correct.

### Decision 2: Simplified payload (no parent_step_id removal)
**Decision**: The retry action payload only carries `message_content`. We do NOT try to remove parent steps.
**Why**: The data-assistant removes a parent `cl.Step` because it wraps the entire agent call in a step. Our law agent doesn't wrap the call in a persistent step — tool steps are created inside `agent.run()` and can't be referenced from the callback. Attempting step removal would cause errors without benefit.
**Alternatives Considered**: Storing step IDs — rejected: no reliable way to get the wrapping step ID in our architecture
**Trade-offs**: The error message and any partial steps remain visible until the retry runs (they disappear when the `cl.Message(id=...).remove()` call fires).

### Decision 3: Remove previous retry actions at message start
**Decision**: At the start of `@cl.on_message`, remove all stored retry actions before processing.
**Why**: When the user sends a new message (not via retry button), the old retry buttons should disappear since the user has moved on. This matches data-assistant's `await self.remove_retry_actions()` pattern.
**Alternatives Considered**: Let retry buttons accumulate — rejected: confusing UX with multiple old retry buttons visible
**Trade-offs**: Adds async I/O at start of every message, but only 1-2 actions typically.

### Decision 4: Error message text updated to mention the retry button
**Decision**: Change error text from generic "دوباره تلاش کنید" to explicitly say "با زدن دکمه «تلاش مجدد»".
**Why**: Users need to be told the button exists. Without guidance, they may miss it.
**Alternatives Considered**: Keep same error text — rejected: users may not discover the button
**Trade-offs**: Slightly more text in the error message.

## Success Criteria

- [ ] Retry button ("تلاش مجدد") appears on every error message
- [ ] Clicking retry re-sends the original message exactly as typed
- [ ] The error message with the retry button is removed before retry runs
- [ ] New messages (not from retry) clear old retry buttons
- [ ] Works for all error types (network, DB, agent, any Exception)
- [ ] Button icon is `refresh-cw` (Chainlit standard)
- [ ] Tooltip in Persian: "تلاش مجدد برای این پیام"
- [ ] 8 unit tests covering the retry logic
- [ ] All 306+ existing tests still pass

## Dependencies

- **Requires**: Task 11.5 complete (✅ done) — `cl.on_feedback` pattern shows action callbacks work
- **Blocks**: Nothing
- **Related**: Task 11.3 (tool steps), Task 11.5 (feedback actions)

## Open Questions

- [x] Does `cl.Action.remove()` work in Chainlit 2.x? Yes — used in data-assistant `base.py:161`
- [x] Can `cl.Message(id=...).remove()` remove a message by ID in callback? Yes — `base.py:387`
- [x] Where to get the error message ID for removal? `action.forId` in the callback
- [ ] Does `cl.user_session` persist into `@cl.action_callback` scope? Need to verify at runtime.

## References

- data-assistant `src/profiles/base.py` lines 135-163 (retry_action method + remove_retry_actions)
- data-assistant `src/profiles/base.py` lines 385-392 (`@cl.action_callback(name="retry")`)
- Current `src/law_agent/ui/app.py` lines 279-290 (existing exception handler)
- `docs/development/v0.0.2-tasks.md` Task 11.8 section

## Estimated Complexity

**Low** — Pure UI/Chainlit change to `app.py`. No database schema changes, no new imports beyond what's already there. The main risk is verifying `cl.user_session` scope inside action callbacks at runtime.
