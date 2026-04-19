# Structured Logging Setup - Plan

## What I'm Building

A comprehensive structured logging system using structlog that integrates with the existing configuration system. This includes:
- Centralized logging configuration via config.yaml (already defined in Task 2.3)
- structlog initialization with context management (sync, no async yet)
- Logging utilities and patterns for consistent log output across the codebase
- Integration with text and JSON formatters (JSON for production/Phoenix, text for development)
- Decorator patterns for function instrumentation (optional)

## Why This Matters

Structured logging is critical for:
- **Observability**: All agent operations, tool calls, and errors are recorded with structured data
- **Debugging**: When things go wrong, we have detailed context (query, parameters, execution time, errors)
- **Integration with Phoenix**: Phoenix expects structured logs and can visualize them
- **Production monitoring**: Logs are machine-parseable (JSON), easy to search and analyze
- **Cost tracking**: Log token usage, search execution times, response times per conversation

Without proper logging, troubleshooting will be extremely difficult. This is foundation for Phase 2 and all subsequent work.

## Key Design Decisions

### Decision 1: Sync-Only Logging (for now)
**Decision**: Implement synchronous structlog setup, no async queue (yet)
**Why**:
- Simpler implementation, easier to debug
- Sufficient for development and early production
- Can add async later (Task 2.7+) if performance becomes an issue

**Alternatives Considered**:
- Async queue with ProcessorFormatter: Would add complexity, needed only if logging becomes bottleneck
- Both sync and async modes: Too much complexity for Phase 2

**Trade-offs**: Logging is synchronous, could block during very high load, but acceptable for initial implementation

### Decision 2: Two-Formatter Strategy
**Decision**: Support both text (development) and JSON (production) via config.logging.format
**Why**:
- Text: Human-readable during development
- JSON: Machine-parseable for production and Phoenix integration
- Single source of truth: Choose format in config.yaml, not code

**Alternatives Considered**:
- Always JSON: Bad for development (hard to read in console)
- Always text: Not suitable for production/Phoenix

**Trade-offs**: Need to support both formatters, slightly more complex

### Decision 3: Contextvars for Request Context
**Decision**: Use contextvars for thread-safe context (conversation_id, user_id, etc.)
**Why**:
- Thread-safe context propagation
- Works with async/await (for future)
- Standard Python approach (PEP 567)
- Phoenix integration: Context variables appear in all logs automatically

**Alternatives Considered**:
- Thread-local storage: Not async-safe
- Passing context through function parameters: Verbose, error-prone

**Trade-offs**: Requires understanding of contextvars, but well-documented

### Decision 4: Minimal Initial Log Points
**Decision**: Set up infrastructure in Phase 2, add extensive logging in Phase 3+ (agent, search)
**Why**:
- Phase 2 is just foundation (config, logging, database setup)
- Real logging needed in Phase 3 (search tools) and Phase 4 (agent)
- Prevents premature instrumentation
- Focus on correct setup, not usage yet

**Alternatives Considered**:
- Log everything now: Overkill for Phase 2, would need to refactor later
- Log nothing: Would need to retrofit logging later

**Trade-offs**: Some useful logging will be added in later phases, Phase 2 is just infrastructure

### Decision 5: No External Dependencies Beyond structlog
**Decision**: Use only structlog (already in pyproject.toml), avoid extra packages
**Why**:
- structlog is highly capable and configurable
- Avoid dependency bloat
- Most use cases covered by structlog built-ins

**Alternatives Considered**:
- python-json-logger: Extra dependency, structlog can do JSON
- pythonjsonlogger: Same issue, structlog handles it

**Trade-offs**: May need custom processors for some use cases (acceptable)

## Success Criteria

- [ ] Create `src/law_agent/logging/` module with:
  - `__init__.py` (exports public API)
  - `config.py` (structlog initialization based on settings)
  - `context.py` (context management with contextvars)
  - `formatters.py` (text and JSON formatters)
- [ ] Integrate with config.yaml logging section (level, format, file_path)
- [ ] Can instantiate logger: `logger = structlog.get_logger(__name__)`
- [ ] Support both text and JSON output formats
- [ ] Context variables work (conversation_id, user_id, session_id, etc.)
- [ ] Write unit tests covering:
  - Logger instantiation
  - Text formatting
  - JSON formatting
  - Context variable binding
  - Config loading and validation
- [ ] Documentation:
  - Usage guide in logging module docstring
  - Example in docstring showing structured data patterns
  - Comments explaining context management
- [ ] All tests pass (pytest)
- [ ] Code quality passes: `make all` (format, lint, typecheck, test)
- [ ] No warnings or errors

## Dependencies

- **Requires**:
  - Task 2.2 (dependencies installed - structlog is in pyproject.toml)
  - Task 2.3 (configuration system - logging config already defined in config.yaml)
- **Blocks**:
  - Task 2.5 (database connection will need logging)
  - Task 2.6 (ORM models will need logging)
  - Task 3.x (search tools will use logging)
  - Task 4.x (agent will use logging)
- **Related**:
  - structlog documentation: https://www.structlog.org/
  - docs/best-practices/agent-engineering.md section on logging
  - CLAUDE.md section 7 (Logging and Debugging)

## Open Questions

- [ ] Q: Should we log to file during development?
  - A: Not yet. Keep file_path: null in config.yaml. Can add later in Phase 2.8.
  - Impact: Simpler setup, logs only to console during development

- [ ] Q: What contextvars do we need (conversation_id, user_id, session_id)?
  - A: Start with minimal set: conversation_id (required), user_id (optional), session_id (optional)
  - Impact: Can add more later as needed

- [ ] Q: Should we filter sensitive data (passwords, API keys) from logs?
  - A: Not in Phase 2. Add in Phase 4+ with dedicated sanitizer
  - Impact: Keep logging setup simple, add security later

- [ ] Q: Use asyncio task context or contextvars?
  - A: contextvars (PEP 567) - works with both sync and async
  - Impact: Correct approach, no changes needed for async later

## References

- `design.md`: No specific logging section, but logging is core infrastructure
- `search.md`: Section "Agent Search Architecture" mentions logging tool calls
- `CLAUDE.md`: Section 7 (Logging and Debugging) - shows logging patterns
- `docs/development/workflow.md`: Section 7 (Logging and Debugging) - same patterns
- structlog documentation: https://www.structlog.org/en/stable/
- contextvars docs: https://docs.python.org/3/library/contextvars.html
- Best practices: CLAUDE.md shows desired logging patterns

## Estimated Complexity

**Medium** - structlog has a learning curve but is well-documented. Main work is:
1. Understanding structlog's processor chains
2. Setting up both text and JSON formatters
3. Integrating with Pydantic Settings config
4. Context management with contextvars (straightforward once understood)
5. Writing comprehensive tests for formatters and context

Timeline estimate: 2-3 hours
