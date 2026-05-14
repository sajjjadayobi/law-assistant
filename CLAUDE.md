# CLAUDE.md

Project instructions. Start with `docs/development/workflow.md`, then use this as a reference.

---

## Quick Commands

**Before every commit:**
```bash
make all                    # format + lint + typecheck + test
```

**Development:**
```bash
python3 start_server.py     # Start Chainlit server (:7860)
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q     # Run all tests quickly
make coverage               # Generate coverage report (htmlcov/index.html)
```

**Code quality (individual):**
```bash
make format                 # Black formatting
make lint                   # Ruff linting + fixes
make typecheck              # mypy type checking
make test                   # pytest (verbose output)
```

**Docker / Deployment:**
```bash
docker compose build        # Build all images
docker compose up -d        # Start all services
docker compose down         # Stop all services
docker compose logs app     # View app logs
curl http://localhost:8000/health    # Check health
curl http://localhost:8000/ready     # Check readiness
```

**Cleanup:**
```bash
make clean                  # Remove caches, coverage, build artifacts
docker compose down -v      # Stop services + remove volumes
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

## Must-Dos

✅ **Put ALL configuration in `config.yaml`** — never hardcode limits, URLs, thresholds, timeouts, or feature flags  
✅ Use `async with cl.Step():` for Chainlit steps (sync `@cl.step` doesn't render)  
✅ Send `cl.Message().send()` **after** `agent.run()` completes, not before  
✅ Use `BaseHTTPMiddleware` for custom routes on `chainlit.server.app` (not decorators)  
✅ Use markdown `[1](url)` for citations, not `<a>` tags (`unsafe_allow_html = false`)  
✅ Store span IDs in module-level `_session_span_ids` dict, not `cl.user_session`  
✅ Start Phoenix **before** Chainlit (OTel exporter needs it)  
✅ Use `@cl.password_auth_callback` + `CHAINLIT_AUTH_SECRET` for sidebar + per-user history  
✅ Put `CREATE DATABASE` in `.sh` init script, not `.sql` (can't run in transaction)  
✅ Use `POST /v1/span_annotations` with `span_id` (not trace_id) for Phoenix feedback  
✅ Read `docs/development/workflow.md` before starting any work  
✅ Check `docs/maintainer/learning.md` when you hit a blocker  
✅ Run `make all` before committing (format, lint, typecheck, test)  

## Don'ts

❌ **Don't hardcode any config** — limits, URLs, timeouts, thresholds, feature flags all go in `config.yaml` (see workflow.md 6b)  
❌ Don't use `cl.user_session` for cross-callback state (use module-level dict)  
❌ Don't hardcode `localhost` for Phoenix — use `http://phoenix:6006` in Docker  
❌ Don't use `DATABASE_URL` — set DB env vars individually (`DB_HOST`, `DB_USER`, etc.)  
❌ Don't use `arizehq/phoenix` image — correct name is `arizephoenix/phoenix`  
❌ Don't skip table column naming — use **camelCase** (`createdAt`, not `created_at`)  
❌ Don't send messages before steps complete (steps appear out of order)  
❌ Don't skip the `steps` table `"defaultOpen"` BOOLEAN column (Chainlit crashes)  
❌ Don't mix structlog kwargs with standard Python logging (use `%s format strings)  
❌ Don't place UI tests in `tests/unit/ui/` (conflicts with `tests/ui/` module)  
❌ Don't commit without updating `CLAUDE.md`, `tasks.md`, and feature `progress.md`

---

## Documentation

| Document | When to read |
|---|---|
| `docs/development/workflow.md` | **First** — orientation, feature workflow, commit guide |
| `docs/maintainer/learning.md` | **When stuck** — blockers, solutions, hard-won lessons |
| `docs/development/tasks.md` | Understanding scope: what's built, what's pending |
| `docs/architecture/design.md` | Product requirements, system design, document types |
| `docs/architecture/search.md` | Agent system prompt (the implementation) |
| `docs/architecture/database.md` | PostgreSQL schema, FTS, relations |
| `docs/maintainer/deployment.md` | Production runbook |
| `docs/features/{name}/progress.md` | Feature-specific blockers and solutions |

---

## Technology Stack

PydanticAI · Claude Sonnet (LiteLLM proxy) · PostgreSQL 14+ · SQLAlchemy 2.0 · Chainlit 2.11 · Arize Phoenix · structlog · uv · pytest · Black/Ruff/mypy · Docker Compose
