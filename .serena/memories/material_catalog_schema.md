# 자재 카탈로그 스키마

## 출처
`C:\Users\PC\Desktop\절대코어파일\핵심파일풀\data\catalog\`

## 브레이커 카탈로그 (breakers.csv)
```csv
컬럼: model, phase, current_a, width_unit, heat_w, price
예시:
- BRK-100-A, A, 100, 1, 50, 120000
- BRK-125-B, B, 125, 1, 60, 135000
- BRK-150-C, C, 150, 1, 70, 150000
- BRK-80-UNI, ALL, 80, 0.5, 40, 90000
```

### 필드 설명
- `model`: 브레이커 모델명
- `phase`: 상 (A/B/C/ALL)
- `current_a`: 정격 전류 (A)
- `width_unit`: 폭 단위 (배수)
- `heat_w`: 발열량 (W)
- `price`: 단가 (원)

## 외함 카탈로그 (enclosures.csv)
```csv
컬럼: model, W, H, D, ip_rating, max_heat_w, slot_unit, price
예시:
- ENCL-600, 600, 2000, 400, IP55, 1200, 1, 1500000
- ENCL-800, 800, 2200, 450, IP54, 1500, 1.2, 1750000
- ENCL-1000, 1000, 2200, 500, IP56, 1800, 1.5, 2100000
- ENCL-1200, 1200, 2400, 600, IP65, 2400, 2.0, 2600000
```

### 필드 설명
- `model`: 외함 모델명
- `W`, `H`, `D`: 폭/높이/깊이 (mm)
- `ip_rating`: IP 등급 (최소 IP44)
- `max_heat_w`: 최대 발열 허용치 (W)
- `slot_unit`: 슬롯 단위 (배수)
- `price`: 단가 (원)

## MCCB 치수 테이블 (size/)

### LS Metasol (LS_Metasol_MCCB_dimensions_by_AF_and_poles.csv)
```csv
컬럼: brand, series, af, poles, width_mm, height_mm, depth_mm
브랜드: LS
시리즈: METASOL
AF 범위: 50~800
극수: 3P, 4P
```

### 상도전기 (Sangdo_MCCB_dimensions_by_AF_model_poles.csv)
```csv
컬럼: brand, series, af, poles, width_mm, height_mm, depth_mm
브랜드: Sangdo
AF 범위: 다양
극수: 3P, 4P
```

## 가격표 통합 (pricebook/pricebook.csv)
```csv
컬럼: item_key, field, price_value, currency, source_zip, source_path, json_path
통합 가격 정보:
- 부스바 기본가: 19,500원
- 브레이커: 3,300원 ~ 400,000원
- 외함: 22,000원 ~ 125,000원
- 부자재: 800원 ~ 12,000원
```

## 데이터 위치
- **브레이커**: `data/catalog/breakers.csv`
- **외함**: `data/catalog/enclosures.csv`
- **MCCB 치수**: `data/catalog/size/`
- **통합 가격표**: `data/pricebook/pricebook.csv`
