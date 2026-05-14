# Garbage Collection: Codebase Cleanup

A guide for cleaning up dead code and unused artifacts from the Law Assistant project.

---

## Automated Cleanup Prompt

Use this prompt with Claude Code to identify and remove dead code:

```
Analyze the law-assistant codebase for dead code and unused artifacts.

For each category below, use grep to find all imports and callers:

1. **Dead source code in `src/`** — modules never imported in production
   - Check each .py file: does anything in src/ or tests/ import it?
   - Exclude re-exports in __init__.py unless that module is also unused
   - Focus on: caching layers, incomplete features (TODO stubs), unused optimizers/analyzers

2. **Dead tests** — test files for removed code
   - test_*.py files that only test dead modules
   - Empty test directories with no test files
   - Load/performance tests not in CI pipeline

3. **Development-only directories**
   - scripts/ (dev utilities, not in Dockerfile/docker-compose)
   - migration/ (one-time database setup, already applied)
   - tests/load/ if not in CI

4. **Unused artifacts**
   - Translation files (keep only actively configured locale + en-US as fallback)
   - Check .chainlit/config.toml for language setting

5. **Unused dependencies in pyproject.toml**
   - Find dependencies never imported anywhere in src/
   - Exclude dev dependencies and transitive dependencies

Output: Three lists
- FILES_TO_DELETE: path and reason for removal
- FILES_TO_KEEP: core production code, all passing tests, deployment configs
- VERIFICATION: test count before/after, key files preserved

User will then:
1. Delete the files
2. Run tests: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`
3. Verify all tests pass
4. Update CLAUDE.md with new test count
5. Commit: `chore: remove dead code and unused artifacts`
```

---

## Last Cleanup Session

**Date**: 2026-05-14
**Commits**: `f8da5cd`, `ed1b393`
**Changes**: Removed 26 files — debug screenshots, unused translations, empty placeholder

### Removed

**Debug artifacts**:
- `.chainlit-debug/screenshots/` — 6 tracked debug screenshots from a UI debugging session (+ 7 untracked)

**Translations** (19 files):
- All locales except `fa-IR.json` (active) and `en-US.json` (fallback)
- Removed: `bn.json`, `de-DE.json`, `el-GR.json`, `es.json`, `fr-FR.json`, `gu.json`, `he-IL.json`, `hi.json`, `it.json`, `ja.json`, `kn.json`, `ko.json`, `ml.json`, `mr.json`, `nl.json`, `ta.json`, `te.json`, `zh-CN.json`, `zh-TW.json`
- Note: these had been correctly deleted in the previous session but reappeared on disk (stale working tree); had to remove twice

**Placeholders**:
- `scripts/.gitkeep` — empty scripts/ directory, no scripts remain

### Also in this session (not GC, but related housekeeping)

- Fixed 19 stale test failures (tests were asserting against old code — `show_thinking` removed, step name strings changed, citation URL changed from `iran.ir` to `panel.danagoo.com`)
- Renamed package `law_agent` → `law_assistant` across all 80+ files
- Updated `.env.example` to match actual `.env` structure

### Test Results

- Before: 298 passing, 19 failing
- After: 313 passing, 0 failing ✓

---

## Previous Cleanup Session

**Date**: 2026-05-08
**Commit**: acc7c2c
**Changes**: Removed 22 files, 3,966 lines of dead code

### Removed

**Source code** (8 modules):
- `src/law_agent/response_cache.py` — unused caching decorator
- `src/law_agent/cache.py` — only imported by response_cache.py
- `src/law_agent/health.py` — routes commented out in app.py with TODO
- `src/law_agent/database/optimization.py` — never imported
- `src/law_agent/ui/observability.py` — stub with TODO methods (real observability in observability/ package)
- `src/law_agent/ui/accessibility.py` — never imported
- `src/law_agent/observability/evaluation.py` — never imported (LLM-as-Judge framework unused)
- `src/law_agent/performance/*` — metrics, profiler, baseline, search_performance (only tested in their own tests, no production callers)

**Tests** (4 items):
- `tests/unit/test_cache.py` — tested dead module
- `tests/unit/test_performance.py` — tested dead module
- `tests/load/*` — Locust load tests (not in CI, no deployment use)
- `tests/unit/ui/__init__.py` — empty package marker

**Scripts & migrations**:
- `scripts/` — dev utilities (load_test_data.py/sql)
- `migration/` — database setup (already applied, in .gitignore)

**Translations**:
- 19 files removed (same list as above — they came back, see 2026-05-14 session)

**Dependencies**:
- `tenacity` from `pyproject.toml`

### Test Results

- Before: 314 passing
- After: 288 passing ✓

---

## Detection Methods

To identify dead code manually:

```bash
# Find all imports of a module
grep -r "from law_assistant.cache import\|import law_assistant.cache" src/ tests/

# Check if a module is exported/used
grep -r "response_cache\|cache_agent_response" src/

# Find files with TODO that are never used
grep -r "TODO\|stub\|incomplete" src/ | grep -E "\.py:" | head -20

# Check translation files actually in use
cat .chainlit/config.toml | grep language

# Find dependencies never imported
for dep in $(grep '^\s*"' pyproject.toml | sed 's/.*"\([^"]*\).*/\1/' | head -20); do
  if ! grep -r "import $dep\|from $dep" src/ >/dev/null; then
    echo "$dep: unused"
  fi
done
```

---

## Preservation Rules

Always keep:
- All files in `src/law_assistant/` that are actively imported
- All test files in `tests/unit/`, `tests/ui/`, `tests/integration/` that test active code
- `docs/` in its entirety (future reference)
- `config.yaml`, `.env.example`, `Makefile`, `pyproject.toml`
- `Dockerfile`, `docker-compose.yml`
- `chainlit.md` (UI welcome message)
- `.chainlit/config.toml`, `.chainlit/translations/fa-IR.json`, `.chainlit/translations/en-US.json`

---

## Checklist for Future Cleanup

- [ ] Run automated detection: grep for imports, analyze dependencies
- [ ] List candidates for removal with reasons
- [ ] Verify tests pass before making changes
- [ ] Delete files in this order: src/, tests/, scripts/, translations, migration/, pyproject.toml
- [ ] Run full test suite: `.venv/bin/python -m pytest tests/ --ignore=tests/integration -q`
- [ ] Update CLAUDE.md with new test count
- [ ] Commit with type `chore` and clear message listing what was removed
- [ ] Verify final test count in commit
