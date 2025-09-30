# 파서 규칙 문서 (Parsing Rules)

## 개요
KIS Estimator 전기 패널 견적서 파서 시스템

**현재 상태**: 프로토타입 (10/10 합성 샘플)
**프로덕션 요구사항**: 60개 실제 샘플 필수

---

## 핵심 규칙

### 1. 탭 2개 규칙 (`TAB_RULE_2`)
- **적용**: Excel 파일에 탭이 정확히 2개인 경우
- **동작**: 1번, 2번 탭 모두 분석
- **이유**: 고압반이 없으며, MCC(Motor Control Center) 포함 가능

### 2. 탭 3개 이상 규칙 (`TAB_RULE_3PLUS`)
- **적용**: Excel 파일에 탭이 3개 이상인 경우
- **동작**: 2번 탭 제외 (고압반), 1번 + 3번 이후 탭만 분석
- **이유**: 2번 탭은 항상 고압반으로 가정, 견적 범위 제외

### 3. 분전반 분할 규칙 (`PANEL_SPLIT_SUBTOTAL`)
- **적용**: 한 탭 내에 여러 분전반이 있는 경우
- **트리거**: '소계' 또는 '합계' 키워드 발견
- **동작**:
  - 소계/합계 행을 현재 분전반의 종료로 판단
  - 다음 1~2행 내 공백 확인
  - 공백 후 첫 비공백 행을 새 분전반 시작으로 판단

### 4. Fuzzy 매칭 규칙 (`FUZZY_KEYWORD_MATCH`)
- **적용**: OCR 오탈자 허용
- **허용 키워드**:
  - '소계' → '소게', '소젤' (편집거리 1)
  - '합계' → '합게', '할계' (편집거리 1)

### 5. 공백 허용 규칙 (`SPACING_TOLERANCE_PM2`)
- **적용**: 분전반 구분 시 공백 행 개수 변이 허용
- **허용 범위**: ±1~2행
- **이유**: 실제 견적서 포맷 다양성

---

## API 엔드포인트

### POST /v1/estimate/parse
파일 파싱 및 분전반 정보 추출

**요청**:
```json
{
  "source": "upload",
  "pathOrFile": "/path/to/file.xlsx",
  "options": {}
}
```

**응답**:
```json
{
  "panels": [
    {
      "tab": "저압반1",
      "tab_index": 0,
      "panel_id": "TAB1_PANEL1",
      "rows_span": [0, 10],
      "items": [...]
    }
  ],
  "evidence": {
    "traceId": "...",
    "rules_applied": [...],
    "warnings": [],
    "tabs_detected": 2,
    "tabs_analyzed": [0, 1],
    "panels_count": 1,
    "duration_ms": 150
  }
}
```

### POST /v1/estimate/parse/validate
파싱 결과 검증

**요청**: 파싱 결과 (panels + evidence)
**응답**:
```json
{
  "status": "OK",
  "reasons": [],
  "edges_hit": ["FUZZY_KEYWORD_MATCH"]
}
```

---

## Zero-Mock 준수

✅ **모든 테스트는 실제 파일 I/O 사용**
- 합성 샘플 10개: 실제 xlsx/csv 파일
- 파싱: openpyxl/csv 라이브러리로 실제 읽기
- 검증: 실제 데이터 구조 확인
- **목업/더미/시뮬레이션 일절 없음**

---

## 프로덕션 게이트

**차단 조건**: `count(fixtures) < 60`

```bash
bash scripts/parser_gate.sh
# Exit 68: 샘플 부족 (배포 차단)
# Exit 0: 60+ 샘플 & 테스트 통과 (배포 승인)
```

**현재 상태**: 🔒 **BLOCKED** (10/60 샘플)

**Action Required**:
1. 60개 실제 견적서 확보 (xlsx/csv)
2. `tests/parser/fixtures/` 에 합성 샘플 교체
3. 프로덕션 게이트 재실행

---

## 성능 목표

| 지표 | 목표 | 현재 (10샘플) |
|------|------|---------------|
| p95 응답시간 | ≤ 200ms | ~130ms ✅ |
| 메모리 사용 | 안정 | 안정 ✅ |
| 회귀 테스트 | 10/10 PASS | 10/10 ✅ |

---

## 한계 및 향후 개선

### 현재 한계
1. **합성 샘플**: 실제 견적서 특성 반영 불완전
2. **헤더 다양성**: 고정 컬럼 순서 가정
3. **복잡한 레이아웃**: 병합셀, 중첩 구조 미지원

### 60개 실샘플 확보 시
- ✅ 실제 포맷 변이 학습
- ✅ 엣지 케이스 완벽 커버
- ✅ 프로덕션 배포 승인

---

## 테스트 실행

```bash
# 합성 샘플 생성 (이미 완료)
python tools/generate_parser_fixtures.py --out tests/parser/fixtures --n 10

# E2E 테스트
pytest tests/parser/test_parser_e2e.py -v

# 프로덕션 게이트 (현재 차단됨)
bash scripts/parser_gate.sh
```

---

**문서 버전**: 1.0
**작성일**: 2025-09-30
**상태**: Prototype (10/10) → 60/60 for Production