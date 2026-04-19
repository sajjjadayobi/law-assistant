# Project Structure Initialization - Plan

## What I'm Building

Initialize the Python package structure for the Law Agent by creating `src/law_agent/` with proper module organization for config, database, tools, agent, and UI components. This provides the foundation for all subsequent development phases.

## Why This Matters

Proper project structure is essential for:
- Clean code organization and maintainability
- Easy module imports and dependencies
- Following Python packaging best practices
- Scaling as the project grows from 3 to 70+ files
- Clear boundaries between concerns (config, DB, tools, agent, UI)

Without this foundation, code becomes scattered and hard to navigate.

## Key Design Decisions

### Decision 1: `src/law_agent/` layout vs. flat structure

**Decision**: Use `src/law_agent/` (namespace package) with organized subdirectories for each concern

**Directory structure**:
```
src/law_agent/
├── __init__.py                    # Package marker
├── config/                        # Configuration system
│   ├── __init__.py
│   └── settings.py               # Pydantic Settings (Task 2.3)
├── database/                     # Database layer
│   ├── __init__.py
│   ├── connection.py             # SQLAlchemy setup (Task 2.5)
│   └── models.py                 # ORM models (Task 2.6)
├── tools/                        # Search tools
│   ├── __init__.py
│   ├── search.py                # search_documents (Task 3.4)
│   └── utils.py                 # Text processing helpers (Task 3.3)
├── agent/                       # Agent core
│   ├── __init__.py
│   └── law_agent.py            # PydanticAI agent (Task 4.2)
└── ui/                          # Chainlit interface
    ├── __init__.py
    └── app.py                   # Chainlit app (Task 5.2)
```

**Why**:
- `src/` layout is Python best practice (PEP 517 compliant)
- Namespaced package (law_agent) prevents naming conflicts
- Clear subdirectories by concern (config, database, tools, agent, ui)
- Easy to add new modules later (logging, observability, etc.)

**Alternatives Considered**:
- Flat structure (all files in root): Rejected - becomes cluttered and unclear as codebase grows
- Single `law_agent/` in root: Rejected - not PEP 517 compliant, harder to package for distribution

**Trade-offs**: Slightly deeper directory nesting, but clarity outweighs this minor cost

### Decision 2: `__init__.py` files and package markers

**Decision**: Create empty `__init__.py` in each module directory (Python 3.3+ namespace packages don't require them, but they're explicit and safe)

**Why**:
- Explicit package markers
- Works with all Python versions
- Standard practice in production code
- Makes it clear these are packages, not just directories

**Alternatives Considered**: Skip `__init__.py` files (Python 3.3+ supports namespace packages without them) - rejected because explicit is better than implicit

### Decision 3: Tests directory structure

**Decision**: Keep tests at project root level (`tests/`) mirroring `src/` structure

**Layout**:
```
tests/
├── conftest.py
├── unit/
│   ├── test_config.py           # (Task 2.7)
│   └── test_models.py           # (Task 2.7)
└── integration/
    ├── test_database.py         # (Task 2.7)
    └── test_search.py           # (Task 3.7)
```

**Why**:
- Standard Python testing convention
- Makes it clear what's production (src/) vs test (tests/)
- Easy to run tests separately (pytest tests/unit, pytest tests/integration)

### Decision 4: Configuration and data files

**Decision**: Keep config.yaml at project root, migrations in separate directory

**Why**:
- config.yaml is an artifact that lives at project root (Pydantic Settings convention)
- Migration scripts are tools, not part of the package
- Easier to find and edit config files

## Success Criteria

- [ ] `src/law_agent/` directory created with correct structure
- [ ] All subdirectories created: config/, database/, tools/, agent/, ui/
- [ ] All `__init__.py` files present (empty is fine for now)
- [ ] `tests/` directory structure created: tests/unit/, tests/integration/
- [ ] `.gitignore` updated to ignore Python artifacts (__pycache__, *.pyc, .pytest_cache, etc.)
- [ ] Project structure matches the layout above
- [ ] Can verify with `find src/ tests/ -type f -name "__init__.py"` (shows all 8+ __init__.py files)
- [ ] No errors when running `python -c "import law_agent"` (after dependencies installed)
- [ ] Project structure documented in this plan.md
- [ ] Committed with documentation

## Dependencies

- **Requires**: Phase 1 completed (migration done)
- **Blocks**: All subsequent tasks (config system, database layer, tools, agent, UI)
- **Related**: pyproject.toml already exists (Task 2.2), will use this structure

## Open Questions

- [x] Should tests use pytest or unittest?
  - Decision: pytest (already in pyproject.toml, modern standard)
- [x] Should we have separate package for migrations?
  - Decision: No, migration is a one-time script at project root level
- [x] Should we have a `scripts/` directory?
  - Decision: Yes, add `scripts/` for utility scripts (future use)

## References

- PEP 517: https://peps.python.org/pep-0517/
- Python Packaging Guide: https://packaging.python.org/tutorials/packaging-projects/
- pytest Conventions: https://docs.pytest.org/en/stable/how-to/pythonpath.html#adding-to-syspath
- Current pyproject.toml at project root (already defines `packages = [{include = "law_agent", from = "src"}]`)

## Estimated Complexity

**Low** - This is mostly creating directories and empty __init__.py files. No complex logic or dependencies.

**Time estimate**: 20-30 minutes including testing
