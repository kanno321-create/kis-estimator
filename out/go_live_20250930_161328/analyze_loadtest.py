import csv
import json
import statistics
import glob

# Find the latest loadtest.csv
files = glob.glob("out/go_live_*/reports/loadtest.csv")
if not files:
    print(json.dumps({"ok": False, "reason": "no_csv"}))
    exit(0)

f = files[-1]
latencies = []
codes = []

with open(f, newline='') as fh:
    rd = csv.DictReader(fh)
    for r in rd:
        try:
            lat = float(r.get("latency_ms", 0))
            if lat > 0:
                latencies.append(lat)
        except:
            pass
        codes.append(r.get("status_code", ""))

total = len(latencies)
ok_count = sum(1 for c in codes if str(c).startswith("2"))
err_count = total - ok_count

# Calculate P95
if total >= 100:
    p95 = statistics.quantiles(latencies, n=100)[94]
elif latencies:
    sorted_lat = sorted(latencies)
    p95_idx = int(len(latencies) * 0.95) - 1
    p95 = sorted_lat[p95_idx] if p95_idx >= 0 else sorted_lat[-1]
else:
    p95 = None

# RPS calculation (assuming 60s test)
rps = total / 60.0 if total else 0.0

out = {
    "ok": True,
    "total": total,
    "ok_count": ok_count,
    "err_count": err_count,
    "err_pct": (err_count/total*100.0) if total else 0.0,
    "p95_ms": p95,
    "rps": rps,
    "mean_ms": statistics.mean(latencies) if latencies else 0,
    "min_ms": min(latencies) if latencies else 0,
    "max_ms": max(latencies) if latencies else 0
}

print(json.dumps(out, ensure_ascii=False, indent=2))