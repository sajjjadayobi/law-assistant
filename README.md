# Law Agent — AI Legal Assistant for Iranian Law

> **This is a toy project.** Built as an experiment in fully agentic AI-assisted coding — every feature, test, and document in this repo was written collaboratively with Claude Code. The goal was to see how far you can get building real, working software for a non-trivial domain purely through agentic coding sessions. The end user is a lawyer friend who needed a way to search and query 47,000+ Iranian legal documents in Persian.

[![Tests](https://img.shields.io/badge/tests-317%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

## What It Does

Answers legal questions in Persian by searching a database of 47,000+ Iranian legal documents (laws, regulations, advisory opinions, court rulings, unified precedents). The agent performs multi-step search — reading summaries, following citation chains, and writing answers with inline citations linked to source documents.

---

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+ with the migrated law database
- LLM API credentials (any OpenAI-compatible provider)
- `uv` package manager

### Development Setup

```bash
# 1. Install dependencies
uv pip install -e ".[dev]"

# 2. Configure environment
cp .env.example .env
# Edit .env: LLM_BASE_URL, LLM_AUTH_TOKEN, DB_PASSWORD, CHAINLIT_AUTH_SECRET

# 3. Verify tests pass
make test

# 4. Start the server
.venv/bin/chainlit run src/law_agent/ui/app.py --port 7860 --headless
# App at http://localhost:7860
```

### Docker Compose

```bash
cp .env.example .env
# Edit .env: LLM_AUTH_TOKEN, LLM_BASE_URL, CHAINLIT_AUTH_SECRET

docker compose build && docker compose up -d

curl http://localhost:8000/health
# App: http://localhost:8000 | Phoenix: http://localhost:6006
```

Full production instructions: **[`docs/maintainer/deployment.md`](docs/maintainer/deployment.md)**

---

## Architecture

### Agent Tools

The agent has three tools and decides its own search strategy at each step:

| Tool | Purpose |
|---|---|
| `search_documents(query, tags, doc_types, limit)` | Full-text search on document summaries |
| `get_document(doc_id)` | Retrieve complete document content |
| `get_related_documents(doc_id, relation_types, limit)` | Traverse the citation graph |

### Database

**`documents`** (47,434 rows): `doc_id`, `title`, `doc_type`, `date`, `summary`, `full_content`, `tags`, `search_vector`

**`relations`** (300,174 rows): `src_doc_id`, `dst_doc_id`, `relation_type` — directed citation graph

Document types: `law`, `regulation`, `advisory_opinion`, `court_ruling`, `unified_precedent`

### Stack

| Component | Technology |
|---|---|
| Agent | PydanticAI |
| LLM | GPT-4.1-mini via MetisAI (`https://api.metisai.ir/openai/v1`) |
| Database | PostgreSQL 14+ with `persian_custom` FTS config |
| ORM | SQLAlchemy 2.0 async |
| UI | Chainlit 2.11 (RTL, sidebar, steps, feedback) |
| Auth | Email + invite code, per-user rate limiting |
| Observability | Arize Phoenix (self-hosted Docker) |
| Config | Pydantic Settings + `config.yaml` |
| Logging | structlog |
| Deployment | Docker Compose |

---

## Development

```bash
make all         # format + lint + typecheck + test
make test        # pytest only
make format      # Black
make lint        # Ruff
make typecheck   # mypy
```

Developer guide: **[`docs/development/workflow.md`](docs/development/workflow.md)**

Task list (what's built, what's next): **[`docs/development/tasks.md`](docs/development/tasks.md)**

Hard-won lessons from all sessions: **[`docs/maintainer/learning.md`](docs/maintainer/learning.md)**

---

## Project Structure

```
src/law_agent/
├── agent/          # LawAgent, tool wrappers
├── tools/          # search_documents, get_document, get_related_documents
├── database/       # SQLAlchemy models, connection pooling
├── data/           # LawAgentDataLayer (Chainlit conversation history)
├── ui/             # app.py (Chainlit handlers), citations.py, rate_limit.py
├── health.py       # /health and /ready endpoints
├── observability/  # Phoenix tracing and feedback
├── config/         # Settings (Pydantic)
└── prompts/        # system prompt, starter questions

tests/
├── unit/           # Pure Python, fast
├── ui/             # Chainlit handler behavior (mocked)
├── integration/    # Require running PostgreSQL
└── load/           # Locust load tests

docs/
├── architecture/   # design.md, search.md, database.md
├── development/    # workflow.md, tasks.md
├── maintainer/     # deployment.md, learning.md
├── best-practices/ # agent-engineering.md
└── features/       # One folder per feature: plan.md + progress.md
```
