# Phase 6 + 11: Observability — Plan (retrospectively updated 2026-05-09)

> **Retrospective note**: This document merges the original Phase 6 plan (written before implementation) with decisions made during Sessions 2–3 (2026-05-08/09). Sections marked `[REVISED]` or `[ADDED]` reflect what was actually built vs. the original design. Sections marked `[DEFERRED]` were planned but not implemented.

---

# Phase 6: Observability & Eval-Driven Development - Original Plan

## What I'm Building

A complete observability and evaluation system for the Law Agent using:
1. **Arize Phoenix**: Self-hosted observability platform capturing all agent conversations, token usage, and feedback
2. **OpenTelemetry**: Distributed tracing of agent execution (search tools, LLM calls, decisions)
3. **Evaluation Framework**: Golden eval set (50 QA pairs) + LLM-as-judge grading for continuous improvement
4. **Feedback Loop**: User feedback → Phoenix → Error Analysis → Prompt Improvement

This transforms the application from a working prototype into a **production-grade system** with built-in continuous improvement.

## Why This Matters

**Phase 5 delivered a working UI**, but without observability we can't:
- See what queries fail or why
- Track token usage and costs
- Identify patterns in user feedback
- Measure improvement from prompt changes
- Build data-driven feature roadmaps

**Phase 6 enables**:
- Complete visibility into agent behavior (every search, tool call, decision)
- Data-driven iteration (measure → analyze → improve → measure)
- Cost and performance analytics
- Error detection and rapid response
- Confidence that changes improve quality (not luck)

## Key Design Decisions

### Decision 1: Arize Phoenix for Observability
**Decision**: Use Arize Phoenix (self-hosted) as observability platform
**Why**:
- Self-hosted = no external dependencies, no data leaving our infrastructure
- Native OpenTelemetry support (industry standard tracing)
- PydanticAI instrumentation built-in
- Token usage and cost tracking out-of-the-box
- Excellent for agent debugging (see exact tool call sequence, parameters, failures)
- Dashboard + API for programmatic access

**Alternatives Considered**:
- LangFuse: Good but more focused on LLM logging, less on agent traces
- LangSmith: Requires account, vendor lock-in
- Custom ELK stack: Too much infrastructure for MVP
- Datadog/New Relic: Overkill, expensive for development

**Trade-offs**:
- Adds infrastructure (Docker container)
- Learning curve (OpenTelemetry concepts)
- Another service to monitor (but worth the insight)

### Decision 2: OpenTelemetry for Distributed Tracing
**Decision**: Use Python OpenTelemetry SDK with OTLP exporter to Phoenix
**Why**:
- Industry standard (not vendor-specific)
- Automatic instrumentation for common libraries
- Can instrument custom code (tool calls, search, decisions)
- Low overhead, async-friendly
- Captures: execution time, parameters, results, errors, status

**Alternatives Considered**:
- Custom logging to Phoenix: Rejected - reinventing the wheel
- Direct HTTP calls to Phoenix: Rejected - less flexible, more coupling
- DataDog SDK: Rejected - vendor lock-in

**Trade-offs**:
- More infrastructure (OpenTelemetry collector, exporter)
- Need to learn OTEL concepts (spans, attributes, events)
- Slightly higher code complexity (decorators, context managers)

### Decision 3: Token Usage Tracking
**Decision**: Capture input/output tokens from Claude API, calculate costs, store in OTEL attributes
**Why**:
- Anthropic API returns token counts in response
- Can calculate cost: (input_tokens × $3/$1M) + (output_tokens × $15/$1M)
- Store in span attributes for Phoenix analytics
- Enables cost optimization (see expensive queries, refine prompts)

**Alternatives Considered**:
- Estimate from text length: Rejected - inaccurate, API gives exact counts
- Only track at conversation level: Rejected - need per-tool detail
- Store in database: Rejected - OTEL attributes sufficient

**Trade-offs**:
- Requires Anthropic API client integration
- Token counts per tool call (more granular data)
- Need to correlate with response quality (expensiveness vs usefulness)

### Decision 4: Eval-Driven Development with Golden Set
**Decision**: Build 50 QA pairs from:
- 30 real user queries (from production or test data)
- 10 edge cases (ambiguous, contradictory law, out-of-scope)
- 10 negative cases (should refuse or clearly state "not in database")

**Why**:
- 50 pairs is achievable, not too large
- Real queries are most important (representative of actual usage)
- Edge cases find failure modes
- Binary pass/fail grading (simple, robust)
- Can run in CI/CD, measure regressions

**Alternatives Considered**:
- Build 200+ pairs: Rejected - too much work, diminishing returns
- Use only synthetic data: Rejected - doesn't match real usage
- Numerical scoring (1-5 stars): Rejected - ambiguous, hard to automate
- Only run locally: Rejected - need to catch regressions before deployment

**Trade-offs**:
- Building golden set takes time (1-2h per 10 pairs with domain expert)
- Binary pass/fail misses nuance (mitigation: add pass/fail reasoning)
- Eval set maintenance needed as product changes (like tests)

### Decision 5: LLM-as-Judge for Automated Grading
**Decision**: Use Claude Sonnet to grade eval set answers automatically
**Why**:
- Subjective evaluation (is answer correct, well-sourced, in right language?)
- Human expert defines pass criteria (clear definition of "good")
- LLM judge learns from human examples (few-shot prompting)
- Can run without human in loop (10x faster iteration)
- Provides reasoning (not just score)

**Alternatives Considered**:
- Only human evaluation: Rejected - too slow, can't iterate fast
- Simple regex/code checks: Rejected - can't evaluate answer quality
- Human + automated hybrid: Selected as Phase 2 (first align human-judge)

**Trade-offs**:
- Judge needs alignment with human expert (build in examples)
- Judge can hallucinate (mitigate with clear rubric, "Unknown" option)
- Bias toward certain answer styles (monitor for overfitting)
- Cost per eval (~0.002 × 50 = $0.10 per full run)

### Decision 6: Error Analysis → Improvement Loop
**Decision**: Regular cycle of:
1. Analyze failed evals in Phoenix
2. Group failures by type (search didn't find docs, wrong tool choice, bad synthesis, etc.)
3. Fix highest-impact category (search quality → tool choice → prompt clarity)
4. Re-run evals, measure improvement
5. Document learnings

**Why**:
- Data-driven: Fix what actually fails, not what we think fails
- Prioritized: Fix highest-impact problems first
- Measurable: Eval score goes up = improvement confirmed
- Repeatable: Process is systematic, not ad-hoc

**Alternatives Considered**:
- Change prompts randomly: Rejected - no feedback loop
- Only use user feedback: Rejected - slow, biased toward loud users
- Manual code review: Rejected - doesn't catch subtle issues
- A/B testing in production: Rejected - too slow for MVP, risky

**Trade-offs**:
- Requires discipline (can't ship without running evals)
- Error analysis is manual (reading traces, finding patterns)
- Eval score changes may be noisy (run multiple times)

### Decision 7: Phoenix Architecture
**Decision**: Docker Compose with single Phoenix container (development), upgrade to multi-container for production
**Why**:
- Single container sufficient for MVP (captures all traces)
- Data persists in local volume
- Can delete and recreate cleanly
- UI at localhost:6006 easy to access
- Docker Compose familiar to developers

**Alternatives Considered**:
- Kubernetes: Rejected - overkill for MVP
- Managed service (Datadog, etc.): Rejected - external dependency
- Local SQLite: Rejected - limited querying, worse UI

**Trade-offs**:
- Single container is not highly available (acceptable for development)
- Shared container for all storage (not ideal for 100TB+ data)
- Local volume storage (not backed up, need manual backup process)

## Success Criteria

- [x] Phoenix running locally at localhost:6006 (Docker or native)
- [x] Agent instrumented with OpenTelemetry (spans visible in Phoenix UI)
- [x] All agent activities traced: search_documents, get_document, get_related_documents, LLM calls
- [x] Token usage tracked on CHAIN span (from PydanticAI usage object)
- [x] Conversation traces include: user query, tool calls, full response, execution time, session ID
- [x] Chainlit feedback (👍/👎) sent to Phoenix as span annotation + span note
- [x] Feedback comment stored in Phoenix Notes panel (visible as chat bubble)
- [x] Tool output shows actual document titles/IDs (not generic counts)
- [x] get_document output includes full document content for eval review
- [x] No DB connection spans polluting traces (SQLAlchemy uninstrumented)
- [x] "law-agent" project used consistently (no "default" project pollution)
- [x] 10 new unit tests for observability (304 total)
- [ ] [DEFERRED] Phoenix dashboard with aggregated metrics
- [ ] [DEFERRED] Error tracking and alerts configured
- [ ] [DEFERRED] Golden eval set created (50 QA pairs)
- [ ] [DEFERRED] LLM-as-judge evaluator implemented
- [ ] [DEFERRED] LLM span cost display (requires knowing LiteLLM proxy pricing)

---

## What Was Actually Built vs. Original Plan `[REVISED]`

### What changed from the plan

**Original plan assumed**:
- PydanticAI had built-in Phoenix instrumentation (`Agent(instrument=True)`)
- `openinference-instrumentation-openai` would be used for LLM tracing
- SQLAlchemy instrumentation would provide useful DB performance data
- Eval framework (golden set + LLM-as-judge) would be built in same phase

**What actually happened**:
- `Agent(instrument=True)` does not exist in PydanticAI — instrumentation is manual
- `openinference-instrumentation-openai 0.1.44` incompatible with `opentelemetry 0.62b1` — switched to `opentelemetry-instrumentation-openai 0.60.0` (Traceloop)
- SQLAlchemy instrumentation created 800+ useless "connect" spans — explicitly removed AND uninstrumented (Traceloop re-enables it)
- Eval framework deferred — observability itself took 2 full sessions to get right

### New decisions made in implementation

| Decision | Chosen | Why |
|---|---|---|
| Project name | `PHOENIX_PROJECT_NAME=law-agent` env var | Prevents "default" project pollution from Traceloop auto-init |
| DB instrumentation | Explicitly uninstrument SQLAlchemy after OpenAIInstrumentor | Traceloop re-enables it despite removal from our code |
| CHAIN span token counts | From PydanticAI `result.usage()` after iter completes | Only way to get total across all LLM calls |
| Feedback storage | annotation (label+score+explanation+metadata) + note (comment text) | Notes panel is more visible than annotation explanation |
| Note content | Comment text only, no username/emoji | Keep Notes clean for evaluators |
| LLM span cost | Not implemented — $0 | Model name (grok-4-1-fast-reasoning) not in Phoenix pricing; LiteLLM proxy pricing unknown |
| Tool output | Titles/IDs list for search, full content for get_document | Evaluators need to see exactly what the agent retrieved |

### Key technical gotchas discovered `[ADDED]`

1. **`openinference-instrumentation-openai` API break**: `wrap_function_wrapper()` signature changed in `opentelemetry-instrumentation 0.62b1` — the `module` keyword arg no longer accepted. Switch to `opentelemetry-instrumentation-openai 0.60.0` from Traceloop.

2. **Traceloop auto-init**: `OpenAIInstrumentor().instrument()` triggers broader auto-instrumentation including SQLAlchemy. Must set `OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=sqlalchemy,psycopg2` AND call `SQLAlchemyInstrumentor().uninstrument()` after.

3. **Phoenix project routing**: All libraries using `phoenix.otel` default to "default" project unless `PHOENIX_PROJECT_NAME` env var is set before any instrumentation.

4. **`batch=False` for dev**: `SimpleSpanProcessor` (not `BatchSpanProcessor`) needed for immediate span delivery during development. With batch, spans may not appear for 5+ seconds.

5. **OTel span context in asyncio**: `trace.get_current_span()` inside `core.py`'s `run()` correctly returns the `user_turn` span created in `app.py` — asyncio propagates OTel context via `contextvars` automatically.

6. **Phoenix Notes API**: `POST /v1/span_notes` is separate from annotations. Allows multiple notes per span, shown as chat bubbles. Annotation explanation is stored but hidden in table view — Notes are more user-friendly for human evaluators.

7. **`BoundedAttributes` mutation**: After span ends, `span.set_attribute()` is blocked (`is_recording()` returns False) but `span._attributes["key"] = value` works — `BoundedAttributes` allows direct item assignment. This is how the LLM bridge exporter was prototyped (not shipped).

8. **Phoenix "default" project cannot be deleted**: The API returns 403 or error. Delete its contents via SQLite instead: `DELETE FROM spans WHERE trace_rowid IN (SELECT id FROM traces JOIN projects...)`.

### Span hierarchy reference

```
user_turn (CHAIN)
  openinference.span.kind = "CHAIN"
  input.value              = user question (Persian)
  output.value             = agent response (Markdown)
  session.id               = Chainlit session UUID
  llm.token_count.prompt   = total request tokens across all LLM calls
  llm.token_count.completion = total response tokens
  llm.model_name           = model name from config
  ├── openai.chat (unknown) — LLM planning call
  │     gen_ai.input.messages  = system prompt + history
  │     gen_ai.output.messages = tool call requests
  │     gen_ai.usage.*         = per-call token counts
  ├── search_documents (TOOL)
  │     input.value  = {"query": "...", "tags": [], "doc_types": [...], "limit": N}
  │     output.value = "[101] قانون کار (law)\n[202] آیین‌نامه... (regulation)"
  ├── openai.chat (unknown) — LLM reasoning over results
  ├── get_document (TOOL)
  │     input.value  = {"doc_id": 12345}
  │     output.value = "[12345] Title\ntype | date\n\nsummary...\n\n---\nfull content..."
  ├── get_related_documents (TOOL)
  │     input.value  = {"doc_id": ..., "relation_types": [], "limit": N}
  │     output.value = "[301] Related Title (regulation)"
  └── openai.chat (unknown) — final answer generation

Phoenix annotations on user_turn span:
  user_feedback | HUMAN | thumbs_up/thumbs_down | score 1.0/0.0
  explanation = user_comment + "[سوال] question + "[پاسخ] response_preview"
  metadata = {session_id, user, user_comment, question, response_preview}

Phoenix notes on user_turn span:
  note = user_comment (only the comment text, nothing else)
```

## Dependencies

**Requires**:
- Phase 5 complete (UI with Chainlit) ✅
- Docker and Docker Compose installed
- Anthropic API key (for Claude calls, already configured)
- PostgreSQL database (already running)

**Blocks**:
- Phase 7 (Testing & CI/CD) - evals integrated into CI pipeline
- Phase 8 (Deployment) - observability configured for production

**Related**:
- `docs/best-practices/evaluation.md`: Eval-driven development guide
- `docs/architecture/search.md`: Agent behavior reference
- Phase 5 UI: Feedback integration point
- CLAUDE.md: Development guidelines, quick reference

## Architecture Overview

```
User Query
    ↓
Chainlit UI
    ↓
Law Agent (PydanticAI)
    ├─ search_documents [TRACE: search params, query time, result count]
    ├─ get_document [TRACE: doc_id, fetch time, content size]
    ├─ get_related_documents [TRACE: relations, graph traversal]
    └─ LLM Call (Claude) [TRACE: prompt tokens, output tokens, latency]
    ↓
Response + Citations
    ↓
Chainlit UI ← Feedback (👍/👎)
    ↓
OpenTelemetry Exporter (OTLP)
    ↓
Arize Phoenix
    ├─ Trace Storage (conversation, tool calls, decisions)
    ├─ Feedback Storage (user feedback linked to traces)
    ├─ Token Analytics (input/output, cost estimation)
    └─ Dashboard (key metrics, error analysis, feedback trends)

Evaluation Loop:
Golden Set (50 QA)
    ↓
Run Agent on Each Query
    ↓
Capture Response
    ↓
LLM-as-Judge Grading (pass/fail + reasoning)
    ↓
Aggregate Results (% passing, failure categories)
    ↓
Error Analysis (read failing traces, identify patterns)
    ↓
Update Prompt/Tools
    ↓
Re-run Evals (measure improvement)
```

## Open Questions

- [ ] How many of the 50 eval questions should be Persian vs English?
  - Decision: At least 80% Persian (it's an Iranian law agent), 20% English for robustness

- [ ] Should evals run on exact match or semantic similarity?
  - Decision: Manual review + LLM-as-judge (semantic similarity via judge)
  - Reason: Legal answers can be paraphrased, exact match too strict

- [ ] How often to run full eval set?
  - Decision: Every prompt change (< 5 min runs), weekly full cycle (~2 min)
  - Reason: Catch regressions early, regular health check

- [ ] Should eval set be versioned in git?
  - Decision: Yes, commit eval set with reference answers
  - Reason: Reproducibility, see what changed when scores change

## References

- `CLAUDE.md`: Phase 6 description (Observability + Evals)
- `docs/best-practices/evaluation.md`: Eval-driven development patterns (START HERE)
- `docs/development/tasks.md`: Task 6.1-6.8 detailed breakdown
- Arize Phoenix docs: https://docs.arize.com/phoenix
- OpenTelemetry Python: https://opentelemetry.io/docs/instrumentation/python/
- OpenTelemetry Best Practices: https://opentelemetry.io/docs/concepts/observability-primer/
- Chainlit Feedback API: https://docs.chainlit.io/references/python/feedback
- PydanticAI + Phoenix integration: https://docs.anthropic.com/pydantic-ai/

## Estimated Complexity

**Very High** - Involves 3 interconnected systems (Phoenix, OpenTelemetry, Evaluation). But clear patterns from Phase 5 and evaluation best practices guide implementation.

**Time Estimate**: 16-20 hours across 2-3 sessions
- 6.1: Study Phoenix + OTEL (2h)
- 6.2: Deploy Phoenix locally (1h)
- 6.3: Instrument agent (2.5h) - spans, context, custom attributes
- 6.4: Token tracking (1h)
- 6.5: Feedback integration (1.5h)
- 6.6: Phoenix dashboard (1.5h)
- 6.7: Error tracking (1h)
- 6.8: Eval framework + LLM-as-judge (3h) - build golden set, align judge
- 6.9: Commit & cleanup (1.5h)

## Implementation Subtasks

1. **Task 6.1**: Study Arize Phoenix and OpenTelemetry
2. **Task 6.2**: Deploy Phoenix locally with Docker Compose
3. **Task 6.3**: Instrument Law Agent with OpenTelemetry tracing
4. **Task 6.4**: Add token usage tracking and cost estimation
5. **Task 6.5**: Integrate Chainlit feedback with Phoenix traces
6. **Task 6.6**: Create Phoenix dashboard for key metrics
7. **Task 6.7**: Add error tracking and monitoring
8. **Task 6.8**: Create evaluation framework (golden set + LLM-as-judge)
9. **Phase 6 Commit**: Review, test, and commit observability work
