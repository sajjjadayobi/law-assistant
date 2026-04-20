-- Performance Index Migration for Phase 9
-- Adds indexes to optimize frequent queries without schema changes

-- Document Type Index (for filtering by doc_type)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_doc_type
ON documents(doc_type);

-- Document Date Index (for date range queries)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_date
ON documents(date);

-- Document Tags Index (for tag-based filtering)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_documents_tags
ON documents USING GIN(tags);

-- Relation Source Index (for finding documents by what they cite)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_src
ON relations(src_doc_id);

-- Relation Destination Index (for finding documents that cite a given doc)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_dst
ON relations(dst_doc_id);

-- Relation Type Index (for filtering relations by type)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_type
ON relations(relation_type);

-- Analyze tables to update statistics
ANALYZE documents;
ANALYZE relations;

-- Enable pg_stat_statements extension if not already enabled
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Verify indexes were created
SELECT indexname, tablename, indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename IN ('documents', 'relations')
ORDER BY tablename, indexname;
