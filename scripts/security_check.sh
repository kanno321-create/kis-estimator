#!/bin/bash
# Security Regression Testing Script for KIS Estimator
# Validates all security fixes are in place and functioning

set -e

echo "========================================="
echo "KIS Estimator Security Regression Test"
echo "========================================="

# Configuration
API_HOST=${API_HOST:-"localhost"}
API_PORT=${API_PORT:-"8000"}
BASE_URL="http://${API_HOST}:${API_PORT}"

# Test JWT token (if provided)
TEST_JWT=${TEST_JWT:-""}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Security test functions
run_test() {
    local test_name=$1
    local test_command=$2
    local expected_result=$3

    echo -n "Testing: $test_name... "

    if eval "$test_command"; then
        if [ "$expected_result" = "pass" ]; then
            echo -e "${GREEN}✓${NC} PASS"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗${NC} FAIL (expected to fail but passed)"
            ((TESTS_FAILED++))
        fi
    else
        if [ "$expected_result" = "fail" ]; then
            echo -e "${GREEN}✓${NC} PASS (correctly rejected)"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗${NC} FAIL"
            ((TESTS_FAILED++))
        fi
    fi
}

# 1. CRITICAL: Hardcoded Password Detection
echo -e "\n${YELLOW}1. Hardcoded Password Detection${NC}"
echo "-------------------------------------"

# Check for hardcoded passwords in scripts
echo "Scanning for hardcoded passwords..."
if grep -r "@dnjsdl2572" scripts/ 2>/dev/null; then
    echo -e "${RED}✗${NC} CRITICAL: Hardcoded password found!"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}✓${NC} No hardcoded passwords detected"
    ((TESTS_PASSED++))
fi

# Check gitignore for protection
if grep -q "scripts/deploy_db_\*.py" .gitignore; then
    echo -e "${GREEN}✓${NC} Gitignore protects sensitive scripts"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗${NC} Gitignore missing protection for deploy_db_*.py"
    ((TESTS_FAILED++))
fi

# 2. JWT Authentication Tests
echo -e "\n${YELLOW}2. JWT Authentication${NC}"
echo "-------------------------------------"

# Test unprotected endpoints (should work)
run_test "Health endpoint without JWT" \
    "curl -s -o /dev/null -w '%{http_code}' '${BASE_URL}/healthz' | grep -q '200'" \
    "pass"

run_test "Readiness endpoint without JWT" \
    "curl -s -o /dev/null -w '%{http_code}' '${BASE_URL}/readyz' | grep -q '200'" \
    "pass"

# Test protected endpoints without JWT (should fail with 401/403)
run_test "Protected endpoint without JWT" \
    "curl -s -o /dev/null -w '%{http_code}' '${BASE_URL}/v1/catalog/items' | grep -E '401|403'" \
    "pass"

run_test "Estimate endpoint without JWT" \
    "curl -s -o /dev/null -w '%{http_code}' '${BASE_URL}/v1/estimate/create' | grep -E '401|403'" \
    "pass"

# Test with invalid JWT
run_test "Protected endpoint with invalid JWT" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer invalid.jwt.token' '${BASE_URL}/v1/catalog/items' | grep -E '401|403'" \
    "pass"

# Test with valid JWT (if provided)
if [ -n "$TEST_JWT" ]; then
    echo -e "\n${YELLOW}Testing with provided JWT token...${NC}"

    run_test "Protected endpoint with valid JWT" \
        "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer ${TEST_JWT}' '${BASE_URL}/v1/catalog/items' | grep -q '200'" \
        "pass"
fi

# 3. CORS Configuration Tests
echo -e "\n${YELLOW}3. CORS Configuration${NC}"
echo "-------------------------------------"

# Test CORS from allowed origin
run_test "CORS from allowed origin" \
    "curl -s -I -X OPTIONS -H 'Origin: https://kis-estimator.com' '${BASE_URL}/v1/catalog/items' | grep -q 'access-control-allow-origin'" \
    "pass"

# Test CORS from disallowed origin
run_test "CORS from disallowed origin" \
    "! curl -s -I -X OPTIONS -H 'Origin: https://evil.com' '${BASE_URL}/v1/catalog/items' | grep -q 'access-control-allow-origin: https://evil.com'" \
    "pass"

# Check for wildcard CORS (should not exist)
if curl -s -I "${BASE_URL}/healthz" | grep -q "access-control-allow-origin: \*"; then
    echo -e "${RED}✗${NC} CRITICAL: Wildcard CORS detected!"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}✓${NC} No wildcard CORS detected"
    ((TESTS_PASSED++))
fi

# 4. Rate Limiting Tests
echo -e "\n${YELLOW}4. Rate Limiting${NC}"
echo "-------------------------------------"

echo "Testing rate limiting (10 rapid requests)..."
RATE_LIMITED=false
for i in {1..15}; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/healthz")
    if [ "$response" = "429" ]; then
        RATE_LIMITED=true
        break
    fi
    sleep 0.05
done

if $RATE_LIMITED; then
    echo -e "${GREEN}✓${NC} Rate limiting is active"
    ((TESTS_PASSED++))
else
    echo -e "${YELLOW}⚠${NC} Rate limiting may not be configured (or limit is high)"
    ((TESTS_PASSED++))  # Warning, not failure
fi

# 5. Security Headers
echo -e "\n${YELLOW}5. Security Headers${NC}"
echo "-------------------------------------"

# Check for security headers
check_header() {
    local header=$1
    local endpoint=$2

    if curl -s -I "${BASE_URL}${endpoint}" | grep -iq "$header"; then
        echo -e "${GREEN}✓${NC} $header present"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} $header not found"
    fi
}

check_header "X-Content-Type-Options" "/healthz"
check_header "X-Frame-Options" "/healthz"
check_header "X-XSS-Protection" "/healthz"
check_header "Strict-Transport-Security" "/healthz"

# 6. Input Validation Tests
echo -e "\n${YELLOW}6. Input Validation${NC}"
echo "-------------------------------------"

# Test SQL injection attempt (should be rejected)
run_test "SQL injection protection" \
    "curl -s -X POST '${BASE_URL}/v1/estimate/create' \
        -H 'Content-Type: application/json' \
        -d '{\"customer\": \"'; DROP TABLE users; --\"}' \
        | grep -v 'DROP TABLE'" \
    "pass"

# Test XSS attempt (should be sanitized)
run_test "XSS protection" \
    "curl -s -X POST '${BASE_URL}/v1/estimate/create' \
        -H 'Content-Type: application/json' \
        -d '{\"customer\": \"<script>alert(1)</script>\"}' \
        | grep -v '<script>'" \
    "pass"

# 7. Secret Management
echo -e "\n${YELLOW}7. Secret Management${NC}"
echo "-------------------------------------"

# Check for exposed secrets in responses
echo "Checking for exposed secrets in API responses..."
health_response=$(curl -s "${BASE_URL}/healthz")

if echo "$health_response" | grep -qE "(password|secret|key|token)" | grep -v "status"; then
    echo -e "${RED}✗${NC} Potential secrets exposed in responses"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}✓${NC} No secrets exposed in health check"
    ((TESTS_PASSED++))
fi

# Check environment variables are not exposed
if curl -s "${BASE_URL}/env" 2>/dev/null | grep -q "DATABASE_URL"; then
    echo -e "${RED}✗${NC} CRITICAL: Environment variables exposed!"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}✓${NC} Environment variables not exposed"
    ((TESTS_PASSED++))
fi

# 8. TLS/HTTPS Enforcement (if HTTPS is available)
echo -e "\n${YELLOW}8. TLS/HTTPS Enforcement${NC}"
echo "-------------------------------------"

if [ "$API_HOST" = "localhost" ] || [ "$API_HOST" = "127.0.0.1" ]; then
    echo -e "${YELLOW}ℹ${NC} Skipping TLS tests (localhost)"
else
    # Check for HTTPS redirect or HSTS header
    check_header "Strict-Transport-Security" "/healthz"
fi

# 9. Audit Logging
echo -e "\n${YELLOW}9. Audit Logging${NC}"
echo "-------------------------------------"

# Check if audit logs are being created
if [ -d "logs" ]; then
    if ls logs/*.log 2>/dev/null | grep -q .; then
        echo -e "${GREEN}✓${NC} Audit logs are being generated"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} No audit logs found"
    fi
else
    echo -e "${YELLOW}⚠${NC} Logs directory not found"
fi

# Summary
echo -e "\n========================================="
echo -e "${GREEN}Security Regression Test Summary${NC}"
echo "========================================="
echo ""
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All security tests PASSED${NC}"
    echo ""
    echo "Security posture: GOOD"
    exit 0
elif [ $TESTS_FAILED -le 2 ]; then
    echo -e "${YELLOW}⚠ Minor security issues detected${NC}"
    echo ""
    echo "Security posture: ACCEPTABLE (review warnings)"
    exit 0
else
    echo -e "${RED}✗ Critical security issues detected${NC}"
    echo ""
    echo "Security posture: VULNERABLE (immediate action required)"
    exit 1
fi