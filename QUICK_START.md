# 🚀 KIS Estimator v2.1.0 - Quick Start Guide

**5분 배포 가이드** | **Production Deployment**

---

## ⚡ 초간단 배포 (3단계)

### 1️⃣ 환경 변수 설정

```bash
# .env.production 파일 생성
cat > .env.production <<'EOF'
export APP_ENV=production
export SUPABASE_URL="https://<prod-project-ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<prod-service-role-key>"
export DATABASE_URL="postgresql://postgres:<DB_PASSWORD>@db.<prod-project-ref>.supabase.co:5432/postgres"
export EVIDENCE_BUCKET="evidence"
export SIGNED_URL_TTL_SEC=600
EOF

# 환경 로드
source .env.production
```

### 2️⃣ 배포 실행

```bash
# 배포 시작!
./PRODUCTION_DEPLOY_FINAL.sh
```

### 3️⃣ 검증 확인

```bash
# Health check
curl https://<prod-project-ref>.supabase.co/healthz

# Readiness check
curl https://<prod-project-ref>.supabase.co/readyz

# 기대 응답:
# {
#   "status": "ok",
#   "db": "ok",
#   "storage": "ok",
#   "ts": "2025-09-30T12:00:00Z",
#   "traceId": "..."
# }
```

---

## 🔄 롤백 (긴급)

```bash
# 3분 복구
./PRODUCTION_DEPLOY_FINAL.sh --rollback
```

---

## 📊 배포 단계

스크립트가 자동으로 다음 단계를 실행합니다:

```
✅ Step 0: 환경 검증
✅ Step 1: 배포 로그 디렉토리 생성
✅ Step 2: Supabase 로그인 및 프로젝트 연결
✅ Step 3: 데이터베이스 스키마 검증 (Dry-Run)
✅ Step 4: 데이터베이스 마이그레이션 푸시
✅ Step 5: 스토리지 버킷 초기화
✅ Step 6: 카탈로그 시드 (옵션)
✅ Step 7: E2E 무결성 테스트 (권장)
✅ Step 8: 애플리케이션 배포
✅ Step 9: 배포 후 검증 (/healthz, /readyz)
✅ Step 11: 배포 요약
```

**예상 소요 시간**: 3-5분

---

## 🎯 성공 기준

배포가 성공하면 다음과 같이 표시됩니다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 11: Deployment Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

==========================================
  KIS Estimator Deployment Summary
==========================================
Timestamp: 20250930_120000
Environment: production
Mode: DEPLOY
Status: SUCCESS
Logs: out/prod_deploy/20250930_120000
==========================================

✅ 🎉 DEPLOYMENT SUCCESSFUL!

✅ Next Steps:
  1. Monitor application logs
  2. Check error rates and performance
  3. Verify E2E tests: pytest tests/test_e2e_supabase.py -v
  4. Keep rollback ready for 24 hours

📊 Monitoring:
  Health: https://<prod-project-ref>.supabase.co/healthz
  Ready: https://<prod-project-ref>.supabase.co/readyz
```

---

## ❌ 실패 시 대응

배포 실패 시:

```
❌ DEPLOYMENT COMPLETED WITH WARNINGS OR ERRORS

❌ Issues Detected:
  - Check logs in: out/prod_deploy/20250930_120000
  - Review health check failures

🔄 Rollback Available:
  bash PRODUCTION_DEPLOY_FINAL.sh --rollback
```

**즉시 롤백**:
```bash
./PRODUCTION_DEPLOY_FINAL.sh --rollback
```

---

## 📋 필수 환경 변수

| 변수 | 설명 | 예시 |
|------|------|------|
| `APP_ENV` | 환경 | `production` |
| `SUPABASE_URL` | Supabase 프로젝트 URL | `https://abc123.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service Role 키 | `eyJhbGciOiJIUzI1NiIs...` |
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql://postgres:pw@db.abc123...` |
| `EVIDENCE_BUCKET` | 증거 버킷 이름 | `evidence` |
| `SIGNED_URL_TTL_SEC` | 서명 URL TTL (초) | `600` (10분) |

**선택 변수**:
- `SUPABASE_ACCESS_TOKEN`: CLI 인증용 (CI/CD)
- `SUPABASE_ANON_KEY`: E2E 테스트용

---

## 🔍 배포 후 모니터링

### 즉시 확인 (5분 간격)

```bash
# Health check
watch -n 5 'curl -s https://your-project.supabase.co/readyz | jq .'

# 데이터베이스 연결
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM pg_stat_activity;"

# 오류 로그
tail -f out/prod_deploy/latest/app_deploy.log
```

### 24시간 관찰

- **API 응답 시간**: P95 < 200ms
- **에러율**: < 0.5%
- **데이터베이스 연결**: < 90% pool usage
- **스토리지 업로드**: 100% success rate

---

## 📞 문제 발생 시 연락처

| 상황 | 연락처 | 긴급도 |
|------|--------|--------|
| 배포 실패 | devops@company.com | 즉시 |
| Health check 실패 | tech-lead@company.com | 15분 이내 |
| 데이터베이스 오류 | dba@company.com | 30분 이내 |
| 보안 이슈 | security@company.com | 즉시 (24/7) |

---

## 📚 상세 문서

자세한 정보는 다음 문서를 참조하세요:

1. **[PRODUCTION_DEPLOY_FINAL.sh](PRODUCTION_DEPLOY_FINAL.sh)** - 실행 스크립트
2. **[PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)** - 상세 가이드
3. **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - 배포 요약
4. **[PROMOTION_READINESS_REPORT.md](docs/PROMOTION_READINESS_REPORT.md)** - 품질 보고서

---

## ✅ 체크리스트

### 배포 전

- [ ] 환경 변수 설정 완료
- [ ] Staging 환경 테스트 통과
- [ ] 팀 통보 완료
- [ ] 백업 확인 (PITR 활성화)
- [ ] 모니터링 대시보드 준비

### 배포 중

- [ ] 스크립트 실행: `./PRODUCTION_DEPLOY_FINAL.sh`
- [ ] 단계별 진행 상황 확인
- [ ] 오류 발생 시 중단 및 롤백 준비

### 배포 후

- [ ] /healthz 200 OK 확인
- [ ] /readyz 200 OK 확인
- [ ] E2E 테스트 실행: `pytest tests/test_e2e_supabase.py -v`
- [ ] 에러율 모니터링 (< 0.5%)
- [ ] 응답 시간 확인 (P95 < 200ms)

---

**🎉 준비 완료! 배포를 시작하세요!**

```bash
./PRODUCTION_DEPLOY_FINAL.sh
```

**배포 성공을 기원합니다! 🚀**