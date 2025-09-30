# Task Completion Checklist

When completing any development task, follow this checklist:

## 1. Code Quality Checks ✅

### Formatting
```bash
black src/ tests/
```
- Must run before commit
- Ensures consistent code style

### Linting
```bash
ruff check src/ tests/
ruff check --fix src/ tests/     # Fix auto-fixable issues
```
- Check for code quality issues
- Fix all reported problems

### Type Checking
```bash
mypy src/
```
- Verify type annotations
- Resolve all type errors

## 2. Testing ✅

### Unit Tests
```bash
pytest -m unit
```
- All unit tests must pass
- Cover new code paths

### Integration Tests
```bash
pytest -m integration
```
- Test database interactions
- Verify API integrations

### Regression Tests (CRITICAL)
```bash
pytest -m regression
```
- **MUST PASS 20/20 tests**
- **Blocking requirement for merge**
- If failed, do NOT proceed to merge

### Coverage Check
```bash
pytest --cov=src --cov-report=term
```
- Minimum 80% code coverage
- Check coverage report for gaps

## 3. Evidence Generation ✅

For any calculation or processing:
- Generate evidence artifacts
- Store in `/spec_kit/evidence/{timestamp}/`
- Include: input.json, output.json, metrics.json, validation.json
- Calculate SHA256 hash for integrity

## 4. Documentation ✅

- Update relevant documentation
- Add docstrings for new functions/classes
- Update API documentation if endpoints changed
- Add inline comments for complex logic

## 5. Contract Validation ✅

If API changes were made:
```bash
# Validate OpenAPI spec
npm run contract:lint
```
- Ensure OpenAPI 3.1 compliance
- Verify error schemas match standard
- Check SSE endpoints have heartbeat + meta.seq

## 6. Quality Gate Validation ✅

Verify stage-specific gates are met:
- **Enclosure**: fit_score ≥ 0.90, IP ≥ 44
- **Breaker**: phase imbalance ≤ 4%, interference = 0
- **Format**: formula preservation = 100%
- **Doc Lint**: lint errors = 0

## 7. Git Workflow ✅

```bash
# Check status
git status

# Stage changes
git add .

# Commit with conventional format
git commit -m "feat: description of changes"

# Verify branch (should NOT be main/master)
git branch
```

## 8. Final Verification ✅

Before marking task complete:
- [ ] All quality checks passed
- [ ] All tests passed (including 20/20 regression)
- [ ] Evidence artifacts generated
- [ ] Documentation updated
- [ ] Code reviewed (if pair/mob programming)
- [ ] No TODO comments for core functionality
- [ ] No console.log or debug statements left
- [ ] Commit message follows conventions

## 9. CI/CD Gate Requirements ✅

For merge to be allowed:
- [ ] unit_tests: PASS
- [ ] integration_tests: PASS
- [ ] regression_tests: 20/20 PASS
- [ ] contract_validation: 100%
- [ ] evidence_pack: COMPLETE
- [ ] code_coverage: ≥ 80%

## Common Mistakes to Avoid ⚠️

1. **Skipping regression tests** - Always run before commit
2. **Forgetting evidence generation** - Required for all calculations
3. **Using TIMESTAMP instead of TIMESTAMPTZ** - Always use TIMESTAMPTZ
4. **Committing on main/master** - Always work on feature branches
5. **Incomplete implementations** - No TODO for core functionality
6. **Missing type hints** - All function signatures need types
7. **Low test coverage** - Must maintain ≥80%

## Session End Checklist ✅

Before ending development session:
```bash
# 1. Run full test suite
pytest --cov=src

# 2. Verify regression tests
pytest -m regression

# 3. Run all quality checks
npm run quality

# 4. Save work if incomplete
git commit -m "wip: description"

# 5. Document progress
# Update task tracking or leave session notes
```