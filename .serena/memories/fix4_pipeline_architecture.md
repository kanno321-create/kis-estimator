# FIX-4 Pipeline Architecture

## Overview
The FIX-4 pipeline is the core processing flow for KIS Estimator. All estimates MUST go through these 5 stages in order.

## Pipeline Stages

### Stage 1: Enclosure (외함 계산)
**Module**: `src/kis_estimator_core/engine/enclosure_solver.py`

**Purpose**: Determine optimal enclosure size for given breakers

**Quality Gates**:
- fit_score ≥ 0.90
- IP rating ≥ 44
- Door clearance ≥ 30mm

**Validation**:
```python
result = enclosure.solve(breakers)
assert result.fit_score >= 0.90
assert result.ip_rating >= 44
assert result.door_clearance >= 30
```

---

### Stage 2: Breaker (브레이커 배치)
**Module**: `src/kis_estimator_core/engine/breaker_placer.py`

**Purpose**: Optimize breaker placement using OR-Tools CP-SAT solver

**Technology**: 
- Primary: OR-Tools CP-SAT solver
- Fallback: Heuristic algorithm (if OR-Tools unavailable)

**Quality Gates**:
- Phase imbalance ≤ 4%
- Interference violations = 0
- Thermal violations = 0

**Auto-Fallback Pattern**:
```python
try:
    from ortools.sat.python import cp_model
    # Use CP-SAT solver
    result = solve_with_cpsat(breakers, panel)
except ImportError:
    # Fallback to heuristic
    from stubs.heuristic_placer import place_breakers_heuristic
    result = place_breakers_heuristic(breakers, panel)
```

---

### Stage 2.1: Critic (배치 검증)
**Module**: `src/kis_estimator_core/engine/breaker_critic.py`

**Purpose**: Validate placement results and suggest improvements

**Outputs**:
- Violations: Critical issues that must be fixed
- Warnings: Issues that should be addressed
- Recommendations: Optimization suggestions

**Validation Categories**:
- Clearance violations
- Thermal constraints
- Phase balance
- Safety requirements

---

### Stage 3: Format (문서 포맷)
**Module**: `src/kis_estimator_core/engine/estimate_formatter.py`

**Purpose**: Generate Excel/PDF estimate documents

**Quality Gates**:
- Formula preservation = 100%
- Named range integrity = 100%

**Requirements**:
- Preserve all Excel formulas
- Maintain named ranges
- Apply company branding
- Include all metadata

---

### Stage 4: Cover (표지 생성)
**Module**: `src/kis_estimator_core/engine/cover_tab_writer.py`

**Purpose**: Generate cover page with metadata

**Quality Gates**:
- Cover rules compliance = 100%

**Cover Elements**:
- Project information
- Client details
- Estimate summary
- Approval signatures
- Company branding

---

### Stage 5: Doc Lint (최종 검증)
**Module**: `src/kis_estimator_core/engine/doc_lint_guard.py`

**Purpose**: Final document quality validation

**Quality Gates**:
- Lint errors = 0

**Checks**:
- Document structure integrity
- Data consistency
- Formula correctness
- Formatting compliance
- Business rule adherence

---

## Performance Targets

| Operation | Target | Maximum |
|-----------|--------|---------|
| Breaker placement (100 units) | <1s | 30s |
| Enclosure calculation | <500ms | 1s |
| Phase balance calculation | <100ms | 500ms |
| API response (P95) | <200ms | 500ms |
| Health check | <50ms | 100ms |

## Evidence Collection

Each stage must generate evidence artifacts:

```
/spec_kit/evidence/{timestamp}/
├── stage1_enclosure/
│   ├── input.json
│   ├── output.json
│   ├── metrics.json
│   └── validation.json
├── stage2_breaker/
│   ├── input.json
│   ├── output.json
│   ├── placement.svg
│   └── metrics.json
├── stage21_critic/
│   └── validation.json
├── stage3_format/
│   └── document.xlsx
├── stage4_cover/
│   └── cover.pdf
└── stage5_lint/
    └── validation.json
```

## Tab/Panel Processing Rules

### Excel Tab Parsing
- **2 tabs**: Analyze tabs 1 and 2 (no high-voltage panel)
- **3+ tabs**: Tab 2 is high-voltage (ignore), analyze tabs 1 and 3
- **Subtotal/Total + 1-2 blank rows**: Indicates new panel block
- **Each block**: Generate separate estimate ID with cross-links

## Integration Pattern

```python
def process_estimate(input_data: EstimateInput) -> EstimateOutput:
    # Stage 1: Enclosure
    enclosure = enclosure_solver.solve(input_data.breakers)
    assert enclosure.fit_score >= 0.90
    
    # Stage 2: Breaker Placement
    placement = breaker_placer.place(enclosure, input_data.breakers)
    assert placement.phase_imbalance <= 0.04
    assert placement.violations == 0
    
    # Stage 2.1: Critic
    critique = breaker_critic.validate(placement)
    if critique.has_errors:
        raise ValidationError(critique.errors)
    
    # Stage 3: Format
    document = estimate_formatter.format(placement, template)
    assert document.formula_preservation == 1.0
    
    # Stage 4: Cover
    cover = cover_tab_writer.generate(document, metadata)
    assert cover.compliance == 1.0
    
    # Stage 5: Doc Lint
    lint_result = doc_lint_guard.validate(document)
    assert lint_result.errors == 0
    
    return EstimateOutput(
        document=document,
        evidence=collect_evidence_pack()
    )
```