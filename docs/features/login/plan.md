# Login — Plan

## What I'm Building

Password authentication for the Chainlit UI using `@cl.password_auth_callback`. Any username/password combination is accepted — authentication exists purely to identify users so each gets their own conversation history in the sidebar.

## Why It Matters

Chainlit's conversation history sidebar (`LawAgentDataLayer`) is per-user. Without authentication, all users share a single anonymous identity and see each other's conversations. Authentication gives each user a private thread list.

## Key Design Decisions

### Decision: Accept any credentials
**Chose**: `@cl.password_auth_callback` returns a `cl.User` for any username/password.
**Why**: This is a legal assistant for internal or trusted use. There is no user management system. The goal is identity isolation, not access control.
**Alternatives**: Real credential database — rejected as unnecessary complexity for current use case.

### Decision: JWT-based sessions via Chainlit
**Chose**: Set `CHAINLIT_AUTH_SECRET` in `.env` as the JWT signing secret.
**Why**: Chainlit handles session tokens automatically once the secret is set.
**Trade-off**: Anyone who knows the `.env` secret can forge tokens, but this is acceptable for the current deployment context.

## Success Criteria

- [x] Login screen appears before chat
- [x] Any username/password is accepted
- [x] Each user sees only their own conversation history
- [x] Sessions persist for 15 days (`user_session_timeout = 1296000` in config.toml)
- [x] `CHAINLIT_AUTH_SECRET` documented in `.env.example`

## References

- `src/law_agent/ui/app.py` — `@cl.password_auth_callback` at line ~134
- `.chainlit/config.toml` — `session_timeout`, `user_session_timeout`
- `docs/features/conversation-sidebar/` — requires login to function
