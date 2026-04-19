# Phase 3: Core Search Tools - Design & Implementation Plan

## Overview

Phase 3 implements the three core search tools that form the foundation of the Law Agent's agentic multi-hop search capability:

1. **search_documents()** - Full-text search on document summaries with optional filtering
2. **get_document()** - Fetch complete document content by ID
3. **get_related_documents()** - Follow citation relationships in the legal document graph

## Architecture & Design Decisions

### Philosophy: Agent-Driven Search
The search system provides simple, composable tools and lets Claude decide the search strategy. There is **no fixed algorithm** - the agent reasons about the best approach at each step:
- Low-level tools provide simple operations
- Agent has full control over tool sequencing
- Search strategy emerges from Claude's reasoning

### The Three Tools

#### 1. search_documents(query, tags=None, doc_types=None, limit=20)
**Purpose**: Discover relevant documents via full-text search

**Design Decisions**:
- Search on summaries (not full content) for speed and relevance
- Use PostgreSQL FTS with `to_tsquery()` for ranking
- Persian text normalization (hazm library) for consistency
- Support optional filtering by document type and subject tags
- Return relevance scores for agent decision-making
- Max 20 results by default (configurable, capped at 100)

**Example Usage**:
```python
results = search_documents("بیمه", doc_types=["law", "regulation"], limit=10)
# Returns list[DocSummary] sorted by relevance_score
```

#### 2. get_document(doc_id: int)
**Purpose**: Load full content when ready to answer or analyze

**Design Decisions**:
- Only called after identifying relevant documents
- Returns all metadata + full_content for comprehensive context
- Includes relations_count for agent awareness of document connectivity
- Raises DocumentNotFoundError for invalid IDs

**Example Usage**:
```python
doc = get_document(summary.doc_id)
# Returns FullDocument with complete text for answering
```

#### 3. get_related_documents(doc_id, relation_types=None, limit=10)
**Purpose**: Follow the legal document citation graph (DAG)

**Design Decisions**:
- Single-hop traversal (agent decides if more hops needed)
- Supports filtering by relation_type (e.g., 'قوانین' for laws)
- Returns DocSummary for agent to decide next action
- Deduplicates when multiple relation types queried

**Example Usage**:
```python
# Find parent laws cited by a ruling
laws = get_related_documents(ruling_id, relation_types=['قوانین'], limit=5)
```

### Multi-Hop Search Patterns

The agent can combine these tools to answer complex questions:

1. **Search → Refine → Search Again**
   - Initial search with user keywords
   - Read summaries, discover legal terminology
   - Search again with refined keywords
   - Use for clarifying vague queries

2. **Search → Follow Relations → Read**
   - Find relevant document via search
   - Navigate citation graph to parent laws
   - Load complete parent documents
   - Use for hierarchical context (regulations citing laws)

3. **Search → Expand → Synthesize**
   - Search finds starting document
   - Get related documents (multiple directions)
   - Load multiple documents
   - Synthesize answer from diverse sources
   - Use for comprehensive answers

## Implementation Details

### Persian Text Handling
- **Normalization**: Convert ك→ک, ي→ی, remove diacritics
- **Library**: hazm.Normalizer (Persian text processing)
- **Applied to**: User queries and tag searches
- **Rationale**: Database text is normalized; queries must match

### Error Handling
- **DocumentNotFoundError**: Custom exception for missing documents
- **Database Errors**: Caught, logged, re-raised with context
- **Empty Results**: Return empty list (not error) - expected scenario

### Performance Considerations
- **Summary-based Search**: Fast FTS on smaller field
- **Lazy Loading**: Full content only when needed
- **Result Limits**: Cap at 100 results to prevent agent loop
- **Logging**: Structured logging for all operations

## Success Criteria

✅ All three tools implemented and functional
✅ Persian text normalization working correctly
✅ Multi-hop search patterns tested (3 scenarios)
✅ Unit tests passing (23+ tests)
✅ Integration tests with real database passing (23+ tests)
✅ Test coverage > 80%
✅ Code quality checks (Black, Ruff, mypy) passing
✅ Structured logging for debugging and observability

## Key Files

- **Implementation**: `src/law_agent/tools/search.py`
- **Data Models**: `src/law_agent/models/document.py` (DocSummary, FullDocument)
- **Database Queries**: `src/law_agent/database/queries.py`
- **Unit Tests**: `tests/unit/test_search_tools.py`
- **Integration Tests**: `tests/integration/test_search_tools_integration.py`

## Dependencies

- **Phase 2**: Configuration, Logging, Database Connection (required)
- **External Libraries**:
  - hazm (Persian text normalization)
  - SQLAlchemy (ORM)
  - structlog (structured logging)
  - Pydantic (data models)

## Learning Resources Used

- PostgreSQL Full-Text Search documentation
- hazm library Persian text normalization
- SQLAlchemy ORM relationships and queries
- Pydantic model serialization
