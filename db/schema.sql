-- KIS Estimator Database Schema
-- All timestamps MUST use TIMESTAMPTZ with UTC
-- Schemas: estimator, shared

-- Create schemas
CREATE SCHEMA IF NOT EXISTS estimator;
CREATE SCHEMA IF NOT EXISTS shared;

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