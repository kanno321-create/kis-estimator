#!/bin/bash
# Go-Live Smoke Test Script
# Execute health checks and basic endpoint validation

set -e

echo "====================================="
echo "KIS Estimator Go-Live Smoke Test"
echo "====================================="

# Configuration
API_HOST=${API_HOST:-"localhost"}
API_PORT=${API_PORT:-"8080"}
BASE_URL="http://${API_HOST}:${API_PORT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test functions
test_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3

    response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${endpoint}")

    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} ${description} [${response}]"
        return 0
    else
        echo -e "${RED}✗${NC} ${description} [Expected: ${expected_status}, Got: ${response}]"
        return 1
    fi
}

# 1. Health Check
echo -e "\n${YELLOW}1. Health Check Tests${NC}"
echo "-------------------------------------"

# Basic health endpoint
test_endpoint "/healthz" "200" "Health endpoint"

# Get full health response
echo -e "\nHealth Response:"
curl -s "${BASE_URL}/healthz" | python -m json.tool || true

# 2. Readiness Check
echo -e "\n${YELLOW}2. Readiness Check${NC}"
echo "-------------------------------------"

# Readiness with full validation
echo "Readiness Response:"
readiness_response=$(curl -s "${BASE_URL}/readyz")
echo "$readiness_response" | python -m json.tool || true

# Check readiness status
if echo "$readiness_response" | grep -q '"status":"ok"'; then
    echo -e "${GREEN}✓${NC} System is ready"
else
    echo -e "${RED}✗${NC} System not ready"
fi

# 3. API Documentation
echo -e "\n${YELLOW}3. API Documentation${NC}"
echo "-------------------------------------"

test_endpoint "/docs" "200" "Swagger UI"
test_endpoint "/openapi.json" "200" "OpenAPI spec"

# 4. JWT Protection Check
echo -e "\n${YELLOW}4. Security Validation${NC}"
echo "-------------------------------------"

# Test protected endpoints without JWT (should return 401)
echo "Testing JWT protection:"

response=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/v1/catalog/items")
if [ "$response" = "401" ] || [ "$response" = "403" ]; then
    echo -e "${GREEN}✓${NC} JWT protection active [${response}]"
else
    echo -e "${RED}✗${NC} JWT protection NOT active [${response}]"
fi

# 5. CORS Headers Check
echo -e "\n${YELLOW}5. CORS Configuration${NC}"
echo "-------------------------------------"

cors_headers=$(curl -s -I -X OPTIONS "${BASE_URL}/v1/catalog/items" 2>/dev/null | grep -i "access-control")
if [ -n "$cors_headers" ]; then
    echo -e "${GREEN}✓${NC} CORS headers present:"
    echo "$cors_headers"
else
    echo -e "${YELLOW}⚠${NC} No CORS headers found (may be configured differently)"
fi

# 6. Response Time Check
echo -e "\n${YELLOW}6. Response Time Check${NC}"
echo "-------------------------------------"

# Measure health endpoint response time
response_time=$(curl -s -o /dev/null -w "%{time_total}" "${BASE_URL}/healthz")
response_time_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "N/A")

echo "Health endpoint response time: ${response_time_ms}ms"

# Check if response time is under 50ms
if [ "$response_time_ms" != "N/A" ]; then
    if (( $(echo "$response_time_ms < 50" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "${GREEN}✓${NC} Response time < 50ms requirement met"
    else
        echo -e "${YELLOW}⚠${NC} Response time > 50ms target"
    fi
fi

# 7. Error Handling
echo -e "\n${YELLOW}7. Error Handling${NC}"
echo "-------------------------------------"

# Test 404 response format
not_found=$(curl -s "${BASE_URL}/nonexistent")
if echo "$not_found" | grep -q "traceId"; then
    echo -e "${GREEN}✓${NC} Error response includes traceId"
else
    echo -e "${YELLOW}⚠${NC} Error response format may not include traceId"
fi

# Summary
echo -e "\n====================================="
echo -e "${GREEN}Smoke Test Complete${NC}"
echo "====================================="
echo ""
echo "Next steps:"
echo "1. If using JWT, set JWT environment variable and run authenticated tests"
echo "2. Run performance benchmarks with autocannon or bombardier"
echo "3. Apply database indexes: psql \"\$DATABASE_URL\" < sql/performance_indexes.sql"
echo ""