# Login — Progress

## Summary

Implemented as part of Task 11.2 (Conversation Sidebar). Login is a prerequisite for per-user history.

**Implementation**: 3 lines in `src/law_agent/ui/app.py`:

```python
@cl.password_auth_callback
async def auth_callback(username: str, password: str) -> Optional[cl.User]:
    return cl.User(identifier=username, metadata={"role": "user"})
```

**Configuration required** in `.env`:
```
CHAINLIT_AUTH_SECRET="your-jwt-secret-here"
```

**Key learnings**:

1. **`CHAINLIT_AUTH_SECRET` format matters** — the value must not contain quotes when loaded by the server startup script. Use the `start_server.py` pattern that strips surrounding double-quotes from `.env` values.

2. **Without this, the sidebar is invisible** — Chainlit only shows per-user threads when a user is authenticated. Without auth, all requests are anonymous and threads are not grouped.

3. **Session duration** — controlled by `user_session_timeout` in `.chainlit/config.toml` (currently 1,296,000 seconds = 15 days). After this period, users must log in again.

4. **The login screen** — Chainlit renders it automatically when `@cl.password_auth_callback` is defined. No additional UI code needed.

**Related**:
- `docs/features/conversation-sidebar/` — depends on login
- `src/law_agent/ui/app.py:134` — implementation
