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