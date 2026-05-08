# Developer Workflow

This is the only document a new developer needs to read before starting work. It covers everything: orientation, feature development, testing, committing, and documentation.

---

## 1. Orientation (First Day)

### Read these first

| Document | What you learn |
|---|---|
| `docs/architecture/design.md` | Full system design, product requirements, document types |
| `docs/architecture/search.md` | How the agent searches — this file IS the agent's system prompt |
| `docs/architecture/database.md` | PostgreSQL schema: `documents`, `relations`, FTS config |
| `docs/development/tasks.md` | What's built, what's pending, key implementation facts |

Do not skip these. They explain *why* the system is designed the way it is.

### Understand the codebase

```bash
# What changed recently (always start here)
git log --oneline -20

# How the app starts
cat src/law_agent/ui/app.py

# Where configuration lives
cat config.yaml

# Run the tests to verify your environment
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q
```

### Start the server (development)

```python
# python3 start_server.py — loads .env without bash variable expansion issues
import os, subprocess
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, _, v = line.strip().partition('=')
            os.environ[k] = v.strip('"')
subprocess.Popen(['.venv/bin/chainlit', 'run', 'src/law_agent/ui/app.py', '--port', '7860', '--headless'])
```

Required `.env` variables: `CHAINLIT_AUTH_SECRET`, `LLM_BASE_URL`, `LLM_AUTH_TOKEN`, `DB_PASSWORD`

---

## 2. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Agent | PydanticAI | Tool registration, `agent.iter()` for streaming |
| LLM | Claude Sonnet (via LiteLLM proxy) | `LLM_BASE_URL` + `LLM_AUTH_TOKEN` in `.env` |
| Database | PostgreSQL 14+ | FTS with `persian_custom` config, DAG for citations |
| ORM | SQLAlchemy 2.0 async | `src/law_agent/database/` |
| UI | Chainlit 2.11 | RTL, sidebar, steps, actions, feedback |
| Config | Pydantic Settings + YAML | `config.yaml` for defaults, `.env` for secrets |
| Logging | structlog | JSON in prod, console in dev |
| Observability | Arize Phoenix (self-hosted) | `http://localhost:6006` |
| Testing | pytest + pytest-asyncio | `asyncio_mode = auto` |
| Quality | Black, Ruff, mypy | via `make` targets |
| Deployment | Docker Compose | Dockerfile + docker-compose.yml |

---

## 3. Project Structure

```
law/
├── src/law_agent/
│   ├── agent/          # LawAgent, ConversationManager, show_thinking()
│   ├── tools/          # search_documents, get_document, get_related_documents
│   ├── database/       # SQLAlchemy engine, session, ORM models
│   ├── data/           # LawAgentDataLayer (Chainlit history persistence)
│   ├── ui/             # app.py (Chainlit handlers), citations.py, steps.py
│   ├── observability/  # Phoenix tracing, feedback client
│   ├── config/         # Settings (Pydantic), config.yaml
│   └── prompts/        # search.md (system prompt), starters.yaml
├── tests/
│   ├── unit/           # Fast, no DB required
│   ├── ui/             # Chainlit UI behavior tests
│   ├── integration/    # Require running PostgreSQL
│   └── load/           # Locust load tests
├── docs/
│   ├── architecture/   # design.md, search.md, database.md
│   ├── development/    # workflow.md (this file), tasks.md
│   ├── best-practices/ # agent-engineering.md, evaluation.md
│   └── features/       # One folder per feature: plan.md + progress.md
├── public/             # patch.css, patch.js, SVG icons
├── config.yaml         # Application configuration
├── .chainlit/          # config.toml, translations/fa-IR.json
├── Makefile            # format, lint, typecheck, test, all
└── pyproject.toml      # Dependencies + tool config
```

---

## 4. Building a Feature

Every feature follows this exact order. No exceptions.

### Step 1 — Session startup ritual (run this every time, without exception)

Before writing a single line of code, establish exactly where you are:

```bash
git log --oneline -10              # What changed recently — always start here
cat CLAUDE.md                      # Current status and the next task
make test                          # Confirm you start from green (all tests passing)
```

Then, if you're continuing work on an existing feature:

```bash
cat docs/features/my-feature/progress.md   # What was done last session and what's next
cat docs/features/my-feature/plan.md       # Original design decisions to stay aligned
```

**Do not start coding until `make test` passes.** If tests are already failing when you sit down, fix that first — you can't know what your changes broke otherwise.

This ritual takes 2 minutes. Skipping it costs hours.

### Step 2 — Create feature documentation directory

```bash
mkdir -p docs/features/my-feature-name
```

### Step 3 — Write `plan.md` BEFORE writing any code

**This is mandatory.** Planning catches design problems before they become code problems.

> **For large or architecturally unclear features**, have Claude interview you before writing plan.md. This surfaces edge cases and tradeoffs you haven't considered yet:
> ```
> I want to build [brief description]. Interview me using the AskUserQuestion tool.
> Ask about edge cases, design decisions, implementation tradeoffs, and anything I
> might not have considered. Then write plan.md based on what we discussed.
> ```
> Start a fresh session to implement once plan.md is written — clean context focused entirely on the work.

```markdown
# Feature Name — Plan

## What I'm Building
[2-3 sentences describing the feature]

## Why It Matters
[How this fits the product and user experience]

## Key Design Decisions

### Decision: [Name]
**Chose**: [What you decided]
**Why**: [Reasoning]
**Alternatives**: [What you rejected and why]

## Verification
How will you prove this works — not just that tests pass, but that the feature is real?
- **Command**: [exact command to run, e.g. `make test` or `pytest tests/ui/test_X.py -v`]
- **Visual check**: [for UI features: what to look at, what URL, what to screenshot]
- **End-to-end**: [user action → expected result, e.g. "click retry → error disappears → message resent"]

## Success Criteria
- [ ] [Specific, testable criterion]
- [ ] Verification steps above all pass

## Open Questions
- [ ] [Things you're unsure about before starting]
```

### Step 4 — Create `progress.md` and update it continuously

```markdown
# Feature Name — Progress

## Session 1: YYYY-MM-DD

**Goal**: [What you plan to accomplish]

**Time log**:
- HH:MM [action]
- HH:MM [blocker encountered]
- HH:MM [solution found]

**Blockers & Solutions**:
### [Blocker title]
**Problem**: [What went wrong]
**Solution**: [How you fixed it]
**Root cause**: [Why it happened]

**Decisions made**:
- [Decision and why]

**Next session**:
- [ ] [What to tackle next]
```

Update progress.md as you work — not after. Decisions and blockers captured in the moment are far more useful than summaries written later.

### Step 5 — Write code

- **Write tests alongside code**, not after
- Keep functions small and focused
- Use `structlog` for all significant operations: `logger.info("event", key=value, ...)`
- No comments unless the WHY is non-obvious

### Step 5b — For UI/UX features: verify visually BEFORE writing tests

If the feature is anything visible — a new UI element, a layout change, a button, a step in the chat, a sidebar update — you **must** verify it in the browser before writing coded tests. Tests verify behavior; screenshots verify reality.

**Mandatory steps for any visible feature:**

1. Start the server (`python3 start_server.py`)
2. Use the `/chainlit-ui-debugger` skill or Playwright manually to take screenshots
3. Look at the screenshots and confirm:
   - The element appears where expected
   - Persian text is RTL and readable
   - The feature works end-to-end (e.g. click retry → error disappears → message resent)
   - No visual regressions in surrounding UI
4. Save the screenshots in `docs/features/{name}/screenshots/`
5. **Only then** write the coded unit/integration tests

```bash
# Use the built-in skill for automated UI screenshots
/chainlit-ui-debugger all              # full suite
/chainlit-ui-debugger retry-button    # specific feature
```

Or write a targeted Playwright script (see `docs/features/retry-messages/` for a real example).

**Why this order matters**: Coded tests mock Chainlit internals and can pass even when the UI is broken or invisible. A screenshot catches what tests cannot — a button that exists in code but renders off-screen, a step that fires but collapses immediately, a Persian string that appears as mojibake. Verify the real thing first, then lock in the behavior with tests.

If the feature is purely backend with no visual output (e.g. a caching layer, a database query), skip this step.

### Step 6 — Test

```bash
# Run everything before committing
make all

# Just tests
.venv/bin/python -m pytest tests/ --ignore=tests/integration -q

# Specific test file
.venv/bin/python -m pytest tests/ui/test_retry_action.py -v

# With coverage
.venv/bin/python -m pytest --cov=src/law_agent --cov-report=html tests/
```

### Step 7 — Update docs, then commit

**Before running `git commit`, update these documents:**

| Document | What to update |
|---|---|
| `CLAUDE.md` | Mark the feature complete in the status section; update "What's next" |
| `docs/development/tasks.md` | Move the task from 📋 Pending to ✅ Completed; add implementation facts |
| `docs/features/{name}/progress.md` | Write the final summary: total time, key learnings, "for future developers" advice |
| `docs/features/{name}/plan.md` | Check all success criteria; note any deviations from the original plan |

**CLAUDE.md is the most important one.** It is what the next developer (or next Claude session) reads first. If it says a task is pending when it's done, or points to the wrong next task, the next developer starts from a false map. Always update it.

**CLAUDE.md pruning rule**: every time you update CLAUDE.md, also prune it. For each line ask: *"Would removing this cause Claude to make mistakes?"* If not, cut it or move it to `docs/features/`. A bloated CLAUDE.md is worse than a short one — Claude ignores instructions buried in noise. Target: 2–3 pages maximum.

Then commit — including all doc changes in the same commit as the code:

```bash
git add src/ tests/ docs/features/my-feature-name/ docs/development/tasks.md CLAUDE.md
git commit -m "feat(scope): short description

Longer explanation of what and why.

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>"
```

### Step 8 — Merge to main

```bash
git checkout main
git merge feature/my-feature-name
git branch -d feature/my-feature-name
```

All work is local — there is no remote. Merge to main when the feature is complete and all tests pass.

---

## 5. Testing

### Test categories

| Directory | What | When |
|---|---|---|
| `tests/unit/` | Pure Python, no DB | Fast, run always |
| `tests/ui/` | Chainlit handler behavior (mocked) | Run always |
| `tests/integration/` | Real PostgreSQL required | Run when touching DB or search |
| `tests/load/` | Locust load tests | Run before performance changes |

### Writing tests

Follow the patterns in `tests/unit/agent/test_thinking_steps.py` and `tests/ui/test_retry_action.py`. Key patterns:

```python
# Async test with mocked Chainlit
@pytest.mark.asyncio
async def test_something() -> None:
    step_mock = MagicMock()
    step_mock.__aenter__ = AsyncMock(return_value=step_mock)
    step_mock.__aexit__ = AsyncMock(return_value=False)

    with patch("law_agent.ui.app.cl.Step", return_value=step_mock), \
         patch("law_agent.ui.app.cl.user_session") as mock_session:
        mock_session.get = MagicMock(return_value=None)
        mock_session.set = MagicMock()
        # ... test body
```

- **Don't mock the database** in unit tests — use fixtures or test data
- **Integration tests** go in `tests/integration/` and are skipped without `@pytest.mark.skipif`
- Keep test names descriptive: `test_retry_action_payload_contains_original_message`

---

## 6. Code Quality

```bash
make format      # Black auto-formatting
make lint        # Ruff linting
make typecheck   # mypy type checking
make test        # pytest
make all         # All four in sequence
```

All checks must pass before committing. The CI pipeline (`.github/workflows/ci.yml`) runs the same checks.

**Style rules**:
- Type hints on all function signatures
- No comments explaining what code does — only explain non-obvious WHY
- No dead code, no commented-out code
- structlog with structured data: `logger.info("search_executed", query=q, result_count=n)`

---

## 7. Documentation Rules

### When to write what

| Situation | Write |
|---|---|
| Starting a feature | `docs/features/{name}/plan.md` |
| While developing | `docs/features/{name}/progress.md` (continuously) |
| Completing a feature | Final summary in `progress.md`, update `CLAUDE.md` status |
| Architecture changes | Update `docs/architecture/` |
| New dev patterns discovered | Update this file (`workflow.md`) |

### plan.md rules

- Write it before touching code
- Include alternatives considered and why you rejected them
- Be specific: "use `cl.user_session`" not "use session storage"
- Include open questions — answer them as you work

### progress.md rules

- Update in real time, not retrospectively
- Document blockers with: problem → what I tried → solution → root cause
- Capture the "gotcha" moments — these save future developers hours
- End each session with what to tackle next

### What NOT to document

- How to use standard libraries — that's what library docs are for
- Business-as-usual code that follows obvious patterns
- Anything already in `git log` (commit messages are documentation too)

---

## 8. Available Skills (Claude Code)

Run these with `/skill-name` in Claude Code:

| Skill | What it does |
|---|---|
| `/chainlit-ui-debugger` | Playwright-based automated UI testing. Takes screenshots, checks RTL text, sidebar, buttons, responsiveness. Usage: `/chainlit-ui-debugger all` or `/chainlit-ui-debugger retry-button` |
| `/simplify` | Reviews changed code for quality and efficiency |
| `/security-review` | Security review of pending branch changes |
| `/review` | Pull request review |
| `/fewer-permission-prompts` | Scans transcripts and adds allowlist to reduce prompts |

---

## 9. Critical Architecture Facts

These are hard-won lessons. Not knowing them costs hours.

### Chainlit

| Fact | Detail |
|---|---|
| Table columns are **camelCase** | `createdAt` (TEXT), `userId`, `threadId` — not snake_case |
| `createdAt` is **TEXT**, not TIMESTAMP | ISO string format |
| `@cl.step` on sync functions **doesn't render** | Always use `async with cl.Step():` |
| `cl.Message().send()` must come **after** `agent.run()` | Otherwise steps appear after the answer |
| `unsafe_allow_html = false` | Use markdown `[1](url)` not `<a href>` for citations |
| `steps` table needs `"defaultOpen"` BOOLEAN column | Chainlit always sends it; add manually if missing |
| Auth requires `CHAINLIT_AUTH_SECRET` in `.env` | JWT secret for `@cl.password_auth_callback` |
| Sidebar requires authentication | Without `@cl.password_auth_callback`, no per-user threads |
| `cl.user_session` scope in action callbacks | Works, but use module-level dict for cross-coroutine state |

### Phoenix / Observability

| Fact | Detail |
|---|---|
| Feedback API endpoint | `POST /v1/span_annotations` with `span_id` (not trace_id) |
| Start Phoenix **before** Chainlit | OTel exporter fails silently if Phoenix isn't up first |
| Span ID must be captured explicitly | Create `_session_span_ids: dict[str, str]` at module level |

### PydanticAI

| Fact | Detail |
|---|---|
| Our LiteLLM model emits only `ToolCallPart` | No `TextPart` or `ThinkingPart` alongside tools |
| Use `agent.iter()` for step visibility | Required to hook into `CallToolsNode` for thinking extraction |

### Database

| Fact | Detail |
|---|---|
| Full-text search uses `persian_custom` config | Not the default `english` or `simple` |
| Relations table is a DAG | `src_doc_id` → `dst_doc_id`, follow via `get_related_documents()` |
| Never override `execute_sql()` in data layer | Parent class handles it; overriding causes SQLAlchemy session bugs |

---

## 10. Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

<longer description explaining what and why>

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Examples**:
```
feat(ui): add retry button for failed messages
fix(data): handle missing defaultOpen column in steps table
docs(workflow): add critical Chainlit architecture facts
test(ui): add 8 tests for retry action behavior
```
