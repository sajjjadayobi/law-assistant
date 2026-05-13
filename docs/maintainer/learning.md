# Learning.md — Consolidated Lessons from All Features

This document consolidates the key learnings, blockers, and patterns discovered across all feature implementations. Use this as a reference to avoid repeating past mistakes and understand proven solutions.

---

## Table of Contents

1. [Agent Architecture & Design](#agent-architecture--design)
2. [Chainlit Architecture](#chainlit-architecture)
3. [OpenTelemetry & Observability](#opentelemetry--observability)
4. [Testing & Mocking](#testing--mocking)
5. [Database & Data Layer](#database--data-layer)
6. [Docker & Deployment](#docker--deployment)
7. [UI/UX Patterns](#uiux-patterns)
8. [Configuration Management](#configuration-management)
9. [Async Programming](#async-programming)
10. [Common Pitfalls & Solutions](#common-pitfalls--solutions)

---

## Agent Architecture & Design

### System Prompt Is the Real Implementation

**Lesson**: The system prompt (500+ lines in `src/law_agent/prompts/search.md`) is the actual implementation of agent behavior, not the code. It:
- Guides search strategy (multi-hop patterns, when to combine tools)
- Explains document hierarchy and relationships
- Instructs persona detection (how to read user intent)
- Provides examples and reasoning patterns
- Can be updated without touching a single line of code

**Implication**: If agent behavior needs adjustment, modify the prompt first. Only change code for structural issues.

---

### Tools Should Be Dumb; Let the Agent Be Smart

**Lesson**: Keep tool implementations simple (return raw JSON, no logic):

```python
# ✅ CORRECT: Tool returns raw data
def search_documents(query: str) -> dict:
    results = db.search(query)
    return {"query": query, "count": len(results), "documents": [d.to_dict() for d in results]}

# ❌ WRONG: Tool applies logic
def search_documents(query: str) -> str:
    results = db.search(query)
    if len(results) == 0:
        return "No documents found. Try a broader query."
    best = max(results, key=lambda d: d.score)
    return f"Best match: {best.title}"
```

**Why**: The agent (with its system prompt) is smarter at deciding how to use results. When tools apply logic:
- Agent can't combine results creatively
- Thresholds and filters are hardcoded
- Tool becomes harder to test and debug
- Changes to behavior require code changes, not prompt tweaks

---

### Persona Detection Is Implicit, Not a Feature

**Lesson**: Don't build separate persona detection code. The agent naturally infers persona from query style (layperson, business, legal professional) and the system prompt guides appropriate responses.

**Why it's simpler**:
- Persona changes per message (not fixed)
- Agent adapts naturally to language complexity
- System prompt handles all guidance
- No classification model needed
- Fewer bugs, more flexible

---

### Error Messages Are UX, Not Logging

**Lesson**: Every error is an opportunity to help the user. Invest in error messages as much as you invest in happy-path UX.

**Pattern**:
- Log errors in English (for debugging)
- Show errors to users in Persian (for understanding)
- Include what was attempted (query, search strategy)
- Suggest recovery actions (try a different query, provide more context)
- Include error codes for troubleshooting

---

### Persian Text Handling Requires Attention

**Lesson**: Unicode matters for Persian. Small differences break things:

| Issue | Wrong | Right | Impact |
|-------|-------|-------|--------|
| Question mark | `?` (U+003F) | `؟` (U+061F) | Agent responses, user queries |
| Word normalization | `ك` (Arabic) | `ک` (Persian) | FTS search, character counting |
| Char counting | Count as 1 | Consider combining marks | String length checks |

**Implication**: Always include Persian text in tests. ASCII-only tests will miss these issues.

---

### Conversation Management: Simple State Tracking

**Lesson**: Keep conversation state simple. Just track:
- Message history (what was said)
- Turn count (prevent infinite loops)
- Optional metadata (persona hints, search strategy)

Don't track:
- User intent classifications (agent infers this)
- Extracted facts (agent remembers context)
- Complex state machines (context window is the memory)

---

## Chainlit Architecture

### Session Storage: Use Module-Level Dict, Not `cl.user_session`

**Lesson**: `cl.user_session` is context-var based and unreliable across different async contexts. If you need to share state between `@on_message` and `@cl.on_feedback` (or other callbacks), use a module-level dict.

**Example**:
```python
# ✅ CORRECT: Module-level dict keyed by session_id
_session_span_ids: dict[str, str] = {}

# In @on_message:
_session_span_ids[session_id] = "16-hex-span-id"

# In @cl.on_feedback:
span_id = _session_span_ids.get(session_id)
```

**Why**: `@cl.on_feedback` runs in a different async context than `@on_message`, so `cl.user_session` reads don't see previously-set values.

---

### Routing: Use BaseHTTPMiddleware, Not Route Decorators

**Lesson**: Chainlit registers a `/{full_path:path}` catch-all route at module import time. Any custom routes added after that are shadowed. Always use `BaseHTTPMiddleware` on `chainlit.server.app` instead.

**Example**:
```python
# ❌ WRONG: Route is shadowed by Chainlit's catch-all
@app.get("/health")
async def health():
    return {"status": "ok"}

# ✅ CORRECT: Middleware runs before routing
class HealthCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/health":
            return JSONResponse({"status": "ok"})
        return await call_next(request)

app.add_middleware(HealthCheckMiddleware)
```

---

### Feedback Button Requires Two Clicks

**Lesson**: Chainlit's 👍/👎 feedback buttons open a dialog ("افزودن نظر"). Just clicking the button doesn't submit the feedback — the user must also click "ثبت نظر" to trigger `@cl.on_feedback`.

**Testing impact**: UI tests that only click the button without confirming the dialog will fail. Always test the full two-step flow.

---

### Table Column Names Are camelCase

**Lesson**: Chainlit stores data with camelCase column names (not snake_case): `createdAt` (TEXT, ISO string), `userId`, `threadId`, `defaultOpen` (BOOLEAN).

**Important**: If you add or modify columns in the steps/threads tables, use camelCase and ensure type matches what Chainlit expects.

---

### `@cl.step` on Sync Functions Doesn't Render

**Lesson**: `@cl.step` decorator only works on async functions. For sync functions, use `async with cl.Step():` context manager.

---

### `cl.Message().send()` Must Come After `agent.run()`

**Lesson**: If you send a message before `agent.run()` completes, subsequent tool steps appear *after* the answer in the chat, confusing the UI flow. Always complete agent processing, then send/update the message.

---

## OpenTelemetry & Observability

### Set `PHOENIX_PROJECT_NAME` Before Any Instrumentation

**Lesson**: Third-party instrumentors (especially Traceloop's OpenAI) trigger auto-init of Traceloop's OpenTelemetry configuration. This auto-init reads `PHOENIX_PROJECT_NAME` from env. If not set, spans go to the "default" project, polluting your main project.

**Fix**:
```python
import os
os.environ.setdefault("PHOENIX_PROJECT_NAME", "law-agent")
# Only THEN initialize tracing
```

**Why it matters**: The "default" project can't be deleted via API and becomes a junk drawer of test spans. Always prevent spans from landing there.

---

### Disable DB Instrumentors Explicitly

**Lesson**: When using Traceloop's `OpenAIInstrumentor().instrument()`, it auto-enables SQLAlchemy and psycopg2 instrumentation as a side effect, even if you never asked for it.

**Fix**:
```python
os.environ.setdefault("OTEL_PYTHON_DISABLED_INSTRUMENTATIONS", "sqlalchemy,psycopg2,psycopg2_binary")
OpenAIInstrumentor().instrument(tracer_provider=_tracer_provider)
# Also explicitly uninstrument in case the env var was ignored
SQLAlchemyInstrumentor().uninstrument()
```

**Why it matters**: Hundreds of useless "connect" spans clutter Phoenix, making it hard to find real traces. The environment variable is only honored by the CLI auto-instrumentation system — direct calls to `.instrument()` ignore it.

---

### Phoenix Feedback API: Use `span_id`, Not `trace_id`

**Lesson**: Phoenix's feedback annotation API requires `span_id` (the 16-hex-character ID of the specific span you're annotating), not `trace_id` (the conversation ID).

**Endpoint**: `POST /v1/span_annotations`

**Payload**:
```json
{
  "data": [{
    "span_id": "6e388b5d8c182c2d",
    "name": "user_feedback",
    "annotator_kind": "HUMAN",
    "result": {
      "label": "thumbs_up",
      "score": 1.0
    }
  }]
}
```

---

### Capture Span ID with `format(span.get_span_context().span_id, "016x")`

**Lesson**: OpenTelemetry span IDs are integers. Phoenix expects them as 16-character hex strings.

**Example**:
```python
ctx = span.get_span_context()
if ctx.is_valid:
    span_id = format(ctx.span_id, "016x")  # "6e388b5d8c182c2d"
```

---

### Start Phoenix Before Chainlit

**Lesson**: If Phoenix isn't up when the OTel exporter first tries to send, it uses a no-op exporter as fallback and never switches to the real Phoenix exporter. Always start Phoenix before Chainlit.

---

### Phoenix Span Notes vs Annotations

**Lesson**: Use **annotations** for scored feedback (thumbs up/down with a label), and **notes** for free-form comments.

- Annotations: `POST /v1/span_annotations` — scored, labeled, appears in Annotations tab
- Notes: `POST /v1/span_notes` — unscored comments, appears in prominent Notes panel (visible immediately, no extra click)

---

## Testing & Mocking

### MagicMock `spec=` Doesn't Allow Dynamic Attributes

**Lesson**: `MagicMock(spec=LawAgent)` blocks access to attributes set dynamically in `__init__`, like `self.agent` (the internal PydanticAI Agent instance).

**Fix**:
```python
# ❌ FAILS: spec prevents access to .agent
mock_agent = MagicMock(spec=LawAgent)
mock_agent.agent  # AttributeError

# ✅ CORRECT: Explicitly set the dynamic attribute
mock_agent = MagicMock(spec=LawAgent)
mock_agent.agent = MagicMock()  # Now it works
```

---

### Use AsyncMock for Async Functions

**Lesson**: Wrapping async code with `MagicMock` doesn't work. Use `AsyncMock` for coroutines, and set `__aenter__`/`__aexit__` for context managers.

**Example**:
```python
step_mock = MagicMock()
step_mock.__aenter__ = AsyncMock(return_value=step_mock)
step_mock.__aexit__ = AsyncMock(return_value=False)

with patch("law_agent.ui.app.cl.Step", return_value=step_mock):
    # Use async with cl.Step(): context manager in your code
    pass
```

---

### Test File Location Matters

**Lesson**: Both `tests/ui/` and `tests/unit/ui/` register as Python packages named `ui`. Having UI tests in both causes pytest module naming conflicts.

**Solution**: Keep all UI tests in `tests/ui/` (the established home for UI tests). Don't create `tests/unit/ui/`.

---

### InMemory Span Exporter for Testing OTel

**Lesson**: Use OpenTelemetry's `InMemoryMetricReader` and in-memory span processors to verify span attributes in unit tests without hitting a real Phoenix instance.

**Example**:
```python
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

exporter = InMemorySpanExporter()
tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

# ... run code that creates spans ...

spans = exporter.get_finished_spans()
assert spans[0].attributes["tool.name"] == "search_documents"
```

---

## Database & Data Layer

### Don't Override `execute_sql()` in Data Layer

**Lesson**: The parent `DataLayer` class handles SQLAlchemy session lifecycle. Overriding `execute_sql()` in a subclass can cause session bugs and resource leaks. Instead, override helper methods that `execute_sql()` calls, or use the `execute()` method directly.

---

### PostgreSQL `CREATE DATABASE` Can't Run in Transaction

**Lesson**: Docker's PostgreSQL init system runs `.sql` files inside a transaction block. `CREATE DATABASE` cannot execute inside a transaction.

**Solution**: Split init into two files:
- `init-db.sql` — `CREATE ROLE`, `ALTER DEFAULT PRIVILEGES` (transaction-safe)
- `init-db.sh` — `CREATE DATABASE` via `psql` command (runs outside transaction)

---

### Full-Text Search Uses `persian_custom` Config

**Lesson**: The project uses the `persian_custom` FTS configuration (not `english` or `simple`). If you're adding FTS queries, specify `@@ to_tsquery('persian_custom', ...)`.

---

## Docker & Deployment

### Phoenix Image: `arizephoenix/phoenix`, Not `arizehq/phoenix`

**Lesson**: The correct image name is `docker.io/arizephoenix/phoenix:latest`. `arizehq/phoenix` doesn't exist on Docker Hub.

---

### Phoenix Health Endpoint: `/healthz`, Not `/health`

**Lesson**: Phoenix's health check is at `/healthz` (not `/health`). Also, no `curl` in the Phoenix container — use Python `urllib` or `wget`.

**Example**:
```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6006/healthz')"]
```

---

### Docker Compose Environment Variables Must Be Explicit

**Lesson**: The settings system doesn't use `DATABASE_URL` or any other standard database connection string. All five DB parameters must be set individually in docker-compose.yml:

```yaml
environment:
  DB_HOST: postgres
  DB_USER: postgres
  DB_PORT: 5432
  DB_NAME: law_agent
  DB_PASSWORD: password
  PHOENIX_ENDPOINT: http://phoenix:6006
```

The settings system reads these in `from_yaml()` and overrides `config.yaml` defaults.

---

### Settings.py Must Override All DB Env Vars

**Lesson**: In `settings.py`, the `from_yaml()` method must read and apply `DB_HOST`, `DB_USER`, `DB_PORT`, `DB_NAME`, `DB_PASSWORD`, and `PHOENIX_ENDPOINT` from env vars, not just `DB_PASSWORD`.

**Why**: Docker Compose sets these individually, but the app defaults to `localhost` (config.yaml) if they're not overridden. The app connects to the wrong database.

---

### Dockerfile `config` Copy is a File, Not Directory

**Lesson**: There is no `config/` directory. Config is a single `config.yaml` file at the repo root.

```dockerfile
# ❌ WRONG: No config/ directory
COPY --chown=appuser:appuser config ./config

# ✅ CORRECT: config.yaml is a file
COPY --chown=appuser:appuser config.yaml .
```

---

### Dockerfile Builder Stage Needs `README.md`

**Lesson**: `pyproject.toml` references `README.md`. The builder stage must copy it, or `uv pip install .` fails.

```dockerfile
COPY pyproject.toml README.md ./
```

---

## UI/UX Patterns

### Auto-Direction Detection with Heuristics

**Lesson**: Chainlit doesn't support RTL natively. Use JavaScript to detect language and apply `dir="rtl"` or `dir="ltr"` dynamically.

**Heuristic**: Count Persian characters (`[؀-ۿ]`) vs Latin characters. If Persian > 30%, set RTL; if Latin > 10%, set LTR; otherwise, keep auto.

**Important**: Mark processed elements with a flag (`dataset.autoDir`) to avoid re-processing them on every update.

---

### RTL CSS Requires Logical Properties

**Lesson**: Simple `direction: rtl` isn't enough. Use logical properties for borders, padding, margins:

```css
/* ✅ CORRECT: Logical properties work for both LTR and RTL */
border-inline-start: 4px solid;
margin-inline-end: 1rem;
padding-inline-start: 1rem;

/* ❌ WRONG: Hardcoded left/right breaks in RTL */
border-left: 4px solid;
margin-right: 1rem;
```

---

### Inline Code in RTL Needs Bidi Isolation

**Lesson**: Inline code mixed with RTL prose (e.g., Persian text with a code snippet) can cause the direction to flip mid-line. Isolate inline code with:

```css
code {
  unicode-bidi: embed;
  display: inline-block;
}
```

---

### Streaming: Token Burst vs Progressive

**Lesson**: Reasoning models (e.g., grok-4-1-fast-reasoning) think first, then dump the complete response in a burst. Progressive-generation models (Claude Sonnet, GPT-4o) yield tokens gradually.

**Effect**: On reasoning models, streaming is indistinguishable from non-streaming (user waits 3s, then sees full response instantly). On progressive models, tokens arrive gradually (visible typing effect).

**Config**: Disable `enable_streaming` by default, enable only when switching to progressive models.

---

### Citation Parsing: Consistent Format Required

**Lesson**: Agent response format (e.g., `[1]`, `[2]`) must be consistent for regex parsing to work reliably. If the format varies, regex-based citation linking breaks.

**Solution**: Have the agent emit structured citations (like `[doc_id]` with `doc_id` being a number), then regex parse confidently. Fallback gracefully if parsing fails.

---

### Share Threads Require Authentication

**Lesson**: Chainlit's `UserParam` dependency enforces authentication when `password_auth_callback` is configured. Even `/share/{thread_id}` requires login.

**Trade-off**: "Share" doesn't mean "public" — shared threads are accessible to any authenticated user, not truly anonymous visitors. If you need truly public links, add a separate `BaseHTTPMiddleware` that serves a public view of shared threads.

---

### `cl.User.id` Can Be None

**Lesson**: `cl.User` (returned by `password_auth_callback`) doesn't have an `id` field. `PersistedUser` (returned by `authenticate_user` via WebSocket) does. In code that needs `user_id`, always have a defensive fallback:

```python
user_id = getattr(user, "id", None)
if not user_id and user.identifier:
    persisted = await self.get_user(user.identifier)
    user_id = persisted.id
```

---

### Authentication: `CHAINLIT_AUTH_SECRET` Format Matters

**Lesson**: `CHAINLIT_AUTH_SECRET` in `.env` must not contain literal quotes. The value is parsed by the startup script which strips surrounding double-quotes.

**Example**:
```bash
# ✅ CORRECT: value without quotes
CHAINLIT_AUTH_SECRET="your-secret-here"
# Loaded as: "your-secret-here"

# ❌ WRONG: quotes become part of the secret
CHAINLIT_AUTH_SECRET='"your-secret-here"'
# Loaded as: '"your-secret-here"' (quotes are part of the value)
```

**Implication**: If JWT validation fails mysteriously, check if quotes are included in the loaded value.

---

### Sidebar Requires Authentication

**Lesson**: Chainlit only shows per-user thread history (sidebar) when a user is authenticated. Without `@cl.password_auth_callback`, all requests are treated as anonymous and threads aren't grouped by user.

**Session Duration**: Controlled by `user_session_timeout` in `.chainlit/config.toml` (default 1,296,000 seconds = 15 days).

---

### Share Feature: Authentication Required

**Lesson**: Even shared threads require authentication. Chainlit's `UserParam` dependency enforces auth when `password_auth_callback` is configured. Shared threads are accessible to *any authenticated user*, not truly public.

**If you need truly public links**: Use `BaseHTTPMiddleware` to intercept `/project/share/{thread_id}` and serve a public view without requiring login.

---

## Configuration Management

### Separate Config Sections for Each Layer

**Lesson**: Organize `config.yaml` into logical sections (model, database, search, conversation, ui, logging). Define corresponding Pydantic `BaseModel` classes in `settings.py`. This keeps config organized and maintainable.

**Pattern**:
```yaml
model:
  name: claude-sonnet
  temperature: 0.1
database:
  host: localhost
  port: 5432
```

```python
class ModelConfig(BaseModel):
    name: str
    temperature: float

class DatabaseConfig(BaseModel):
    host: str
    port: int

class Settings(BaseModel):
    model: ModelConfig
    database: DatabaseConfig
```

---

### Env Vars Override YAML Defaults

**Lesson**: Use `from_yaml()` classmethod to load YAML, then apply environment variable overrides. This gives you the best of both worlds: readable defaults in YAML, secrets in `.env`.

```python
@classmethod
def from_yaml(cls):
    with open("config.yaml") as f:
        yaml_data = yaml.safe_load(f)
    
    # Override from env vars
    if os.getenv("DB_HOST"):
        yaml_data["database"]["host"] = os.getenv("DB_HOST")
    
    return cls(**yaml_data)
```

---

### Secrets Go in `.env`, Not `config.yaml`

**Lesson**: Never commit secrets (API keys, passwords, tokens) to config.yaml. Provide a `.env.example` template so developers know what to set.

---

## Async Programming

### Get OTel Span Context Across Async Boundaries

**Lesson**: OpenTelemetry span context propagates through `asyncio` automatically. If you create a span in one async function and reference it in another, `get_current_span()` works as long as they're in the same `asyncio` task chain.

**Example**:
```python
async def on_message(message):
    with tracer.start_as_current_span("user_turn") as span:
        response = await agent.run(message)  # agent.run in a different function
        # Span context still propagates to agent.run()
```

In `agent.py`'s `run()` method, `get_current_span()` returns the `user_turn` span from `on_message()`.

---

### Use `async with` for Context Managers, Never Sync `@` Decorator

**Lesson**: `@cl.step` on sync functions doesn't work. Always use `async with cl.Step():` for Chainlit steps.

---

## Agent Evaluation & Observability

### Start with End-to-End Evaluation, Not Component Tests

**Lesson**: Traditional evals test if the agent followed a specific path (input X → steps Y → output Z). With agentic systems, you can't predict the correct path. Instead:

1. **Evaluate the outcome**: Did the agent solve the user's problem?
2. **Evaluate the process reasonableness**: Was the approach reasonable (even if different from expected)?
3. **Use LLM-as-Judge**: A single prompt scoring 0.0-1.0 with pass/fail is more consistent than multi-step evaluation

**Pattern**:
```python
# ❌ WRONG: Check if agent used search_documents before get_document
assert calls[0].tool_name == "search_documents"
assert calls[1].tool_name == "get_document"

# ✅ CORRECT: Check if final answer was accurate and helpful
judge_prompt = """
Was this legal answer accurate, helpful, and properly cited?
Evaluate on: correctness (0-5), completeness (0-5), citations (0-5).
Pass if average > 3.5 and correctness > 3.
"""
```

---

### LLM-as-Judge Works Better Than Rubrics

**Lesson**: Multiple judges evaluating components leads to inconsistency. A single LLM call with one comprehensive prompt aligns better with human judgment.

**Why**: Humans naturally evaluate holistically. Breaking into rubrics loses nuance. An LLM judge naturally balances competing factors like "accurate but terse" vs "verbose but clear".

---

### Start Small; Evaluate Immediately

**Lesson**: Don't wait to build 100 test cases. Start with 5-10 examples with clear correct answers. In early development, changes have dramatic impact because there's abundant low-hanging fruit. Small-scale testing catches these wins fast.

**Pattern**: Evaluate after each major change, not at the end of development.

---

### Human Evaluation Catches What Automation Misses

**Lesson**: Automated evals catch predictable failures. Humans catch:
- Edge cases (unusual queries, system failures)
- Subtle biases (source selection, hallucinations on fringe topics)
- UX issues (confusing error messages, missing context)

**Recommendation**: Always include manual testing. Ask people to write free-form feedback about failures and how to fix them.

---

### Build Comprehensive Observability From the Start

**Lesson**: You'll need full production tracing to create feedback loops with agentic observability:
- Log tool calls and compute summary stats
- Monitor for new patterns in traces
- Flag anomalies for manual review
- Use observability data to find good few-shot examples
- Identify bugs through error pattern analysis

**Beyond basic logging**: Track number of tool calls, latency, token usage, error recovery attempts, tool success rates.

---

## Common Pitfalls & Solutions

### Blocker: Test File Location Conflict

**Problem**: Tests in both `tests/ui/` and `tests/unit/ui/` cause pytest module naming conflicts.

**Solution**: Use `tests/ui/` for all UI tests. Don't create `tests/unit/ui/`.

---

### Blocker: Chainlit Feedback Not Triggering

**Problem**: `@cl.on_feedback` doesn't fire even after clicking 👍.

**Root Cause**: The button click opens a dialog. The user must also click "ثبت نظر" to submit.

**Solution**: In UI tests, always test the full two-step flow (button click + dialog submission).

---

### Blocker: `send_feedback_to_phoenix()` Fails with Logging Error

**Problem**: `logger.info("event", key=value)` raises TypeError in `feedback.py`.

**Root Cause**: Mixing structlog style (arbitrary kwargs) with standard Python logging. Python's logger doesn't accept `**kwargs`.

**Solution**: Use standard logging format: `logger.info("message %s", value)`.

---

### Blocker: Phoenix Shows No LLM Traces (Only DB Noise)

**Problem**: Phoenix waterfall is filled with useless "connect" spans. Real LLM/tool traces are missing.

**Root Causes**:
1. `OpenAIInstrumentor()` auto-enables DB instrumentation as a side effect
2. Traceloop's auto-init doesn't honor `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS` for direct `.instrument()` calls
3. Explicit `SQLAlchemyInstrumentor().uninstrument()` wasn't being called

**Solutions**:
1. Set `PHOENIX_PROJECT_NAME` env var before any instrumentation
2. Disable DB instrumentors explicitly: `os.environ["OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"] = "sqlalchemy,psycopg2"`
3. Call `SQLAlchemyInstrumentor().uninstrument()` after OpenAI instrumentation
4. Add a `SpanProcessor` filter that drops spans with name in `{"connect", "query", "execute"}`

---

### Blocker: Docker Compose Exits With "Can't Create Database"

**Problem**: Postgres container crashes with "CREATE DATABASE cannot run in transaction block".

**Root Cause**: Docker's Postgres init system runs `.sql` files inside a transaction. `CREATE DATABASE` is not allowed.

**Solution**: Put `CREATE DATABASE` in a `.sh` script, not `.sql`.

---

### Blocker: App Connects to `localhost`, Not Docker `postgres` Service

**Problem**: App tries to connect to `localhost:5432` even though docker-compose.yml sets `DB_HOST=postgres`.

**Root Cause**: `settings.py` only reads `DB_PASSWORD` from env. `DB_HOST` defaults to `localhost` from config.yaml.

**Solution**: In `from_yaml()`, read and apply all five DB env vars: `DB_HOST`, `DB_USER`, `DB_PORT`, `DB_NAME`, `DB_PASSWORD`.

---

### Gotcha: Phoenix Notes vs Annotations

**Problem**: User feedback comment is not visible in Phoenix.

**Root Cause**: Annotations tab only shows columns; the explanation is hidden until you click the edit icon (✏️).

**Solution**: Use the Notes API (`POST /v1/span_notes`) for comments. Notes appear in the prominent Notes panel and are immediately visible.

---

### Gotcha: "default" Project Reappears

**Problem**: Spans keep appearing in Phoenix's "default" project even after setting `PHOENIX_PROJECT_NAME`.

**Root Cause**: `PHOENIX_PROJECT_NAME` env var only affects Traceloop's auto-init. If you call `OpenAIInstrumentor().instrument()` directly without setting the env var first, Traceloop defaults to "default".

**Solution**: Set `os.environ.setdefault("PHOENIX_PROJECT_NAME", ...)` BEFORE calling any instrumentor.

---

### Gotcha: Share Dialog Not Visible After Playwright Test

**Problem**: Playwright screenshot shows share dialog off-screen or invisible.

**Root Cause**: The share dialog shifts layout in a way that pushes other elements off-screen in headless mode.

**Solution**: Navigate back to `BASE_URL` before testing sidebar or header elements (a fresh page reset).

---

## Rapid Reference

| Problem | Solution |
|---------|----------|
| `cl.user_session` not shared across callbacks | Use module-level dict keyed by session_id |
| Feedback button not triggering | User must click button + "ثبت نظر" dialog |
| Health endpoint returns Chainlit SPA | Use `BaseHTTPMiddleware`, not route decorator |
| Phoenix shows only "connect" spans | Set `PHOENIX_PROJECT_NAME`, disable DB instrumentors, call `.uninstrument()` |
| App connects to `localhost` not `postgres` | Override all DB env vars in `from_yaml()` |
| `CREATE DATABASE` fails in Docker | Use `.sh` init script, not `.sql` |
| Test file location conflict | Use `tests/ui/`, not `tests/unit/ui/` |
| Logging error with structlog kwargs | Use standard logging format (`%s`), not arbitrary `**kwargs` |
| RTL text has wrong direction | Use `dir="rtl"` attribute + logical CSS properties |
| Citation parsing breaks | Ensure consistent response format (`[N]` where N is a number) |

---

## Building Trust: Agent Principles

### Know What You Don't Know

**Lesson**: The best feature is the ability to say "I don't know" with confidence. Never produce a misleading answer when sources don't support it.

**Pattern**:
1. Carefully analyze each candidate data source
2. If none actually help solve the problem, refuse to answer
3. Explain what information would help

**User impact**: Customers use "I don't know" answers as signposts for areas that need better documentation. This creates a feedback loop that improves the knowledge base.

---

### Don't Make the Same Mistake Twice

**Lesson**: When an agent makes a mistake and receives feedback:
1. Identify the mistake as general guidance (not just this instance)
2. Add the guidance to a shared knowledge base
3. When using that knowledge later, notify the user so they know what principles are being applied

**Implication**: Build memory systems (in prompts, config, or databases) that capture feedback and apply it consistently.

---

### Maximize Visibility Into Work Being Done

**Lesson**: Build trust by showing users:
- What tools the agent is using (Phoenix traces, step visualization)
- What data the agent is reading (display document titles, sources)
- Why the agent made decisions (system prompt guidance, tool parameters)
- How much work was invested (token counts, turn counts)

This transparency makes errors more forgivable because users understand the agent's reasoning.

---

### Reflection & Error Recovery Are Part of the Process

**Lesson**: Failing is expected. What matters is:
1. Reflecting on failures (analyzing what went wrong)
2. Recovering gracefully (asking for help, trying new approaches)
3. Learning from failures (updating prompts, adjusting thresholds)

**Pattern**: Include reflection steps in agent workflows:
- After tool failures, ask: "Why did this fail? What can I try instead?"
- After errors, log: "I attempted X. It failed because Y. Next I'll try Z."
- Regular checkpoints: Summarize progress before proceeding to new tasks

---

### Ask Questions Before Acting

**Lesson**: Failing fast with questions is more reliable than confidently doing the wrong thing.

**Pattern**:
1. Before processing, verify you understand the request
2. Check assumptions with the user
3. Ask for clarification on ambiguous queries
4. Users forgive good questions, not mistakes

**Implication**: An agent that asks "Did you mean X or Y?" is better than one that guesses and fails.

