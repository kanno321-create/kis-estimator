<<<<<<< HEAD
# KIS Estimator - Operations Runbook

## Supabase Database Operations

### Prerequisites
- Supabase CLI installed: `npm install -g supabase`
- Environment variables configured (see `.specify/contracts/env.md`)
- Database connection access

### Database Schema Management

#### 1. Initialize Database (First Time)
```bash
# Link to Supabase project (required once)
supabase link --project-ref YOUR_PROJECT_REF

# Apply consolidated migration
supabase db push

# OR apply single migration file explicitly
psql $SUPABASE_DB_URL < db/migrations/20250930_init.sql
```

#### 2. Lint Database Migration
```bash
# Check migration file for issues (REQUIRED before merge)
supabase db lint --file db/migrations/20250930_init.sql

# Expected output: No errors or warnings
# Any errors MUST be fixed before deployment

# Check for common issues
supabase db lint --level warning
```

#### 3. Check Database Diff
```bash
# Compare local migration with remote database (PR stage)
supabase db diff --linked

# Expected output: No differences if already deployed
# Shows pending changes if migration not yet applied

# Generate new migration from manual changes
supabase db diff --linked --file db/migrations/$(date +%Y%m%d%H%M%S)_changes.sql
```

#### 4. Apply Migrations (Production Deploy)
```bash
# STEP 1: Link to production project
supabase link --project-ref YOUR_PROD_PROJECT_REF

# STEP 2: Dry-run check (ALWAYS do this first)
supabase db diff --linked

# STEP 3: Push migrations (only on main branch merge)
supabase db push

# Verify deployment
supabase db diff --linked  # Should show no differences
```

#### 5. Rollback Migration (Emergency)
```bash
# CRITICAL: Only use in emergencies
# Rollback requires manual SQL if migration was already pushed

# Option 1: Rollback via Supabase CLI (if migration not pushed)
supabase migration down

# Option 2: Manual rollback (if migration was pushed to production)
# 1. Create rollback SQL script
cat > rollback_20250930.sql <<'EOF'
-- Drop tables in reverse order (respecting foreign keys)
DROP TABLE IF EXISTS estimator.evidence_blobs CASCADE;
DROP TABLE IF EXISTS estimator.documents CASCADE;
DROP TABLE IF EXISTS estimator.breakers CASCADE;
DROP TABLE IF EXISTS estimator.panels CASCADE;
DROP TABLE IF EXISTS estimator.quote_items CASCADE;
DROP TABLE IF EXISTS estimator.quotes CASCADE;
DROP TABLE IF EXISTS shared.catalog_items CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS public.update_updated_at() CASCADE;
DROP FUNCTION IF EXISTS public.check_sha256(TEXT);
DROP FUNCTION IF EXISTS public.validate_evidence_integrity(UUID, TEXT);
DROP FUNCTION IF EXISTS public.calculate_quote_totals(UUID);
DROP FUNCTION IF EXISTS public.get_phase_balance(UUID);

-- Drop schemas
DROP SCHEMA IF EXISTS estimator CASCADE;
DROP SCHEMA IF EXISTS shared CASCADE;
EOF

# 2. BACKUP FIRST (CRITICAL!)
supabase db dump > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql

# 3. Apply rollback
psql $SUPABASE_DB_URL < rollback_20250930.sql

# 4. Verify rollback
supabase db diff --linked

# Option 3: Restore from backup (last resort)
supabase db restore < backup_before_deploy.sql
```

#### 6. Reset Database (DEV/LOCAL ONLY)
```bash
# WARNING: This will delete ALL data
# NEVER run this on production

# Reset local database
supabase db reset

# Reset and apply migrations
supabase db reset
supabase db push
```

### Storage Operations

#### 1. Initialize Storage Bucket
```bash
# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Run initialization script
bash ops/supabase/storage_init.sh
```

#### 2. Generate Signed URLs
```bash
# Generate 10-minute signed URL for evidence file
supabase storage signed-url evidence/quote/{QUOTE_ID}/{STAGE}/{HASH}.json --expires-in 600

# Example
supabase storage signed-url evidence/quote/123e4567-e89b-12d3-a456-426614174000/enclosure/abc123.json --expires-in 600
```

**Python Example:**
```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Generate signed URL (10 minutes)
signed_url = supabase.storage.from_("evidence").create_signed_url(
    path="quote/123e4567/enclosure/abc123.json",
    expires_in=600  # seconds
)
```

#### 3. Upload Evidence Files
```bash
# Upload via CLI
supabase storage cp local_file.json evidence/quote/{QUOTE_ID}/{STAGE}/{HASH}.json

# Example
supabase storage cp output.json evidence/quote/123e4567/enclosure/abc123.json
```

**Python Example:**
```python
# Upload evidence file
with open("evidence.json", "rb") as f:
    supabase.storage.from_("evidence").upload(
        path=f"quote/{quote_id}/enclosure/{hash}.json",
        file=f,
        file_options={"content-type": "application/json"}
    )
```

#### 4. List Storage Objects
```bash
# List all objects in evidence bucket
supabase storage ls evidence/

# List objects for specific quote
supabase storage ls evidence/quote/{QUOTE_ID}/
```

#### 5. Delete Storage Objects
```bash
# Delete specific file
supabase storage rm evidence/quote/{QUOTE_ID}/{STAGE}/{HASH}.json

# Delete entire quote folder (CAREFUL!)
supabase storage rm evidence/quote/{QUOTE_ID}/ --recursive
```

### Database Functions Usage

#### 1. Update Quote Totals
```sql
-- Recalculate quote totals from quote_items
UPDATE estimator.quotes
SET totals = public.calculate_quote_totals(id)
WHERE id = '123e4567-e89b-12d3-a456-426614174000';
```

#### 2. Check Phase Balance
```sql
-- Get phase balance for a panel
SELECT public.get_phase_balance('panel-uuid-here');

-- Result example:
{
  "phase_r": 100,
  "phase_s": 98,
  "phase_t": 102,
  "total": 300,
  "imbalance": 0.0392,
  "imbalance_percent": 3.92,
  "balanced": true,
  "calculated_at": "2025-09-30T12:00:00Z"
}
```

#### 3. Validate Evidence Integrity
```sql
-- Check if evidence SHA256 matches stored hash
SELECT public.validate_evidence_integrity(
    '123e4567-e89b-12d3-a456-426614174000',  -- quote_id
    'computed-sha256-hash-here'
);
-- Returns: true/false
```

#### 4. Validate SHA256 Format
```sql
-- Check if hash is valid SHA256 format
SELECT public.check_sha256('a1b2c3d4e5f6789...');  -- 64 hex chars
-- Returns: true/false
```

### Monitoring & Troubleshooting

#### 1. Check Database Connection
```bash
# Test connection
supabase db ping

# Check connection pool status
supabase db status
```

#### 2. Monitor Active Connections
```sql
-- View active connections
SELECT
    datname,
    usename,
    application_name,
    client_addr,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'postgres';
```

#### 3. Check Table Sizes
```sql
-- View table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('estimator', 'shared')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

#### 4. Check RLS Policies
```sql
-- List all RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE schemaname IN ('estimator', 'shared')
ORDER BY schemaname, tablename;
```

#### 5. View Recent Evidence
```sql
-- Get recent evidence uploads
SELECT
    e.id,
    e.quote_id,
    e.stage,
    e.path,
    e.sha256,
    e.created_at
FROM estimator.evidence_blobs e
ORDER BY e.created_at DESC
LIMIT 20;
```

### Backup & Recovery

#### 1. Backup Database
```bash
# Backup entire database
supabase db dump > backup_$(date +%Y%m%d).sql

# Backup specific schema
supabase db dump --schema estimator > estimator_backup.sql

# Backup with data
supabase db dump --data-only > data_backup.sql
```

#### 2. Restore Database
```bash
# Restore from backup
supabase db restore < backup.sql

# Restore specific schema
psql $SUPABASE_DB_URL < estimator_backup.sql
```

#### 3. Export Evidence Files
```bash
# Download all evidence for a quote
supabase storage download evidence/quote/{QUOTE_ID}/ --recursive --output ./evidence_backup/
```

### Performance Optimization

#### 1. Analyze Query Performance
```sql
-- Explain query plan
EXPLAIN ANALYZE
SELECT * FROM estimator.quotes
WHERE created_at > NOW() - INTERVAL '7 days';
```

#### 2. Rebuild Indexes
```sql
-- Rebuild all indexes for better performance
REINDEX TABLE estimator.quotes;
REINDEX TABLE estimator.quote_items;
REINDEX TABLE estimator.panels;
REINDEX TABLE estimator.breakers;
```

#### 3. Vacuum Tables
```sql
-- Clean up dead tuples
VACUUM ANALYZE estimator.quotes;
VACUUM ANALYZE estimator.quote_items;
```

### Security Operations

#### 1. Rotate Service Role Key
```bash
# Generate new service role key (Supabase Dashboard)
# Update environment variables
export SUPABASE_SERVICE_ROLE_KEY="new-key-here"

# Update GitHub Secrets
gh secret set SUPABASE_SERVICE_ROLE_KEY --body "new-key-here"
```

#### 2. Audit RLS Policies
```bash
# Test RLS policies
supabase test db --file tests/rls_test.sql
```

#### 3. Review Access Logs
```sql
-- View recent access patterns (if audit logging enabled)
SELECT
    actor,
    action,
    target,
    created_at
FROM shared.audit_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

### Real Connection Deployment Testing

#### 1. Local Deployment Test (Development)
```bash
# Set environment variables (use .env file)
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
export SUPABASE_DB_URL="postgresql://postgres:password@db.project.supabase.co:6543/postgres"
export APP_ENV="staging"
export APP_PORT="8000"
export SKIP_DB_PUSH="true"  # Skip DB push for dry-run

# Run deployment test script (POSIX)
bash ops/supabase/deploy_test.sh

# OR run deployment test script (Windows PowerShell)
powershell -ExecutionPolicy Bypass -File ops/supabase/deploy_test.ps1
```

**Expected Output:**
```
✅ Environment variables validated
✅ DB lint passed
✅ DB diff OK
✅ Storage initialized
✅ API server is ready
✅ /readyz check passed
✅ Supabase 실제 연결 배포 테스트 완료
```

#### 2. E2E Supabase Test (CI/CD)
```bash
# Run E2E tests with real Supabase connection
pytest tests/test_e2e_supabase.py -v

# Expected tests:
# ✅ test_db_ping: SELECT 1
# ✅ test_db_utc_timestamp: UTC timestamp query
# ✅ test_storage_upload_download_integrity: Full upload/download/SHA256 cycle
# ✅ test_evidence_blobs_table_exists: Table structure validation
# ✅ test_storage_bucket_exists: Bucket existence check
# ✅ test_db_health_check_function: health_check_detailed() function
# ✅ test_readyz_endpoint_integration: /readyz endpoint async test
```

#### 3. Deployment Workflow Steps

**Step 0: Environment Variable Check**
```bash
# Required variables for deployment testing
SUPABASE_URL="https://project.supabase.co"
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
SUPABASE_DB_URL="postgresql://postgres:password@db.project.supabase.co:6543/postgres"
APP_PORT="8000"
APP_ENV="staging"  # or "production"
```

**Step 1: DB Lint & Diff**
- Runs `supabase db lint` to check SQL quality
- Runs `supabase db diff --linked` to compare with remote
- Non-fatal warnings allowed

**Step 2: DB Push (Optional with Guard)**
- Skipped if `SKIP_DB_PUSH=true`
- Skipped if `APP_ENV=production` (manual only)
- Requires user confirmation: "Push database migrations? (yes/NO)"
- Runs `supabase db push --include-all`

**Step 3: Storage Initialization**
- Runs `ops/supabase/storage_init.sh`
- Creates "evidence" bucket if not exists (idempotent)
- Sets bucket to private with RLS enforcement
- Configures lifecycle policies

**Step 4: API Server Start**
- Kills existing process on APP_PORT
- Starts `uvicorn api.main:app` in background
- Waits up to 30 seconds for `/health` endpoint
- Captures logs to `/tmp/kis_api.log`

**Step 5: /readyz Endpoint Test**
- Calls `http://localhost:APP_PORT/readyz`
- Verifies HTTP 200 status
- Checks response format:
  ```json
  {
    "status": "ok",
    "db": "ok",
    "storage": "ok",
    "ts": "2025-09-30T12:00:00Z",
    "traceId": "uuid-here"
  }
  ```

#### 4. /readyz Endpoint Behavior

**Health Check Flow:**
1. **App Context Check**: Verifies application is ready
2. **DB Health Check** (`api/db.py:check_db_health()`):
   - Executes `SELECT 1` for connection test
   - Queries `SELECT now() AT TIME ZONE 'utc'` for timestamp
   - Returns `{"status": "ok", "connected": true, "timestamp": "2025-09-30T12:00:00Z"}`
3. **Storage Health Check** (`api/storage.py:check_storage_health()`):
   - Uploads test file to `readyz/{uuid}.txt`
   - Generates signed URL with 60s TTL
   - Deletes test file (cleanup)
   - Returns `{"status": "ok", "accessible": true, "bucket": "evidence"}`
4. **Combined Response**:
   - Returns 200 if both DB and Storage are "ok"
   - Returns 503 if either fails with detailed error

**Response Examples:**
```json
// Success
{
  "status": "ok",
  "db": "ok",
  "storage": "ok",
  "ts": "2025-09-30T12:00:00Z",
  "traceId": "123e4567-e89b-12d3-a456-426614174000"
}

// Degraded
{
  "status": "degraded",
  "db": "error",
  "storage": "ok",
  "db_error": "connection timeout",
  "ts": "2025-09-30T12:00:00Z",
  "traceId": "123e4567-e89b-12d3-a456-426614174000"
}

// Not Ready
{
  "status": "not_ready",
  "message": "Application not ready",
  "traceId": "123e4567-e89b-12d3-a456-426614174000"
}
```

### CI/CD Operations

#### 1. Pre-Deployment Checks (Automated in CI)
```bash
# These checks run automatically on every PR

# Step 1: Lint migration file
supabase db lint --file db/migrations/20250930_init.sql

# Step 2: Check diff against remote (requires linked project)
supabase db diff --linked

# Step 3: Run E2E Supabase tests (real connection)
pytest tests/test_e2e_supabase.py -v

# Step 4: Run all regression tests (20/20 MUST pass)
pytest tests/regression/test_regression_runner.py -v -m regression

# Step 5: Verify test suite passes
pytest tests/test_contracts.py tests/test_sse.py tests/test_documents.py -v
```

#### 2. Production Deployment (Main Branch Merge)
```bash
# CI/CD automatically runs on main branch merge:
# 1. supabase-check job: Lint + Diff
# 2. test job: All tests including 20/20 regression
# 3. supabase-deploy job: Push migrations + Initialize storage

# Manual deployment (if needed)
export SUPABASE_PROJECT_REF="your-project-ref"
export SUPABASE_ACCESS_TOKEN="your-access-token"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Link project
supabase link --project-ref $SUPABASE_PROJECT_REF

# Push migrations
supabase db push

# Initialize storage
export SUPABASE_URL="https://${SUPABASE_PROJECT_REF}.supabase.co"
bash ops/supabase/storage_init.sh

# Verify deployment
supabase db diff --linked  # Should show no differences
supabase storage ls evidence/  # Should show bucket exists
```

#### 3. Rollback Procedure (Emergency)
```bash
# CRITICAL: Use only in production emergencies

# Step 1: BACKUP CURRENT STATE (MANDATORY)
supabase db dump > emergency_backup_$(date +%Y%m%d_%H%M%S).sql
echo "Backup saved to: emergency_backup_$(date +%Y%m%d_%H%M%S).sql"

# Step 2: Choose rollback method

# Method A: Revert migration (if migration not yet fully applied)
supabase migration down

# Method B: Manual rollback SQL (if migration was applied)
cat > rollback_emergency.sql <<'EOF'
-- Drop tables in reverse order (respecting foreign keys)
DROP TABLE IF EXISTS estimator.evidence_blobs CASCADE;
DROP TABLE IF EXISTS estimator.documents CASCADE;
DROP TABLE IF EXISTS estimator.breakers CASCADE;
DROP TABLE IF EXISTS estimator.panels CASCADE;
DROP TABLE IF EXISTS estimator.quote_items CASCADE;
DROP TABLE IF EXISTS estimator.quotes CASCADE;
DROP TABLE IF EXISTS shared.catalog_items CASCADE;

-- Drop functions and triggers
DROP TRIGGER IF EXISTS trg_catalog_items_updated_at ON shared.catalog_items;
DROP TRIGGER IF EXISTS trg_breakers_updated_at ON estimator.breakers;
DROP TRIGGER IF EXISTS trg_panels_updated_at ON estimator.panels;
DROP TRIGGER IF EXISTS trg_quote_items_updated_at ON estimator.quote_items;
DROP TRIGGER IF EXISTS trg_quotes_updated_at ON estimator.quotes;

DROP FUNCTION IF EXISTS public.get_phase_balance(UUID);
DROP FUNCTION IF EXISTS public.calculate_quote_totals(UUID);
DROP FUNCTION IF EXISTS public.validate_evidence_integrity(UUID, TEXT);
DROP FUNCTION IF EXISTS public.check_sha256(TEXT);
DROP FUNCTION IF EXISTS public.update_updated_at();

-- Drop policies
DROP POLICY IF EXISTS catalog_service_role_all ON shared.catalog_items;
DROP POLICY IF EXISTS catalog_public_select ON shared.catalog_items;
DROP POLICY IF EXISTS evidence_authenticated_select ON estimator.evidence_blobs;
DROP POLICY IF EXISTS evidence_service_role_all ON estimator.evidence_blobs;
DROP POLICY IF EXISTS documents_authenticated_select ON estimator.documents;
DROP POLICY IF EXISTS documents_service_role_all ON estimator.documents;

-- Drop schemas
DROP SCHEMA IF EXISTS estimator CASCADE;
DROP SCHEMA IF EXISTS shared CASCADE;
EOF

psql $SUPABASE_DB_URL < rollback_emergency.sql

# Method C: Full restore from backup (last resort)
supabase db restore < backup_before_deploy.sql

# Step 3: Verify rollback
supabase db diff --linked
echo "Rollback complete. Verify database state in Supabase dashboard."

# Step 4: Notify team
echo "⚠️  EMERGENCY ROLLBACK EXECUTED"
echo "Time: $(date -u +'%Y-%m-%d %H:%M:%S UTC')"
echo "Backup: emergency_backup_*.sql"
echo "Action: [Describe what was rolled back]"
```

#### 4. GitHub Secrets Configuration
```bash
# Required secrets for CI/CD (set in GitHub repo settings)

# Supabase connection
gh secret set SUPABASE_PROJECT_REF --body "your-project-ref"
gh secret set SUPABASE_ACCESS_TOKEN --body "your-access-token"
gh secret set SUPABASE_DB_PASSWORD --body "your-db-password"
gh secret set SUPABASE_SERVICE_ROLE_KEY --body "your-service-role-key"

# Verify secrets are set
gh secret list
```

#### 5. CI/CD Workflow Stages

**On Pull Request:**
1. `quality-check`: Black, Ruff, MyPy
2. `test`: Unit, Integration, Contract, SSE, Regression (20/20)
3. `supabase-check`: Lint migration, Diff against remote
4. `regression`: Document, Evidence, SSE progress tests

**On Main Branch Merge:**
1. All PR checks (must pass)
2. `supabase-deploy`:
   - Push migrations to production
   - Initialize storage buckets
   - Verify deployment
3. Deployment summary posted to GitHub

### Common Issues & Solutions

#### Issue: "relation does not exist"
**Solution:**
```bash
# Ensure schemas are created
supabase db push --file db/schema.sql
```

#### Issue: "permission denied for schema"
**Solution:**
```sql
-- Grant necessary permissions
GRANT USAGE ON SCHEMA estimator TO authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA estimator TO authenticated;
```

#### Issue: "RLS policy violation"
**Solution:**
```bash
# Check RLS policies
supabase db lint --file db/policies.sql

# Verify using service_role key for admin operations
```

#### Issue: "Storage bucket not found"
**Solution:**
```bash
# Re-initialize storage
bash ops/supabase/storage_init.sh
```

### Useful Commands Reference

```bash
# Database
supabase db push          # Apply migrations
supabase db reset         # Reset database (DEV)
supabase db diff          # Show differences
supabase db lint          # Check SQL quality

# Storage
supabase storage ls       # List objects
supabase storage cp       # Copy/upload
supabase storage rm       # Remove
supabase storage signed-url  # Generate signed URL

# Project
supabase link            # Link to remote project
supabase status          # Check project status
supabase start           # Start local instance
supabase stop            # Stop local instance
```

---

## Emergency Contacts

- **Database Issues**: Contact DevOps team
- **Storage Issues**: Contact Infrastructure team
- **Security Incidents**: Contact Security team immediately

## Change Log

| Date       | Change                                        | Author |
|------------|-----------------------------------------------|--------|
| 2025-09-30 | Initial runbook creation                      | AI     |
| 2025-09-30 | Added Supabase migration procedures           | AI     |
| 2025-09-30 | Added CI/CD integration with GitHub Actions   | AI     |
| 2025-09-30 | Added emergency rollback procedures           | AI     |
| 2025-09-30 | Updated storage initialization instructions   | AI     |
| 2025-09-30 | Added real connection deployment testing      | AI     |
| 2025-09-30 | Added /readyz endpoint behavior documentation | AI     |
| 2025-09-30 | Added E2E Supabase test procedures            | AI     |

---

**Last Updated**: 2025-09-30
**Version**: 1.2.0

## Quick Reference Card

### Daily Operations
```bash
# Check database status
supabase db diff --linked

# View recent evidence
supabase storage ls evidence/quote/

# Monitor active connections
psql $SUPABASE_DB_URL -c "SELECT COUNT(*) FROM pg_stat_activity;"
```

### Deployment Checklist
- [ ] Run `supabase db lint --file db/migrations/20250930_init.sql`
- [ ] Verify `supabase db diff --linked` shows expected changes
- [ ] Run regression tests: `pytest -m regression` (20/20 PASS required)
- [ ] Backup database: `supabase db dump > backup.sql`
- [ ] Deploy: `supabase db push`
- [ ] Initialize storage: `bash ops/supabase/storage_init.sh`
- [ ] Verify: `supabase db diff --linked` (no differences)

### Emergency Contacts
- **Database Issues**: DevOps team
- **Storage Issues**: Infrastructure team
- **Security Incidents**: Security team (IMMEDIATE)
- **CI/CD Failures**: Build team

### Critical Reminders
⚠️ **ALWAYS backup before deployment**
⚠️ **NEVER run `supabase db reset` on production**
⚠️ **ALWAYS test rollback procedures in staging first**
⚠️ **Service role key = FULL ACCESS - protect carefully**
=======
# KIS Estimator Runbook

## 📋 목차
1. [시스템 개요](#시스템-개요)
2. [환경 설정](#환경-설정)
3. [배포 절차](#배포-절차)
4. [롤백 절차](#롤백-절차)
5. [Evidence 검토](#evidence-검토)
6. [성능 모니터링](#성능-모니터링)
7. [비용 가드](#비용-가드)
8. [트러블슈팅](#트러블슈팅)

---

## 시스템 개요

### 아키텍처
- **API**: FastAPI (Python 3.10+)
- **DB**: PostgreSQL 14 (schemas: estimator, shared)
- **Cache**: Redis 7
- **Queue**: Celery + RabbitMQ
- **Gateway**: FastMCP (MCP Tool Orchestration)

### 품질 기준
- 계약 일치율 ≥99%
- 회귀 테스트 20/20 통과
- Evidence 커버리지 100%
- API p95 < 200ms
- Health check < 50ms

---

## 환경 설정

### 필수 환경 변수
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kis_estimator
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/kis_estimator_test

# Redis
REDIS_URL=redis://localhost:6379

# MCP Gateway
MCP_GATEWAY_URL=http://localhost:9000
MCP_GATEWAY_API_KEY=your_api_key

# OR-Tools
ORTOOLS_TIMEOUT_SECONDS=30
ORTOOLS_NUM_WORKERS=4

# Application
APP_ENV=production  # development, staging, production
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here
CORS_ORIGINS=["https://app.kis-estimator.com"]

# Monitoring
OPENTELEMETRY_ENDPOINT=http://localhost:4317
SENTRY_DSN=https://your_sentry_dsn
```

### 로컬 개발 환경 설정
```bash
# 1. Python 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 데이터베이스 초기화
python scripts/init_db.py
alembic upgrade head

# 4. 시드 데이터 로드
python scripts/load_seed_data.py

# 5. 개발 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 배포 절차

### Pre-deployment Checklist
- [ ] 모든 테스트 통과 (`pytest`)
- [ ] 회귀 테스트 20/20 통과 (`pytest -m regression`)
- [ ] 보안 스캔 통과 (`bandit -r api/`)
- [ ] Evidence Pack 생성 완료
- [ ] 롤백 계획 준비

### 배포 단계

#### 1. CI/CD 파이프라인 확인
```bash
# GitHub Actions 상태 확인
gh workflow view "KIS Estimator CI/CD Pipeline"

# 최근 실행 결과
gh run list --workflow=ci.yml
```

#### 2. Evidence Pack 검증
```bash
# Evidence SHA 검증
sha256sum evidence/${COMMIT_SHA}/* > evidence.sha256
diff evidence.sha256 evidence/${COMMIT_SHA}/evidence.sha256
```

#### 3. 데이터베이스 마이그레이션
```bash
# 백업 생성
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# 마이그레이션 실행
alembic upgrade head

# 검증
python scripts/verify_migration.py
```

#### 4. 애플리케이션 배포
```bash
# Docker 이미지 빌드
docker build -t kis-estimator:${VERSION} .

# 이미지 푸시
docker push registry.kis-estimator.com/estimator:${VERSION}

# Kubernetes 배포
kubectl set image deployment/estimator estimator=registry.kis-estimator.com/estimator:${VERSION}

# 배포 상태 확인
kubectl rollout status deployment/estimator
```

#### 5. Health Check
```bash
# Health 엔드포인트 확인
curl -f https://api.kis-estimator.com/healthz

# Ready 엔드포인트 확인
curl -f https://api.kis-estimator.com/readyz

# OpenAPI 스펙 확인
curl https://api.kis-estimator.com/openapi
```

---

## 롤백 절차

### 즉시 롤백 (< 5분)
```bash
# 1. 이전 버전으로 롤백
kubectl rollout undo deployment/estimator

# 2. 롤백 상태 확인
kubectl rollout status deployment/estimator

# 3. Health check
curl -f https://api.kis-estimator.com/healthz
```

### 데이터베이스 롤백
```bash
# 1. 애플리케이션 중지
kubectl scale deployment/estimator --replicas=0

# 2. DB 롤백
alembic downgrade -1

# 3. 백업에서 복원 (필요시)
psql $DATABASE_URL < backup_${BACKUP_DATE}.sql

# 4. 애플리케이션 재시작
kubectl scale deployment/estimator --replicas=3
```

---

## Evidence 검토

### Evidence Pack 구조
```
/evidence/{trace_id}/
├── input.json          # 입력 데이터
├── output.json         # 출력 결과
├── pipeline/           # 파이프라인 단계별 결과
│   ├── enclosure.json
│   ├── breaker.json
│   ├── format.json
│   ├── cover.json
│   └── lint.json
├── metrics.json        # 성능 지표
├── validation.json     # 검증 결과
└── visual.svg          # 시각화
```

### Evidence 검증 스크립트
```python
# scripts/verify_evidence.py
import json
import hashlib

def verify_evidence(trace_id):
    with open(f"/evidence/{trace_id}/evidence.json") as f:
        data = json.load(f)

    # SHA256 검증
    json_str = json.dumps(data, sort_keys=True)
    sha = hashlib.sha256(json_str.encode()).hexdigest()

    # 품질 게이트 확인
    assert data["enclosure"]["fit_score"] >= 0.90
    assert data["breaker"]["phase_imbalance"] <= 0.03
    assert data["lint"]["errors"] == 0

    return sha
```

---

## 성능 모니터링

### 주요 메트릭

#### API 응답 시간
```sql
-- P95 응답 시간 조회
SELECT
    percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY response_time_ms) as p99
FROM api_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour';
```

#### 파이프라인 단계별 성능
| 단계 | 목표 시간 | 알림 임계값 | 최대 허용 |
|------|-----------|-------------|-----------|
| Enclosure | < 500ms | 750ms | 1s |
| Breaker | < 1s | 1.5s | 30s |
| Format | < 2s | 3s | 5s |
| Total | < 5s | 7s | 10s |

### 모니터링 대시보드
- **Grafana**: https://monitoring.kis-estimator.com/dashboard/estimator
- **OpenTelemetry**: https://otel.kis-estimator.com/traces

### 알림 설정
```yaml
alerts:
  - name: "API Response Time"
    metric: "api.response.p95"
    threshold: 200
    unit: "ms"
    action: "page"

  - name: "Regression Test Failure"
    metric: "regression.passed"
    threshold: 20
    operator: "<"
    action: "block_deployment"

  - name: "Evidence Missing"
    metric: "evidence.coverage"
    threshold: 100
    operator: "<"
    action: "alert"
```

---

## 비용 가드

### 리소스 제한
```yaml
resources:
  api:
    requests:
      cpu: "500m"
      memory: "512Mi"
    limits:
      cpu: "2000m"
      memory: "2Gi"

  database:
    max_connections: 100
    max_idle_connections: 10

  redis:
    maxmemory: "1gb"
    maxmemory-policy: "allkeys-lru"
```

### 비용 모니터링
```bash
# CPU/메모리 사용량
kubectl top pods -l app=estimator

# 데이터베이스 쿼리 비용
SELECT
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

### 자동 스케일링
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: estimator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: estimator
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 트러블슈팅

### 일반적인 문제

#### 1. Health Check 실패
```bash
# 로그 확인
kubectl logs -l app=estimator --tail=100

# 파드 상태 확인
kubectl describe pod -l app=estimator

# 재시작
kubectl rollout restart deployment/estimator
```

#### 2. 회귀 테스트 실패
```bash
# 실패한 테스트 확인
pytest tests/test_regression.py -v --tb=short

# 특정 테스트만 실행
pytest tests/test_regression.py::TestRegressionGoldSet::test_breaker_phase_balance
```

#### 3. Evidence 누락
```bash
# Evidence 경로 확인
ls -la /evidence/${TRACE_ID}/

# Evidence 재생성
python scripts/regenerate_evidence.py --trace-id ${TRACE_ID}
```

#### 4. 성능 저하
```bash
# Slow query 확인
SELECT
    query,
    mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

# 인덱스 확인
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;

# 캐시 히트율 확인
redis-cli INFO stats | grep keyspace_hits
```

### 긴급 연락처
- **On-call Engineer**: +82-10-XXXX-XXXX
- **DevOps Team**: devops@kis-estimator.com
- **Escalation**: engineering-lead@kis-estimator.com

### 관련 문서
- [Architecture Guide](./ARCHITECTURE.md)
- [API Documentation](./API.md)
- [Frontend-API Map](./Frontend-API-Map.md)
- [Testing Guide](./TESTING.md)

---

*Last Updated: 2024-12-30*
*Version: 1.0.0*
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
