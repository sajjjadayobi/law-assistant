# Task 0.2: Architecture Understanding Summary

This document captures key concepts learned from studying the Law Agent architecture.

---

## 1. Agentic Search vs. Traditional Algorithmic Search

### Traditional Algorithmic Search
- **Fixed workflow**: Predefined multi-stage algorithm (always do X, then Y, then Z)
- **Hardcoded thresholds**: Rules like "if score < 0.8, expand"
- **Mechanical keyword extraction**: Uses regex or NLP algorithms
- **Rigid logic**: Same path for every query type
- **Limited adaptability**: Cannot reason about context

### Agentic Search (Law Agent Approach)
- **Agent decides strategy**: No fixed algorithm - Claude reasons at each step
- **Dynamic evaluation**: Agent judges relevance by reading summaries, not thresholds
- **Reasoning-based refinement**: Agent reads results, discovers legal terminology, and refines
- **Adaptive paths**: Different strategies for different query types
- **Multi-hop via decisions**: Agent chooses when to search again, follow relations, or stop

**Key Principle**: Give the agent simple tools and let it decide the search strategy based on what it finds.

**Example**:
- Traditional: "Always extract keywords → search → if score < 0.8, expand"
- Agentic: "Search → Read top results → Reasoning: 'User said شکستگی but docs use دیه' → Search again with better term"

---

## 2. The 5 Document Types & Hierarchical Relationships

### Document Hierarchy (Top to Bottom)

```
Level 1: Laws (law)
   ↓ implemented by
Level 2: Regulations (regulation)
   ↓ interpreted by
Level 3: Advisory Opinions (advisory_opinion)
   ↓ applied in
Level 4: Court Rulings (court_ruling)
   ↓ unified by
Level 5: Unified Precedents (unified_precedent)
```

### Document Type Descriptions

1. **`law`**: Primary legislation - the legal foundation
   - Example: قانون مجازات اسلامی (Islamic Penal Code)
   - Characteristics: Foundational, cited by all other types
   - Percentage: ~4.2% of database (1,987 docs)

2. **`regulation`**: Implementation rules and amendments to laws
   - Example: آیین‌نامه‌های اجرایی (Executive Regulations)
   - Characteristics: Operational details for laws
   - Percentage: ~1.0% of database (456 docs)

3. **`advisory_opinion`**: Legal interpretations from the judiciary
   - Persian term: نظریه مشورتی
   - Characteristics: ALWAYS cite parent laws they interpret
   - Percentage: ~81.4% of database (38,456 docs)
   - **Most common type**

4. **`court_ruling`**: Case law applying laws to specific situations
   - Persian terms: دادنامه, احکام دادگاه
   - Characteristics: Real cases with fact patterns
   - Percentage: ~13.2% of database (6,234 docs)

5. **`unified_precedent`**: Supreme Court unified opinions
   - Persian term: رای وحدت رویه
   - Characteristics: Resolves contradictory interpretations
   - Percentage: ~0.2% of database (102 docs)
   - **Rarest type**

### Why Hierarchy Matters for Search

**Search Strategy**:
- User asks specific situation → Search opinions/rulings (they cite relevant laws)
- User asks general principle → Search laws directly
- User asks how law is applied → Search opinions, then fetch cited parent laws

**Agent Tool Use**:
- `search_documents(..., doc_types=['law'])` → Only search laws
- `get_related_documents(doc_id, relation_types=['قوانین'])` → Follow citations UP to parent laws

---

## 3. The Three Core Search Tools

### Tool 1: `search_documents`
**Purpose**: Full-text search on document summaries

```python
search_documents(
    query: str,
    tags: Optional[List[str]] = None,
    doc_types: Optional[List[str]] = None,
    limit: int = 20
) -> List[DocSummary]
```

**What it does**:
- PostgreSQL FTS on `summary` field (200-500 words)
- Returns: doc_id, title, summary, doc_type, tags, relevance_score
- Agent can call multiple times with different queries

**When to use**: Initial search, keyword refinement

---

### Tool 2: `get_document`
**Purpose**: Load full content of a specific document

```python
get_document(doc_id: int) -> FullDocument
```

**What it does**:
- Loads `full_content` field (800-2000 words)
- Returns complete document for answering

**When to use**: Only when ready to read for answering, after finding relevant doc_id via search

---

### Tool 3: `get_related_documents`
**Purpose**: Traverse the relations graph

```python
get_related_documents(
    doc_id: int,
    relation_types: Optional[List[str]] = None,
    limit: int = 10
) -> List[DocSummary]
```

**What it does**:
- Follows citations from one document to related documents
- Relation types: 'قوانین' (cited laws), 'مواد مرتبط' (related articles)
- Traverses the legal document DAG

**When to use**: Fetch parent laws, explore legal graph, get complete legal basis

---

### Multi-Hop Search Patterns

**Pattern 1: Search → Read → Search Again**
- Initial search finds related topic
- Read summaries, discover legal terminology
- Search again with refined keywords

**Pattern 2: Search → Follow Relations → Read (Using Hierarchy)**
- Search finds advisory opinion (lower level)
- Opinion cites parent law (higher level)
- Fetch parent law using `get_related_documents(..., relation_types=['قوانین'])`

**Pattern 3: Search → Expand → Synthesize**
- Search finds one relevant document
- Fetch related docs via graph
- Read multiple perspectives and synthesize

---

## 4. The DAG (Directed Acyclic Graph) Structure

### Relations Table Schema

```sql
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    src_doc_id BIGINT REFERENCES documents(doc_id),
    dst_doc_id BIGINT REFERENCES documents(doc_id),
    relation_type VARCHAR(50)  -- Persian: 'قوانین', 'مواد مرتبط'
);
```

### Why It's a DAG, Not a Simple Tree

**Directed**: Edges have direction (src → dst)
- Advisory opinion → cites → Parent law

**Acyclic**: No cycles (prevents infinite loops)
- Legal documents don't cite themselves in circular fashion
- Lower-level docs cite higher-level (no backwards citations)

**Graph (not tree)**: Multiple parents, cross-branch connections
- One advisory opinion can cite multiple laws
- Different legal branches interconnect

### Document Graph Structure

```
      Laws
       ↓ ↓ ↓
   Regulations & Advisory Opinions
       ↓  ↓
    Court Rulings
       ↓
  Unified Precedents
```

**Cross-branch connections**: Drug laws ←→ Tax evasion laws (via 'مواد مرتبط')

### Graph Traversal

**Find Ancestors** (going UP hierarchy):
```sql
-- Find all laws cited by a document
SELECT * FROM relations WHERE src_id = [doc_id] AND relation_type = 'قوانین'
```

**Find Descendants** (going DOWN hierarchy):
```sql
-- Find all opinions that cite a specific law
SELECT * FROM relations WHERE dst_id = [law_id]
```

### Why DAG Matters for Agent

- **Context expansion**: Automatically fetch connected ancestors (parent laws)
- **Precedent chains**: Follow citations to build legal arguments
- **Complete legal basis**: Get both specific opinion AND foundational law
- **Depth limiting**: Cap at 3-4 levels to manage token usage

---

## 5. Persian Text Normalization - Why Critical

### The Problem: Character Variants

Persian text has multiple Unicode representations for the same character:

| Character | Arabic Form | Persian Form | Issue |
|-----------|-------------|--------------|-------|
| ک (kaf) | ك (U+0643) | ک (U+06A9) | Search for "ك" won't find "ک" |
| ی (ye) | ي (U+064A) | ی (U+06CC) | Search for "ي" won't find "ی" |

**Example failure**:
- User searches: "بیمه" (with ی)
- Database has: "بيمه" (with ي - Arabic form)
- **Result: NO MATCH!** (even though semantically identical)

### Other Normalization Issues

1. **Zero-width characters**: `&zwnj;` (zero-width non-joiner) used in Persian but invisible
2. **HTML entities**: `&nbsp;`, `&shy;` from HTML content
3. **Diacritics**: Optional vowel marks that shouldn't affect search
4. **Multiple spaces**: Should collapse to single space

### Migration Solution

The migration script uses **Hazm library** to normalize ALL text:

```python
# Normalization steps:
1. Convert HTML entities: &nbsp; → space, &zwnj; → ZWNJ
2. Normalize Persian: ك→ک, ي→ی (Arabic→Persian forms)
3. Remove diacritics: Keep base characters only
4. Collapse whitespace: Multiple spaces → single space
```

### Why This Matters

**Without normalization**:
- Search fails for ~30-40% of queries (due to mixed Arabic/Persian characters in data)
- User frustration: "I know this exists but can't find it!"
- Agent cannot find relevant documents

**With normalization**:
- Consistent character encoding across all documents
- Search works regardless of input character variant
- FTS vector built on normalized text
- Agent finds all relevant documents reliably

### PostgreSQL FTS Configuration

```sql
CREATE TEXT SEARCH CONFIGURATION persian_custom (COPY = simple);
-- Applies Persian-specific stemming and stop words
-- All queries automatically normalized before search
```

---

## Database Migration: Old → New Schema

### Key Transformations

| Aspect | Old Schema (Website) | New Schema (Agent) |
|--------|---------------------|-------------------|
| Content | HTML in single `content` field | Split: `summary` (search) + `full_content` (answer) |
| Tags | Junction table `page_tags` | TEXT[] array (flattened) |
| Metadata | None | **NEW**: `doc_type`, `date` (inferred) |
| FTS | None | **NEW**: Auto-generated `search_vector` |
| Columns | Many processing flags | Minimal (removed flags) |

### Why This Design

1. **Split content**: Fast FTS on summary, load full content only when needed
2. **Flattened tags**: No JOINs needed, GIN index for fast array search
3. **Inferred metadata**: Enables filtering by doc_type, temporal search
4. **Auto-generated FTS**: Always in sync, weighted (title > summary)

---

## Summary: Task 0.2 Definition of Done

✅ **Can explain "agentic search" vs traditional algorithmic search**
- Agent decides strategy dynamically vs. fixed algorithm

✅ **Can describe the 5 document types and their hierarchical relationships**
- Laws → Regulations → Advisory Opinions → Court Rulings → Unified Precedents

✅ **Can name the 3 core search tools and their purposes**
- `search_documents`: FTS on summaries
- `get_document`: Load full content
- `get_related_documents`: Traverse DAG

✅ **Understand the DAG structure in the relations table**
- Directed: src → dst citations
- Acyclic: No cycles, hierarchy enforced
- Graph: Multiple parents, cross-branch connections

✅ **Understand why Persian text normalization is critical**
- Arabic vs Persian character variants cause search failures
- Normalization ensures consistent encoding
- Enables reliable FTS across all documents

---

**Completed**: 2026-04-18
**Task**: 0.2 - Study Project Architecture
