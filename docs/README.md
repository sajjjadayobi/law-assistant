# Law Agent — Documentation

**An AI-powered legal assistant for Iranian law built with PydanticAI, Claude Sonnet, and PostgreSQL.**

---

## Start Here

New to the project? Read in this order:

1. **[`architecture/design.md`](architecture/design.md)** — Product requirements, document types, agent behavior
2. **[`architecture/search.md`](architecture/search.md)** — How the agent searches (this file IS the system prompt)
3. **[`development/workflow.md`](development/workflow.md)** — How to build features: setup → code → test → commit
4. **[`development/tasks.md`](development/tasks.md)** — What's built, what's pending, key implementation facts

---

## Architecture

| Document | Contents |
|---|---|
| [`architecture/design.md`](architecture/design.md) | Functional requirements, document hierarchy, conversation behavior, citation format |
| [`architecture/search.md`](architecture/search.md) | Agentic search philosophy, 3 core tools, multi-hop patterns, system prompt |
| [`architecture/database.md`](architecture/database.md) | PostgreSQL schema, `documents` and `relations` tables, FTS configuration |
| [`architecture/migration/`](architecture/migration/) | Database migration scripts (HTML → clean text), schema SQL |

---

## Development

| Document | Contents |
|---|---|
| [`development/workflow.md`](development/workflow.md) | **Full developer guide**: setup, feature process, testing, committing, docs, available skills, critical architecture facts |
| [`development/tasks.md`](development/tasks.md) | What's built (Phases 0–9, UI v0.0.2), what's pending, key implementation details per feature |

---

## Features

One folder per feature with `plan.md` (design decisions) and `progress.md` (development journal with blockers and solutions).

```
docs/features/
├── login/                  # @cl.password_auth_callback, JWT sessions
├── configuration/          # Pydantic Settings, config.yaml, .env secrets
├── search-tools/           # search_documents, get_document, get_related_documents
├── agent-core/             # PydanticAI agent, conversation management, citations
├── ui/                     # Chainlit setup, RTL, citation rendering
├── observability/          # Arize Phoenix, OpenTelemetry, token tracking
├── testing-cicd/           # pytest, CI pipeline, pre-commit hooks
├── deployment/             # Docker Compose, Dockerfile, health checks → DEPLOYMENT.md
├── performance/            # Indexes, LRU cache, connection pooling → PERFORMANCE.md
├── conversation-sidebar/   # LawAgentDataLayer, camelCase schema, auth requirement
├── thinking-steps/         # async cl.Step(), dynamic names, step ordering
├── feedback/               # @cl.on_feedback, Phoenix span annotations, two-click UI
└── retry-messages/         # cl.Action retry, session-scoped cleanup, action callback
```

### Key learnings by feature

**`conversation-sidebar/progress.md`** — Chainlit DB schema is camelCase, `createdAt` is TEXT not TIMESTAMP, never override `execute_sql()`

**`thinking-steps/progress.md`** — `@cl.step` on sync functions doesn't render, `cl.Message().send()` must come after `agent.run()`, `steps` table needs `"defaultOpen"` BOOLEAN column

**`feedback/progress.md`** — Phoenix feedback: `POST /v1/span_annotations` with `span_id`, module-level dict for cross-coroutine session state, start Phoenix before Chainlit

**`retry-messages/progress.md`** — `cl.user_session` for per-session action list, `action.forId` to remove error message, `@cl.action_callback` re-calls `main()`

---

## Best Practices

| Document | Contents |
|---|---|
| [`best-practices/agent-engineering.md`](best-practices/agent-engineering.md) | Multi-context window workflows, progressive disclosure, state management |
| [`best-practices/evaluation.md`](best-practices/evaluation.md) | Eval-driven development, golden sets, LLM-as-judge |

---

## Deployment & Performance

- **[`features/deployment/DEPLOYMENT.md`](features/deployment/DEPLOYMENT.md)** — Full production deployment guide: Docker Compose, environment setup, health checks, monitoring
- **[`features/performance/PERFORMANCE.md`](features/performance/PERFORMANCE.md)** — Performance benchmarks, database indexes, caching strategy, load test results

---

## Technology Stack

| Layer | Technology |
|---|---|
| Agent | PydanticAI |
| LLM | Claude Sonnet via LiteLLM proxy |
| Database | PostgreSQL 14+ with `persian_custom` FTS |
| ORM | SQLAlchemy 2.0 async |
| UI | Chainlit 2.11 |
| Observability | Arize Phoenix (self-hosted) |
| Config | Pydantic Settings + YAML |
| Logging | structlog |
| Testing | pytest + pytest-asyncio |
| Quality | Black, Ruff, mypy |
| Deployment | Docker Compose |
