# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Law Agent** is an AI-powered legal assistant for Iranian law built with PydanticAI and PostgreSQL. It provides ChatGPT-style conversational interactions to answer questions about Iranian legal documents using a database of 47K+ documents (1.3GB).

**Core Capability**: The agent performs agentic multi-hop search across legal documents, synthesizes answers from multiple sources, and provides inline citations - all in Persian.

## Project Status

**Current Phase**: Phase 2 (Foundation) - Ready to Start

**Completed**:
- ✅ Phase 0: Onboarding & Setup (environment documentation complete)
- ✅ Phase 1: Database Migration (47K+ documents migrated from HTML to clean text)

**Next Steps**:
- Phase 2: Foundation (project structure, config system, logging, database connection)
- Phase 3: Core Search Tools (search_documents, get_document, get_related_documents)
- Phase 4: Agent Core (PydanticAI agent with conversation management)
- Phase 5-8: UI, Observability, Testing, Deployment

See `docs/development/tasks.md` for complete task breakdown.

### What to Work On Next (Phase 2)

**Ready to Start**: Phase 2 tasks in sequential order:

1. **Task 2.1**: Initialize project structure (create `src/law_agent/` directories)
2. **Task 2.2**: Set up pyproject.toml with dependencies (already done - verify it's correct)
3. **Task 2.3**: Build configuration system (config.yaml + Pydantic Settings)
4. **Task 2.4**: Implement structured logging (structlog setup)
5. **Task 2.5**: Create database connection layer (SQLAlchemy)
6. **Task 2.6**: Define ORM models (Document, Relation models)
7. **Task 2.7**: Write foundation tests
8. **Task 2.8**: Commit Phase 2

**Before Starting**:
- Read `docs/development/workflow.md` (complete workflow guide)
- Pick a task from above
- Create `docs/features/{task-name}/plan.md` (design before coding!)
- Follow the workflow exactly - it's designed for productivity

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
- Secrets (DB_PASSWORD, ANTHROPIC_API_KEY, LLM_AUTH_TOKEN) only in environment variables or .env

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
git commit -m "feat(scope): description of changes"

# Push to remote
git push origin <branch-name>
```

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

- RTL (right-to-left) support for Persian
- Show agent thinking/tool calls to keep user engaged
- Chat history section to return to old conversations
- Thumbs up/down for responses (written to observability)
- Show 3-5 random example questions at start
- Must visualize all actions and model reasoning

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
3. **`docs/development/workflow.md`** - Complete developer workflow guide (Plan, Build, Document, Learn)
4. **`docs/development/tasks.md`** - Hierarchical task breakdown for all 9 phases (~70 tasks)

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

# 2. Write plan.md (design before coding!)
# - What you're building
# - Why it matters
# - Key design decisions with alternatives considered
# - Success criteria checklist
# - Dependencies and blockers
# - Open questions

# 3. Create progress.md (update continuously!)
# - Session log with time tracking
# - What you accomplished
# - Blockers encountered and how you solved them
# - Decisions made with rationale
# - Lessons learned

# 4. Start feature branch
git checkout -b feature/my-feature-name

# 5. Build incrementally with tests
# - Write test first (TDD)
# - Implement feature
# - Update progress.md continuously

# 6. Before committing, run all checks
make all

# 7. Commit with plan.md and progress.md
git add src/
git add tests/
git add docs/features/my-feature-name/  # Don't forget!
git commit -m "feat(scope): brief description

Detailed description of changes and why.

See docs/features/my-feature-name/ for design and learnings."
```

**Key Principles**:
- Always write plan.md BEFORE writing code
- Update progress.md continuously (not at the end!)
- Commit plan.md and progress.md with code
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
