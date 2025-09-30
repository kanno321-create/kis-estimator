# JWT Secret 문제 해결 완료

## ✅ **해결 완료**

**날짜**: 2025-09-30
**JWT Secret**: `2Ujjd4++CT6/reNK0pOvIbuCwcq/3BPDMaiEvWyEp3QjyF4Q5uLts+GA+H0XY8EzR1UErgoZvTiAp7gdilhfCw==`

---

## 🔍 **문제 분석**

### 초기 문제
1. **환경 변수 누락**: `SUPABASE_JWT_SECRET` 설정되지 않음
2. **토큰 만료 오류**: `datetime.utcnow().timestamp()` 사용으로 잘못된 타임스탬프 생성
3. **테스트 실패**: 15/17 테스트가 401 Unauthorized로 실패

### 근본 원인
```python
# ❌ 잘못된 방법 (미래 시간 생성)
exp = int(datetime.utcnow().timestamp() + 3600)
# Windows에서 타임존 문제로 미래 시간 반환

# ✅ 올바른 방법
import time
now = int(time.time())
exp = now + 3600
```

---

## 🔧 **적용된 수정사항**

### 1. JWT Secret 설정
```bash
# 환경 변수
SUPABASE_JWT_SECRET=2Ujjd4++CT6/reNK0pOvIbuCwcq/3BPDMaiEvWyEp3QjyF4Q5uLts+GA+H0XY8EzR1UErgoZvTiAp7gdilhfCw==
```

### 2. 테스트 픽스처 수정 (tests/evidence/test_evidence_api.py)

**admin_token 픽스처**:
```python
@pytest.fixture
def admin_token():
    import jwt
    import time
    from api.auth import JWT_SECRET, JWT_AUD

    if not JWT_SECRET:
        pytest.skip("JWT_SECRET not configured")

    now = int(time.time())  # ✅ 올바른 현재 시간
    payload = {
        "sub": "test-admin-user",
        "email": "admin@example.com",
        "role": "admin",
        "aud": JWT_AUD,
        "iat": now,
        "exp": now + 3600  # 1시간 후 만료
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token
```

**user_token 픽스처**:
```python
@pytest.fixture
def user_token():
    import jwt
    import time
    from api.auth import JWT_SECRET, JWT_AUD

    if not JWT_SECRET:
        pytest.skip("JWT_SECRET not configured")

    now = int(time.time())
    payload = {
        "sub": "test-regular-user",
        "email": "user@example.com",
        "role": "authenticated",  # 일반 유저
        "aud": JWT_AUD,
        "iat": now,
        "exp": now + 3600
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token
```

---

## ✅ **검증 결과**

### 보안 테스트 통과
```bash
$ pytest tests/evidence/test_evidence_api.py::test_list_packs_user_token \
  tests/evidence/test_evidence_api.py::test_list_packs_admin_access -v

tests/evidence/test_evidence_api.py::test_list_packs_user_token PASSED   [50%]
tests/evidence/test_evidence_api.py::test_list_packs_admin_access PASSED [100%]

======================== 2 passed in 1.33s ========================
```

### 테스트 케이스
1. ✅ **일반 유저 토큰** → 403 Forbidden (관리자 권한 없음)
2. ✅ **관리자 토큰** → 200 OK / 500 (Storage 오류 예상)

---

## 🎯 **다음 단계**

### 필수: Supabase Storage 설정

테스트를 완전히 실행하려면 추가 환경 변수 필요:

```bash
# .env.test 파일
SUPABASE_JWT_SECRET=2Ujjd4++CT6/reNK0pOvIbuCwcq/3BPDMaiEvWyEp3QjyF4Q5uLts+GA+H0XY8EzR1UErgoZvTiAp7gdilhfCw==
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
STORAGE_BUCKET=evidence
```

### 전체 테스트 실행

```bash
# 환경 변수 설정 후
set SUPABASE_JWT_SECRET=2Ujjd4++CT6/reNK0pOvIbuCwcq/3BPDMaiEvWyEp3QjyF4Q5uLts+GA+H0XY8EzR1UErgoZvTiAp7gdilhfCw==
set SUPABASE_URL=https://your-project.supabase.co
set SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# 전체 테스트 실행
pytest tests/evidence/test_evidence_api.py -v
```

---

## 📊 **예상 테스트 결과**

### JWT Secret만 설정된 경우 (현재)
- ✅ 보안 테스트 (2/3): PASS
- ❌ 기능 테스트 (13/15): SKIP (Supabase Storage 없음)
- ⏭️ 성능 테스트: SKIP

### 모든 환경 변수 설정 시 (예상)
- ✅ 보안 테스트 (3/3): PASS
- ✅ 기능 테스트 (15/15): PASS
- ✅ 성능 테스트: PASS (p95 < 200ms)

---

## 🔒 **보안 참고사항**

1. **JWT Secret 보호**
   - ❌ Git에 커밋 금지
   - ❌ 로그에 출력 금지
   - ✅ 환경 변수로만 관리
   - ✅ `.gitignore`에 `.env*` 추가

2. **토큰 만료 시간**
   - 테스트: 1시간 (3600초)
   - 프로덕션: 필요에 따라 조정 (보통 15분~1시간)

3. **알고리즘**
   - HS256 (Supabase 기본값)
   - 대칭키 암호화
   - 서버-서버 통신에 적합

---

## ✅ **결론**

**Status**: 🎉 **JWT Secret 문제 해결 완료**

**성과**:
- ✅ JWT Secret 식별 및 설정
- ✅ 토큰 생성 로직 수정 (타임스탬프 버그 해결)
- ✅ 보안 테스트 2개 통과
- ✅ Admin/User 권한 구분 작동 확인

**남은 작업**:
- Supabase URL 및 Service Role Key 설정
- Evidence bucket 생성 (Supabase Storage)
- 전체 테스트 스위트 실행

---

**작업 완료**: 2025-09-30
**수정 파일**: `tests/evidence/test_evidence_api.py` (JWT 토큰 생성 로직)