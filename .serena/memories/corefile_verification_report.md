# 절대코어파일 검증 리포트 (2025-10-01)

## ✅ 핵심 파일 검증 결과

### 📁 위치별 파일 분포

#### 1. core/rules/ (마스터 디렉토리)
```
✅ ai_estimation_core.json (마스터 파일)
✅ breaker_dimensions.json
✅ breaker_selection_guide_v1.00.json
✅ breaker_model_rules.json
✅ breaker_layout_rules.json
✅ accessories_v1.0.0.json (CEO 서명)
✅ [100+ 추가 JSON 파일]
```

#### 2. 핵심파일풀/KIS/Knowledge/packs/ (지식 베이스)
```
✅ ai_estimation_core_v1.2.0.json (최신 버전)
✅ enclosure_rules_v1.00.json
✅ enclosure_dimension_formula.json
✅ enclosure_dimension_rules.json
✅ width_rules.json
✅ accessories_v1.0.0.json
✅ IEC61439_tables.json
✅ KS_tables.json
✅ estimate_rag_bundle_v1.0.0.json
✅ [2000+ JSON 파일 - 많은 중복 버전 포함]
```

#### 3. 최상위
```
✅ 중요ai단가표의_2.0V.csv (643 라인 실제 데이터)
✅ README.md
```

## 📊 CLAUDE.md 명시 파일 매칭

### 차단기 지식 (4/4)
- ✅ breaker_dimensions.json
- ✅ breaker_selection_guide_v1.00.json
- ✅ breaker_model_rules.json
- ✅ breaker_layout_rules.json

### 외함 지식 (4/4)
- ✅ enclosure_rules_v1.00.json
- ✅ enclosure_dimension_formula.json
- ✅ enclosure_dimension_rules.json
- ✅ width_rules.json

### 부속자재 (4/4)
- ✅ accessories_v1.0.0.json (CEO 서명)
- ✅ accessory_rules.json
- ✅ accessory_layout_rules.json
- ✅ sub_material_bundles.json

### 표준 (2/2)
- ✅ IEC61439_tables.json
- ✅ KS_tables.json

### 가격 (1/1)
- ✅ 중요ai단가표의_2.0V.csv

### RAG (1/1)
- ✅ estimate_rag_bundle_v1.0.0.json

## 🔍 중복 파일 분석

### 문제점
1. **핵심 파일이 2곳에 존재**:
   - `core/rules/` (깨끗한 버전)
   - `핵심파일풀/KIS/Knowledge/packs/` (여러 버전)

2. **버전 네이밍 패턴**:
   ```
   breaker_critic.json
   breaker_critic__1.json
   breaker_critic__1__1.json
   breaker_critic_20250919T115850Z.json
   breaker_critic_20250919T115851Z.json (타임스탬프 버전)
   ```

3. **타임스탬프 파일 500+ 개**:
   - breaker_critic_[timestamp].json (매우 많음)
   - 2025-09-19 생성된 반복 버전들

### 권장 사항
- **사용할 디렉토리**: `core/rules/` (정리된 버전)
- **백업 용도**: `핵심파일풀/` (참조 및 버전 비교)

## 🎯 통합 우선순위

### Priority 1: 즉시 통합 필요
```
core/rules/ai_estimation_core.json
중요ai단가표의_2.0V.csv
core/rules/breaker_selection_guide_v1.00.json
core/rules/accessories_v1.0.0.json
핵심파일풀/KIS/Knowledge/packs/IEC61439_tables.json
핵심파일풀/KIS/Knowledge/packs/KS_tables.json
```

### Priority 2: 참조 데이터
```
core/catalog/breakers.csv
core/catalog/enclosures.csv
core/size/*.csv (LS, 상도 치수 테이블)
```

### Priority 3: RAG 준비
```
핵심파일풀/KIS/Knowledge/packs/*.json (최신 버전만)
estimate_rag_bundle_v1.0.0.json
```

## 📁 제안 통합 구조
```
kis-estimator-main/
├── data/
│   └── corefile/  (새로 생성)
│       ├── master/
│       │   └── ai_estimation_core.json
│       ├── pricebook/
│       │   └── 중요ai단가표_v2.0.csv
│       ├── rules/
│       │   ├── breaker_selection_guide_v1.00.json
│       │   ├── accessories_v1.0.0.json
│       │   ├── IEC61439_tables.json
│       │   └── KS_tables.json
│       └── catalog/
│           ├── breakers.csv
│           ├── enclosures.csv
│           └── size/
│               ├── LS_MCCB_dimensions.csv
│               └── Sangdo_MCCB_dimensions.csv
```

## ✅ 검증 완료
- **총 파일 확인**: 20+ 핵심 파일
- **CLAUDE.md 매칭**: 100% (모든 명시 파일 존재)
- **다음 단계 준비**: 통합 가능 상태
