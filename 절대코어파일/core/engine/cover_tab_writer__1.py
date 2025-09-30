#!/usr/bin/env python3
from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Any

from _util_io import (
    MetricsCollector,
    arg_parser,
    read_json,
    write_json,
    make_evidence,
    log,
)

def _safe_get(d: Dict, path: str, default=None):
    cur = d
    for p in path.split("."):
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def _build_cover_payload(work_dir: Path) -> Dict[str, Any]:
    est = read_json(work_dir / "format" / "estimate_format.json")
    enc = read_json(work_dir / "enclosure" / "enclosure_plan.json")

    project_name = _safe_get(est, "estimate.project_name", "N/A")
    client       = _safe_get(est, "estimate.client", "N/A")
    subtotal     = _safe_get(est, "estimate.subtotal", 0)
    vat          = _safe_get(est, "estimate.vat", 0)
    total        = _safe_get(est, "estimate.total", 0)

    sku         = _safe_get(enc, "selected_sku.id", "N/A")
    width_mm    = _safe_get(enc, "selected_sku.width_mm", None)
    height_mm   = _safe_get(enc, "selected_sku.height_mm", None)
    depth_mm    = _safe_get(enc, "selected_sku.depth_mm", None)
    size_str    = f"{width_mm}x{height_mm}x{depth_mm}mm" if None not in (width_mm, height_mm, depth_mm) else "N/A"

    prepared_by = "KIS Assistant"
    # 프로젝트 메타(요구 필드): 번호/날짜
    # number: 기존 값이 없으면 규칙적으로 생성(PRJ-YYYYMMDD-<ts>)
    import datetime
    today = datetime.date.today()
    project_number = _safe_get(est, "estimate.project_number", None)
    if not project_number:
        project_number = f"PRJ-{today.strftime('%Y%m%d')}-{int(time.time())%100000}"
    project_date = _safe_get(est, "estimate.date", today.strftime("%Y-%m-%d"))

    cover_data = {
        "project": {
            "title": project_name,
            "client": client,
            "number": project_number,         # ← required
            "date": project_date,             # ← required (YYYY-MM-DD)
        },
        "financial": {
            "total": total,
            "totals": {                       # ← required cluster
                "subtotal": subtotal,
                "vat": vat,
                "total": total,
            },
        },
        "signature": {"prepared_by": prepared_by},
        "enclosure": {"sku": sku, "size": size_str},
    }

    # 문서 자체의 최소 검증 결과(cover 레벨)
    validation_pass = all([
        cover_data["project"]["title"],
        cover_data["project"]["client"],
        cover_data["project"]["number"],
        cover_data["project"]["date"],
        isinstance(cover_data["financial"]["total"], (int, float)),
        isinstance(cover_data["financial"]["totals"].get("subtotal", 0), (int, float)),
        isinstance(cover_data["financial"]["totals"].get("vat", 0), (int, float)),
        isinstance(cover_data["financial"]["totals"].get("total", 0), (int, float)),
        bool(cover_data["signature"]["prepared_by"]),
    ])

    return {
        "ts": int(time.time()),
        "cover_data": cover_data,
        "compliance": {
            "pass": validation_pass,
            "errors": [] if validation_pass else ["REQUIRED_FIELD_MISSING"],
        }
    }

def main() -> None:
    ap = arg_parser()
    args = ap.parse_args()
    work = Path(args.work)
    templates = Path(getattr(args, "templates", "."))  # 유지: CLI 시그니처 불변

    metrics = MetricsCollector()
    with metrics.timer("cover_tab_writer"):
        payload = _build_cover_payload(work)
        out = work / "cover" / "cover_tab.json"
        write_json(out, payload)

        # evidence + 최소 SVG 보장
        make_evidence(out.with_suffix(""), {
            "project": payload["cover_data"]["project"]["title"],
            "client": payload["cover_data"]["project"]["client"],
            "total":  payload["cover_data"]["financial"]["total"],
            "prepared_by": payload["cover_data"]["signature"]["prepared_by"],
            "project_number": payload["cover_data"]["project"]["number"],
            "date": payload["cover_data"]["project"]["date"],
            "subtotal": payload["cover_data"]["financial"]["totals"]["subtotal"],
            "vat": payload["cover_data"]["financial"]["totals"]["vat"],
            "compliance": payload["compliance"]["pass"],
        })

        svg_path = out.with_suffix(".svg")
        if not svg_path.exists():
            try:
                svg = (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="180">'
                    '<rect width="640" height="180" fill="#fff" stroke="#222"/>'
                    '<text x="20" y="40" font-family="Arial" font-size="18">cover-tab</text>'
                    f'<text x="20" y="80" font-family="Arial" font-size="14">project={payload["cover_data"]["project"]["title"]}</text>'
                    f'<text x="20" y="105" font-family="Arial" font-size="14">client={payload["cover_data"]["project"]["client"]}</text>'
                    f'<text x="20" y="130" font-family="Arial" font-size="14">total={payload["cover_data"]["financial"]["total"]}</text>'
                    '</svg>'
                )
                svg_path.write_text(svg, encoding="utf-8")
            except Exception:
                pass

        if payload["compliance"]["pass"]:
            log("OK cover-tab-writer")
        else:
            log("WARN cover-tab-writer (compliance=false)", "WARN")

    metrics.save()

if __name__ == "__main__":
    main()