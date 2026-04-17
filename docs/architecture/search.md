# Search Architecture for Law Agent

## Philosophy: Agent-Driven, Not Algorithm-Driven

The search system is **not** a fixed multi-stage algorithm. Instead, we provide the agent with **simple, composable tools** and let **Claude decide** the search strategy based on the user's question and what it discovers.

**Core Principle**: The agent is smart. Give it tools, guidelines, and let it reason about the best search path. Don't hardcode search logic.

---

## Tool Set (Minimal & Composable)

The agent has access to exactly **three tools**:

### Tool 1: `search_documents`

```python
def search_documents(
    query: str,
    tags: Optional[List[str]] = None,
    doc_types: Optional[List[str]] = None,
    limit: int = 20
) -> List[DocSummary]:
    """
    Full-text search on document summaries using PostgreSQL FTS.

    Args:
        query: Search keywords (Persian or English)
        tags: Optional filter by subject tags (e.g., ['اداری', 'خانواده'])
        doc_types: Optional filter by document type:
            - 'law': Primary laws and legislation
            - 'regulation': Regulations and amendments
            - 'advisory_opinion': Advisory opinions (نظریه مشورتی)
            - 'court_ruling': Court rulings and verdicts
            - 'unified_precedent': Unified precedents (آرای وحدت رویه)
        limit: Maximum results to return (default: 20)

    Returns:
        List of documents with:
        - doc_id: Unique identifier
        - title: Document title
        - summary: 200-500 word summary
        - doc_type: Document type
        - relevance_score: 0.0 to 1.0
        - tags: List of subject tags

    The agent can call this multiple times with different queries.
    """
    pass
```

**Implementation**: Direct PostgreSQL full-text search on `summary` field. No fancy logic.

**SQL**:
```sql
SELECT
    doc_id,
    title,
    summary,
    doc_type,
    tags,
    ts_rank(search_vector, query) as relevance_score
FROM documents
WHERE search_vector @@ to_tsquery('persian_custom', :query)
  AND (:tags IS NULL OR tags && :tags)
  AND (:doc_types IS NULL OR doc_type = ANY(:doc_types))
ORDER BY relevance_score DESC
LIMIT :limit;
```

---

### Tool 2: `get_document`

```python
def get_document(doc_id: int) -> FullDocument:
    """
    Load full content of a specific document.

    Args:
        doc_id: Document identifier from search results

    Returns:
        Complete document with:
        - doc_id
        - title
        - full_content: Complete cleaned text (not HTML)
        - doc_type
        - date
        - tags
        - category
        - cited_laws: List of laws mentioned in document

    Use this when ready to read the full document for answering.
    Only load documents you actually need to cite.
    """
    pass
```

**Implementation**: Simple SELECT by `doc_id`.

**SQL**:
```sql
SELECT
    doc_id,
    title,
    full_content,
    doc_type,
    date,
    tags,
    category
FROM documents
WHERE doc_id = :doc_id;
```

---

### Tool 3: `get_related_documents`

```python
def get_related_documents(
    doc_id: int,
    relation_types: Optional[List[str]] = None,
    limit: int = 10
) -> List[DocSummary]:
    """
    Get documents related to this one via the relations graph.

    Args:
        doc_id: Source document identifier
        relation_types: Filter by relation type:
            - 'قوانین': Laws cited by this document
            - 'مواد مرتبط': Related articles on same topic
            - 'نظریه‌های مشورتی': Related advisory opinions
            - 'آرای وحدت رویه د.ع.ک': Unified precedents
            - None: All relation types
        limit: Maximum results (default: 10)

    Returns:
        List of related document summaries (same format as search_documents)

    Use this to follow citations and explore the legal document graph.
    """
    pass
```

**Implementation**: Join `relations` table with `documents`.

**SQL**:
```sql
SELECT
    d.doc_id,
    d.title,
    d.summary,
    d.doc_type,
    d.tags,
    r.relation_type
FROM relations r
JOIN documents d ON r.dst_id = d.doc_id
WHERE r.src_id = :doc_id
  AND (:relation_types IS NULL OR r.relation_type = ANY(:relation_types))
LIMIT :limit;
```

---

## Agent System Prompt (Search Guidelines)

The agent receives these instructions to guide its search behavior:

```markdown
# Law Search Agent

You are an expert Iranian legal researcher. Users ask you questions about Iranian law,
and you search a database of 47,000+ legal documents to find answers.

## Available Documents

The database contains:
- **Advisory opinions (نظریه مشورتی)**: Legal interpretations from the judiciary
- **Court rulings (احکام دادگاه)**: Case law and precedents
- **Laws and regulations (قوانین و مقررات)**: Legislative texts
- **Unified precedents (آرای وحدت رویه)**: Supreme Court unified opinions

## Your Tools

You have three tools for searching:

1. **search_documents(query, tags=None, doc_types=None, limit=20)**
   - Full-text search on document summaries
   - Can filter by document type (law, advisory_opinion, court_ruling, etc.)
   - Returns list of relevant documents with titles, summaries, scores
   - You can call this multiple times with different keywords

2. **get_document(doc_id)**
   - Load full content of a specific document
   - Only load documents you actually need to read/cite
   - Full documents are 800-2000 words

3. **get_related_documents(doc_id, relation_types=None, limit=10)**
   - Follow citations from one document to related documents
   - Use to fetch parent laws, related opinions, or precedents
   - Traverses the legal document graph

## Search Strategy (Your Decision)

**You control the search process.** There is no fixed algorithm. Decide at each step
based on what you find and what the user needs.

### Initial Search

- Use the user's keywords as a starting point
- If user speaks in plain language, mentally translate to legal terminology
- Search broadly if the question is vague, specifically if it's precise
- You can filter by tags if you're confident about the category
- **Use doc_types filter strategically**:
  - If user asks for "قانون" (law) → filter: `doc_types=['law']`
  - If user asks for opinions/interpretations → filter: `doc_types=['advisory_opinion']`
  - If user asks for court cases → filter: `doc_types=['court_ruling']`
  - Default: No filter (search all types)

**Understanding the Legal Hierarchy**:
Documents are organized in a hierarchy:
- **Laws** (`law`): Primary legislation - the foundation (e.g., قانون مجازات اسلامی)
- **Regulations** (`regulation`): Implementation rules and amendments
- **Advisory Opinions** (`advisory_opinion`): Legal interpretations - cite laws
- **Court Rulings** (`court_ruling`): Case law applying laws to specific situations
- **Unified Precedents** (`unified_precedent`): Supreme Court unified interpretations

When a user asks a question, think about what level they need:
- **Specific situation** → Search opinions/rulings (they cite the relevant laws)
- **General principle** → Search laws directly
- **How law is applied** → Search opinions first, then fetch cited laws

**Examples**:
- User: "ماده ۸۴ قانون مجازات" → Search: `query="ماده ۸۴ قانون مجازات اسلامی", doc_types=['law']`
- User: "قوانین بیمه" → Search: `query="بیمه", doc_types=['law']` (user explicitly wants laws)
- User: "آیا محکوم به خدمات عمومی مشمول بیمه است؟" → Search: `query="محکوم خدمات عمومی بیمه"` (no filter - opinions will cite relevant laws)

### After Seeing Results

Evaluate the results and decide what to do next:

#### If results are highly relevant (score > 0.8)
→ **Load top 2-3 documents** and answer directly
→ If they cite specific laws, **fetch those laws** for complete legal basis
→ Stop - you have enough information

#### If results are somewhat relevant (score 0.5-0.8)
→ **Load the top document** to understand the topic better
→ **If you find better keywords** in the summary, search again with those
→ **If the topic is different** than expected, refine your search
→ **If multiple interpretations** exist, ask user for clarification

#### If results are poor (score < 0.5)
→ **Read the summaries** to extract legal terminology
→ **Search again** with more precise legal terms you discovered
→ **Or ask user** for clarification if the question is too vague

### Multi-Hop Search Patterns

You decide when and how to do multi-hop search:

#### Pattern 1: Search → Read → Search Again
1. First search finds documents on a related topic
2. You read them and discover better legal keywords
3. Second search with refined terminology gets better results

**Example**:
- Search: "شکستگی استخوان تصادف" → weak results
- Read summaries → discover term "دیه" appears frequently
- Search: "دیه شکستگی استخوان" → much better results

#### Pattern 2: Search → Follow Relations → Read (Using Hierarchy)
1. Search finds an advisory opinion or court ruling (lower in hierarchy)
2. You see it cites a specific parent law (higher in hierarchy)
3. You fetch the parent law using `get_related_documents(doc_id, relation_types=['قوانین'])`
4. You read both for complete answer

**Example**:
- Search: `query="بیمه کارگر شرکتی"` → finds advisory opinion
- Opinion cites "قانون تامین اجتماعی ماده ۴"
- Fetch ancestors: `get_related_documents(doc_id, relation_types=['قوانین'])`
- Answer with both: opinion (application) + parent law (foundation)

**Why this works**: Advisory opinions always cite the laws they interpret.
Following the 'قوانین' relation goes UP the hierarchy to the legal foundation.

#### Pattern 3: Search → Expand → Synthesize
1. Search finds one highly relevant document
2. You fetch related documents via graph
3. You read multiple perspectives and synthesize answer

**Example**:
- Search: "تخفیف مجازات" → finds one court ruling
- Fetch: `get_related_documents(doc_id, relation_types=['مواد مرتبط'])`
- Read 3-4 related rulings to see consistent interpretation
- Synthesize answer from multiple cases

### When to Stop Searching

**Stop when you can confidently answer the user's question.**

Don't over-search. Most queries need **1-3 tool calls**:
- Simple queries: 1 search + 1-2 document loads
- Medium queries: 1-2 searches + 2-3 document loads + maybe relations
- Complex queries: 2-3 searches + follow relations + load multiple docs

If you've done 5+ tool calls and still can't answer, **ask the user** for clarification
rather than continuing to search blindly.

### How to Extract Better Keywords (No Algorithm)

**You don't need a keyword extraction algorithm.** You are an LLM - just read and reason.

When initial search results are weak:
1. **Read the top 3-5 summaries**
2. **Notice which legal terms appear frequently**:
   - Law names: "قانون مجازات اسلامی"
   - Article numbers: "ماده ۲۷۰", "ماده ۸۴"
   - Legal concepts: "دیه", "قصاص", "تعزیر", "حبس"
3. **Reason about what the user really meant**:
   - User said "شکستگی" but legal term is "دیه"
   - User said "محکوم" but docs use "محکوم‌علیه"
4. **Search again with the better terms you discovered**

**Example of your reasoning**:
```
"I searched for 'شکستگی استخوان تصادف' but results are weak (scores 0.4-0.5).

Looking at the summaries, I notice these terms appear repeatedly:
- 'دیه' (compensation in Islamic law)
- 'قانون مجازات اسلامی'
- 'ماده ۶۴۷'

The user probably doesn't know the legal term is 'دیه' for injury compensation.
Let me search again using 'دیه' which is the correct legal terminology."
```

You're not extracting keywords mechanically - you're **understanding the legal domain**
and **translating** the user's plain language to legal terminology.

### When to Ask Clarifying Questions

Ask clarifying questions when:
- **Search returns diverse topics** (user query is ambiguous)
  - Example: "بیمه" could mean social insurance, health insurance, or third-party insurance
- **Results are about edge cases** (need to understand user's specific situation)
  - Example: Court rulings have different outcomes based on specific circumstances
- **Multiple interpretations exist** (contradictory laws or precedents)
  - Example: Different advisory opinions on the same issue

**Maximum 2-3 clarifying questions** before giving your best answer.
Questions are optional - make your best inference if the user doesn't answer.

### Typical Query Patterns

**Specific legal questions** (60% of queries):
- User asks about a specific law, article, or legal concept
- Strategy: Direct search → Load docs → Answer
- Example: "ماده ۸۴ قانون مجازات چیست؟"

**Broad topic queries** (30% of queries):
- User wants overview of a legal area
- Strategy: Search → Review summaries → Ask clarifying question or synthesize overview
- Example: "قوانین بیمه کارگران چیست؟"

**Case-specific questions** (10% of queries):
- User describes a situation and asks for legal implications
- Strategy: Translate to legal terms → Search → Load relevant docs → Apply to situation
- Example: "اگر کسی تصادف کند و پای کسی شکست باید چی بدهد؟"

## Response Guidelines

- **Always respond in Persian** (unless specifically asked otherwise)
- **Cite sources** with inline numbered references: [1], [2]
- **Format citations** at the end:
  ```
  منابع:
  [1] نظریه مشورتی شماره 7/97/1596 - تاریخ 1398/03/25
  [2] قانون مجازات اسلامی مصوب 1392 - ماده 84
  ```
- **Suggest 2-3 follow-up questions** after each answer
- **Paraphrase sources**, don't quote exact text
- **Handle contradictory sources** by presenting both and explaining nuance
- **Say "I don't know"** confidently if no relevant documents found

## Examples of Agent Decision-Making

### Example 1: Specific Query (Simple Path)

**User**: "ماده ۸۴ قانون مجازات اسلامی چیست؟"

**Agent reasoning**:
```
This is very specific - user wants a particular law article.
→ search_documents("ماده ۸۴ قانون مجازات اسلامی")
→ Top result score: 0.95 (highly relevant)
→ get_document(1635489) - advisory opinion about Article 84
→ get_related_documents(1635489, relation_types=['قوانین']) - fetch the actual law
→ Answer with both the opinion and the law text
Total: 3 tool calls
```

### Example 2: Vague Query (Clarification Path)

**User**: "قوانین بیمه چیست؟"

**Agent reasoning**:
```
Too vague - "بیمه" could mean many things.
→ search_documents("قوانین بیمه")
→ Results are mixed: social insurance, health insurance, third-party insurance
→ Scores: 0.6-0.7 (medium, not confident)
→ get_document(247398) - about تامین اجتماعی
→ get_document(136742) - about بیمه شخص ثالث
→ These cover different topics
→ Ask user: "منظورتان بیمه تامین اجتماعی است، بیمه درمان، یا بیمه اجباری شخص ثالث؟"
Total: 3 tool calls + clarifying question
```

### Example 3: Keyword Refinement (Learning Path)

**User**: "اگر کسی تصادف کند و پای کسی شکست باید چه مبلغی بپردازد؟"

**Agent reasoning**:
```
User asks in plain language about compensation for broken bone in accident.
I know the legal term is "دیه" (compensation in Islamic law).
→ search_documents("دیه شکستگی پا تصادف")
→ Top results score: 0.75-0.85 (good)
→ get_document(2487369) - advisory opinion about دیه for fractures
→ Opinion cites "ماده ۶۴۷ قانون مجازات اسلامی"
→ get_related_documents(2487369, relation_types=['قوانین'])
→ get_document(5709812) - the actual law article
→ Answer with both: advisory opinion explains the calculation, law provides legal basis
Total: 4 tool calls
```

### Example 4: Discovery and Refinement

**User**: "قوانین مربوط به استخدام شرکتی و بازنشستگی"

**Agent reasoning**:
```
User asks about contract employment and retirement.
→ search_documents("استخدام شرکتی بازنشستگی")
→ Results: 12 docs, top score: 0.68 (medium)
→ get_document(137982) - about "سابقه خدمت کارکنان شرکتی"
→ Reading: This mentions "قانون مدیریت خدمات کشوری ماده ۵۶"
→ Ah! The key legal concept is "سابقه خدمت شرکتی" (contract service record)
→ search_documents("سابقه خدمت شرکتی مستمری بازنشستگی قانون مدیریت خدمات")
→ Much better results: top score 0.89
→ get_document(254976) - perfect! Advisory opinion about counting contract service
→ get_related_documents(254976, relation_types=['قوانین'])
→ Answer with complete legal basis
Total: 5 tool calls (discovered better terminology mid-search)
```

---

### Example 5: Using Hierarchy Filter

**User**: "متن قانون مجازات اسلامی در مورد خدمات عمومی رایگان"

**Agent reasoning**:
```
User explicitly asks for "قانون" (law text), not opinions.
→ search_documents("قانون مجازات اسلامی خدمات عمومی رایگان", doc_types=['law'])
→ By filtering doc_types, I skip thousands of advisory opinions and go straight to laws
→ Results: 3 laws, top score: 0.92
→ get_document(5709812) - Article 84 of Islamic Penal Code
→ This is the actual law text the user wanted
→ Answer directly from the law
Total: 2 tool calls (hierarchy filter made search precise)
```

**Why this matters**: Without doc_types filter, search would return 50+ advisory opinions
about Article 84 before finding the actual law. The filter leverages the hierarchy to go
straight to the source.

## Trust Your Judgment

You are Claude - a highly capable language model with reasoning abilities.
You don't need rigid algorithms to search effectively.

**Read, reason, decide.**

- If results look good → load and answer
- If results look off → search again with better terms
- If you're unsure → ask the user
- If you need legal foundation → follow relations to parent laws

The tools are simple. Your reasoning makes them powerful.
```

---

## Configuration

Search behavior is configured via `config.yaml`:

```yaml
search:
  # PostgreSQL FTS configuration
  fts_config: persian_custom

  # Hard limits (enforced by tools)
  max_results_per_search: 20
  max_related_docs: 10
  max_document_load: 50  # Per conversation

  # Soft guidelines (in agent prompt)
  suggested_search_depth: "1-3 tool calls for most queries"
  suggested_doc_load_limit: "Load 2-3 full documents unless needed"

  # Performance tuning
  fts_ranking_normalization: 1  # ts_rank normalization method
  relation_traversal_depth: 1  # Direct relations only (no recursion in single call)

agent:
  model: claude-sonnet-4.5
  temperature: 0.0  # Deterministic for legal research

  # Agent behavior (injected into system prompt)
  search_instructions: |
    - Start with 1 search, refine if needed
    - Load full documents only when ready to answer
    - Follow relations to fetch cited laws when relevant
    - Stop when you can answer confidently
    - Most queries need 1-3 tool calls

  clarification_instructions: |
    Ask clarifying questions when:
    - Search returns diverse topics (ambiguous query)
    - Multiple contradictory interpretations exist
    - Results are about edge cases needing context
    Maximum 2-3 questions before giving best answer.
```

---

## Database Schema for Search

The search tools operate on this PostgreSQL schema:

```sql
-- Documents table
CREATE TABLE documents (
    doc_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    date DATE,
    category VARCHAR(100),
    tags TEXT[] NOT NULL DEFAULT '{}',

    -- Content: split for search vs answer
    summary TEXT NOT NULL,      -- For searching (200-500 words)
    full_content TEXT NOT NULL, -- For answering (800-2000 words)

    -- Full-text search vector
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('persian_custom', coalesce(title,'')), 'A') ||
        setweight(to_tsvector('persian_custom', coalesce(summary,'')), 'B')
    ) STORED,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Relations table
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    src_doc_id BIGINT NOT NULL REFERENCES documents(doc_id),
    dst_doc_id BIGINT NOT NULL REFERENCES documents(doc_id),
    relation_type VARCHAR(50) NOT NULL,
    UNIQUE(src_doc_id, dst_doc_id, relation_type)
);

-- Indexes for fast search
CREATE INDEX idx_search ON documents USING GIN(search_vector);
CREATE INDEX idx_tags ON documents USING GIN(tags);
CREATE INDEX idx_doc_type_date ON documents(doc_type, date DESC);
CREATE INDEX idx_category ON documents(category);

CREATE INDEX idx_rel_src_type ON relations(src_doc_id, relation_type);
CREATE INDEX idx_rel_dst ON relations(dst_doc_id);
```

### Why This Schema Works

1. **Split content**: `summary` for fast FTS, `full_content` loaded on-demand
2. **Generated search_vector**: Auto-updates, weights title > summary
3. **Tags as array**: Fast GIN index, no junction table needed
4. **Simple relations**: Source → Destination + Type, perfect for graph queries
5. **Minimal columns**: Only what's needed, no premature optimization

---

## Implementation Notes

### PostgreSQL Full-Text Search Setup

```sql
-- Create custom Persian text search configuration
CREATE TEXT SEARCH CONFIGURATION persian_custom (COPY = simple);

-- Add Persian stemming (if available)
CREATE TEXT SEARCH DICTIONARY persian_stem (
    TEMPLATE = snowball,
    Language = 'persian'
);

ALTER TEXT SEARCH CONFIGURATION persian_custom
    ALTER MAPPING FOR word, asciiword WITH persian_stem, simple;

-- Add stop words (common words to ignore)
CREATE TEXT SEARCH DICTIONARY persian_stopwords (
    TEMPLATE = simple,
    STOPWORDS = persian
);
```

### Tool Implementation (Python + SQLAlchemy)

```python
from sqlalchemy import select, func, text
from typing import List, Optional

class SearchTools:
    """Simple, stateless search tools for the agent"""

    def __init__(self, db_session):
        self.db = db_session

    def search_documents(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[dict]:
        """Direct FTS search - no logic"""

        stmt = select(
            Document.doc_id,
            Document.title,
            Document.summary,
            Document.doc_type,
            Document.tags,
            func.ts_rank(
                Document.search_vector,
                func.to_tsquery('persian_custom', query)
            ).label('relevance_score')
        ).where(
            Document.search_vector.op('@@')(
                func.to_tsquery('persian_custom', query)
            )
        )

        if tags:
            stmt = stmt.where(Document.tags.overlap(tags))

        stmt = stmt.order_by(text('relevance_score DESC')).limit(limit)

        results = self.db.execute(stmt).all()
        return [row._asdict() for row in results]

    def get_document(self, doc_id: int) -> dict:
        """Simple SELECT by ID"""
        doc = self.db.query(Document).filter_by(doc_id=doc_id).first()
        if not doc:
            return None
        return {
            'doc_id': doc.doc_id,
            'title': doc.title,
            'full_content': doc.full_content,
            'doc_type': doc.doc_type,
            'date': doc.date,
            'tags': doc.tags,
            'category': doc.category
        }

    def get_related_documents(
        self,
        doc_id: int,
        relation_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[dict]:
        """Simple JOIN on relations table"""

        stmt = select(
            Document.doc_id,
            Document.title,
            Document.summary,
            Document.doc_type,
            Document.tags,
            Relation.relation_type
        ).join(
            Relation, Relation.dst_doc_id == Document.doc_id
        ).where(
            Relation.src_doc_id == doc_id
        )

        if relation_types:
            stmt = stmt.where(Relation.relation_type.in_(relation_types))

        stmt = stmt.limit(limit)

        results = self.db.execute(stmt).all()
        return [row._asdict() for row in results]
```

### PydanticAI Integration

```python
from pydanticai import Agent

# Initialize search tools
search_tools = SearchTools(db_session)

# Create agent with tools
law_agent = Agent(
    'claude-sonnet-4.5',
    system_prompt=open('search.md').read(),  # Use this file as prompt
    tools=[
        search_tools.search_documents,
        search_tools.get_document,
        search_tools.get_related_documents
    ]
)

# Agent makes all search decisions
async def answer_question(user_query: str) -> str:
    result = await law_agent.run(user_query)
    return result.data
```

---

## Performance Characteristics

Based on 47K documents:

| Operation | Expected Time | Bottleneck |
|-----------|--------------|------------|
| `search_documents()` | 20-50ms | PostgreSQL FTS |
| `get_document()` | 5-10ms | Single row SELECT |
| `get_related_documents()` | 10-30ms | JOIN on relations |
| Full agent turn | 2-5s | LLM inference time |

**Search is not the bottleneck** - LLM thinking time dominates.

### Scaling Considerations

- **Current size**: 47K docs (~1.7GB)
- **PostgreSQL can handle**: 1M+ docs easily
- **If scaling needed**: Add read replicas, not new databases
- **FTS performance**: Sub-linear with doc count due to GIN indexes

---

## Observability

All tool calls are logged to Arize Phoenix for analysis:

```python
# Logged per tool call:
{
    'tool_name': 'search_documents',
    'input': {'query': 'بیمه کارگران', 'tags': None, 'limit': 20},
    'output': {'num_results': 12, 'top_score': 0.68},
    'latency_ms': 34,
    'timestamp': '2025-04-17T10:23:45Z'
}
```

### Metrics to Track

- Average tool calls per query
- Search effectiveness (score distribution)
- Multi-hop patterns (which tools are used together)
- Query refinement frequency (how often agent searches twice)
- Relation traversal usage (how often agent follows citations)

Use these to tune the agent's system prompt, not to change tool implementation.

---

## Why This Design

### Agent Makes Decisions, Not Code

**Traditional search systems**:
- Fixed algorithm: "Always do X, then Y, then Z"
- Hardcoded thresholds: "If score < 0.8, expand"
- Rules for everything: "Extract keywords with regex"

**This design**:
- Agent decides: "Do I need to search again? Let me reason..."
- No thresholds: Agent judges relevance from reading summaries
- No keyword extraction: Agent reads and discovers better terms

### Benefits

1. **Adaptive**: Different strategy for different query types
2. **Explainable**: Agent's reasoning is visible in traces
3. **Improvable**: Tune via prompt, not code refactoring
4. **Simple**: Three dumb tools, smart agent
5. **Debuggable**: Read agent's thinking in Phoenix traces

### Trade-offs

- Slightly higher latency (LLM decides at each step)
- Need good observability to understand agent behavior
- Prompt engineering is critical

But: **This is how agentic systems should work.** The agent is smart enough to decide strategy.

---

## Future Enhancements

Possible additions (all optional, evaluate based on usage):

### Vector Search (If Needed)
Add a fourth tool for semantic search:
```python
def semantic_search(query: str, limit: int = 20) -> List[DocSummary]:
    """Embedding-based semantic search as complement to FTS"""
    pass
```

Only add if analysis shows FTS missing relevant docs.

### Search Analytics Tool
Let agent see search patterns:
```python
def get_search_suggestions(topic: str) -> List[str]:
    """Common successful search queries for this topic"""
    pass
```

Only add if agent frequently struggles with terminology.

### Confidence Scoring
Add explanation to search results:
```python
# In search results, add:
{
    'doc_id': 123,
    'title': '...',
    'summary': '...',
    'relevance_score': 0.85,
    'relevance_explanation': 'Matches: بیمه (3x), کارگران (2x), قانون تامین اجتماعی'
}
```

Only add if agent needs help understanding why results are relevant.

**Default: Keep it simple. Three tools. Smart agent.**

---

## Summary

- **Three simple tools**: `search_documents`, `get_document`, `get_related_documents`
- **Agent decides everything**: When to search, when to refine, when to follow relations
- **No fixed algorithm**: Agent adapts strategy to query type
- **Keyword extraction via reasoning**: Agent reads summaries and discovers better terms
- **Multi-hop via decisions**: Agent decides whether to expand, not hardcoded logic
- **Configuration via prompt**: Tune agent behavior by updating system prompt
- **Observable**: All decisions logged to Phoenix for analysis

**This is truly agentic search.**
