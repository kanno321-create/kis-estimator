-- KIS Estimator Core Database Schema
-- Version: 0.1.0-rebuild
-- Database: PostgreSQL 14+ / SQLite 3.35+

-- Drop existing tables if they exist (for clean rebuild)
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS estimate_items CASCADE;
DROP TABLE IF EXISTS estimates CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table (authentication and authorization)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user',  -- admin, manager, user
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    contact_person VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    tax_id VARCHAR(50),
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id)
);

-- Products table (enclosures, breakers, components)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,  -- enclosure, breaker, accessory
    manufacturer VARCHAR(100),
    model VARCHAR(100),
    specifications JSONB,  -- Flexible spec storage
    dimensions JSONB,      -- {width, height, depth, unit}
    price DECIMAL(12, 2),
    currency VARCHAR(10) DEFAULT 'KRW',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Estimates table (main estimation records)
CREATE TABLE estimates (
    id SERIAL PRIMARY KEY,
    estimate_no VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER REFERENCES customers(id),
    project_name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, pending, approved, rejected, completed

    -- Financial fields
    subtotal DECIMAL(15, 2),
    tax_rate DECIMAL(5, 2) DEFAULT 10.0,
    tax_amount DECIMAL(15, 2),
    discount_rate DECIMAL(5, 2) DEFAULT 0,
    discount_amount DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    currency VARCHAR(10) DEFAULT 'KRW',

    -- Technical fields (AI Estimator results)
    enclosure_data JSONB,     -- Enclosure calculation results
    breaker_data JSONB,       -- Breaker placement results
    heat_analysis JSONB,      -- Thermal analysis results
    criticality_score DECIMAL(5, 2),  -- Critic score (0-100)

    -- Metadata
    valid_until DATE,
    notes TEXT,
    internal_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP
);

-- Estimate items table (line items)
CREATE TABLE estimate_items (
    id SERIAL PRIMARY KEY,
    estimate_id INTEGER REFERENCES estimates(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    item_no INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL,
    unit VARCHAR(20) DEFAULT 'EA',
    unit_price DECIMAL(12, 2) NOT NULL,
    discount_rate DECIMAL(5, 2) DEFAULT 0,
    total_price DECIMAL(15, 2) NOT NULL,

    -- Technical specifications
    specifications JSONB,
    placement_data JSONB,  -- Position in enclosure

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs table (for tracking changes)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    action VARCHAR(20) NOT NULL,  -- INSERT, UPDATE, DELETE
    changes JSONB,
    user_id INTEGER REFERENCES users(id),
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_customers_code ON customers(code);
CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_products_code ON products(code);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_estimates_no ON estimates(estimate_no);
CREATE INDEX idx_estimates_customer ON estimates(customer_id);
CREATE INDEX idx_estimates_status ON estimates(status);
CREATE INDEX idx_estimates_created ON estimates(created_at DESC);
CREATE INDEX idx_estimate_items_estimate ON estimate_items(estimate_id);
CREATE INDEX idx_audit_logs_table_record ON audit_logs(table_name, record_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp trigger to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_estimates_updated_at BEFORE UPDATE ON estimates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_estimate_items_updated_at BEFORE UPDATE ON estimate_items
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();