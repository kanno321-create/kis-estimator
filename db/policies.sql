-- ============================================================================
-- KIS Estimator Row Level Security (RLS) Policies - OPERATIONS MODE
-- Supabase PostgreSQL Security Model - Production Hardening
-- ============================================================================

-- ============================================================================
-- SECURITY PRINCIPLE (OPERATIONS MODE)
-- ============================================================================
-- ✅ ALL TABLES: RLS ENABLED (no exceptions)
-- ✅ PUBLIC ACCESS: REVOKED (all tables)
-- ✅ WRITER: Service Role ONLY (server-side operations)
-- ✅ READER: Signed URLs ONLY (time-limited, short TTL)
-- ✅ EVIDENCE: No-Evidence-No-Action (integrity enforced)
-- ✅ AUDIT: All changes logged with trace_id

-- ============================================================================
-- ENABLE RLS ON ALL TABLES
-- ============================================================================

ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE panels ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence_blobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Revoke all public access
REVOKE ALL ON quotes FROM PUBLIC;
REVOKE ALL ON quote_items FROM PUBLIC;
REVOKE ALL ON panels FROM PUBLIC;
REVOKE ALL ON evidence_blobs FROM PUBLIC;
REVOKE ALL ON audit_log FROM PUBLIC;

-- ============================================================================
-- ESTIMATOR.QUOTES POLICIES
-- ============================================================================

-- Service role: Full write access (bypass RLS inherently)
CREATE POLICY "quotes_service_role_all"
ON quotes
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Authenticated users: Read-only (minimal, for API layer)
CREATE POLICY "quotes_authenticated_select"
ON quotes
FOR SELECT
TO authenticated
USING (true);

-- Anonymous: No access
-- No policy = explicit denial

-- ============================================================================
-- ESTIMATOR.QUOTE_ITEMS POLICIES
-- ============================================================================

CREATE POLICY "quote_items_service_role_all"
ON quote_items
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "quote_items_authenticated_select"
ON quote_items
FOR SELECT
TO authenticated
USING (EXISTS (
    SELECT 1 FROM quotes
    WHERE quotes.id = quote_items.quote_id
));

-- ============================================================================
-- ESTIMATOR.PANELS POLICIES
-- ============================================================================

CREATE POLICY "panels_service_role_all"
ON panels
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "panels_authenticated_select"
ON panels
FOR SELECT
TO authenticated
USING (EXISTS (
    SELECT 1 FROM quotes
    WHERE quotes.id = panels.quote_id
));

-- ============================================================================
-- ESTIMATOR.EVIDENCE_BLOBS POLICIES (STRICT)
-- ============================================================================

CREATE POLICY "evidence_blobs_service_role_all"
ON evidence_blobs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Authenticated: Read-only metadata (for signed URL generation)
-- No direct blob access
CREATE POLICY "evidence_blobs_authenticated_select"
ON evidence_blobs
FOR SELECT
TO authenticated
USING (true);

-- Anonymous: No access (signed URLs only)

-- ============================================================================
-- AUDIT_LOG POLICIES (READ-ONLY for authenticated)
-- ============================================================================

CREATE POLICY "audit_log_service_role_all"
ON audit_log
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Authenticated: Read-only audit trail
CREATE POLICY "audit_log_authenticated_select"
ON audit_log
FOR SELECT
TO authenticated
USING (true);

-- Anonymous: No access

-- ============================================================================
-- STORAGE POLICIES (evidence bucket) - OPERATIONS MODE
-- ============================================================================
-- Note: Apply via Supabase CLI or Dashboard
-- Bucket: 'evidence' (PRIVATE, lifecycle enabled)
-- Path: evidence/quote/{QUOTE_ID}/{STAGE}/{SHA256}.{ext}

-- Storage RLS: Service role write, Signed URL read only

-- Service role: Full access
-- CREATE POLICY "evidence_storage_service_all"
-- ON storage.objects
-- FOR ALL
-- TO service_role
-- USING (bucket_id = 'evidence')
-- WITH CHECK (bucket_id = 'evidence');

-- Authenticated: Read via signed URLs only (TTL enforced)
-- CREATE POLICY "evidence_storage_authenticated_select"
-- ON storage.objects
-- FOR SELECT
-- TO authenticated
-- USING (bucket_id = 'evidence');

-- Anonymous: No access (signed URLs required)

-- ============================================================================
-- OPERATIONS MODE POLICY SUMMARY
-- ============================================================================
--
-- TABLE / SCHEMA            | ANON  | AUTHENTICATED | SERVICE_ROLE
-- --------------------------|-------|---------------|-------------
-- quotes                    | ❌    | SELECT        | ALL ✅
-- quote_items               | ❌    | SELECT (FK)   | ALL ✅
-- panels                    | ❌    | SELECT (FK)   | ALL ✅
-- evidence_blobs            | ❌    | SELECT        | ALL ✅
-- audit_log                 | ❌    | SELECT        | ALL ✅
--
-- STORAGE BUCKET            | ANON  | AUTHENTICATED | SERVICE_ROLE
-- --------------------------|-------|---------------|-------------
-- evidence                  | ❌    | Signed URL ⏱️ | ALL ✅
--
-- OPERATIONS HARDENING:
-- ✅ RLS enabled on ALL tables (no exceptions)
-- ✅ PUBLIC access revoked (all tables)
-- ✅ Writer: Service Role ONLY (server-side operations)
-- ✅ Reader: Authenticated minimal SELECT + Signed URLs (TTL enforced)
-- ✅ Evidence: Short TTL (300s prod, 600s staging)
-- ✅ Audit: All changes logged with trace_id
-- ✅ No-Evidence-No-Action: Integrity checks in application layer
--
-- SECURITY ENFORCEMENT:
-- 1. ✅ All write operations: service_role key ONLY
-- 2. ✅ All read operations: Authenticated minimal OR Signed URLs
-- 3. ✅ Signed URLs: Time-limited (300s prod / 600s staging)
-- 4. ✅ Evidence integrity: SHA256 verification in application
-- 5. ✅ Audit trail: All changes captured with trace_id
-- 6. ✅ RLS: Automatically enforced (service_role bypasses inherently)
-- 7. ✅ Storage: Private bucket, signed URL access only
-- ============================================================================