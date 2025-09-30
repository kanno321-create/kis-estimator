-- ==========================================
-- KIS Estimator Database Schema for Supabase
-- ==========================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA extensions;

-- ==========================================
-- ESTIMATOR SCHEMA TABLES
-- ==========================================

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    contact VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Quotes (main estimates)
CREATE TABLE IF NOT EXISTS quotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    totals JSONB NOT NULL DEFAULT '{"subtotal": 0, "tax": 0, "total": 0}'::jsonb,
    currency VARCHAR(3) NOT NULL DEFAULT 'KRW',
    evidence_sha VARCHAR(64),
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Quote items (line items)
CREATE TABLE IF NOT EXISTS quote_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE NOT NULL,
    item_type VARCHAR(50) NOT NULL CHECK (item_type IN ('enclosure', 'breaker_main', 'breaker_branch', 'accessory')),
    name VARCHAR(255) NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price DECIMAL(15, 2),
    amount DECIMAL(15, 2),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Panels (electrical panels)
CREATE TABLE IF NOT EXISTS panels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE NOT NULL,
    name VARCHAR(255) NOT NULL,
    enclosure_sku VARCHAR(100),
    fit_score DECIMAL(3, 2) CHECK (fit_score >= 0 AND fit_score <= 1),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Breakers (circuit breakers)
CREATE TABLE IF NOT EXISTS breakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    panel_id UUID REFERENCES panels(id) ON DELETE CASCADE NOT NULL,
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

-- Documents (generated PDFs, Excel files)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE NOT NULL,
    kind VARCHAR(10) NOT NULL CHECK (kind IN ('pdf', 'xlsx', 'svg')),
    path TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Catalog items (product catalog)
CREATE TABLE IF NOT EXISTS catalog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind VARCHAR(50) NOT NULL CHECK (kind IN ('enclosure', 'breaker', 'accessory')),
    name VARCHAR(255) NOT NULL,
    spec JSONB NOT NULL,
    unit_price DECIMAL(15, 2) NOT NULL CHECK (unit_price >= 0),
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Evidence blobs (audit trail)
CREATE TABLE IF NOT EXISTS evidence_blobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    path TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- Audit logs for all operations
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    target VARCHAR(255) NOT NULL,
    trace_id UUID NOT NULL,
    meta JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_quotes_created_at ON quotes(created_at DESC);
CREATE INDEX idx_quotes_idempotency_key ON quotes(idempotency_key);
CREATE INDEX idx_quote_items_quote_id ON quote_items(quote_id);
CREATE INDEX idx_panels_quote_id ON panels(quote_id);
CREATE INDEX idx_breakers_panel_id ON breakers(panel_id);
CREATE INDEX idx_breakers_type ON breakers(type);
CREATE INDEX idx_documents_quote_id ON documents(quote_id);
CREATE INDEX idx_documents_kind ON documents(kind);
CREATE INDEX idx_catalog_items_kind ON catalog_items(kind);
CREATE INDEX idx_catalog_items_name ON catalog_items(name);
CREATE INDEX idx_evidence_blobs_quote_id ON evidence_blobs(quote_id);
CREATE INDEX idx_evidence_blobs_stage ON evidence_blobs(stage);
CREATE INDEX idx_audit_logs_trace_id ON audit_logs(trace_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ==========================================
-- FUNCTIONS & TRIGGERS
-- ==========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to all tables with updated_at
CREATE TRIGGER update_quotes_updated_at BEFORE UPDATE ON quotes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_quote_items_updated_at BEFORE UPDATE ON quote_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_panels_updated_at BEFORE UPDATE ON panels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_breakers_updated_at BEFORE UPDATE ON breakers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_catalog_items_updated_at BEFORE UPDATE ON catalog_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==========================================
-- VIEWS
-- ==========================================

-- Quote summary view
CREATE OR REPLACE VIEW quote_summary AS
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
FROM quotes q
LEFT JOIN customers c ON q.customer_id = c.id
LEFT JOIN panels p ON p.quote_id = q.id
LEFT JOIN quote_items qi ON qi.quote_id = q.id
GROUP BY q.id, c.name, c.company;

-- Phase balance analysis view
CREATE OR REPLACE VIEW phase_balance AS
SELECT
    p.id as panel_id,
    p.name as panel_name,
    SUM(CASE WHEN b.phase = 'R' THEN b.capacity * b.qty ELSE 0 END) as phase_r_load,
    SUM(CASE WHEN b.phase = 'S' THEN b.capacity * b.qty ELSE 0 END) as phase_s_load,
    SUM(CASE WHEN b.phase = 'T' THEN b.capacity * b.qty ELSE 0 END) as phase_t_load,
    COUNT(*) as breaker_count
FROM panels p
LEFT JOIN breakers b ON b.panel_id = p.id
GROUP BY p.id, p.name;

-- ==========================================
-- ROW LEVEL SECURITY (RLS) for Supabase
-- ==========================================

-- Enable RLS on all tables
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE breakers ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE catalog_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
-- (You can customize these based on your auth requirements)

-- Customers: authenticated users can read all, write own
CREATE POLICY "Users can view all customers" ON customers
    FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "Users can create customers" ON customers
    FOR INSERT TO authenticated
    WITH CHECK (true);

-- Quotes: authenticated users can manage their quotes
CREATE POLICY "Users can view all quotes" ON quotes
    FOR SELECT TO authenticated
    USING (true);

CREATE POLICY "Users can create quotes" ON quotes
    FOR INSERT TO authenticated
    WITH CHECK (true);

CREATE POLICY "Users can update their quotes" ON quotes
    FOR UPDATE TO authenticated
    USING (true);

-- Catalog items: everyone can read
CREATE POLICY "Public can view catalog" ON catalog_items
    FOR SELECT TO anon, authenticated
    USING (true);

-- Audit logs: read-only for authenticated
CREATE POLICY "Users can view audit logs" ON audit_logs
    FOR SELECT TO authenticated
    USING (true);