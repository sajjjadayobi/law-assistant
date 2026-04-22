# Configuration System - Plan

## What I'm Building

A type-safe configuration management system using Pydantic Settings that loads defaults from `config.yaml` and allows environment variable overrides for secrets. All application components will use this centralized configuration for model settings, database credentials, search parameters, conversation limits, and UI behavior.

## Why This Matters

Every component needs configuration (database credentials, model settings, search parameters, UI behavior). Centralizing config prevents scattered hardcoded values, makes the system easier to deploy across environments, enables type-safe access to settings throughout the codebase, and follows 12-factor app principles (especially for secrets management).

## Key Design Decisions

### Decision 1: Pydantic Settings + YAML Hybrid

**Decision**: Use Pydantic Settings with YAML file for defaults and environment variables for secrets

**Why**:
- Type safety with automatic validation (prevents invalid configs)
- YAML is readable and easy to edit for developers
- Environment variables follow 12-factor app principles (keep secrets out of code)
- Single source of truth

**Alternatives Considered**:
- Pure environment variables: Rejected - too many variables (20+), hard to document defaults
- Python config files (config.py): Rejected - harder to validate, security risk if someone commits secrets
- JSON config: Rejected - no comments, less readable than YAML

**Trade-offs**: More complex setup than simple dict, but safety is worth it

### Decision 2: Nested Configuration Models

**Decision**: Separate Pydantic models for each config section (ModelConfig, DatabaseConfig, SearchConfig, etc.)

**Why**: Better organization, easier to test individual sections, clearer IDE autocomplete

**Alternatives Considered**: Flat structure with all settings in one model - rejected because harder to navigate with 20+ settings

**Trade-offs**: More boilerplate code, but better maintainability

### Decision 3: Secrets Only in Environment Variables

**Decision**: Never put secrets in config.yaml, only in .env (which is gitignored)

**Why**: Prevents accidental commit of secrets to version control

**Alternatives Considered**: Encrypted config file - rejected as overly complex for this project

**Trade-offs**: Requires setting env vars in all environments, but this is standard practice

## Success Criteria

- [ ] config.yaml created with all 6 sections (model, database, search, conversation, ui, logging)
- [ ] Pydantic models defined: ModelConfig, DatabaseConfig, SearchConfig, ConversationConfig, UIConfig, LoggingConfig
- [ ] Settings class loads from YAML and env vars correctly
- [ ] Environment variables override YAML values (tested)
- [ ] Secrets (DB_PASSWORD, LLM_AUTH_TOKEN) only in environment variables (model-agnostic)
- [ ] .env.example template created with comments
- [ ] Can instantiate Settings() without errors
- [ ] Unit tests pass: config loading, validation, env override
- [ ] Type checking passes (mypy)
- [ ] Documentation: each field in config.yaml has comments explaining its purpose
- [ ] All tests pass (make all)

## Dependencies

- **Requires**: pyproject.toml with pydantic-settings, pyyaml dependencies (Task 2.2 ✅)
- **Blocks**: All subsequent features that need configuration (logging, database, agent, UI)
- **Related**: logging.py will use logging config, database/connection.py will use database config

## Open Questions

- [x] Should we support multiple config files (dev.yaml, prod.yaml)?
  - Decision: No - one config.yaml, use env vars for environment differences (simpler)
- [ ] Do we need config validation beyond Pydantic?
  - Need to: Test edge cases and see if Pydantic validation is sufficient
- [ ] Should port numbers have specific validation?
  - Decision: Yes - use Field(gt=0, lt=65536) to validate port range

## References

- `CLAUDE.md` section: "Configuration Management"
- `design.md`: Configuration section (lines 123-131)
- Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- 12-factor app config: https://12factor.net/config

## Estimated Complexity

**Medium** - Pydantic Settings has learning curve, but well-documented. Main work is defining models, creating config.yaml with all sections, and writing comprehensive tests.
