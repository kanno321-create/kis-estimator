#!/usr/bin/env python3
import json, os, argparse, pathlib, time, sys
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime

class MetricsCollector:
    def __init__(self):
        self.metrics = {"steps": {}, "total_ms": 0, "errors": []}
    
    @contextmanager
    def timer(self, step_name):
        start = time.time()
        try:
            yield
            elapsed_ms = int((time.time() - start) * 1000)
            self.metrics["steps"][step_name] = {"ms": elapsed_ms, "status": "OK"}
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            self.metrics["steps"][step_name] = {"ms": elapsed_ms, "status": "FAIL", "error": str(e)}
            self.metrics["errors"].append({"step": step_name, "error": str(e)})
            raise
    
    def save(self, path=".meta/metrics.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.metrics["total_ms"] = sum(s.get("ms", 0) for s in self.metrics["steps"].values())
        self.metrics["timestamp"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def write_json(p: Path, obj: dict):
    ensure_dir(p.parent)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def read_json(p: Path) -> dict:
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def write_text(p: Path, text: str):
    ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")

def make_evidence(base: Path, data=None, kind="svg"):
    """Generate evidence files with actual data visualization"""
    if kind == "svg":
        if data and isinstance(data, dict):
            # Create data-driven SVG
            svg_parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">']
            svg_parts.append('<rect width="100%" height="100%" fill="#f8f9fa"/>')
            svg_parts.append('<text x="10" y="20" font-size="14" font-weight="bold">Evidence: {}</text>'.format(base.name))
            
            y_pos = 50
            for key, value in list(data.items())[:8]:  # Show first 8 items
                svg_parts.append(f'<text x="20" y="{y_pos}" font-size="12">{key}: {value}</text>')
                y_pos += 20
            
            svg_parts.append('</svg>')
            svg = ''.join(svg_parts)
        else:
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><rect width="100%" height="100%" fill="#e8f4f8"/><text x="10" y="80" font-size="14">Evidence for {base.name}</text></svg>'
        write_text(base.with_suffix(".svg"), svg)
    else:
        # PNG placeholder
        write_text(base.with_suffix(".png"), "")
    
    evidence_data = {"ok": True, "target": base.name, "timestamp": datetime.now().isoformat()}
    if data:
        evidence_data["summary"] = data
    write_json(base.parent / (base.stem + "_evidence.json"), evidence_data)

def arg_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="KIS/Work/current")
    ap.add_argument("--templates", default="KIS/Templates")
    ap.add_argument("--rules", default="KIS/Rules")
    return ap

def log(msg, level="INFO"):
    print(f"[{level}] {msg}", file=sys.stderr if level == "ERROR" else sys.stdout)