# Migrated Database Documentation: law_agent

**Database**: PostgreSQL 14.22
**Schema**: Clean, minimal, agent-optimized
**Size**: 1.1 GB (documents) + 67 MB (relations)
**Records**: 201,434 documents + 300,174 relations

---

## Overview

The `law_agent` database is a clean, minimal schema optimized for AI agent search. All HTML has been removed, Persian text normalized, and unnecessary fields stripped away. The database contains Iranian legal documents organized in a directed acyclic graph (DAG) structure.

---

## Schema

### Table 1: `documents` (1,057 MB, 201,434 records)

Primary table storing legal documents with clean text only.

```sql
CREATE TABLE documents (
    -- Identifiers
    doc_id BIGINT PRIMARY KEY,

    -- Metadata
    title TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,  -- enum: see constraint below
    date DATE,  -- Gregorian (converted from Persian)

    -- Content (clean text, no HTML)
    summary TEXT NOT NULL,       -- 200-500 words for searching
    full_content TEXT NOT NULL,  -- Full document for answering

    -- Classification
    tags TEXT[] NOT NULL DEFAULT '{}',  -- Subject tags array

    -- Full-text search (auto-generated)
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('persian_custom', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('persian_custom', coalesce(summary, '')), 'B')
    ) STORED,

    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_doc_type CHECK (
        doc_type IN ('law', 'regulation', 'advisory_opinion',
                     'court_ruling', 'unified_precedent')
    )
);
```

#### Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| `doc_id` | BIGINT | Original page_id from source (knowledge database) |
| `title` | TEXT | Document title in Persian, cleaned |
| `doc_type` | VARCHAR(50) | Document type (see types below) |
| `date` | DATE | Gregorian date converted from Persian date in title/content |
| `summary` | TEXT | 200-500 word summary from خلاصه متن, used for search |
| `full_content` | TEXT | Full document text, all HTML/CSS/JS removed |
| `tags` | TEXT[] | Array of subject tags (اداری, خانواده, etc.) |
| `search_vector` | tsvector | Auto-generated FTS vector: title (A) + summary (B) |
| `created_at` | TIMESTAMP | Migration timestamp |

#### Document Types

| Type | Persian | Count | % | Description |
|------|---------|-------|---|-------------|
| `advisory_opinion` | نظریه مشورتی | 148,965 | 74.0% | Legal interpretations from judiciary |
| `law` | قانون | 22,863 | 11.4% | Primary legislation |
| `court_ruling` | دادنامه | 17,620 | 8.7% | Court decisions |
| `regulation` | آیین‌نامه | 10,004 | 5.0% | Implementation rules |
| `unified_precedent` | رای وحدت رویه | 1,982 | 1.0% | Supreme Court unified opinions |

#### Document Hierarchy

```
Laws (قانون)
  ↓ implemented by
Regulations (آیین‌نامه)
  ↓ interpreted by
Advisory Opinions (نظریه مشورتی)
  ↓ applied in
Court Rulings (دادنامه)
  ↓ unified by
Unified Precedents (رای وحدت رویه)
```

#### Indexes (153 MB total)

```sql
-- Full-text search (most important, 96 MB)
CREATE INDEX idx_fts_search ON documents USING GIN(search_vector);

-- Tag filtering (1.5 MB)
CREATE INDEX idx_tags_gin ON documents USING GIN(tags);

-- Doc type filtering (1.7 MB)
CREATE INDEX idx_doc_type ON documents(doc_type);

-- Date sorting (1.9 MB)
CREATE INDEX idx_date_desc ON documents(date DESC NULLS LAST);

-- Compound index for filtered searches (2.8 MB)
CREATE INDEX idx_doc_type_date ON documents(doc_type, date DESC NULLS LAST);
```

---

### Table 2: `relations` (67 MB, 300,174 records)

Document citation graph: src_doc_id → dst_doc_id

```sql
CREATE TABLE relations (
    id SERIAL PRIMARY KEY,

    -- Graph edge
    src_doc_id BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    dst_doc_id BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,

    -- Relation type (Persian)
    relation_type VARCHAR(50) NOT NULL,

    -- Constraints
    UNIQUE(src_doc_id, dst_doc_id, relation_type),
    CONSTRAINT no_self_reference CHECK (src_doc_id != dst_doc_id)
);
```

#### Column Descriptions

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL | Auto-incrementing primary key |
| `src_doc_id` | BIGINT | Source document (citing document) |
| `dst_doc_id` | BIGINT | Destination document (cited document) |
| `relation_type` | VARCHAR(50) | Type of relation in Persian |

#### Relation Types (17 types)

| Type (Persian) | Type (English) | Count | % |
|----------------|----------------|-------|---|
| مواد مرتبط | Related articles | 176,733 | 58.9% |
| قوانین | Laws | 101,787 | 33.9% |
| نظریه‌های مشورتی | Advisory opinions | 10,394 | 3.5% |
| نشست‌های قضایی | Judicial sessions | 7,642 | 2.5% |
| آرای وحدت رویه د.ع.ک | Unified precedents | 2,033 | 0.7% |
| آیین‌نامه‌ها | Regulations | 1,052 | 0.4% |
| دادنامه و رای | Court rulings | 260 | 0.1% |
| دستورالعمل‌ها | Guidelines | 108 | 0.04% |
| ... (9 more types) | ... | 165 | 0.05% |

#### Graph Structure

- **Type**: Directed Acyclic Graph (DAG)
- **Direction**: src_doc_id → dst_doc_id (citing → cited)
- **Hierarchy**: Lower-level docs cite higher-level docs (opinions → laws)
- **Most cited**: Civil Procedure Code (16,815 citations)
- **Most citing**: Article 522 Civil Procedure Code (377 citations)

#### Indexes (46 MB total)

```sql
-- Forward traversal: get documents this document cites (10 MB)
CREATE INDEX idx_rel_src_type ON relations(src_doc_id, relation_type);

-- Backward traversal: get documents that cite this one (3.3 MB)
CREATE INDEX idx_rel_dst ON relations(dst_doc_id);

-- Backward with type filter (4.2 MB)
CREATE INDEX idx_rel_dst_type ON relations(dst_doc_id, relation_type);

-- Unique constraint index (22 MB)
CREATE UNIQUE INDEX ON relations(src_doc_id, dst_doc_id, relation_type);
```

---

## Text Search Configuration

### Persian FTS Configuration

```sql
CREATE TEXT SEARCH CONFIGURATION persian_custom (COPY = simple);
```

**Features**:
- Persian-specific stemming
- Persian stop words
- Handles Persian character variants
- Configured for `search_vector` generation

**Character Normalization**:
- Arabic kaf (ك) → Persian kaf (ک)
- Arabic yeh (ي) → Persian yeh (ی)
- Alef maksura (ى) → Persian yeh (ی)

**Coverage**: 99.99% normalized (only 1 doc with Arabic chars)

---

## Common Query Patterns

### 1. Full-Text Search

```sql
-- Simple search
SELECT doc_id, title, ts_rank(search_vector, query) as score
FROM documents, to_tsquery('persian_custom', 'بیمه') as query
WHERE search_vector @@ query
ORDER BY score DESC
LIMIT 10;

-- Search with AND operator
SELECT doc_id, title
FROM documents
WHERE search_vector @@ to_tsquery('persian_custom', 'مجازات & اسلامی')
LIMIT 10;

-- Search with filters
SELECT doc_id, title, doc_type
FROM documents, to_tsquery('persian_custom', 'قانون') as query
WHERE search_vector @@ query
  AND doc_type = 'law'
  AND date >= '2010-01-01'
ORDER BY ts_rank(search_vector, query) DESC;
```

### 2. Filter by Document Type

```sql
-- Get all laws
SELECT doc_id, title, date
FROM documents
WHERE doc_type = 'law'
ORDER BY date DESC NULLS LAST;

-- Get recent advisory opinions
SELECT doc_id, title, date
FROM documents
WHERE doc_type = 'advisory_opinion'
  AND date >= '2020-01-01'
ORDER BY date DESC;
```

### 3. Filter by Tags

```sql
-- Documents with specific tag
SELECT doc_id, title, tags
FROM documents
WHERE 'اداری' = ANY(tags);

-- Documents with multiple tags
SELECT doc_id, title, tags
FROM documents
WHERE tags && ARRAY['اداری', 'خانواده'];
```

### 4. Graph Traversal (Forward)

```sql
-- Get documents that this document cites
SELECT
    r.relation_type,
    d.doc_id,
    d.title,
    d.doc_type
FROM relations r
JOIN documents d ON r.dst_doc_id = d.doc_id
WHERE r.src_doc_id = 1635489
ORDER BY r.relation_type;

-- Get only cited laws
SELECT d.doc_id, d.title
FROM relations r
JOIN documents d ON r.dst_doc_id = d.doc_id
WHERE r.src_doc_id = 1635489
  AND r.relation_type = 'قوانین'
  AND d.doc_type = 'law';
```

### 5. Graph Traversal (Backward)

```sql
-- Get documents that cite this document
SELECT
    r.relation_type,
    d.doc_id,
    d.title,
    d.doc_type
FROM relations r
JOIN documents d ON r.src_doc_id = d.doc_id
WHERE r.dst_doc_id = 5709812  -- Islamic Penal Code
ORDER BY r.relation_type;

-- Count citations by type
SELECT relation_type, COUNT(*) as citation_count
FROM relations
WHERE dst_doc_id = 5709812
GROUP BY relation_type
ORDER BY citation_count DESC;
```

### 6. Multi-Hop Traversal

```sql
-- Get cited documents and their parent laws (2 hops)
WITH cited_docs AS (
    SELECT dst_doc_id
    FROM relations
    WHERE src_doc_id = 1635489
      AND relation_type = 'مواد مرتبط'
)
SELECT DISTINCT d.doc_id, d.title, d.doc_type
FROM cited_docs cd
JOIN relations r ON cd.dst_doc_id = r.src_doc_id
JOIN documents d ON r.dst_doc_id = d.doc_id
WHERE r.relation_type = 'قوانین'
  AND d.doc_type = 'law';
```

---

## Data Quality Metrics

### Coverage

| Metric | Count | Percentage |
|--------|-------|------------|
| Total documents | 201,434 | 100% |
| Documents with dates | 100,488 | 49.9% |
| Documents with tags | 6,235 | 3.1% |
| Documents with search vectors | 201,434 | 100% |

### Content Quality

| Metric | Value |
|--------|-------|
| Persian normalization | 99.99% |
| HTML removal success | 99.91% |
| Average summary length | ~720 chars |
| Average full_content length | ~2,400 chars |

### Date Range

| Metric | Value |
|--------|-------|
| Earliest date | 1920-01-03 |
| Latest date | 2025-03-10 |
| Span | 105 years |
| Peak period | 2010s (48,665 docs) |

### Graph Metrics

| Metric | Value |
|--------|-------|
| Total relations | 300,174 |
| Relation types | 17 |
| Most cited document | Civil Procedure Code (16,815) |
| Most citing document | Article 522 (377) |

---

## Performance Characteristics

### Query Performance (201K documents)

| Query Type | Execution Time | Notes |
|------------|----------------|-------|
| Simple FTS | ~1.6s | First query with planning |
| Simple FTS (cached) | ~200ms | Subsequent queries |
| Complex FTS + filters | ~150ms | Uses bitmap index scan |
| Graph aggregation | ~660ms | Parallel query execution |

### Index Usage

- ✅ All FTS queries use `idx_fts_search` (GIN index)
- ✅ Type filters use `idx_doc_type` or `idx_doc_type_date`
- ✅ Graph queries use `idx_rel_src_type` or `idx_rel_dst_type`
- ✅ No sequential scans on large tables

### Optimization Tips

1. **Always use `to_tsquery()`** for FTS, not `LIKE`
2. **Combine filters** for better performance (uses bitmap scan)
3. **Use relation type filters** to reduce graph traversal
4. **Limit multi-hop queries** to 2-3 levels (token usage)
5. **Use `ANALYZE`** after bulk updates

---

## Database Maintenance

### Regular Maintenance

```sql
-- Update statistics (run weekly)
ANALYZE documents;
ANALYZE relations;

-- Vacuum (run monthly)
VACUUM ANALYZE documents;
VACUUM ANALYZE relations;

-- Reindex (if search performance degrades)
REINDEX INDEX idx_fts_search;
```

### Monitoring

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    pg_size_pretty(pg_relation_size(quote_ident(schemaname)||'.'||quote_ident(indexname))) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- Check slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE query LIKE '%documents%'
ORDER BY mean_time DESC
LIMIT 10;
```

---

## Connection Information

### Local Development

```bash
# Connect to database
psql -d law_agent

# With full path (if not in PATH)
/opt/homebrew/opt/postgresql@14/bin/psql -d law_agent

# Connection string
postgresql://localhost/law_agent
```

### Python (psycopg2)

```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='law_agent',
    user='divar'
)
```

---

## Migration History

### Source Database
- **Name**: `knowledge`
- **Size**: 1.3 GB (with HTML)
- **Records**: 204,423 pages
- **Schema**: 4 tables (pages, tags, page_tags, relations)

### Migration Date
- **Completed**: 2026-04-18
- **Duration**: ~25 minutes
- **Success Rate**: 98.5% (201,434 / 204,423)
- **Skipped**: 2,989 documents (summary < 50 chars)

### Changes Applied
1. ✅ Stripped all HTML tags
2. ✅ Normalized Persian characters (ك→ک, ي→ی)
3. ✅ Split content: summary + full_content
4. ✅ Inferred doc_type from title/content patterns
5. ✅ Extracted Persian dates, converted to Gregorian
6. ✅ Flattened tags (junction table → array)
7. ✅ Auto-generated FTS vectors
8. ✅ Removed processing flags (relations_built, etc.)

---

## Developer Notes

### Best Practices

1. **Search Strategy**:
   - Use `summary` for search (via FTS)
   - Load `full_content` only when ready to answer
   - Follow relations to get parent laws

2. **Date Handling**:
   - 50% of documents don't have dates
   - Always use `NULLS LAST` when sorting by date
   - Filter by reasonable range (1920-2030)

3. **Tag Usage**:
   - Only 3.1% have tags (limited coverage)
   - Don't rely on tags for primary filtering
   - Use FTS + doc_type instead

4. **Graph Traversal**:
   - Most common: 'مواد مرتبط' and 'قوانین'
   - Advisory opinions cite laws (not vice versa)
   - Limit recursive queries to 3-4 levels

5. **Performance**:
   - FTS on 200K docs: sub-second
   - Always use indexes (check with EXPLAIN)
   - Batch updates, then ANALYZE

### Common Pitfalls

❌ **Don't**:
- Use `LIKE '%term%'` for Persian search (use FTS)
- Traverse graph without relation_type filter (slow)
- Assume all documents have dates or tags
- Use sequential scans on large tables

✅ **Do**:
- Use `to_tsquery()` for all text search
- Filter by doc_type + date for better performance
- Check for NULL dates in application logic
- Use EXPLAIN ANALYZE to verify index usage

---

## Support

For issues or questions:
1. Check query performance with `EXPLAIN ANALYZE`
2. Verify index usage with `pg_stat_user_indexes`
3. Review migration docs: `docs/features/env/migration-understanding.md`
4. Review test results: `docs/features/env/migration-test-results.md`

---

**Database Version**: PostgreSQL 14.22
**Last Updated**: 2026-04-18
**Status**: Production Ready ✅
