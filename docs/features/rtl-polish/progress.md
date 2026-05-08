# RTL Polish (Task 11.11) — Progress

## Session 1: 2026-05-08

**Goal**: Implement auto-direction detection, fix markdown RTL edge cases, polish mixed text rendering.

**Changes made**:
- `public/patch.css`: Added `li` to `direction: auto` selectors; added `unicode-bidi: embed; display: inline-block` to inline code within prose; added blockquote with `border-inline-start` (logical property); added RTL table support; added explicit `[dir="ltr"]` rule; added code isolation inside `[dir="rtl"]` containers
- `public/patch.js`: Added `detectPersianRatio()` counting `[؀-ۿ]` vs `[a-zA-Z]`; added `applyAutoDirection()` that sets `dir="rtl"` / `dir="ltr"` on `.prose` elements based on ratio; consolidated three MutationObserver callbacks into one `domObserver`

**Key decisions**:
- Threshold 30%/10% for Persian ratio → RTL/LTR/auto
- Used Unicode block `[؀-ۿ]` (U+0600–U+06FF) instead of narrower range for better coverage
- Skip elements already processed (`dataset.autoDir`) to avoid thrashing

**Tests**: 288 passed, 15 skipped — no regressions.

**For future developers**:
- The `dataset.autoDir` flag prevents re-processing; if streaming (task 11.12) is added, remove this flag or reset it when content updates
- The regex `[؀-ۿ]` covers Arabic/Persian Unicode block; if Urdu or other RTL scripts are needed, expand the range
- `border-inline-start` on blockquotes requires the parent `.prose` to have a resolved direction; the JS `applyAutoDirection()` ensures this happens
