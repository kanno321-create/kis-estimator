import csv
import json
import statistics

# 부하 테스트 결과 분석
with open('out/go_live_20250930_163213/reports/loadtest.csv', 'r') as f:
    rows = list(csv.DictReader(f))

latencies = [float(r['latency_ms']) for r in rows]
codes = [r['status_code'] for r in rows]

total = len(latencies)
ok_count = sum(1 for c in codes if str(c).startswith('2'))
err_count = total - ok_count

# P95 계산
latencies.sort()
p95 = latencies[int(len(latencies) * 0.95)]

# RPS 계산 (60초 테스트 가정)
rps = total / 60.0

result = {
    "total": total,
    "ok": ok_count,
    "err": err_count,
    "err_pct": (err_count/total*100) if total else 0,
    "p95_ms": p95,
    "p50_ms": statistics.median(latencies),
    "mean_ms": statistics.mean(latencies),
    "rps": rps,
    "tuning_applied": True,
    "status": "PASS" if p95 <= 200 and (err_count/total*100) <= 0.5 else "FAIL"
}

with open('out/go_live_20250930_163213/reports/loadtest_summary.json', 'w') as f:
    json.dump(result, f, indent=2)

print(json.dumps(result, indent=2))