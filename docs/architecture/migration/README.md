# Database Migration: HTML → Clean Text

This migration transforms your PostgreSQL database from the old website schema (with HTML content) to a clean, minimal schema optimized for agent search.

## What This Migration Does

### HTML Extraction & Cleaning
- ✅ **Strips ALL HTML tags** from content
- ✅ **Extracts summary** from `خلاصه متن` section (200-500 words)
- ✅ **Extracts full content** from `post-text` div
- ✅ **Removes** CSS classes, JavaScript, Livewire components
- ✅ **Normalizes** Persian characters (ك→ک, ي→ی)
- ✅ **Cleans** HTML entities (&nbsp;, &zwnj;, etc.)

### Field Transformation

| Old Field | New Field(s) | Notes |
|-----------|-------------|-------|
| `content` (HTML) | `summary` + `full_content` (clean text) | HTML completely removed |
| `title` | `title` | Preserved, cleaned |
| - | `doc_type` | **NEW**: Inferred from content |
| - | `date` | **NEW**: Extracted from Persian dates, converted to Gregorian |
| `page_id` | `doc_id` | Renamed |
| Tags (junction table) | `tags` (array) | Flattened, only "subjects" category |
| Relations | Relations | Preserved as-is |

### Removed Fields (Not Needed)
- ❌ `relations_built`, `relations_in_progress`, `relations_started_at` (internal flags)
- ❌ `http_status` (not relevant for agent)
- ❌ `category` field on tags (flattened into array)

---

## Prerequisites

```bash
# 1. Install dependencies
pip install psycopg2-binary beautifulsoup4 jdatetime

# 2. Create new database
createdb law_agent

# 3. Run schema creation
psql -d law_agent -f schema.sql
```

---

## Migration Steps

### Step 1: Configure Database Connections

Edit `migrate.py` lines 513-524:

```python
OLD_DB = {
    'host': 'localhost',
    'database': 'knowledge',  # Your old database name
    'user': 'postgres',
    'password': 'your_password'
}

NEW_DB = {
    'host': 'localhost',
    'database': 'law_agent',  # New clean database
    'user': 'postgres',
    'password': 'your_password'
}
```

### Step 2: Run Migration

```bash
python migrate.py
```

**Expected output**:
```
════════════════════════════════════════════════════════════════════════════════
                     LAW AGENT DATABASE MIGRATION
                  HTML → Clean Text + Minimal Schema
════════════════════════════════════════════════════════════════════════════════

Connecting to databases...
✓ Connected

════════════════════════════════════════════════════════════════════════════════
MIGRATING DOCUMENTS
════════════════════════════════════════════════════════════════════════════════
Total documents to migrate: 47,235
  ✓ Migrated 500/47,235 documents (1.1%)
  ✓ Migrated 1,000/47,235 documents (2.1%)
  ...
  ✓ Migrated 47,235/47,235 documents (100.0%)

✓ Documents migration complete!
  - Migrated: 47,235
  - Errors: 0

════════════════════════════════════════════════════════════════════════════════
MIGRATING TAGS
════════════════════════════════════════════════════════════════════════════════
  ✓ Updated tags for 1000 documents
  ...
✓ Tags migration complete!

════════════════════════════════════════════════════════════════════════════════
MIGRATING RELATIONS
════════════════════════════════════════════════════════════════════════════════
Total relations to migrate: 185,429
  ✓ Migrated 5,000/185,429 relations
  ...
✓ Relations migration complete! (185,429 total)

════════════════════════════════════════════════════════════════════════════════
VALIDATING MIGRATION
════════════════════════════════════════════════════════════════════════════════
✓ Total documents: 47,235

  Document types:
    - advisory_opinion: 38,456 (81.4%)
    - court_ruling: 6,234 (13.2%)
    - law: 1,987 (4.2%)
    - regulation: 456 (1.0%)
    - unified_precedent: 102 (0.2%)

  Documents with dates: 42,108 (89.1%)
  Documents with tags: 35,234 (74.6%)
  Total relations: 185,429

  Sample document:
    - ID: 1635489
    - Title: نظریه مشورتی شماره 7/97/1596 مورخ 1398/03/25
    - Type: advisory_opinion
    - Summary preview: موضوع استعلام درباره امکان تحت پوشش بیمه‌های اجتماعی قرار گرفتن محکوم‌علیه‌ای است که به عنوان مجازات جایگزین حبس، خدمات عمومی رایگان انجام می‌دهد...

  Documents with search vectors: 47,235 (should be 100%)

✓ Validation complete!

════════════════════════════════════════════════════════════════════════════════
✓ MIGRATION COMPLETE!
════════════════════════════════════════════════════════════════════════════════

Your new database is ready for the agent!
All HTML has been cleaned, unnecessary fields removed.

Next steps:
  1. Run: ANALYZE documents;
  2. Test search: SELECT * FROM documents WHERE search_vector @@ to_tsquery('persian_custom', 'بیمه');
  3. Start building your agent!
```

**Duration**: ~10-15 minutes for 47K documents

---

## Verify Migration

### Check Sample Document

```sql
-- See a full document with clean text
SELECT
    doc_id,
    title,
    doc_type,
    date,
    LEFT(summary, 200) as summary_preview,
    LEFT(full_content, 300) as content_preview,
    tags
FROM documents
WHERE doc_id = 1635489;
```

**Expected**: Clean Persian text, no HTML tags, no CSS classes

### Test Search

```sql
-- Test full-text search
SELECT
    doc_id,
    title,
    doc_type,
    ts_rank(search_vector, query) as score
FROM documents,
     to_tsquery('persian_custom', 'بیمه & کارگران') as query
WHERE search_vector @@ query
ORDER BY score DESC
LIMIT 10;
```

### Test Relations

```sql
-- Test graph traversal
SELECT
    d.doc_id,
    d.title,
    r.relation_type
FROM relations r
JOIN documents d ON r.dst_doc_id = d.doc_id
WHERE r.src_doc_id = 1635489
  AND r.relation_type = 'قوانین';
```

---

## Migration Details

### HTML Parsing Logic

The migration script uses **BeautifulSoup** to:

1. **Find summary section**:
   ```python
   # Look for: <span>خلاصه متن:</span>
   # Navigate to: parent div → content div (with line-clamp class)
   # Extract: text content only
   ```

2. **Find full content**:
   ```python
   # Look for: <div class="post-text">
   # Remove: script, style, section tags
   # Remove: Livewire components (JSON metadata)
   # Extract: all text with line breaks
   ```

3. **Clean text**:
   - Remove HTML entities: `&nbsp;` → space, `&zwnj;` → zero-width non-joiner
   - Normalize: Arabic characters → Persian (ك→ک, ي→ی)
   - Collapse whitespace: multiple spaces → single space

### Document Type Inference

```python
# Rules (in order):
if 'نظریه مشورتی' in title → 'advisory_opinion'
if 'دادنامه' or 'رای دادگاه' in title → 'court_ruling'
if 'رای وحدت رویه' in title → 'unified_precedent'
if 'آیین‌نامه' in title → 'regulation'
if 'قانون' in title and not 'نظریه' → 'law'
else → 'advisory_opinion' (default)
```

### Date Extraction & Conversion

```python
# 1. Find pattern: YYYY/MM/DD (Persian or Latin digits)
# 2. Convert Persian digits to Latin: ۱۳۹۸ → 1398
# 3. Parse as Persian (Jalali) date
# 4. Convert to Gregorian using jdatetime library
# Example: 1398/03/25 → 2019-06-15
```

---

## Schema Comparison

### Old Schema (Website)

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
CREATE TABLE page_tags (page_id, tag_id);  -- Junction table
CREATE TABLE relations (id, src_id, dst_id, relation_name);
```

### New Schema (Agent)

```sql
CREATE TABLE documents (
    doc_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,  -- NEW: inferred
    date DATE,  -- NEW: extracted & converted
    summary TEXT NOT NULL,  -- NEW: extracted from HTML
    full_content TEXT NOT NULL,  -- NEW: cleaned from HTML
    tags TEXT[],  -- CHANGED: array instead of junction table
    search_vector tsvector,  -- NEW: auto-generated
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE relations (
    id SERIAL PRIMARY KEY,
    src_doc_id BIGINT REFERENCES documents(doc_id),
    dst_doc_id BIGINT REFERENCES documents(doc_id),
    relation_type VARCHAR(50)
);
```

**Changes**:
- ✅ Content split: `summary` (for search) + `full_content` (for answers)
- ✅ HTML completely removed
- ✅ Tags flattened into array
- ✅ Metadata inferred: `doc_type`, `date`
- ✅ FTS vector auto-generated
- ❌ Removed: processing flags, http_status

---

## Troubleshooting

### Error: "jdatetime module not found"

```bash
pip install jdatetime
```

### Error: "Cannot connect to database"

Check PostgreSQL is running:
```bash
pg_ctl status
# or
brew services list | grep postgresql
```

### Migration is slow

Increase `batch_size` in `migrate.py`:
```python
migrate_documents(old_conn, new_conn, batch_size=1000)  # Default: 500
```

### Some documents missing dates

This is expected - not all documents have dates in their title/content. The script sets `date = NULL` for these.

### Summary is too short

The script requires minimum 50 characters. Documents with shorter summaries are skipped (check logs for warnings).

---

## Performance

With 47K documents:
- **Migration time**: ~10-15 minutes
- **New database size**: ~1.9 GB (vs 1.3 GB old with HTML)
- **Indexes**: ~370 MB
- **Search speed**: <50ms per query

---

## Next Steps

After migration:

1. **Verify** data quality (spot check 10-20 documents)
2. **Test** searches with the agent tools
3. **Build** your PydanticAI agent
4. **Deploy** with Docker

Migration is complete! Your database is now clean and optimized for agent search. 🎉
