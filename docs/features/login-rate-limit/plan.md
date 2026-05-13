# Email + Invite Code Login with Rate Limiting

## Objective
Replace the permissive login (accepts any username/password) with a real authentication mechanism that:
1. Requires users to identify themselves by email
2. Validates an invite code (shared by app owner) for access
3. Enables rate limiting per user (30 requests/day, configurable)

## Design Decisions

### 1. Email + Invite Code Pattern
**Decision**: Validate both email format and INVITE_CODE from environment.

**Why**:
- Simple: no external service required
- Chainlit's native login form already shows username/password fields
- Email serves as the user identifier for rate limiting
- Invite code provides minimal access control (share with trusted users only)
- If INVITE_CODE not set in `.env`, any password is accepted (for dev/testing)

**Alternatives rejected**:
- Google OAuth: requires Google Cloud Console access (user doesn't have)
- Header auth: needs reverse proxy or custom JS (adds complexity)
- Password hashing: unnecessary for a single-user/trusted-group app

### 2. Rate Limiting Strategy
**Decision**: Daily (UTC) rolling counter per email, 30 requests/day default.

**Why**:
- Simple: one row per user per day in PostgreSQL
- Fair: resets every calendar day
- Configurable: change limit in `config.yaml` without code changes
- Atomic: uses `INSERT ... ON CONFLICT` for consistency

**Storage**: Dedicated `rate_limits` table (user_id TEXT, day DATE, count INT).

### 3. Lazy Table Initialization
**Decision**: Create `rate_limits` table on first request, not at startup.

**Why**:
- No schema migrations needed (SQL runs inline)
- Works in dev/testing without full DB setup
- Zero startup cost if feature not used

## UX
- **Login Form** (Chainlit's native):
  - **Username** field → user enters their email
  - **Password** field → user enters the invite code
- **Rate Limit Message** (Persian): "شما به محدودیت روزانه رسیده‌اید. فردا دوباره تلاش کنید." (You've reached your daily limit. Try again tomorrow.)

## Success Criteria
- [x] Email validation in login (rejects non-email usernames)
- [x] Invite code validation (rejects wrong passwords if INVITE_CODE set)
- [x] Rate limit enforced (30th request succeeds, 31st rejected)
- [x] Rate limit resets at UTC midnight (new calendar day)
- [x] `make all` passes (format, lint, typecheck, tests)
