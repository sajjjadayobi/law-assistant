# Task 2.6: Implement Search Tools

## Overview

Implement three core search tools that form the foundation of the agent's legal document retrieval system:

1. **search_documents** - Full-text search on document summaries
2. **get_document** - Load complete document content
3. **get_related_documents** - Follow citation relationships in the legal graph

These tools enable the agentic search strategy described in the design docs.

## Why It Matters

- **Critical for agent function**: The agent uses these tools to answer user queries
- **Enables multi-hop search**: Tools compose to support complex search patterns
- **Database utilization**: Leverages PostgreSQL full-text search and relations DAG already in place
- **Gating item**: Blocks Tasks 2.7 (integration tests), 2.8 (Phase 2 completion), and Phase 3+

## What We're Building

### Tool 1: search_documents(query, tags=None, doc_types=None, limit=20)

**Purpose**: Find relevant documents using full-text search

**Parameters**:
- `query` (str): Search query in Persian or English
- `tags` (list[str], optional): Filter by subject classifications (e.g., ['بیمه', 'کار'])
- `doc_types` (list[str], optional): Filter by type (law, regulation, advisory_opinion, court_ruling, unified_precedent)
- `limit` (int): Max results to return (default 20)

**Returns**: List of DocSummary objects with:
- doc_id, title, doc_type, date
- summary, tags (first 3 tags for context)
- relevance_score (0-1 ranking)

**Implementation**:
- Query PostgreSQL full-text search on `search_vector` (title + summary)
- Apply optional filters (tags and doc_types as WHERE clauses)
- Rank by ts_rank (PostgreSQL's built-in relevance)
- Return as sorted list, highest scores first

**Search Behavior**:
- Normalize Persian input (ك→ک, ي→ی) via hazm
- Empty results: Return empty list (agent handles "no results" messaging)
- Case insensitive
- Multi-word queries: AND by default (standard FTS behavior)

### Tool 2: get_document(doc_id)

**Purpose**: Retrieve complete document for reading/answering

**Parameters**:
- `doc_id` (int): Document ID from search results

**Returns**: FullDocument object with:
- All fields from documents table
- Metadata: doc_type, date, tags
- Content: full_content (complete text)
- Relations: list of related doc_ids (from relations table)

**Implementation**:
- Single SQL query to documents table
- Fetch all fields including full_content
- Use primary key index (fast)
- Load relations count from relations table (for context)

**Error Handling**:
- If doc_id not found: Raise DocumentNotFound exception (agent handles gracefully)

### Tool 3: get_related_documents(doc_id, relation_types=None, limit=10)

**Purpose**: Follow citations/relationships in the legal document graph

**Parameters**:
- `doc_id` (int): Source document ID
- `relation_types` (list[str], optional): Filter relations (e.g., ['قوانین', 'مواد مرتبط'])
- `limit` (int): Max related documents to return

**Returns**: List of DocSummary objects (same format as search_documents)

**Implementation**:
- Query relations table WHERE src_doc_id = {doc_id}
- If relation_types specified, add AND relation_type IN (...)
- JOIN with documents table to fetch dst_doc_id details
- Return as DocSummary list

**Graph Traversal**:
- Single hop only (don't recursively follow chains)
- Agent decides if more hops needed
- Useful for: finding parent laws (src→law), related regulations (src→regulation)

**Edge Cases**:
- If no relations found: Return empty list (normal)
- Unknown relation_types: Filter silently (allow agent to explore)

## Design Decisions

### Database Schema Choice
**Decision**: Use existing PostgreSQL FTS on `search_vector` (title + summary) rather than embeddings

**Rationale**:
- ✅ Schema already in place and populated (Phase 1)
- ✅ Keyword-based search aligns with legal domain (laws use specific terminology)
- ✅ Exact matches preferred over semantic similarity for legal research
- ✅ No ML dependency, fully deterministic
- ✅ Supports Persian text with proper normalization

**Alternative Considered**: Embeddings (too slow to implement, Phase 1 didn't set up)

### Return Types
**Decision**: Use Pydantic models (DocSummary, FullDocument) for type safety

**Rationale**:
- ✅ Aligns with PydanticAI framework
- ✅ Type hints enable IDE autocomplete for agent
- ✅ JSON serializable (needed for traces/logging)
- ✅ Validation built-in

### Single-Hop Relations
**Decision**: get_related_documents returns only direct relations, not recursive traversal

**Rationale**:
- ✅ Agent decides if more hops needed (keep tools simple)
- ✅ Avoids expensive recursive queries
- ✅ Prevents infinite loops in graph
- ✅ Agent can call multiple times for multi-hop searches

## File Structure

```
src/law_agent/
├── tools/
│   ├── __init__.py
│   └── search.py          # NEW: search_documents, get_document, get_related_documents
├── models/
│   ├── __init__.py
│   └── document.py        # NEW: DocSummary, FullDocument Pydantic models
└── database/
    ├── __init__.py
    └── connection.py      # EXISTING: database session management

tests/
├── unit/
│   └── test_search_tools.py     # NEW: Unit tests for each tool
└── integration/
    └── test_search_tools.py     # NEW: Integration tests with real DB
```

## Implementation Steps

1. **Create Pydantic models** (models/document.py)
   - DocSummary: id, title, type, date, summary, tags, relevance_score
   - FullDocument: extends DocSummary + full_content, relations_count

2. **Implement search_documents** (tools/search.py)
   - Query PostgreSQL FTS
   - Apply tag/doc_type filters
   - Return sorted DocSummary list
   - Handle empty results

3. **Implement get_document** (tools/search.py)
   - Query documents table by ID
   - Return FullDocument
   - Handle not found with exception

4. **Implement get_related_documents** (tools/search.py)
   - Query relations table
   - Apply relation_type filter
   - JOIN with documents for details
   - Return DocSummary list

5. **Write unit tests** (tests/unit/test_search_tools.py)
   - Test each tool with mock DB data
   - Test filters (tags, doc_types, relation_types)
   - Test error cases (not found, empty results)
   - ~15-20 test cases

6. **Write integration tests** (tests/integration/test_search_tools.py)
   - Test with real database
   - Test search ranking (verify ts_rank works)
   - Test Persian text handling (normalization)
   - Test graph traversal (follow relations)
   - ~10-15 test cases

7. **Configure logging** (search.py)
   - Log search queries with parameters
   - Log result counts and top scores
   - Log execution time

8. **Test coverage** (make all)
   - Achieve 80%+ code coverage
   - No type errors (mypy)
   - Code formatted (black)
   - No linting issues (ruff)

## Success Criteria Checklist

- [ ] DocSummary and FullDocument Pydantic models created and tested
- [ ] search_documents implemented with FTS + filters
- [ ] get_document implemented with error handling
- [ ] get_related_documents implemented with single-hop traversal
- [ ] Unit tests passing (15+ cases)
- [ ] Integration tests passing (10+ cases) with real database
- [ ] Code coverage ≥80%
- [ ] All formatting/linting/type checks passing (make all)
- [ ] Structured logging added (search queries, results, execution time)
- [ ] Documentation updated in code (docstrings)
- [ ] progress.md completed with learnings
- [ ] CLAUDE.md updated with completion status

## Dependencies

**Already Available**:
- ✅ PostgreSQL database with documents and relations tables (Task 2.5)
- ✅ Database connection layer (Task 2.5, src/law_agent/database/connection.py)
- ✅ Logging system (Task 2.4, structlog)
- ✅ Configuration system (Task 2.3, config.yaml)
- ✅ SQLAlchemy ORM (Task 2.5, already using)

**New Dependencies**: None required

## Blockers/Risks

1. **Persian text normalization**: hazm library already in pyproject.toml, should work
2. **FTS query syntax**: PostgreSQL FTS for Persian - verify search_vector was built correctly in Phase 1
3. **Database connection**: Must use existing connection pool from Task 2.5
4. **Test data**: Need sample Persian queries for integration tests

## Open Questions

1. Should search_documents normalize the query input via hazm before searching?
   - **Answer**: Yes, normalize input to match how search_vector was built
2. What should happen if relation_types is specified but doesn't match any relations?
   - **Answer**: Return empty list (normal case, agent can adjust strategy)
3. Should get_document fetch relation count or full relation list?
   - **Answer**: Fetch count only (keep response size small, agent can call get_related_documents if needed)

## Timeline

- **Planning**: Done (this document)
- **Implementation**: 2-3 hours
- **Testing**: 1-2 hours
- **Debugging/Polish**: 1 hour
- **Total**: ~4-6 hours

## Reference Links

- Architecture: `docs/architecture/design.md` (functional requirements)
- Search strategy: `docs/architecture/search.md` (agent instructions for using tools)
- Database schema: `docs/architecture/database.md` (documents + relations tables)
- Phase 2 tasks: `docs/development/tasks.md` (task hierarchy)
