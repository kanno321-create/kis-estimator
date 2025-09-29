-- ==========================================
-- Seed Data for KIS Estimator
-- ==========================================

-- Insert catalog items
INSERT INTO catalog_items (id, kind, name, spec, unit_price, meta) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'enclosure', '외함 2000x800x400 (IP54)',
 '{"width": 2000, "height": 800, "depth": 400, "ip_rating": "IP54", "material": "steel", "color": "RAL7035"}'::jsonb,
 850000, '{"sku": "ENC-2000x800x400", "manufacturer": "KIS Electric", "weight_kg": 45, "door_type": "single"}'::jsonb),

('550e8400-e29b-41d4-a716-446655440002', 'enclosure', '외함 1600x800x400 (IP54)',
 '{"width": 1600, "height": 800, "depth": 400, "ip_rating": "IP54", "material": "steel", "color": "RAL7035"}'::jsonb,
 720000, '{"sku": "ENC-1600x800x400", "manufacturer": "KIS Electric", "weight_kg": 38, "door_type": "single"}'::jsonb),

('550e8400-e29b-41d4-a716-446655440003', 'breaker', '메인 차단기 3P 100A',
 '{"type": "main", "poles": 3, "capacity": 100, "breaking_capacity": "35kA", "voltage": "380V"}'::jsonb,
 125000, '{"sku": "BRK-M3P100", "manufacturer": "LS Electric", "width_mm": 75, "height_mm": 130}'::jsonb),

('550e8400-e29b-41d4-a716-446655440004', 'breaker', '메인 차단기 3P 200A',
 '{"type": "main", "poles": 3, "capacity": 200, "breaking_capacity": "50kA", "voltage": "380V"}'::jsonb,
 245000, '{"sku": "BRK-M3P200", "manufacturer": "LS Electric", "width_mm": 105, "height_mm": 160}'::jsonb),

('550e8400-e29b-41d4-a716-446655440005', 'breaker', '분기 차단기 2P 20A',
 '{"type": "branch", "poles": 2, "capacity": 20, "breaking_capacity": "10kA", "voltage": "220V"}'::jsonb,
 18000, '{"sku": "BRK-B2P20", "manufacturer": "LS Electric", "width_mm": 36, "height_mm": 80}'::jsonb),

('550e8400-e29b-41d4-a716-446655440006', 'breaker', '분기 차단기 2P 30A',
 '{"type": "branch", "poles": 2, "capacity": 30, "breaking_capacity": "10kA", "voltage": "220V"}'::jsonb,
 22000, '{"sku": "BRK-B2P30", "manufacturer": "LS Electric", "width_mm": 36, "height_mm": 80}'::jsonb),

('550e8400-e29b-41d4-a716-446655440007', 'breaker', '누전 차단기 2P 30A 30mA',
 '{"type": "earth_leakage", "poles": 2, "capacity": 30, "sensitivity": "30mA", "voltage": "220V"}'::jsonb,
 45000, '{"sku": "BRK-EL2P30", "manufacturer": "LS Electric", "width_mm": 36, "height_mm": 80}'::jsonb),

('550e8400-e29b-41d4-a716-446655440008', 'accessory', '부스바 3P 200A',
 '{"type": "busbar", "phases": 3, "capacity": 200, "length_mm": 1000, "material": "copper"}'::jsonb,
 85000, '{"sku": "ACC-BB3P200", "manufacturer": "KIS Electric", "cross_section_mm2": 50}'::jsonb),

('550e8400-e29b-41d4-a716-446655440009', 'accessory', '단자대 12P',
 '{"type": "terminal_block", "points": 12, "max_wire_mm2": 4, "voltage": "600V"}'::jsonb,
 8500, '{"sku": "ACC-TB12", "manufacturer": "Phoenix Contact", "mounting": "DIN rail"}'::jsonb),

('550e8400-e29b-41d4-a716-446655440010', 'accessory', '서지 보호기 3P Type2',
 '{"type": "surge_protector", "poles": 3, "class": "Type 2", "discharge_current": "40kA", "voltage": "380V"}'::jsonb,
 125000, '{"sku": "ACC-SPD3P-T2", "manufacturer": "ABB", "width_mm": 54, "response_time_ns": 25}'::jsonb);

-- Insert sample customer
INSERT INTO customers (id, name, contact, company, meta) VALUES
('550e8400-e29b-41d4-a716-446655440100', '홍길동', '010-1234-5678', '한국전기공사',
 '{"email": "hong@example.com", "address": "서울시 강남구", "business_no": "123-45-67890"}'::jsonb);

-- Insert sample quote
INSERT INTO quotes (id, customer_id, status, totals, currency, evidence_sha) VALUES
('550e8400-e29b-41d4-a716-446655440200', '550e8400-e29b-41d4-a716-446655440100',
 'completed', '{"subtotal": 2500000, "tax": 250000, "total": 2750000}'::jsonb, 'KRW',
 'a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890');

-- Insert sample panel
INSERT INTO panels (id, quote_id, name, enclosure_sku, fit_score, meta) VALUES
('550e8400-e29b-41d4-a716-446655440300', '550e8400-e29b-41d4-a716-446655440200',
 'MCC-01 메인 분전반', 'ENC-2000x800x400', 0.95,
 '{"location": "1층 전기실", "installation_date": "2024-12-30"}'::jsonb);

-- Insert sample breakers
INSERT INTO breakers (id, panel_id, type, poles, capacity, qty, brand, phase) VALUES
('550e8400-e29b-41d4-a716-446655440401', '550e8400-e29b-41d4-a716-446655440300', 'main', 3, 200, 1, 'LS Electric', 'R'),
('550e8400-e29b-41d4-a716-446655440402', '550e8400-e29b-41d4-a716-446655440300', 'branch', 2, 30, 5, 'LS Electric', 'R'),
('550e8400-e29b-41d4-a716-446655440403', '550e8400-e29b-41d4-a716-446655440300', 'branch', 2, 30, 5, 'LS Electric', 'S'),
('550e8400-e29b-41d4-a716-446655440404', '550e8400-e29b-41d4-a716-446655440300', 'branch', 2, 30, 5, 'LS Electric', 'T'),
('550e8400-e29b-41d4-a716-446655440405', '550e8400-e29b-41d4-a716-446655440300', 'earth_leakage', 2, 30, 3, 'LS Electric', NULL);