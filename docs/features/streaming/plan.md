# Response Streaming (Task 11.12) — Plan

## What I'm Building

Token-by-token streaming of agent responses to the Chainlit UI. Instead of waiting for the full response, users see text appear as the model writes it — identical to how ChatGPT and similar tools behave.

## Why It Matters

Without streaming, the UI is frozen for 2–5 seconds while the model computes. With streaming, users see progress immediately and can start reading the answer while it is still being generated.

## Key Design Decisions

### Decision: `agent.run_stream()` instead of `agent.iter()` for the streaming path
**Chose**: `agent.run_stream()` + `result.stream_text(delta=True)`.
**Why**: PydanticAI's `run_stream()` streams the final text response token by token. Tool functions still execute normally and render their own `cl.Step()` blocks (جستجو، خواندن سند).
**Trade-off**: The synthetic "تحلیل سوال" planning step (which was generated from `CallToolsNode`) is no longer shown in streaming mode. Real tool steps still appear. This is an acceptable trade because: (a) the planning step was synthetic, not actual model reasoning; (b) seeing live text is a better UX signal than a fabricated planning summary.

### Decision: Non-streaming path unchanged
**Chose**: Keep `agent.iter()` + `agent.run()` for the non-streaming path.
**Why**: `enable_streaming: false` must produce identical output to the pre-streaming codebase. No regressions for users who need to disable streaming (e.g., because their LiteLLM proxy does not support SSE).

### Decision: Stream-then-update for citations
**Chose**: Stream raw text tokens, then format citations on the complete text and call `msg.update()`.
**Why**: Citation markers (`[1]`, `[2]`) can arrive as split tokens. Applying citation formatting during streaming would require buffering and lookahead. The two-phase approach (stream raw → update formatted) is simple and correct. The user sees a brief flash of `[1]` → `[1](url)` at the end, which is acceptable.

### Decision: `on_delta` callback in `LawAgent.run_streaming()`
**Chose**: Accept an async `Callable[[str], Awaitable[None]]` callback instead of yielding from a generator.
**Why**: Keeps the return type of `run_streaming()` identical to `run()` — both return `tuple[str, list[ModelMessage]]`. The caller (`app.py`) can inject any side effect (Chainlit streaming, logging, testing) without coupling `core.py` to Chainlit.

### Decision: `enable_streaming` flag in config.yaml
**Chose**: `ui.enable_streaming: true` default.
**Why**: The model (`grok-4-1-fast-reasoning`) goes through LiteLLM which proxies SSE streaming. Setting `false` reverts to the pre-streaming behavior for operators whose proxy or model does not support streaming.

## Model Streaming Support

The current model (`grok-4-1-fast-reasoning`) is accessed via a LiteLLM proxy (`LLM_BASE_URL`). LiteLLM supports SSE streaming for most major models. xAI Grok models support streaming via their API. If streaming fails with a proxy error, set `enable_streaming: false` in `config.yaml`.

## Verification

- **Tests**: `pytest tests/ui/test_streaming.py -v` — 6 tests covering `run_streaming()` internals and the `app.py` streaming/non-streaming branches
- **Visual check**: Start server → ask a question → verify text appears token by token
- **End-to-end**: Text streams live → tool steps appear during processing → citations appear formatted at end

## Success Criteria

- [x] `enable_streaming: true` in config.yaml (default on)
- [x] `run_streaming()` method calls `on_delta` for each token
- [x] Streaming path: empty `cl.Message` sent first → tokens streamed → `msg.update()` with citations
- [x] Non-streaming path: unchanged `agent.run()` → `cl.Message(formatted).send()`
- [x] 6 new tests, all passing; full suite 294 passed
