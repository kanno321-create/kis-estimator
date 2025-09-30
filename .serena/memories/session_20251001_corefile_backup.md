# 세션 요약: COREFILE 백업 및 Git 저장소 생성

## 날짜
2025-10-01 03:50 KST

## 주요 성과

### 1. 핵심 파일 발견 및 분석
**위치**: `C:\Users\PC\Desktop\절대코어파일\`

#### 📁 핵심파일풀/ (규칙 + 데이터)
- **견적 공식**: ai_estimation_core_v1.2.0.json (CEO 서명 필수)
  - PVC 커버 비용: `(W × H) / 90000 × 12000 KRW`
  - 도장 면적: `2 × (W×H + W×D + H×D)`
  - 공간 활용률: ≤ 0.85
  - 인건비: 35,000원/시간 (관리비 15%, 마크업 12%)

- **외함 크기 공식**: enclosure_dimension_formula.json
  - 100AF=600mm, 125-250AF=700mm, 400AF=800mm, 600AF+=900mm
  - 높이: 브레이커행당 100mm, 마그네트 70mm, 단자대 50mm

- **부스바 규칙**: busbar_rules.json
  - 공식: `T × width × length` (KG)
  - 기본 단가: 19,500원/KG

- **자재 카탈로그**:
  - breakers.csv: model, phase, current_a, width_unit, heat_w, price
  - enclosures.csv: W, H, D, ip_rating, max_heat_w, slot_unit, price
  - MCCB 치수: LS Metasol, 상도전기

#### 📁 core/ (엔진 구현 코드)
**FIX-4 파이프라인 실제 구현**:

1. **enclosure_solver.py**: 외함 계산
   - fit_score ≥ 0.93 필수
   - IP 등급 결정
   - 미터 윈도우/CT 구획 옵션

2. **breaker_placer.py**: 브레이커 배치
   - OR-Tools CP-SAT 솔버 (폴백: 휴리스틱)
   - 상평형 ≤ 4% 필수
   - 간섭 위반 = 0 필수
   - 열 위반 = 0 필수

3. **breaker_critic.py**: 배치 검증
   - 임계값 상수 정의
   - 위반 사항 보고
   - 개선 권고

4. **estimate_formatter.py**: 문서 포맷
   - openpyxl 네임드 레인지
   - 수식 보존 100% 필수

5. **doc_lint_guard.py**: 최종 검증
   - 필수 필드 확인
   - 문서별 품질 게이트

### 2. Serena 메모리 저장
**저장된 메모리 4개**:

1. **core_estimation_formulas**
   - 견적 공식 (PVC, 도장, 공간활용)
   - 레이아웃 규칙 (양 어레이, 대면 배치)
   - 비용 요소 (인건비, 설치시간)
   - 외함/부스바 계산

2. **material_catalog_schema**
   - 브레이커/외함 스펙 구조
   - MCCB 치수 테이블
   - 통합 가격표 구조

3. **accessory_rules_schema**
   - 부자재 카테고리 및 가격
   - 배치 규칙
   - 적용 우선순위

4. **fix4_engine_implementations**
   - 5단계 파이프라인 상세 설명
   - OR-Tools 통합 패턴
   - 품질 게이트 기준
   - 통합 방법

### 3. Git 저장소 생성 및 푸시

**저장소**: https://github.com/kanno321-create/COREFILE

**통계**:
- 파일 수: 12,980개
- 코드 라인: 968,531줄
- Initial commit 완료

**구조**:
```
COREFILE/
├── README.md                    # 상세 문서
├── .gitignore                   # Git 제외 규칙
├── core/
│   ├── engine/                  # FIX-4 엔진 (Python)
│   ├── catalog/                 # 자재 카탈로그 (CSV)
│   ├── rules/                   # 비즈니스 규칙 (JSON/YAML)
│   ├── size/                    # MCCB 치수 테이블
│   ├── pricebook/               # 통합 가격표
│   └── manifests/               # SHA256, 인벤토리
└── 핵심파일풀/
    ├── KIS/Knowledge/packs/     # 견적 규칙
    ├── data/catalog/            # 자재 스펙
    ├── data/pricebook/          # 가격표
    └── docs/                    # 운영 정책
```

## 중요 발견

### 🚨 위기 해결
사용자가 "핵심 파일이랑 자재리스트, 견적로직 없어졌다"고 보고
→ `C:\Users\PC\Desktop\절대코어파일\` 폴더에서 모두 발견
→ Git 백업으로 안전하게 보관

### ✅ 품질 게이트 (절대 기준)
| 단계 | 지표 | 기준 |
|------|------|------|
| Enclosure | fit_score | ≥ 0.90 |
| Breaker | 상평형 | ≤ 4% |
| Breaker | 간섭 위반 | = 0 |
| Breaker | 열 위반 | = 0 |
| Format | 수식 보존 | = 100% |
| Doc Lint | 오류 | = 0 |
| Regression | 골드셋 | 20/20 PASS |

### 🔧 기술 스택
- **Python 3.11+**
- **OR-Tools** ≥9.7.0 (CP-SAT 솔버)
- **openpyxl** ≥3.1.0 (Excel 네임드 레인지)
- **FastAPI** (메인 프로젝트)
- **PostgreSQL** (Supabase)

## 다음 단계

### 즉시 필요 작업
1. **메인 프로젝트 통합**
   ```bash
   # 엔진 코드 복사
   cp -r COREFILE/core/engine/* kis-estimator-main/src/kis_estimator_core/engine/
   
   # 규칙 파일 복사
   cp -r COREFILE/core/rules/* kis-estimator-main/data/rules/
   
   # 카탈로그 임포트
   python scripts/import_catalog.py --source COREFILE/core/catalog/
   ```

2. **의존성 추가**
   ```toml
   [tool.poetry.dependencies]
   ortools = "^9.7.0"
   openpyxl = "^3.1.0"
   ```

3. **테스트 실행**
   ```bash
   pytest tests/unit/test_enclosure_solver.py
   pytest tests/unit/test_breaker_placer.py
   pytest -m regression  # 20/20 PASS 필수
   ```

### 중장기 계획
1. FIX-4 파이프라인 완전 통합
2. Supabase DB에 카탈로그 마이그레이션
3. API 엔드포인트 구현 (/v1/estimate, /v1/validate)
4. Evidence 시스템 구축

## 참고 링크
- **COREFILE 저장소**: https://github.com/kanno321-create/COREFILE
- **메인 프로젝트**: kis-estimator-main
- **Supabase**: NABERAL_PROJECT

## 메모
- **목업 금지 규칙** 엄수 필요
- **품질 게이트** 절대 타협 불가
- **CEO 서명 공식** (ai_estimation_core_v1.2.0.json) 변경 금지
- **회귀 테스트 20/20 PASS** 필수
