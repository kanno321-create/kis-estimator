# NABERAL Project Constitution v1.0

## 📜 헌법 전문
본 헌법은 NABERAL 프로젝트의 개발 원칙, 품질 기준, 그리고 절차를 정의합니다.

## 🎯 핵심 원칙

### 1. SPEC KIT 절대 기준
- 모든 개발 작업은 SPEC KIT 프레임워크를 준수해야 한다
- 문서화 우선, 구현 후순위 원칙
- 증거 기반 개발 (Evidence-Based Development)

### 2. FIX-4 파이프라인
모든 견적 시스템은 다음 순서를 엄격히 준수:
1. **Enclosure (외함)**: 크기 및 사양 결정
2. **Breaker (차단기)**: 배치 및 상평형 (+Critic 검증)
3. **Format (양식)**: 문서 포맷팅 및 표준화
4. **Cover (표지)**: 표지 생성 및 메타데이터
5. **Doc Lint (검증)**: 최종 문서 품질 검증

### 3. 품질 게이트 (Quality Gates)

#### 필수 통과 기준:
```
ENC (Enclosure):
- fit_score ≥ 0.90
- IP rating ≥ 44
- 도어 여유 ≥ 30mm

BRK (Breaker):
- 상평형 ≤ 3-5%
- 간섭/열/간극 위반 = 0
- Critic 재검증 통과

FORMAT:
- 문서 린트 오류 = 0
- 표지 규칙 준수 = 100%
- 네임드 범위 손상 = 0

DESIGN:
- Polisher score ≥ 95(A)
- WCAG AA compliance = 100%

REGRESSION:
- 20/20 테스트 케이스 PASS
- 골드셋 비교 일치율 ≥ 99%
```

## 📊 증거 수집 체계

### Evidence Bundle 구성:
```
/evidence/{timestamp}/
├── enclosure/
│   ├── calculation.json
│   ├── validation.svg
│   └── metrics.json
├── breaker/
│   ├── placement.json
│   ├── heatmap.png
│   └── phase_balance.json
├── format/
│   ├── document.pdf
│   ├── lint_report.json
│   └── template_check.csv
└── meta/
    ├── pipeline_log.json
    ├── gate_results.json
    └── hash_manifest.txt
```

## 🔄 개발 워크플로우

### 1. 계획 단계 (Planning)
- Spec 문서 작성
- 요구사항 정의
- 테스트 케이스 설계

### 2. 구현 단계 (Implementation)
- TDD (Test-Driven Development)
- 페어 프로그래밍 권장
- 코드 리뷰 필수

### 3. 검증 단계 (Verification)
- 단위 테스트: ≥ 80% 커버리지
- 통합 테스트: FIX-4 파이프라인
- 회귀 테스트: 20/20 골드셋

### 4. 릴리스 단계 (Release)
- Evidence Bundle 생성
- 게이트 검증 통과
- 문서화 완료

## 🛡️ 보안 및 규정

### 데이터 보호:
- PII (개인식별정보) 마스킹
- 암호화 저장 (at-rest)
- 암호화 전송 (in-transit)

### 접근 제어:
- RBAC (Role-Based Access Control)
- API 키 관리
- 감사 로그 필수

### 규정 준수:
- GDPR / 개인정보보호법
- 산업 표준 (IEC, IEEE)
- 접근성 표준 (WCAG AA)

## 📈 성능 기준

### 응답 시간:
- API 응답: < 200ms (P95)
- 브레이커 배치: < 1s (100개)
- 문서 생성: < 5s

### 확장성:
- 동시 사용자: 100+
- 일일 처리량: 10,000+ 견적
- 데이터 보존: 7년

### 가용성:
- SLA: 99.9% uptime
- RPO: 1시간
- RTO: 4시간

## 🔧 기술 스택 표준

### 필수 기술:
- Python 3.11+
- OR-Tools 9.10+
- PostgreSQL 14+ / SQLite 3.35+

### 권장 라이브러리:
- FastAPI (API)
- SQLAlchemy (ORM)
- Pydantic (검증)
- pytest (테스트)

## 📝 문서화 표준

### 코드 문서:
- Docstring 필수 (Google Style)
- Type hints 필수
- 주석: Why > What

### 프로젝트 문서:
- README.md 필수
- CHANGELOG.md 유지
- API 문서 (OpenAPI)

## 🚀 개정 이력

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| 1.0 | 2024-12-29 | 초기 헌법 제정 |

---

**본 헌법은 NABERAL 프로젝트의 최고 규범으로서 모든 개발 활동의 기준이 됩니다.**