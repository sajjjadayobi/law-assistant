# Task 2.2: Set Up Dependency Management

## Overview

Set up `pyproject.toml` with all project dependencies and tool configurations for Python package management using modern standards (PEP 517/518).

## Goal

Create a production-ready Python package configuration that:
- Declares all core and dev dependencies with pinned versions
- Configures Black, Ruff, and mypy with consistent rules
- Enables installation with `uv pip install -e .` and `uv pip install -e ".[dev]"`
- Supports the build system for wheel generation

## Key Design Decisions

### 1. Package Manager: uv
- **Why**: Modern, fast Python package manager with deterministic resolution
- **Alternative**: pip (slower, no lock file support)
- **Decision**: Use `uv` as primary tool, documented in CLAUDE.md

### 2. Build System: hatchling
- **Why**: Modern, PEP 517 compliant build backend
- **Alternative**: setuptools (heavier, more complex)
- **Decision**: Use hatchling for lightweight builds

### 3. Tool Configuration Location
- **Why**: Centralized pyproject.toml instead of separate files
- **Benefits**: Single source of truth, easier to manage
- **Tools configured**: Black, Ruff, mypy, pytest

### 4. Dependency Strategy
- **Core dependencies**: Only what's needed for production
- **Dev dependencies**: Testing, linting, type checking (optional group)
- **Version pinning**: Minimum versions specified, allow upgrades

## Dependencies Structure

### Core Dependencies (47 total)
- **Database**: psycopg2-binary, sqlalchemy
- **Text Processing**: beautifulsoup4, jdatetime, hazm
- **Agent Framework**: pydantic-ai, pydantic, pydantic-settings
- **LLM Integration**: anthropic
- **Resilience**: tenacity
- **Logging**: structlog
- **Configuration**: pyyaml
- **UI**: chainlit
- **Observability**: arize-phoenix, opentelemetry-api, opentelemetry-sdk

### Dev Dependencies (7 total)
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Code Quality**: black, ruff, mypy
- **Git Hooks**: pre-commit

## Tool Configurations

### Black (Code Formatter)
- Line length: 100 characters
- Target Python: 3.9+
- Config in `[tool.black]`

### Ruff (Linter)
- Line length: 100 characters
- Target Python: 3.9
- Selected rules: E, W, F, I, N, UP, B, C4
- Ignored: E501 (line too long - handled by Black)
- Config in `[tool.ruff]`

### mypy (Type Checker)
- Python version: 3.9
- Strict mode: enabled
- Excluded paths: tests/, .venv/
- Library stubs: hazm, chainlit, arize, opentelemetry
- Config in `[tool.mypy]`

### pytest (Test Runner)
- Test paths: tests/
- Python path: src/
- Async mode: auto
- Config in `[tool.pytest.ini_options]`

## Success Criteria

- ✅ pyproject.toml created with all dependencies
- ✅ Black, Ruff, mypy configured with appropriate rules
- ✅ Installation works: `uv pip install -e .`
- ✅ Dev installation works: `uv pip install -e ".[dev]"`
- ✅ Makefile targets work (format, lint, typecheck, test, all, clean)
- ✅ Package builds without errors
- ✅ Tools run successfully on codebase

## Dependencies

- **Prerequisite**: Task 2.1 (Project Structure) - COMPLETED
  - Requires `src/law_agent/` directory structure
  - Requires `src/law_agent/__init__.py` for package discovery

## Open Questions

None - configuration is straightforward and well-documented in pyproject.toml.
