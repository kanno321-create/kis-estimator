#!/usr/bin/env python3
"""
Database Initialization Script for KIS Estimator
Creates all necessary tables, functions, and indexes in Supabase
"""

import os
import sys
import asyncio
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Database connection from environment
DATABASE_URL = os.getenv('SUPABASE_DB_URL', os.getenv('DATABASE_URL'))

# SQL for creating tables
CREATE_TABLES_SQL = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Quotes table (견적)
CREATE TABLE IF NOT EXISTS quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_number VARCHAR(50) UNIQUE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    project_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'draft',
    total_amount DECIMAL(15,2),
    created_by VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    completed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Quote items table (견적 항목)
CREATE TABLE IF NOT EXISTS quote_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    breaker_sku VARCHAR(100) NOT NULL,
    breaker_name VARCHAR(200),
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(12,2),
    total_price DECIMAL(12,2),
    phase_assignment CHAR(1) CHECK (phase_assignment IN ('A', 'B', 'C')),
    position_x INTEGER,
    position_y INTEGER,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Panels table (패널/외함)
CREATE TABLE IF NOT EXISTS panels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    enclosure_sku VARCHAR(100),
    enclosure_name VARCHAR(200),
    width_mm INTEGER,
    height_mm INTEGER,
    depth_mm INTEGER,
    ip_rating VARCHAR(10),
    fit_score DECIMAL(3,2),
    phase_balance DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Evidence blobs table (증거 데이터)
CREATE TABLE IF NOT EXISTS evidence_blobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    stage VARCHAR(50) NOT NULL,
    hash VARCHAR(64) NOT NULL,
    data JSONB NOT NULL,
    validation_result JSONB,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    UNIQUE(quote_id, stage, hash)
);

-- Breaker catalog table (브레이커 카탈로그)
CREATE TABLE IF NOT EXISTS breaker_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    model_name VARCHAR(200),
    rating_amps INTEGER,
    poles INTEGER,
    width_mm DECIMAL(6,2),
    height_mm DECIMAL(6,2),
    depth_mm DECIMAL(6,2),
    price DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    specifications JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Enclosure catalog table (외함 카탈로그)
CREATE TABLE IF NOT EXISTS enclosure_catalog (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku VARCHAR(100) UNIQUE NOT NULL,
    manufacturer VARCHAR(100),
    model_name VARCHAR(200),
    width_mm INTEGER,
    height_mm INTEGER,
    depth_mm INTEGER,
    usable_width_mm INTEGER,
    usable_height_mm INTEGER,
    ip_rating VARCHAR(10),
    door_type VARCHAR(50),
    material VARCHAR(50),
    price DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    specifications JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Validation rules table
CREATE TABLE IF NOT EXISTS validation_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_name VARCHAR(100) UNIQUE NOT NULL,
    rule_type VARCHAR(50),
    threshold_value DECIMAL(10,2),
    error_message VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50),
    entity_id UUID,
    action VARCHAR(50),
    user_id VARCHAR(200),
    changes JSONB,
    trace_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- SSE events table for progress tracking
CREATE TABLE IF NOT EXISTS sse_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID REFERENCES quotes(id) ON DELETE CASCADE,
    event_type VARCHAR(50),
    stage VARCHAR(50),
    progress DECIMAL(3,2),
    message TEXT,
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
CREATE INDEX IF NOT EXISTS idx_quotes_created_at ON quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quote_items_quote_id ON quote_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_panels_quote_id ON panels(quote_id);
CREATE INDEX IF NOT EXISTS idx_evidence_quote_id ON evidence_blobs(quote_id);
CREATE INDEX IF NOT EXISTS idx_evidence_stage ON evidence_blobs(stage);
CREATE INDEX IF NOT EXISTS idx_breaker_catalog_sku ON breaker_catalog(sku);
CREATE INDEX IF NOT EXISTS idx_enclosure_catalog_sku ON enclosure_catalog(sku);
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sse_events_quote_id ON sse_events(quote_id, created_at DESC);
"""

# SQL for creating functions
CREATE_FUNCTIONS_SQL = """
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update trigger to tables with updated_at
DO $$
BEGIN
    -- Quotes table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_quotes_updated_at') THEN
        CREATE TRIGGER update_quotes_updated_at BEFORE UPDATE ON quotes
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Customers table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_customers_updated_at') THEN
        CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Breaker catalog table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_breaker_catalog_updated_at') THEN
        CREATE TRIGGER update_breaker_catalog_updated_at BEFORE UPDATE ON breaker_catalog
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- Enclosure catalog table
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_enclosure_catalog_updated_at') THEN
        CREATE TRIGGER update_enclosure_catalog_updated_at BEFORE UPDATE ON enclosure_catalog
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Function to calculate phase balance
CREATE OR REPLACE FUNCTION calculate_phase_balance(quote_uuid UUID)
RETURNS DECIMAL AS $$
DECLARE
    phase_a_load DECIMAL;
    phase_b_load DECIMAL;
    phase_c_load DECIMAL;
    max_load DECIMAL;
    min_load DECIMAL;
    balance_percent DECIMAL;
BEGIN
    -- Calculate load per phase
    SELECT COALESCE(SUM(CASE WHEN phase_assignment = 'A' THEN quantity ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN phase_assignment = 'B' THEN quantity ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN phase_assignment = 'C' THEN quantity ELSE 0 END), 0)
    INTO phase_a_load, phase_b_load, phase_c_load
    FROM quote_items
    WHERE quote_id = quote_uuid;

    -- Find max and min loads
    max_load := GREATEST(phase_a_load, phase_b_load, phase_c_load);
    min_load := LEAST(phase_a_load, phase_b_load, phase_c_load);

    -- Calculate balance percentage
    IF max_load > 0 THEN
        balance_percent := ((max_load - min_load) / max_load) * 100;
    ELSE
        balance_percent := 0;
    END IF;

    RETURN ROUND(balance_percent, 2);
END;
$$ LANGUAGE 'plpgsql';

-- Function to validate quote completeness
CREATE OR REPLACE FUNCTION validate_quote_completeness(quote_uuid UUID)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    item_count INTEGER;
    panel_count INTEGER;
    evidence_count INTEGER;
BEGIN
    -- Count related entities
    SELECT COUNT(*) INTO item_count FROM quote_items WHERE quote_id = quote_uuid;
    SELECT COUNT(*) INTO panel_count FROM panels WHERE quote_id = quote_uuid;
    SELECT COUNT(*) INTO evidence_count FROM evidence_blobs WHERE quote_id = quote_uuid;

    -- Build result JSON
    result := jsonb_build_object(
        'is_complete', (item_count > 0 AND panel_count > 0),
        'has_items', item_count > 0,
        'has_panel', panel_count > 0,
        'has_evidence', evidence_count > 0,
        'item_count', item_count,
        'panel_count', panel_count,
        'evidence_count', evidence_count,
        'phase_balance', calculate_phase_balance(quote_uuid)
    );

    RETURN result;
END;
$$ LANGUAGE 'plpgsql';

-- Function to generate quote number
CREATE OR REPLACE FUNCTION generate_quote_number()
RETURNS VARCHAR AS $$
DECLARE
    new_number VARCHAR;
    year_month VARCHAR;
    seq_num INTEGER;
BEGIN
    -- Format: EST-YYYYMM-XXXX
    year_month := TO_CHAR(now(), 'YYYYMM');

    -- Get next sequence number for this month
    SELECT COALESCE(MAX(CAST(SUBSTRING(quote_number FROM 13 FOR 4) AS INTEGER)), 0) + 1
    INTO seq_num
    FROM quotes
    WHERE quote_number LIKE 'EST-' || year_month || '-%';

    -- Format with leading zeros
    new_number := 'EST-' || year_month || '-' || LPAD(seq_num::TEXT, 4, '0');

    RETURN new_number;
END;
$$ LANGUAGE 'plpgsql';
"""

# Sample data for testing
INSERT_SAMPLE_DATA_SQL = """
-- Insert sample validation rules
INSERT INTO validation_rules (rule_name, rule_type, threshold_value, error_message) VALUES
('phase_balance_check', 'phase_balance', 4.0, 'Phase balance exceeds 4% threshold'),
('min_fit_score', 'fit_score', 0.90, 'Enclosure fit score below 90% minimum'),
('max_thermal_load', 'thermal', 0.95, 'Thermal load exceeds 95% capacity'),
('clearance_minimum', 'clearance', 10.0, 'Minimum clearance violation (10mm required)')
ON CONFLICT (rule_name) DO NOTHING;

-- Insert sample breaker catalog items
INSERT INTO breaker_catalog (sku, manufacturer, model_name, rating_amps, poles, width_mm, height_mm, depth_mm, price) VALUES
('BKR-MCB-20A-1P', 'LS Electric', 'MCB 20A 1P', 20, 1, 17.5, 85, 68, 25000),
('BKR-MCB-32A-1P', 'LS Electric', 'MCB 32A 1P', 32, 1, 17.5, 85, 68, 28000),
('BKR-MCB-40A-1P', 'LS Electric', 'MCB 40A 1P', 40, 1, 17.5, 85, 68, 32000),
('BKR-MCB-63A-1P', 'LS Electric', 'MCB 63A 1P', 63, 1, 17.5, 85, 68, 38000),
('BKR-MCB-20A-3P', 'LS Electric', 'MCB 20A 3P', 20, 3, 52.5, 85, 68, 65000),
('BKR-MCB-32A-3P', 'LS Electric', 'MCB 32A 3P', 32, 3, 52.5, 85, 68, 72000),
('BKR-MCB-40A-3P', 'LS Electric', 'MCB 40A 3P', 40, 3, 52.5, 85, 68, 85000),
('BKR-MCB-63A-3P', 'LS Electric', 'MCB 63A 3P', 63, 3, 52.5, 85, 68, 95000),
('BKR-MCCB-100A', 'LS Electric', 'MCCB 100A', 100, 3, 105, 130, 70, 250000),
('BKR-MCCB-200A', 'LS Electric', 'MCCB 200A', 200, 3, 140, 165, 85, 380000)
ON CONFLICT (sku) DO NOTHING;

-- Insert sample enclosure catalog items
INSERT INTO enclosure_catalog (sku, manufacturer, model_name, width_mm, height_mm, depth_mm, usable_width_mm, usable_height_mm, ip_rating, door_type, material, price) VALUES
('ENC-600x800x250', 'KIS Electric', 'Wall Mount 600x800', 600, 800, 250, 550, 750, 'IP66', 'Single', 'Steel', 450000),
('ENC-800x1000x300', 'KIS Electric', 'Floor Standing 800x1000', 800, 1000, 300, 750, 950, 'IP66', 'Single', 'Steel', 680000),
('ENC-1000x1200x350', 'KIS Electric', 'Floor Standing 1000x1200', 1000, 1200, 350, 950, 1150, 'IP66', 'Double', 'Steel', 920000),
('ENC-1200x1600x400', 'KIS Electric', 'Floor Standing 1200x1600', 1200, 1600, 400, 1150, 1550, 'IP66', 'Double', 'Steel', 1350000),
('ENC-400x500x200', 'KIS Electric', 'Compact 400x500', 400, 500, 200, 350, 450, 'IP54', 'Single', 'Plastic', 180000)
ON CONFLICT (sku) DO NOTHING;

-- Insert sample customer (for testing)
INSERT INTO customers (id, name, email, company) VALUES
('123e4567-e89b-12d3-a456-426614174000', 'Test Customer', 'test@example.com', 'Test Company Ltd.')
ON CONFLICT DO NOTHING;
"""

def init_database():
    """Initialize database with tables, functions, and sample data"""
    print("[DATABASE INIT] Starting database initialization...")
    print(f"[DATABASE INIT] Connecting to: {DATABASE_URL[:50]}...")

    try:
        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Create tables
        print("[DATABASE INIT] Creating tables...")
        cur.execute(CREATE_TABLES_SQL)
        print("[OK] Tables created successfully")

        # Create functions
        print("[DATABASE INIT] Creating functions and triggers...")
        cur.execute(CREATE_FUNCTIONS_SQL)
        print("[OK] Functions created successfully")

        # Insert sample data
        print("[DATABASE INIT] Inserting sample data...")
        cur.execute(INSERT_SAMPLE_DATA_SQL)
        print("[OK] Sample data inserted")

        # Verify tables
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        print(f"\n[DATABASE INIT] Created {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")

        # Verify functions
        cur.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name;
        """)
        functions = cur.fetchall()
        print(f"\n[DATABASE INIT] Created {len(functions)} functions:")
        for func in functions:
            print(f"  - {func[0]}")

        # Get row counts
        print("\n[DATABASE INIT] Table row counts:")
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cur.fetchone()[0]
            print(f"  - {table[0]}: {count} rows")

        # Close connection
        cur.close()
        conn.close()

        print("\n[SUCCESS] Database initialization completed!")
        print(f"  Tables: {len(tables)}")
        print(f"  Functions: {len(functions)}")
        print("  Sample data: Loaded")

        return True

    except Exception as e:
        print(f"\n[ERROR] Database initialization failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)