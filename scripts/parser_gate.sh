#!/bin/bash
# 프로덕션 게이트: 60개 실샘플 확보 전 배포 차단
# Exit 68: 샘플 부족

set -e

FIXTURES_DIR="tests/parser/fixtures"
MIN_SAMPLES=60
CURRENT_SAMPLES=$(find "$FIXTURES_DIR" -type f \( -name "*.xlsx" -o -name "*.csv" \) | wc -l)

echo "=== Parser Production Gate ==="
echo "Fixtures directory: $FIXTURES_DIR"
echo "Current samples: $CURRENT_SAMPLES"
echo "Required samples: $MIN_SAMPLES"

if [ "$CURRENT_SAMPLES" -lt "$MIN_SAMPLES" ]; then
    echo ""
    echo "❌ GATE BLOCKED: Insufficient real samples"
    echo "   Current: $CURRENT_SAMPLES / Required: $MIN_SAMPLES"
    echo ""
    echo "ACTION REQUIRED:"
    echo "  1. Replace synthetic samples with 60 real quotation files"
    echo "  2. Re-run parser gate: bash scripts/parser_gate.sh"
    echo ""
    echo "Exit code: 68 (blocked for production)"
    exit 68
fi

echo ""
echo "✓ Sample count OK: $CURRENT_SAMPLES >= $MIN_SAMPLES"
echo ""
echo "Running parser regression tests..."

# Run pytest
pytest -q tests/parser/test_parser_e2e.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ GATE PASSED: All tests passed with 60+ real samples"
    echo "   Deployment approved"
    exit 0
else
    echo ""
    echo "❌ GATE FAILED: Tests failed"
    echo "   Fix parser issues before deployment"
    exit 1
fi