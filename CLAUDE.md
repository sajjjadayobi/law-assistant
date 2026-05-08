# CLAUDE.md

Project instructions for Claude Code. Read this first, then follow the links.

---

## Current Status

**Version**: v0.0.2 (Enhanced UI — in progress)
**Branch**: `feature/phase-11-thinking-steps`
**Tests**: 288 passing (after cleanup) — `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`

### What's done
- ✅ Full agent stack: search tools, PydanticAI agent, citations, conversation management
- ✅ PostgreSQL + FTS (47K+ legal documents), Arize Phoenix observability
- ✅ Chainlit UI: RTL, sidebar, thinking steps, feedback 👍/👎, retry button, copy-to-clipboard
- ✅ Docker Compose deployment, CI pipeline, 288 tests (cleaned up dead code)

### What's next
- 📋 Task 11.9: Browser notifications
- 📋 Task 11.11: RTL polish
- 📋 Task 11.12: Response streaming

Full task list: `docs/development/tasks.md`

---

## Quick Commands

```bash
# Start server (use this — avoids .env bash expansion issues)
python3 start_server.py

# Tests
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q

# Code quality (run before every commit)
make all           # format + lint + typecheck + test

# Individual checks
make format        # Black
make lint          # Ruff
make typecheck     # mypy
make test          # pytest
```

---

## Key Files

| File | Purpose |
|---|---|
| `src/law_agent/ui/app.py` | Chainlit handlers — on_message, on_feedback, action callbacks |
| `src/law_agent/agent/core.py` | LawAgent, show_thinking(), tool step wrappers |
| `src/law_agent/data/data_layer.py` | LawAgentDataLayer (conversation history) |
| `src/law_agent/prompts/search.md` | Agent system prompt |
| `src/law_agent/prompts/starters.yaml` | Welcome screen starter questions |
| `config.yaml` | Application configuration |
| `.chainlit/config.toml` | UI config: sidebar, language, CSS/JS paths |
| `.chainlit/translations/fa-IR.json` | Persian UI strings |
| `public/patch.css` / `public/patch.js` | Custom UI CSS and JavaScript |

---

## Critical Architecture Facts

Things that cost hours to discover — know them before you start.

**Chainlit**
- Table columns are **camelCase**: `createdAt` (TEXT), `userId`, `threadId`
- `@cl.step` on sync functions **doesn't render** — always use `async with cl.Step():`
- `cl.Message().send()` must come **after** `agent.run()` — otherwise steps appear after the answer
- `unsafe_allow_html = false` — use markdown `[1](url)`, not `<a>` tags for citations
- `steps` table needs `"defaultOpen"` BOOLEAN column or Chainlit crashes
- Sidebar requires `@cl.password_auth_callback` + `CHAINLIT_AUTH_SECRET` in `.env`

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
| `docs/features/{name}/plan.md` | Why a feature was designed a certain way |
| `docs/features/{name}/progress.md` | Blockers, solutions, gotchas for a feature |
| `docs/best-practices/` | Agent engineering and evaluation patterns |

---

## Technology Stack

PydanticAI · Claude Sonnet (LiteLLM proxy) · PostgreSQL 14+ · SQLAlchemy 2.0 · Chainlit 2.11 · Arize Phoenix · structlog · uv · pytest · Black/Ruff/mypy · Docker Compose
