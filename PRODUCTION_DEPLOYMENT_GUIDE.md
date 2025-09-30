# 🚀 KIS Estimator - Production Deployment Guide (v2.1.0)

**Release Date**: 2025-09-30
**Status**: ✅ **READY FOR PRODUCTION PROMOTION**
**Deployment Mode**: Click-by-Click → One-Step Automation

---

## 📋 Pre-Deployment Checklist

### ✅ Verification Status

| Item | Status | Details |
|------|--------|---------|
| **OpenAPI Contract** | ✅ PASS | 8/8 tests |
| **Regression Tests** | ✅ PASS | 22/22 goldset |
| **Document Rendering** | ✅ PASS | formula_loss=0, lint_errors=0 |
| **SSE Validation** | ✅ PASS | heartbeat, meta.seq OK |
| **Supabase E2E** | ✅ PASS | 7/7 tests |
| **Evidence Pack** | ✅ READY | v2.1.0 + SHA256SUMS |
| **Deployment Scripts** | ✅ READY | DEPLOYMENT_SCRIPT.sh |
| **Rollback Plan** | ✅ DOCUMENTED | 3-minute recovery |

---

## 🎯 Step 0: Release Cut & Evidence Freeze

### Evidence Pack Location

```
out/evidence/v2.1.0/
├── PROMOTION_READINESS_REPORT.md  (14KB)
├── openapi.yaml
├── regression_seeds_v1.jsonl
├── ci.yml
├── deploy_production.sh
├── deploy_test.sh
├── storage_init.sh
└── SHA256SUMS  (checksums for all files)
```

### SHA256 Checksums (Verified)

```
d81645296bb05a0b458c05c57e4193d34ecb948d5f1f17328054b6076c50ad01  PROMOTION_READINESS_REPORT.md
4d2d53604d0e31cafbe3ff521e21e898e67ed77a3f0a95c90d0416d76368dc0f  ci.yml
8086a823f8e234f74456aa2adc37adc8c66a20fdc80b6933ce124be17c334fee  deploy_production.sh
740a141361a8203c674d5050cca63cad0b329fbb3cc2d78842b71397f21fbd7c  deploy_test.sh
f5f681685de1be58d4b004e0b5d24d6dd64dc31403516c2d1b7b0dfccde72685  openapi.yaml
5a893c0eade01cc50c28f1c50eba152bb820297baa7117b9ff7b07b7d2a0279d  regression_seeds_v1.jsonl
5e18239671d8de5dc2a74c13cc3f2906ec65633677b83effe08d600b51bcceca  storage_init.sh
```

### Git Tag (To be created)

```bash
git tag -a v2.1.0-estimator -m "Release v2.1.0: Production-ready with Supabase E2E validation"
git push origin v2.1.0-estimator
```

---

## 🚀 Step 1: ONE-STEP DEPLOYMENT (Recommended)

### Environment Variables Setup

**Create `.env.production` file:**

```bash
# Application Configuration
export APP_ENV="production"
export APP_PORT="8000"
export APP_DEBUG="false"

# Supabase Configuration
export SUPABASE_URL="https://your-prod-project.supabase.co"
export SUPABASE_ANON_KEY="your-production-anon-key"
export SUPABASE_SERVICE_ROLE_KEY="your-production-service-role-key"
export SUPABASE_DB_URL="postgresql://postgres:password@db.your-prod-project.supabase.co:6543/postgres"

# Supabase CLI (for deployment)
export SUPABASE_PROJECT_REF="your-prod-project-ref"
export SUPABASE_ACCESS_TOKEN="your-supabase-access-token"

# Storage Configuration
export STORAGE_BUCKET="evidence"
export SIGNED_URL_TTL_SEC="300"  # 5 minutes for production

# Database Configuration
export DB_POOL_SIZE="20"
export DB_MAX_OVERFLOW="10"
export DB_POOL_TIMEOUT="30"
```

### Execute Deployment

```bash
# Step 1: Load environment variables
source .env.production

# Step 2: Verify environment (security check)
./DEPLOYMENT_SCRIPT.sh --check-env  # Optional: will be added if needed

# Step 3: Execute deployment
./DEPLOYMENT_SCRIPT.sh
```

**Expected Output:**

```
ℹ Step 0: Pre-flight Checks
✅ Environment variables validated

ℹ Step 1: Creating deployment logs directory
✅ Deployment directory created: out/prod_deploy/20250930_040000

ℹ Step 2: Supabase Login and Project Link
✅ Project linked successfully

ℹ Step 3: Database Schema Validation (Dry-Run)
✅ Database validation completed

ℹ Step 4: Pushing Database Migrations
⚠️  PRODUCTION DATABASE MIGRATION ⚠️
Are you sure you want to push migrations to PRODUCTION? (yes/NO): yes
✅ Database migrations pushed successfully

ℹ Step 5: Initializing Storage Buckets
✅ Storage buckets initialized

ℹ Step 6: Deploying Application
✅ Application deployed successfully

ℹ Step 7: Post-Deployment Validation
✅ /healthz check passed (200 OK)
✅ /readyz check passed (200 OK)
✅ Status: ok
✅ DB: ok
✅ Storage: ok
✅ TraceId: present

ℹ Step 9: Deployment Summary
==========================================
  KIS Estimator Deployment Summary
==========================================
Timestamp: 20250930_040000
Environment: production
Mode: DEPLOY
Logs: out/prod_deploy/20250930_040000
==========================================

✅ 🎉 DEPLOYMENT SUCCESSFUL!

Next steps:
  1. Monitor application logs
  2. Check error rates and performance
  3. Verify E2E tests: pytest tests/test_e2e_supabase.py -v
  4. Keep rollback ready for 24 hours
```

---

## 🔧 Step 2: MANUAL DEPLOYMENT (Click-by-Click)

If you prefer manual control over each step:

### 2.1 Environment Preparation

```bash
# Set production environment
export APP_ENV="production"
export SUPABASE_URL="https://your-prod-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-production-service-role-key"
export SIGNED_URL_TTL_SEC="300"

# Security check (output suppression recommended)
test -n "$SUPABASE_SERVICE_ROLE_KEY" || { echo "❌ SERVICE ROLE KEY empty"; exit 1; }
```

### 2.2 Database/Storage Promotion

```bash
# Login to Supabase
supabase login

# Link to production project
supabase link --project-ref <your-prod-project-ref>

# Pre-deployment checks (dry-run logs)
mkdir -p out/prod_deploy
date +"%F_%T" > out/prod_deploy/TIMESTAMP.txt

supabase db lint | tee out/prod_deploy/db_lint.log
supabase db diff  | tee out/prod_deploy/db_diff.log

# Apply migrations
supabase db push  | tee out/prod_deploy/db_push.log

# Initialize storage bucket (idempotent)
bash ops/supabase/storage_init.sh | tee out/prod_deploy/storage_init.log
```

### 2.3 Application Deployment

```bash
# Deploy application
bash ops/supabase/deploy_production.sh | tee out/prod_deploy/app_deploy.log
```

### 2.4 Post-Deployment Validation

```bash
# Wait for application to be ready
sleep 30

# Health check
curl -s https://api.kis-estimator.com/healthz | jq .

# Readiness check
curl -s https://api.kis-estimator.com/readyz | jq .

# Expected response:
# {
#   "status": "ok",
#   "db": "ok",
#   "storage": "ok",
#   "ts": "2025-09-30T12:00:00Z",
#   "traceId": "123e4567-e89b-12d3-a456-426614174000"
# }
```

---

## ✅ Step 3: Definition of Done (DoD) Validation

### Post-Deployment Checklist

| Criterion | Threshold | Verification Command | Status |
|-----------|-----------|---------------------|--------|
| **/readyz Endpoint** | 200 OK | `curl https://api.kis-estimator.com/readyz` | [ ] |
| **DB Health** | "ok" | Check `"db":"ok"` in readyz response | [ ] |
| **Storage Health** | "ok" | Check `"storage":"ok"` in readyz response | [ ] |
| **TraceId** | Present | Check `"traceId"` field exists | [ ] |
| **API Response Time** | P95 < 200ms | Monitor for 1 hour | [ ] |
| **Error Rate** | < 0.5% | Monitor for 24 hours | [ ] |
| **Evidence Upload** | SHA256 match | Upload test file and verify | [ ] |
| **OpenAPI Checksum** | Match release | `sha256sum openapi.yaml` | [ ] |

### Verification Commands

```bash
# 1. Basic health check
curl -s https://api.kis-estimator.com/readyz | jq '.'

# 2. Run E2E tests against production
export SUPABASE_URL="https://prod-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="prod-service-role-key"
pytest tests/test_e2e_supabase.py -v

# 3. Evidence upload test
python scripts/test_evidence_upload.py --env production

# 4. OpenAPI contract verification
sha256sum openapi.yaml
# Compare with: f5f681685de1be58d4b004e0b5d24d6dd64dc31403516c2d1b7b0dfccde72685
```

---

## 🔄 ROLLBACK PROCEDURE (3-Minute Recovery)

### When to Rollback

**NO-GO Triggers**:
- /readyz returns non-200 status
- Error rate > 0.5% within first hour
- P95 response time > 500ms
- Critical functionality broken
- Database corruption detected

### Rollback Execution (ONE COMMAND)

```bash
# Execute rollback
./DEPLOYMENT_SCRIPT.sh --rollback

# OR manually:
bash ops/rollback/production_rollback.sh --to-tag v2.0.x | tee out/prod_deploy/rollback.log
```

### Rollback Steps (Manual)

#### A) Application Rollback

```bash
# Revert to previous version
bash ops/rollback/production_rollback.sh --to-tag v2.0.x | tee out/prod_deploy/rollback_app.log
```

#### B) Database Rollback (PITR/Snapshot)

```bash
# Restore from snapshot (Supabase Console or CLI)
# Note: Use pre-deployment snapshot ID
bash ops/rollback/db_restore_to_snapshot.sh <SNAPSHOT_ID> | tee out/prod_deploy/rollback_db.log
```

#### C) Post-Rollback Validation

```bash
# Verify application is working
curl -s https://api.kis-estimator.com/readyz

# Run E2E tests
pytest -q tests/test_e2e_supabase.py

# Check logs
tail -f out/prod_deploy/rollback.log
```

---

## 📊 Monitoring & Observability

### Key Metrics to Monitor

**First Hour (Critical Period)**:
- API response times (P50, P95, P99)
- Error rates by endpoint
- Database connection pool usage
- Storage upload/download success rates

**First 24 Hours (Observation Period)**:
- User-facing errors
- Background job failures
- Evidence integrity checks
- Memory/CPU usage trends

### Monitoring Commands

```bash
# Real-time logs (if using systemd/docker)
journalctl -u kis-estimator -f

# Database connections
psql $SUPABASE_DB_URL -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Storage usage
supabase storage ls evidence/ | wc -l

# Recent errors (if using structured logging)
tail -n 100 /var/log/kis-estimator/error.log
```

---

## 📞 Emergency Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| **Technical Lead** | tech-lead@company.com | 24/7 |
| **DevOps Team** | devops@company.com | 24/7 |
| **Security Team** | security@company.com | 24/7 (IMMEDIATE) |
| **Database Admin** | dba@company.com | Business hours + On-call |

---

## 📝 Post-Deployment Tasks

### Immediate (Within 1 Hour)

- [ ] Verify all /readyz checks passing
- [ ] Monitor error rates and response times
- [ ] Check database connection pool status
- [ ] Validate storage bucket accessibility
- [ ] Run smoke tests on critical workflows

### Within 24 Hours

- [ ] Generate deployment report
- [ ] Update runbook with any lessons learned
- [ ] Archive deployment logs
- [ ] Remove rollback readiness (if stable)
- [ ] Notify stakeholders of successful deployment

### Within 1 Week

- [ ] Conduct post-mortem (if issues occurred)
- [ ] Update documentation with production findings
- [ ] Review performance metrics trends
- [ ] Plan next release improvements

---

## 🎉 Success Criteria

**Deployment is considered SUCCESSFUL if:**

1. ✅ All health checks passing (200 OK)
2. ✅ Error rate < 0.5% for 24 hours
3. ✅ P95 response time < 200ms
4. ✅ No critical incidents
5. ✅ All E2E tests passing
6. ✅ Evidence upload/download working
7. ✅ No customer-reported issues

---

## 📚 Additional Resources

- **Promotion Readiness Report**: [docs/PROMOTION_READINESS_REPORT.md](docs/PROMOTION_READINESS_REPORT.md)
- **Operations Runbook**: [docs/Runbook.md](docs/Runbook.md)
- **Architecture Documentation**: [ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)
- **Evidence Pack**: [out/evidence/v2.1.0/](out/evidence/v2.1.0/)

---

**Generated**: 2025-09-30
**Version**: 2.1.0
**Status**: ✅ READY FOR PRODUCTION

---

**🚀 Good luck with the deployment! 배포 성공을 기원합니다!**