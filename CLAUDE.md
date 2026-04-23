# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 🎯 Current Focus: v0.0.2 - Enhanced UI/UX

**Status**: Planning Complete ✅ - Ready for implementation

**Next Task**: Start Phase 11A with Task 11.1 (Centered welcome screen)

**Implementation Guide**: `docs/development/v0.0.2-tasks.md` (comprehensive, with exact code references)

**Reference Project**: `/Users/divar/Documents/codes/data-assistant` (SQL Assistant)

**What's Missing**: The UI features marked complete in old Phase 5 are NOT actually working yet (thinking steps, tool visualization, conversation history, feedback). Phase 11 will implement all of these properly by adapting patterns from data-assistant.

---

## Project Overview

**Law Agent** is an AI-powered legal assistant for Iranian law built with PydanticAI and PostgreSQL. It provides ChatGPT-style conversational interactions to answer questions about Iranian legal documents using a database of 47K+ documents (1.3GB).

**Core Capability**: The agent performs agentic multi-hop search across legal documents, synthesizes answers from multiple sources, and provides inline citations - all in Persian.

## Project Status

**Current Version**: v0.0.1
**Current Phase**: Phase 11 (Enhanced UI/UX) - v0.0.2 - In Planning 📋

**Completed**:
- ✅ Phase 0: Onboarding & Setup (environment documentation complete)
- ✅ Phase 1: Database Migration (47K+ documents migrated from HTML to clean text)
- ✅ Phase 2: Foundation (configuration, logging, database connection, ORM models)
  - ✅ Task 2.1-2.8: All foundation tasks complete (114 total tests)
- ✅ Phase 3: Core Search Tools (PostgreSQL FTS, Persian processing, search tools, 114 tests)
  - ✅ Task 3.1-3.8: All search tool tasks complete (47 search-specific tests)
- ✅ Phase 4: Agent Core - All tasks complete (191 total tests, +77 new agent tests)
  - ✅ Task 4.1: PydanticAI framework studied
  - ✅ Task 4.2: Law Agent created with search tools (async tool handlers, JSON returns)
  - ✅ Task 4.3: Conversation management (state tracking, turn limits, persona)
  - ✅ Task 4.4: Citation system (extraction, formatting, deduplication)
  - ✅ Task 4.5: Persona detection (in system prompt, implicit per message)
  - ✅ Task 4.6: Follow-up question generation (extraction, formatting)
  - ✅ Task 4.7: Error handling (7 custom exceptions, Persian messages)
  - ✅ Task 4.8: End-to-end testing (77 comprehensive unit tests, 100% pass rate)
  - ✅ Task 4.9: Agent Core committed
- ⚠️ Phase 5: UI (Chainlit Interface) - **Partially Complete** (+44 UI tests)
  - ✅ Task 5.1: Chainlit framework setup and basic chat interface
  - ✅ Task 5.2: RTL (right-to-left) support for Persian text (CSS-based)
  - ✅ Task 5.3: Citation links to iran.ir documents (regex parsing + HTML formatting)
  - ✅ Task 5.4: Example questions display at chat start (config.yaml driven)
  - ❌ Task 5.5: Feedback collection (👍/👎 buttons) - **Handler exists but commented out**
  - ❌ Task 5.6: Agent thinking and tool calls visualization - **Not working yet**
  - ❌ Task 5.7: Conversation history sidebar - **Not implemented**
  - ✅ Task 5.8: End-to-end testing and polish (44 comprehensive UI tests, 100% pass rate)
- ✅ Phase 6: Observability (Arize Phoenix + Eval-Driven Development) - Complete ✅
  - ✅ Task 6.1: Study Arize Phoenix and OpenTelemetry concepts
  - ✅ Task 6.2: Deploy Phoenix locally with Docker Compose (docker-compose.yml, Dockerfile)
  - ✅ Task 6.3: Instrument Law Agent with OpenTelemetry tracing (tracer.py, instrumentation.py)
  - ✅ Task 6.4: Add token usage tracking and cost estimation (in tracer.py)
  - ✅ Task 6.5: Integrate Chainlit feedback with Phoenix (feedback.py, UI handler)
  - ✅ Task 6.6: Create Phoenix dashboard for metrics (traces, analytics configuration)
  - ✅ Task 6.7: Add error tracking and monitoring (error spans in tracer)
  - ✅ Task 6.8: Create evaluation framework - LLM-as-Judge (evaluation.py, golden set)
- ✅ Phase 7: Testing & CI/CD - Complete ✅
  - ✅ Task 7.1: Expand test coverage to 60%+ (fixed UI imports, Ruff violations, +15 new tests)
  - ✅ Task 7.3: Configure Black, Ruff, mypy with Makefile (8 targets, tested)
  - ✅ Task 7.4: Set up pre-commit hooks (.pre-commit-config.yaml, ready to install)
  - ✅ Task 7.5: Build GitHub Actions CI pipeline (.github/workflows/ci.yml, 3 jobs)
  - ✅ Task 7.6: Create test data management scripts (SQL + Python loader, idempotent)
- ✅ Phase 9: Performance & Polish - Complete ✅
  - ✅ Task 9.1: Profiling and baseline metrics (cProfile integration, metrics collection)
  - ✅ Task 9.2: Database query optimization (6 new indexes, 60-70% latency reduction)
  - ✅ Task 9.3: Search tool performance improvements (LRU caching, 35-45% hit rate)
  - ✅ Task 9.4: Agent response caching (5-day TTL, cost tracking)
  - ✅ Task 9.5: Load testing framework (Locust-based, 10-200 concurrent users)
  - ✅ Task 9.6: UI/UX polish and accessibility (WCAG AA compliance, RTL support)
  - ✅ Task 9.7: Documentation and performance guide (comprehensive PERFORMANCE.md)
  - ✅ Task 9.8: Performance regression testing (baseline tracking, automated alerts)
- ✅ Phase 8: Deployment & Production - Complete ✅
  - ✅ Task 8.1: Multi-stage Dockerfile (builder+runtime, non-root user, <500MB image)
  - ✅ Task 8.2: Docker Compose setup (PostgreSQL, Phoenix, App with health checks)
  - ✅ Task 8.3: Environment configuration (.env.example, secrets management)
  - ✅ Task 8.4: Health check endpoints (/health, /ready for orchestration)
  - ✅ Task 8.5: Production logging (JSON format, log rotation, configurable)
  - ✅ Task 8.6: Deployment documentation (900+ line comprehensive guide)
  - ✅ Task 8.7: Testing & validation (formatting, linting, type checks)
  - ✅ Task 8.8: Final commit (all deployment files, production-ready)

**In Progress**:
- 📋 Phase 11: Enhanced UI/UX (v0.0.2) - **Planning Complete, Ready to Implement**
  - 📋 Task 11.1: Centered welcome screen with starter questions
  - 📋 Task 11.2: Conversation history sidebar (grouped by date)
  - 📋 Task 11.3: Thinking steps visualization
  - 📋 Task 11.4: Tool calls visualization
  - 📋 Task 11.5: Feedback collection (thumbs up/down)
  - 📋 Task 11.6: Share conversations
  - 📋 Task 11.7: Export to Markdown
  - 📋 Task 11.8: Retry failed messages
  - 📋 Task 11.9: Browser notifications
  - 📋 Task 11.10: Copy to clipboard
  - 📋 Task 11.11: RTL and Persian UI polish
  - 📋 Task 11.12: Response streaming

**Next Steps After v0.0.2**:
- Phase 10: Scalability & Infrastructure (Kubernetes, Redis, multi-region)

**Documentation**:
- See `docs/development/tasks.md` for complete task breakdown
- See `docs/development/v0.0.2-tasks.md` for Phase 11 detailed implementation guide
- See `docs/features/phase-8-deployment/` for deployment guide and design decisions
- See `docs/features/phase-9-performance-polish/` for performance optimization details

### What to Work On Next (Phase 11 - v0.0.2)

**Ready to Start**: Phase 11 - Enhanced UI/UX (v0.0.2) ⭐

**Status**: Planning Complete ✅ - Ready for implementation

Phase 11 completes the missing UI features from Phase 5 by implementing a polished user experience matching the data-assistant SQL Assistant profile. This transforms the law agent from functional to delightful.

**High-Priority Features** (Phase 11A - Week 1-2):
1. ⭐ Centered welcome screen with starter questions (like ChatGPT)
2. ⭐ Thinking steps visualization (show AI reasoning)
3. ⭐ Tool calls visualization (show search operations)
4. ⭐ Conversation history sidebar (grouped by date)
5. ⭐ Response streaming (token-by-token)

**User Engagement** (Phase 11B - Week 3):
6. Feedback collection (thumbs up/down) - re-enable commented handler
7. Retry failed messages action button
8. RTL and Persian UI polish

**Sharing & Export** (Phase 11C - Week 4):
9. Share conversations (read-only links)
10. Export to Markdown
11. Browser notifications
12. Copy to clipboard

**Reference Project**: `/Users/divar/Documents/codes/data-assistant` (SQL Assistant)

**Estimated Time**: 36-48 hours (4-6 weeks at 8-10 hours/week)

**Before Starting**:
- ✅ Read `docs/development/v0.0.2-tasks.md` - **Comprehensive implementation guide**
- ✅ Review data-assistant codebase at `/Users/divar/Documents/codes/data-assistant`
- ✅ Each task has exact file references with line numbers to copy from
- ✅ No guessing needed - just study reference implementation and adapt
- ⚠️ Follow the implementation order (Phase 11A → 11B → 11C)

**Key Files to Study in data-assistant**:
1. `src/profiles/sql_assistant_v3/profile.py` - Profile structure with starters
2. `src/profiles/sql_assistant_v3/agents/sql_assistant.py` - Thinking steps extraction
3. `src/profiles/sql_assistant_v3/tools/execute_sql.py` - Tool visualization with @cl.step
4. `src/datasource/postgres/chainlit_data_layer.py` - Conversation history backend
5. `public/patch.js` - UI customizations (share button, export, RTL)
6. `public/patch.css` - RTL styling

**After Phase 11**:
- Phase 10: Scalability & Infrastructure (Kubernetes, Redis, multi-region)

---

## Technology Stack

- **Language**: Python 3.9+
- **Agent Framework**: PydanticAI (lightweight agentic framework with type safety)
- **LLM**: Claude Sonnet 4.5 (claude-sonnet-4.5) via anthropic SDK
- **Database**: PostgreSQL 14+ with full-text search (no embeddings)
- **ORM**: SQLAlchemy 2.0+
- **Package Manager**: uv (fast Python package installer)
- **UI**: Chainlit 1.0+ (RTL-enabled chat interface)
- **Logging**: structlog (structured, machine-parseable logging)
- **Configuration**: Pydantic Settings (type-safe config from config.yaml + env vars)
- **Retry Logic**: tenacity (resilience patterns)
- **Text Processing**: Hazm (Persian text normalization)
- **Observability**: Arize Phoenix (self-hosted, OpenTelemetry-based)
- **Testing**: pytest with async support
- **Code Quality**: Black, Ruff, mypy
- **Deployment**: Docker Compose

## Database Architecture

### Schema Overview

The database contains two main tables:

**documents** table:
- `doc_id`: Unique identifier (BIGINT)
- `title`: Document title in Persian
- `doc_type`: One of: law, regulation, advisory_opinion, court_ruling, unified_precedent
- `date`: Document date (Gregorian, extracted from Persian dates)
- `summary`: 200-500 word summary (used for search)
- `full_content`: Complete cleaned text (used for answering)
- `tags`: TEXT[] array of subject classifications
- `search_vector`: tsvector (auto-generated from title + summary)

**relations** table (Directed Acyclic Graph):
- `src_doc_id`: Source document
- `dst_doc_id`: Destination document
- `relation_type`: Persian relation type (e.g., 'قوانین', 'مواد مرتبط')

### Document Hierarchy

Documents form a legal hierarchy:
- **Laws** (law): Primary legislation - foundation
- **Regulations** (regulation): Implementation rules and amendments
- **Advisory Opinions** (advisory_opinion): Legal interpretations citing laws
- **Court Rulings** (court_ruling): Case law applying laws
- **Unified Precedents** (unified_precedent): Supreme Court unified opinions

Lower-level documents (opinions, rulings) cite higher-level documents (laws) via the relations table.

### Migration

The database was migrated from HTML content to clean text using `migration/migrate.py`:
- Strips all HTML tags from original `pages.content`
- Extracts summary from `خلاصه متن` section
- Normalizes Persian characters (ك→ک, ي→ی)
- Infers document types from content patterns
- Converts Persian dates to Gregorian using jdatetime

Migration commands (if needed):
```bash
pip install psycopg2-binary beautifulsoup4 jdatetime
python migration/migrate.py
```

## Agent Search Architecture

### Philosophy: Agent-Driven, Not Algorithm-Driven

The search system provides simple, composable tools and lets Claude decide the search strategy. There is **no fixed multi-stage algorithm** - the agent reasons about the best search path.

### Three Core Tools

1. **search_documents(query, tags=None, doc_types=None, limit=20)**
   - Full-text search on document summaries using PostgreSQL FTS
   - Optional filters: tags (subject classifications), doc_types (law, advisory_opinion, etc.)
   - Returns: List of DocSummary with relevance scores

2. **get_document(doc_id)**
   - Load full content of a specific document
   - Only used when ready to read for answering
   - Returns: Complete document with all metadata

3. **get_related_documents(doc_id, relation_types=None, limit=10)**
   - Follow citations/relations from one document to related documents
   - Relation types: 'قوانین' (laws cited), 'مواد مرتبط' (related articles)
   - Use to fetch parent laws or explore the legal graph

### Agentic Search Strategy

The agent decides at each step based on results:
- **Initial search**: Use user keywords, optionally filter by doc_types
- **Evaluate results**: If score > 0.8, load and answer. If 0.5-0.8, refine search. If < 0.5, extract better keywords.
- **Multi-hop patterns**:
  - Search → Read → Search Again (with refined keywords)
  - Search → Follow Relations → Read (use hierarchy to get parent laws)
  - Search → Expand → Synthesize (read multiple perspectives)
- **Keyword discovery**: Agent reads summaries and discovers legal terminology, translates plain language to legal terms
- **Stop when confident**: Most queries need 1-3 tool calls

See `search.md` for complete search instructions (used as agent system prompt).

## Key Product Requirements

### Conversational Behavior

- **Language**: Always respond in Persian (can use English internally)
- **Clarifying questions**: Max 2-3 questions before answering, only when truly needed
- **Humble transparency**: Say "I don't know" when no relevant docs found, explain what was searched
- **Citations**: Inline numbered format `[1]`, paraphrase sources (don't quote), all citations clickable to iran.ir
- **Follow-up suggestions**: Generate 2-3 LLM-based follow-up questions after each answer
- **Multi-turn**: Support 5-10 turn conversations typically, hard limit 50 messages
- **Scope**: Only answers questions about Iranian law in the database

### Context Assembly

- **Most queries**: Only retrieve direct answer documents
- **When needed**: Fetch parent laws (ancestors) using relations DAG
- **Persona adaptation**: Infer expertise from query style (Layperson vs Business/Organization), adapt per message

### Error Handling

- **No docs found**: Explain what was searched, ask for more context
- **Contradictory laws**: Present both sources, explain nuance
- **Search rounds**: 2-3 multi-hop rounds, then give best answer or say "I don't know"

## Configuration Management

All configuration is centralized in `config.yaml` (Phase 2 task):
- Model config: primary model, temperature, max_tokens
- Database config: host, port (credentials via env vars)
- Search config: max_results, graph_traversal_depth
- Conversation config: max_turns (50)
- UI config: show_thinking, show_tool_calls, enable_feedback, example_questions
- Each field documented with comments explaining purpose
- Secrets (DB_PASSWORD, LLM_AUTH_TOKEN) only in environment variables or .env (LLM_BASE_URL optional for custom endpoints)

**Database is ready**: The PostgreSQL database has been migrated and contains:
- 47,000+ documents with clean text (HTML removed)
- Full-text search configured and populated
- Relations DAG for document citations
- Ready to connect and query

## Quick Start for Developers

### First Time Setup

```bash
# Clone repo and enter directory
cd law

# Install dependencies
uv pip install -e ".[dev]"

# Verify database connection
psql -d law_agent -c "SELECT COUNT(*) FROM documents;"

# Run existing tests to verify setup
pytest tests/
```

### Daily Development Commands

```bash
# Format code with Black
make format

# Lint with Ruff
make lint

# Type check with mypy
make typecheck

# Run tests
make test

# Run all checks (format, lint, typecheck, test)
make all

# Clean up build artifacts
make clean
```

### Before Committing

```bash
# Run all checks and ensure they pass
make all

# Review changes
git status
git diff

# Commit with descriptive message
git add <files>
git add docs/features/<feature-name>/  # Include plan.md and progress.md!
git add CLAUDE.md  # Update project status
git commit -m "feat(scope): description of changes"

# After committing: merge to main and clean up feature branch
git checkout main
git merge <feature-branch-name>
git branch -d <feature-branch-name>
```

**Note**: All work is local only. Merge to main when your feature is complete.

---

## Development Commands (Detailed)

### Database Operations
```bash
# Connect to database
psql -d law_agent

# Check document count by type
SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type;

# Test full-text search (Persian)
SELECT doc_id, title, ts_rank(search_vector, query) as rank
FROM documents,
     to_tsquery('persian_custom', 'بیمه') query
WHERE search_vector @@ query
LIMIT 10;

# Analyze documents table for query optimization
ANALYZE documents;
```

### Python Package Management
```bash
# Install dependencies (using uv)
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

# Update dependencies
uv pip install --upgrade -e ".[dev]"
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_search.py

# Run specific test
pytest tests/test_search.py::test_search_documents

# Run with coverage report
pytest --cov=src/law_agent --cov-report=html tests/

# Run only unit tests (fast)
pytest tests/unit/

# Run only integration tests (requires database)
pytest tests/integration/

# Run with async support
pytest --asyncio-mode=auto
```

## Evaluation & Observability

### Evaluation Strategy (Eval-Driven Development)

- **Golden set**: 50 QA pairs with reference answers
- **Run frequency**: Every prompt change
- **Metrics**: Binary task completion (pass/fail) - Did the agent answer the legal question?
- **Grading**: Human expert or LLM-as-judge
- **Process**: Start with error analysis → build evals from failure patterns → iterate

Key principles from `best_practices/eval.md`:
- Start early with 20-50 simple tasks from real failures
- Write tasks with clear reference solutions
- Build balanced problem sets (positive and negative cases)
- Check traces regularly, don't just trust metrics
- Monitor for eval saturation (100% = no improvement signal)
- Use LLM-as-judge with pass/fail + reasoning (not numerical scores)

### Arize Phoenix (Observability)

Self-hosted platform for:
- All conversation traces with filtering
- Token usage and cost analytics per conversation
- Thumbs up/down feedback integration
- Built-in LLM-as-Judge for evaluations
- Error analysis and management
- Native PydanticAI framework support

Deployed via Docker Compose (single container, no Redis/Clickhouse/S3).

## Agent Engineering Best Practices

From `best_practices/agent.md`:

### Multi-Context Window Workflows
- **Initializer**: Set up environment, create progress.txt log, initial git commit
- **Feature Creator**: Work on one feature at a time, commit with descriptive messages
- **Testing**: Use browser automation for end-to-end testing
- **State Management**: Code + git history = full state, allows context clearing

### Progressive Disclosure
- Load context on-demand via links in prompts
- Don't front-load everything into context
- Use files on disk for memory (USER.md, AGENT.md, TOOLS.md)

### Trust & Transparency
- Say "I don't know" confidently when uncertain
- Explain what was searched when failing
- Don't make the same mistake twice - update knowledge base from feedback

### Verification
- Verify work at each stage
- Write rule-based checks where possible
- Test after implementing features

## UI Requirements (Chainlit)

**Currently Implemented (v0.0.1)**:
- ✅ Basic RTL (right-to-left) support for Persian text
- ✅ Citation links to iran.ir documents (clickable)
- ✅ Example questions at chat start (from config.yaml)
- ✅ Basic chat interface with message history in session

**Planned for v0.0.2 (Phase 11)**:
- 📋 Enhanced RTL polish with auto-direction detection
- 📋 Centered welcome screen with starter question buttons
- 📋 Agent thinking visualization (show reasoning process)
- 📋 Tool calls visualization (show search operations)
- 📋 Conversation history sidebar (persistent across sessions, grouped by date)
- 📋 Thumbs up/down feedback (re-enable commented handler)
- 📋 Share conversations (read-only links)
- 📋 Export to Markdown
- 📋 Response streaming (token-by-token)
- 📋 Retry failed messages
- 📋 Browser notifications
- 📋 Copy to clipboard

**Reference**: See `docs/development/v0.0.2-tasks.md` for implementation details

## Deployment

Run cleanly using Docker Compose:
- PostgreSQL container
- Arize Phoenix container (observability)
- Agent application container

Very high detail and clean logging using structlog.

## Git Workflow

- Use incremental commits with descriptive messages
- Follow conventional commit style
- Commit format should include:
  - Clear description of changes
  - Why the change was made (not just what)
  - Generated with Claude Code attribution

## Key Resources

### For New Developers (Start Here!)

1. **`docs/README.md`** - Documentation hub with complete index and onboarding path
2. **`CLAUDE.md`** (this file) - Quick reference for project overview and commands
3. **`docs/development/v0.0.2-tasks.md`** - **Current work: Phase 11 implementation guide** ⭐
4. **`docs/development/workflow.md`** - Complete developer workflow guide (Plan, Build, Document, Learn)
5. **`docs/development/tasks.md`** - Hierarchical task breakdown for all phases
6. **`docs/development/future.md`** - Future plans and v0.0.2 overview

### Architecture & Design

- **`docs/architecture/design.md`** - Complete functional requirements and technical decisions
- **`docs/architecture/search.md`** - Agent search strategy and system prompt (becomes agent instructions)
- **`docs/architecture/database.md`** - Database schema documentation and DAG structure
- **`docs/architecture/migration/`** - Database migration scripts and results

### Best Practices

- **`docs/best-practices/agent-engineering.md`** - Multi-context workflows, state management, trust & transparency
- **`docs/best-practices/evaluation.md`** - Eval-driven development, golden sets, LLM-as-judge patterns

### Development Files

- **`Makefile`** - Common development commands (format, lint, typecheck, test, all, clean)
- **`pyproject.toml`** - Project dependencies, tool configurations (Black, Ruff, mypy, pytest)
- **`migrate.py`** - Database migration script (HTML → clean text) - Phase 1 completed
- **`docs/features/*/`** - Feature-specific plan.md and progress.md (living documentation)

## Architecture Principles

1. **Agent-driven search**: No fixed algorithms, agent decides strategy based on results
2. **Simple tools, smart agent**: Three minimal tools, complex reasoning in agent
3. **Progressive disclosure**: Load context on-demand, don't front-load
4. **Eval-driven development**: Build evals from error analysis, iterate continuously
5. **Configuration as code**: Everything in config.yaml, nothing hardcoded
6. **Observability first**: Log everything, analyze traces, build feedback loops
7. **Humble transparency**: Say "I don't know" when uncertain, explain failures
8. **Persian-first**: All user-facing content in Persian, internal can use English

## Common Development Workflows

### Starting a New Feature (Required for Every Task)

**IMPORTANT**: Follow the **Plan, Build, Document, Learn** approach from `docs/development/workflow.md`.

```bash
# 1. Create feature documentation directory
mkdir -p docs/features/my-feature-name
cd docs/features/my-feature-name

# 2. MANDATORY: Write plan.md BEFORE ANY CODE
# DO NOT skip this step - plan first, code second!
# - What you're building
# - Why it matters
# - Key design decisions with alternatives considered
# - Success criteria checklist
# - Dependencies and blockers
# - Open questions

# 3. Create progress.md (to update during development)
# - Session log with time tracking
# - What you accomplished
# - Blockers encountered and how you solved them
# - Decisions made with rationale
# - Lessons learned

# 4. Start feature branch
git checkout -b feature/my-feature-name

# 5. Build incrementally with tests (update progress.md DURING work!)
# - Write test first (TDD)
# - Implement feature
# - UPDATE progress.md as you go (not after!)

# 6. Before committing, run all checks
make all

# 7. MANDATORY: Update CLAUDE.md with completed task status
# - Update "Project Status" section
# - Update "What to Work On Next" section
# - Commit CLAUDE.md changes with your feature

# 8. Commit with plan.md and progress.md
git add src/
git add tests/
git add docs/features/my-feature-name/  # Don't forget!
git add CLAUDE.md  # Include updated project status!
git commit -m "feat(scope): brief description

Detailed description of changes and why.

See docs/features/my-feature-name/ for design and learnings."

# 9. Merge to main (local only - no remote)
git checkout main
git merge feature/my-feature-name
git branch -d feature/my-feature-name  # Clean up feature branch
```

**Key Principles**:
- **MANDATORY**: Write plan.md BEFORE writing any code (no exceptions)
- **MANDATORY**: Update progress.md DURING implementation (not after!)
- **MANDATORY**: Update CLAUDE.md "Project Status" section after feature completion
- Commit plan.md, progress.md, and updated CLAUDE.md with your code
- See `docs/development/workflow.md` for complete guide
- See `docs/development/tasks.md` for phase breakdown

### Adding a New Feature to the Agent

1. **Design Phase** (Task planning):
   - Read relevant sections in `docs/architecture/design.md` and `docs/architecture/search.md`
   - Create `docs/features/{feature-name}/plan.md` with design decisions
   - Identify dependencies from `docs/development/tasks.md`

2. **Implementation Phase**:
   - Follow project structure: `src/law_agent/{module}/`
   - Write tests first (unit + integration)
   - Update progress.md as you work
   - Use structlog for all significant operations

3. **Testing Phase**:
   - Run `make all` to verify code quality
   - Achieve 80%+ test coverage for new code
   - Test with real database for integration tests
   - Update progress.md with learnings

4. **Documentation Phase**:
   - Complete progress.md final summary
   - Capture key learnings and "for future developers" advice
   - Reference code locations with `file.py:line-number`

5. **Commit Phase**:
   - Include plan.md and progress.md
   - Use conventional commits format
   - Reference task number from `docs/development/tasks.md`

### Adding a New Search Feature

1. Update tool signature in `src/law_agent/tools/search.py`
2. Update agent system prompt in `docs/architecture/search.md`
3. Add configuration parameters to `config.yaml`
4. Write integration tests using real database
5. Update search tool documentation
6. Test with Phoenix traces to verify behavior

### Debugging Agent Behavior

**Using Phoenix (Observability)**:
1. Open Phoenix UI at http://localhost:6006
2. Find the conversation trace that's failing
3. Review tool call sequence and parameters
4. Check token usage and execution times
5. Inspect error spans if any

**Using Logs**:
```bash
# View application logs
docker-compose logs -f app

# Search for specific query in logs
docker-compose logs app | grep "بیمه"

# Filter by log level
docker-compose logs app | grep "ERROR"
```

**Manual Investigation**:
1. Check Phoenix traces for tool call sequence
2. Verify database query results manually with SQL
3. Review agent system prompt in `search.md` for misalignment
4. Check configuration issues in `config.yaml`
5. Look at test cases for similar scenarios

### Improving Answer Quality

1. **Analyze Failures**:
   - Review failed queries in Phoenix
   - Identify patterns (wrong tool, bad search, unclear prompt)

2. **Create Test Cases**:
   - Build eval set from failures
   - Document expected vs actual behavior
   - See `docs/best-practices/evaluation.md`

3. **Iterate**:
   - Update system prompt or tool behavior
   - Run evals to measure improvement
   - Use LLM-as-judge for quality assessment
   - Document learnings in progress.md
