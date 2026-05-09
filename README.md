# Law Agent — AI Legal Assistant for Iranian Law

An intelligent conversational agent for Iranian legal documents, built with PydanticAI, Claude Sonnet, and PostgreSQL full-text search.

[![Tests](https://img.shields.io/badge/tests-304%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

## What It Does

Law Agent answers legal questions in Persian by searching a database of 47,000+ legal documents (laws, regulations, advisory opinions, court rulings, unified precedents). It performs multi-hop agentic search — reading summaries, following citation chains, and synthesizing answers with inline citations linked to iran.ir.

**Key behaviors**:
- Always responds in Persian
- Inline citations `[1]`, `[2]` linked to source documents on iran.ir
- Agentic search: agent decides the search strategy at each step
- Visible thinking steps in the UI (showing search progress)
- Conversation history per user (persistent sidebar)
- Thumbs up/down feedback with Phoenix observability

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ with the migrated law database
- LLM API credentials (Anthropic or LiteLLM proxy)
- `uv` package manager

### Development Setup

```bash
# 1. Install dependencies
uv pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env: LLM_BASE_URL, LLM_AUTH_TOKEN, DB_PASSWORD, CHAINLIT_AUTH_SECRET

# 3. Verify tests pass
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q

# 4. Start the server
python3 start_server.py
# App at http://localhost:7860
```

### Docker Compose (production)

```bash
# 1. Configure secrets
cp .env.example .env
# Edit .env: LLM_AUTH_TOKEN, LLM_BASE_URL, CHAINLIT_AUTH_SECRET

# 2. Build and start all services (postgres + phoenix + app)
docker compose build
docker compose up -d

# 3. Verify all services are healthy
curl http://localhost:8000/health
# App: http://localhost:8000 | Phoenix: http://localhost:6006
```

For full production instructions see **[`docs/maintainer/deployment.md`](docs/maintainer/deployment.md)**.

---

## Architecture

### Three core search tools

The agent has exactly three tools and decides the search strategy at each step:

| Tool | Purpose |
|---|---|
| `search_documents(query, tags, doc_types, limit)` | Full-text search on document summaries |
| `get_document(doc_id)` | Retrieve complete document content |
| `get_related_documents(doc_id, relation_types, limit)` | Traverse the citation DAG |

### Database

**`documents`** (47,434 rows): `doc_id`, `title`, `doc_type`, `date`, `summary`, `full_content`, `tags`, `search_vector`

**`relations`** (300,174 rows): `src_doc_id`, `dst_doc_id`, `relation_type` — directed citation graph

Document types: `law`, `regulation`, `advisory_opinion`, `court_ruling`, `unified_precedent`

### Stack

| Component | Technology |
|---|---|
| Agent | PydanticAI |
| LLM | Claude Sonnet via LiteLLM proxy |
| Database | PostgreSQL 14+ with `persian_custom` FTS config |
| ORM | SQLAlchemy 2.0 async |
| UI | Chainlit 2.11 (RTL, sidebar, steps, actions) |
| Observability | Arize Phoenix (self-hosted Docker) |
| Config | Pydantic Settings + `config.yaml` |
| Logging | structlog (JSON in production) |
| Deployment | Docker Compose |

---

## Development

```bash
make format      # Black
make lint        # Ruff
make typecheck   # mypy
make test        # pytest
make all         # All four
```

For the complete developer guide — how to build features, write tests, commit, and document:

→ **[`docs/development/workflow.md`](docs/development/workflow.md)**

For what's built and what's next:

→ **[`docs/development/tasks.md`](docs/development/tasks.md)**

---

## Project Structure

```
src/law_agent/
├── agent/          # LawAgent, ConversationManager, show_thinking()
├── tools/          # search_documents, get_document, get_related_documents
├── database/       # SQLAlchemy models, connection pooling
├── data/           # LawAgentDataLayer (Chainlit conversation history)
├── ui/             # app.py (Chainlit handlers + health middleware), citations.py
├── health.py       # /health and /ready check functions
├── observability/  # Phoenix tracing and feedback
├── config/         # Settings (Pydantic) — reads all DB/Phoenix env vars
└── prompts/        # search.md (system prompt), starters.yaml

tests/
├── unit/           # Pure Python, fast
├── ui/             # Chainlit handler behavior (mocked)
├── integration/    # Require running PostgreSQL
└── load/           # Locust load tests

docs/
├── architecture/   # design.md, search.md, database.md
├── development/    # workflow.md, tasks.md
├── maintainer/     # deployment.md — production runbook
├── best-practices/ # agent-engineering.md, evaluation.md
└── features/       # One folder per feature: plan.md + progress.md
```

---

## Documentation

- **[docs/README.md](docs/README.md)** — Full documentation index
- **[docs/architecture/design.md](docs/architecture/design.md)** — System design and product requirements
- **[docs/architecture/search.md](docs/architecture/search.md)** — Agent search strategy (= system prompt)
- **[docs/development/workflow.md](docs/development/workflow.md)** — Developer guide
- **[docs/maintainer/deployment.md](docs/maintainer/deployment.md)** — Production deployment runbook
- **[docs/features/performance/PERFORMANCE.md](docs/features/performance/PERFORMANCE.md)** — Performance benchmarks
