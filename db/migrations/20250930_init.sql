-- ============================================================================
-- KIS Estimator Initial Migration
-- Combined: Schema + Policies + Functions + Triggers
-- Supabase PostgreSQL with TIMESTAMPTZ/UTC Standard
-- ============================================================================
-- Migration: 20250930_init
-- Description: Initial database setup with all schemas, tables, RLS policies, and functions
-- Author: KIS Estimator Team
-- Date: 2025-09-30
-- ============================================================================

-- ============================================================================
-- PART 1: SCHEMA AND TABLES
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
CREATE TABLE shared.catalog_items (
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
COMMENT ON COLUMN shared.catalog_items.spec IS 'Technical specifications (poles, capacity, IP rating, dimensions, etc.)';
COMMENT ON COLUMN shared.catalog_items.meta IS 'Additional metadata (brand, manufacturer, datasheet URL, etc.)';

-- Indexes for catalog
CREATE INDEX idx_catalog_kind_name ON shared.catalog_items(kind, name);
CREATE INDEX idx_catalog_sku ON shared.catalog_items(sku);
CREATE INDEX idx_catalog_active ON shared.catalog_items(is_active) WHERE is_active = true;

-- ============================================================================
-- ESTIMATOR SCHEMA
-- ============================================================================

-- quotes: Main estimate/quote records
CREATE TABLE estimator.quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer JSONB NOT NULL DEFAULT '{}'::jsonb,
    totals JSONB NOT NULL DEFAULT '{}'::jsonb,
    currency TEXT NOT NULL DEFAULT 'KRW',
    evidence_sha TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE estimator.quotes IS 'Main quote/estimate records with customer and total information';
COMMENT ON COLUMN estimator.quotes.customer IS 'Customer information as JSONB (name, contact, address, etc.)';
COMMENT ON COLUMN estimator.quotes.totals IS 'Quote totals as JSONB (subtotal, tax, total, discount, etc.)';
COMMENT ON COLUMN estimator.quotes.evidence_sha IS 'SHA256 hash of complete evidence package for integrity';

-- Indexes for quotes
CREATE INDEX idx_quotes_created_at ON estimator.quotes(created_at DESC);
CREATE INDEX idx_quotes_status ON estimator.quotes(status);
CREATE INDEX idx_quotes_evidence_sha ON estimator.quotes(evidence_sha) WHERE evidence_sha IS NOT NULL;

-- quote_items: Line items for each quote
CREATE TABLE estimator.quote_items (
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

COMMENT ON TABLE estimator.quote_items IS 'Line items for quotes (breakers, enclosures, accessories, etc.)';
COMMENT ON COLUMN estimator.quote_items.meta IS 'Additional metadata (specs, brand, model, etc.)';

CREATE INDEX idx_quote_items_quote_id ON estimator.quote_items(quote_id);
CREATE INDEX idx_quote_items_type ON estimator.quote_items(item_type);

-- panels: Panel/enclosure configurations
CREATE TABLE estimator.panels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    enclosure_sku TEXT,
    fit_score NUMERIC(3, 2) CHECK (fit_score >= 0 AND fit_score <= 1),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE estimator.panels IS 'Panel/enclosure configurations for quotes';
COMMENT ON COLUMN estimator.panels.fit_score IS 'Enclosure fit quality score (0.0-1.0, target ≥0.90)';
COMMENT ON COLUMN estimator.panels.meta IS 'Panel specifications (dimensions, IP rating, door clearance, etc.)';

CREATE INDEX idx_panels_quote_id ON estimator.panels(quote_id);

-- breakers: Individual breakers within panels
CREATE TABLE estimator.breakers (
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

COMMENT ON TABLE estimator.breakers IS 'Breaker specifications and placement within panels';
COMMENT ON COLUMN estimator.breakers.phase_assignment IS 'Phase assignment (R/S/T/N for 3-phase systems)';
COMMENT ON COLUMN estimator.breakers.position_x IS 'X coordinate in panel layout (mm)';
COMMENT ON COLUMN estimator.breakers.position_y IS 'Y coordinate in panel layout (mm)';
COMMENT ON COLUMN estimator.breakers.meta IS 'Additional specs (thermal rating, interrupt capacity, etc.)';

CREATE INDEX idx_breakers_panel_id ON estimator.breakers(panel_id);
CREATE INDEX idx_breakers_type ON estimator.breakers(type);
CREATE INDEX idx_breakers_phase ON estimator.breakers(phase_assignment) WHERE phase_assignment IS NOT NULL;

-- documents: Generated documents (PDF, Excel, SVG)
CREATE TABLE estimator.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('pdf', 'xlsx', 'svg', 'dxf')),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 ~ '^[a-f0-9]+$'),
    file_size BIGINT CHECK (file_size > 0),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE estimator.documents IS 'Generated documents for quotes (PDFs, Excel files, drawings)';
COMMENT ON COLUMN estimator.documents.path IS 'Storage path in Supabase Storage (evidence bucket)';
COMMENT ON COLUMN estimator.documents.sha256 IS 'SHA256 hash for file integrity verification';

CREATE INDEX idx_documents_quote_id_created ON estimator.documents(quote_id, created_at DESC);
CREATE INDEX idx_documents_kind ON estimator.documents(kind);
CREATE INDEX idx_documents_sha256 ON estimator.documents(sha256);

-- evidence_blobs: Evidence artifacts from FIX-4 pipeline
CREATE TABLE estimator.evidence_blobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID NOT NULL REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    stage TEXT NOT NULL CHECK (stage IN ('enclosure', 'breaker', 'critic', 'format', 'cover', 'lint')),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 ~ '^[a-f0-9]+$'),
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

COMMENT ON TABLE estimator.evidence_blobs IS 'Evidence artifacts from each FIX-4 pipeline stage';
COMMENT ON COLUMN estimator.evidence_blobs.stage IS 'FIX-4 pipeline stage (enclosure/breaker/critic/format/cover/lint)';
COMMENT ON COLUMN estimator.evidence_blobs.path IS 'Storage path: evidence/quote/{QUOTE_ID}/{STAGE}/{HASH}.json';

CREATE INDEX idx_evidence_quote_id_created ON estimator.evidence_blobs(quote_id, created_at DESC);
CREATE INDEX idx_evidence_stage ON estimator.evidence_blobs(stage);

-- ============================================================================
-- PART 2: FUNCTIONS AND TRIGGERS
-- ============================================================================

-- FUNCTION: update_updated_at
-- Purpose: Automatically update updated_at column to current UTC timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION public.update_updated_at() IS 'Automatically updates updated_at column to current UTC timestamp on UPDATE';

-- FUNCTION: check_sha256
-- Purpose: Validate SHA256 hash format (64 hex characters)
CREATE OR REPLACE FUNCTION public.check_sha256(hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN hash IS NOT NULL
        AND length(hash) = 64
        AND hash ~ '^[a-f0-9]{64}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;

COMMENT ON FUNCTION public.check_sha256(TEXT) IS 'Validates SHA256 hash format (64 lowercase hex characters)';

-- FUNCTION: validate_evidence_integrity
-- Purpose: Verify evidence SHA256 matches stored hash
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

-- FUNCTION: calculate_quote_totals
-- Purpose: Recalculate quote totals from quote_items
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

-- FUNCTION: get_phase_balance
-- Purpose: Calculate phase load balance for a panel
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
-- PART 3: GRANTS AND ROW LEVEL SECURITY
-- ============================================================================

-- Grant schema usage
GRANT USAGE ON SCHEMA estimator TO authenticated, anon;
GRANT USAGE ON SCHEMA shared TO authenticated, anon;

-- Grant table access (RLS will control actual permissions)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA estimator TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA shared TO authenticated;

-- Service role gets full access
GRANT ALL ON ALL TABLES IN SCHEMA estimator TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA shared TO service_role;

-- Enable RLS on all tables
ALTER TABLE estimator.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.breakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.evidence_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared.catalog_items ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- PART 4: RLS POLICIES
-- ============================================================================

-- ESTIMATOR.DOCUMENTS POLICIES
CREATE POLICY "documents_service_role_all"
ON estimator.documents
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "documents_authenticated_select"
ON estimator.documents
FOR SELECT
TO authenticated
USING (true);

-- ESTIMATOR.EVIDENCE_BLOBS POLICIES
CREATE POLICY "evidence_service_role_all"
ON estimator.evidence_blobs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "evidence_authenticated_select"
ON estimator.evidence_blobs
FOR SELECT
TO authenticated
USING (true);

-- SHARED.CATALOG_ITEMS POLICIES
CREATE POLICY "catalog_public_select"
ON shared.catalog_items
FOR SELECT
TO anon, authenticated
USING (is_active = true);

CREATE POLICY "catalog_service_role_all"
ON shared.catalog_items
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- ============================================================================
-- SCHEMA COMMENTS
-- ============================================================================

COMMENT ON SCHEMA estimator IS 'KIS Estimator domain - quotes, panels, breakers, evidence';
COMMENT ON SCHEMA shared IS 'Shared resources - catalog items, reference data';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- This migration establishes:
-- - Two schemas (estimator, shared)
-- - 7 tables with proper indexes and constraints
-- - 5 database functions for business logic
-- - 5 updated_at triggers
-- - RLS policies for security
-- - All timestamps in TIMESTAMPTZ with UTC
-- - SHA256 validation for evidence integrity
-- ============================================================================