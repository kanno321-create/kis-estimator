# Runbook/Operations — Go-Live v1

## Deployment Process
- Start: `deploy_production.sh` → parse SERVICE_URL
- Health: `/healthz`, `/readyz` (x-trace-id attached)
- Load: hey 60s c=50 on `/api/catalog`
- Stop rules: p95>500ms 10m, err%>1% 5m, /readyz fail → `rollback.sh`
- Watcher: `ops_watch.sh` (1m interval)
- Evidence: SHA256SUMS, readyz.json, loadtest_summary.json

## Stop Rules (Active)
| Rule | Threshold | Window | Action |
|------|-----------|---------|--------|
| P95 Latency | > 500ms | 10 min | Rollback |
| Error Rate | > 1.0% | 5 min | Rollback |
| Readiness | != ok | 1 occurrence | Rollback |

## Current Deployment Result
- **Deployment ID**: deploy_20250930_161328
- **Status**: ROLLBACK TRIGGERED
- **Reason**: Error rate 2.0% exceeded 1.0% threshold
- **P95 Latency**: 114.85ms (PASS)
- **Error Rate**: 2.0% (FAIL)
- **RPS**: 1.67

## Monitoring Commands
```bash
# Start continuous monitoring
./out/go_live_20250930_161328/ops_watch.sh &

# Check latest metrics
cat out/go_live_20250930_161328/reports/loadtest_summary.json

# View stop rule triggers
grep "STOP RULE" out/go_live_20250930_161328/logs/*.log

# Manual rollback if needed
./rollback.sh
```

## Evidence Locations
- **Logs**: `out/go_live_20250930_161328/logs/`
- **Reports**: `out/go_live_20250930_161328/reports/`
- **Evidence**: `out/go_live_20250930_161328/evidence/SHA256SUMS`
- **Archive**: `out/go_live_20250930_161328/EvidencePack_20250930_161328.tar.gz`