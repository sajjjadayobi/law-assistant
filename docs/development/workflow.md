# Developer Workflow Guide

This guide covers the complete workflow for building features in the Law Agent project. It emphasizes **documentation-driven development** where you plan first, document as you go, and capture learnings for future developers.

---

## Core Philosophy: Plan, Build, Document, Learn

Every task follows this cycle in strict order:
1. **Plan**: Write down what you'll build and why (plan.md) ← **DO THIS FIRST, BEFORE ANY CODE**
2. **Build**: Implement incrementally with tests (update progress.md DURING this phase)
3. **Document**: Keep a living progress log as you work (progress.md) ← **UPDATE CONTINUOUSLY, NOT AT THE END**
4. **Learn**: Capture lessons, blockers, and solutions

This approach ensures knowledge transfer and helps you (and future developers) understand not just what was built, but why decisions were made and what was learned along the way.

⚠️ **CRITICAL**: plan.md must be written BEFORE you start coding. progress.md must be updated DURING development, not after. See "Before Starting Any Feature" section below.

---

## Before Starting Any Feature

**MANDATORY**: Read `design.md` before starting any new feature. Pay special attention to:
- The sections related to your feature
- How your feature integrates with the overall architecture
- The product requirements and user experience goals

**MANDATORY WORKFLOW ORDER**:
1. ✅ Read design docs
2. ✅ Create feature documentation directory (`docs/features/my-feature/`)
3. ✅ **WRITE plan.md** (do not skip!)
4. ✅ **Create progress.md** (to update during work)
5. ❌ **ONLY THEN** start writing code
6. ✅ **Update progress.md continuously** as you work (not at the end!)
7. ✅ Update CLAUDE.md "Project Status" when feature is complete

If you write code before completing plan.md, you're doing it wrong. Plan first, code second.

---

## 1. Starting a Task

### Step 1.1: Create Feature Documentation Directory

**Before writing any code**, create a documentation directory for your feature:

```bash
# Example: Starting Phase 2, Task 2.3 - Configuration System
mkdir -p docs/features/configuration
cd docs/features/configuration
```

**Directory naming convention**: Use lowercase with hyphens, descriptive names:
- `docs/features/configuration/`
- `docs/features/search-tools/`
- `docs/features/agent-core/`
- `docs/features/citation-system/`
- `docs/features/conversation-management/`

---

### Step 1.2: Write Your Plan (plan.md)

**🔴 MANDATORY - DO THIS FIRST**: Before writing ANY code, create `plan.md` in your feature directory.

If you skip this step or write code before completing plan.md, you're bypassing the core workflow. Plan first, code second - no exceptions.

**Template**:

```markdown
# [Feature Name] - Plan

## What I'm Building

[Concise description of what this feature does - 2-3 sentences]

## Why This Matters

[Explain why this feature is important and how it fits into the overall system]

## Key Design Decisions

### Decision 1: [Name]
**Decision**: [What you decided]
**Why**: [Rationale - explain the reasoning]
**Alternatives Considered**: [What else you thought about and why you didn't choose it]
**Trade-offs**: [What you're giving up with this choice]

### Decision 2: [Name]
[Same structure...]

## Success Criteria

What does "done" look like?
- [ ] Criterion 1 (specific and testable)
- [ ] Criterion 2
- [ ] All tests pass (unit and integration)
- [ ] Documentation updated
- [ ] Code reviewed and merged

## Dependencies

- **Requires**: [What must be done before this - reference tasks]
- **Blocks**: [What is waiting for this to be done]
- **Related**: [Other relevant features or documentation]

## Open Questions

- [ ] Question 1: [What you're uncertain about]
  - Need to: [What you need to do to answer this]
- [ ] Question 2: [What needs clarification]

## References

- `design.md` section: [relevant section name and page/line]
- Related documentation: [file paths]
- External docs: [links to frameworks, libraries]
- Previous discussions: [links to PRs, issues if applicable]

## Estimated Complexity

[Low / Medium / High - with brief justification]
```

**Example** (`docs/features/configuration/plan.md`):

```markdown
# Configuration System - Plan

## What I'm Building

A type-safe configuration management system using Pydantic Settings that loads defaults from `config.yaml` and allows environment variable overrides for secrets. All application components will use this centralized configuration.

## Why This Matters

Every component needs configuration (database credentials, model settings, search parameters, UI behavior). Centralizing config prevents scattered hardcoded values, makes the system easier to deploy across environments, and enables type-safe access to settings throughout the codebase.

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
- [ ] Secrets (DB_PASSWORD, ANTHROPIC_API_KEY) only in environment variables
- [ ] .env.example template created with comments
- [ ] Can instantiate Settings() without errors
- [ ] Unit tests pass: config loading, validation, env override
- [ ] Type checking passes (mypy)
- [ ] Documentation: each field in config.yaml has comments explaining its purpose

## Dependencies

- **Requires**: pyproject.toml with pydantic-settings, pyyaml dependencies (Task 2.2)
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
- `design.md`: No specific section, but affects all components
- Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- 12-factor app config: https://12factor.net/config

## Estimated Complexity

**Medium** - Pydantic Settings has learning curve, but well-documented. Main work is defining models and writing tests.
```

**Purpose of plan.md**:
- Forces you to think before coding (plan-driven development)
- Documents your reasoning for future reference ("Why did we do it this way?")
- Helps identify unclear requirements early (before writing code)
- Makes code review easier (reviewers understand intent)
- Serves as design artifact for the project

---

### Step 1.3: Create Progress Log (progress.md)

**MANDATORY**: Create `progress.md` alongside `plan.md` and **update it continuously** as you work.

This is your development journal - capture everything as it happens.

**Template**:

```markdown
# [Feature Name] - Progress Log

## Session 1: [Date] - [Brief Description]

**Session Goal**: [What you plan to accomplish this session]

**Time Log**:
- [HH:MM] Started session, reviewed plan.md
- [HH:MM] Action taken (be specific)
- [HH:MM] Action taken
- [HH:MM] Encountered blocker: [brief description]
- [HH:MM] Solved blocker, continuing
- [HH:MM] Session complete

**What I Accomplished**:
- [Concrete deliverable 1]
- [Concrete deliverable 2]
- [Tests written/passing]

**Blockers & Solutions**:

#### Blocker 1: [Short title]
**Problem**: [Describe the issue you encountered]
**What I Tried**:
1. Attempt 1 - [what you tried and result]
2. Attempt 2 - [what you tried and result]

**Solution**: [How you finally solved it]
**Why It Worked**: [Explanation of the root cause and solution]
**Lesson Learned**: [Key takeaway for future]
**Time Spent**: [Estimate of time on this blocker]

#### Blocker 2: [Short title]
[Same structure...]

**Questions Asked & Answered**:
- **Q**: [Question you had]
  - **A**: [Answer you found]
  - **Source**: [Where you found it - docs, team member, Stack Overflow, experimentation]
  - **Impact**: [How this changed your approach]

**Decisions Made**:
- Decision: [What you decided]
- Why: [Brief rationale]
- Alternative: [What you didn't choose]

**Code Written**:
- Files modified: [list]
- Files created: [list]
- Tests written: [count and type]

**Next Session**:
- [ ] Task 1 to tackle next
- [ ] Task 2
- [ ] Open question to resolve

**Confidence Level**: [High / Medium / Low] - [brief explanation]

---

## Session 2: [Date] - [Brief Description]

[Same structure as Session 1...]

---

## Final Summary (When Feature is Complete)

**Total Time**: [Estimate]

**What Went Well**:
- [Success 1]
- [Success 2]

**What Was Challenging**:
- [Challenge 1 and how overcome]
- [Challenge 2 and how overcome]

**Key Learnings**:
1. [Learning 1 - specific and actionable]
2. [Learning 2]
3. [Learning 3]

**For Future Developers**:
- [Advice 1 - specific to this feature]
- [Advice 2 - what to watch out for]
- [Advice 3 - shortcuts or best practices discovered]

**If I Had to Do It Again**:
- [What you would do differently]
- [What you would keep the same]

**Related Code**:
- Main files: [list key files with line ranges]
- Tests: [list test files]
- Documentation: [list docs updated]
```

**Example** (`docs/features/configuration/progress.md`):

```markdown
# Configuration System - Progress Log

## Session 1: 2024-01-15 - Initial Structure and Basic Loading

**Session Goal**: Get config.yaml structure defined and basic Settings class loading

**Time Log**:
- 10:00 Started session, reviewed plan.md and design docs
- 10:15 Created config.yaml structure with 6 sections
- 10:45 Defined ModelConfig and DatabaseConfig Pydantic models
- 11:00 Struggled with Settings class loading both YAML and env vars
- 11:30 Found solution in Pydantic docs (model_config)
- 11:50 Got Settings.from_yaml() working!
- 12:00 Created .env.example template
- 12:10 Session complete (ran out of time, will continue tomorrow)

**What I Accomplished**:
- Created config.yaml with all 6 sections (model, database, search, conversation, ui, logging)
- Defined ModelConfig and DatabaseConfig Pydantic models (2 of 6)
- Implemented Settings.from_yaml() class method
- Created .env.example with DB_PASSWORD and ANTHROPIC_API_KEY
- Basic loading works - can instantiate Settings()

**Blockers & Solutions**:

#### Blocker 1: YAML + Environment Variable Merging
**Problem**: Couldn't figure out how to load YAML defaults but allow env vars to override. Was getting either YAML-only or env-only, not both.

**What I Tried**:
1. Manual YAML loading with PyYAML, then passing dict to Settings() - didn't respect env vars
2. Using Settings() directly without YAML - no defaults available
3. Two-pass loading (load YAML, update with env vars) - too complex and error-prone

**Solution**: Found in Pydantic Settings docs that Settings has built-in support via `model_config` with `SettingsConfigDict`. Set `env_file=".env"` and `env_nested_delimiter="__"` in model_config.

**Why It Worked**: Pydantic Settings can natively handle both config files and env vars with proper precedence. I was over-engineering it by trying to do it manually.

**Lesson Learned**: Read framework docs thoroughly before implementing. Pydantic Settings was designed for exactly this use case - I wasted 45 minutes trying to reinvent it.

**Time Spent**: ~45 minutes on this blocker

#### Blocker 2: Type Checking Errors
**Problem**: mypy was complaining about Settings fields: "Need type annotation for 'database'"

**What I Tried**:
1. Adding `# type: ignore` comments - bad practice, didn't solve root cause
2. Tried different import styles for Pydantic models

**Solution**: Needed explicit type annotations for nested models: `database: DatabaseConfig`. Also needed to use `Field(...)` for required fields with descriptions.

**Why It Worked**: mypy requires explicit types for class attributes in strict mode. Pydantic needs Field() to mark required fields.

**Lesson Learned**: In strict mypy mode, always annotate types explicitly. Don't rely on inference.

**Time Spent**: ~15 minutes

**Questions Asked & Answered**:

- **Q**: Should database password have a default value like "password123"?
  - **A**: No! Use `Field(...)` to make it required. Better to fail fast with clear error than have insecure default.
  - **Source**: 12-factor app principles, security best practices
  - **Impact**: Made DB_PASSWORD required with no default

- **Q**: How to validate that model temperature is between 0 and 2?
  - **A**: Use `Field(ge=0.0, le=2.0)` for range validation
  - **Source**: Pydantic Field docs
  - **Impact**: Added validation to ModelConfig.temperature

- **Q**: What format for log level - string or enum?
  - **A**: Use Literal type: `Literal["DEBUG", "INFO", "WARNING", "ERROR"]` for type safety
  - **Source**: Python typing docs, Pydantic best practices
  - **Impact**: Better IDE autocomplete, catches typos at type-check time

**Decisions Made**:
- Decision: Use one config.yaml for all environments
- Why: Simpler than multiple files (dev.yaml, prod.yaml), env vars handle differences
- Alternative: Multiple YAML files per environment - rejected as overkill for our use case

**Code Written**:
- Files created:
  - config.yaml (70 lines with comments)
  - src/law_agent/config/settings.py (90 lines)
  - .env.example (10 lines)
- Tests written: None yet (next session)

**Next Session**:
- [ ] Add remaining 4 config models (SearchConfig, ConversationConfig, UIConfig, LoggingConfig)
- [ ] Write comprehensive unit tests (config loading, validation, env override)
- [ ] Test edge cases (missing required fields, invalid values)
- [ ] Document each field in config.yaml with inline comments

**Confidence Level**: Medium - Basic structure works, but need tests to verify all edge cases

---

## Session 2: 2024-01-16 - Complete Models and Comprehensive Testing

**Session Goal**: Finish all config models, write tests, handle edge cases

**Time Log**:
- 09:00 Started, reviewed yesterday's progress
- 09:15 Added SearchConfig model with validation
- 09:30 Added ConversationConfig model
- 09:45 Added UIConfig model (show_thinking, show_tool_calls, etc.)
- 10:00 Added LoggingConfig with Literal types
- 10:20 Created tests/test_config.py
- 10:35 Wrote test_model_config_defaults() - passed!
- 10:50 Wrote test_model_config_validation() - found bug in temperature validation!
- 11:00 Fixed temperature validation (was using wrong range)
- 11:15 Wrote test_settings_from_yaml() with tmp_path fixture
- 11:45 All 8 tests passing!
- 12:00 Added port number validation (1-65535)
- 12:20 Documented each field in config.yaml with comments
- 12:35 Ran `make all` - everything passes!
- 12:40 Session complete, feature done!

**What I Accomplished**:
- Completed all 6 config models (SearchConfig, ConversationConfig, UIConfig, LoggingConfig)
- Wrote comprehensive test suite: 8 tests covering defaults, validation, YAML loading, env override
- All tests passing (100% coverage for settings.py)
- Added field-level validation (port numbers, temperature range, max_turns limit)
- Documented every field in config.yaml with inline comments
- Feature complete and ready for commit!

**Blockers & Solutions**:

#### Blocker 1: Test Failing Due to Missing .env File
**Problem**: Test test_settings_from_yaml() was failing with "Field required" for DB_PASSWORD, even though I thought I mocked it.

**What I Tried**:
1. Creating actual .env file in tests/ directory - worked but pollutes test environment
2. Using monkeypatch to set env vars - seemed to work but still failing

**Solution**: Needed to set env vars BEFORE calling Settings.from_yaml(). Moved monkeypatch.setenv() calls to top of test function, before creating config file.

**Why It Worked**: Pydantic Settings checks env vars at instantiation time. If not set before calling Settings(), it fails.

**Lesson Learned**: Order matters with env vars in tests - set them first before instantiating classes that depend on them. Consider using pytest fixture for env setup.

**Time Spent**: ~20 minutes

**Questions Asked & Answered**:

- **Q**: Should we allow temperature > 2.0 for experimentation?
  - **A**: No, stick to Anthropic's documented range (0.0-1.0 for Claude). Using 2.0 as max for safety margin.
  - **Source**: Anthropic API docs
  - **Impact**: Set validation to ge=0.0, le=2.0 in Field

- **Q**: What should default log level be in production?
  - **A**: INFO. DEBUG is too verbose for production, INFO captures important events without noise.
  - **Source**: Best practices, 12-factor app
  - **Impact**: Set default to "INFO" in config.yaml

- **Q**: Should max_turns be configurable or hardcoded?
  - **A**: Configurable with sensible default (50). Allows flexibility for testing and future adjustments.
  - **Source**: Design decision
  - **Impact**: Made it configurable with Field(gt=0, le=100)

**Decisions Made**:
- Decision: Use Literal types for enums (log level, log format, persona)
- Why: Better than string typing - catches typos at type-check time, gives IDE autocomplete
- Alternative: Python Enum classes - rejected as more verbose for simple cases

**Code Written**:
- Files modified:
  - src/law_agent/config/settings.py (now 180 lines, all 6 models complete)
  - config.yaml (now 85 lines with detailed comments)
- Files created:
  - tests/test_config.py (120 lines, 8 test functions)
- Tests written: 8 unit tests, all passing

**Test Coverage**: 100% for settings.py module (verified with pytest --cov)

**Next Session**: Feature complete! Ready to commit and move to next task (Logging setup)

**Confidence Level**: High - All tests pass, edge cases handled, code reviewed

---

## Final Summary

**Total Time**: ~3 hours across 2 sessions

**What Went Well**:
- Planning (plan.md) helped identify structure upfront - no major refactoring needed
- Incremental approach (one model at a time) made debugging easy
- Writing tests exposed edge cases early (temperature validation, env var loading)
- Pydantic Settings worked great once I understood it - type safety is excellent

**What Was Challenging**:
- Understanding Pydantic Settings YAML + env var merging took time (should have read docs first)
- Test setup for env vars tricky - needed to understand pytest fixtures better
- Deciding between Literal types vs Enum classes (went with Literal for simplicity)

**Key Learnings**:
1. **Read framework docs first, code second** - Wasted 45 min trying to manually merge YAML+env when Pydantic has built-in support
2. **Test order matters** - Set up test environment (env vars, fixtures) BEFORE instantiating classes
3. **Literal types > strings for constrained values** - Type safety catches bugs at development time
4. **Field validation is powerful** - Use Field(ge=, le=) for ranges, prevents invalid configs
5. **Documentation in config.yaml is critical** - Future developers will thank you

**For Future Developers**:
- When adding new config sections, follow the pattern: create BaseModel, add to Settings class, add to config.yaml with comments
- Always use Field(...) for required secrets (DB_PASSWORD, API keys) - no defaults!
- Test both YAML defaults and env var overrides - they interact in subtle ways
- Use tmp_path fixture for test config files - cleaner than polluting test directory
- Validate ranges for numeric fields (ports: 1-65535, temperature: 0.0-2.0, etc.)

**If I Had to Do It Again**:
- Would read Pydantic Settings docs more thoroughly before starting (save 45 min)
- Would write tests earlier (TDD approach) - found validation bug via tests
- Same approach for plan.md and progress.md - really helpful for staying organized

**Related Code**:
- Main files:
  - src/law_agent/config/settings.py (lines 1-180) - all config models
  - config.yaml (lines 1-85) - configuration defaults
  - .env.example (lines 1-10) - secrets template
- Tests:
  - tests/test_config.py (lines 1-120) - comprehensive test suite
- Documentation:
  - docs/features/configuration/plan.md
  - docs/features/configuration/progress.md (this file)
```

**Purpose of progress.md**:
- **Living document** of your development journey
- Captures **WHY** decisions were made in the moment (not reconstructed later)
- Records **blockers and solutions** so others avoid same mistakes
- Shows **what you learned** - valuable for knowledge transfer and your own growth
- Helps **when you return after a break** ("What was I doing?")
- **Accountability** - tracks time and progress
- **Improves estimation** - understand your own pace and challenges
- **Onboarding tool** - new developers can read your progress logs to understand how features evolved

---

### Step 1.4: Set Up Git Branch

Now that you have your plan, create your feature branch:

```bash
# Always start from main
git checkout main
git pull origin main

# Create feature branch (use descriptive name from plan)
git checkout -b feature/phase-2-configuration

# Verify you're on the right branch
git branch --show-current
```

**Principles** (from Accelerate):
- Keep branches short-lived (< 2 days ideal)
- Merge to main frequently
- Small, incremental changes over large rewrites

---

### Step 1.5: Environment Setup

Before writing code:

```bash
# Activate virtual environment
source .venv/bin/activate

# Ensure dependencies are up to date
uv pip install -e ".[dev]"

# Verify tests pass before you start
pytest tests/

# Check current code quality baseline
make lint
make typecheck
```

---

## 2. Writing Code

### Code Quality Standards

- **Readability first**: Code should be self-explanatory; comments explain *why*, not *what*
- **Type safety**: Use type hints for all function signatures
- **Error handling**: Every function should handle its failure modes gracefully
- **Logging**: Use structlog for all significant operations (see section 7)

### Test-Driven Development

Write tests *alongside* your code, not after:

```bash
# Example workflow for implementing search_documents():
1. Write test case in tests/test_search.py
2. Run test (it fails): pytest tests/test_search.py::test_search_documents
3. Implement function in src/law_agent/tools/search.py
4. Run test again (it passes)
5. Refactor if needed
6. Move to next test case
```

**Coverage goal**: 80%+ for all new code

### Update progress.md as You Go

**CRITICAL**: Update progress.md DURING development, not after! This is not optional.

Update when you:
- Start a new work session (log start time, goal, initial plan check)
- Complete a meaningful chunk of work (file created, test passing, blocker solved)
- Encounter a blocker (document problem, your attempts, and solution)
- Make a decision (document what, why, and alternatives considered)
- Have a question or learning (capture it immediately - DURING the work)
- Learn something unexpected (write it down right away - don't forget later!)
- End your session (summarize accomplishments, plan next steps, confidence level)

**Why?**: You won't remember these details later. Capturing them immediately preserves the reasoning and experience for future developers (and yourself). This is how knowledge transfer happens.

**How**: Keep progress.md open in your editor while coding. It takes 30 seconds to add an entry. Every entry is valuable for understanding how and why the feature evolved.

**What counts as "updating DURING work"?**
- ✅ Adding a progress entry every 15-30 minutes
- ✅ Logging blockers as you encounter them, with solutions as you find them
- ✅ Recording decisions and alternatives in real-time
- ✅ Capturing learnings as you discover them
- ❌ Writing progress.md only at the end of the day
- ❌ Reconstructing what happened from memory
- ❌ Generic updates without specific details

---

## 3. Testing

### Running Tests Locally

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_search.py

# Run specific test
pytest tests/test_search.py::test_search_documents

# Run with coverage
pytest --cov=src/law_agent --cov-report=html

# Run only unit tests (fast)
pytest tests/unit/

# Run integration tests (requires database)
pytest tests/integration/
```

### Test Data Management

```bash
# Reset test database to clean state
./tests/scripts/reset_test_db.sh

# Load fresh test data
./tests/scripts/load_test_data.sh
```

### Manual Testing Checklist

Before considering a feature "done":
- [ ] Feature works with happy path input
- [ ] Feature handles edge cases (empty input, invalid input, etc.)
- [ ] Feature handles errors gracefully (shows user-friendly messages)
- [ ] Feature works with Persian text (if applicable)
- [ ] Feature logs appropriately (see section 7)
- [ ] Feature doesn't break existing functionality (run full test suite)
- [ ] plan.md success criteria all met
- [ ] progress.md final summary written

---

## 4. Self-Review

Before committing, review your own code:

### Code Review Checklist

- [ ] **Correctness**: Does it solve the problem completely?
- [ ] **Simplicity**: Is this the simplest solution? Can it be simplified?
- [ ] **Readability**: Can another developer understand this in 6 months?
- [ ] **Type safety**: All functions have type hints?
- [ ] **Error handling**: All failure modes handled?
- [ ] **Tests**: Tests cover critical paths and edge cases?
- [ ] **Documentation**: Complex logic explained in docstrings?
- [ ] **No dead code**: Removed commented-out code and unused imports?
- [ ] **Performance**: No obvious performance issues? (Don't premature-optimize)
- [ ] **Security**: No secrets hardcoded? Inputs validated?
- [ ] **Progress log**: progress.md updated with final summary?

### Automated Checks

Run all quality checks before committing:

```bash
# Format code
make format

# Lint
make lint

# Type check
make typecheck

# Run tests
make test

# Or run everything at once
make all
```

Fix all issues before committing.

---

## 5. Committing Changes

### Commit Strategy

Follow these principles (from Accelerate):
- **Small, meaningful commits**: One logical change per commit
- **Frequent commits**: Commit working code multiple times per day
- **Descriptive messages**: Explain *what* and *why*, not just *what*
- **Include documentation**: Always commit plan.md, progress.md, and updated CLAUDE.md with feature code

### Commit Message Format

We use Conventional Commits style:

```
<type>(<scope>): <short description>

<longer description if needed>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `chore`: Maintenance tasks (dependencies, config, etc.)

### Before Pushing

**Step 1: Update CLAUDE.md Project Status**

When your feature is complete, update `CLAUDE.md` to reflect the new status:

```bash
# Edit CLAUDE.md
# 1. Update "Project Status" section
#    - Mark completed tasks with ✅
#    - Update "Current Phase" if needed
#
# 2. Update "What to Work On Next"
#    - Move next task to "START HERE"
#    - Update task list based on phase progress
#
# 3. Save and stage the file
git add CLAUDE.md
```

**Example CLAUDE.md update**:
```markdown
**Current Phase**: Phase 2 (Foundation) - In Progress (Tasks 2.1, 2.2, 2.3 complete)

**Completed**:
- ✅ Phase 0: Onboarding & Setup
- ✅ Phase 1: Database Migration
- ✅ Task 2.1: Project Structure initialized
- ✅ Task 2.2: Dependency management complete
- ✅ Task 2.3: Configuration system implemented  ← NEW!

**Next Steps**:
4. **Task 2.4**: Implement structured logging (structlog setup) ← **START HERE**
```

**Step 2: Review and Commit All Documentation**

```bash
# Review what you're committing
git status
git diff

# Stage files including documentation
git add src/law_agent/config/
git add tests/test_config.py
git add config.yaml .env.example
git add docs/features/configuration/  # Include plan.md and progress.md!
git add CLAUDE.md  # Include updated project status!

# Commit with descriptive message
git commit -m "feat(config): implement type-safe configuration system

Added Pydantic Settings-based config with YAML defaults and env var
overrides. Includes 6 config sections: model, database, search,
conversation, ui, logging.

Key features:
- Type-safe configuration with validation
- Secrets only in environment variables
- Comprehensive test suite (8 tests, 100% coverage)

Resolves Task 2.3 from docs/development/tasks.md

Documentation: docs/features/configuration/"

# Push to remote
git push origin feature/phase-2-configuration
```

**IMPORTANT**: Always commit these files with your code:
- ✅ plan.md and progress.md (feature documentation)
- ✅ CLAUDE.md (updated project status)
- ✅ Your code changes and tests

They are all part of the feature delivery. Keeping CLAUDE.md current helps everyone know what's completed and what's next.

---

## 6. Engineering Principles from Accelerate

Key principles to follow:

### Continuous Integration
- **Merge to main frequently** (at least every 2 days)
- **Keep main deployable** (all tests pass, no broken code)
- **Fast feedback loops** (CI runs in < 5 minutes)

### Small Batch Sizes
- **Small features** over large features
- **Incremental changes** over big-bang releases
- **Early integration** over long-lived branches

### Test Automation
- **Test coverage** as a quality gate (80%+ required)
- **Fast tests** (unit tests run in seconds, integration tests in minutes)
- **Reliable tests** (no flaky tests; fix or remove them)

### Monitoring and Observability
- **Log everything** significant (user queries, errors, performance)
- **Structured logging** for easy searching and analysis
- **Trace requests** end-to-end (using Phoenix)

### Iterative Development
- **Measure then optimize** (don't premature-optimize)
- **Build, measure, learn** (use Phoenix metrics to improve)
- **Fail fast** (prefer early errors over silent failures)

### Documentation and Knowledge Sharing
- **Document decisions** (plan.md explains why)
- **Capture learnings** (progress.md preserves knowledge)
- **Make knowledge accessible** (docs/features/ for all features)

---

## 7. Logging and Debugging

### Structured Logging Pattern

Always use structlog with structured data:

```python
import structlog

logger = structlog.get_logger(__name__)

# Good - structured data
logger.info(
    "search_executed",
    query="بیمه مسئولیت",
    result_count=15,
    execution_time_ms=234,
    doc_types=["law", "regulation"],
)

# Bad - string formatting
logger.info(f"Search for بیمه مسئولیت returned 15 results in 234ms")
```

**Why structured?** You can grep, filter, and analyze logs easily:

```bash
# Find all slow searches (> 1 second)
grep "search_executed" app.log | jq 'select(.execution_time_ms > 1000)'

# Count searches by doc_type
grep "search_executed" app.log | jq '.doc_types[]' | sort | uniq -c
```

### What to Log

Log these events:
- **User queries** (query text, persona, conversation_id)
- **Tool calls** (tool name, parameters, execution time, result count)
- **Errors** (exception type, message, stack trace, context)
- **Performance** (slow queries > 2s, high token usage)
- **Business metrics** (searches per conversation, feedback events)

### Log Levels

- `DEBUG`: Detailed diagnostic information (not in production)
- `INFO`: Normal operations (user queries, tool calls)
- `WARNING`: Unexpected but handled situations (no search results)
- `ERROR`: Errors that need attention (database connection failed)

### Checking Logs

```bash
# Local development - view logs in console
# Logs appear in terminal as you work

# Production - view Docker logs
docker-compose logs app

# Follow logs in real-time
docker-compose logs -f app

# Filter logs by level
docker-compose logs app | grep "ERROR"

# Search for specific query
docker-compose logs app | grep "بیمه"
```

### Using Phoenix for Debugging

For complex issues, use Phoenix traces:

1. Open Phoenix UI: http://localhost:6006
2. Find the conversation trace
3. Inspect tool calls and timing
4. Check token usage and cost
5. View error details if any

**Common debugging workflows**:
- **Slow response**: Check Phoenix trace for slow tool calls
- **Wrong answer**: Review tool call sequence (did agent use right tools?)
- **No results**: Check search parameters in logs
- **Error**: Find error span in Phoenix, review stack trace

---

## 8. Feature Documentation Review

Before marking a feature complete, ensure:

### plan.md Checklist
- [ ] All success criteria met
- [ ] All open questions answered (mark as resolved with decisions)
- [ ] No major deviations from plan (if there are, document why)

### progress.md Checklist
- [ ] Final summary written
- [ ] Key learnings captured
- [ ] "For future developers" section completed
- [ ] All major blockers documented with solutions
- [ ] Total time estimated

### Code Checklist
- [ ] All files created/modified listed in progress.md
- [ ] All tests passing
- [ ] Documentation (docstrings, comments) complete
- [ ] No TODOs or FIXMEs left in code

---

## Quick Reference

```bash
# Starting a new feature
mkdir -p docs/features/my-feature
cd docs/features/my-feature
# Write plan.md
# Create progress.md
git checkout -b feature/my-feature

# Daily workflow
# ... write code and update progress.md continuously ...
make all                    # format, lint, typecheck, test
git add <files>
git add docs/features/my-feature/  # Don't forget documentation!
git commit                  # write good message!
git push origin feature/my-feature

# Common commands
make format                 # Format code with Black
make lint                   # Lint with Ruff
make typecheck              # Type check with mypy
make test                   # Run tests
make all                    # Run all checks

# Testing
pytest tests/               # All tests
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest --cov                # With coverage

# Debugging
docker-compose logs -f app  # View logs
# Open http://localhost:6006 for Phoenix traces
```

---

## Getting Help

- **Stuck on design?** Re-read `design.md` and `search.md`
- **Stuck on task?** Check Definition of Done in `TASK_BREAKDOWN.md`
- **Stuck on similar feature?** Read docs/features/ for related features
- **Tests failing?** Check feature's test.md (if exists) or progress.md for testing notes
- **Environment issues?** Reset database with `./tests/scripts/reset_test_db.sh`
- **Ask questions!** Document questions in progress.md as you resolve them

---

## Why This Workflow?

This workflow might seem like "extra work" at first, but it provides massive benefits:

**For You**:
- Clearer thinking (planning before coding prevents mistakes)
- Less context switching (progress.md helps you resume after breaks)
- Better learning (documenting blockers cements knowledge)
- Faster debugging (logs show your reasoning)

**For Future Developers** (including future you):
- Understand **why** things were built this way
- Avoid **same mistakes** (blockers are documented with solutions)
- Learn from **your experience** (progress logs are tutorials)
- **Estimate better** (see how long similar tasks took)

**For the Project**:
- **Knowledge base** grows with every feature
- **Onboarding** is faster (read plan + progress docs)
- **Maintenance** is easier (understand original intent)
- **Quality** improves (planning catches issues early)

**Remember**: Documentation is not separate from development - it IS development. Write it as you go, not after.
