-- ============================================================================
-- KIS Estimator Database Functions and Triggers
-- Supabase PostgreSQL with TIMESTAMPTZ/UTC Standard
-- ============================================================================

-- ============================================================================
-- FUNCTION: update_updated_at
-- Purpose: Automatically update updated_at column to current UTC timestamp
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.update_updated_at() IS 'Automatically updates updated_at column to current UTC timestamp on UPDATE';

-- ============================================================================
-- FUNCTION: check_sha256
-- Purpose: Validate SHA256 hash format (64 hex characters)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.check_sha256(hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN hash IS NOT NULL
        AND length(hash) = 64
        AND hash ~ '^[a-f0-9]{64}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

COMMENT ON FUNCTION public.check_sha256(TEXT) IS 'Validates SHA256 hash format (64 lowercase hex characters)';

-- ============================================================================
-- FUNCTION: validate_evidence_integrity
-- Purpose: Verify evidence SHA256 matches stored hash
-- ============================================================================

CREATE OR REPLACE FUNCTION public.validate_evidence_integrity(
    p_quote_id UUID,
    p_computed_sha TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_stored_sha TEXT;
BEGIN
    SELECT evidence_sha INTO v_stored_sha
    FROM estimator.quotes
    WHERE id = p_quote_id;

    IF v_stored_sha IS NULL THEN
        RETURN false;
    END IF;

    RETURN v_stored_sha = p_computed_sha;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.validate_evidence_integrity(UUID, TEXT) IS 'Validates evidence package integrity by comparing SHA256 hashes';

-- ============================================================================
-- FUNCTION: calculate_quote_totals
-- Purpose: Recalculate quote totals from quote_items
-- ============================================================================

CREATE OR REPLACE FUNCTION public.calculate_quote_totals(p_quote_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_subtotal NUMERIC(12, 2);
    v_tax NUMERIC(12, 2);
    v_total NUMERIC(12, 2);
    v_tax_rate NUMERIC(4, 4) := 0.10; -- 10% default tax rate
BEGIN
    SELECT COALESCE(SUM(amount), 0)
    INTO v_subtotal
    FROM estimator.quote_items
    WHERE quote_id = p_quote_id;

    v_tax := ROUND(v_subtotal * v_tax_rate, 2);
    v_total := v_subtotal + v_tax;

    RETURN jsonb_build_object(
        'subtotal', v_subtotal,
        'tax', v_tax,
        'tax_rate', v_tax_rate,
        'total', v_total,
        'calculated_at', (now() AT TIME ZONE 'utc')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.calculate_quote_totals(UUID) IS 'Calculates quote totals (subtotal, tax, total) from quote_items';

-- ============================================================================
-- FUNCTION: get_phase_balance
-- Purpose: Calculate phase load balance for a panel
-- ============================================================================

CREATE OR REPLACE FUNCTION public.get_phase_balance(p_panel_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_phase_r NUMERIC := 0;
    v_phase_s NUMERIC := 0;
    v_phase_t NUMERIC := 0;
    v_total NUMERIC;
    v_max_phase NUMERIC;
    v_min_phase NUMERIC;
    v_imbalance NUMERIC(5, 4);
BEGIN
    -- Calculate total capacity per phase
    SELECT
        COALESCE(SUM(CASE WHEN phase_assignment = 'R' THEN qty ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN phase_assignment = 'S' THEN qty ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN phase_assignment = 'T' THEN qty ELSE 0 END), 0)
    INTO v_phase_r, v_phase_s, v_phase_t
    FROM estimator.breakers
    WHERE panel_id = p_panel_id;

    v_total := v_phase_r + v_phase_s + v_phase_t;

    IF v_total = 0 THEN
        v_imbalance := 0;
    ELSE
        v_max_phase := GREATEST(v_phase_r, v_phase_s, v_phase_t);
        v_min_phase := LEAST(v_phase_r, v_phase_s, v_phase_t);

        IF v_max_phase > 0 THEN
            v_imbalance := (v_max_phase - v_min_phase) / v_max_phase;
        ELSE
            v_imbalance := 0;
        END IF;
    END IF;

    RETURN jsonb_build_object(
        'phase_r', v_phase_r,
        'phase_s', v_phase_s,
        'phase_t', v_phase_t,
        'total', v_total,
        'imbalance', v_imbalance,
        'imbalance_percent', ROUND(v_imbalance * 100, 2),
        'balanced', v_imbalance <= 0.04,
        'calculated_at', (now() AT TIME ZONE 'utc')
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.get_phase_balance(UUID) IS 'Calculates 3-phase load balance for a panel (target imbalance ≤4%)';

-- ============================================================================
-- TRIGGERS: Apply updated_at triggers to all tables with updated_at column
-- ============================================================================

-- estimator.quotes
DROP TRIGGER IF EXISTS trg_quotes_updated_at ON estimator.quotes;
CREATE TRIGGER trg_quotes_updated_at
    BEFORE UPDATE ON estimator.quotes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- estimator.quote_items
DROP TRIGGER IF EXISTS trg_quote_items_updated_at ON estimator.quote_items;
CREATE TRIGGER trg_quote_items_updated_at
    BEFORE UPDATE ON estimator.quote_items
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- estimator.panels
DROP TRIGGER IF EXISTS trg_panels_updated_at ON estimator.panels;
CREATE TRIGGER trg_panels_updated_at
    BEFORE UPDATE ON estimator.panels
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- estimator.breakers
DROP TRIGGER IF EXISTS trg_breakers_updated_at ON estimator.breakers;
CREATE TRIGGER trg_breakers_updated_at
    BEFORE UPDATE ON estimator.breakers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- shared.catalog_items
DROP TRIGGER IF EXISTS trg_catalog_items_updated_at ON shared.catalog_items;
CREATE TRIGGER trg_catalog_items_updated_at
    BEFORE UPDATE ON shared.catalog_items
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Validate SHA256 hash
-- SELECT public.check_sha256('a1b2c3d4e5f6...'); -- Returns true/false

-- Validate evidence integrity
-- SELECT public.validate_evidence_integrity(
--     'quote-uuid-here',
--     'computed-sha256-hash'
-- ); -- Returns true/false

-- Calculate quote totals
-- UPDATE estimator.quotes
-- SET totals = public.calculate_quote_totals(id)
-- WHERE id = 'quote-uuid-here';

-- Get phase balance for panel
-- SELECT public.get_phase_balance('panel-uuid-here');
-- Returns: {
--   "phase_r": 100,
--   "phase_s": 98,
--   "phase_t": 102,
--   "total": 300,
--   "imbalance": 0.0392,
--   "imbalance_percent": 3.92,
--   "balanced": true,
--   "calculated_at": "2025-09-30T12:00:00Z"
-- }

-- ============================================================================
-- OPERATIONS MODE FUNCTIONS
-- ============================================================================

-- ============================================================================
-- FUNCTION: set_evidence_expiry
-- Purpose: Set evidence blob expiration for lifecycle management
-- ============================================================================

CREATE OR REPLACE FUNCTION public.set_evidence_expiry(
    p_evidence_id UUID,
    p_retention_days INTEGER DEFAULT 90
)
RETURNS TIMESTAMPTZ AS $$
DECLARE
    v_expires_at TIMESTAMPTZ;
BEGIN
    v_expires_at := (now() AT TIME ZONE 'utc') + (p_retention_days || ' days')::INTERVAL;

    UPDATE estimator.evidence_blobs
    SET expires_at = v_expires_at
    WHERE id = p_evidence_id;

    RETURN v_expires_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.set_evidence_expiry IS 'Sets evidence blob expiration for lifecycle management (Operations)';

-- ============================================================================
-- FUNCTION: cleanup_expired_evidence
-- Purpose: Remove expired evidence blobs (run via cron)
-- ============================================================================

CREATE OR REPLACE FUNCTION public.cleanup_expired_evidence()
RETURNS TABLE(
    deleted_count INTEGER,
    total_size_bytes BIGINT
) AS $$
DECLARE
    v_deleted_count INTEGER;
    v_total_size BIGINT;
BEGIN
    SELECT COUNT(*), COALESCE(SUM(size_bytes), 0)
    INTO v_deleted_count, v_total_size
    FROM estimator.evidence_blobs
    WHERE expires_at IS NOT NULL
      AND expires_at < (now() AT TIME ZONE 'utc');

    DELETE FROM estimator.evidence_blobs
    WHERE expires_at IS NOT NULL
      AND expires_at < (now() AT TIME ZONE 'utc');

    RETURN QUERY SELECT v_deleted_count, v_total_size;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.cleanup_expired_evidence IS 'Removes expired evidence blobs (Operations: run periodically)';

-- ============================================================================
-- FUNCTION: increment_quote_version
-- Purpose: Optimistic locking for concurrent updates
-- ============================================================================

CREATE OR REPLACE FUNCTION public.increment_quote_version(
    p_quote_id UUID,
    p_expected_version INTEGER
)
RETURNS BOOLEAN AS $$
DECLARE
    v_current_version INTEGER;
    v_rows_updated INTEGER;
BEGIN
    SELECT version INTO v_current_version
    FROM estimator.quotes
    WHERE id = p_quote_id
    FOR UPDATE;

    IF v_current_version IS NULL THEN
        RAISE EXCEPTION 'Quote not found: %', p_quote_id;
    END IF;

    IF v_current_version != p_expected_version THEN
        RETURN FALSE; -- Version mismatch
    END IF;

    UPDATE estimator.quotes
    SET version = version + 1
    WHERE id = p_quote_id
      AND version = p_expected_version;

    GET DIAGNOSTICS v_rows_updated = ROW_COUNT;

    RETURN v_rows_updated = 1;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.increment_quote_version IS 'Optimistic locking: increment version if expected version matches (Operations)';

-- ============================================================================
-- FUNCTION: health_check_detailed
-- Purpose: Detailed health check for /readyz endpoint
-- ============================================================================

CREATE OR REPLACE FUNCTION public.health_check_detailed()
RETURNS TABLE(
    component VARCHAR(50),
    status VARCHAR(20),
    details JSONB,
    checked_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'database'::VARCHAR(50),
        'ok'::VARCHAR(20),
        jsonb_build_object(
            'utc_time', now() AT TIME ZONE 'utc',
            'connection', 'active'
        ),
        (now() AT TIME ZONE 'utc')::TIMESTAMPTZ;

    RETURN QUERY
    SELECT
        'tables'::VARCHAR(50),
        'ok'::VARCHAR(20),
        jsonb_build_object(
            'quotes', (SELECT COUNT(*) FROM estimator.quotes),
            'evidence_blobs', (SELECT COUNT(*) FROM estimator.evidence_blobs)
        ),
        (now() AT TIME ZONE 'utc')::TIMESTAMPTZ;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.health_check_detailed IS 'Detailed health check for /readyz endpoint (Operations)';

-- ============================================================================
-- FUNCTION SUMMARY (UPDATED)
-- ============================================================================
--
-- BASE FUNCTIONS:
-- FUNCTION                      | PURPOSE                           | RETURNS
-- ------------------------------|-----------------------------------|----------
-- update_updated_at()           | Auto-update timestamp trigger     | TRIGGER
-- check_sha256(text)            | Validate SHA256 format            | BOOLEAN
-- validate_evidence_integrity() | Verify evidence hash matches      | BOOLEAN
-- calculate_quote_totals(uuid)  | Recalculate quote totals          | JSONB
-- get_phase_balance(uuid)       | Calculate 3-phase balance         | JSONB
--
-- OPERATIONS FUNCTIONS:
-- FUNCTION                      | PURPOSE                           | RETURNS
-- ------------------------------|-----------------------------------|----------
-- set_evidence_expiry()         | Set evidence expiration           | TIMESTAMPTZ
-- cleanup_expired_evidence()    | Remove expired evidence           | TABLE
-- increment_quote_version()     | Optimistic locking                | BOOLEAN
-- health_check_detailed()       | Detailed health check             | TABLE
--
-- TRIGGERS:
-- TRIGGER                       | TABLE                 | WHEN
-- ------------------------------|------------------------|--------
-- trg_quotes_updated_at         | estimator.quotes      | BEFORE UPDATE
-- trg_quote_items_updated_at    | estimator.quote_items | BEFORE UPDATE
-- trg_panels_updated_at         | estimator.panels      | BEFORE UPDATE
-- trg_breakers_updated_at       | estimator.breakers    | BEFORE UPDATE
-- trg_catalog_items_updated_at  | shared.catalog_items  | BEFORE UPDATE
--
-- ============================================================================