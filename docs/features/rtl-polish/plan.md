# RTL Polish (Task 11.11) — Plan

## What I'm Building

Improved right-to-left text rendering for the Persian legal assistant UI. Focuses on three areas: more reliable direction auto-detection via JS, proper RTL rendering of markdown elements (blockquotes, tables), and correct LTR isolation for inline code within Persian paragraphs.

## Why It Matters

The app is Persian-first. All agent responses are in Persian. Without reliable RTL, text may render left-aligned, blockquote borders appear on the wrong side, and inline code disrupts sentence flow in RTL paragraphs.

## Key Design Decisions

### Decision: JS direction detection alongside CSS `direction: auto`
**Chose**: Count Persian vs Latin characters in `.prose` elements and set `dir` attribute based on ratio.
**Why**: CSS `direction: auto` only uses the **first** strongly-typed character. If a paragraph starts with a number, punctuation, or a Latin technical term, the entire block goes LTR. Counting characters over the full text is far more reliable for mixed-content Persian responses.
**Alternatives**: Pure CSS — insufficient for the first-character edge case. Server-side detection — overkill; the CSS/JS approach handles it without backend changes.

### Decision: CSS logical properties for blockquotes and lists
**Chose**: `border-inline-start`, `padding-inline-start`, `margin-inline-start` throughout.
**Why**: Logical properties automatically map to the correct physical side based on the element's computed direction (RTL or LTR). No separate RTL/LTR rule variants needed.
**Alternatives**: Separate `[dir="rtl"]` and `[dir="ltr"]` overrides — more verbose and error-prone.

### Decision: Consolidate into one MutationObserver
**Chose**: Replace the two separate observers (`observer` for placeholder, `copyObserver` for copy buttons) with a single `domObserver` that calls all three functions.
**Why**: Reduces DOM listener overhead; simpler reasoning about when callbacks fire.

### Decision: Threshold of 30% Persian for RTL
**Chose**: `ratio > 0.3` → RTL, `ratio < 0.1` → LTR, otherwise leave as CSS auto.
**Why**: Legal responses always have ≥50% Persian characters. The 30% threshold catches even sparse Persian text. The 10% lower bound avoids flipping clearly-Latin content. Mixed content (code-heavy paragraphs) falls through to CSS `direction: auto` which is the correct default for ambiguous cases.

## Verification

- **Tests**: `make test` — no new tests needed (pure CSS/JS, no Python behavior changes)
- **Visual check**: Start server, send a Persian query with inline code, verify response is right-aligned; check that code blocks remain LTR
- **End-to-end**: Response with Persian text → `dir="rtl"` on `.prose` → text right-aligned; blockquote border on right; list bullets on right; inline code stays LTR

## Success Criteria

- [x] Persian-only responses reliably render RTL (not just when first char happens to be Persian)
- [x] Inline `` `code` `` within Persian sentences stays LTR via `unicode-bidi: embed`
- [x] Blockquote accent border appears on the right for RTL content
- [x] Tables render with RTL column alignment
- [x] All existing tests pass
