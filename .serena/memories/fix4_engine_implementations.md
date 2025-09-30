# FIX-4 파이프라인 엔진 구현 코드

## 출처
`C:\Users\PC\Desktop\절대코어파일\core\engine\`

## Stage 1: Enclosure Solver (enclosure_solver.py)

### 핵심 로직
```python
def calculate_enclosure(work_dir: Path, rules_dir: Path) -> dict:
    """외함 계산 with 제약조건"""
    
    # 입력 스펙 로드
    - zones: 구역별 디바이스 수, IP 등급 요구사항
    - total_devices: 전체 디바이스 합계
    
    # 최소 크기 계산
    - min_width = max(600, total_devices * 25)  # 디바이스당 25mm
    - min_height = max(800, total_devices * 35)  # 디바이스당 35mm
    
    # IP 등급 결정
    - 모든 존 중 최대 IP 등급 선택
    
    # SKU 매칭 및 fit_score 계산
    - 3개 후보 생성 (기본, W+100, H+100)
    - fit_score 기준으로 정렬
    - 최고 fit_score SKU 선택
    
    # 미터기 옵션
    - meter_window: 미터기 존 있으면 true
    - ct_compartment: CT 구획 필요 시 true
    - inspection_window: 항상 true
    
    # 검증
    - fit_score < 0.93 → violation
    - constraints_satisfied = false
```

### 품질 게이트
- **fit_score ≥ 0.93** (필수)
- IP 등급 ≥ 요구사항
- 미터 윈도우/CT 구획 옵션 정확성

### Evidence 생성
```python
evidence_data = {
    "fit_score": result["selected_sku"]["fit_score"],
    "ip_rating": result["requirements"]["ip_rating"],
    "zones": len(result["zones"]),
    "violations": len(result["violations"])
}
```

## Stage 2: Breaker Placer (breaker_placer.py)

### 핵심 로직
```python
class BreakerSpec:
    id, rating_a, width_mm, height_mm, phase, heat_w

class PanelSpec:
    width_mm, height_mm, rows, clearance_mm, max_row_heat_w

class PlacementResult:
    slots, phase_loads, phase_distribution
    phase_imbalance_pct  # 핵심 지표
    total_heat_w
    clearances_violation  # 0이어야 함
    thermal_violation     # 0이어야 함
    optimization_method   # "cp_sat" or "heuristic"
```

### OR-Tools CP-SAT 솔버
```python
def _solve_with_cp_sat(breakers, panel, seed):
    """OR-Tools CP-SAT로 최적 배치"""
    
    # 변수 정의
    - phase_vars: 각 브레이커의 상 할당 (0=L1, 1=L2, 2=L3)
    - 1상: L1/L2/L3 중 선택
    - 3상: 모든 상 사용
    - 2상: L1-L2 사용
    
    # 제약조건
    - 상평형: max_load - min_load 최소화
    - 발열: 행당 max_row_heat_w 이하
    - 간섭: clearance_mm 이상 간격
    
    # 목적함수
    - 상평형 최소화 우선
    - 발열 분산 차순위
```

### 휴리스틱 폴백
```python
def _solve_with_heuristic_fallback(breakers, panel, seed):
    """OR-Tools 없을 때 대체 알고리즘"""
    
    # 라운드 로빈 방식
    - 브레이커를 전류 기준 정렬
    - 순차적으로 L1 → L2 → L3 배치
    - 행별 발열 체크
    - 간섭 체크 (50mm 간격)
```

### 품질 게이트
- **상평형 ≤ 4%** (필수)
- **간섭 위반 = 0** (필수)
- **열 위반 = 0** (필수)
- 발열: 행당 650W, 패널 전체 2500W 이하

## Stage 2.1: Breaker Critic (breaker_critic.py)

### 임계값 상수
```python
MAX_LIMITS = {
    "phase_imbalance_pct": 4.0,
    "clearances_violation": 0,
    "thermal_violation": 0,
    "row_heat_w": 650,
    "panel_heat_w": 2500,
    "min_clearance_mm": 50
}
```

### 검증 로직
```python
def critique_placement(work_dir):
    """배치 결과 검증 및 위반 사항 보고"""
    
    violations = []
    warnings = []
    
    # 1. 상평형 체크
    if imbalance > 4.0:
        violations.append({
            "type": "phase_imbalance",
            "severity": "critical",
            "value": imbalance,
            "limit": 4.0,
            "recommendation": "단상 브레이커 재분배"
        })
    elif imbalance > 3.5:  # 87.5% 임계값
        warnings.append("상평형 임계값 근접")
    
    # 2. 간섭 체크
    if clearance_violations > 0:
        violations.append({
            "type": "clearance",
            "count": clearance_violations,
            "min_required_mm": 50
        })
    
    # 3. 발열 체크
    if thermal_violations > 0:
        violations.append({
            "type": "thermal",
            "max_row_heat_w": 650
        })
    
    # 4. 전체 패널 발열
    if total_heat > 2500:
        violations.append({
            "type": "panel_thermal",
            "limit": 2500
        })
    
    return {
        "pass": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
        "recommendations": [...]
    }
```

## Stage 3: Estimate Formatter (estimate_formatter.py)

### openpyxl 통합
```python
def _apply_named_ranges_with_openpyxl(workbook_path, range_specs, estimate_data):
    """네임드 레인지 적용"""
    
    wb = openpyxl.load_workbook(workbook_path)
    
    # 기존 네임드 레인지 제거
    # 새 네임드 레인지 적용
    
    # 필수 네임드 레인지
    - Project.Name → Cover!B3
    - Project.Client → Cover!B4
    - Project.Date → Cover!B5
    - Project.Number → Cover!B6
    - Totals.Net → Estimate!H52
    - Totals.VAT → Estimate!H53
    - Totals.Total → Estimate!H54
    - Items.Start → Estimate!A10
    - Items.End → Estimate!H50
    
    wb.save(workbook_path)
```

### 품질 게이트
- **수식 보존 = 100%**
- **네임드 레인지 손상 = 0**

## Stage 4: Cover Tab (cover_tab_writer.py)

### 표지 데이터 생성
```python
cover_data = {
    "project": {
        "title": "...",
        "client": "...",
        "date": "...",
        "number": "..."
    },
    "financial": {
        "net": ...,
        "vat": ...,
        "total": ...
    },
    "signature": {
        "prepared_by": "...",
        "approved_by": "...",
        "date": "..."
    },
    "branding": {
        "logo_path": "...",
        "company_info": "..."
    }
}
```

## Stage 5: Doc Lint Guard (doc_lint_guard.py)

### 필수 필드 검증
```python
REQUIRED_FIELDS = {
    "cover": [
        "cover_data.project.title",
        "cover_data.project.client",
        "cover_data.financial.total",
        "cover_data.signature.prepared_by"
    ],
    "placement": [
        "phase_imbalance_pct",
        "clearances_violation",
        "thermal_violation"
    ],
    "enclosure": [
        "selected_sku.sku",
        "selected_sku.fit_score"
    ],
    "format": [
        "named_ranges.total",
        "format_lint.errors"
    ]
}
```

### 문서별 검증
```python
def lint_documents(work_dir):
    """최종 품질 검사"""
    
    # 문서 존재 확인
    documents = [enclosure, placement, critic, format, cover, spatial]
    
    # 필수 필드 확인
    for doc in documents:
        check_required_fields(doc)
    
    # 문서별 검증
    - enclosure: fit_score ≥ 0.93
    - placement: phase_imbalance ≤ 4%
    - placement: clearances_violation = 0
    - placement: thermal_violation = 0
    - format: named_ranges 무결성
    - cover: 필수 정보 완전성
    
    return {
        "pass": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
```

## 엔진 파일 목록
```
core/engine/
├── enclosure_solver.py          # Stage 1: 외함 계산
├── breaker_placer.py             # Stage 2: 브레이커 배치 (OR-Tools)
├── breaker_critic.py             # Stage 2.1: 배치 검증
├── estimate_formatter.py         # Stage 3: 문서 포맷 (openpyxl)
├── cover_tab_writer.py           # Stage 4: 표지 생성
├── doc_lint_guard.py             # Stage 5: 최종 검증
├── estimate_engine.py            # 전체 파이프라인 오케스트레이터
├── estimate_policy.py            # 정책 및 제약조건
└── _util_io.py                   # 공통 유틸리티
```

## 통합 방법
1. 현재 프로젝트의 `src/kis_estimator_core/engine/` 폴더로 복사
2. `_util_io.py` 공통 모듈 통합
3. OR-Tools 의존성 추가: `ortools>=9.7.0`
4. openpyxl 의존성 추가: `openpyxl>=3.1.0`
5. 테스트 실행하여 검증
