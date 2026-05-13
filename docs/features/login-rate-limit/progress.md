# Email + Invite Code Login Progress

## Status
✅ **Complete** — all code done, tests passing, ready for manual testing.

## Completed
- [x] Add `RateLimitConfig` to `settings.py` with `requests_per_day: 30`
- [x] Add `rate_limit` section to `config.yaml`
- [x] Create `src/law_agent/ui/rate_limit.py`:
  - `ensure_rate_limits_table()` — creates table on first use
  - `check_and_increment()` — atomic rate limit check
  - Lazy initialization with `_table_initialized` flag
- [x] Update auth_callback in `app.py`:
  - Validate email format via regex
  - Validate INVITE_CODE from env if set
  - Log login success/failure
- [x] Add rate limit check in `on_message`:
  - Before running agent, check if user exceeds daily limit
  - Send Persian error message if over limit
- [x] Create unit tests in `tests/unit/test_rate_limit.py`:
  - Table creation
  - First request allowed
  - Request at limit allowed
  - Request exceeding limit rejected
  - Database error handling (fail open)
- [x] All 317 tests passing
- [x] Code formatting with Black complete

## Pending (User Setup)
- [ ] Set `INVITE_CODE` in `.env` (optional, defaults to accept any password)
- [ ] Test login with valid email + invite code
- [ ] Test login with invalid email (should be rejected)
- [ ] Test login with wrong invite code (should be rejected)
- [ ] Test rate limit: send 31 messages, 2nd should fail

## Known Notes
- **INVITE_CODE optional**: If not set in `.env`, any password is accepted (for dev/testing)
- **Rate limit resets at UTC midnight**: Daily bucket keyed by `CURRENT_DATE` (UTC)
- **Table created lazily**: On first message, if rate_limits table doesn't exist, it's created automatically
- **Fail-open on DB errors**: If rate limit check fails due to DB error, request is allowed (reliability > strict limiting)
- **Email stored lowercase**: User identifier normalized to lowercase for consistency

## Manual Testing Steps

### 1. Start the app
```bash
! .venv/bin/chainlit run src/law_agent/ui/app.py --host 0.0.0.0 --port 8000
```

### 2. Test email validation
```
Login: test@example.com / testing123
→ Success (if INVITE_CODE=testing123 in .env)

Login: notanemail / testing123
→ Rejected (invalid email format)

Login: test@example.com / wrongcode
→ Rejected (invite code mismatch, if INVITE_CODE set)
```

### 3. Test rate limit (optional)
- In `config.yaml`: temporarily set `requests_per_day: 2`
- Send 3 messages:
  - Message 1: succeeds
  - Message 2: succeeds
  - Message 3: rejected with Persian error

### 4. Check database
```bash
psql -U postgres -d law_agent
SELECT * FROM rate_limits;
```
Should show one row per user per day: `(email, today_date, count)`

## Files Modified
- `src/law_agent/config/settings.py` — added RateLimitConfig
- `src/law_agent/ui/app.py` — email+invite validation, rate limit check
- `src/law_agent/ui/rate_limit.py` — new module
- `config.yaml` — rate_limit section
- `tests/unit/test_rate_limit.py` — 5 new tests
- `.env` — (user adds INVITE_CODE)
