# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Law Agent** is an AI-powered legal assistant for Iranian law built with PydanticAI and PostgreSQL. It provides ChatGPT-style conversational interactions to answer questions about Iranian legal documents using a database of 47K+ documents (1.3GB).

**Core Capability**: The agent performs agentic multi-hop search across legal documents, synthesizes answers from multiple sources, and provides inline citations - all in Persian.

## Technology Stack

- **Language**: Python 3.9+
- **Agent Framework**: PydanticAI (lightweight agentic framework with type safety)
- **LLM**: Claude Sonnet 4.5 (claude-sonnet-4.5)
- **Database**: PostgreSQL with full-text search (no embeddings)
- **ORM**: SQLAlchemy
- **Package Manager**: uv (fast Python package installer)
- **UI**: Chainlit (RTL-enabled chat interface)
- **Logging**: structlog (structured logging)
- **Configuration**: Pydantic Settings (type-safe config from config.yaml + env vars)
- **Retry Logic**: tenacity
- **Text Processing**: Hazm (Persian text normalization)
- **Observability**: Arize Phoenix (self-hosted, OpenTelemetry-based)
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

All configuration is centralized in `config.yaml` (NOT YET CREATED):
- Model config: primary model, temperature, max_tokens
- Database config: host, port (credentials via env vars)
- Search config: max_results, graph_traversal_depth
- Conversation config: max_turns (50)
- UI config: show_thinking, show_tool_calls, enable_feedback, example_questions
- Document each field with comments
- Use environment variables for secrets (DB_PASSWORD, ANTHROPIC_API_KEY)

## Development Commands

### Database Operations
```bash
# Connect to database
psql -d law_agent

# Analyze documents table (after migration)
ANALYZE documents;

# Test full-text search
SELECT * FROM documents
WHERE search_vector @@ to_tsquery('persian_custom', 'بیمه')
LIMIT 10;
```

### Python Package Management
```bash
# Install dependencies (using uv)
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

# Format code
black . --line-length=100

# Lint code
ruff check . --fix
```

### Testing
```bash
# Run tests
pytest

# Run tests with async support
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

## Important Files

- `design.md`: Complete functional requirements and technical decisions
- `search.md`: Agent search architecture and instructions (used as system prompt)
- `pg_db_doc.md`: Database schema documentation and relationship structure
- `best_practices/agent.md`: Agent engineering principles and workflows
- `best_practices/eval.md`: Evaluation methodology and best practices
- `migration/migrate.py`: Database migration script (HTML → clean text)
- `migration/README.md`: Migration documentation and validation steps
- `pyproject.toml`: Project dependencies and metadata

## Architecture Principles

1. **Agent-driven search**: No fixed algorithms, agent decides strategy based on results
2. **Simple tools, smart agent**: Three minimal tools, complex reasoning in agent
3. **Progressive disclosure**: Load context on-demand, don't front-load
4. **Eval-driven development**: Build evals from error analysis, iterate continuously
5. **Configuration as code**: Everything in config.yaml, nothing hardcoded
6. **Observability first**: Log everything, analyze traces, build feedback loops
7. **Humble transparency**: Say "I don't know" when uncertain, explain failures
8. **Persian-first**: All user-facing content in Persian, internal can use English

## Common Patterns

### Adding a New Search Feature
1. Update tool signature in search tools
2. Update agent system prompt in search.md
3. Add configuration to config.yaml
4. Write eval cases for new behavior
5. Test with traces in Phoenix

### Debugging Agent Behavior
1. Check Phoenix traces for full conversation
2. Review tool call sequence and results
3. Look for prompt misalignment in search.md
4. Verify database query results manually
5. Check for configuration issues in config.yaml

### Improving Answer Quality
1. Error analysis on failed conversations
2. Identify patterns in failures
3. Update system prompt with specific guidance
4. Create eval cases from failures
5. Measure improvement with LLM-as-judge
