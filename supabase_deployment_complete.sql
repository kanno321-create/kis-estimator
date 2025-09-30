-- ============================================================================
-- KIS Estimator - Complete Supabase Deployment Script
-- Execute this file in Supabase Dashboard -> SQL Editor
-- Project: kis-estimator (cgqukhmqnndwdbmkmjrn)
-- Region: ap-northeast-2 (Seoul)
-- ============================================================================

-- ============================================================================
-- PART 1: DATABASE SCHEMA
-- ============================================================================

-- Create schemas
CREATE SCHEMA IF NOT EXISTS estimator;
CREATE SCHEMA IF NOT EXISTS shared;

-- Extensions (Supabase includes these by default)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set search path
SET search_path TO estimator, shared, public;

-- ============================================================================
-- SHARED SCHEMA
-- ============================================================================

-- catalog_items: Material catalog (breakers, enclosures, accessories)
CREATE TABLE IF NOT EXISTS shared.catalog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind TEXT NOT NULL CHECK (kind IN ('breaker', 'enclosure', 'accessory', 'wire', 'component')),
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    spec JSONB NOT NULL DEFAULT '{}'::jsonb,
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    currency TEXT NOT NULL DEFAULT 'KRW',
    is_active BOOLEAN NOT NULL DEFAULT true,
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE shared.catalog_items IS 'Material catalog with SKUs, specs, and pricing';

-- Indexes for catalog
CREATE INDEX IF NOT EXISTS idx_catalog_kind_name ON shared.catalog_items(kind, name);
CREATE INDEX IF NOT EXISTS idx_catalog_sku ON shared.catalog_items(sku);
CREATE INDEX IF NOT EXISTS idx_catalog_active ON shared.catalog_items(is_active) WHERE is_active = true;

-- ============================================================================
-- ESTIMATOR SCHEMA
-- ============================================================================

-- quotes: Main estimate/quote records
CREATE TABLE IF NOT EXISTS estimator.quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer JSONB NOT NULL DEFAULT '{}'::jsonb,
    totals JSONB NOT NULL DEFAULT '{}'::jsonb,
    currency TEXT NOT NULL DEFAULT 'KRW',
    evidence_sha TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE estimator.quotes IS 'Main quote/estimate records';

-- Indexes for quotes
CREATE INDEX IF NOT EXISTS idx_quotes_created_at ON estimator.quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON estimator.quotes(status);
CREATE INDEX IF NOT EXISTS idx_quotes_evidence_sha ON estimator.quotes(evidence_sha) WHERE evidence_sha IS NOT NULL;

-- quote_items: Line items for each quote
CREATE TABLE IF NOT EXISTS estimator.quote_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    item_type TEXT NOT NULL CHECK (item_type IN ('breaker', 'enclosure', 'accessory', 'labor', 'other')),
    name TEXT NOT NULL,
    qty NUMERIC(10, 2) NOT NULL CHECK (qty > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    amount NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_quote_items_quote_id ON estimator.quote_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_quote_items_type ON estimator.quote_items(item_type);

-- panels: Panel/enclosure configurations
CREATE TABLE IF NOT EXISTS estimator.panels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    enclosure_sku TEXT,
    fit_score NUMERIC(3, 2) CHECK (fit_score >= 0 AND fit_score <= 1),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_panels_quote_id ON estimator.panels(quote_id);

-- breakers: Individual breakers within panels
CREATE TABLE IF NOT EXISTS estimator.breakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    panel_id UUID NOT NULL REFERENCES estimator.panels(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    poles INTEGER NOT NULL CHECK (poles IN (1, 2, 3, 4)),
    capacity TEXT NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    brand TEXT,
    phase_assignment CHAR(1) CHECK (phase_assignment IN ('R', 'S', 'T', 'N')),
    position_x NUMERIC(8, 2),
    position_y NUMERIC(8, 2),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_breakers_panel_id ON estimator.breakers(panel_id);
CREATE INDEX IF NOT EXISTS idx_breakers_type ON estimator.breakers(type);
CREATE INDEX IF NOT EXISTS idx_breakers_phase ON estimator.breakers(phase_assignment) WHERE phase_assignment IS NOT NULL;

-- documents: Generated documents (PDF, Excel, SVG)
CREATE TABLE IF NOT EXISTS estimator.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('pdf', 'xlsx', 'svg', 'dxf')),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 ~ '^[a-f0-9]+$'),
    file_size BIGINT CHECK (file_size > 0),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_documents_quote_id_created ON estimator.documents(quote_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_documents_kind ON estimator.documents(kind);
CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON estimator.documents(sha256);

-- evidence_blobs: Evidence artifacts from FIX-4 pipeline
CREATE TABLE IF NOT EXISTS estimator.evidence_blobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('enclosure', 'breaker', 'critic', 'format', 'cover', 'lint')),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 ~ '^[a-f0-9]+$'),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE INDEX IF NOT EXISTS idx_evidence_quote_id_created ON estimator.evidence_blobs(quote_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evidence_stage ON estimator.evidence_blobs(stage);

-- ============================================================================
-- PART 2: DATABASE FUNCTIONS
-- ============================================================================

-- Function: update_updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: check_sha256
CREATE OR REPLACE FUNCTION public.check_sha256(hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN hash IS NOT NULL
        AND length(hash) = 64
        AND hash ~ '^[a-f0-9]{64}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

-- Function: validate_evidence_integrity
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

-- Function: calculate_quote_totals
CREATE OR REPLACE FUNCTION public.calculate_quote_totals(p_quote_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_subtotal NUMERIC(12, 2);
    v_tax NUMERIC(12, 2);
    v_total NUMERIC(12, 2);
    v_tax_rate NUMERIC(4, 4) := 0.10;
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

-- Function: get_phase_balance
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

-- ============================================================================
-- PART 3: TRIGGERS
-- ============================================================================

-- Apply updated_at triggers
DROP TRIGGER IF EXISTS trg_quotes_updated_at ON estimator.quotes;
CREATE TRIGGER trg_quotes_updated_at
    BEFORE UPDATE ON estimator.quotes
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_quote_items_updated_at ON estimator.quote_items;
CREATE TRIGGER trg_quote_items_updated_at
    BEFORE UPDATE ON estimator.quote_items
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_panels_updated_at ON estimator.panels;
CREATE TRIGGER trg_panels_updated_at
    BEFORE UPDATE ON estimator.panels
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_breakers_updated_at ON estimator.breakers;
CREATE TRIGGER trg_breakers_updated_at
    BEFORE UPDATE ON estimator.breakers
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS trg_catalog_items_updated_at ON shared.catalog_items;
CREATE TRIGGER trg_catalog_items_updated_at
    BEFORE UPDATE ON shared.catalog_items
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

-- ============================================================================
-- PART 4: ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE estimator.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.breakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.evidence_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared.catalog_items ENABLE ROW LEVEL SECURITY;

-- Quotes policies
DROP POLICY IF EXISTS "quotes_service_role_all" ON estimator.quotes;
CREATE POLICY "quotes_service_role_all"
ON estimator.quotes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "quotes_authenticated_select" ON estimator.quotes;
CREATE POLICY "quotes_authenticated_select"
ON estimator.quotes
FOR SELECT
TO authenticated
USING (true);

-- Quote items policies
DROP POLICY IF EXISTS "quote_items_service_role_all" ON estimator.quote_items;
CREATE POLICY "quote_items_service_role_all"
ON estimator.quote_items
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "quote_items_authenticated_select" ON estimator.quote_items;
CREATE POLICY "quote_items_authenticated_select"
ON estimator.quote_items
FOR SELECT
TO authenticated
USING (EXISTS (
    SELECT 1 FROM estimator.quotes
    WHERE quotes.id = quote_items.quote_id
));

-- Panels policies
DROP POLICY IF EXISTS "panels_service_role_all" ON estimator.panels;
CREATE POLICY "panels_service_role_all"
ON estimator.panels
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "panels_authenticated_select" ON estimator.panels;
CREATE POLICY "panels_authenticated_select"
ON estimator.panels
FOR SELECT
TO authenticated
USING (EXISTS (
    SELECT 1 FROM estimator.quotes
    WHERE quotes.id = panels.quote_id
));

-- Breakers policies
DROP POLICY IF EXISTS "breakers_service_role_all" ON estimator.breakers;
CREATE POLICY "breakers_service_role_all"
ON estimator.breakers
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "breakers_authenticated_select" ON estimator.breakers;
CREATE POLICY "breakers_authenticated_select"
ON estimator.breakers
FOR SELECT
TO authenticated
USING (true);

-- Documents policies
DROP POLICY IF EXISTS "documents_service_role_all" ON estimator.documents;
CREATE POLICY "documents_service_role_all"
ON estimator.documents
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "documents_authenticated_select" ON estimator.documents;
CREATE POLICY "documents_authenticated_select"
ON estimator.documents
FOR SELECT
TO authenticated
USING (true);

-- Evidence blobs policies
DROP POLICY IF EXISTS "evidence_blobs_service_role_all" ON estimator.evidence_blobs;
CREATE POLICY "evidence_blobs_service_role_all"
ON estimator.evidence_blobs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "evidence_blobs_authenticated_select" ON estimator.evidence_blobs;
CREATE POLICY "evidence_blobs_authenticated_select"
ON estimator.evidence_blobs
FOR SELECT
TO authenticated
USING (true);

-- Catalog items policies
DROP POLICY IF EXISTS "catalog_items_service_role_all" ON shared.catalog_items;
CREATE POLICY "catalog_items_service_role_all"
ON shared.catalog_items
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "catalog_items_authenticated_select" ON shared.catalog_items;
CREATE POLICY "catalog_items_authenticated_select"
ON shared.catalog_items
FOR SELECT
TO authenticated
USING (true);

-- ============================================================================
-- DEPLOYMENT COMPLETE
-- ============================================================================

-- Verify deployment
DO $$
DECLARE
    v_table_count INTEGER;
    v_function_count INTEGER;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO v_table_count
    FROM information_schema.tables
    WHERE table_schema IN ('estimator', 'shared');
    
    -- Count functions
    SELECT COUNT(*) INTO v_function_count
    FROM information_schema.routines
    WHERE routine_schema = 'public'
    AND routine_name IN ('update_updated_at', 'check_sha256', 'validate_evidence_integrity', 'calculate_quote_totals', 'get_phase_balance');
    
    RAISE NOTICE '✅ Deployment Complete';
    RAISE NOTICE 'Tables created: %', v_table_count;
    RAISE NOTICE 'Functions created: %', v_function_count;
END $$;
