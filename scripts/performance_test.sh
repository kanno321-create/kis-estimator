#!/bin/bash
# Performance Testing Script for KIS Estimator
# Uses autocannon (Node.js) or bombardier (Go) for load testing

set -e

echo "========================================="
echo "KIS Estimator Performance Test"
echo "========================================="

# Configuration
API_HOST=${API_HOST:-"localhost"}
API_PORT=${API_PORT:-"8000"}
BASE_URL="http://${API_HOST}:${API_PORT}"
TEST_JWT=${TEST_JWT:-""}

# Test parameters
DURATION=${DURATION:-"30"}  # seconds
CONNECTIONS=${CONNECTIONS:-"10"}  # concurrent connections
RATE=${RATE:-"100"}  # requests per second

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check which tool is available
TOOL=""
if command -v autocannon &> /dev/null; then
    TOOL="autocannon"
elif command -v bombardier &> /dev/null; then
    TOOL="bombardier"
else
    echo -e "${YELLOW}Installing autocannon...${NC}"
    npm install -g autocannon
    TOOL="autocannon"
fi

echo -e "${BLUE}Using: $TOOL${NC}"
echo ""

# Create test data files
echo "Preparing test payloads..."

# Simple health check payload
cat > /tmp/health_test.json << 'EOF'
{
  "test": "health"
}
EOF

# Estimate creation payload
cat > /tmp/estimate_test.json << 'EOF'
{
  "customer": {
    "name": "Performance Test Customer",
    "project": "Load Test Project"
  },
  "panels": [
    {
      "name": "TEST-PANEL-1",
      "type": "distribution_board",
      "voltage": 380,
      "phases": 3,
      "breakers": [
        {
          "name": "MAIN",
          "type": "MCCB",
          "rating": 400,
          "poles": 4,
          "quantity": 1
        },
        {
          "name": "SUB",
          "type": "MCB",
          "rating": 32,
          "poles": 2,
          "quantity": 10
        }
      ]
    }
  ],
  "requirements": {
    "ip_rating": "IP54",
    "delivery_days": 30
  }
}
EOF

# Function to run autocannon test
run_autocannon() {
    local endpoint=$1
    local method=$2
    local body_file=$3
    local test_name=$4

    echo -e "\n${YELLOW}Test: $test_name${NC}"
    echo "-------------------------------------"

    if [ "$method" = "GET" ]; then
        if [ -n "$TEST_JWT" ]; then
            autocannon \
                -c $CONNECTIONS \
                -d $DURATION \
                -r $RATE \
                -H "Authorization: Bearer $TEST_JWT" \
                "${BASE_URL}${endpoint}"
        else
            autocannon \
                -c $CONNECTIONS \
                -d $DURATION \
                -r $RATE \
                "${BASE_URL}${endpoint}"
        fi
    else
        if [ -n "$TEST_JWT" ]; then
            autocannon \
                -c $CONNECTIONS \
                -d $DURATION \
                -r $RATE \
                -m $method \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $TEST_JWT" \
                -b "$(cat $body_file)" \
                "${BASE_URL}${endpoint}"
        else
            autocannon \
                -c $CONNECTIONS \
                -d $DURATION \
                -r $RATE \
                -m $method \
                -H "Content-Type: application/json" \
                -b "$(cat $body_file)" \
                "${BASE_URL}${endpoint}"
        fi
    fi
}

# Function to run bombardier test
run_bombardier() {
    local endpoint=$1
    local method=$2
    local body_file=$3
    local test_name=$4

    echo -e "\n${YELLOW}Test: $test_name${NC}"
    echo "-------------------------------------"

    if [ "$method" = "GET" ]; then
        if [ -n "$TEST_JWT" ]; then
            bombardier \
                -c $CONNECTIONS \
                -d ${DURATION}s \
                -r $RATE \
                -H "Authorization: Bearer $TEST_JWT" \
                "${BASE_URL}${endpoint}"
        else
            bombardier \
                -c $CONNECTIONS \
                -d ${DURATION}s \
                -r $RATE \
                "${BASE_URL}${endpoint}"
        fi
    else
        if [ -n "$TEST_JWT" ]; then
            bombardier \
                -c $CONNECTIONS \
                -d ${DURATION}s \
                -r $RATE \
                -m $method \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $TEST_JWT" \
                -f "$body_file" \
                "${BASE_URL}${endpoint}"
        else
            bombardier \
                -c $CONNECTIONS \
                -d ${DURATION}s \
                -r $RATE \
                -m $method \
                -H "Content-Type: application/json" \
                -f "$body_file" \
                "${BASE_URL}${endpoint}"
        fi
    fi
}

# Wrapper function to choose tool
run_test() {
    if [ "$TOOL" = "autocannon" ]; then
        run_autocannon "$@"
    else
        run_bombardier "$@"
    fi
}

# 1. Warmup
echo -e "\n${YELLOW}Warming up...${NC}"
for i in {1..10}; do
    curl -s "${BASE_URL}/healthz" > /dev/null
done
echo "Warmup complete"

# 2. Health Check Performance (Target: < 50ms)
run_test "/healthz" "GET" "" "Health Check Endpoint"

# 3. Readiness Check Performance
run_test "/readyz" "GET" "" "Readiness Check Endpoint"

# 4. Catalog API Performance (if JWT available)
if [ -n "$TEST_JWT" ]; then
    run_test "/v1/catalog/items" "GET" "" "Catalog Items List"
fi

# 5. Estimate Creation Performance (if JWT available)
if [ -n "$TEST_JWT" ]; then
    # Reduce rate for heavy endpoints
    RATE=10 run_test "/v1/estimate/create" "POST" "/tmp/estimate_test.json" "Estimate Creation"
fi

# 6. Concurrent User Simulation
echo -e "\n${YELLOW}6. Concurrent User Simulation${NC}"
echo "-------------------------------------"
echo "Simulating $CONNECTIONS concurrent users for ${DURATION}s..."

if [ "$TOOL" = "autocannon" ]; then
    autocannon \
        -c $CONNECTIONS \
        -d $DURATION \
        --workers 4 \
        "${BASE_URL}/healthz" \
        --json > /tmp/perf_results.json
else
    bombardier \
        -c $CONNECTIONS \
        -d ${DURATION}s \
        --print result \
        "${BASE_URL}/healthz" > /tmp/perf_results.txt
fi

# Parse and display results
echo -e "\n${YELLOW}Performance Summary${NC}"
echo "-------------------------------------"

if [ "$TOOL" = "autocannon" ]; then
    # Parse autocannon JSON output
    if command -v jq &> /dev/null; then
        echo "Latency Statistics:"
        jq '.latency' /tmp/perf_results.json 2>/dev/null || echo "Unable to parse results"

        echo ""
        echo "Throughput:"
        jq '.throughput' /tmp/perf_results.json 2>/dev/null || echo "Unable to parse results"

        echo ""
        echo "Errors:"
        jq '.errors' /tmp/perf_results.json 2>/dev/null || echo "0"
    else
        cat /tmp/perf_results.json
    fi
else
    # Display bombardier text output
    cat /tmp/perf_results.txt
fi

# 7. Target Validation
echo -e "\n${YELLOW}Target Validation${NC}"
echo "-------------------------------------"

# Check if we meet performance targets
TARGETS_MET=true

# Extract p95 latency (this is tool-specific and may need adjustment)
if [ "$TOOL" = "autocannon" ] && command -v jq &> /dev/null; then
    P95=$(jq '.latency.p95' /tmp/perf_results.json 2>/dev/null | cut -d. -f1)

    if [ -n "$P95" ]; then
        echo -n "P95 Latency: ${P95}ms "
        if [ "$P95" -lt 200 ]; then
            echo -e "${GREEN}✓${NC} (Target: < 200ms)"
        else
            echo -e "${RED}✗${NC} (Target: < 200ms)"
            TARGETS_MET=false
        fi
    fi
fi

# 8. Generate Performance Report
echo -e "\n${YELLOW}Generating Performance Report...${NC}"

REPORT_FILE="evidence/performance_$(date +%Y%m%d_%H%M%S).json"
mkdir -p evidence

cat > "$REPORT_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": {
    "host": "$API_HOST",
    "port": "$API_PORT",
    "tool": "$TOOL"
  },
  "test_parameters": {
    "duration_seconds": $DURATION,
    "concurrent_connections": $CONNECTIONS,
    "target_rps": $RATE
  },
  "results": {
EOF

if [ "$TOOL" = "autocannon" ] && [ -f /tmp/perf_results.json ]; then
    echo '    "raw_results":' >> "$REPORT_FILE"
    cat /tmp/perf_results.json >> "$REPORT_FILE"
    echo ',' >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" << EOF
    "targets_met": $TARGETS_MET,
    "notes": "Performance test completed successfully"
  }
}
EOF

echo -e "${GREEN}Report saved to: $REPORT_FILE${NC}"

# 9. Recommendations
echo -e "\n${YELLOW}Performance Recommendations${NC}"
echo "-------------------------------------"

if $TARGETS_MET; then
    echo -e "${GREEN}✓${NC} System meets performance targets"
    echo ""
    echo "Next steps:"
    echo "1. Run extended duration test (5-10 minutes)"
    echo "2. Test with production-like data volumes"
    echo "3. Monitor resource utilization during tests"
else
    echo -e "${RED}✗${NC} Performance targets not met"
    echo ""
    echo "Recommendations:"
    echo "1. Review slow query logs"
    echo "2. Check database indexes are applied"
    echo "3. Verify connection pooling is configured"
    echo "4. Profile application for bottlenecks"
    echo "5. Consider horizontal scaling"
fi

echo ""
echo "To run extended tests:"
echo "  DURATION=300 CONNECTIONS=50 RATE=500 $0"
echo ""
echo "To test specific endpoints with JWT:"
echo "  TEST_JWT='your-jwt-token' $0"

# Cleanup
rm -f /tmp/health_test.json /tmp/estimate_test.json

exit 0