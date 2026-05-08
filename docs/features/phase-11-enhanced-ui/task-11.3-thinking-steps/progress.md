# Task 11.3: Thinking Steps Visualization — Progress

**Start**: 2026-05-07
**Complete**: 2026-05-08
**Status**: ✅ DONE

---

## Summary

Implemented collapsible thinking + tool-call steps that appear **before** the final answer, matching the data-assistant UX. Steps are distinct by type, have dynamic result-based Persian labels, and "استفاده شد" suffix is removed. Also fixed citations (HTML → markdown), added راهنما page, sidebar closed by default, logo redesigned.

---

## Root Cause Analysis — Six Problems Solved

### Problem 1: `@cl.step` on sync function doesn't render in UI

**Symptom**: `create_step` logged in DB, "در حال فکر کردن" never appeared in browser DOM.

**Root cause**: `@cl.step def show_thinking()` — a sync function decorated with `@cl.step` in an async context doesn't reliably fire the WebSocket event to the frontend. The step is persisted to DB but the UI never receives it.

**Fix**:
```python
# ❌ Doesn't work
@cl.step(name="...", type="tool")
def show_thinking(text_parts): ...

# ✅ Works every time
async def show_thinking(text_parts):
    async with cl.Step(name="...", type="tool", show_input=False) as step:
        step.output = "\n".join(text_parts)
```

---

### Problem 2: Model emits only `ToolCallPart` — no text to show as "thinking"

**Symptom**: `CallToolsNode` fires, but `thinking_parts` and `text_parts` are always empty.

**Root cause**: Our LiteLLM-proxied model (via `OpenAIModel`) returns only tool call parts with no accompanying text. The "thinking text" pattern requires extended thinking or parallel text+tool models.

**Fix**: Added a third branch — when the model has tool parts but no text, synthesise a planning description from the tool names:
```python
elif has_tool_part:
    lines = ["برای پاسخ به سوال شما:"] + [f"- {label}" for label in tool_labels]
    await show_thinking(lines)
```

---

### Problem 3: Steps appeared AFTER the final answer

**Symptom**: Tool/thinking steps rendered below the agent response in the chat.

**Root cause**: The handler called `msg.send()` (empty placeholder) before `agent.run()`. Chainlit renders in creation order — the placeholder was created before all tool steps, so it displayed above them.

**Fix**: Remove the upfront `msg.send()`. Run the agent first, then send `cl.Message()` at the end:
```python
# ❌ Placeholder first = steps end up after the answer
msg = cl.Message(content=""); await msg.send()
response = await agent.run()
msg.content = response; await msg.update()

# ✅ Steps first = answer comes last
response = await agent.run()         # steps created here
await cl.Message(content=response).send()
```

---

### Problem 4: "استفاده شد" suffix on every step

**Symptom**: Steps displayed as "جستجوی اسناد حقوقی استفاده شد ∨" instead of just their name.

**Root cause**: Chainlit appends the `messages.status.used` translation key to every completed step label. We had set it to `"استفاده شد"` in `fa-IR.json`.

**Fix**: Set both `using` and `used` to `""` in `.chainlit/translations/fa-IR.json`:
```json
"status": { "using": "", "used": "" }
```

---

### Problem 5: steps table missing `"defaultOpen"` column

**Symptom**: `asyncpg.exceptions.UndefinedColumnError: column "defaultOpen" of relation "steps" does not exist` — steps failed to persist, no UI render.

**Fix**:
```sql
ALTER TABLE steps ADD COLUMN IF NOT EXISTS "defaultOpen" BOOLEAN DEFAULT FALSE;
```
Also added to `migration/add_chainlit_tables_camelcase.sql`.

---

### Problem 6: Citations rendered as raw HTML

**Symptom**: `<a href="..." style="...">  [1]  </a>` shown as raw text in the chat. Also `[doc_id: X]` leaked into the reference section display.

**Root cause**: Chainlit has `unsafe_allow_html = false`, so HTML tags are displayed as text. The citation formatter was generating `<a>` tags. Also the system prompt example introduced a literal `"— doc_id"` string in the reference format.

**Fix**:
- `citations.py`: Replace HTML link generation with markdown: `[1](https://iran.ir/en/law/{doc_id})`
- Parse `[doc_id: X]` from reference lines to extract the actual doc_id for the URL
- Strip `[doc_id: X]` and trailing dashes from displayed reference text
- `system_prompt.yaml`: Fix the example format to not include `"— doc_id"` literal text

---

## Key Learnings for Future Developers

| # | Learning | Why it matters |
|---|----------|----------------|
| 1 | Always use `async with cl.Step()` — never `@cl.step` on sync functions | Sync decorated steps don't reliably send WebSocket events |
| 2 | Send `cl.Message()` AFTER `agent.run()` | Steps are rendered in creation order — message first = message above steps |
| 3 | Update `step.name` inside the context manager | Lets you show "در حال جستجو ..." → "جستجو — 4 سند پیدا شد" |
| 4 | `steps` table needs `"defaultOpen"` BOOLEAN column | `cl.Step()` always includes it in the INSERT |
| 5 | Set `messages.status.used = ""` in translation | Removes the "استفاده شد" suffix from step labels |
| 6 | `unsafe_allow_html = false` in Chainlit — use markdown links | HTML in responses is shown as raw text |
| 7 | Check model output parts before assuming ThinkingPart exists | LiteLLM-proxied models may only emit ToolCallPart |
| 8 | System prompt citation format must not contain literal "doc_id" text | Agent copies examples verbatim — be precise about the format |

---

## Additional Changes in This Task

Beyond thinking steps, the following polish items were completed:

- **راهنما page** (`chainlit.md`): Full Persian help page with usage tips, examples, disclaimer
- **Sidebar closed by default**: `default_sidebar_state = "closed"` in `.chainlit/config.toml`
- **Citation fix**: Markdown links using real `doc_id`, `[doc_id: X]` stripped from display
- **"سوالات بیشتر:" header**: System prompt now instructs agent to use this header for follow-up questions
- **Logo redesign**: Bolder scales with cleaner proportions and elegant pan arcs
- **Translations**: Only `en-US.json` and `fa-IR.json` kept in project; all other languages removed
- **Tool step labels**: Dynamic — "در حال جستجو ..." → "جستجو — N سند پیدا شد" after result
- **"— None" dates removed**: `filter(None, [...])` strips absent dates from doc step output

---

## Screenshots

| File | Shows |
|------|-------|
| `1_thinking_during_processing.png` | تحلیل سوال + جستجو steps while agent processes |
| `2_thinking_with_response.png` | Steps collapsed under final answer |
| `3_final_response_view.png` | Final answer arrives after all steps |
| `4_search_step_expanded.png` | Expanded "جستجو — N سند پیدا شد" with document list |
