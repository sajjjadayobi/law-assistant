---
name: chainlit-ui-debugger
description: Automatically test and debug Chainlit UI/UX changes using Playwright without manual screenshots. Checks welcome screen, chat interface, RTL text, sidebar, buttons, responsiveness, and visual regression.
arguments:
  - "$0": optional test name or feature to focus on (e.g., 'welcome-screen', 'sidebar', 'rtl-text', or 'all')
---

# Chainlit UI/UX Debugging Skill

Automatically test and validate Chainlit UI/UX changes without needing human screenshots or manual validation. This skill uses **Playwright** for browser automation and visual testing.

## Quick Start

```bash
# Test a specific feature
/chainlit-ui-debugger welcome-screen
/chainlit-ui-debugger sidebar
/chainlit-ui-debugger rtl-text

# Test everything
/chainlit-ui-debugger all
/chainlit-ui-debugger
```

## What It Tests

### Core Functionality
- ✅ **Welcome Screen** - Centered layout with starter questions visible
- ✅ **Chat Interface** - Message input, send button, message display
- ✅ **Conversation Sidebar** - History visible, date grouping (امروز, دیروز, ۷ روز, ۳۰ روز)
- ✅ **Thinking Steps** - AI reasoning visualization appears
- ✅ **Tool Calls** - Search operations display correctly

### UI/UX Features
- ✅ **RTL Text** - Persian content displays right-to-left correctly
- ✅ **Responsiveness** - Layout adapts to mobile (375px), tablet (768px), desktop (1920px)
- ✅ **Interactive Elements** - Buttons work, links are clickable
- ✅ **Visual Elements** - Icons visible, colors correct, spacing consistent
- ✅ **Error States** - Error messages display properly
- ✅ **Loading States** - Spinners and progress indicators appear

### Performance
- ✅ **Page Load Time** - Initial load < 3 seconds
- ✅ **Interaction Responsiveness** - Button clicks register < 500ms
- ✅ **Visual Regression** - UI hasn't changed unexpectedly

## Output

The skill generates:
1. **Test Report** - Pass/fail status for each component
2. **Screenshots** - Baseline and current state for comparison
3. **Performance Metrics** - Load times, interaction speeds
4. **Actionable Feedback** - Specific issues with line numbers if applicable

## Requirements

Automatically installs if missing:
- `playwright` - Browser automation
- `pillow` - Image comparison
- `python-dotenv` - Environment loading

## Usage Instructions

### Step 1: Setup

The skill will automatically:
1. Install Playwright (if needed): `pip install playwright && playwright install`
2. Start your Chainlit app in the background on `http://localhost:8000`
3. Wait for app to be ready (with timeout)

### Step 2: Run Tests

Choose a testing mode:

**Option A: Test Specific Feature (Recommended for iterative development)**
```bash
/chainlit-ui-debugger welcome-screen
```
Tests just the welcome screen - fast feedback loop.

**Option B: Test Everything**
```bash
/chainlit-ui-debugger all
```
Comprehensive suite - run before final commit.

**Option C: Quick Smoke Test (Default)**
```bash
/chainlit-ui-debugger
```
Fast core functionality checks.

### Step 3: Review Report

The skill outputs:
- **PASS/FAIL** - Each test component
- **Screenshots** - Saved in `.chainlit-debug/screenshots/`
- **Diffs** - Visual differences highlighted
- **Metrics** - Performance numbers
- **Recommendations** - How to fix failures

### Step 4: Fix Issues

The report includes:
- Expected vs actual values
- Specific selectors that failed
- Line numbers for code references
- Suggested fixes

## Advanced Features

### Visual Regression Tracking

After first run, baseline screenshots are stored:
```
.chainlit-debug/
├── screenshots/
│   ├── baseline/
│   │   ├── welcome-screen.png
│   │   ├── sidebar.png
│   │   └── ...
│   └── current/
│       ├── welcome-screen.png
│       └── ...
├── diffs/
│   ├── welcome-screen-diff.png
│   └── ...
└── report.json
```

Subsequent runs compare against baseline to detect regressions.

### Custom Tests

For features not in default suite, provide details:
- What should happen
- Expected visual appearance
- User interactions to test
- Success criteria

The skill can be extended with new test cases.

## Common Issues & Solutions

### App Won't Start
- Check if port 8000 is in use: `lsof -i :8000`
- Check environment variables: `echo $DATABASE_URL`
- Verify app.py exists and runs: `chainlit run app.py`

### Screenshots Are Blank
- App takes time to render - skill waits 3 seconds
- Check browser console for JavaScript errors
- Verify CSS files are loading (check Chrome DevTools)

### RTL Text Not Working
- Check Persian characters render: Search for 'خ', 'ج', 'ع'
- Verify dir="rtl" is set on parent elements
- Check CSS direction property

### Sidebar Not Visible
- Requires asyncpg: Check `pip list | grep asyncpg`
- Check database has thread records: `psql -c "SELECT COUNT(*) FROM threads;"`
- Verify data layer enabled in app.py (line 155-170)

## Integration with Development

### During Development

```bash
# After UI change, test immediately
/chainlit-ui-debugger sidebar

# If it fails, fix issues, then retest
/chainlit-ui-debugger sidebar
```

### Before Committing

```bash
# Run full suite to catch regressions
/chainlit-ui-debugger all

# If all pass, commit confidently
git add -A && git commit -m "feat(ui): ..."
```

### During Code Review

Share the test report output instead of screenshots:
- "7/8 tests passing"
- "RTL text failing: [specific issue]"
- "3% performance regression on load time"

## How It Works (Technical Details)

### Architecture
1. **Launcher** - Starts Chainlit app, verifies readiness
2. **Navigator** - Opens browser, loads app
3. **Tester** - Runs individual test cases with Playwright
4. **Comparator** - Compares screenshots using pixel-perfect diffing
5. **Reporter** - Aggregates results into readable format

### Test Execution
- Each test runs in isolation
- Timeout protection on all operations (30s default)
- Graceful failure with informative error messages
- Automatic cleanup on exit

### Performance Metrics
- Page load time (time to interactive)
- Time to first meaningful paint
- Button interaction latency
- Network round-trip times

## Extending the Skill

To add new tests for Phase 11 features:

1. Identify UI component to test
2. Provide Playwright selectors
3. Define success criteria
4. Add to test suite configuration

Examples for Phase 11:
- **Thinking Steps** - Check `[role="region"]` contains step text
- **Tool Calls** - Verify `[data-testid="tool-call"]` displays search parameters
- **Sidebar** - Check `[role="complementary"]` shows thread list

## Related Resources

- [Playwright Documentation](https://playwright.dev/)
- [Chainlit API Reference](https://docs.chainlit.io/)
- [Visual Regression Testing Guide](https://playwright.dev/docs/test-snapshots)
- Project: `docs/development/v0.0.2-tasks.md` - Phase 11 features
