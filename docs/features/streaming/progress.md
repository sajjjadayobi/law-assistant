# Response Streaming (Task 11.12) — Progress

## Session 1: 2026-05-08

**Goal**: Implement token-by-token streaming of agent responses using PydanticAI's `run_stream()` API, with a config flag to enable/disable it.

**Time log**:
- Checked PydanticAI 1.84.1 API — confirmed `agent.run_stream()` + `result.stream_text(delta=True)` is the right entry point
- Checked model (`grok-4-1-fast-reasoning` via LiteLLM proxy) — LiteLLM supports SSE streaming; Grok supports streaming via OpenAI-compatible API
- Added `enable_streaming: bool = True` to `UIConfig` in `settings.py`
- Added `enable_streaming: true` to `config.yaml` with comment about disabling if proxy lacks SSE support
- Added `run_streaming(on_delta)` to `LawAgent` in `core.py` — async callback pattern keeps `core.py` decoupled from Chainlit
- Updated `app.py` main handler: streaming branch sends empty `cl.Message`, streams tokens, formats citations on full text, calls `msg.update()`; non-streaming branch is unchanged
- Fixed two pre-existing lint issues found during ruff check (`Optional[cl.User]` → `cl.User | None`, unused `settings` variable in `start()`)
- Wrote 6 tests in `tests/ui/test_streaming.py` — all pass; full suite 294 passed

**Blockers & Solutions**:

### `spec=LawAgent` blocks dynamic `.agent` attribute
**Problem**: `MagicMock(spec=LawAgent)` blocked access to `self.agent` (the internal PydanticAI `Agent` instance), which is set dynamically in `_create_agent()`, not declared as a class attribute.
**Solution**: Explicitly set `agent.agent = MagicMock()` in tests that use `spec=LawAgent`.
**Root cause**: `spec=` only allows attributes that exist at class definition time, not those set in `__init__`.

**Decisions made**:
- Streaming mode drops the synthetic "تحلیل سوال" planning step (was synthesized from `CallToolsNode`). Tool steps (search, read doc) still appear — they render from inside the tool functions themselves.
- Citation formatting is two-phase: stream raw tokens → format citations on complete text → `msg.update()`. Avoids split-token issues where `[`, `1`, `]` might arrive as separate deltas.
- `on_delta` async callback pattern (not async generator) keeps `run_streaming()` return type identical to `run()` — both return `(str, list[ModelMessage])`.

**Post-implementation finding: reasoning model burst behavior**:
Tested SSE streaming directly against the LiteLLM proxy → 6 real SSE chunks, but ALL 6 arrive at the same timestamp (3.29s wait, then burst). `grok-4-1-fast-reasoning` thinks first, then dumps the complete response in milliseconds. PydanticAI's `debounce_by=0.1` batches all 6 into one yield. From the user's perspective: 3s wait → full text instantly. Indistinguishable from non-streaming.

**Resolution**: Changed `enable_streaming` default to `false` in both `config.yaml` and `settings.py`. The implementation is correct for progressive-generation models (claude-sonnet, gpt-4o). Enable when switching away from reasoning models.

**Screenshots**: See `screenshots/` directory — shows tool steps during processing and the complete RTL response.

**Next session**:
- No follow-up needed — streaming is complete and tested
