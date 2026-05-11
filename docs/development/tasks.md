# Law Agent — Task History & Roadmap

Single source of truth for what has been built, what is in progress, and what comes next. Each entry describes **what was done and why it matters**, not a wish-list.

**Current version**: v0.0.2 (Enhanced UI — in progress)
**Tests**: 312 passing — `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`

---

## ✅ Foundation (Phases 0–2)

### Environment & Project Structure
- Python 3.10+ with `uv` package manager
- `pyproject.toml` with all dependencies, Black/Ruff/mypy configurations
- Standard `src/law_agent/` layout with `agent/`, `tools/`, `database/`, `ui/`, `config/`, `observability/`, `prompts/`

### Configuration System
- Pydantic Settings + `config.yaml` for typed defaults
- Secrets (`DB_PASSWORD`, `LLM_AUTH_TOKEN`, `CHAINLIT_AUTH_SECRET`) only in `.env` (gitignored)
- `.env.example` documents all required variables
- Nested models: `ModelConfig`, `DatabaseConfig`, `SearchConfig`, `UIConfig`, `ConversationConfig`, `LoggingConfig`

### Logging
- structlog with JSON output in production, colored console in development
- Every significant operation logged with structured key=value pairs
- Log level configurable via `config.yaml`

### Database Layer
- Async SQLAlchemy engine with connection pooling (5–15 connections)
- ORM models for `documents` (read-only) and `relations` (read-only) — no new tables created
- Session factory with context manager for safe transaction handling
- See `docs/features/configuration/` and `docs/architecture/database.md`

---

## ✅ Search Tools (Phase 3)

Three composable tools that give the agent full access to the legal corpus. The agent decides the search strategy — there is no fixed algorithm.

### `search_documents(query, tags, doc_types, limit)`
- PostgreSQL FTS using `persian_custom` text search config (`@@` operator, `ts_rank()` scoring)
- Optional filters: `doc_types` (law, regulation, etc.), `tags` (subject classifications)
- Returns `List[DocSummary]` with relevance scores, sorted descending
- Results shown in UI as `async with cl.Step(type="retrieval")` with dynamic name: `"جستجو — N سند پیدا شد"`

### `get_document(doc_id)`
- Fetches full document content from `documents.full_content`
- Used when agent has identified a promising document to read for answering
- Returns complete metadata: title, doc_type, date, summary, tags, full_content
- UI step shows: `"خواندن سند — {title}"`

### `get_related_documents(doc_id, relation_types, limit)`
- Traverses the citation DAG in `relations` table: `src_doc_id → dst_doc_id`
- Used to fetch parent laws cited by regulations, or advisory opinions citing a law
- UI step shows: `"اسناد مرتبط — N سند"`

**Persian text**: All queries normalized via Hazm (`Normalizer`) before FTS — handles ك→ک, ي→ی, diacritics, zero-width chars.

See `docs/features/search-tools/`

---

## ✅ Agent Core (Phase 4)

### PydanticAI Agent
- `LawAgent` wraps a PydanticAI `Agent` with three registered tools
- Model: Claude Sonnet via LiteLLM proxy (`LLM_BASE_URL` + `LLM_AUTH_TOKEN`)
- System prompt loaded from `src/law_agent/prompts/search.md` (the search strategy and persona instructions)
- `agent.iter()` used for streaming — enables hooking into `CallToolsNode` for thinking step extraction

### Conversation Management
- `ConversationManager` holds per-session `message_history` and `turn_count`
- Hard limit: 50 turns per conversation (configurable in `config.yaml`)
- Message history passed as `conversation_history` to each `agent.run()` call

### Citation System
- Agent responses contain inline `[1]`, `[2]` markers referencing doc_ids
- `CitationFormatter` extracts markers, resolves to iran.ir URLs, renders as markdown links
- Deduplication: same doc_id referenced twice gets one citation number
- `unsafe_allow_html = false` in Chainlit — citations must be markdown, not HTML

### Error Handling
- 7 custom exception types with Persian user-facing messages
- `ModelError`, `SearchError`, `DatabaseError`, `TurnLimitExceeded`, `NoDocumentsFound`, etc.
- All exceptions logged with full context before re-raising

See `docs/features/agent-core/`

---

## ✅ Observability (Phase 6)

### Arize Phoenix
- Self-hosted at `http://localhost:6006` via Docker Compose
- PydanticAI auto-instrumentation via `opentelemetry-instrumentation-pydantic-ai`
- All agent runs produce spans visible in Phoenix UI

### Tracing
- Custom `"user_turn"` span wraps each `agent.run()` call
- Span ID captured in module-level `_session_span_ids[session_id]` for feedback linkage
- Token usage (input/output) and estimated cost tracked per span

### Feedback Integration
- `@cl.on_feedback` → `POST http://localhost:6006/v1/span_annotations` with `span_id`
- Annotation payload: `{"name": "user_feedback", "score": 1/-1, "annotator_kind": "HUMAN"}`
- **Critical**: use `span_id` not `trace_id`; start Phoenix before Chainlit

See `docs/features/observability/` and `docs/features/feedback/`

---

## ✅ Testing & CI (Phase 7)

### Test Suite (314 tests)
- `tests/unit/` — pure Python, no DB, fast
- `tests/ui/` — Chainlit handler behavior with mocked `cl.*`
- `tests/integration/` — require running PostgreSQL, skipped in CI unless DB available
- `tests/load/` — Locust-based load tests

### Quality Gates
- `make format` — Black auto-formatting
- `make lint` — Ruff linting (E, W, F, I rules)
- `make typecheck` — mypy strict mode
- `make test` — full pytest suite
- `make all` — all four in sequence

### CI Pipeline
- `.github/workflows/ci.yml` with lint, typecheck, and test jobs
- PostgreSQL service container for integration tests
- Runs on every PR and push to `main`

### Pre-commit hooks
- `.pre-commit-config.yaml` with Black, Ruff, mypy
- Install with `pre-commit install`

See `docs/features/testing-cicd/`

---

## ✅ Deployment (Phase 8)

- **Dockerfile**: multi-stage build (builder + runtime), non-root user, < 500MB image
- **docker-compose.yml**: three services — `postgres`, `phoenix`, `app` — with health checks and volume mounts
- **Environment**: all secrets via `.env`, documented in `.env.example`
- **Health checks**: `/health` (all components), `/ready` (database ready)
- **Production logging**: JSON format, log rotation, configurable per-module levels

See `docs/features/deployment/DEPLOYMENT.md` for full production guide.

---

## ✅ Performance (Phase 9)

- **6 new indexes** on `documents`: `(doc_type)`, `(date)`, `(search_vector)` GIN, composite `(doc_type, date)`, etc.
- **5 new indexes** on `relations`: `(dst_doc_id)`, `(relation_type)`, composite patterns
- **LRU search cache**: 1-hour TTL, ~35–45% hit rate on repeated queries
- **Document content cache**: 24-hour TTL for fetched document bodies
- **Query optimization**: explicit `ANALYZE documents` in migration, planner statistics up-to-date

Benchmarks: `search_documents` P99 ~400–600ms, `get_document` P99 ~200–300ms, full agent response ~2–4s (cached).

See `docs/features/performance/PERFORMANCE.md`

---

## ✅ UI — v0.0.1 Base (Phase 5)

- Chainlit 2.11 chat interface
- RTL support via `public/patch.css`: Vazirmatn font, `direction: auto` on text elements, code blocks forced LTR
- Custom JS via `public/patch.js`: placeholder text, copy-to-clipboard buttons
- Citation links as markdown `[N](url)` — HTML not allowed (`unsafe_allow_html = false`)
- `config.yaml` driven: `show_thinking`, `show_tool_calls`, `enable_feedback`

See `docs/features/ui/`

---

## ✅ UI — v0.0.2 Enhanced (Phase 11)

### Login (`@cl.password_auth_callback`)
- Any username/password accepted — purpose is user identity for thread isolation
- `CHAINLIT_AUTH_SECRET` in `.env` generates JWT session tokens
- Sessions last 15 days (`user_session_timeout = 1296000` in config.toml)
- **Without this, the conversation sidebar doesn't work** — Chainlit requires auth for per-user threads

See `docs/features/login/`

### 11.1 — Centered welcome screen
- `@cl.set_chat_profiles` returns one `cl.ChatProfile` with a `starters` list
- 3 starter questions loaded from `src/law_agent/prompts/starters.yaml`
- Law scales logo at `/public/logo.svg`, description below it
- After first message, layout switches to standard bottom-input chat

### 11.2 — Conversation history sidebar
- `LawAgentDataLayer` extends Chainlit `SQLAlchemyDataLayer` — minimal override (139 lines)
- Only `create_step()` and `get_all_user_threads()` overridden; everything else delegated to parent
- **Schema gotcha**: Chainlit creates tables with camelCase columns — `createdAt` (TEXT), `userId`, `threadId`
- `createdAt` is stored as ISO string TEXT, not TIMESTAMP — date grouping parses this manually
- Threads grouped in sidebar by: امروز / دیروز / ۷ روز گذشته / ۳۰ روز گذشته
- A `asyncio.Lock` in `create_step()` prevents race condition creating the thread on first message

See `docs/features/conversation-sidebar/`

### 11.3 — Thinking steps + UI polish
- Agent tool calls wrapped in `async with cl.Step(type="retrieval"):` — **not** `@cl.step` decorator (sync functions don't render in UI)
- Step name updated inside context manager after results are known: `step.name = "جستجو — 17 سند پیدا شد"`
- `cl.Message().send()` called **after** `agent.run()` completes — otherwise steps appear after the answer
- `steps` table requires `"defaultOpen"` BOOLEAN column — add with: `ALTER TABLE steps ADD COLUMN IF NOT EXISTS "defaultOpen" BOOLEAN DEFAULT FALSE`
- Translation: `messages.status.used = ""` in `fa-IR.json` removes "استفاده شد" suffix on steps
- Additional polish: Persian help page (`chainlit.md`), sidebar closed by default, law scales SVG logo

See `docs/features/thinking-steps/`

### 11.5 — Feedback 👍/👎
- `@cl.on_feedback` fires on every thumbs click: stores to PostgreSQL via `upsert_feedback`, also POSTs to Phoenix
- Phoenix endpoint: `POST /v1/span_annotations` with body `{"span_id": "...", "name": "user_feedback", "score": 1/-1, ...}`
- Span ID from `_session_span_ids[session_id]` (module-level dict) — `cl.user_session` is unreliable across async coroutines
- UI requires **two clicks**: thumbs button → comment dialog → "ثبت نظر" submit button
- Phoenix must be running before Chainlit starts or the OTLP exporter silently fails

See `docs/features/feedback/`

### 11.6 — Share conversations

- `allow_thread_sharing = true` in `.chainlit/config.toml` — enables the share button UI
- `@cl.on_shared_thread_view` callback in `app.py` — returns `bool(metadata["is_shared"])` to authorize read-only access
- Chainlit handles everything else: `PUT /project/thread/share` toggle endpoint, `GET /project/share/{thread_id}` read-only route, copy-link button, sidebar UI, and `is_shared`/`shared_at` metadata in the existing `threads` table
- Persian translations for all share UI strings already present in `fa-IR.json` (no translation work needed)
- **Both flags must be set**: `allow_thread_sharing = true` AND `on_shared_thread_view` defined — Chainlit checks `threadSharing = allow_thread_sharing AND callback_exists`
- **Share requires login** — Chainlit's `UserParam` dependency always requires auth when `password_auth_callback` is configured. Share links work for any authenticated user, not truly anonymous viewers. This is by design.
- **Bug fix in `create_step`** — `cl.User.id` is `None` (only `PersistedUser` has `id`). Fixed by falling back to `get_user(identifier)` to resolve the UUID. Without this fix, threads could lack `userIdentifier`, causing `is_thread_author()` to return 404 and block sharing.

See `docs/features/share-conversations/`

### 11.8 — Retry failed messages
- On any exception in `@cl.on_message`: sends error message with `cl.Action(name="retry", label="تلاش مجدد")`
- Action payload: `{"message_content": original_query}`
- Retry actions stored in `cl.user_session["retry_actions"]` as a list, cleared at start of next message
- `@cl.action_callback(name="retry")`: calls `cl.Message(id=action.forId).remove()` then re-calls `main()` with original content
- Error message text explicitly says "با زدن دکمه «تلاش مجدد»" so users know the button exists

See `docs/features/retry-messages/`

### 11.10 — Copy to clipboard
- `addCopyButtons()` in `public/patch.js` injects a `<button class="copy-btn">کپی</button>` into every `<pre>` block
- `MutationObserver` re-runs on DOM changes so new messages get buttons automatically
- On click: `navigator.clipboard.writeText()` → button shows "✓ کپی شد" for 2s → reverts
- Button positioned `bottom: 8px; left: 8px` in `public/patch.css` (RTL-friendly, overlays code block corner)

### 11.11 — RTL polish
- `applyAutoDirection()` in `public/patch.js`: counts Persian `[؀-ۿ]` vs Latin `[a-zA-Z]` chars in `.prose` elements; sets `dir="rtl"` if ratio > 30%, `dir="ltr"` if < 10%, otherwise falls back to CSS `direction: auto`
- Single consolidated `domObserver` (replaces two separate observers) calls placeholder + copy button + direction functions on every DOM change
- `public/patch.css`: blockquotes use `border-inline-start` (logical property → right border in RTL, left in LTR); tables get `direction: rtl; text-align: start`; inline code within prose gets `unicode-bidi: embed; display: inline-block` so it stays LTR in RTL paragraphs
- `[dir="rtl"] code` and `[dir="ltr"] code` rules ensure code blocks are never flipped by direction inheritance

See `docs/features/rtl-polish/`

---

### 11.12 — Response streaming

- `ui.enable_streaming: true/false` in `config.yaml` + `UIConfig.enable_streaming` in `settings.py` (default `true`)
- `LawAgent.run_streaming(user_query, conversation_history, conversation_id, on_delta)` in `core.py`:
  - Uses `agent.run_stream()` + `result.stream_text(delta=True)` to yield tokens
  - Calls async `on_delta(token)` callback for each delta
  - Returns `(full_text, updated_history)` — same signature as `run()`
  - Tool functions still execute normally; their `cl.Step()` blocks still render
  - The synthetic "تحلیل سوال" planning step (from `CallToolsNode`) is not shown in streaming mode
- `app.py` streaming path: send empty `cl.Message` → stream tokens → format citations → `msg.update()`
- `app.py` non-streaming path: unchanged `agent.run()` → `cl.Message(formatted).send()`
- **Citation formatting**: applied on complete streamed text after stream ends, then `msg.update()` (two-phase approach to avoid split-token issues with `[1]`, `[2]` markers)
- **Reasoning model caveat**: `grok-4-1-fast-reasoning` generates its full response during the thinking phase, then sends all tokens in a rapid burst (verified: 6 SSE chunks all arriving at t=3.29s). No visible streaming effect regardless of `enable_streaming`. Default is `false`. Enable only when using progressive-generation models (claude-sonnet, gpt-4o).
- 6 tests in `tests/ui/test_streaming.py`

See `docs/features/streaming/`

---

## 📋 Pending

### Phase 11 — Remaining UI tasks

| Task | Description | Effort |
|---|---|---|
| **11.9** | Browser notifications via JS `Notification API` when tab is hidden | ~2h |

### Deferred

- **11.7** Export to Markdown

### Phase 10 — Scalability (not started, no timeline)
- Kubernetes / Helm deployment
- Redis distributed caching (replace in-process LRU)
- PostgreSQL read replicas
- Multi-region setup
