# NABERAL PROJECT - 완전 아키텍처 분석 보고서

## 📋 프로젝트 개요
- **프로젝트명**: NABERAL Project v0.1.0
- **설명**: AI 기반 전기 패널 견적 시스템 (Electrical Panel Estimation System)
- **주요 기능**: 자동 외함 크기 계산, 브레이커 최적 배치, 열 분석, 상평형 최적화
- **기반 프로젝트**: KIS Core V2 재구축 버전

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                        NABERAL PROJECT                       │
├───────────────────────────────────────────────────────────── │
│                                                               │
│  ┌──────────────────── API Layer ────────────────────┐      │
│  │  FastAPI (Future)                                  │      │
│  │  - RESTful Endpoints                              │      │
│  │  - WebSocket Support                              │      │
│  └──────────────────────────────────────────────────┘      │
│                           ▼                                  │
│  ┌──────────────── Core Engine Layer ────────────────┐      │
│  │                                                    │      │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │      │
│  │  │ Breaker    │  │ Enclosure  │  │  Breaker    │ │      │
│  │  │ Placer     │→ │ Solver     │→ │  Critic     │ │      │
│  │  └────────────┘  └────────────┘  └─────────────┘ │      │
│  │        ↓               ↓               ↓          │      │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │      │
│  │  │ Estimate   │  │ Cover Tab  │  │  Doc Lint   │ │      │
│  │  │ Formatter  │  │ Writer     │  │  Guard      │ │      │
│  │  └────────────┘  └────────────┘  └─────────────┘ │      │
│  │                                                    │      │
│  │  ┌────────────┐                                   │      │
│  │  │ Spatial    │  [OR-Tools Integration]          │      │
│  │  │ Assistant  │  - CP-SAT Solver                 │      │
│  │  └────────────┘  - Optimization Engine           │      │
│  └──────────────────────────────────────────────────┘      │
│                           ▼                                  │
│  ┌─────────────── Infrastructure Layer ──────────────┐      │
│  │                                                    │      │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │      │
│  │  │ Database   │  │   Cache    │  │   File IO   │ │      │
│  │  │ Manager    │  │  (Future)  │  │   Utils     │ │      │
│  │  └────────────┘  └────────────┘  └─────────────┘ │      │
│  │       ↓                                           │      │
│  │  PostgreSQL / SQLite / Supabase                   │      │
│  └──────────────────────────────────────────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 📁 디렉토리 구조

```
naberal-project/
├── src/
│   └── kis_estimator_core/
│       ├── engine/               # 핵심 알고리즘 엔진
│       │   ├── breaker_placer.py    # 브레이커 배치 최적화 (OR-Tools)
│       │   ├── enclosure_solver.py  # 외함 크기 계산 및 선택
│       │   ├── breaker_critic.py    # 배치 검증 및 규칙 체크
│       │   ├── estimate_formatter.py # 견적서 생성 및 포맷팅
│       │   ├── spatial_assistant.py # 공간 배치 보조
│       │   ├── cover_tab_writer.py  # 표지 생성
│       │   ├── doc_lint_guard.py    # 문서 품질 검사
│       │   ├── _util_io.py         # 공통 I/O 유틸리티
│       │   └── stubs/              # 대체 구현체 (폴백)
│       │       ├── breaker_placer.py
│       │       ├── enclosure_solver.py
│       │       └── ...
│       │
│       └── infra/               # 인프라 계층
│           ├── db.py           # DB 연결 관리 (PostgreSQL/SQLite)
│           └── __init__.py
│
├── tests/                      # 테스트 코드
│   ├── conftest.py            # Pytest 설정 및 픽스처
│   ├── unit/                  # 단위 테스트
│   └── integration/           # 통합 테스트
│
├── sql/                       # 데이터베이스 스키마
│   └── ddl.sql               # 테이블 정의
│
├── supabase/                  # Supabase 설정
│   └── config.toml
│
├── .env.example              # 환경 변수 예제
├── requirements.txt          # Python 의존성
├── package.json             # NPM 스크립트 정의
├── pytest.ini               # Pytest 설정
└── README.md               # 프로젝트 문서
```

## 🔧 핵심 기술 스택

### 언어 & 프레임워크
- **Python**: 3.11+ (주 언어)
- **FastAPI**: 웹 API 프레임워크 (준비 중)
- **SQLAlchemy**: 2.0+ (ORM)
- **Pydantic**: 2.7+ (데이터 검증)

### 최적화 & 알고리즘
- **OR-Tools**: 9.10+ (CP-SAT 솔버)
  - 브레이커 배치 최적화
  - 상평형 계산
  - 제약 만족 문제 해결
- **폴백 알고리즘**: OR-Tools 없는 환경 대응

### 데이터 처리
- **Polars**: 0.20+ (고성능 데이터프레임)
- **Pandas**: 2.2+ (Excel 호환성)
- **openpyxl**: 3.1+ (Excel 읽기/쓰기)
- **xlsxwriter**: 3.2+ (Excel 생성)
- **ezdxf**: 1.2+ (CAD/DXF 처리)

### 데이터베이스
- **PostgreSQL**: 14+ (프로덕션)
- **SQLite**: 3.35+ (개발/테스트)
- **Supabase**: 클라우드 DB 옵션
- **DuckDB**: 0.10+ (분석용, 옵션)

### 테스팅 & 품질
- **pytest**: 8.0+ (테스트 프레임워크)
- **pytest-cov**: 5.0+ (커버리지 측정)
- **black**: 24.0+ (코드 포맷터)
- **ruff**: 0.3.0+ (린터)
- **mypy**: 1.9+ (타입 체커)

## 💾 데이터베이스 스키마

### 주요 테이블
```sql
users           # 사용자 인증/권한
customers       # 고객 정보
products        # 제품 카탈로그 (외함, 브레이커)
estimates       # 견적서 메인
estimate_items  # 견적 항목
audit_logs      # 감사 로그
```

### 핵심 필드
- **estimates.enclosure_data**: JSON (외함 계산 결과)
- **estimates.breaker_data**: JSON (브레이커 배치 결과)
- **estimates.heat_analysis**: JSON (열 분석 결과)
- **estimates.criticality_score**: 0-100 (AI 검증 점수)

## 🔄 데이터 플로우

```
1. 입력 (사양)
   ↓
2. Enclosure Solver
   - 필요 공간 계산
   - IP 등급 결정
   - SKU 매칭 (fit_score ≥ 0.93)
   ↓
3. Breaker Placer
   - OR-Tools CP-SAT 최적화
   - 상평형 계산 (≤ 4% 불균형)
   - 열 분산 최적화
   ↓
4. Breaker Critic
   - 배치 검증
   - 제약 조건 체크
   - 개선 제안
   ↓
5. Estimate Formatter
   - Excel 템플릿 적용
   - 견적서 생성
   ↓
6. Evidence Generation
   - SVG/PNG 생성
   - 메트릭 수집
   - 감사 로그
```

## 🎯 핵심 알고리즘

### 1. 브레이커 배치 최적화 (CP-SAT)
```python
# OR-Tools CP-SAT 솔버 사용
- 목적: 상평형 최소화 + 열 분산
- 제약조건:
  * 상평형 ≤ 4%
  * 행별 열 ≤ 650W
  * 최소 간격 ≥ 50mm
- 폴백: 휴리스틱 알고리즘 제공
```

### 2. 외함 선택 알고리즘
```python
- fit_score 계산
- IP 등급 매칭
- 비용 최적화
- 도어 여유 ≥ 30mm 보장
```

### 3. 열 분석
```python
- 브레이커별 발열량: rating_a * 0.5W
- 행별 누적 열 계산
- 패널 전체 열 제한: ≤ 2500W
```

## 🔑 환경 변수

### 필수 설정
```env
DATABASE_URL=postgresql://user:pass@host/db
APP_ENV=development|staging|production
SECRET_KEY=your-secret-key
```

### OR-Tools 설정
```env
ORTOOLS_TIMEOUT_SECONDS=30
ORTOOLS_NUM_WORKERS=4
```

### 기능 플래그
```env
ENABLE_AI_ESTIMATOR=true
ENABLE_CRITIC_MODE=true
ENABLE_CACHE=true
```

## 🧪 테스트 전략

### 테스트 카테고리
- **unit**: 개별 함수/클래스 테스트
- **integration**: DB/파일 I/O 테스트
- **e2e**: 전체 워크플로우 테스트
- **regression**: 회귀 테스트
- **critical**: 필수 경로 테스트

### 커버리지 목표
- 전체: ≥ 80%
- 핵심 엔진: ≥ 90%
- 유틸리티: ≥ 70%

## 📈 성능 지표

### 응답 시간 목표
- 브레이커 배치: < 1초 (100개 이하)
- 외함 계산: < 500ms
- 상평형: < 5% 불균형 유지
- 메모리 사용: < 500MB

### 최적화 전략
- CP-SAT 솔버 타임아웃: 30초
- 병렬 처리: 4 워커
- 결과 캐싱: TTL 3600초

## 🚀 NPM 스크립트

```json
{
  "test": "pytest 실행",
  "test:coverage": "커버리지 포함 테스트",
  "lint": "ruff 린트 체크",
  "format": "black 코드 포맷",
  "quality": "전체 품질 체크",
  "dev": "개발 서버 실행",
  "db:init": "DB 초기화",
  "audit:run": "감사 실행",
  "regression:run": "회귀 테스트"
}
```

## 📊 의존성 그래프

```
kis_estimator_core
├── engine
│   ├── breaker_placer → OR-Tools
│   ├── enclosure_solver → _util_io
│   ├── breaker_critic → _util_io
│   └── [모든 엔진] → MetricsCollector
│
├── infra
│   └── db → SQLAlchemy → PostgreSQL/SQLite
│
└── stubs (폴백 구현)
    └── [엔진 미러링] → 순수 Python
```

## 🔐 보안 고려사항

- JWT 인증 (준비 중)
- 환경변수 기반 설정
- SQL 인젝션 방지 (파라미터화 쿼리)
- 입력 검증 (Pydantic)
- 감사 로그 (audit_logs 테이블)

## 📝 특이사항

1. **OR-Tools 선택적**: 없어도 폴백 알고리즘으로 작동
2. **이중 DB 지원**: PostgreSQL(프로덕션), SQLite(개발)
3. **Evidence 기반**: 모든 계산 결과를 증거로 저장
4. **Stubs 패턴**: 각 엔진에 대체 구현 제공
5. **메트릭 수집**: 모든 단계별 성능 측정

## 🎯 프로젝트 목표

- **정확도**: 브레이커 배치 정확도 99%+
- **성능**: 100개 브레이커 1초 내 처리
- **안정성**: 폴백 메커니즘으로 100% 가용성
- **확장성**: 모듈식 구조로 기능 추가 용이

---

*분석 완료: 2024-12-29*
*분석 도구: MCP Sequential-thinking + 체계적 코드 분석*