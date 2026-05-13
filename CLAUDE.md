# CLAUDE.md

Project instructions for Claude Code. Read this first, then follow the links.

---

## Current Status

**Version**: v0.0.3 (Auth & Rate Limiting — complete)
**Branch**: `feature/login-rate-limit`
**Tests**: 317 passing — `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`

### What's done
- ✅ Full agent stack: search tools, PydanticAI agent, citations, conversation management
- ✅ PostgreSQL + FTS (47K+ legal documents), Arize Phoenix observability
- ✅ Chainlit UI: RTL, sidebar, thinking steps, feedback 👍/👎, retry button, copy-to-clipboard
- ✅ RTL polish (11.11): JS direction detection, blockquote/table logical properties, inline code bidi
- ✅ Response streaming (11.12): `enable_streaming` config flag, `run_streaming(on_delta)` in agent
- ✅ Phoenix observability: real CHAIN/TOOL/LLM traces, token counts, feedback with message context
- ✅ Docker Compose deployment fully working (fixed 2026-05-09) — all three services healthy on `docker compose up -d`
- ✅ Share conversations (11.6): `allow_thread_sharing = true` + `@cl.on_shared_thread_view` — share button in sidebar, read-only public links
- ✅ Email + Invite Code Login: users log in with email + invite code (no external service); per-user daily rate limiting (30 req/day, configurable)

### What's next
- 📋 Task 11.9: Browser notifications via JS `Notification API` when tab is hidden

Full task list: `docs/development/tasks.md`

---

## Quick Commands

```bash
# Development server (avoids .env bash expansion issues)
python3 start_server.py

# Docker deployment
docker compose build && docker compose up -d
curl http://localhost:8000/health   # verify all services healthy

# Tests
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q

# Code quality (run before every commit)
.venv/bin/python -m black src/ && .venv/bin/python -m ruff check src/ && .venv/bin/python -m pytest tests/ --ignore=tests/integration -q
```

---

## Key Files

| File | Purpose |
|---|---|
| `src/law_agent/ui/app.py` | Chainlit handlers — on_message, on_feedback, action callbacks, health middleware |
| `src/law_agent/health.py` | `/health` and `/ready` check functions |
| `src/law_agent/agent/core.py` | LawAgent, show_thinking(), tool step wrappers |
| `src/law_agent/data/data_layer.py` | LawAgentDataLayer (conversation history) |
| `src/law_agent/config/settings.py` | Settings — reads DB_HOST/DB_USER/DB_PORT/DB_NAME/PHOENIX_ENDPOINT from env |
| `src/law_agent/prompts/search.md` | Agent system prompt |
| `config.yaml` | Application configuration |
| `.chainlit/config.toml` | UI config: sidebar, language, CSS/JS paths |
| `docker-compose.yml` | Three services: postgres, phoenix, app |
| `init-db.sh` | Creates phoenix database (shell script — `CREATE DATABASE` needs to run outside a transaction) |

---

## Critical Architecture Facts

**Chainlit**
- Table columns are **camelCase**: `createdAt` (TEXT), `userId`, `threadId`
- `@cl.step` on sync functions **doesn't render** — always use `async with cl.Step():`
- `cl.Message().send()` must come **after** `agent.run()` — otherwise steps appear after the answer
- `unsafe_allow_html = false` — use markdown `[1](url)`, not `<a>` tags for citations
- `steps` table needs `"defaultOpen"` BOOLEAN column or Chainlit crashes
- Sidebar requires `@cl.password_auth_callback` + `CHAINLIT_AUTH_SECRET` in `.env`
- Chainlit registers `/{full_path:path}` catch-all at import time — **use `BaseHTTPMiddleware`, not route decorators**, for any custom routes on `chainlit.server.app`

**Docker / Deployment**
- `CREATE DATABASE` cannot run in a PostgreSQL transaction block — put it in a `.sh` init script, not `.sql`
- Phoenix image is `arizephoenix/phoenix`, health endpoint is `/healthz` (no curl in container — use Python urllib)
- `settings.py` reads `DB_HOST`, `DB_USER`, `DB_PORT`, `DB_NAME`, `DB_PASSWORD`, `PHOENIX_ENDPOINT` from env — does NOT use `DATABASE_URL`
- Set `PHOENIX_ENDPOINT=http://phoenix:6006` in docker-compose (not localhost) so the app can reach Phoenix inside Docker

**Phoenix / Feedback**
- Feedback API: `POST /v1/span_annotations` with `span_id` (not trace_id)
- Start Phoenix **before** Chainlit starts
- Store span IDs in module-level `_session_span_ids` dict, not `cl.user_session`

**PydanticAI**
- LiteLLM model emits only `ToolCallPart` (no `TextPart` alongside tools)
- Use `agent.iter()` to access `CallToolsNode` for thinking step extraction

---

## Documentation Map

| Document | Read when |
|---|---|
| `docs/development/workflow.md` | **Starting any work** — full developer guide |
| `docs/development/tasks.md` | Understanding what's built and what's pending |
| `docs/architecture/design.md` | Understanding product requirements and system design |
| `docs/architecture/search.md` | Understanding how the agent searches (= system prompt) |
| `docs/architecture/database.md` | PostgreSQL schema, FTS, DAG relations |
| `docs/maintainer/deployment.md` | Production deployment runbook |
| `docs/features/{name}/progress.md` | Blockers, solutions, gotchas for a feature |

---

## Technology Stack

PydanticAI · Claude Sonnet (LiteLLM proxy) · PostgreSQL 14+ · SQLAlchemy 2.0 · Chainlit 2.11 · Arize Phoenix · structlog · uv · pytest · Black/Ruff/mypy · Docker Compose
