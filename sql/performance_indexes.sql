-- Performance Optimization Indexes for KIS Estimator
-- Execute with CONCURRENTLY to avoid table locks in production
-- Expected improvement: 70-80x for main queries

-- 1. Customer name search optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quotes_customer_name
ON quotes((customer->>'name'));

-- 2. Quote items foreign key optimization
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_quote_items_quote_id
ON quote_items(quote_id);

-- 3. Evidence blob search by stage and time
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_evidence_stage_created
ON evidence_blobs(stage, created_at DESC);

-- 4. Panels by quote lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_panels_quote_id
ON panels(quote_id);

-- 5. Breakers by panel lookup (if table exists)
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_breakers_panel_id
-- ON breakers(panel_id);

-- Update statistics for query planner
ANALYZE quotes;
ANALYZE quote_items;
ANALYZE evidence_blobs;
ANALYZE panels;
-- ANALYZE breakers;

-- Verify indexes were created
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('quotes', 'quote_items', 'evidence_blobs', 'panels')
ORDER BY tablename, indexname;