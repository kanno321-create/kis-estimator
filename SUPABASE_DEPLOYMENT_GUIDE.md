# Supabase 배포 가이드

## 📋 배포 정보

- **프로젝트**: kis-estimator
- **프로젝트 ID**: cgqukhmqnndwdbmkmjrn
- **URL**: https://cgqukhmqnndwdbmkmjrn.supabase.co
- **리전**: ap-northeast-2 (Seoul)
- **배포 시각**: 2025-09-30

## 🚀 배포 방법 (수동 SQL 실행)

### 1단계: Supabase 대시보드 접속
1. https://supabase.com/dashboard 접속
2. kis-estimator 프로젝트 선택

### 2단계: SQL Editor 열기
1. 왼쪽 메뉴에서 **SQL Editor** 클릭
2. **New Query** 버튼 클릭

### 3단계: SQL 스크립트 실행
1. `/workspace/supabase_deployment_complete.sql` 파일 열기 (462줄)
2. 파일 전체 내용을 복사 (Ctrl+A, Ctrl+C)
3. SQL Editor에 붙여넣기 (Ctrl+V)
4. **RUN** 버튼 클릭 (또는 Ctrl+Enter)

### 4단계: 결과 확인
실행 결과 하단에 다음 메시지가 표시되어야 합니다:
```
✅ Deployment Complete
Tables created: 7
Functions created: 5
```

## 📊 배포 내용

### 데이터베이스 스키마
- **Schemas**: `estimator`, `shared`
- **Tables**: 7개
  - `estimator.quotes` - 견적 메인 테이블
  - `estimator.quote_items` - 견적 항목
  - `estimator.panels` - 패널/외함
  - `estimator.breakers` - 브레이커
  - `estimator.documents` - 생성 문서
  - `estimator.evidence_blobs` - 증거 데이터
  - `shared.catalog_items` - 자재 카탈로그

### 함수 (Functions)
- `update_updated_at()` - 자동 타임스탬프 업데이트
- `check_sha256()` - SHA256 해시 검증
- `validate_evidence_integrity()` - 증거 무결성 검증
- `calculate_quote_totals()` - 견적 합계 계산
- `get_phase_balance()` - 3상 전력 균형 계산

### 보안 (RLS Policies)
- 모든 테이블에 Row Level Security 활성화
- Service Role: 전체 권한
- Authenticated: 읽기 전용

## 🔐 Storage Bucket 생성

SQL 실행 후, Storage 버킷을 생성해야 합니다:

### 1단계: Storage 메뉴 접속
1. 왼쪽 메뉴에서 **Storage** 클릭
2. **Create a new bucket** 버튼 클릭

### 2단계: Bucket 설정
- **Name**: `evidence`
- **Public**: **OFF** (Private)
- **Create bucket** 클릭

### 3단계: Bucket Policies 설정
1. `evidence` 버킷 클릭
2. **Policies** 탭 클릭
3. 다음 정책 추가:

#### Service Role: 전체 권한
```sql
CREATE POLICY "evidence_service_role_all"
ON storage.objects
FOR ALL
TO service_role
USING (bucket_id = 'evidence')
WITH CHECK (bucket_id = 'evidence');
```

#### Authenticated: 읽기 전용 (Signed URL 통해서만)
```sql
CREATE POLICY "evidence_authenticated_select"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'evidence');
```

## ✅ 배포 검증

### 데이터베이스 검증
SQL Editor에서 다음 쿼리 실행:

```sql
-- 1. 스키마 확인
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('estimator', 'shared');
-- 결과: estimator, shared (2개)

-- 2. 테이블 확인
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('estimator', 'shared')
ORDER BY table_schema, table_name;
-- 결과: 7개 테이블

-- 3. 함수 확인
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
AND routine_name LIKE '%quote%' OR routine_name LIKE '%sha%';
-- 결과: 5개 함수

-- 4. RLS 확인
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'estimator';
-- 결과: 모든 테이블 rowsecurity=true
```

### Storage 검증
1. Storage 메뉴에서 `evidence` 버킷 존재 확인
2. 버킷 클릭 → Policies 탭에서 2개 정책 확인

## 🔧 API 연결 테스트

### Python 연결 테스트
```python
from supabase import create_client

url = "https://cgqukhmqnndwdbmkmjrn.supabase.co"
service_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNncXVraG1xbm5kd2RibWttanJuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTIwNTkyMSwiZXhwIjoyMDc0NzgxOTIxfQ.-olqMJ5sx_LofEGqlePOMK0MnFJT-LLg3_ll0IR3yj4"

supabase = create_client(url, service_key)

# 테스트 쿼리
result = supabase.table("quotes").select("*").limit(1).execute()
print("✅ Connection successful")
```

### Health Check 엔드포인트
```bash
curl https://cgqukhmqnndwdbmkmjrn.supabase.co/rest/v1/
```

## 📝 환경 변수 설정

API 서버에서 다음 환경 변수를 사용하세요:

```bash
# Supabase Configuration
export SUPABASE_URL="https://cgqukhmqnndwdbmkmjrn.supabase.co"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNncXVraG1xbm5kd2RibWttanJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkyMDU5MjEsImV4cCI6MjA3NDc4MTkyMX0.H9KNzfszjnS3owidNYbf5HFExu_SMCjnm2pyP0hIezk"
export SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNncXVraG1xbm5kd2RibWttanJuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTIwNTkyMSwiZXhwIjoyMDc0NzgxOTIxfQ.-olqMJ5sx_LofEGqlePOMK0MnFJT-LLg3_ll0IR3yj4"
export SUPABASE_PROJECT_REF="cgqukhmqnndwdbmkmjrn"

# Database Configuration (PostgreSQL Pooler)
export DATABASE_URL="postgresql://postgres.cgqukhmqnndwdbmkmjrn:%40dnjsdl2572@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"

# Storage Configuration
export STORAGE_BUCKET="evidence"
export SIGNED_URL_TTL_SEC="300"
```

## 🆘 문제 해결

### SQL 실행 오류
- **"syntax error"**: SQL 파일 전체가 복사되었는지 확인
- **"already exists"**: 이미 배포됨 - 무시해도 안전
- **"permission denied"**: Service Role 권한 확인

### Connection 오류
- **"Tenant or user not found"**: 비밀번호 URL 인코딩 확인 (`@` → `%40`)
- **"could not translate host name"**: 프로젝트 ID 확인

### Storage 오류
- **"Bucket not found"**: Storage 메뉴에서 `evidence` 버킷 생성
- **"Policy violation"**: Bucket policies 설정 확인

## 📚 다음 단계

배포 완료 후:
1. ✅ API 서버 시작: `uvicorn api.main:app --reload`
2. ✅ Health check: `curl http://localhost:8000/healthz`
3. ✅ Readiness check: `curl http://localhost:8000/readyz`
4. ✅ API 테스트: Postman/Thunder Client로 엔드포인트 테스트

---

**배포 완료!** 🎉

문제가 발생하면 로그를 확인하고, 위 문제 해결 섹션을 참고하세요.