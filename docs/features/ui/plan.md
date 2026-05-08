# Phase 5: UI (Chainlit Interface) - Plan

## What I'm Building

A production-ready Persian-language chat interface using Chainlit that connects to the Law Agent (Phase 4). The UI will provide:
- RTL (right-to-left) chat interface optimized for Persian
- Citation links to source documents (iran.ir)
- Example questions at start to guide users
- Feedback collection (thumbs up/down) for observability
- Agent thinking and tool call visualization for transparency
- Conversation history management with save/load capabilities

This transforms the backend agent into a complete end-to-end conversational AI application.

## Why This Matters

Phase 4 built a production-grade agent, but without a UI it's unusable by end users. Phase 5 delivers the complete product:
- Users can ask legal questions in Persian through a web chat interface
- Answers show sources with clickable links (transparency)
- Example questions reduce friction for first-time users
- Feedback collection enables eval-driven improvements
- Tool visualization shows agent's reasoning (builds trust)
- History management supports multi-session workflows

## Key Design Decisions

### Decision 1: Chainlit as UI Framework
**Decision**: Use Chainlit 1.0+ for the chat interface
**Why**:
- Production-ready with minimal code
- Native support for intermediate step visualization (tool calls)
- Built-in data persistence and analytics
- Handles authentication, user sessions, message history
- Active community and well-documented
- No RTL support built-in, but CSS customization available

**Alternatives Considered**:
- Streamlit: Rejected - not optimized for chat, worse RTL support
- Custom React/Next.js: Rejected - overkill, would take 2-3x longer to implement
- Gradio: Rejected - limited customization, poor agent tool visualization

**Trade-offs**:
- Chainlit isn't specifically designed for RTL, requires CSS customization
- Less UI customization than custom frontend (but 80/20 rule applies)
- Vendor lock-in to Chainlit (but framework-agnostic backend allows switching)

### Decision 2: RTL Support via CSS + Custom Styling
**Decision**: Implement RTL using CSS flexbox direction: rtl, Chainlit's custom CSS features, and JavaScript DOM manipulation
**Why**:
- Chainlit supports custom CSS injection
- Can override default LTR behavior without forking framework
- Persian text naturally reads RTL, just need UI elements to align
- Document title, citations, buttons all need RTL handling

**Alternatives Considered**:
- Use different UI framework with native RTL: Rejected - no Chainlit equivalent with RTL
- Wait for Chainlit RTL support: Rejected - may never happen, need working UI now
- Use Bidi text direction markers: Rejected - doesn't solve button/layout alignment

**Trade-offs**:
- RTL implementation is custom CSS, could break on Chainlit upgrades (mitigated by tests)
- May need JavaScript for dynamic RTL (e.g., element order in tool calls)
- Not as polished as native RTL framework (but acceptable for MVP)

### Decision 3: Citation Links Architecture
**Decision**: Extract citation numbers from agent response, link each to ian.ir document URL
**Why**:
- Agent already generates [1], [2] format citations (from Phase 4)
- Citations include doc_id in agent response (structured data)
- Simple regex parsing of response text to create clickable links
- All citations point to iran.ir (single source of truth for legal documents)

**Alternatives Considered**:
- Embed citations in agent response as JSON metadata: Rejected - requires agent changes, more complex
- Hardcode citation display in UI: Rejected - brittle, doesn't scale
- Use Chainlit's Step visualization for citations: Rejected - citations are inline in text, not discrete steps

**Trade-offs**:
- Depends on agent continuing to output citations in [N] format (mitigated by agent tests)
- Regex parsing could be fragile (mitigated by careful parsing + tests)
- All citations same source (iran.ir) - not flexible, but appropriate for Iranian legal system

### Decision 4: Example Questions Display
**Decision**: Store 5-10 example questions in config.yaml, display at chat start using Chainlit's initial message system
**Why**:
- Example questions reduce friction for first-time users (important for legal domain)
- Questions should be diverse: simple, complex, edge cases
- Config-driven allows easy updates without code changes
- Chainlit's initial message feature allows formatted display with buttons

**Alternatives Considered**:
- Hard-code example questions in Python: Rejected - not config-driven, requires code change to update
- Load from database: Rejected - added complexity, not needed
- Display only first time user uses app: Rejected - helpful for all users, keep simple

**Trade-offs**:
- Need to maintain examples (but easy in config.yaml)
- Fixed examples (not personalized), but good for MVP
- May need JavaScript to make examples clickable (Chainlit limitation)

### Decision 5: Feedback Collection + Observability Integration
**Decision**: Use Chainlit's feedback feature (👍/👎 buttons) to collect user feedback, send to Arize Phoenix for analysis
**Why**:
- Chainlit has native feedback UI (built-in buttons)
- Feedback events map directly to Phoenix observability data
- Binary feedback (👍/👎) is simple, unambiguous, and common in chat UIs
- Enables eval-driven iteration (measure → improve → measure)

**Alternatives Considered**:
- 5-star rating system: Rejected - less data than binary, unclear what 3 stars means
- Custom feedback form: Rejected - users won't fill it out, friction
- No feedback collection: Rejected - need data for evals

**Trade-offs**:
- Binary feedback less granular than detailed surveys (but acceptable)
- Must wire Chainlit feedback → Phoenix traces
- Feedback only on final response (not on individual tool calls)

### Decision 6: Tool Call Visualization
**Decision**: Use Chainlit's Step objects to show tool calls (search_documents, get_document, etc.) with parameters and results
**Why**:
- Chainlit has native Step support for showing intermediate reasoning
- Steps help user understand agent's search strategy
- Shows tool name, input parameters, execution time, result count
- Increases trust by transparency

**Alternatives Considered**:
- Show tool calls as text in agent response: Rejected - clutters answer, hard to read
- No tool visualization: Rejected - users want transparency
- Custom visualization in separate section: Rejected - Chainlit Steps are perfect fit

**Trade-offs**:
- Steps add verbosity (more messages in UI)
- Not all tool calls are interesting (e.g., internal retries) - need filtering
- Requires agent to provide tool call data in structured format (already done in Phase 4)

### Decision 7: Conversation History Management
**Decision**: Use Chainlit's built-in session/history management with local database backend
**Why**:
- Chainlit automatically manages conversation history per user session
- Data stored in SQLite by default (can upgrade to PostgreSQL)
- No need to build custom session management
- Users can resume conversation from save points

**Alternatives Considered**:
- Custom session table in law_agent PostgreSQL: Rejected - duplicate logic, Chainlit already does this
- In-memory only: Rejected - users lose history on app restart, poor UX
- Cloud-based (Firebase, etc.): Rejected - adds external dependency, more complex

**Trade-offs**:
- Depends on Chainlit's session API (framework coupling)
- SQLite default may need upgrade to PostgreSQL for production scale
- Privacy considerations (storing conversation history) - document in privacy policy

### Decision 8: Integration with Phase 4 Agent
**Decision**: Call `LawAgent.run_conversation()` from Chainlit's message handler, feed response back to UI
**Why**:
- Phase 4 agent is production-ready, no changes needed
- Simple function call from UI layer
- Decouples UI from agent (UI can be replaced)
- Async support for non-blocking chat

**Alternatives Considered**:
- WebSocket/gRPC communication: Rejected - overkill, adds infrastructure
- Agent as separate microservice: Rejected - too much for MVP
- Refactor agent into Chainlit callbacks: Rejected - breaks agent encapsulation

**Trade-offs**:
- UI and agent run in same process (could be separated later for scaling)
- Synchronous to async conversion needed (mitigated by async/await)
- No separate scaling of agent layer (acceptable for MVP)

## Success Criteria

- [ ] Chainlit server runs and serves chat interface at http://localhost:8000
- [ ] Chat interface displays in RTL layout (text right-aligned, buttons on right side)
- [ ] User can type message and receive response from Law Agent
- [ ] Citations in response are clickable links to iran.ir
- [ ] Example questions display at chat start (configurable in config.yaml)
- [ ] Thumbs up/down feedback buttons visible and functional
- [ ] Tool calls (search_documents, get_document) display as Chainlit Steps with parameters and results
- [ ] Conversation history persists and can be resumed in new sessions
- [ ] Persian text renders correctly (right-to-left)
- [ ] Agent thinking shows in UI (intermediate reasoning steps)
- [ ] No console errors or warnings in Chainlit logs
- [ ] All 8 subtasks (5.1-5.8) have implementation + tests
- [ ] Smoke tests pass: 5+ test cases covering basic functionality
- [ ] Documentation complete: plan.md and progress.md updated
- [ ] Code review passed: no issues blocking merge

## Dependencies

- **Requires**:
  - Phase 4 complete (Agent Core) ✅
  - Python 3.9+ with Law Agent environment set up ✅
  - PostgreSQL database with documents table ✅
  - PydanticAI and Claude API configured ✅

- **Blocks**:
  - Phase 6 (Observability) - Phase 5 UI sends feedback to Phoenix
  - Phase 7+ (Testing, Deployment)

- **Related**:
  - Phase 4: Agent Core (backend being wrapped)
  - docs/architecture/design.md: UI requirements section
  - config.yaml: UI configuration (example_questions, show_thinking, etc.)

## Open Questions

- [x] How to handle RTL in Chainlit?
  - Decision: Custom CSS with flexbox direction: rtl
  - Implementation: CSS file with RTL overrides

- [x] Should tool calls show all execution details?
  - Decision: Yes - show tool name, parameters, result count, execution time
  - Rationale: Transparency builds user trust in agent's reasoning

- [x] How to handle long citation lists (10+ sources)?
  - Decision: Show all citations numbered [1]-[N], clickable, expand/collapse section if needed
  - Rationale: Legal documents often cite many sources

- [ ] Should conversation history be wiped on new session?
  - Decision: TBD - Chainlit's default is per-user persistence
  - Need to test user experience - does persistent history help or confuse?

## References

- `CLAUDE.md`: Phase 5 description (UI with Chainlit)
- `docs/architecture/design.md`: UI requirements section (RTL, citations, example questions, feedback)
- `docs/features/phase-4-agent-core/`: Agent implementation details
- Chainlit docs: https://docs.chainlit.io/
- Chainlit Python API: https://docs.chainlit.io/references/python
- RTL CSS guide: https://www.w3.org/International/questions/qa-html-dir

## Estimated Complexity

**High** - Multiple subsystems (UI framework, RTL customization, observability integration, agent integration). However, clear requirements and existing agent make it tractable.

**Time Estimate**: 8-12 hours
- 5.1: Chainlit setup & basic interface (1.5h)
- 5.2: RTL support (2h) - CSS can be tricky
- 5.3: Citations (1h) - regex parsing
- 5.4: Example questions (0.5h) - config-driven
- 5.5: Feedback collection (1h) - Chainlit → Phoenix
- 5.6: Tool visualization (1.5h) - Chainlit Steps API
- 5.7: History management (1h) - Chainlit built-in
- 5.8: Tests & polish (1.5-2h)

## Implementation Subtasks

1. **Task 5.1**: Study Chainlit framework and set up basic chat interface
2. **Task 5.2**: Implement RTL (right-to-left) support for Persian text
3. **Task 5.3**: Implement citation links to iran.ir documents
4. **Task 5.4**: Add example questions display at chat start
5. **Task 5.5**: Add feedback collection (thumbs up/down) integration with Phoenix
6. **Task 5.6**: Display agent thinking and tool calls using Chainlit Steps
7. **Task 5.7**: Set up conversation history management
8. **Task 5.8**: End-to-end testing and polish (smoke tests)
