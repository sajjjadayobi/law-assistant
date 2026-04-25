# Chainlit UI/UX Debugger Skill

**Automated testing and debugging for Chainlit UI changes without manual screenshots or human validation.**

## 🎯 Purpose

When you make UI/UX changes to your Chainlit app, you want to know immediately:
- ✅ Does the welcome screen look centered?
- ✅ Can users click starter questions?
- ✅ Does Persian text display RTL correctly?
- ✅ Is the sidebar showing conversation history?
- ✅ Do thinking steps and tool calls appear?
- ✅ Is the layout responsive on mobile?

Instead of manually taking screenshots and describing what you see, this skill **automatically validates all UI aspects** and reports findings.

## 🚀 Quick Start

```bash
# Test everything
/chainlit-ui-debugger all

# Test specific feature
/chainlit-ui-debugger welcome-screen
/chainlit-ui-debugger sidebar
/chainlit-ui-debugger rtl-text

# Test core functionality (default)
/chainlit-ui-debugger
```

## 📋 What Gets Tested

### Phase 11 (v0.0.2) Features
- **11.1**: Centered welcome screen with starter questions ✅
- **11.2**: Conversation history sidebar with date grouping ✅
- **11.3**: Thinking steps visualization ✅
- **11.4**: Tool calls visualization ✅

### Core UI/UX
- Welcome screen layout and centering
- Chat message input and display
- Conversation history sidebar
- RTL (right-to-left) text for Persian
- Responsiveness (mobile, tablet, desktop)
- Interactive elements (buttons, links)
- Error states and messages

### Performance & Quality
- Page load time
- Button interaction latency
- Visual regression detection
- Network performance

## 📊 Example Output

```
============================================================
🧪 CHAINLIT UI/UX TEST REPORT
============================================================
Generated: 2025-04-25 14:32:15

✅ WELCOME-SCREEN: 3/3 passed
✅ CHAT: 2/2 passed
✅ SIDEBAR: 2/3 passed (1 skipped - requires asyncpg)
✅ RTL-TEXT: 2/2 passed
✅ RESPONSIVENESS: 3/3 passed
⚠️  VISUAL-REGRESSION: 1 warning (5% image diff)

DETAILED RESULTS:
✅ [welcome-screen] Welcome screen centered
   Message: Welcome screen is centered
   Time: 1245ms

✅ [welcome-screen] Starter questions visible
   Message: Found 3 starter questions
   Time: 1256ms
...
```

## 🏗️ Architecture

### How It Works

1. **Setup Phase**
   - Checks if Chainlit app is already running on port 8000
   - If not, starts it automatically with `chainlit run app.py`
   - Waits for app to be ready (with timeout)

2. **Test Phase** (each test in isolation)
   - Launches browser using Playwright (Chromium)
   - Navigates to the app
   - Performs UI checks (visibility, layout, interaction)
   - Captures screenshots if needed
   - Measures timing

3. **Comparison Phase**
   - First run: Establishes baseline screenshots
   - Later runs: Compares current state vs baseline
   - Calculates visual diff percentage
   - Reports regressions

4. **Report Phase**
   - Aggregates results by category
   - Generates readable text report
   - Saves detailed JSON report
   - Provides actionable feedback

### Test Categories

| Category | Tests | Phase |
|----------|-------|-------|
| `welcome-screen` | Centering, starter questions, clickability | 11.1 |
| `chat` | Message input, send button, message display | Core |
| `sidebar` | Visibility, date grouping, thread list | 11.2 |
| `rtl-text` | Text direction, Persian character rendering | Core |
| `responsiveness` | Mobile, tablet, desktop layouts | Core |
| `thinking-steps` | Step visibility and content | 11.3 |
| `tool-calls` | Tool call visualization | 11.4 |
| `visual-regression` | Pixel-perfect comparison vs baseline | Core |

## 🔧 Requirements

### Automatic Installation
The skill handles these automatically on first run:
- `playwright` (browser automation)
- `pillow` (image comparison)
- Playwright browsers (Chromium, Firefox, WebKit)

### Manual Setup (if needed)
```bash
pip install playwright pillow
playwright install
```

### Environment
- Python 3.9+
- Running from project directory (contains `app.py`)
- Port 8000 available (or modify base_url)
- 2-3GB free disk space for screenshots and baselines

## 🐛 Troubleshooting

### "App won't start"
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Check if app.py exists
ls -la app.py

# Try running manually to see errors
chainlit run app.py
```

### "Screenshots are blank"
- App needs time to render - skill waits up to 3 seconds
- Check browser console for JavaScript errors
- Verify CSS files are loading correctly
- Try in Chrome DevTools: `F12` → Console

### "RTL text not rendering"
- Check Persian characters render: Search for 'خ', 'ج', 'ع'
- Verify `dir="rtl"` is set on parent elements
- Check CSS: `direction: rtl;` property applied
- Use browser DevTools to inspect computed styles

### "Sidebar shows as SKIP"
- Sidebar requires `asyncpg` to be installed
- Check: `pip list | grep asyncpg`
- Data layer must be enabled in `app.py` (lines 155-170)
- Database must have thread records: `psql -c "SELECT COUNT(*) FROM threads;"`

### "Visual regression shows high diff %"
- First run establishes baseline - expected for new features
- Large diff (>20%) suggests UI layout changed
- Review screenshot diffs in `.chainlit-debug/diffs/`
- If intentional, delete baseline and re-run to establish new baseline

## 📁 Output Files

The skill generates:

```
.chainlit-debug/
├── screenshots/
│   ├── baseline/          # First run snapshots (golden standard)
│   │   ├── welcome-screen.png
│   │   ├── sidebar.png
│   │   └── ...
│   └── current/           # Latest run snapshots
│       ├── welcome-screen.png
│       └── ...
├── diffs/                 # Visual differences highlighted
│   ├── welcome-screen-diff.png
│   └── ...
└── report.json            # Machine-readable results
```

## 🔄 Integration with Development

### During Active Development

```bash
# After UI change, test immediately
/chainlit-ui-debugger sidebar

# If fails, fix, then retest
/chainlit-ui-debugger sidebar

# Keep iterating until all pass
```

### Before Committing

```bash
# Full suite catches regressions
/chainlit-ui-debugger all

# If all pass, commit confidently
git add -A && git commit -m "feat(ui): ..."
```

### In Code Review

Instead of screenshots, share:
```
✅ WELCOME-SCREEN: 3/3 passed
✅ CHAT: 2/2 passed
⚠️  SIDEBAR: 2/3 passed (1 skipped)
✅ RTL-TEXT: 2/2 passed
✅ VISUAL-REGRESSION: no regressions
```

## 🎨 Extending for New Features

To add tests for new Phase 11 features:

### Example: Testing "Feedback Thumbs Up/Down"

1. Identify the selector: `[data-testid="feedback-thumbs"]`
2. Define success: "User can click thumbs up/down"
3. Add to test category (could be new category "feedback")
4. Specify assertions in test method

The skill is extensible - add new test methods to `test_chainlit_ui.py` and register in `_get_tests_to_run()`.

## 🔗 Related Resources

- [Playwright Docs](https://playwright.dev/) - Browser automation details
- [Chainlit Docs](https://docs.chainlit.io/) - App framework reference
- [Visual Regression Testing](https://playwright.dev/docs/test-snapshots) - Screenshot comparison patterns
- Project: `docs/development/v0.0.2-tasks.md` - Phase 11 feature specs

## 💡 Pro Tips

1. **Run after every UI change** - Catch regressions immediately
2. **Use focused test categories** - `welcome-screen` tests faster than `all`
3. **Keep baseline up-to-date** - Delete old baseline when intentionally changing UI
4. **Check the JSON report** - More details than text output
5. **Use with CI/CD** - Skill can be called from GitHub Actions

## 🚦 Success Criteria

Your UI/UX is in good shape when:

- ✅ All tests pass or are expected SKIPs
- ✅ Visual regression < 5%
- ✅ No FAIL status (only PASS, WARN, SKIP)
- ✅ Screenshots look good (review in `.chainlit-debug/screenshots/`)
- ✅ Response times < 500ms for interactions

---

**Created**: 2025-04-25
**Status**: Ready for Phase 11 UI/UX development
**Maintained by**: Claude Code
