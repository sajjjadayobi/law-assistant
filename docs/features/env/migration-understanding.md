# Phase 1: Database Migration Understanding

This document summarizes the migration requirements and transformation process from the old HTML-based schema to the clean, agent-optimized schema.

---

## Migration Overview

### Purpose
Transform the existing PostgreSQL database from a website-oriented schema (with HTML content) to a minimal, clean schema optimized for agent search.

### Key Transformations

| Aspect | Old (Website) | New (Agent) | Reason |
|--------|--------------|-------------|---------|
| **Content** | Single `content` field with HTML | Split into `summary` + `full_content` (clean text) | Fast FTS on summary, load full content on-demand |
| **Tags** | Junction table (`page_tags`) | TEXT[] array | No JOINs needed, GIN index for fast search |
| **Metadata** | None | `doc_type`, `date` (inferred) | Enable filtering by type and temporal search |
| **FTS** | Manual | Auto-generated `search_vector` | Always in sync, weighted (title > summary) |
| **Fields** | 8+ fields with processing flags | 7 essential fields only | Minimal, focused schema |

---

## Schema Comparison

### Old Schema (pages table)

```sql
CREATE TABLE pages (
    page_id BIGINT PRIMARY KEY,
    content TEXT,  -- FULL HTML WITH CSS/JS
    title VARCHAR,
    relations_built BOOLEAN,
    relations_in_progress BOOLEAN,
    relations_started_at TIMESTAMP,
    http_status VARCHAR,
    created_at TIMESTAMP
);

CREATE TABLE tags (tag_id, tag_name, category);
CREATE TABLE page_tags (page_id, tag_id);  -- Junction
CREATE TABLE relations (id, src_id, dst_id, relation_name);
```

### New Schema (documents table)

```sql
CREATE TABLE documents (
    doc_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,  -- NEW: inferred
    date DATE,  -- NEW: extracted & converted
    summary TEXT NOT NULL,  -- NEW: from خلاصه متن
    full_content TEXT NOT NULL,  -- NEW: cleaned
    tags TEXT[],  -- CHANGED: flattened array
    search_vector tsvector,  -- NEW: auto-generated
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT valid_doc_type CHECK (
        doc_type IN ('law', 'regulation', 'advisory_opinion',
                     'court_ruling', 'unified_precedent')
    )
);

CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    src_doc_id BIGINT REFERENCES documents(doc_id),
    dst_doc_id BIGINT REFERENCES documents(doc_id),
    relation_type VARCHAR(50),
    UNIQUE(src_doc_id, dst_doc_id, relation_type),
    CONSTRAINT no_self_reference CHECK (src_doc_id != dst_doc_id)
);
```

---

## HTML Parsing & Text Extraction

### Summary Extraction (`extract_summary_from_html`)

**Strategy**:
1. Find `<span>خلاصه متن</span>` label
2. Navigate to parent div
3. Find content div with `line-clamp` class
4. Extract text, strip all HTML
5. **Fallback**: First 500 words from main content

**Output**: 200-500 word clean text summary

### Full Content Extraction (`extract_full_content_from_html`)

**Strategy**:
1. Find `<div class="post-text">` main content area
2. Remove unwanted elements:
   - `<script>`, `<style>`, `<section>` tags
   - Livewire components (JSON metadata)
   - Print-hidden sections
3. Extract text with line breaks preserved
4. Clean and normalize
5. Remove excessive line breaks (>2 consecutive)

**Output**: 800-2000 word clean full document text

### Text Cleaning (`clean_text`)

**Normalizations Applied**:
1. **HTML entities**:
   - `&nbsp;` → space
   - `&zwnj;` → zero-width non-joiner (‌)
   - `&lt;`, `&gt;` → `<`, `>`
   - `<br>`, `<br/>` → `\n`

2. **Persian character normalization**:
   - `ك` (Arabic kaf) → `ک` (Persian kaf)
   - `ي` (Arabic yeh) → `ی` (Persian yeh)
   - `ى` (Alef maksura) → `ی` (Persian yeh)

3. **Whitespace cleanup**:
   - Multiple spaces → single space
   - Leading/trailing spaces on lines → removed
   - Final strip()

---

## Metadata Inference

### Document Type Inference (`infer_doc_type`)

**Rules (in priority order)**:

```python
if 'نظریه مشورتی' in title or content:
    return 'advisory_opinion'

elif 'دادنامه' or 'رای دادگاه' in title:
    return 'court_ruling'

elif 'رای وحدت رویه' in title:
    return 'unified_precedent'

elif 'آیین‌نامه' or 'مقررات' in title:
    return 'regulation'

elif 'قانون' in title and 'نظریه' not in title:
    return 'law'

else:
    return 'advisory_opinion'  # Default (81.4% of corpus)
```

**Expected Distribution**:
- advisory_opinion: ~81.4% (38,456 docs)
- court_ruling: ~13.2% (6,234 docs)
- law: ~4.2% (1,987 docs)
- regulation: ~1.0% (456 docs)
- unified_precedent: ~0.2% (102 docs)

### Date Extraction & Conversion (`extract_date_from_document`)

**Pattern**: `YYYY/MM/DD` in Latin or Persian digits

**Process**:
1. Search title first (most reliable)
2. Fallback: First 300 chars of content
3. Convert Persian digits to Latin: `۱۳۹۸` → `1398`
4. Parse as Persian (Jalali) date
5. Convert to Gregorian using `jdatetime` library

**Example**:
- Persian: `1398/03/25`
- Gregorian: `2019-06-15`

**Coverage**: ~89.1% of documents have dates

---

## Migration Process

### Phase 1: Migrate Documents

```python
migrate_documents(old_conn, new_conn, batch_size=500)
```

**Steps**:
1. Read from `pages` table (where `relations_built = true`)
2. For each document:
   - Parse HTML with BeautifulSoup
   - Extract summary and full content
   - Infer doc_type and date
   - Validate (summary >= 50 chars)
3. Batch insert into `documents` table (500 at a time)
4. Progress reporting every batch

**Output**: ~47,235 documents migrated

### Phase 2: Migrate Tags

```python
migrate_tags(old_conn, new_conn)
```

**Steps**:
1. Join `page_tags` and `tags` tables
2. Filter: only tags with `category = 'subjects'`
3. Aggregate tags per document into array
4. Batch update `documents.tags` field (1000 at a time)

**Output**: ~74.6% of documents have tags

### Phase 3: Migrate Relations

```python
migrate_relations(old_conn, new_conn)
```

**Steps**:
1. Direct copy from old `relations` table
2. Map: `src_id` → `src_doc_id`, `dst_id` → `dst_doc_id`
3. Preserve `relation_type` in Persian
4. Batch insert (5000 at a time)

**Output**: ~185,429 relations migrated

### Phase 4: Validation

```python
validate_migration(new_conn)
```

**Checks**:
1. Document count
2. Document type distribution
3. Documents with dates (should be ~89%)
4. Documents with tags (should be ~75%)
5. Relations count
6. Sample document (verify clean text)
7. Search vectors created (should be 100%)

---

## PostgreSQL FTS Configuration

### Text Search Configuration

```sql
CREATE TEXT SEARCH CONFIGURATION persian_custom (COPY = simple);
```

**Purpose**: Persian-specific full-text search

**Features**:
- Persian stemming (if available)
- Persian stop words
- Handles Persian character variants

### Auto-Generated Search Vector

```sql
search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('persian_custom', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('persian_custom', coalesce(summary, '')), 'B')
) STORED
```

**Design**:
- **Title**: Weight 'A' (highest)
- **Summary**: Weight 'B' (medium)
- **Full content**: NOT indexed (too large, use summary for search)
- **Auto-updated**: Always in sync with content

### Indexes Created

```sql
-- FTS index (most important)
CREATE INDEX idx_fts_search ON documents USING GIN(search_vector);

-- Tag filtering
CREATE INDEX idx_tags_gin ON documents USING GIN(tags);

-- Doc type filtering
CREATE INDEX idx_doc_type ON documents(doc_type);

-- Date sorting
CREATE INDEX idx_date_desc ON documents(date DESC NULLS LAST);

-- Compound index
CREATE INDEX idx_doc_type_date ON documents(doc_type, date DESC NULLS LAST);

-- Relations indexes
CREATE INDEX idx_rel_src_type ON relations(src_doc_id, relation_type);
CREATE INDEX idx_rel_dst ON relations(dst_doc_id);
CREATE INDEX idx_rel_dst_type ON relations(dst_doc_id, relation_type);
```

---

## Migration Performance

**With 47K documents**:
- **Migration time**: ~10-15 minutes
- **Old database size**: ~1.3 GB (with HTML)
- **New database size**: ~1.9 GB (clean text + indexes)
- **Index size**: ~370 MB
- **Search speed**: <50ms per query

**Bottleneck**: HTML parsing with BeautifulSoup (CPU-bound)

---

## Dependencies Required

```bash
pip install psycopg2-binary beautifulsoup4 jdatetime
```

**Versions**:
- `psycopg2-binary`: PostgreSQL adapter
- `beautifulsoup4`: HTML parsing
- `jdatetime`: Persian (Jalali) to Gregorian date conversion

---

## Migration Script Configuration

### Database Connections (lines 528-540)

**Old Database (Source)**:
```python
OLD_DB = {
    'host': 'localhost',
    'database': 'knowledge',  # Old database name
    'user': 'postgres',
    'password': 'your_password'
}
```

**New Database (Target)**:
```python
NEW_DB = {
    'host': 'localhost',
    'database': 'law_agent',  # New clean database
    'user': 'postgres',
    'password': 'your_password'
}
```

**Note**: Need to update password before running

---

## Running the Migration

### Prerequisites

1. **Install dependencies**:
   ```bash
   source .venv/bin/activate
   pip install psycopg2-binary beautifulsoup4 jdatetime
   ```

2. **Create target database**:
   ```bash
   createdb law_agent
   ```

3. **Run schema creation**:
   ```bash
   psql -d law_agent -f docs/architecture/migration/schema.sql
   ```

### Execute Migration

```bash
python docs/architecture/migration/migrate.py
```

### Post-Migration

```bash
# Analyze for query planner
psql -d law_agent -c "ANALYZE documents;"

# Test search
psql -d law_agent -c "
SELECT doc_id, title, ts_rank(search_vector, query) as score
FROM documents, to_tsquery('persian_custom', 'بیمه') as query
WHERE search_vector @@ query
ORDER BY score DESC
LIMIT 10;
"
```

---

## Current Status

**Source Database**:
- Database name: `knowledge`
- **Status**: ❌ NOT AVAILABLE (need to obtain dump/backup)
- Required for migration

**Target Database**:
- Database name: `law_agent`
- **Status**: Not yet created
- Will be created once source is available

---

## Next Steps

1. **Obtain source database**:
   - Get `knowledge` database dump
   - Or restore from backup
   - Or connect to existing instance

2. **Prepare environment**:
   - Create `law_agent` database
   - Run `schema.sql`
   - Install Python dependencies

3. **Configure migration script**:
   - Update database credentials
   - Set correct passwords

4. **Run migration**:
   - Execute `migrate.py`
   - Monitor progress (10-15 min)
   - Validate results

5. **Test search**:
   - Run sample queries
   - Verify FTS works
   - Check document quality

---

## Migration Results (Completed)

### Final Statistics

**Source Database** (`knowledge`):
- Total pages: 204,423
- Total tags: 1,452
- Total page-tag associations: 283,513
- Total relations: 300,304

**Target Database** (`law_agent`):
- **Documents migrated**: 201,434 (98.5% success rate)
- **Documents skipped**: 2,989 (summaries < 50 chars)
- **Relations migrated**: 300,174
- **Relations skipped**: 130 (referenced non-existent documents)

### Document Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| advisory_opinion | 148,965 | 74.0% |
| law | 22,863 | 11.4% |
| court_ruling | 17,620 | 8.7% |
| regulation | 10,004 | 5.0% |
| unified_precedent | 1,982 | 1.0% |

### Data Quality Metrics

- **Documents with dates**: 100,488 (49.9%)
- **Documents with tags**: 6,235 (3.1% - only "subjects" category)
- **Search vectors created**: 201,434 (100%)
- **FTS tested**: ✓ Working (Persian search validated)
- **Graph traversal tested**: ✓ Working (relations validated)

### Migration Duration

- **Total time**: ~25 minutes
- **Documents**: ~20 minutes (201K documents @ ~10K/min)
- **Tags**: ~1 minute
- **Relations**: ~3 minutes (300K relations)
- **Validation**: <1 minute

### Key Findings

1. **Lower date coverage**: Only 49.9% vs expected 89% - many documents don't have dates in title/content
2. **Lower tag coverage**: Only 3.1% vs expected 74.6% - only "subjects" category tags were migrated
3. **Document type distribution**: Different from docs (74% vs 81.4% advisory opinions) - larger dataset
4. **Migration success rate**: 98.5% success, 1.5% skipped due to insufficient summary content

### Tested Features

✅ **Persian Full-Text Search**:
```sql
SELECT doc_id, title, ts_rank(search_vector, query) as score
FROM documents, to_tsquery('persian_custom', 'بیمه') as query
WHERE search_vector @@ query
ORDER BY score DESC LIMIT 5;
```
Result: 5 documents found with relevance scores 0.89-0.91

✅ **Graph Traversal**:
```sql
SELECT d.title, r.relation_type, COUNT(*) as count
FROM documents d
JOIN relations r ON d.doc_id = r.src_doc_id
WHERE d.doc_id = 1635489
GROUP BY d.title, r.relation_type;
```
Result: 3 'قوانین' + 6 'مواد مرتبط' relations found

---

**Task 1.1 Status**: ✓ Complete
**Task 1.2 Status**: ✓ Complete
**Phase 1**: ✅ **COMPLETED**

**Completed**: 2026-04-18
**Phase**: 1 - Database Migration
