# Parser Implementation Patterns & Best Practices

**Context**: KIS Estimator Parser Service
**Date**: 2025-10-01

---

## 🏗️ Architecture Patterns

### 1. Rules Engine Separation

**Pattern**: Separate rules engine from service layer
```python
# Rules Engine (parser_rules.py)
class ParserRules:
    def detect_tab_count_and_strategy(self, tab_count: int)
    def find_panel_boundaries(self, rows: List[List[str]])
    def get_rules_applied(self) -> List[Dict]
    
# Service Layer (parser_service.py)
class ParserService:
    def __init__(self):
        self.rules_engine = ParserRules()
    
    def parse_file(self, file_path: str) -> Dict
```

**Benefits**:
- Clear separation of concerns
- Testable rules in isolation
- Evidence collection at rule level
- Service orchestrates rules + I/O

### 2. Evidence-First Design

**Pattern**: Every operation produces evidence
```python
{
    "traceId": "uuid",
    "rules_applied": [
        {"rule_id": "TAB_RULE_2", "span": [0, 1], "reason": "..."}
    ],
    "warnings": [],
    "duration_ms": 150
}
```

**Implementation**:
- Rules engine collects evidence during execution
- Service adds performance metrics
- API routes include traceId in responses
- Evidence enables debugging and auditing

### 3. Zero-Mock Testing Strategy

**Pattern**: Real file I/O, no mocking
```python
# DON'T: Mock file operations
@patch('openpyxl.load_workbook')
def test_parse(mock_load):
    mock_load.return_value = fake_workbook
    
# DO: Use real files
def test_parse():
    result = parser_service.parse_file("tests/parser/fixtures/sample.xlsx")
    assert len(result["panels"]) >= 1
```

**Benefits**:
- Tests validate actual I/O behavior
- Catches file format issues
- No mock/real divergence
- Confidence in production behavior

---

## 🧪 Testing Patterns

### 1. Test Organization

**Structure**:
```
tests/parser/
├── test_parser_rules.py    # Unit tests (18 cases)
├── test_parser_e2e.py       # E2E tests (10 cases)
├── fixtures/                # Real test data
│   ├── 01_2tab_simple.xlsx
│   ├── ...
│   └── manifest.json
└── conftest.py              # Shared fixtures
```

**Pattern**: Separate unit vs. E2E
- Unit tests: Test rules engine methods in isolation
- E2E tests: Full file → parse → validate flow
- Fixtures: Real files, organized by test case

### 2. Parametric E2E Tests

**Pattern**: Data-driven E2E tests
```python
@pytest.fixture
def fixtures_dir():
    return Path("tests/parser/fixtures")

def test_01_2tab_simple(fixtures_dir):
    result = parser_service.parse_file(str(fixtures_dir / "01_2tab_simple.xlsx"))
    assert len(result["panels"]) >= 1
```

**Future Enhancement**: Manifest-driven parametrization
```python
@pytest.mark.parametrize("sample", load_manifest())
def test_real_sample(sample):
    result = parser_service.parse_file(sample["file"])
    assert result["evidence"]["status"] == "OK"
```

### 3. Performance Testing Integration

**Pattern**: Assert performance targets in tests
```python
def test_performance(fixtures_dir):
    result = parser_service.parse_file(str(fixtures_dir / "sample.xlsx"))
    assert result["evidence"]["duration_ms"] < 200  # p95 target
```

---

## 🔍 Rule Engine Patterns

### 1. Stateful Evidence Collection

**Pattern**: Rules engine maintains state
```python
class ParserRules:
    def __init__(self):
        self.rules_applied: List[RuleApplied] = []
    
    def detect_tab_count_and_strategy(self, tab_count: int):
        # Apply rule logic
        self.rules_applied.append(RuleApplied(...))
        return result
    
    def clear_rules(self):
        self.rules_applied.clear()
```

**Usage**: Service calls `clear_rules()` per file

### 2. Fuzzy Matching for OCR Tolerance

**Pattern**: Edit distance for typo tolerance
```python
SUBTOTAL_KEYWORDS = ["소계", "소게", "소젤"]  # Edit distance 1

def _is_subtotal_or_total(self, text: str) -> bool:
    for keyword in self.SUBTOTAL_KEYWORDS:
        if keyword in text_lower:
            if keyword in ["소게", "소젤"]:  # Typo detected
                self.rules_applied.append(
                    RuleApplied(rule_id=self.RULE_FUZZY_MATCH, ...)
                )
            return True
    return False
```

### 3. Tolerance-Based Boundary Detection

**Pattern**: Allow variance in patterns
```python
def _find_next_panel_start(self, rows, start_from):
    blank_count = 0
    max_blank_tolerance = 2  # ±2 rows allowed
    
    for i in range(start_from, min(start_from + 5, len(rows))):
        if self._is_blank_row(rows[i]):
            blank_count += 1
            continue
        
        if blank_count > 0 and blank_count <= max_blank_tolerance:
            return i  # Found valid panel start
```

---

## 📦 Sample Management Patterns

### 1. Synthetic Sample Generation

**Pattern**: Programmatic fixture generation
```python
class FixtureGenerator:
    def generate_all(self, count: int = 10):
        self._generate_2tab_simple()
        self._generate_2tab_mcc()
        # ...
        return generated_files
```

**Benefits**:
- Reproducible test data
- Version controlled
- Easy to regenerate
- Covers edge cases systematically

### 2. Real Sample Ingestion (Future)

**Pattern**: Validate, classify, persist
```python
class SampleIngestor:
    def ingest(self, src_dir: str):
        for file in scan(src_dir):
            # 1. Validate format
            if not self._validate_schema(file):
                reject(file, reason)
                continue
            
            # 2. Classify
            class_type = self._classify(file)  # tab2|tab3|multi
            
            # 3. Calculate SHA256
            sha256 = self._hash(file)
            
            # 4. Move to fixtures
            dest = self._apply_naming(file, class_type)
            move(file, dest)
            
            # 5. Update manifest
            self._update_manifest(dest, sha256, class_type)
```

### 3. Manifest-Driven Testing

**Pattern**: Metadata-driven test execution
```json
{
  "samples": [
    {
      "file": "real_001_tab2.xlsx",
      "size": 45678,
      "sha256": "abc123...",
      "class": "tab2",
      "notes": "Standard low-voltage panel"
    }
  ]
}
```

**Usage**: Load manifest → parametrize tests → validate all samples

---

## 🚦 Production Gate Patterns

### 1. Count-Based Gate

**Pattern**: Block deployment below threshold
```bash
MIN_SAMPLES=60
CURRENT_SAMPLES=$(find "$FIXTURES_DIR" -type f | wc -l)

if [ "$CURRENT_SAMPLES" -lt "$MIN_SAMPLES" ]; then
    echo "❌ GATE BLOCKED"
    exit 68  # Custom exit code for sample insufficiency
fi
```

### 2. Test-Based Gate

**Pattern**: All tests must pass
```bash
pytest -q tests/parser/test_parser_e2e.py

if [ $? -eq 0 ]; then
    echo "✅ GATE PASSED"
    exit 0
else
    echo "❌ GATE FAILED"
    exit 1
fi
```

### 3. Combined Gate Strategy

**Pattern**: Both count AND tests
```bash
# Step 1: Check sample count
validate_sample_count || exit 68

# Step 2: Run regression tests
pytest -q tests/parser || exit 1

# Step 3: Approve deployment
echo "✅ DEPLOYMENT APPROVED"
exit 0
```

---

## 📊 Performance Optimization Patterns

### 1. Single-Pass Parsing

**Pattern**: Parse once, extract all information
```python
def parse_file(self, file_path: str):
    # Single parse
    tabs_data = self._parse_xlsx(file_path)
    
    # Extract all panels in one pass
    for tab_idx in tabs_to_analyze:
        panel_boundaries = self.rules_engine.find_panel_boundaries(rows)
        for start, end in panel_boundaries:
            panels.append(...)
    
    return {"panels": panels, "evidence": evidence}
```

### 2. Performance Tracking

**Pattern**: Measure everything
```python
start_time = datetime.now(timezone.utc)

# ... parsing logic ...

duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
evidence["duration_ms"] = duration_ms
```

### 3. Target-Based Assertions

**Pattern**: Assert performance targets
```python
# In tests
assert result["evidence"]["duration_ms"] < 200  # p95 target

# In docs
p95 target: ≤ 200ms
Current: ~130ms
Margin: +70ms (35%)
```

---

## 🔐 Security Patterns

### 1. Admin-Only Endpoints

**Pattern**: Role-based access control
```python
@router.post("/parse", dependencies=[Depends(ensure_admin)])
async def parse_file(parse_req: ParseRequest, _admin: dict = Depends(ensure_admin)):
    # Only admins can parse files
```

### 2. TraceId Propagation

**Pattern**: Request tracing
```python
trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

# Pass through service
result = parser_service.parse_file(file_path=path, trace_id=trace_id)

# Include in errors
raise HTTPException(status_code=500, detail={
    "code": "PARSE_FAILED",
    "traceId": trace_id
})
```

---

## 📝 Documentation Patterns

### 1. Rule Documentation Structure

**Pattern**: Rule ID, trigger, action, rationale
```markdown
### Rule 1: TAB_RULE_2
- **Trigger**: Excel file has exactly 2 tabs
- **Action**: Analyze both tabs
- **Rationale**: No high-voltage panel, MCC possible
```

### 2. Evidence Documentation

**Pattern**: Schema + example
```markdown
## Evidence Schema
- `traceId`: Request tracking UUID
- `rules_applied[]`: Applied rule evidence
- `warnings[]`: Non-blocking issues
- `duration_ms`: Parsing time

## Example
{
  "traceId": "abc-123",
  "rules_applied": [{"rule_id": "TAB_RULE_2", ...}],
  "warnings": [],
  "duration_ms": 150
}
```

---

## 🎯 Lessons Learned

1. **Zero-Mock is Achievable**: Synthetic samples = real files, not mocks
2. **Evidence Enables Debugging**: Every operation leaves trace
3. **Production Gates Work**: Clear thresholds prevent premature deployment
4. **Rule Separation Scales**: Rules engine + service = clean architecture
5. **Performance Targets Matter**: Assert targets in tests to catch regressions

**Status**: Patterns validated in prototype, ready for production scale.