# Phase 6: Observability & Eval-Driven Development - Plan

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

- [ ] Phoenix running in Docker at localhost:6006
- [ ] Agent instrumented with OpenTelemetry (spans visible in Phoenix UI)
- [ ] All agent activities traced: search_documents, get_document, get_related_documents, LLM calls
- [ ] Token usage tracked per tool call
- [ ] Conversation traces include: user query, tool calls, final response, execution time
- [ ] Chainlit feedback (👍/👎) sent to Phoenix
- [ ] Phoenix dashboard created with key metrics (conversations, tokens, cost, feedback)
- [ ] Error tracking and alerts configured
- [ ] Golden eval set created (50 QA pairs)
- [ ] LLM-as-judge evaluator implemented
- [ ] Eval harness runs 50 test cases in < 2 minutes (cached)
- [ ] Pass/fail grading implemented (with reasoning)
- [ ] Error analysis framework documented
- [ ] All 8 subtasks (6.1-6.8) have implementation + tests
- [ ] Tests pass: eval grading, trace visibility, feedback integration
- [ ] Documentation complete: plan.md and progress.md updated
- [ ] CLAUDE.md updated with Phase 6 completion status

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
