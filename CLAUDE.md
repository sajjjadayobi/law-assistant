# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Law Agent project for building an AI assistant that answers questions about Iranian law using a comprehensive legal knowledge base. The agent will search through a PostgreSQL database containing legal documents (advisory opinions, court rulings, laws) and provide accurate, contextual answers.

**Stack**: Python with Claude Agent SDK (potentially with LiteLLM for multi-model support), Streamlit UI, PostgreSQL database

**Status**: Early design phase - no code written yet, only documentation and database schema

## Database Architecture

The knowledge base is stored in a 1.3GB PostgreSQL database (`pg_db.sql`) with a graph-based relational structure:

### Core Tables

1. **`pages`** - Primary document storage (advisory opinions, court rulings, laws)
   - `page_id` (BIGINT, PK) - unique document identifier
   - `content` (TEXT) - full HTML content in Persian
   - `title` (VARCHAR) - document title (e.g., "نظریه مشورتی شماره...")
   - `relations_built`, `relations_in_progress`, `relations_started_at` - processing flags
   - `created_at`, `http_status`

2. **`tags`** - Document classification system
   - `tag_id` (SERIAL, PK)
   - `tag_name` (VARCHAR) - Persian tag names
   - `category` (VARCHAR) - classification type ('subjects', etc.)
   - Examples: 'اساسی' (Constitutional), 'اداری' (Administrative)

3. **`page_tags`** - Many-to-many junction table linking documents to tags
   - `page_id` (FK → pages.page_id)
   - `tag_id` (FK → tags.tag_id)

4. **`relations`** - Document cross-reference graph (DAG structure)
   - `id` (SERIAL, PK)
   - `src_id` (FK → pages.page_id) - source document
   - `dst_id` (FK → pages.page_id) - destination document
   - `relation_name` (VARCHAR) - relation type in Persian:
     - `مواد مرتبط` (Related Articles) - lateral connections
     - `قوانین` (Laws/Legislation) - hierarchical parent-child links

### Document Hierarchy

The database forms a **Directed Acyclic Graph (DAG)** with hierarchical structure:

```
Level 0: Constitutional Laws (نظام اساسی)
  ↓
Level 1: Primary Laws & Legislation (قانون مجازات اسلامی, قانون مالیاتهای مستقیم, etc.)
  ↓
Level 2: Amendments & Executive Regulations
  ↓
Level 3: Advisory Opinions (نظریه مشورتی)
  ↓
Level 4: Court Rulings (احکام دیوان عدالت اداری, etc.)
```

**Key insight**: When retrieving a document, you should traverse the relation graph to fetch:
- **Ancestors** (primary laws the document cites) - follow `dst_id` from relations
- **Descendants** (rulings that apply the document) - follow `src_id` from relations
- **Cross-references** (similar documents via shared tags)

Use recursive CTEs to traverse the graph, limiting depth to 3-4 levels to manage context window.

## Agent Design Philosophy (from best_practices/agent.md)

### Core Principles

1. **Harness, not workflow** - Build agent harnesses that let Claude be agentic rather than rigid workflows
2. **Incremental progress** - Use multi-context window workflows with state management (progress tracking, git commits)
3. **Progressive context disclosure** - Load context on-demand via files (table_of_content.md, USER.md, AGENT.md, TOOLS.md)
4. **Humble transparency** - Agent should say "I don't know" confidently when lacking information
5. **Research then act** - Always verify understanding before acting; ask clarifying questions
6. **State in code** - Use git history and file system as state management for context freshness

### Multi-Context Window Workflow

For long-running tasks:
- **Initializer agent**: Set up environment (init.sh, progress.txt, initial git commit, feature list)
- **Feature creator**: Work on ONE feature at a time, commit progress, update progress.txt, run tests
- **Testing**: Verify end-to-end as human user would
- Use progress.txt and git log to maintain state across context windows

### Trust & Error Recovery

- **Say "I don't know" confidently** - This builds trust and creates a feedback loop for improving knowledge
- **Reflection & error recovery** - Failing is acceptable if you can reflect and recover
- **Don't repeat mistakes** - Learn from feedback and add to knowledge base
- **Verification at every stage** - Validate work incrementally, not just at the end

## Evaluation Philosophy (from best_practices/eval.md)

### Eval-Driven Development

1. **Start early** - Begin with 20-50 simple tasks from real failures, not hundreds
2. **Define success first** - What does "good" look like? Define this before building
3. **Error analysis is primary** - Spend 60-80% of development time on error analysis
4. **Binary grading** - Use pass/fail with reasoning, not numeric scores
5. **LLM-as-judge** - Use for subjective quality assessment, aligned with human expert judgment
6. **End-to-end first** - Evaluate entire conversation/task completion, then drill down to components

### Agent-Specific Eval Patterns

For conversational agents (like this Law Agent):
- **End-state outcomes** - Did the agent accomplish the user's goal?
- **Transcript constraints** - Did it finish in <10 turns?
- **Tone/persona alignment** - Was the response appropriate for user expertise level?
- **Groundedness** - Are claims supported by retrieved sources?
- **Coverage** - Did answer include key facts from authoritative sources?
- **Source quality** - Were consulted sources authoritative?

### Evaluation Lifecycle

1. Start with manual error analysis on traces
2. Group similar failures into categories
3. Build automated evals for persistent issues (not trivial one-time fixes)
4. Monitor judge alignment with human expert (aim for 80%+ agreement)
5. Use syntactic data generation to fill gaps
6. Iterate on both product and evals together

## Functional Requirements

### Agent Capabilities

1. **Intro & Context Setting**
   - Show example questions to set tone and vibe
   - Explain capabilities clearly and concisely

2. **Clarifying Questions**
   - Ask questions at any point, especially initially
   - Understand user's expertise level and question intent
   - Reject or clarify irrelevant queries

3. **Knowledge Retrieval**
   - Load table_of_content.md to understand available knowledge
   - Search agentic-ally through database (potentially file system-based)
   - Follow document relations to gather complete context
   - May ask clarifying questions during search

4. **Answer Synthesis**
   - Combine retrieved documents with common sense and law knowledge
   - Adapt answer style to user's expertise level
   - Provide concise, clear, to-the-point responses
   - Include follow-up question suggestions (make them clickable)

5. **Multi-Round Conversations**
   - Support detailed follow-up questions
   - Maintain context across conversation turns
   - Show agent actions/thinking transparently

### UX Requirements

- **Not a blank canvas** - Show random great questions at start
- **Clickable suggestions** - Make follow-up questions obvious and clickable
- **Loading states** - Show what agent is doing during searches/thinking
- **Feedback mechanism** - Thumbs up/down for responses
- **Transparency** - Show all tool calls and reasoning steps

## Configuration

All configuration should be in `config.yaml` (nothing hardcoded):
- Model selection (start with Claude Sonnet 4.6)
- Database connection details
- API keys (use environment variables)
- UI settings (Streamlit)
- Search/retrieval parameters
- Prompt templates

## Engineering Practices

### Git Usage

- Use git like an experienced engineer
- Commit incrementally with descriptive messages
- Use branches for features
- Track progress in progress.txt for multi-context workflows

### Agent Development

- **AGENT.md** - Capture the "soul" of the agent during testing
  - Meta-level insights from user feedback
  - Concise principles about agent behavior
  - Update iteratively as you learn

### Tools & Stack

- **Claude Agent SDK** (or PydanticAI if SDK is overkill)
- **LiteLLM** - For multi-model support under Claude Agent SDK
- **Streamlit** - Simple chat interface showing all actions/tool calls
- **PostgreSQL** - Current data source (may migrate to MongoDB BSON later per draft.md)

## Future Considerations

- **Database migration**: Possibly move from PostgreSQL to MongoDB with BSON documents containing `{doc, tags, relations, relation_types}` (see draft.md)
- **Deep research vs assistant**: Determine optimal balance between research-like exploration and quick assistant-like responses
- **Multi-agent**: Consider if parallel sub-agents for search make sense given database size
