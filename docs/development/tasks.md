# Law Agent - Hierarchical Task Breakdown

This document provides a complete task breakdown for building the Law Agent from scratch. Tasks are organized into sequential phases, designed for a developer new to the project.

**Important**: Before starting any feature, read the relevant sections in `design.md` and related documentation files.

---

## Phase 0: Onboarding & Setup

**Goal**: Understand the project architecture and set up development environment.

### Task 0.1: Environment Setup

**Description**: Install and configure all required development tools (PostgreSQL, Python, uv, git).

**Definition of Done**:
- [ ] PostgreSQL 14+ installed and running
- [ ] Python 3.9+ installed
- [ ] `uv` package manager installed
- [ ] Can connect to PostgreSQL locally
- [ ] Repository cloned and accessible

**Dependencies**: None

---

### Task 0.2: Study Project Architecture

**Description**: Read and understand the core design documents. Focus on understanding the agentic search philosophy, document hierarchy, and database schema.

**Required Reading**:
- `design.md` - Complete functional and technical design
- `search.md` - Agent search strategy (this becomes the system prompt)
- `pg_db_doc.md` - Database schema and relations
- `CLAUDE.md` - Development guidelines
- `best_practices/` - Agent engineering and evaluation practices

**Definition of Done**:
- [ ] Can explain "agentic search" vs traditional algorithmic search
- [ ] Can describe the 5 document types and their hierarchical relationships
- [ ] Can name the 3 core search tools and their purposes
- [ ] Understand the DAG structure in the relations table
- [ ] Understand why Persian text normalization is critical

**Dependencies**: Task 0.1

---

### Task 0.3: Explore Database Schema

**Description**: Connect to the database and explore its structure hands-on. Write queries to understand document types, relations, and full-text search.

**Key Explorations**:
- Examine documents and relations table structures
- Count documents by type
- Find examples of citations (regulations citing laws)
- Test PostgreSQL full-text search with Persian queries
- Understand search_vector usage

**Definition of Done**:
- [ ] Successfully connected to law_agent database
- [ ] Explored both tables with SQL queries
- [ ] Tested full-text search with `to_tsquery()` and `@@` operator
- [ ] Found real examples of document citations in relations table
- [ ] Understand difference between summary and full_content fields

**Dependencies**: Task 0.2

---

## Phase 1: Database Migration

**Goal**: Migrate the existing database from HTML content to clean text format suitable for the agent.

**Context**: The database currently has documents with HTML in the content field. We need clean text with proper summaries extracted.

### Task 1.1: Study Migration Requirements

**Description**: Review the existing migration script in `migration/migrate.py` and understand the transformation needed.

**Key Understanding**:
- How HTML is stripped to clean text
- How summaries are extracted from content
- How Persian dates are converted to Gregorian
- How document types are inferred
- How Persian text is normalized

**Definition of Done**:
- [ ] Read and understand `migration/migrate.py`
- [ ] Read `migration/README.md`
- [ ] Understand each transformation step
- [ ] Can explain why each transformation is necessary

**Dependencies**: Phase 0 completed

---

### Task 1.2: Run and Validate Migration

**Description**: Execute the migration script and validate the results.

**What to Validate**:
- All HTML tags removed from content
- Summaries extracted correctly (200-500 words)
- Persian characters normalized (ك→ک, ي→ی)
- Document types correctly inferred
- Dates converted to Gregorian format
- search_vector populated for full-text search

**Definition of Done**:
- [ ] Migration script executed successfully
- [ ] No HTML tags remain in content
- [ ] All documents have valid summaries
- [ ] search_vector column populated
- [ ] Full-text search works on migrated data
- [ ] Sample queries return expected results

**Dependencies**: Task 1.1

---

## Phase 2: Foundation

**Goal**: Build core infrastructure - project structure, configuration, logging, database connection.

### Task 2.1: Initialize Project Structure

**Description**: Create Python package structure with proper organization for config, database, tools, agent, and UI modules.

**Definition of Done**:
- [ ] Directory structure created following Python best practices
- [ ] All `__init__.py` files present
- [ ] `.gitignore` configured for Python projects
- [ ] README updated with project description

**Dependencies**: Phase 1 completed

---

### Task 2.2: Set Up Dependency Management

**Description**: Create `pyproject.toml` with all dependencies and tool configurations (Black, Ruff, mypy).

**Core Dependencies**: PydanticAI, SQLAlchemy, psycopg2, Pydantic Settings, structlog, tenacity, hazm, Chainlit, PyYAML

**Dev Dependencies**: pytest, pytest-asyncio, pytest-cov, black, ruff, mypy, pre-commit

**Definition of Done**:
- [ ] `pyproject.toml` created with all dependencies
- [ ] Black, Ruff, and mypy configured
- [ ] Can install with `uv pip install -e .`
- [ ] Can install dev dependencies with `uv pip install -e ".[dev]"`

**Dependencies**: Task 2.1

---

### Task 2.3: Build Configuration System

**Description**: Implement type-safe configuration management using Pydantic Settings. Configuration should load from `config.yaml` for defaults, with secrets from environment variables.

**Configuration Sections**: Model settings, database connection, search parameters, conversation limits, UI behavior, logging

**Definition of Done**:
- [ ] `config.yaml` created with all configuration sections
- [ ] Pydantic Settings models defined for type safety
- [ ] Environment variables override YAML values
- [ ] Secrets (passwords, API keys) only in environment variables
- [ ] `.env.example` template created
- [ ] Can load and validate configuration

**Dependencies**: Task 2.2

---

### Task 2.4: Implement Structured Logging

**Description**: Configure structlog for consistent, machine-parseable logging throughout the application.

**Requirements**: JSON output for production, console output for development, include timestamps and log levels, support structured data

**Definition of Done**:
- [ ] structlog configured with appropriate processors
- [ ] Log messages include timestamp, level, and structured data
- [ ] Log level configurable from config.yaml
- [ ] Can log with structured data: `logger.info("event", key=value)`
- [ ] Console and JSON output modes both work

**Dependencies**: Task 2.3

---

### Task 2.5: Create Database Connection Layer

**Description**: Build SQLAlchemy database connection with connection pooling and session management.

**Requirements**: Connection pooling, safe session handling with context manager, connection testing function

**Definition of Done**:
- [ ] SQLAlchemy engine created with connection pooling
- [ ] Session factory configured
- [ ] Context manager for safe session handling
- [ ] Connection test function works
- [ ] Can execute test queries successfully

**Dependencies**: Task 2.4

---

### Task 2.6: Define ORM Models

**Description**: Create SQLAlchemy models for documents and relations tables that map to existing database schema.

**Important**: Map to existing tables, do not create new tables. Include relationships for navigating the DAG.

**Definition of Done**:
- [ ] Document model defined with all fields matching schema
- [ ] Relation model defined with composite primary key
- [ ] Relationships configured (outgoing_relations, incoming_relations)
- [ ] Can query documents and relations
- [ ] Can navigate relationships via ORM
- [ ] No new tables created in database

**Dependencies**: Task 2.5

---

### Task 2.7: Write Foundation Tests

**Description**: Create unit and integration tests for configuration, logging, and database layers.

**Test Coverage**: Config loading, environment variable override, database connection, model queries, relationship navigation

**Definition of Done**:
- [ ] Unit tests for configuration loading
- [ ] Integration tests for database connection
- [ ] Integration tests for ORM models
- [ ] All tests pass
- [ ] Test coverage > 80% for foundation modules

**Dependencies**: Task 2.6

---

### Task 2.8: Commit Foundation Phase

**Description**: Review, lint, test, and commit all foundation work.

**Definition of Done**:
- [ ] All linting passes (black, ruff)
- [ ] All type checking passes (mypy)
- [ ] All tests pass
- [ ] Code committed with descriptive message
- [ ] Commit follows conventional commits format

**Dependencies**: Task 2.7

---

## Phase 3: Core Search Tools

**Goal**: Implement the three core tools that enable agentic multi-hop search.

**Important**: Read `search.md` in full before starting. This phase includes learning tasks - take time to understand PostgreSQL FTS and Persian text processing.

### Task 3.1: Study PostgreSQL Full-Text Search

**Description**: Learn how PostgreSQL FTS works with Persian text. Experiment with `to_tsquery()`, `@@` operator, and `ts_rank()`.

**Key Concepts**: persian_custom text search configuration, tsquery syntax (& for AND, | for OR), relevance ranking

**Definition of Done**:
- [ ] Understand how to_tsquery() works
- [ ] Can write FTS queries with AND/OR operators
- [ ] Understand ts_rank() relevance scoring
- [ ] Tested queries on actual database
- [ ] Documented learnings

**Dependencies**: Phase 2 completed

---

### Task 3.2: Study Persian Text Processing

**Description**: Learn about Persian text normalization challenges and the hazm library.

**Key Issues**: Different character forms (ك/ک, ي/ی), zero-width characters, diacritics

**Definition of Done**:
- [ ] Understand Persian text normalization issues
- [ ] Experimented with hazm Normalizer
- [ ] Can explain why normalization is necessary for search
- [ ] Tested normalized vs unnormalized queries

**Dependencies**: Task 3.1

---

### Task 3.3: Build Search Utilities

**Description**: Create utility functions for Persian text normalization and PostgreSQL FTS query building.

**Functions Needed**: Text normalization, FTS query builder with operator support, tag normalization

**Definition of Done**:
- [ ] Persian text normalization function implemented
- [ ] FTS query builder handles AND/OR operators
- [ ] Edge cases handled (empty input, special characters)
- [ ] Unit tests written and passing
- [ ] Functions documented with examples

**Dependencies**: Task 3.2

---

### Task 3.4: Implement search_documents Tool

**Description**: Build full-text search on document summaries with filtering by doc_type and tags. Return results with relevance scores.

**Key Decisions**: Search on summaries (not full content), return DocSummary models, support filtering, rank by relevance

**Definition of Done**:
- [ ] DocSummary Pydantic model defined
- [ ] search_documents function implemented
- [ ] Filtering by doc_type works
- [ ] Filtering by tags works
- [ ] Results sorted by relevance score
- [ ] Logging captures query, filters, timing, result count
- [ ] Unit tests written
- [ ] Integration test with real database passes

**Dependencies**: Task 3.3

---

### Task 3.5: Implement get_document Tool

**Description**: Fetch complete document content by ID. Returns full_content field for answering questions.

**Definition of Done**:
- [ ] FullDocument Pydantic model defined
- [ ] get_document function implemented
- [ ] Returns None for invalid doc_id
- [ ] All fields populated correctly
- [ ] Logging captures doc_id and timing
- [ ] Tests written and passing

**Dependencies**: Task 3.4

---

### Task 3.6: Implement get_related_documents Tool

**Description**: Traverse the relations DAG to find related documents. Support both outgoing (docs this one cites) and incoming (docs that cite this one) directions.

**Definition of Done**:
- [ ] get_related_documents function implemented
- [ ] Direction parameter works (outgoing/incoming)
- [ ] Optional filtering by relation_type works
- [ ] Returns list of DocSummary
- [ ] Logging captures source, direction, result count
- [ ] Tests written and passing

**Dependencies**: Task 3.5

---

### Task 3.7: Test Multi-Hop Search Patterns

**Description**: Write integration tests demonstrating the three multi-hop patterns described in `search.md`.

**Patterns to Test**:
1. Search → Refine → Search Again
2. Search → Follow Relations → Read
3. Search → Expand → Synthesize

**Definition of Done**:
- [ ] Integration tests for all three patterns
- [ ] All tests pass with real database
- [ ] Tests demonstrate tools are sufficient for complex queries
- [ ] Patterns documented in test docstrings

**Dependencies**: Task 3.6

---

### Task 3.8: Commit Search Tools Phase

**Description**: Review, test, and commit all search tools work.

**Definition of Done**:
- [ ] All tests pass (unit and integration)
- [ ] Linting and type checking pass
- [ ] Test coverage > 80%
- [ ] Commit message describes three tools and multi-hop capability

**Dependencies**: Task 3.7

---

## Phase 4: Agent Core

**Goal**: Build the PydanticAI agent that orchestrates search, manages conversations, and generates cited answers.

**Important**: Read PydanticAI documentation and `search.md` (the agent's system prompt) before starting.
make all the prompts or anyfile or peice of in a folder called src/propmts/ and use yaml for formatting and varibales of it plus always verion it.

### Task 4.1: Study PydanticAI Framework

**Description**: Learn PydanticAI's agent patterns, tool registration, and conversation handling.

**Key Concepts**: Agent creation, tool decoration, RunContext, conversation history

**Definition of Done**:
- [ ] Read PydanticAI documentation
- [ ] Ran simple examples locally
- [ ] Understand how to register tools
- [ ] Understand conversation history management
- [ ] Understand dependency injection pattern

**Dependencies**: Phase 3 completed

---

### Task 4.2: Create Law Agent with Search Tools

**Description**: Initialize PydanticAI agent with system prompt from `search.md` and register the three search tools.

**Definition of Done**:
- [ ] Agent created with Claude Sonnet 4.5
- [ ] System prompt loaded from search.md file
- [ ] All three search tools registered
- [ ] Tools have clear descriptions for the agent
- [ ] Can execute simple query successfully
- [ ] Agent calls search tools correctly

**Dependencies**: Task 4.1

---

### Task 4.3: Build Conversation Management

**Description**: Implement conversation state tracking with message history and turn limits.

**Requirements**: Track messages per conversation, enforce max_turns limit (50), unique conversation IDs, created/updated timestamps

**Definition of Done**:
- [ ] ConversationState model defined
- [ ] ConversationManager implemented
- [ ] Can create and track multiple conversations
- [ ] Turn limit enforced (raises error at max)
- [ ] Message history accessible
- [ ] Unit tests pass

**Dependencies**: Task 4.2

---

### Task 4.4: Implement Citation System

**Description**: Extract document references from agent responses and format as inline citations with iran.ir links.

**Format**: Numbered citations [1], [2] inline, with full list at end of response

**Definition of Done**:
- [ ] Citation extraction from response text
- [ ] Citations numbered in order of appearance
- [ ] Duplicate references handled correctly
- [ ] iran.ir URLs generated
- [ ] Citations formatted as numbered list
- [ ] Unit tests pass

**Dependencies**: Task 4.3

---

### Task 4.5: Implement Persona Detection

**Description**: Detect user expertise level from query style and adapt response accordingly. tell it in the system prompt

**Personas**: Layperson, Business/Organization, Legal Professional
**Dependencies**: Task 4.4

---

### Task 4.6: Add Follow-Up Question Generation

**Description**: Generate 2-3 contextual follow-up questions after each answer of current quetion.

**Requirements**: Questions in Persian, relevant to response, match user persona, concise 

**Definition of Done**:
- [ ] Follow-up generation function implemented
- [ ] Generates 2-3 questions per response
- [ ] Questions contextually relevant
- [ ] Questions respect persona
- [ ] Unit tests pass (mock LLM)

**Dependencies**: Task 4.5

---

### Task 4.7: Implement Error Handling

**Description**: Add robust error handling for all failure modes with user-friendly Persian error messages.

**Error Types**: No documents found, search timeout, turn limit exceeded, database connection errors

**Definition of Done**:
- [ ] Custom exceptions defined
- [ ] Error handlers implemented
- [ ] User-friendly Persian messages for each error
- [ ] Errors logged with full context
- [ ] Retry logic for transient errors
- [ ] Unit tests for error scenarios pass

**Dependencies**: Task 4.6

---

### Task 4.8: End-to-End Agent Testing

**Description**: Test complete agent workflows from question to cited answer.

**Test Scenarios**: Simple query, multi-hop query, no results scenario, follow-up conversation

**Definition of Done**:
- [ ] E2E test suite created
- [ ] All test scenarios pass
- [ ] Responses in Persian
- [ ] Citations formatted correctly
- [ ] Error handling works
- [ ] Follow-up questions generated

**Dependencies**: Task 4.7

---

### Task 4.9: Commit Agent Core Phase

**Description**: Review, test, and commit all agent core work.

**Definition of Done**:
- [ ] All tests pass (unit and E2E)
- [ ] Linting and type checking pass
- [ ] Manual testing with diverse queries successful
- [ ] Commit message describes agent capabilities

**Dependencies**: Task 4.8

---

## Phase 5: UI (Chainlit Interface)

**Goal**: Build RTL-enabled chat interface with citations, feedback, and conversation history.

### Task 5.1: Study Chainlit Framework

**Description**: Learn Chainlit's chat interface, message types, RTL support, and customization.

**Definition of Done**:
- [ ] Read Chainlit documentation
- [ ] Ran simple example locally
- [ ] Understand message handling
- [ ] Understand feedback integration
- [ ] Understand UI customization

**Dependencies**: Phase 4 completed

---

### Task 5.2: Build Basic Chat Interface

**Description**: Create Chainlit app that connects to Law Agent with chat start and message handlers.

**Definition of Done**:
- [ ] Chainlit app created
- [ ] Welcome message in Persian
- [ ] Can send/receive messages
- [ ] Conversation connects to agent
- [ ] App runs without errors
- [ ] UI accessible at localhost:8000

**Dependencies**: Task 5.1

---

### Task 5.3: Add RTL Support

**Description**: Configure right-to-left text direction for Persian with custom CSS.

**Definition of Done**:
- [ ] Custom CSS created
- [ ] RTL direction applied to messages
- [ ] Persian text aligned right
- [ ] Mixed Persian/English handled correctly
- [ ] Tested in multiple browsers

**Dependencies**: Task 5.2

---

### Task 5.4: Implement Citation Links

**Description**: Render citations as clickable links to iran.ir documents.

**Definition of Done**:
- [ ] Citations parsed from agent response
- [ ] Citation numbers rendered as clickable links
- [ ] Links point to correct iran.ir URLs
- [ ] Links open in new tab
- [ ] Citations visually distinct

**Dependencies**: Task 5.3

---

### Task 5.5: Add Example Questions

**Description**: Display 3-5 random example questions at chat start as clickable buttons.

**Definition of Done**:
- [ ] Example questions list created (20+ diverse questions)
- [ ] Random selection function implemented
- [ ] Examples displayed at chat start
- [ ] Clicking example sends as query
- [ ] Randomization works

**Dependencies**: Task 5.4

---

### Task 5.6: Implement Feedback Collection

**Description**: Add thumbs up/down feedback buttons with optional comments.

**Definition of Done**:
- [ ] Feedback buttons appear on responses
- [ ] Feedback saved with conversation context
- [ ] Optional comment field works
- [ ] All feedback logged
- [ ] Can view saved feedback

**Dependencies**: Task 5.5

---

### Task 5.7: Add Tool Call Visibility

**Description**: Show agent's tool calls and thinking process to keep user engaged.

**Definition of Done**:
- [ ] Tool calls visible during execution
- [ ] Tool calls show in Persian
- [ ] Progress indication works
- [ ] Tool calls collapsible
- [ ] Configurable via config.yaml

**Dependencies**: Task 5.6

---

### Task 5.8: Add Conversation History

**Description**: Allow users to view and resume past conversations.

**Definition of Done**:
- [ ] History visible in sidebar
- [ ] Can click to resume conversation
- [ ] History persists across restarts
- [ ] Conversations sorted by date
- [ ] Can create new conversation

**Dependencies**: Task 5.7

---

### Task 5.9: Commit UI Phase

**Description**: Test all UI features and commit.

**Definition of Done**:
- [ ] All features tested manually
- [ ] Linting and type checking pass
- [ ] Screenshots captured
- [ ] Commit message describes UI features

**Dependencies**: Task 5.8

---

## Phase 6: Observability (Arize Phoenix)

**Goal**: Integrate Arize Phoenix for conversation traces, token analytics, and feedback analysis.

### Task 6.1: Study Arize Phoenix

**Description**: Learn Phoenix's self-hosted deployment, OpenTelemetry integration, and PydanticAI support.

**Definition of Done**:
- [ ] Read Phoenix documentation
- [ ] Understand OpenTelemetry tracing
- [ ] Understand Phoenix deployment options
- [ ] Know how to instrument PydanticAI

**Dependencies**: Phase 5 completed

---

### Task 6.2: Deploy Phoenix Locally

**Description**: Run Phoenix using Docker for local development.

**Definition of Done**:
- [ ] Docker Compose config created for Phoenix
- [ ] Phoenix container running
- [ ] UI accessible at localhost:6006
- [ ] Data persists across restarts

**Dependencies**: Task 6.1

---

### Task 6.3: Instrument Agent with OpenTelemetry

**Description**: Add OpenTelemetry tracing to capture all agent activity.

**Definition of Done**:
- [ ] OpenTelemetry configured
- [ ] OTLP exporter points to Phoenix
- [ ] PydanticAI auto-instrumentation enabled
- [ ] Custom spans for key operations
- [ ] Traces appear in Phoenix UI

**Dependencies**: Task 6.2

---

### Task 6.4: Add Token Usage Tracking

**Description**: Track and log token usage for cost analytics.

**Definition of Done**:
- [ ] Token counts captured per LLM call
- [ ] Input and output tokens tracked separately
- [ ] Cost estimation implemented
- [ ] Token data in OpenTelemetry spans
- [ ] Metrics visible in Phoenix

**Dependencies**: Task 6.3

---

### Task 6.5: Integrate Feedback with Phoenix

**Description**: Send user feedback to Phoenix linked to conversation traces.

**Definition of Done**:
- [ ] Feedback sent to Phoenix API
- [ ] Feedback linked to traces via trace_id
- [ ] Can filter traces by feedback in Phoenix
- [ ] Positive and negative feedback visible

**Dependencies**: Task 6.4

---

### Task 6.6: Create Phoenix Dashboard

**Description**: Set up dashboard for key metrics (conversations, tokens, cost, feedback, response time).

**Definition of Done**:
- [ ] Dashboard created in Phoenix UI
- [ ] All key metrics displayed
- [ ] Dashboard auto-refreshes
- [ ] Configuration exported
- [ ] Setup documented

**Dependencies**: Task 6.5

---

### Task 6.7: Add Error Tracking

**Description**: Send error events to Phoenix for monitoring.

**Definition of Done**:
- [ ] Error spans created for exceptions
- [ ] Errors linked to conversation traces
- [ ] Can view errors in Phoenix
- [ ] Alert configured for error rate

**Dependencies**: Task 6.6

---

### Task 6.8: Commit Observability Phase

**Description**: Test and commit observability work.

**Definition of Done**:
- [ ] Traces visible in Phoenix
- [ ] Token usage tracked accurately
- [ ] Feedback integration working
- [ ] Error tracking working
- [ ] Commit includes Phoenix config

**Dependencies**: Task 6.7

---

## Phase 7: Testing & CI/CD

**Goal**: Comprehensive testing and continuous integration pipeline.

### Task 7.1: Expand Test Coverage

**Description**: Increase unit test coverage to 80%+ for all core modules.

**Definition of Done**:
- [ ] Coverage report generated
- [ ] 80%+ line coverage achieved
- [ ] All critical paths covered
- [ ] Edge cases tested

**Dependencies**: Phase 6 completed

---

### Task 7.2: Create Integration Test Suite

**Description**: Build comprehensive integration tests for all components.

**Definition of Done**:
- [ ] Integration tests for database
- [ ] Integration tests for search
- [ ] Integration tests for agent
- [ ] All tests pass with real database
- [ ] Tests complete in < 2 minutes

**Dependencies**: Task 7.1

---

### Task 7.3: Configure Linting and Formatting

**Description**: Set up Black, Ruff, and mypy with consistent rules and Makefile commands.

**Definition of Done**:
- [ ] Tool configurations in pyproject.toml
- [ ] Makefile created with format, lint, typecheck, test targets
- [ ] All checks pass
- [ ] Workflow documented

**Dependencies**: Task 7.2

---

### Task 7.4: Create Pre-Commit Hooks

**Description**: Set up pre-commit hooks to enforce code quality.

**Definition of Done**:
- [ ] .pre-commit-config.yaml created
- [ ] Hooks installed locally
- [ ] Test commit triggers hooks
- [ ] Failed hooks prevent commits
- [ ] Setup documented

**Dependencies**: Task 7.3

---

### Task 7.5: Build CI Pipeline

**Description**: Create GitHub Actions workflow for linting, type checking, and testing on every PR.

**Definition of Done**:
- [ ] .github/workflows/ci.yml created
- [ ] Workflow has lint, typecheck, test jobs
- [ ] Runs on PR and push to main
- [ ] PostgreSQL service configured for tests
- [ ] Workflow completes in < 5 minutes
- [ ] Status badges added to README

**Dependencies**: Task 7.4

---

### Task 7.6: Add Test Data Management

**Description**: Create scripts to manage test data for local and CI environments.

**Definition of Done**:
- [ ] Sample data SQL file created (100+ docs)
- [ ] Load test data script created
- [ ] Reset test database script created
- [ ] Scripts are idempotent
- [ ] Scripts documented

**Dependencies**: Task 7.5

---

### Task 7.7: Commit Testing & CI/CD Phase

**Description**: Verify all tests and CI, then commit.

**Definition of Done**:
- [ ] All tests pass locally
- [ ] Test PR created and CI passes
- [ ] Coverage > 80%
- [ ] CI completes successfully
- [ ] Commit includes workflows and scripts

**Dependencies**: Task 7.6

---

## Phase 8: Deployment

**Goal**: Package application for production deployment with Docker Compose.

### Task 8.1: Create Application Dockerfile

**Description**: Build multi-stage Dockerfile for the Law Agent application.

**Definition of Done**:
- [ ] Dockerfile created with multi-stage build
- [ ] Uses Python slim base image
- [ ] Dependencies installed with uv
- [ ] Runs as non-root user
- [ ] Image builds successfully
- [ ] Image size < 500MB
- [ ] Container runs and serves UI

**Dependencies**: Phase 7 completed

---

### Task 8.2: Create Docker Compose Configuration

**Description**: Build complete setup with PostgreSQL, Phoenix, and application services.

**Definition of Done**:
- [ ] docker-compose.yml created with 3 services
- [ ] Service dependencies configured
- [ ] Volumes for data persistence
- [ ] Network for service communication
- [ ] All services start with `docker-compose up`

**Dependencies**: Task 8.1

---

### Task 8.3: Add Environment Configuration

**Description**: Manage environment variables and secrets for deployment.

**Definition of Done**:
- [ ] .env.example created with all variables
- [ ] All variables documented
- [ ] docker-compose uses .env file
- [ ] .env in .gitignore
- [ ] Configuration tested

**Dependencies**: Task 8.2

---

### Task 8.4: Add Health Checks

**Description**: Implement health check endpoints for all services.

**Definition of Done**:
- [ ] /health endpoint added to application
- [ ] Health check verifies database and Phoenix
- [ ] Health checks in docker-compose.yml
- [ ] Unhealthy services restart automatically
- [ ] Health checks tested

**Dependencies**: Task 8.3

---

### Task 8.5: Configure Production Logging

**Description**: Set up structured logging for production with log rotation.

**Definition of Done**:
- [ ] Production logs output as JSON
- [ ] Log rotation configured
- [ ] Log levels per module configurable
- [ ] All queries and errors logged
- [ ] Can search logs effectively

**Dependencies**: Task 8.4

---

### Task 8.6: Create Deployment Documentation

**Description**: Write comprehensive deployment guide.

**Definition of Done**:
- [ ] Deployment guide created
- [ ] Prerequisites documented
- [ ] Step-by-step deployment instructions
- [ ] Monitoring and troubleshooting guide
- [ ] Backup/restore procedures documented

**Dependencies**: Task 8.5

---

### Task 8.7: Test Production Deployment

**Description**: Deploy and test complete system end-to-end.

**Definition of Done**:
- [ ] Clean deployment from documentation successful
- [ ] All services running and healthy
- [ ] E2E tests with 10 diverse queries pass
- [ ] Feedback, history, traces all working
- [ ] Resource usage documented
- [ ] Load test with 10 concurrent users successful

**Dependencies**: Task 8.6

---

### Task 8.8: Commit Deployment Phase

**Description**: Final review and commit of deployment work.

**Definition of Done**:
- [ ] Dockerfile builds without errors
- [ ] docker-compose up starts all services
- [ ] Health checks pass
- [ ] E2E test successful
- [ ] Documentation complete
- [ ] Commit includes all deployment files

**Dependencies**: Task 8.7

---

## Summary

**Total Phases**: 9 (Onboarding + Database Migration + 7 implementation phases)

**Total Tasks**: ~70 discrete tasks with clear deliverables

**Key Principles**:
- Read design docs before each phase
- Each task is independently completable
- Definition of Done ensures quality
- Tests written alongside features
- Incremental commits preserve progress

**For Help**: Refer to `docs/DEV_WORKFLOW.md` for development practices.
