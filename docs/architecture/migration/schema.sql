-- ============================================================================
-- LAW AGENT DATABASE SCHEMA - Clean & Minimal
-- Only fields needed for agent search workflow
-- All HTML removed, clean text only
-- ============================================================================

-- Drop existing if re-running
DROP TABLE IF EXISTS relations CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TEXT SEARCH CONFIGURATION IF EXISTS persian_custom CASCADE;

-- ============================================================================
-- POSTGRESQL FTS CONFIGURATION (Persian)
-- ============================================================================

CREATE TEXT SEARCH CONFIGURATION persian_custom (COPY = simple);

COMMENT ON TEXT SEARCH CONFIGURATION persian_custom IS 'Persian full-text search configuration';

-- ============================================================================
-- TABLE: documents (Clean text only, minimal fields)
-- ============================================================================

CREATE TABLE documents (
    -- Primary key
    doc_id BIGINT PRIMARY KEY,

    -- Metadata (essential only)
    title TEXT NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    date DATE,  -- Gregorian (converted from Persian)

    -- Content (NO HTML, clean text only)
    summary TEXT NOT NULL,       -- 200-500 words extracted from خلاصه متن
    full_content TEXT NOT NULL,  -- Full document, HTML stripped

    -- Classification
    tags TEXT[] NOT NULL DEFAULT '{}',  -- Subject tags only

    -- Full-text search (auto-generated)
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('persian_custom', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('persian_custom', coalesce(summary, '')), 'B')
    ) STORED,

    -- Timestamp
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraint
    CONSTRAINT valid_doc_type CHECK (
        doc_type IN ('law', 'regulation', 'advisory_opinion', 'court_ruling', 'unified_precedent')
    )
);

-- Comments
COMMENT ON TABLE documents IS 'Legal documents with all HTML removed - clean text only';
COMMENT ON COLUMN documents.doc_id IS 'Original page_id from source database';
COMMENT ON COLUMN documents.doc_type IS 'Inferred from title/content: law, regulation, advisory_opinion, court_ruling, unified_precedent';
COMMENT ON COLUMN documents.date IS 'Gregorian date converted from Persian date in title/content';
COMMENT ON COLUMN documents.summary IS 'For searching: 200-500 word summary from خلاصه متن section, cleaned';
COMMENT ON COLUMN documents.full_content IS 'For answering: Full document text with all HTML/CSS/JS removed';
COMMENT ON COLUMN documents.tags IS 'Array of subject tags (اداری, خانواده, etc.) - only "subjects" category from old schema';
COMMENT ON COLUMN documents.search_vector IS 'Auto-generated FTS vector: title (weight A) + summary (weight B)';

-- ============================================================================
-- INDEXES: Optimized for agent search patterns
-- ============================================================================

-- FTS index (most important)
CREATE INDEX idx_fts_search ON documents USING GIN(search_vector);

-- Tag filtering
CREATE INDEX idx_tags_gin ON documents USING GIN(tags);

-- Doc type filtering (for hierarchy-aware search)
CREATE INDEX idx_doc_type ON documents(doc_type);

-- Date sorting
CREATE INDEX idx_date_desc ON documents(date DESC NULLS LAST);

-- Compound index for filtered searches
CREATE INDEX idx_doc_type_date ON documents(doc_type, date DESC NULLS LAST);

-- ============================================================================
-- TABLE: relations (Document citation graph)
-- ============================================================================

CREATE TABLE relations (
    id SERIAL PRIMARY KEY,

    -- Graph edge: src_doc_id cites dst_doc_id
    src_doc_id BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    dst_doc_id BIGINT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,

    -- Relation type (preserved in Persian)
    relation_type VARCHAR(50) NOT NULL,

    -- Constraints
    UNIQUE(src_doc_id, dst_doc_id, relation_type),
    CONSTRAINT no_self_reference CHECK (src_doc_id != dst_doc_id)
);

-- Comments
COMMENT ON TABLE relations IS 'Document citation graph: src_doc_id cites dst_doc_id';
COMMENT ON COLUMN relations.relation_type IS 'Persian relation types: قوانین, مواد مرتبط, نظریه‌های مشورتی, etc.';

-- ============================================================================
-- INDEXES: Optimized for graph traversal
-- ============================================================================

-- Forward traversal: get documents that this document cites (go UP hierarchy)
CREATE INDEX idx_rel_src_type ON relations(src_doc_id, relation_type);

-- Backward traversal: get documents that cite this one (go DOWN hierarchy)
CREATE INDEX idx_rel_dst ON relations(dst_doc_id);

-- Backward with type filter
CREATE INDEX idx_rel_dst_type ON relations(dst_doc_id, relation_type);

-- ============================================================================
-- STATISTICS (for query planner)
-- ============================================================================

ALTER TABLE documents ALTER COLUMN doc_type SET STATISTICS 1000;
ALTER TABLE documents ALTER COLUMN tags SET STATISTICS 1000;
ALTER TABLE relations ALTER COLUMN relation_type SET STATISTICS 1000;

-- ============================================================================
-- INITIAL ANALYSIS
-- ============================================================================

ANALYZE documents;
ANALYZE relations;

-- ============================================================================
-- SUMMARY
-- ============================================================================

-- Fields REMOVED from old schema:
--   - content (HTML) → replaced with summary + full_content (clean text)
--   - relations_built, relations_in_progress, relations_started_at → not needed
--   - http_status → not needed
--   - source_url → not needed for agent

-- Fields ADDED:
--   - doc_type (inferred from content)
--   - date (extracted and converted from Persian)
--   - summary (extracted from خلاصه متن)
--   - full_content (cleaned from HTML)
--   - search_vector (auto-generated for FTS)

-- Result: Clean, minimal schema optimized for agent search workflow
