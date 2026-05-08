# Task 11.3: Thinking Steps Visualization — Plan

**Date**: 2026-05-07
**Reference**: `docs/development/v0.0.2-tasks.md` § Task 11.3

---

## What We're Building

Show the AI's reasoning and search process as collapsible steps in the chat UI — before the final answer arrives. The user sees the agent "thinking" and searching in real time, which keeps them engaged during the 20–40 second wait.

Target UX (matching data-assistant):

```
User question
  ↓
  تحلیل سوال ∨          ← thinking/planning (collapsed)
  جستجو — 5 سند پیدا شد ∨  ← search results (collapsed, expandable)
  خواندن سند — ماده ۷۶ قانون کار ∨  ← doc read (collapsed)
  [more steps as agent hops...]
  ↓
Final Persian legal answer
```

---

## Key Design Decisions

### 1. Steps appear BEFORE the answer (not after)

**Decision**: Remove `msg.send()` upfront in `on_message`. Run `agent.run()` first — which creates steps — then send `cl.Message()` at the end.

**Why this matters**: In the old code, an empty placeholder message was sent first, then the agent ran. This put steps *after* the placeholder in Chainlit's render order. Moving `cl.Message().send()` to the end means steps are rendered before the answer.

**Alternative considered**: Keep the placeholder for immediate feedback. Rejected — the steps themselves appear immediately as each tool fires, so the user sees activity within 5–10 seconds.

### 2. Two distinct step types

| Step | Chainlit type | When shown | Name pattern |
|------|---------------|------------|--------------|
| Thinking | `tool` | When `CallToolsNode` fires | "تحلیل سوال" |
| Search | `retrieval` | Inside each tool | "جستجو — N سند پیدا شد" |
| Doc read | `retrieval` | Inside each tool | "خواندن سند — {title}" |
| Related | `retrieval` | Inside each tool | "اسناد مرتبط — N سند" |

`retrieval` renders with a different icon than `tool` in Chainlit — gives visual distinction.

### 3. Dynamic step names (result-based)

Step names update AFTER the tool call completes to show the actual result. Start with "در حال جستجو ..." and update to "جستجو — 4 سند پیدا شد". This gives real-time feedback.

### 4. No "استفاده شد" suffix

Chainlit appends a localised "Used" string to every completed step name. Cleared this to empty in `fa-IR.json` so step names stand alone cleanly.

### 5. cl.Step context manager (not @cl.step decorator)

**Decision**: Use `async with cl.Step(...) as step:` inside each tool, not `@cl.step` decorator.

**Why**: `@cl.step` on a sync function doesn't reliably send WebSocket events in an async context. The explicit async context manager always works. The decorator form also makes it harder to update `step.name` dynamically after the result is known.

### 6. Thinking step shows planning intent

Since our LiteLLM-proxied model returns only `ToolCallPart` (no text alongside tool calls), there's no actual "thinking text" to show. The thinking step instead lists what tools are about to be called:

```
برای پاسخ به سوال شما:
- جستجو در قوانین
- مطالعه سند
```

---

## Files Modified

| File | Change |
|------|--------|
| `src/law_agent/agent/core.py` | Switch `agent.run()` → `agent.iter()`, add `show_thinking()`, add `cl.Step` in all 3 tools |
| `src/law_agent/ui/app.py` | Move `cl.Message().send()` to after `agent.run()` |
| `.chainlit/translations/fa-IR.json` | Set `messages.status.used` and `using` to `""` |
| `migration/add_chainlit_tables_camelcase.sql` | Add `"defaultOpen"` column to steps table |

---

## Success Criteria

- [x] Steps appear BEFORE the final answer
- [x] "تحلیل سوال" step appears when agent plans tool calls
- [x] "جستجو — N سند پیدا شد" shows actual search count
- [x] "خواندن سند — {title}" shows actual document name
- [x] "اسناد مرتبط — N سند" shows related document count
- [x] No "استفاده شد" suffix on any step
- [x] Steps are collapsible with expand/collapse chevron
- [x] Steps appear in real time (not all at once at the end)
- [x] Works with the LiteLLM-proxied model (no actual ThinkingPart in responses)
