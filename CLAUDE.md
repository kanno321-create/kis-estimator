# CLAUDE.md - KIS Estimator 백엔드 개발 가이드

이 파일은 Claude Code (claude.ai/code)가 KIS Estimator 시스템을 개발할 때 필요한 모든 정보를 제공합니다.

## 🚫 절대 규칙: 목업(MOCKUP) 금지

### 핵심 규칙
**목업 테스트는 절대 금지다. 실제 테스트가 안 되면 안 되는 이유를 명확히 설명하라.**
- 가짜 데이터 생성 금지
- 시뮬레이션 금지
- 실제 서버 없이 테스트 결과 조작 금지
- 목업 때문에 폐기된 프로젝트가 여러 개 있음

### 실제 테스트 불가 시 대응
1. "실제 테스트 불가: [구체적 이유]" 명시
2. 필요한 환경변수/설정 안내
3. 해결 방법 제시
4. 절대 목업으로 대체하지 않음

## 🎯 프로젝트 개요 및 운영 모드

### 시스템 정의
- **프로젝트명**: NABERAL KIS Estimator (전기 패널 견적 AI 시스템)
- **운영 모드**: Contract-First + Evidence-Gated + SPEC KIT 기반
- **목표**: Estimator 전용 AI 시스템 구축 (ERP는 별도 AI가 담당)
- **품질 기준**:
  - 계약 일치율 ≥99%
  - 회귀 테스트 20/20 통과
  - Evidence 커버리지 100%
  - API 응답 p95 < 200ms
  - Health 체크 < 50ms

### 범위 (Scope)
**포함**:
- `/v1/estimate`: 견적 생성 API
- `/v1/validate`: 검증 API
- `/v1/documents`: 문서 생성 API
- `/v1/catalog`: 자재 카탈로그 API
- FIX-4 파이프라인 전체
- 증거팩 생성 (PDF/XLSX/SVG/JSON)

**제외**:
- ERP 관련 기능 (발주/재고/회계/인사)
- ERP는 별도 AI 시스템이 담당

## 📋 개발 명령어

### 테스트
```bash
# 모든 테스트 실행
pytest

# 커버리지 포함 실행
pytest --cov=src --cov-report=html

# 특정 카테고리별 실행
pytest -m unit          # 유닛 테스트
pytest -m integration   # 통합 테스트
pytest -m regression    # 회귀 테스트 (20/20 필수 통과)

# 단일 테스트 파일
pytest tests/unit/test_breaker_placer.py

# 단일 테스트 함수
pytest tests/unit/test_breaker_placer.py::test_phase_balance
```

### 코드 품질
```bash
# 코드 포맷팅
black src/ tests/

# 린팅
ruff check src/ tests/
ruff check --fix src/ tests/  # 자동 수정

# 타입 체크
mypy src/

# 모든 품질 체크 실행
npm run quality
```

### 데이터베이스 작업
```bash
# 데이터베이스 초기화
python scripts/init_db.py

# 마이그레이션 실행
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

### 개발 서버
```bash
# 개발 서버 실행 (자동 리로드)
uvicorn src.kis_estimator_core.api.main:app --reload --host 0.0.0.0 --port 8000

# 또는 npm 스크립트 사용
npm run dev
```

## 🏗️ 아키텍처 및 FIX-4 파이프라인

### FIX-4 파이프라인 (필수 구현)
시스템은 반드시 다음 5단계를 순서대로 거쳐야 합니다:

#### Stage 1: Enclosure (외함 계산)
- **모듈**: `engine/enclosure_solver.py`
- **목적**: 최적 외함 크기 결정
- **품질 게이트**:
  - fit_score ≥ 0.90
  - IP 등급 ≥ 44
  - 도어 여유 ≥ 30mm

#### Stage 2: Breaker (브레이커 배치)
- **모듈**: `engine/breaker_placer.py`
- **도구**: OR-Tools CP-SAT 솔버 (폴백: 휴리스틱)
- **품질 게이트**:
  - 상평형 ≤ 4%
  - 간섭 위반 = 0
  - 열 위반 = 0

#### Stage 2.1: Critic (배치 검증)
- **모듈**: `engine/breaker_critic.py`
- **목적**: 배치 결과 검증 및 개선 제안
- **출력**: 위반 사항, 경고, 개선 권고

#### Stage 3: Format (문서 포맷)
- **모듈**: `engine/estimate_formatter.py`
- **목적**: Excel/PDF 문서 생성
- **품질 게이트**:
  - 수식 보존 = 100%
  - 네임드 범위 손상 = 0

#### Stage 4: Cover (표지 생성)
- **모듈**: `engine/doc_generator.py`
- **목적**: 표지 및 메타데이터 생성
- **품질 게이트**: 표지 규칙 준수 = 100%

#### Stage 5: Doc Lint (최종 검증)
- **모듈**: `engine/doc_lint_guard.py`
- **목적**: 문서 품질 최종 검증
- **품질 게이트**: 린트 오류 = 0

### 기술 스택
```yaml
API: FastAPI (Python) + OpenAPI 3.1
DB: PostgreSQL (schemas: estimator, shared)
Cache: Redis (idempotency, dedup, rate-limit)
Queue: Celery + RabbitMQ
Gateway: FastMCP (MCP 도구 오케스트레이션)
Observability: OpenTelemetry + TraceId
Delivery: Docker + GitHub Actions CI
```

## 📖 바이브코딩 규칙 (Vibe Coding Rules)

### 3가지 파일 규칙 시스템

#### 1️⃣ PRD 생성 규칙
- 주니어도 이해 가능한 쉬운 언어 사용
- 질문 우선 방식으로 정보 수집
- 체크포인트별로 사용자 확인

#### 2️⃣ Task 생성 규칙
```markdown
- [ ] Task 1: 데이터베이스 스키마 설계
- [ ] Task 2: API 엔드포인트 구현
- [ ] Task 3: 입력 검증 로직 추가
```
- 1시간 이내 완료 가능한 단위로 분할
- 마크다운 체크박스 필수
- 독립적으로 테스트 가능

#### 3️⃣ Task 실행 규칙
- **단일 Task 원칙**: 한 번에 하나의 Task만 실행
- **승인 체크포인트**: Task 완료 → 정지 → 사용자 검토 대기
- **진행 상황 추적**:
```markdown
## 진행 상황
- [x] Task 1: 완료 ✅
- [x] Task 2: 완료 ✅
- [ ] Task 3: 진행 중 🔄
- [ ] Task 4: 대기 ⏳
```

## 🛠️ MCP 도구 목록 (필수 등록)

### 핵심 비즈니스 로직 도구
1. `enclosure.solve` / `validate` → fit_score ≥ 0.90
2. `layout.place_breakers` / `check_clearance` / `balance_phases` → 간섭=0, 상평형 ≤3%
3. `estimate.format` / `export(pdf|xlsx)` → 수식 보존=100%
4. `doc.cover_generate` / `doc.apply_branding` → 규범 위반=0
5. `doc.lint` / `doc.policy_check` → lint_errors=0

### 데이터 관리 도구
6. `rag.ingest` / `normalize` / `index` / `verify` → citation coverage=100%
7. `db.modeler` → TIMESTAMPTZ DDL 생성
8. `cache.invalidate` / `cache.warm` → 캐시 관리

### 테스트 및 검증 도구
9. `testgen.make` / `fuzz.contract` → 유닛/통합/퍼징 테스트
10. `regression.run` → 골드셋 20/20 PASS 필수
11. `contract.lint` → OpenAPI 규약 검증

### 보안 및 운영 도구
12. `sec.secrets_guard` → 키/토큰 유출 0
13. `ops.rollbacks` → 원클릭 롤백
14. `monitor.health` / `monitor.metrics` → 모니터링

## ✅ 품질 게이트 및 Evidence 시스템

### Evidence 수집 경로
```
/spec_kit/evidence/{timestamp}/
├── input.json       # 입력 데이터
├── output.json      # 출력 결과
├── metrics.json     # 성능 지표
├── validation.json  # 검증 결과
└── visual.svg       # 시각화
```

### 필수 품질 게이트
| 단계 | 지표 | 기준 | 검증 방법 |
|------|------|------|----------|
| Enclosure | fit_score | ≥ 0.90 | `enclosure.validate()` |
| Breaker | 상평형 | ≤ 4% | `layout.balance_phases()` |
| Breaker | 간섭 | = 0 | `layout.check_clearance()` |
| Format | 수식 보존 | = 100% | `estimate.verify_formulas()` |
| Doc Lint | 오류 | = 0 | `doc.lint()` |
| Regression | 골드셋 | 20/20 PASS | `regression.run()` |

### CI/CD 게이트
```yaml
merge_requirements:
  - unit_tests: PASS
  - integration_tests: PASS
  - regression_tests: 20/20 PASS
  - contract_validation: 100%
  - evidence_pack: COMPLETE
  - code_coverage: ≥ 80%
```

## 💾 데이터베이스 스키마

### 필수 테이블 (PostgreSQL)
```sql
-- 모든 timestamp는 반드시 TIMESTAMPTZ with UTC
CREATE TABLE quotes (
    id UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(id),
    status VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now() AT TIME ZONE 'utc',
    updated_at TIMESTAMPTZ DEFAULT now() AT TIME ZONE 'utc'
);

CREATE TABLE quote_items (
    id UUID PRIMARY KEY,
    quote_id UUID REFERENCES quotes(id),
    breaker_sku VARCHAR(100),
    quantity INTEGER,
    phase_assignment CHAR(1)
);

CREATE TABLE panels (
    id UUID PRIMARY KEY,
    quote_id UUID REFERENCES quotes(id),
    enclosure_sku VARCHAR(100),
    fit_score DECIMAL(3,2)
);

CREATE TABLE evidence_blobs (
    id UUID PRIMARY KEY,
    quote_id UUID REFERENCES quotes(id),
    stage VARCHAR(50),
    hash SHA256,
    data JSONB,
    created_at TIMESTAMPTZ DEFAULT now() AT TIME ZONE 'utc'
);
```

## 🎯 탭/패널 처리 규칙

### 엑셀 파싱 규칙
- **탭 2개**: 1번, 2번 탭 모두 분석 (고압반 없음)
- **탭 3개 이상**: 2번 탭은 고압반으로 무시, 1번과 3번 탭만 분석
- **한 탭 내 '소계/합계' 이후 +1~2행 공백**: 새 분전반 블록 시작
- **각 블록**: 별도 견적 ID 생성, 상호 링크 저장

## ⚡ OR-Tools 통합 패턴

### 자동 폴백 메커니즘
```python
try:
    from ortools.sat.python import cp_model
    # CP-SAT 솔버로 최적 배치
    model = cp_model.CpModel()
    # ... 제약조건 추가
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
except ImportError:
    # 휴리스틱 알고리즘으로 폴백
    from stubs.heuristic_placer import place_breakers_heuristic
    result = place_breakers_heuristic(breakers, panel)
```

## 📊 성능 목표

| 작업 | 목표 시간 | 최대 시간 |
|------|-----------|-----------|
| 브레이커 배치 (100개) | < 1s | 30s |
| 외함 계산 | < 500ms | 1s |
| 상평형 계산 | < 100ms | 500ms |
| API 응답 (P95) | < 200ms | 500ms |
| Health 체크 | < 50ms | 100ms |

## 🚨 중요 주의사항

### Contract-First 개발
1. **모든 API는 OpenAPI 3.1 사양 먼저 작성**
2. **오류 스키마**: `{code, message, hint?, traceId, meta{dedupKey}}`
3. **SSE 엔드포인트**: heartbeat + meta.seq 필수

### Evidence-Gated 검증
1. **모든 계산은 증거 생성 필수**
2. **SHA256 해시로 무결성 보장**
3. **회귀 테스트 20/20 통과 전 머지 금지**

### 시간대 처리
1. **모든 TIMESTAMP는 TIMESTAMPTZ 사용**
2. **UTC 기본, 로컬 시간 변환은 클라이언트에서**
3. **created_at/updated_at 필수**

### 보안
1. **키/토큰 유출 검사 필수**
2. **입력 검증 100% 커버리지**
3. **감사 로그 모든 변경사항 기록**

## 🔄 개발 워크플로우

### 세션 시작
```bash
# 1. 프로젝트 컨텍스트 로드
/sc:load

# 2. 현재 상태 확인
git status && git branch
pytest -m regression  # 회귀 테스트 확인

# 3. 작업 브랜치 생성
git checkout -b feature/[작업명]
```

### 개발 중
```bash
# 1. TodoWrite로 작업 계획
# 2. 단위별 구현 → 테스트 → 검증
# 3. 30분마다 체크포인트
/sc:save --checkpoint

# 4. 품질 체크
black src/ tests/
ruff check src/ tests/
mypy src/
pytest
```

### 세션 종료
```bash
# 1. 모든 테스트 실행
pytest --cov=src

# 2. 회귀 테스트 필수
pytest -m regression  # 20/20 PASS 확인

# 3. 작업 저장
/sc:save --type all --summarize

# 4. PR 생성 (요청 시에만)
gh pr create
```

## 📚 참조 문서

- `/spec_kit/docs/constitution.md`: 프로젝트 헌법 및 원칙
- `/spec_kit/rules/vibe_coding_rules.md`: 바이브코딩 상세 규칙
- `/spec_kit/spec/fix4_pipeline.md`: FIX-4 파이프라인 사양
- `/spec_kit/rules/business_rules.yaml`: 비즈니스 제약사항
- `/readme/claudecode.txt`: Contract-First 모드 정의
- `/readme/program.txt`: 전체 시스템 요구사항

---
*이 문서는 NABERAL KIS Estimator 프로젝트의 핵심 개발 가이드입니다.*
*Contract-First + Evidence-Gated + SPEC KIT 기반 개발을 준수하세요.*