# LLM Provider: MetisAI — Progress

## Session: 2026-05-14

**Goal**: Switch LLM backend to MetisAI and get the agent working end-to-end.

---

## Blockers & Solutions

### Blocker 1: Wrong base URL
**Problem**: `LLM_BASE_URL` was set to `https://api.metisai.ir` (root), which has no chat endpoint.
**Solution**: Set to `https://api.metisai.ir/openai/v1` (their documented OpenAI-compatible route).

### Blocker 2: Default timeout too short
**Problem**: `OpenAIModel` default timeout (~10s) caused `APITimeoutError` on first request. MetisAI typically takes 8–10s to respond.
**Solution**: Pass `httpx.AsyncClient(timeout=30.0)` to `OpenAIProvider`.

### Blocker 3: `OpenAIModel` doesn't accept `api_key` / `http_client` directly
**Problem**: Passing `api_key` and `http_client` to `OpenAIModel.__init__()` raised `TypeError: unexpected keyword argument`.
**Solution**: Pass them to `OpenAIProvider` instead, then pass the provider to `OpenAIModel`.

### Blocker 4: `/wrapper/grok` does not support function calling
**Problem**: MetisAI's Grok wrapper endpoint (`/api/v1/wrapper/grok`) explicitly does not support function calling. The first request (tool definitions) went through, but the second (tool results) returned 400 or connection error.
**Solution**: Switched endpoint to `/openai/v1` which uses GPT models with full tool calling support.

### Blocker 5: `"strict": true` rejected by MetisAI proxy
**Problem**: PydanticAI sends `"strict": true` in tool schemas (an OpenAI-specific extension). MetisAI's proxy rejected it with a connection error.
**Solution**: `OpenAIModelProfile(openai_supports_strict_tool_definition=False)` — removes `strict` cleanly without patching.

### Blocker 6: `model_not_supported` on `/openai/v1`
**Problem**: Model name `grok-4-1-fast` is not available on the `/openai/v1` endpoint (GPT-only route).
**Solution**: Queried `/openai/v1/models` to find available models. Tested tool calling on all candidates. Confirmed `gpt-4o`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`, `gpt-4-turbo`, `gpt-4` all work. Chose `gpt-4.1-mini`.

---

## Final State

**`.env`**:
```
LLM_BASE_URL="https://api.metisai.ir/openai/v1"
LLM_AUTH_TOKEN="..."
```

**`config.yaml`**:
```yaml
model:
  name: "gpt-4.1-mini"
```

**`core.py`** (`_create_agent`):
```python
http_client = httpx.AsyncClient(timeout=30.0)
provider = OpenAIProvider(
    base_url=self.settings.model.base_url,
    api_key=self.settings.model.auth_token,
    http_client=http_client,
)
profile = OpenAIModelProfile(openai_supports_strict_tool_definition=False)
model_instance = OpenAIModel(model_name=self.model, provider=provider, profile=profile)
```

---

## Key Learnings

1. **MetisAI has two separate routes** — `/wrapper/*` (per-model, no tools) and `/openai/v1` (GPT models, full OpenAI compatibility including tools). Always use `/openai/v1` for agentic use cases.
2. **`OpenAIProvider` is the right layer** for custom base URL, API key, and http client — not `OpenAIModel` directly.
3. **`OpenAIModelProfile(openai_supports_strict_tool_definition=False)`** is the clean way to handle non-OpenAI providers that reject `strict: true` in tool schemas.
4. **Test tool calling explicitly** before assuming an endpoint supports it — a successful simple chat completion does not guarantee tool calling works.
5. **Query `/models`** to discover what model names are valid on a given endpoint before configuring.

---

## Models with Tool Calling on MetisAI `/openai/v1`

| Model | Tool Calling |
|---|---|
| `gpt-4.1` | ✅ |
| `gpt-4.1-mini` | ✅ (current) |
| `gpt-4.1-nano` | ✅ |
| `gpt-4o` | ✅ |
| `gpt-4o-mini` | ✅ |
| `gpt-4-turbo` | ✅ |
| `gpt-4` | ✅ |
| `gpt-3.5-turbo` | ❌ |
