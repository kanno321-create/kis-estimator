<<<<<<< HEAD
-- ============================================================================
-- KIS Estimator Database Schema
-- Supabase PostgreSQL with TIMESTAMPTZ/UTC Standard
-- ============================================================================

-- Drop existing schemas if recreating (DEV ONLY - comment out in production)
-- DROP SCHEMA IF EXISTS estimator CASCADE;
-- DROP SCHEMA IF EXISTS shared CASCADE;
=======
-- KIS Estimator Database Schema
-- All timestamps MUST use TIMESTAMPTZ with UTC
-- Schemas: estimator, shared
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e

-- Create schemas
CREATE SCHEMA IF NOT EXISTS estimator;
CREATE SCHEMA IF NOT EXISTS shared;

<<<<<<< HEAD
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
=======
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set default timezone to UTC
SET timezone = 'UTC';

-- ==========================================
-- SHARED SCHEMA (Cross-cutting concerns)
-- ==========================================

-- Audit logs for all operations
CREATE TABLE shared.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255) NOT NULL,
    trace_id UUID NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_audit_logs_trace_id ON shared.audit_logs(trace_id);
CREATE INDEX idx_audit_logs_created_at ON shared.audit_logs(created_at DESC);

-- ==========================================
-- ESTIMATOR SCHEMA (Core business logic)
-- ==========================================

-- Customers
CREATE TABLE estimator.customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_customers_name ON estimator.customers(name);

-- Quotes (main estimates)
CREATE TABLE estimator.quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID REFERENCES estimator.customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    totals JSONB NOT NULL DEFAULT '{"subtotal": 0, "tax": 0, "total": 0}',
    currency VARCHAR(3) NOT NULL DEFAULT 'KRW',
    evidence_sha VARCHAR(64),
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    CONSTRAINT check_evidence_sha CHECK (evidence_sha ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_quotes_customer_id ON estimator.quotes(customer_id);
CREATE INDEX idx_quotes_status ON estimator.quotes(status);
CREATE INDEX idx_quotes_created_at ON estimator.quotes(created_at DESC);
CREATE INDEX idx_quotes_idempotency_key ON estimator.quotes(idempotency_key);

-- Quote items (line items)
CREATE TABLE estimator.quote_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES estimator.quotes(id) ON DELETE CASCADE NOT NULL,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('enclosure', 'breaker_main', 'breaker_branch', 'accessory')),
    name VARCHAR(255) NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price DECIMAL(15, 2),
    amount DECIMAL(15, 2),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_quote_items_quote_id ON estimator.quote_items(quote_id);

-- Panels (electrical panels)
CREATE TABLE estimator.panels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES estimator.quotes(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    enclosure_sku VARCHAR(100),
    fit_score DECIMAL(3, 2) CHECK (fit_score >= 0 AND fit_score <= 1),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_panels_quote_id ON estimator.panels(quote_id);

-- Breakers (circuit breakers)
CREATE TABLE estimator.breakers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    panel_id UUID REFERENCES estimator.panels(id) ON DELETE CASCADE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('main', 'branch', 'earth_leakage', 'surge_protector')),
    poles INTEGER NOT NULL CHECK (poles IN (1, 2, 3, 4)),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    qty INTEGER NOT NULL CHECK (qty > 0),
    brand VARCHAR(100),
    phase CHAR(1) CHECK (phase IN ('R', 'S', 'T')),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_breakers_panel_id ON estimator.breakers(panel_id);
CREATE INDEX idx_breakers_type ON estimator.breakers(type);

-- Documents (generated PDFs, Excel files)
CREATE TABLE estimator.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES estimator.quotes(id) ON DELETE CASCADE NOT NULL,
    kind VARCHAR(10) NOT NULL CHECK (kind IN ('pdf', 'xlsx', 'svg')),
    path TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    CONSTRAINT check_sha256 CHECK (sha256 ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_documents_quote_id ON estimator.documents(quote_id);
CREATE INDEX idx_documents_kind ON estimator.documents(kind);

-- Catalog items (product catalog)
CREATE TABLE estimator.catalog_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    kind VARCHAR(50) NOT NULL CHECK (kind IN ('enclosure', 'breaker', 'accessory')),
    name VARCHAR(255) NOT NULL,
    spec JSONB NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL CHECK (unit_price >= 0),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

CREATE INDEX idx_catalog_items_kind ON estimator.catalog_items(kind);
CREATE INDEX idx_catalog_items_name ON estimator.catalog_items(name);

-- Evidence blobs (audit trail)
CREATE TABLE estimator.evidence_blobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES estimator.quotes(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    path TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    CONSTRAINT check_evidence_sha256 CHECK (sha256 ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_evidence_blobs_quote_id ON estimator.evidence_blobs(quote_id);
CREATE INDEX idx_evidence_blobs_stage ON estimator.evidence_blobs(stage);
CREATE INDEX idx_evidence_blobs_created_at ON estimator.evidence_blobs(created_at DESC);

-- ==========================================
-- FUNCTIONS & TRIGGERS
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION estimator.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to all tables with updated_at
CREATE TRIGGER update_quotes_updated_at BEFORE UPDATE ON estimator.quotes
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

CREATE TRIGGER update_quote_items_updated_at BEFORE UPDATE ON estimator.quote_items
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

CREATE TRIGGER update_panels_updated_at BEFORE UPDATE ON estimator.panels
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

CREATE TRIGGER update_breakers_updated_at BEFORE UPDATE ON estimator.breakers
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

CREATE TRIGGER update_catalog_items_updated_at BEFORE UPDATE ON estimator.catalog_items
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON estimator.customers
    FOR EACH ROW EXECUTE FUNCTION estimator.update_updated_at_column();

-- ==========================================
-- VIEWS
-- ==========================================

-- Quote summary view
CREATE VIEW estimator.v_quote_summary AS
SELECT
    q.id,
    q.status,
    c.name as customer_name,
    c.company,
    q.totals->>'total' as total_amount,
    q.currency,
    q.created_at,
    q.updated_at,
    COUNT(DISTINCT p.id) as panel_count,
    COUNT(DISTINCT qi.id) as item_count
FROM estimator.quotes q
LEFT JOIN estimator.customers c ON q.customer_id = c.id
LEFT JOIN estimator.panels p ON p.quote_id = q.id
LEFT JOIN estimator.quote_items qi ON qi.quote_id = q.id
GROUP BY q.id, c.name, c.company;

-- Phase balance analysis view
CREATE VIEW estimator.v_phase_balance AS
SELECT
    p.id as panel_id,
    p.name as panel_name,
    SUM(CASE WHEN b.phase = 'R' THEN b.capacity * b.qty ELSE 0 END) as phase_r_load,
    SUM(CASE WHEN b.phase = 'S' THEN b.capacity * b.qty ELSE 0 END) as phase_s_load,
    SUM(CASE WHEN b.phase = 'T' THEN b.capacity * b.qty ELSE 0 END) as phase_t_load,
    COUNT(*) as breaker_count
FROM estimator.panels p
LEFT JOIN estimator.breakers b ON b.panel_id = p.id
GROUP BY p.id, p.name;

-- ==========================================
-- PERMISSIONS (Example for production)
-- ==========================================

-- Create roles
CREATE ROLE estimator_read;
CREATE ROLE estimator_write;
CREATE ROLE estimator_admin;

-- Grant permissions
GRANT USAGE ON SCHEMA estimator TO estimator_read, estimator_write, estimator_admin;
GRANT USAGE ON SCHEMA shared TO estimator_read, estimator_write, estimator_admin;

GRANT SELECT ON ALL TABLES IN SCHEMA estimator TO estimator_read;
GRANT SELECT ON ALL TABLES IN SCHEMA shared TO estimator_read;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA estimator TO estimator_write;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA shared TO estimator_write;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA estimator TO estimator_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA shared TO estimator_admin;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA estimator TO estimator_write, estimator_admin;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA shared TO estimator_write, estimator_admin;
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
