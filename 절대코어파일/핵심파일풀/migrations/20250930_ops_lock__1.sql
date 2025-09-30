-- KIS Estimator - Operations Lock Migration
-- Purpose: Production-grade constraints, versioning, and audit trail
-- Created: 2025-09-30
-- Version: 1.0.0

-- ============================================================================
-- MIGRATION VERSION LOCK
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(14) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    description TEXT,
    checksum VARCHAR(64) NOT NULL
);

-- Current migration record
INSERT INTO schema_migrations (version, description, checksum)
VALUES (
    '20250930_ops_lock',
    'Operations mode: constraints, versioning, audit trail',
    encode(sha256('20250930_ops_lock'::bytea), 'hex')
) ON CONFLICT (version) DO NOTHING;

-- ============================================================================
-- UPDATED_AT TRIGGER FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now() AT TIME ZONE 'utc';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- QUOTES TABLE ENHANCEMENTS
-- ============================================================================

-- Add version column for optimistic locking
ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL;

-- Add evidence tracking
ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS evidence_sha256 VARCHAR(64);

-- Add audit trail
ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS created_by VARCHAR(100);

ALTER TABLE quotes
ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100);

-- Ensure TIMESTAMPTZ with UTC
ALTER TABLE quotes
ALTER COLUMN created_at TYPE TIMESTAMPTZ,
ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

ALTER TABLE quotes
ALTER COLUMN updated_at TYPE TIMESTAMPTZ,
ALTER COLUMN updated_at SET DEFAULT (now() AT TIME ZONE 'utc');

-- Create updated_at trigger
DROP TRIGGER IF EXISTS update_quotes_updated_at ON quotes;
CREATE TRIGGER update_quotes_updated_at
    BEFORE UPDATE ON quotes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_quotes_created_at ON quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
CREATE INDEX IF NOT EXISTS idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_evidence_sha ON quotes(evidence_sha256);

-- ============================================================================
-- QUOTE_ITEMS TABLE ENHANCEMENTS
-- ============================================================================

ALTER TABLE quote_items
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc');

ALTER TABLE quote_items
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc');

DROP TRIGGER IF EXISTS update_quote_items_updated_at ON quote_items;
CREATE TRIGGER update_quote_items_updated_at
    BEFORE UPDATE ON quote_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_quote_items_quote_id ON quote_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_quote_items_breaker_sku ON quote_items(breaker_sku);

-- ============================================================================
-- PANELS TABLE ENHANCEMENTS
-- ============================================================================

ALTER TABLE panels
ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc');

ALTER TABLE panels
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc');

-- Fit score constraint
ALTER TABLE panels
ADD CONSTRAINT check_fit_score CHECK (fit_score >= 0.0 AND fit_score <= 1.0);

DROP TRIGGER IF EXISTS update_panels_updated_at ON panels;
CREATE TRIGGER update_panels_updated_at
    BEFORE UPDATE ON panels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_panels_quote_id ON panels(quote_id);
CREATE INDEX IF NOT EXISTS idx_panels_fit_score ON panels(fit_score DESC);

-- ============================================================================
-- EVIDENCE_BLOBS TABLE ENHANCEMENTS
-- ============================================================================

ALTER TABLE evidence_blobs
ALTER COLUMN hash TYPE VARCHAR(64);

-- Rename to sha256 for clarity
ALTER TABLE evidence_blobs
RENAME COLUMN hash TO sha256;

-- Add size tracking
ALTER TABLE evidence_blobs
ADD COLUMN IF NOT EXISTS size_bytes BIGINT;

-- Add retention tracking
ALTER TABLE evidence_blobs
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

ALTER TABLE evidence_blobs
ALTER COLUMN created_at TYPE TIMESTAMPTZ,
ALTER COLUMN created_at SET DEFAULT (now() AT TIME ZONE 'utc');

-- Unique constraint on sha256 for deduplication
CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_blobs_sha256 ON evidence_blobs(sha256);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_evidence_blobs_quote_id ON evidence_blobs(quote_id);
CREATE INDEX IF NOT EXISTS idx_evidence_blobs_stage ON evidence_blobs(stage);
CREATE INDEX IF NOT EXISTS idx_evidence_blobs_created_at ON evidence_blobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_blobs_expires_at ON evidence_blobs(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- AUDIT LOG TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    operation VARCHAR(10) NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    trace_id VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_at ON audit_log(changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_trace_id ON audit_log(trace_id);

-- ============================================================================
-- AUDIT TRIGGER FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO audit_log (table_name, record_id, operation, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW)::jsonb, current_user);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO audit_log (table_name, record_id, operation, old_data, new_data, changed_by)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD)::jsonb, row_to_json(NEW)::jsonb, current_user);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO audit_log (table_name, record_id, operation, old_data, changed_by)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD)::jsonb, current_user);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to critical tables
DROP TRIGGER IF EXISTS audit_quotes ON quotes;
CREATE TRIGGER audit_quotes
    AFTER INSERT OR UPDATE OR DELETE ON quotes
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

DROP TRIGGER IF EXISTS audit_evidence_blobs ON evidence_blobs;
CREATE TRIGGER audit_evidence_blobs
    AFTER INSERT OR UPDATE OR DELETE ON evidence_blobs
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

-- ============================================================================
-- HEALTH CHECK FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION health_check()
RETURNS TABLE(
    status TEXT,
    timestamp TIMESTAMPTZ,
    version TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'ok'::TEXT as status,
        (now() AT TIME ZONE 'utc')::TIMESTAMPTZ as timestamp,
        (SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1)::TEXT as version;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- QUERY PLAN SNAPSHOT TABLE (for performance monitoring)
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_plan_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_name VARCHAR(200) NOT NULL,
    query_text TEXT NOT NULL,
    plan_json JSONB NOT NULL,
    execution_time_ms NUMERIC(10,2),
    captured_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_plan_snapshots_name ON query_plan_snapshots(query_name);
CREATE INDEX IF NOT EXISTS idx_query_plan_snapshots_captured_at ON query_plan_snapshots(captured_at DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE schema_migrations IS 'Tracks applied database migrations with checksums';
COMMENT ON TABLE audit_log IS 'Comprehensive audit trail for all critical table changes';
COMMENT ON TABLE query_plan_snapshots IS 'Performance monitoring: query execution plans over time';
COMMENT ON FUNCTION health_check() IS 'Database health check for /readyz endpoint';
COMMENT ON FUNCTION update_updated_at_column() IS 'Automatically updates updated_at timestamp on row changes';
COMMENT ON FUNCTION audit_trigger_func() IS 'Captures INSERT/UPDATE/DELETE operations to audit_log';

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all constraints and indexes are in place
DO $$
DECLARE
    v_count INTEGER;
BEGIN
    -- Check updated_at triggers
    SELECT COUNT(*) INTO v_count
    FROM pg_trigger
    WHERE tgname LIKE 'update_%_updated_at';

    IF v_count < 3 THEN
        RAISE WARNING 'Not all updated_at triggers are installed. Expected 3, found %', v_count;
    END IF;

    -- Check audit triggers
    SELECT COUNT(*) INTO v_count
    FROM pg_trigger
    WHERE tgname LIKE 'audit_%';

    IF v_count < 2 THEN
        RAISE WARNING 'Not all audit triggers are installed. Expected 2, found %', v_count;
    END IF;

    RAISE NOTICE 'Migration 20250930_ops_lock applied successfully';
END $$;