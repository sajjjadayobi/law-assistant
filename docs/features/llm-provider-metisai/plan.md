# LLM Provider: MetisAI — Plan

## What I'm Building
Switch the LLM backend from a direct Anthropic endpoint to MetisAI (`api.metisai.ir`), an Iranian proxy service that provides access to multiple LLM providers.

## Key Design Decisions

### Decision: Use `/openai/v1` not `/wrapper/grok`
**Chose**: `https://api.metisai.ir/openai/v1`
**Why**: MetisAI has two routes. `/wrapper/grok` has Grok models but explicitly does not support function calling. `/openai/v1` is their full OpenAI-compatible endpoint with GPT-4.1/4o models that support tool calling.
**Alternatives**: `/wrapper/grok` — rejected because the agent requires tool calling to search the legal database.

### Decision: `gpt-4.1-mini` as default model
**Chose**: `gpt-4.1-mini`
**Why**: Fast, capable, supports tool calling, good balance of cost and quality for legal Q&A.
**Alternatives**: `gpt-4.1` (smarter but slower), `gpt-4o` (comparable quality), `gpt-4.1-nano` (too lightweight for complex legal reasoning).

### Decision: `OpenAIProvider` + `OpenAIModelProfile`
**Chose**: PydanticAI's `OpenAIProvider` with `openai_supports_strict_tool_definition=False`
**Why**: Cleanly configures a custom base URL, API key, and timeout without monkey-patching. The `strict: false` profile removes the `"strict": true` field from tool schemas that non-OpenAI providers may reject.

## Credentials (in `.env`, never hardcoded)
- `LLM_BASE_URL`: `https://api.metisai.ir/openai/v1`
- `LLM_AUTH_TOKEN`: MetisAI bearer token

## Success Criteria
- [ ] Agent calls tools (search, get_document, get_related_documents) successfully
- [ ] Multi-turn conversation with tool results works end-to-end
- [ ] Persian legal questions answered correctly
