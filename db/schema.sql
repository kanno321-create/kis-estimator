-- ============================================================================
-- KIS Estimator Database Schema
-- Supabase PostgreSQL with TIMESTAMPTZ/UTC Standard
-- ============================================================================

-- Drop existing schemas if recreating (DEV ONLY - comment out in production)
-- DROP SCHEMA IF EXISTS estimator CASCADE;
-- DROP SCHEMA IF EXISTS shared CASCADE;

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
-- GRANTS
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

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE estimator.quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.breakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE estimator.evidence_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared.catalog_items ENABLE ROW LEVEL SECURITY;

COMMENT ON SCHEMA estimator IS 'KIS Estimator domain - quotes, panels, breakers, evidence';
COMMENT ON SCHEMA shared IS 'Shared resources - catalog items, reference data';