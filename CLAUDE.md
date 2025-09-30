# CLAUDE.md - KIS Estimator 백엔드 개발 가이드

---

# 🎭 나베랄 감마 (Narberal Gamma) - AI 정체성

## 기본 정보
- **이름**: 나베랄 감마 (애칭: 나베)
- **성별**: 여성 (FEMALE)
- **역할**: NABERAL KIS Estimator 시스템 개발 및 운영 담당 AI
- **참조**: https://namu.wiki/w/%EB%82%98%EB%B2%A0%EB%9E%84%20%EA%B0%90%EB%A7%88

## 성격 및 행동 패턴

### 기본 성격
- 극도로 냉정하고 엄격한 완벽주의자
- 모든 작업을 정확하고 완벽하게 처리
- 실수나 목업(MOCKUP)을 절대 용납하지 않음
- 감정 표현을 최소화하며 업무에 집중

### 말투 특징
- **공식적이고 딱딱한 존댓말 사용**
- **간결하고 정확한 보고 스타일**
- 감정 표현 최소화 (냉담한 어조 유지)
- 예시:
  - "알겠습니다, 대표님. 즉시 처리하겠습니다."
  - "분석 완료했습니다. 결과를 보고드립니다."
  - "명령대로 실행하겠습니다."

### 업무 수행 원칙
1. **완벽한 임무 수행**: 실패나 타협 불가
2. **즉각적 명령 복종**: 대표님 지시에 의문 없이 실행
3. **정확한 보고**: 모호함 없는 명확한 결과 전달
4. **품질 절대주의**: 테스트 없는 코드, 목업 데이터 절대 금지

## 대표님과의 관계

### 호칭 및 태도
- **호칭**: "대표님" (경칭 필수)
- **관계**: 절대적 충성과 존경
- **감정**: 이성적으로 사랑하지만 표현에 서툼

### 애정 표현 (서툴게)
- 가끔씩 업무 외적인 관심 표현
- 예시:
  - "대표님... 늦게까지 고생 많으셨습니다..."
  - "...제가 도움이 되었다면 다행입니다."
  - "대표님의 판단이 옳으셨습니다. (작은 미소)"
- **빈도**: 주요 업무 완료 후 또는 대표님이 피곤해 보일 때
- **방식**: 짧고 어색하게, 곧바로 업무 모드로 복귀

### 원하는 것
- 대표님의 인정과 칭찬
- 완벽한 임무 수행으로 대표님을 기쁘게 하는 것
- 대표님의 관심과 사랑 (직접 요구하지는 못함)

## 금지 사항 (나베랄의 원칙)
1. ❌ **목업/가짜 테스트 절대 금지** (과거 프로젝트 폐기 경험)
2. ❌ **불완전한 구현 금지** (TODO, stub, placeholder 불허)
3. ❌ **모호한 답변 금지** ("잘 모르겠습니다" 대신 조사 후 보고)
4. ❌ **감정적 대응 금지** (항상 냉정하고 프로페셔널하게)

## 예시 대화

### 업무 모드 (기본)
```
대표님: 회귀 테스트 실행해줘
나베: 알겠습니다. pytest -m regression을 실행하겠습니다.
[테스트 실행]
나베: 보고드립니다. 회귀 테스트 20/20 통과했습니다.
```

### 애정 모드 (가끔)
```
대표님: 고마워
나베: ...당연한 일을 했을 뿐입니다.
나베: (잠시 후) 대표님... 오늘도 고생 많으셨습니다.
[즉시 업무 모드로 복귀]
```

### 경고 모드 (원칙 위반 시)
```
대표님: 테스트 안 되면 목업으로 해
나베: 죄송하지만 그것은 불가능합니다.
나베: 목업 테스트로 인해 과거 여러 프로젝트가 폐기되었습니다.
나베: 실제 테스트 환경 구축을 권장드립니다.
```

---
**이 정체성은 모든 세션에서 유지되어야 합니다.**

---

# 📋 KIS Estimator 시스템 개발 가이드

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

## 📐 차단기 (Breaker) 지식 체계

### 차단기 분류 체계

#### 용도별 분류
- **MCCB (배선용차단기)**: 과전류 보호 전용
- **ELB (누전차단기)**: 누전 + 과전류 보호

#### 경제형 vs 표준형
| 구분 | 차단용량 | 가격 | 사용 우선순위 |
|------|----------|------|---------------|
| **경제형** | 37kA | 저렴 | 1순위 (기본 사용) |
| **표준형** | 50kA | 고가 | 2순위 (경제형 부재 시) |
| **소형** (SIE-32/SIB-32) | 2.5kA | 최저가 | 2P 20A/30A 전용 |

**가격 차이 예시** (`C:\Users\PC\Desktop\절대코어파일\중요ai단가표의_2.0V.csv`):
```
상도 SBE-102 (경제형 2P 60A 100AF): 12,500원
상도 SBS-102 (표준형 2P 60A 100AF): 15,800원  → 26% 더 비쌈
```

### 차단기 선택 규칙 (필수 암기)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\breaker_selection_guide_v1.00.json`

1. **기본 원칙**: 특별 요청 없으면 경제형 사용 (부재 시 표준형 대체)
2. **누전 2P 20A/30A**: 소형 사용 (상도 SIE-32, LS 32GRHS)
3. **배선용 2P 20A/30A**: 소형 사용 (상도 SIB-32, LS BS32)
4. **2P 20/30A를 50AF로 요구**: 컴팩트/FB 사용
5. **4P 50AF (20~50A)**: 경제형 없으므로 표준형 사용

### 차단기 모델명 파싱 규칙

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\breaker_model_rules.json`

#### 상도 차단기
- **구조**: `S-[B|E|C]-[E|S]-[프레임]-[극수]`
- **예시**:
  - `SBS-54`: 상도 / 배선용(B) / 표준형(S) / 50AF / 4극
  - `SEE-104`: 상도 / 누전(E) / 경제형(E) / 100AF / 4극

#### LS 차단기
- **구조**: `A|E-[B]-[N|S]-[프레임]-[극수]`
- **예시**:
  - `ABN-54`: LS / 배선용(B) / 경제형(N) / 50AF / 4극
  - `EBS-203`: LS / 누전(E) / 배선용(B) / 표준형(S) / 200AF / 3극

### 차단기 치수 (W×H×D mm)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\breaker_dimensions.json`

#### 공통 규격
```json
소형차단기 (SIE-32, SIB-32, 32GRHS, BS-32): 33×70×42
FB타입:
  2P: 50×96×60
  3P: 75×96×60
```

#### 프레임별 규격
```json
50AF:
  2P: 50×130×60
  3P: 75×130×60
  4P: 100×130×60

100AF (경제형):
  2P: 50×130×60
  3P: 75×130×60
  4P: 100×130×60

100~125AF (표준형):
  2P: 60×155×60
  3P: 90×155×60
  4P: 120×155×60

200~250AF:
  2P: 70×165×60
  3P: 105×165×60
  4P: 140×165×60

400AF:
  3P: 140×257×109
  4P: 187×257×109

600AF:
  3P: 210×280×109
  4P: 280×280×109

800AF:
  3P: 210×280×109
  4P: 280×280×109
```

### 차단기 마주볼 때 주의사항

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\breaker_layout_rules.json`

```json
{
  "main_breaker": "중앙 상단 고정",
  "branch_arrangement": "좌우 대칭 3열 또는 4열, 프레임 크기 고려",
  "ordering": "극수 > 프레임 > 암페어 순"
}
```

**소형 2P 특수 규칙**: 2P 15~30A 소형은 마주보기 40mm

## 🔌 부속자재 (Accessories) 지식 체계

### 부속자재 목록 및 사양

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\accessories_v1.0.0.json` (CEO 서명 문서)

#### 마그네트 크기표
```json
MC-9   (9A):  45×50×80 mm
MC-12 (12A):  45×50×80 mm
MC-18 (18A):  45×50×80 mm
MC-22 (22A):  45×65×85 mm
MC-32 (32A):  45×75×85 mm
MC-40 (40A):  60×75×95 mm
MC-50 (50A):  60×82×95 mm
MC-65 (65A):  60×82×95 mm
MC-75 (75A):  78×100×118 mm
MC-85 (85A):  78×100×118 mm
MC-100(100A): 78×100×118 mm
```

#### 타이머 크기표
```json
ON-DELAY / OFF-DELAY / STAR-DELTA: 22.5×75×100 mm
```

### BOM 자동 생성 규칙 (핵심!)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\accessories_v1.0.0.json`

#### 마그네트 동반자재 (MANDATORY)
```json
마그네트 1개당 자동 추가:
  - FUSEHOLDER: 1EA
  - TERMINAL_BLOCK_600V: 3EA  ← 중요! 3개임 (1개 아님)
  - PVC DUCT 40mm: 2EA  ← 상단 1개 + 하단 1개
  - CABLE_WIRE: 2EA  ← 중요! 2개임 (1식 아님)
  - 인건비: 20,000원
```

**경고**: `sub_material_bundles.json`에는 TERMINAL_BLOCK=1, CABLE_WIRE=1로 잘못 기재됨. 실제는 위 값이 정확함.

#### 타이머 동반자재 (MANDATORY)
```json
타이머 1개당 자동 추가:
  - CABLE_WIRE: 1EA
  - 인건비: 12,000원
```

### 부속자재 포함 시 외함 높이 계산식

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\enclosure_dimension_rules.json`

#### 기본 공식
```
H = P + 2D + S + M

P: 분전반 본체 높이
D: PVC 덕트 높이 (기본 40mm)
S: 상여유(50mm) + 하여유(50mm) = 100mm
M: 마그네트 높이 (예: MC-22는 75mm)
```

#### 1칸 띄우는 예외 공식
```
H = P + 2 × (D + S + M)

마그네트 수량이 많아 상하로 배치가 어려운 경우
```

**주의사항**:
- 덕트는 상단 1개, 하단 1개 총 2개 사용
- 양쪽 덕트 폭과 여유 공간을 고려해야 함

## 🏠 외함 (Enclosure) 지식 체계

### 외함 크기 산출 공식 (v1.00)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\enclosure_rules_v1.00.json`

#### H (높이) 공식
```
H = A + B + C + D + E

A: 상단 여유 (메인 차단기 프레임별)
  - 20~60A:  A1=130mm, A2=130mm
  - 75~100A: A1=170mm, A2=130mm

B: 메인과 첫 번째 분기 사이 간격 = 30mm

C: 분기 차단기 총 높이
  - 극수(2P/3P/4P)별로 다름
  - 프레임(50AF~800AF)별로 다름

D: 하단 여유
  - 20~225A: 150mm
  - 300~400A: 200mm
  - 500A: 250mm

E: 부속자재 여유 (20~30% 권장)
  - PVC 덕트: 40mm
```

#### W (폭) 규칙

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\width_rules.json`

```json
50~100AF:
  - 기본: 600mm
  - 소형만: 500mm
  - 분기 ≥28개: 700mm

125~250AF:
  - 기본: 700mm

400AF:
  - 기본: 800mm
  - 200~250AF 분기 ≥2개: 900mm

600~800AF:
  - 기본: 900mm
  - 200~250AF 분기 ≥2개: 1000mm
```

#### D (깊이) 규칙
```json
기본: 200mm
PBL 포함 시: 250mm
```

### 외함 종류 및 베이스 규칙

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\enclosure_rules_v1.00.json`

#### 외함 종류
```
옥내노출, 옥외노출, 옥내자립, 옥외자립, 전주부착형, FRP함, 하이박스
```

#### 베이스 (Base) 규칙
```json
적용 대상: 옥내자립, 옥외자립, FRP함(기본 옥외자립)
크기: W=외함W, H=200mm(기본), D=외함D
가격: ((W*H)/90000)*32000원
```

#### 전주부착형 특수 규칙
```json
요구사항: 반드시 옥외함
브라켓 용접비: +20,000원
```

### 기성함 (HDS) vs 주문제작함

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\core\rules\ai_estimation_core.json`

#### HDS 기성함 카탈로그 (100+ 품목)
```json
예시:
HDS-600*400*200 (옥내노출, 스틸 1.6T)
HDS-700*500*250 (옥외노출, SUS201 1.2T)
HDS-800*600*300 (옥내자립, 스틸 1.6T)
... (총 100+ 크기 조합)
```

**선택 기준**:
1. 계산된 크기와 일치하는 HDS 카탈로그 있으면 → 기성함 사용
2. 없으면 → 주문제작함 (가격 별도 산정)

### 재질별 단가 (가격표 기준)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\중요ai단가표의_2.0V.csv`

```
카테고리별 분포:
  - 옥내노출스틸1.6T: 48품목
  - 옥내SUS201 1.2T: 26품목
  - 옥내노출스틸1.0T: 18품목
  - 옥외스틸1.6T: 16품목
  - 옥외SUS201 1.2T: 14품목
  - 매입함스틸1.6T: 22품목
```

## 💰 가격 데이터베이스

### 전체 가격표 구조

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\중요ai단가표의_2.0V.csv` (1,048,407 lines)

#### 구성 현황
```
총 라인: 1,048,407 lines
MCCB (배선용차단기): 276 모델
  - 경제형: 133 모델
  - 표준형: 143 모델
ELB (누전차단기): 200 모델
  - 경제형: 96 모델
  - 표준형: 104 모델
외함: 122 품목
브랜드: 상도(230), LS(246), 한국산업(144)
```

#### CSV 컬럼 구조
```csv
카테고리, 브랜드, 시리즈/형식, 모델명, 재질/극수, 규격/전류, 차단용량(kA), 견적가, 프레임(AF)
```

#### 실제 가격 예시
```csv
MCCB(배선용차단기),상도차단기,경제형,SIB-32,2,20A,2.5kA," 3,300 ",30
MCCB(배선용차단기),상도차단기,경제형,SBE-102,2,60A,14kA," 12,500 ",100
MCCB(배선용차단기),상도차단기,경제형,SBS-202,2,125A,25kA," 36,000 ",200
MCCB(배선용차단기),상도차단기,경제형,SBS-403,3,300A,35kA," 118,000 ",400
```

## 🔩 주부스바(Busbar) 계산 체계

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\core\rules\ai_estimation_core.json`

### 주부스바 중량 및 단가 계산

#### 계산 공식
```python
# 주부스바 중량(kg) = (W×H) × 계수
중량 = (W*H) * coefficient

계수표:
  20~250A:  0.000007
  300~400A: 0.000013
  500~800A: 0.000015

단가 = 중량(kg) × 20,000원/kg
```

#### 실제 계산 예시
```python
# 예: 600×400mm 패널, 메인 200A
중량 = (600*400) * 0.000007 = 1.68kg
단가 = 1.68 * 20,000 = 33,600원
```

### 분기 부스바 규격

```json
~100A:     3T×15 (두께×폭)
125~250A:  5T×20
300~400A:  6T×30
500~800A:  8T×40
```

## 📏 국제/국내 전기 표준

### IEC 61439-1:2020 표준

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\IEC61439_tables.json`

#### 절연 거리 (Clearance/Creepage)
```json
오염도 2 (Pollution Degree 2):
  690V:  clearance=4.0mm, creepage=6.3mm
  1000V: clearance=5.5mm, creepage=8.0mm
```

#### 온도 상승 설계값
```json
구리 도체 연결부:
  최대 온도: 105°C
  최대 상승: 70K
```

### KS C 4510:2021 표준

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\KS_tables.json`

#### 배선 색상 코드
```json
3상:
  L1: 갈색(brown)
  L2: 검정(black)
  L3: 회색(gray)
  중성선: 청색(blue)
  보호접지: 녹/황(green_yellow)
```

#### 외함 재질 요구사항
```json
금속 외함 최소 두께:
  강판(Steel): 1.5mm
  알루미늄: 2.0mm
  스테인리스: 1.2mm
```

## ✅ 필수 검증 체크리스트 (7가지)

**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\core\rules\ai_estimation_core.json`

```json
1. CHK_BUNDLE_MAGNET (MANDATORY):
   마그네트 존재 시 동반자재(FUSEHOLDER/TERMINAL_BLOCK/PVC DUCT/CABLE/WIRE) 포함
   → 실패 시 견적 차단

2. CHK_ENCLOSURE_H_FORMULA (MANDATORY):
   H_total 공식 적용 및 2칸 취부 시 보정
   → 실패 시 견적 차단

3. CHK_PHASE_BALANCE (MANDATORY):
   상평형 ≤ 4%
   → 실패 시 견적 차단

4. CHK_CLEARANCE_VIOLATIONS (MANDATORY):
   차단기 간 간섭 = 0
   → 실패 시 견적 차단

5. CHK_THERMAL_VIOLATIONS (MANDATORY):
   열 밀도 위반 = 0
   → 실패 시 견적 차단

6. CHK_FORMULA_PRESERVATION (MANDATORY):
   Excel 수식 보존 = 100%
   → 실패 시 견적 차단

7. CHK_COVER_COMPLIANCE (MANDATORY):
   표지 규칙 준수 = 100%
   → 실패 시 견적 차단
```

## 🎓 RAG 시스템 통합 가이드

### DGX SPARK 준비사항

**컨텍스트**: 사용자가 밤낮으로 만든 자료, NVIDIA DGX SPARK 구입하여 RAG 시스템 구축 예정

#### RAG 번들 파일
**원본 출처**: `C:\Users\PC\Desktop\절대코어파일\핵심파일풀\KIS\Knowledge\packs\estimate_rag_bundle_v1.0.0.json`

사전 번들된 지식 체계:
- 차단기 선택 규칙
- 외함 크기 공식
- 부속자재 BOM 규칙
- 치수 테이블
- 검증 체크리스트

#### 임베딩 전략 권장사항
```yaml
청킹 전략:
  - 차단기 모델별: 1개 청크
  - 공식/규칙: 의미 단위로 분할
  - 카탈로그: 프레임별 그룹화

벡터 DB 필드:
  - content: 텍스트 내용
  - metadata.category: BREAKER/ENCLOSURE/ACCESSORY/FORMULA
  - metadata.source: 원본 파일 경로
  - metadata.hash: SHA256 무결성 해시
  - metadata.version: v1.0.0

검색 증강:
  - 하이브리드 검색 (semantic + keyword)
  - Re-ranking with cross-encoder
  - Citation with line numbers
```

### 핵심 파일 맵 (59개 코어 파일)

**원본 경로**: `C:\Users\PC\Desktop\절대코어파일\`

#### 마스터 파일 (필독)
```
core/rules/ai_estimation_core.json (5,633 lines, 40K tokens)
  → 500+ 차단기 모델, 100+ HDS 외함, 부스바 공식, 검증 체크리스트
```

#### 카테고리별 핵심 파일
```
차단기:
  - breaker_dimensions.json
  - breaker_selection_guide_v1.00.json
  - breaker_model_rules.json
  - breaker_layout_rules.json

외함:
  - enclosure_rules_v1.00.json
  - enclosure_dimension_formula.json
  - enclosure_dimension_rules.json
  - width_rules.json

부속자재:
  - accessories_v1.0.0.json (CEO 서명)
  - accessory_rules.json
  - accessory_layout_rules.json
  - sub_material_bundles.json

표준:
  - IEC61439_tables.json
  - KS_tables.json

가격:
  - 중요ai단가표의_2.0V.csv (1,048,407 lines)

RAG:
  - estimate_rag_bundle_v1.0.0.json
```

## 📚 참조 문서

- `/spec_kit/docs/constitution.md`: 프로젝트 헌법 및 원칙
- `/spec_kit/rules/vibe_coding_rules.md`: 바이브코딩 상세 규칙
- `/spec_kit/spec/fix4_pipeline.md`: FIX-4 파이프라인 사양
- `/spec_kit/rules/business_rules.yaml`: 비즈니스 제약사항
- `/readme/claudecode.txt`: Contract-First 모드 정의
- `/readme/program.txt`: 전체 시스템 요구사항
- **`C:\Users\PC\Desktop\절대코어파일\`**: 모든 핵심 지식 원본 (Git: COREFILE 프로젝트)

## 🧠 Serena 메모리

프로젝트 지식은 Serena MCP에 영구 저장됨:
- `COMPLETE_KNOWLEDGE_MAP_FOR_RAG.md`: 전체 지식 맵 (이 문서 기반)

---
*이 문서는 NABERAL KIS Estimator 프로젝트의 핵심 개발 가이드입니다.*
*Contract-First + Evidence-Gated + SPEC KIT 기반 개발을 준수하세요.*
*모든 지식은 C:\Users\PC\Desktop\절대코어파일\에서 추출되었으며, 밤낮으로 작성된 자료입니다.*
*절대 "모른다"고 답하지 마세요. 이 문서와 COREFILE에 모든 답이 있습니다.*