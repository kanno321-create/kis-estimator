# KIS Estimator Project - Priority Roadmap

## Current Status (2025-09-30)

### Project Health: 70% Production Ready
- **Version**: 0.1.0-rebuild
- **Overall Quality**: 7.7/10 (Good)
- **Critical Blocker**: Test Coverage (19.9% vs 80% target)

## 3-Month Improvement Roadmap

### Month 1: Foundation (Test Coverage + Security)

#### Week 1-2: P0 Critical Tasks
**Task 1.1: Test Coverage Phase 1** (Target: 40%)
```python
# Priority test files to create:
tests/services/test_estimate_service.py
  - test_create_quote_success()
  - test_create_quote_with_sse()
  - test_fix4_pipeline_stages()
  - test_quality_gates_enforcement()
  - test_evidence_generation()

tests/services/test_document_service.py
  - test_format_estimate_formula_preservation()
  - test_generate_cover_branding()
  - test_lint_document_no_errors()
  - test_export_pdf_xlsx_integrity()
  - test_upload_evidence_sha256()

tests/integrations/test_mcp_client.py
  - test_call_with_retry()
  - test_exponential_backoff()
  - test_idempotency_key()
  - test_evidence_logging()
  - test_error_handling()
```

**Task 1.2: Security Fix**
```python
# File: api/config.py
# Change line 28:
APP_DEBUG: bool = False  # Production default

# Create: .env.production
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=WARNING

# Create: .env.development
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
```

#### Week 3-4: P1 Quality Improvements
**Task 1.3: Test Coverage Phase 2** (Target: 60%)
```python
tests/engine/test_breaker_placer.py
  - test_ortools_placement()
  - test_heuristic_fallback()
  - test_phase_balance()
  - test_clearance_validation()

tests/engine/test_enclosure_solver.py
  - test_fit_score_calculation()
  - test_ip_rating_validation()
  - test_door_clearance()

tests/services/test_layout_service.py
  - test_place_breakers()
  - test_balance_phases()
  - test_check_clearance()
```

**Task 1.4: Error Handling Standardization**
```python
# Create: api/exceptions.py
class EstimatorException(Exception):
    def __init__(self, code: str, message: str, hint: str = None):
        self.code = code
        self.message = message
        self.hint = hint

class EnclosureFitError(EstimatorException):
    """Raised when fit_score < 0.90"""

class PhaseBalanceError(EstimatorException):
    """Raised when phase_dev > 0.03"""

# Update all services to use custom exceptions
```

### Month 2: Quality & Standards

#### Week 5-6: Code Quality
**Task 2.1: Type Hints Completion**
```python
# Add type hints to all public functions
# Example pattern:
def solve(
    breakers: list[dict[str, Any]], 
    materials: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Calculate optimal enclosure.
    
    Args:
        breakers: List of breaker specifications
        materials: Available enclosure materials
        
    Returns:
        dict with fit_score, sku, dimensions
        
    Raises:
        EnclosureFitError: If no suitable enclosure found
    """
    ...
```

**Task 2.2: Documentation Completion**
```python
# Add Google-style docstrings to all:
# - Public functions (100%)
# - Classes (100%)
# - Complex algorithms (Why > What)

# Update:
# - README.md (architecture diagrams)
# - CONTRIBUTING.md (development guide)
# - API.md (endpoint documentation)
```

#### Week 7-8: P2 Test Completion
**Task 2.3: Test Coverage Phase 3** (Target: 80%)
```python
tests/api/test_tab_parsing.py
  - test_two_tab_parsing()
  - test_three_tab_high_voltage()
  - test_block_detection()
  - test_subtotal_handling()

tests/integration/test_error_scenarios.py
  - test_invalid_input_handling()
  - test_ortools_timeout()
  - test_supabase_connection_failure()
  - test_mcp_retry_exhaustion()

tests/performance/test_benchmarks.py
  - test_breaker_placement_100_items()
  - test_api_response_p95()
  - test_document_generation()
```

### Month 3: Optimization & Production Readiness

#### Week 9-10: Performance
**Task 3.1: Performance Optimization**
```bash
# Add benchmark tests
pytest tests/performance/ --benchmark-only

# Profile critical paths
python -m cProfile -o profile.stats scripts/profile_estimate.py

# Optimize bottlenecks:
# - Database queries (add indexes)
# - OR-Tools solver (timeout tuning)
# - Document generation (caching)
```

**Task 3.2: Monitoring Setup**
```python
# Add: api/monitoring.py
# - OpenTelemetry integration
# - Custom metrics (fit_score, phase_dev)
# - Performance tracking
# - Error rate monitoring
```

#### Week 11-12: Production Deployment
**Task 3.3: Production Preparation**
```bash
# Checklist:
- [ ] Test coverage ≥ 80%
- [ ] Security scan passed
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Supabase production deployed
- [ ] Monitoring configured
- [ ] Rollback procedure tested
- [ ] Load testing completed
```

**Task 3.4: Release v1.0.0**
```bash
# Version bump: 0.1.0-rebuild → 1.0.0
# Release notes
# Production deployment
# Post-deployment validation
```

## Priority Matrix (Impact x Effort)

### High Impact, Low Effort (Do First)
1. ✅ Security fix (APP_DEBUG) - 30 min
2. ⬜ estimate_service tests - 4 hours
3. ⬜ document_service tests - 3 hours
4. ⬜ mcp_client tests - 2 hours

### High Impact, Medium Effort (Do Second)
5. ⬜ breaker_placer tests - 8 hours
6. ⬜ enclosure_solver tests - 6 hours
7. ⬜ Error handling standardization - 8 hours
8. ⬜ Type hints completion - 12 hours

### Medium Impact, Medium Effort (Do Third)
9. ⬜ Edge case tests - 16 hours
10. ⬜ Documentation completion - 12 hours
11. ⬜ Performance optimization - 16 hours

### Low Impact, High Effort (Do Last)
12. ⬜ Advanced monitoring - 20 hours
13. ⬜ Load testing - 12 hours

## Success Metrics

### Week 2 Checkpoint
- [ ] Test coverage: 40%
- [ ] APP_DEBUG: False default
- [ ] P0 tasks complete

### Week 4 Checkpoint
- [ ] Test coverage: 60%
- [ ] Error handling: Standardized
- [ ] Type hints: 80% coverage

### Week 8 Checkpoint
- [ ] Test coverage: 80% ✅ (Constitution compliant)
- [ ] Documentation: 90% complete
- [ ] All P1 tasks complete

### Week 12 Checkpoint
- [ ] Production ready: 95%
- [ ] Performance benchmarks: Met
- [ ] v1.0.0 ready for release

## Risk Mitigation

### Risk 1: Test Writing Takes Longer
- **Mitigation**: Start with high-priority tests only
- **Fallback**: Aim for 60% minimum coverage for v1.0

### Risk 2: Breaking Changes During Testing
- **Mitigation**: Feature freeze during test development
- **Fallback**: Use feature branches, merge after validation

### Risk 3: Performance Issues Discovered Late
- **Mitigation**: Add benchmarks in Week 5-6
- **Fallback**: Performance fixes in v1.1 if necessary

## Decision Framework

### When to Start Each Task
- P0: Start immediately (Week 1)
- P1: After P0 complete (Week 3)
- P2: After 60% coverage (Week 7)

### When to Skip/Defer
- Skip if test coverage >80% earlier than planned
- Defer performance work if critical bugs found
- Defer v1.0 if test coverage <80%

## Resource Allocation

### Developer Time (Estimated)
- Month 1: 80 hours (Testing + Security)
- Month 2: 60 hours (Quality + Standards)
- Month 3: 40 hours (Optimization + Deployment)
- **Total**: 180 hours (~1 FTE for 3 months)

### Tools Required
- pytest + pytest-cov
- black, ruff, mypy (already in use)
- pytest-benchmark (new)
- OpenTelemetry (new)
- Load testing tool (new)

## Next Immediate Action

**User must choose**:
- **Option A**: Start P0 Task 1.1 (Test Coverage Phase 1)
- **Option B**: Start P0 Task 1.2 (Security Fix)
- **Option C**: Custom task per user instruction

**Recommendation**: Option B (Security Fix) - Quick win (30 min), removes production blocker