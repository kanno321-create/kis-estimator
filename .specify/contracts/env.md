# Environment Variables Contract - Operations Mode

## Overview
KIS Estimator 운영 환경 변수 계약. **Staging/Production 완전 분리** 및 보안·성능·비용 최적화.

## Environment Separation Matrix

| Variable | Staging Secret | Production Secret | Default (Staging) | Default (Production) | Required |
|----------|----------------|-------------------|-------------------|----------------------|----------|
| `SUPABASE_URL` | `STAGING_SUPABASE_URL` | `PROD_SUPABASE_URL` | - | - | ✅ |
| `SUPABASE_ANON_KEY` | `STAGING_SUPABASE_ANON_KEY` | `PROD_SUPABASE_ANON_KEY` | - | - | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | `STAGING_SUPABASE_SERVICE_ROLE_KEY` | `PROD_SUPABASE_SERVICE_ROLE_KEY` | - | - | ✅ |
| `SUPABASE_DB_URL` | `STAGING_SUPABASE_DB_URL` | `PROD_SUPABASE_DB_URL` | - | - | ✅ |
| `APP_ENV` | - | - | `staging` | `production` | ✅ |
| `APP_PORT` | - | - | `8000` | `8000` | ✅ |
| `LOG_LEVEL` | - | - | `debug` | `info` | ✅ |
| `RATE_LIMIT_RPS` | - | - | `20` | `10` | ✅ |
| `SIGNED_URL_TTL_SEC` | - | - | `600` | `300` | ✅ |
| `DB_POOL_SIZE` | - | - | `20` | `50` | ✅ |
| `DB_POOL_TIMEOUT` | - | - | `30` | `30` | ✅ |
| `DB_MAX_OVERFLOW` | - | - | `10` | `20` | ✅ |
| `EVIDENCE_RETENTION_DAYS` | - | - | `30` | `90` | ✅ |

## Supabase Configuration Details

### `SUPABASE_URL`
- **Purpose**: Supabase 프로젝트 API 엔드포인트
- **Format**: `https://[PROJECT_REF].supabase.co`
- **Scope**: Server-side, Client-side (public safe)
- **Usage**: REST API, Storage, Auth 작업

### `SUPABASE_ANON_KEY`
- **Purpose**: 익명 공개 API 키 (프론트엔드/읽기 전용)
- **Format**: JWT token (긴 영숫자 문자열)
- **Scope**: Client-side safe (RLS 보호)
- **Security**: RLS 정책으로 데이터 보호, 직접 테이블 접근 불가

### `SUPABASE_SERVICE_ROLE_KEY`
- **Purpose**: 서비스 역할 키 (서버 사이드 관리 작업)
- **Format**: JWT token (긴 영숫자 문자열)
- **Scope**: **Server-side ONLY**, 절대 클라이언트 노출 금지
- **Usage**: RLS 우회, 관리 작업, 마이그레이션, 서버 사이드 쓰기
- **Security**: 전체 DB 접근 권한, 반드시 비밀 유지

### `SUPABASE_DB_URL`
- **Purpose**: PostgreSQL 직접 연결 (Connection Pooler)
- **Format**: `postgresql://postgres:[PASSWORD]@[HOST]:6543/postgres?sslmode=require`
- **Scope**: **Server-side ONLY**, 절대 노출 금지
- **Usage**: DB 쿼리, 마이그레이션, 관리 작업
- **Pooler**: Port 6543 (Transaction Mode, Serverless 권장)

## Application Configuration

### `APP_ENV`
- **Values**: `staging` | `production`
- **Usage**: 환경별 동작 분기, 로깅 레벨, 디버그 모드

### `LOG_LEVEL`
- **Values**: `debug` | `info` | `warn` | `error`
- **Staging**: `debug` (상세 로깅)
- **Production**: `info` (최소 로깅)

### `RATE_LIMIT_RPS`
- **Purpose**: API Rate Limit (requests per second)
- **Staging**: `20` (테스트용 여유)
- **Production**: `10` (엄격한 제한)
- **Implementation**: Token bucket algorithm

### `SIGNED_URL_TTL_SEC`
- **Purpose**: Storage 서명 URL Time-To-Live (초)
- **Staging**: `600` (10분, 테스트 편의)
- **Production**: `300` (5분, 보안 강화)
- **Usage**: Evidence blob 다운로드 임시 URL

### Database Connection Pool
- **`DB_POOL_SIZE`**: 커넥션 풀 크기
  - Staging: `20` (소규모 트래픽)
  - Production: `50` (고가용성)
- **`DB_POOL_TIMEOUT`**: 커넥션 대기 타임아웃 (초)
- **`DB_POOL_MAX_OVERFLOW`**: 풀 초과 시 추가 커넥션

### Evidence Management
- **`EVIDENCE_RETENTION_DAYS`**: Evidence blob 보관 기간
  - Staging: `30일` (빠른 정리)
  - Production: `90일` (법적 요구사항)

## GitHub Secrets Configuration

### Staging Environment
```
STAGING_SUPABASE_URL
STAGING_SUPABASE_ANON_KEY
STAGING_SUPABASE_SERVICE_ROLE_KEY
STAGING_SUPABASE_DB_URL
```

### Production Environment
```
PROD_SUPABASE_URL
PROD_SUPABASE_ANON_KEY
PROD_SUPABASE_SERVICE_ROLE_KEY
PROD_SUPABASE_DB_URL
```

### CI/CD Workflow Mapping
```yaml
# Staging deployment (main branch)
env:
  SUPABASE_URL: ${{ secrets.STAGING_SUPABASE_URL }}
  SUPABASE_ANON_KEY: ${{ secrets.STAGING_SUPABASE_ANON_KEY }}
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.STAGING_SUPABASE_SERVICE_ROLE_KEY }}
  SUPABASE_DB_URL: ${{ secrets.STAGING_SUPABASE_DB_URL }}
  APP_ENV: staging

# Production deployment (tags v*)
env:
  SUPABASE_URL: ${{ secrets.PROD_SUPABASE_URL }}
  SUPABASE_ANON_KEY: ${{ secrets.PROD_SUPABASE_ANON_KEY }}
  SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.PROD_SUPABASE_SERVICE_ROLE_KEY }}
  SUPABASE_DB_URL: ${{ secrets.PROD_SUPABASE_DB_URL }}
  APP_ENV: production
```

## Security Requirements

### Mandatory Rules
1. ✅ **No Secrets in Code**: 모든 민감 정보는 환경 변수/GitHub Secrets로만
2. ✅ **RLS Enforcement**: Service Role Key는 서버 사이드에서만 사용
3. ✅ **SSL Required**: DB URL은 `sslmode=require` 필수
4. ✅ **Signed URLs Only**: Storage 접근은 서명 URL (TTL 적용)
5. ✅ **No Logging Secrets**: 로그에 키/토큰/URL 노출 절대 금지

### Client-Side vs Server-Side
**Client-Side Safe** ✅:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY` (RLS 보호)

**Server-Side ONLY** ❌:
- `SUPABASE_DB_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Validation

All variables must be set before application start:
```python
import os
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "SUPABASE_DB_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
]

for var in required_vars:
    if not os.getenv(var):
        raise EnvironmentError(f"Missing required environment variable: {var}")
```

## Usage Patterns

### Database Operations (Pooled Connection)
```python
from supabase import create_client

db_url = os.getenv("SUPABASE_DB_URL")
# Use for direct SQL queries with connection pooling
```

### API Operations (Client)
```python
from supabase import create_client

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")  # For client-side
)
```

### Admin Operations (Service Role)
```python
from supabase import create_client

supabase_admin = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Bypass RLS
)
```

## Connection Pooling

Use pooler URL for better performance:
- **Transaction Mode**: Port 6543 (recommended for serverless)
- **Session Mode**: Port 5432 (for persistent connections)

## References
- [Supabase Environment Variables](https://supabase.com/docs/guides/getting-started/environment-variables)
- [Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)