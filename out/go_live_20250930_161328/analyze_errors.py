import csv
import json
import sys
import collections

p = sys.argv[1]
rows = list(csv.DictReader(open(p, newline='')))
errs = [r for r in rows if not str(r.get("status_code", "")).startswith("2")]
by_code = dict(collections.Counter([r.get("status_code", "") for r in errs]))
by_latency = [float(r.get("latency_ms", 0)) for r in errs]

print(json.dumps({
    "total": len(rows),
    "errors": len(errs),
    "by_code": by_code,
    "error_latencies": by_latency,
    "error_lines": [i+2 for i, r in enumerate(rows) if not str(r.get("status_code", "")).startswith("2")]
}, ensure_ascii=False, indent=2))