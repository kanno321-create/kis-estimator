#!/usr/bin/env bash
# Simple load test script that respects rate limits
# Sends requests at a controlled rate to measure p95 latency

set -euo pipefail

BASE_URL="${1:-http://localhost:8001}"
ENDPOINT="${2:-/healthz}"
DURATION="${3:-60}"
RPS_TARGET="${4:-1.5}"  # Target 90 req/min (under 100 req/min limit)

URL="$BASE_URL$ENDPOINT"
echo "Load test starting..."
echo "URL: $URL"
echo "Duration: ${DURATION}s"
echo "Target RPS: $RPS_TARGET"

LATENCIES=()
SUCCESSES=0
FAILURES=0
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))
SLEEP_TIME=$(awk "BEGIN {print 1.0 / $RPS_TARGET}")

while [ $(date +%s) -lt $END_TIME ]; do
    START_MS=$(date +%s%3N)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
    END_MS=$(date +%s%3N)
    LATENCY=$((END_MS - START_MS))

    if [ "$HTTP_CODE" = "200" ]; then
        SUCCESSES=$((SUCCESSES + 1))
        LATENCIES+=($LATENCY)
    else
        FAILURES=$((FAILURES + 1))
    fi

    sleep "$SLEEP_TIME"
done

# Calculate statistics
TOTAL=$((SUCCESSES + FAILURES))
ERR_RATE=$(awk -v f="$FAILURES" -v t="$TOTAL" 'BEGIN {print (f/t)*100}')

# Sort latencies and calculate p95
IFS=$'\n' SORTED=($(sort -n <<<"${LATENCIES[*]}"))
P95_INDEX=$(awk -v n="${#SORTED[@]}" 'BEGIN {print int(n * 0.95)}')
P95="${SORTED[$P95_INDEX]}"

echo ""
echo "=== Load Test Results ==="
echo "Total requests: $TOTAL"
echo "Successful: $SUCCESSES"
echo "Failed: $FAILURES"
echo "Error rate: $ERR_RATE%"
echo "P95 latency: ${P95}ms"
echo ""

# Output JSON for parsing
cat > /tmp/load_test_results.json <<EOF
{
  "total_requests": $TOTAL,
  "successful": $SUCCESSES,
  "failed": $FAILURES,
  "error_rate": $ERR_RATE,
  "p95_latency_ms": $P95
}
EOF

echo "Results saved to: /tmp/load_test_results.json"