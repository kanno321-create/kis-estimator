# COREFILE - KIS Estimator 핵심 지식 베이스

**통합 날짜**: 2025-10-01
**출처**: C:\Users\PC\Desktop\절대코어파일\
**버전**: v1.2.0

---

## 📁 디렉토리 구조

```
data/corefile/
├── master/
│   └── ai_estimation_core.json (133KB, 5633 lines)
├── rules/
│   ├── accessories_v1.0.0.json (CEO 서명)
│   ├── breaker_selection_guide_v1.00.json
│   ├── IEC61439_tables.json (국제 표준)
│   └── KS_tables.json (한국 표준)
└── pricebook/
    └── 중요ai단가표의_2.0V.csv (14MB, 643 데이터 라인)
```

---

## 📊 ai_estimation_core.json 구조

### 전체 구조 (5633 lines)

```json
{
  "meta": {           // Line 1-17
    "version": "1.2.0",
    "locale": "ko-KR",
    "units": {
      "length": "mm",
      "current": "A",
      "mass": "kg",
      "currency": "KRW"
    }
  },

  "pipeline": {       // Line 18-28
    "order": [
      "accessories",
      "drawing_parse",
      "layout",
      "enclosure",
      "mapping",
      "estimation"
    ]
  },

  "merge_policy": {   // Line 29-37
    // 중복 해결 정책
  },

  "catalog": {        // Line 38-4963
    "accessories": {  // Line 39-176
      // 마그네트, 타이머, 미터기 등 (138 lines)
    },
    "breakers": {     // Line 177-2569
      // 차단기 카탈로그 (2393 lines)
      // 500+ 모델 (MCCB, ELB)
    },
    "enclosures": {   // Line 2570-4963
      // 외함 카탈로그 (2394 lines)
      // 100+ HDS 모델
    }
  },

  "rules": {          // Line 4964-5632
    "bundles": [      // Line 4965-5011
      // 마그네트 동반자재 규칙 (MANDATORY)
    ],
    "drawing": {      // Line 5012-5027
      // 도면 분석 규칙
    },
    "enclosure": {    // Line 5028-5108
      // 외함 크기 계산 공식
      // H = A + B + C + D + E
    },
    "breaker_selection": { // Line 5109-5619
      // 차단기 선택 규칙
      // 경제형 우선, 소형 특수 규칙
    },
    "output": {       // Line 5620-5631
      "ordering": [
        "ENCLOSURE",
        "MAIN_BREAKER",
        "BRANCH_BREAKERS",
        "ACCESSORIES_REQUIRED",
        "ACCESSORIES_OPTIONAL",
        "BUSBAR",
        "SUPPORTS",
        "COSTS",
        "TOTALS"
      ]
    }
  }
}
```

---

## 🔑 핵심 비즈니스 규칙

### 1. 마그네트 동반자재 (MANDATORY)
**규칙 ID**: BND_MAGNET_BASE
**적용 대상**: 모든 마그네트 컨택터

**자동 추가 항목**:
```
- FUSE_HOLDER: 1EA
- TERMINAL_BLOCK_600V: 3EA (중요: 3개!)
- PVC_DUCT_40mm: 2EA (상단 + 하단)
- CABLE_WIRE: 2EA (중요: 2개!)
- 인건비: 20,000원
```

### 2. 차단기 선택 우선순위
1. **경제형 우선** (37kA, 저렴)
2. **표준형 대체** (50kA, 경제형 부재 시)
3. **소형 특수 규칙**:
   - 누전 2P 20/30A → SIE-32 (소형)
   - 배선용 2P 20/30A → SIB-32 (소형)

### 3. 외함 높이 계산 공식
```
H = A + B + C + D + E

A: 상단 여유 (메인 프레임별)
B: 메인-분기 간격 (30mm)
C: 분기 차단기 총 높이
D: 하단 여유 (150-250mm)
E: 부속자재 여유 (PVC 덕트 등)
```

---

## 📋 중요ai단가표_2.0V.csv 구조

### 파일 정보
- **크기**: 14MB
- **실제 데이터**: 643 lines (헤더 1 + 데이터 642)
- **공백 라인**: 644 ~ 1,048,407 lines

### 데이터 구성
```
총 품목: 642개
- MCCB (배선용차단기): 276 모델
  - 경제형: 133 모델
  - 표준형: 143 모델
- ELB (누전차단기): 200 모델
  - 경제형: 96 모델
  - 표준형: 104 모델
- 외함: 122 품목
- 브랜드: 상도(230), LS(246), 한국산업(144)
```

### CSV 컬럼
```csv
카테고리, 브랜드, 시리즈/형식, 모델명, 재질/극수, 규격/전류, 차단용량(kA), 견적가, 프레임(AF)
```

---

## 🎯 사용 방법

### Python에서 로드
```python
import json
from pathlib import Path
import pandas as pd

# 마스터 파일 로드
with open("data/corefile/master/ai_estimation_core.json", "r", encoding="utf-8") as f:
    core = json.load(f)

# 단가표 로드 (실제 데이터만)
df = pd.read_csv("data/corefile/pricebook/중요ai단가표의_2.0V.csv", nrows=643)

# 규칙 파일 로드
with open("data/corefile/rules/accessories_v1.0.0.json", "r", encoding="utf-8") as f:
    accessories = json.load(f)

# 차단기 카탈로그 추출
breakers = core["catalog"]["breakers"]
print(f"차단기 모델 수: {len(breakers['items'])}")

# 외함 카탈로그 추출
enclosures = core["catalog"]["enclosures"]["standard"]["items"]
print(f"외함 모델 수: {len(enclosures)}")
```

---

## 🔄 업데이트 이력

### v1.2.0 (2025-10-01)
- ✅ 절대코어파일 전체 통합
- ✅ ai_estimation_core.json 구조 매핑 완료
- ✅ 핵심 규칙 파일 선별 복사
- ✅ 단가표 CSV 검증 및 통합

---

## ⚠️ 주의사항

1. **중복 파일 관리**:
   - 원본 위치: `C:\Users\PC\Desktop\절대코어파일\`
   - 백업: `핵심파일풀/` (2000+ 중복 버전 포함)
   - **이 디렉토리 사용**: 정리된 최신 버전만 포함

2. **단가표 CSV**:
   - 실제 데이터는 643 lines만
   - 나머지는 공백 (무시 필요)

3. **파일 인코딩**:
   - 모든 JSON: UTF-8
   - CSV: UTF-8 with BOM

---

## 📚 관련 문서

- **프로젝트 가이드**: `CLAUDE.md`
- **완전 지식 맵**: `.serena/memories/COMPLETE_KNOWLEDGE_MAP_FOR_RAG.md`
- **검증 리포트**: `.serena/memories/corefile_verification_report.md`

---

**이 지식 베이스는 NABERAL KIS Estimator 시스템의 핵심 자산입니다.**
**수정 시 반드시 버전 관리 및 백업을 유지하세요.**
