# COREFILE - KIS Estimator 핵심 파일 저장소

## 📦 개요
NABERAL KIS Estimator 프로젝트의 핵심 비즈니스 로직, 자재 카탈로그, 견적 공식이 포함된 저장소입니다.

## 📂 디렉토리 구조

### 📁 core/
FIX-4 파이프라인 엔진 구현 코드 (Python)

```
core/
├── engine/                      # FIX-4 파이프라인 구현
│   ├── enclosure_solver.py     # Stage 1: 외함 계산
│   ├── breaker_placer.py        # Stage 2: 브레이커 배치 (OR-Tools)
│   ├── breaker_critic.py        # Stage 2.1: 배치 검증
│   ├── estimate_formatter.py    # Stage 3: 문서 포맷 (openpyxl)
│   ├── cover_tab_writer.py      # Stage 4: 표지 생성
│   └── doc_lint_guard.py        # Stage 5: 최종 검증
├── catalog/                     # 자재 카탈로그 (CSV)
│   ├── breakers.csv
│   └── enclosures.csv
├── rules/                       # 비즈니스 규칙 (JSON/YAML)
├── size/                        # MCCB 치수 테이블
└── pricebook/                   # 통합 가격표
```

### 📁 핵심파일풀/
견적 규칙, 자재 스펙, 비즈니스 로직이 포함된 지식 베이스

```
핵심파일풀/
├── KIS/Knowledge/packs/         # 견적 규칙 (JSON)
│   ├── ai_estimation_core_v1.2.0.json
│   ├── busbar_rules.json
│   ├── enclosure_dimension_formula.json
│   ├── accessory_rules.json
│   └── ...
├── data/
│   ├── catalog/                 # 자재 카탈로그
│   │   ├── breakers.csv
│   │   ├── enclosures.csv
│   │   └── size/                # MCCB 치수 (LS/상도전기)
│   └── pricebook/               # 통합 가격표
│       └── pricebook.csv
├── docs/                        # 운영 정책 문서
│   └── Operations.md
└── README.txt
```

## 🎯 핵심 내용

### 1. 견적 공식 (ai_estimation_core_v1.2.0.json)
- **PVC 커버 비용**: `(W × H) / 90000 × 12000 KRW`
- **도장 면적**: `2 × (W×H + W×D + H×D)`
- **공간 활용률**: `used_volume / total_enclosure_volume` (최대 0.85)
- **인건비**: 35,000원/시간 (관리비 15%, 자재 마크업 12%)

### 2. 외함 크기 공식
- **폭(W)**: 100AF=600mm, 125-250AF=700mm, 400AF=800mm, 600AF+=900mm
- **높이(H)**: 브레이커행당 100mm, 마그네트행당 70mm, 단자대행당 50mm
- **깊이(D)**: 기본 200mm, PBL 포함 시 250mm

### 3. 부스바 계산
- **공식**: `T × width × length` (KG)
- **기본 단가**: 19,500원/KG

### 4. 품질 게이트
| 단계 | 지표 | 기준 |
|------|------|------|
| Enclosure | fit_score | ≥ 0.90 |
| Breaker | 상평형 | ≤ 4% |
| Breaker | 간섭 위반 | = 0 |
| Breaker | 열 위반 | = 0 |
| Format | 수식 보존 | = 100% |
| Doc Lint | 오류 | = 0 |

## 🔧 기술 스택
- **언어**: Python 3.11+
- **최적화**: OR-Tools CP-SAT 솔버 (폴백: 휴리스틱)
- **문서**: openpyxl (Excel 네임드 레인지)
- **데이터**: CSV, JSON, YAML

## 📚 자재 카탈로그

### 브레이커 (breakers.csv)
- `model`: 브레이커 모델명
- `phase`: 상 (A/B/C/ALL)
- `current_a`: 정격 전류 (A)
- `width_unit`: 폭 단위 (배수)
- `heat_w`: 발열량 (W)
- `price`: 단가 (원)

### 외함 (enclosures.csv)
- `model`: 외함 모델명
- `W`, `H`, `D`: 폭/높이/깊이 (mm)
- `ip_rating`: IP 등급 (최소 IP44)
- `max_heat_w`: 최대 발열 허용치 (W)
- `slot_unit`: 슬롯 단위 (배수)
- `price`: 단가 (원)

### MCCB 치수 테이블
- **LS Metasol**: AF 50~800, 3P/4P
- **상도전기**: 다양한 AF, 3P/4P

## 🚀 사용 방법

### 1. 메인 프로젝트에 통합
```bash
# core 엔진 코드 복사
cp -r core/engine/* /path/to/kis-estimator/src/kis_estimator_core/engine/

# 자재 카탈로그 임포트
python scripts/import_catalog.py --source core/catalog/
```

### 2. 의존성 설치
```bash
pip install ortools>=9.7.0 openpyxl>=3.1.0
```

### 3. 테스트 실행
```bash
pytest tests/unit/test_enclosure_solver.py
pytest tests/unit/test_breaker_placer.py
```

## 📊 데이터 무결성
- **생성 시간**: 2025-09-30 18:33~18:38 UTC
- **SHA256 체크섬**: `manifests/SHA256SUMS.txt` 참조
- **인벤토리**: `manifests/inventory.json` 참조

## ⚠️ 중요 주의사항

### 🚫 절대 규칙
- **목업(MOCKUP) 절대 금지**: 실제 테스트만 허용
- **수식 보존 100%**: Excel 네임드 레인지 손상 금지
- **품질 게이트 필수**: 회귀 테스트 20/20 통과 필수

### 🔒 보안
- **키/토큰 유출 검사 필수**
- **입력 검증 100% 커버리지**
- **감사 로그 모든 변경사항 기록**

## 📝 버전 관리
- **v1.2.0**: ai_estimation_core 최신 버전 (CEO 서명 필수)
- **Signature**: `SHA256:core_v120_certified_by_ceo_20250115`

## 🔗 관련 프로젝트
- **kis-estimator-main**: 메인 Estimator API 프로젝트
- **NABERAL_PROJECT**: Supabase 기반 병렬 개발 환경

---
*이 저장소는 NABERAL KIS Estimator의 핵심 자산입니다.*
*무단 수정 및 배포를 금지합니다.*
