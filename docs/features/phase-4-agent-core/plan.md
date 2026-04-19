# Phase 4: Agent Core - Design & Planning

## Overview

Build the PydanticAI agent that orchestrates the three search tools (search_documents, get_document, get_related_documents) to answer legal questions with citations and follow-up suggestions.

## What We're Building

A production-grade agentic legal research assistant that:
1. **Orchestrates search tools** - Decides when to search, read docs, or follow relations
2. **Manages conversations** - Tracks message history, enforces turn limits (50 max)
3. **Generates citations** - Extracts document references and formats as [1], [2], etc.
4. **Detects user persona** - Adapts response style based on query (Layperson, Business, Professional)
5. **Generates follow-up questions** - Suggests 2-3 contextual next questions
6. **Handles errors gracefully** - Persian error messages for all failure modes

## System Architecture

### Agent Components

```
LawAgent (PydanticAI Agent)
├── System Prompt (prompts/system_prompt.yaml) - controls search strategy & persona
├── Search Tools (3 tools)
│   ├── search_documents() - FTS with filtering
│   ├── get_document() - Full content retrieval
│   └── get_related_documents() - Citation graph traversal
├── Conversation Manager - State tracking & turn limits
├── Citation System - Extract & format references
├── Error Handler - Polish Persian error messages
└── Follow-up Generator - Suggest next questions
```

### Key Design Decisions

1. **Stateless Agent** - Conversation state managed by ConversationManager, not agent
2. **System Prompt-Driven** - Agent behavior controlled via YAML, not hardcoded logic
3. **Persian-First UI** - All user-facing text in Persian (even error messages)
4. **Tool Simplicity** - Three dumb tools, smart agent reasoning
5. **Persona in Prompt** - Agent detects persona by reasoning, not separate code

## Implementation Plan

### Task 4.1: Study PydanticAI Framework ✅
- Learn Agent creation, tool registration, RunContext, conversation handling
- Run simple examples locally
- Understand dependency injection pattern

### Task 4.2: Create Law Agent with Search Tools ✅
- Initialize PydanticAI Agent with Claude Sonnet 4.5
- Load system prompt from prompts/system_prompt.yaml
- Register three search tools with proper tool decorators
- Implement async tool handlers that return JSON to agent

### Task 4.3: Build Conversation Management ✅
- ConversationState: dataclass for conversation metadata & messages
- ConversationManager: manage multiple conversations
- Track message history, enforce max_turns (50), detect persona
- Provide conversation listing and stats

### Task 4.4: Implement Citation System ✅
- Citation dataclass: number, doc_id, title, type, date
- CitationExtractor: parse [1], [2] markers from response
- ResponsePostProcessor: format citations section & add to response
- Support duplicate deduplication & iran.ir URL generation

### Task 4.5: Implement Persona Detection ✅
- **Handled in system prompt only** - agent reads query style and adapts
- Three personas: Layperson (plain language), Business (compliance), Professional (legal terms)
- Persona detection happens per message (not fixed per conversation)

### Task 4.6: Add Follow-Up Question Generation ✅
- FollowupQuestionExtractor: parse "سوالات پیگیری" section
- FollowupQuestionGenerator: format questions with bullets
- Extract from agent response or generate separately
- Max 3 questions, contextually relevant

### Task 4.7: Implement Error Handling ✅
- Custom exceptions: NoDocumentsFoundError, DocumentNotFoundError, TurnLimitExceededError, etc.
- ErrorHandler: centralized error logging & user messages
- All user messages in Persian with recovery suggestions

### Task 4.8: End-to-End Agent Testing ✅
- Unit tests: ConversationState, ConversationManager (20 tests)
- Unit tests: Citation extraction, formatting (26 tests)
- Unit tests: Error handling, exceptions (24 tests)
- Unit tests: Follow-up question generation (11 tests)
- All tests pass: 77 agent tests + 114 existing Phase 3 tests = 191 total

### Task 4.9: Commit Agent Core Phase ✅
- Format code with Black
- Fix linting issues (F841, B007 - unused variables)
- Verify tests pass (191/191 passing)
- Update CLAUDE.md with Phase 4 status
- Create plan.md and progress.md
- Commit with descriptive message

## File Structure Created

```
src/law_agent/agent/
├── __init__.py                # Export LawAgent, ConversationManager
├── core.py                    # LawAgent class with PydanticAI
├── conversation.py            # ConversationState, ConversationManager
├── citations.py               # Citation, CitationExtractor, ResponsePostProcessor
├── errors.py                  # Custom exceptions, ErrorHandler
├── followup.py                # FollowupQuestionExtractor, FollowupQuestionGenerator

src/prompts/
└── system_prompt.yaml         # Complete system prompt with persona detection

tests/unit/agent/
├── __init__.py
├── test_conversation.py       # 20 tests
├── test_citations.py          # 26 tests
├── test_errors.py             # 24 tests
└── test_followup.py           # 11 tests
```

## Success Criteria

- [x] LawAgent instantiates with PydanticAI
- [x] All three search tools registered and callable
- [x] ConversationManager tracks state correctly
- [x] Citation extraction and formatting works
- [x] Error messages in Persian with recovery suggestions
- [x] Follow-up questions extracted/formatted
- [x] All 77 unit tests pass
- [x] Code formatted with Black
- [x] Tests pass (191/191)
- [x] Phase 4 status documented in CLAUDE.md

## What's Next

**Phase 5: UI (Chainlit Interface)**
- Build RTL-enabled chat interface
- Integrate agent with Chainlit
- Show tool calls and thinking process
- Implement feedback collection

**Integration Points**
- Agent needs conversation ID to track state
- Agent returns response with citations and follow-ups
- UI renders citations as clickable links
- Feedback sent back to observability (Phoenix)

## Lessons Learned

1. **System Prompt is Powerful** - Persona detection doesn't need separate code, agent handles it naturally via prompt
2. **Simplicity Scales** - Three simple tools let agent use them creatively in combinations
3. **Persian Handling** - Must account for Persian question marks (؟, U+061F) vs ASCII (?)
4. **Tool Design** - Returning JSON to agent lets agent parse flexibly (not tightly coupled)
5. **Stateless is Better** - Agent doesn't manage state, ConversationManager does - cleaner separation

## Technical Notes

- Using `ModelMessage` from `pydantic_ai.messages` for conversation history
- System prompt in YAML allows variables and versioning
- Error codes follow SCREAMING_SNAKE_CASE convention
- All Persian strings use native characters (not transliteration)
- Tests use Persian text throughout to catch encoding issues
