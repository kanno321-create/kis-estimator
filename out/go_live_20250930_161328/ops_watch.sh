#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVICE_URL="$(cat "${ROOT}/SERVICE_URL.txt")"
JWT_HEADER=${KIS_JWT:+-H "Authorization: Bearer ${KIS_JWT}"}
STOP_P95_MS=500
STOP_ERR_PCT=1.0
COUNT_ERR=0; COUNT_P95=0

while true; do
  TS="$(date -Is)"
  curl -sS ${JWT_HEADER} "${SERVICE_URL}/readyz" -o "${ROOT}/reports/readyz_${TS}.json" -m 10 || echo "{}" > "${ROOT}/reports/readyz_${TS}.json"
  CODE=$(jq -r '.status // .ok // empty' "${ROOT}/reports/readyz_${TS}.json")

  if [ "${CODE}" != "ok" ] && [ "${CODE}" != "ready" ]; then
     echo "${TS} READYZ FAIL — triggering rollback" | tee -a "${ROOT}/logs/ops_watch.log"
     (cd "$(dirname "${ROOT}")" && ./rollback.sh | tee "${ROOT}/logs/rollback_watch.log")
     exit 0
  fi

  # Quick 10s load test
  hey -o csv -z 10s -c 30 ${JWT_HEADER} "${SERVICE_URL}/api/catalog" > "${ROOT}/reports/watch_${TS}.csv" 2>> "${ROOT}/logs/ops_watch.log" || true

  # Analyze metrics
  python3 - "${ROOT}/reports/watch_${TS}.csv" <<'PY'
import csv, sys, statistics, json
f=sys.argv[1]; rows=list(csv.DictReader(open(f)))
lat=[float(r.get("latency_ms", 0)) for r in rows if r.get("latency_ms")]
tot=len(lat); ok=sum(1 for r in rows if str(r.get("status_code","")).startswith("2")); err=tot-ok
p95=statistics.quantiles(lat, n=100)[94] if tot>=100 else (sorted(lat)[int(len(lat)*0.95)-1] if lat else None)
print(json.dumps({"p95_ms":p95,"err_pct":(err/tot*100.0 if tot else 0.0),"total":tot}))
PY > "${ROOT}/reports/watch_${TS}.json"

  P95=$(jq -r '.p95_ms // 0' "${ROOT}/reports/watch_${TS}.json")
  ERR=$(jq -r '.err_pct // 0' "${ROOT}/reports/watch_${TS}.json")

  # Check stop rules
  if (( $(awk -v p="$P95" 'BEGIN{print (p>500)}') )); then
    COUNT_P95=$((COUNT_P95+1))
  else
    COUNT_P95=0
  fi

  if (( $(awk -v e="$ERR" 'BEGIN{print (e>1.0)}') )); then
    COUNT_ERR=$((COUNT_ERR+1))
  else
    COUNT_ERR=0
  fi

  if [ $COUNT_P95 -ge 10 ] || [ $COUNT_ERR -ge 5 ]; then
     echo "${TS} STOP RULE window breached — rollback" | tee -a "${ROOT}/logs/ops_watch.log"
     (cd "$(dirname "${ROOT}")" && ./rollback.sh | tee "${ROOT}/logs/rollback_watch.log")
     exit 0
  fi

  echo "${TS} Monitoring: P95=${P95}ms ERR=${ERR}% (P95_count=${COUNT_P95} ERR_count=${COUNT_ERR})" | tee -a "${ROOT}/logs/ops_watch.log"
  sleep 60
done