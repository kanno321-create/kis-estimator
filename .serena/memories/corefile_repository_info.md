# COREFILE 저장소 정보

## 기본 정보
- **저장소 URL**: https://github.com/kanno321-create/COREFILE
- **생성 일자**: 2025-10-01 03:50 KST
- **저장소 타입**: Public
- **설명**: NABERAL KIS Estimator 핵심 파일 저장소 - FIX-4 엔진, 견적 공식, 자재 카탈로그

## 로컬 경로
```
C:\Users\PC\Desktop\절대코어파일\
```

## 통계
- **파일 수**: 12,980개
- **코드 라인**: 968,531줄
- **커밋 수**: 1 (Initial commit)

## 포함 내용

### 1. FIX-4 엔진 (core/engine/)
```python
# Stage 1: Enclosure Solver
enclosure_solver.py         # 외함 계산 (fit_score ≥ 0.90)

# Stage 2: Breaker Placer  
breaker_placer.py           # OR-Tools CP-SAT 배치
                            # 상평형 ≤ 4%, 간섭=0, 열=0

# Stage 2.1: Breaker Critic
breaker_critic.py           # 배치 검증 및 개선 권고

# Stage 3: Estimate Formatter
estimate_formatter.py       # openpyxl 네임드 레인지
                            # 수식 보존 100%

# Stage 4: Cover Tab
cover_tab_writer.py         # 표지 생성

# Stage 5: Doc Lint Guard
doc_lint_guard.py           # 최종 문서 검증
```

### 2. 비즈니스 규칙 (core/rules/, 핵심파일풀/KIS/Knowledge/packs/)
```json
// CEO 서명 필수 공식
ai_estimation_core_v1.2.0.json

// 부스바 계산
busbar_rules.json
{
  "main_busbar": "T × width × length (KG)",
  "default_price": 19500
}

// 외함 크기
enclosure_dimension_formula.json
{
  "W": {
    "100AF": 600,
    "125-250AF": 700,
    "400AF": 800,
    "600AF+": 900
  }
}

// 부자재
accessory_rules.json
accessory_layout_rules.json
```

### 3. 자재 카탈로그 (core/catalog/, 핵심파일풀/data/catalog/)
```csv
// breakers.csv
model,phase,current_a,width_unit,heat_w,price
BRK-100-A,A,100,1,50,120000

// enclosures.csv  
model,W,H,D,ip_rating,max_heat_w,slot_unit,price
ENCL-600,600,2000,400,IP55,1200,1,1500000

// MCCB 치수 (size/)
LS_Metasol_MCCB_dimensions_by_AF_and_poles.csv
Sangdo_MCCB_dimensions_by_AF_model_poles.csv
```

### 4. 통합 가격표 (core/pricebook/)
```csv
// pricebook.csv
item_key,field,price_value,currency,source_zip,source_path
default_price,default_price,19500,KRW,기본지식.zip,busbar_rules.json
```

## Git 클론 방법
```bash
# HTTPS
git clone https://github.com/kanno321-create/COREFILE.git

# SSH (설정된 경우)
git clone git@github.com:kanno321-create/COREFILE.git
```

## 메인 프로젝트 통합 방법

### 1. 엔진 코드 복사
```bash
cd /path/to/kis-estimator-main

# 엔진 디렉토리 생성 (없을 경우)
mkdir -p src/kis_estimator_core/engine

# COREFILE에서 엔진 복사
cp -r /path/to/COREFILE/core/engine/* src/kis_estimator_core/engine/
```

### 2. 규칙 파일 복사
```bash
# 규칙 디렉토리 생성
mkdir -p data/rules

# COREFILE에서 규칙 복사
cp -r /path/to/COREFILE/core/rules/* data/rules/
cp -r /path/to/COREFILE/핵심파일풀/KIS/Knowledge/packs/* data/rules/
```

### 3. 카탈로그 임포트
```bash
# 카탈로그 임포트 스크립트 실행
python scripts/import_catalog.py \
  --breakers /path/to/COREFILE/core/catalog/breakers.csv \
  --enclosures /path/to/COREFILE/core/catalog/enclosures.csv \
  --pricebook /path/to/COREFILE/core/pricebook/pricebook.csv
```

### 4. 의존성 설치
```bash
# pyproject.toml에 추가
poetry add ortools@^9.7.0
poetry add openpyxl@^3.1.0

# 또는 pip
pip install ortools>=9.7.0 openpyxl>=3.1.0
```

### 5. 테스트 실행
```bash
# 엔진 테스트
pytest tests/unit/test_enclosure_solver.py
pytest tests/unit/test_breaker_placer.py
pytest tests/unit/test_breaker_critic.py

# 회귀 테스트 (20/20 PASS 필수)
pytest -m regression
```

## 주의사항

### 🚫 절대 금지
1. **목업 테스트**: 실제 데이터만 사용
2. **공식 수정**: CEO 서명 공식 변경 금지
3. **품질 게이트 타협**: 기준 절대 준수

### ✅ 필수 사항
1. **fit_score ≥ 0.90**
2. **상평형 ≤ 4%**
3. **간섭/열 위반 = 0**
4. **회귀 테스트 20/20 PASS**

## 버전 관리
- **v1.2.0**: ai_estimation_core (CEO 서명, 2025-01-15)
- **Signature**: `SHA256:core_v120_certified_by_ceo_20250115`

## 관련 프로젝트
- **kis-estimator-main**: 메인 Estimator API
- **NABERAL_PROJECT**: Supabase 병렬 개발
