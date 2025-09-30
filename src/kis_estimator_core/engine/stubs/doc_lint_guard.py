"""Documentation lint guard with DesignOps checks."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

import polars as pl

from . import evidence


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    color = color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", color):
        raise ValueError("Invalid hex colour")
    r = int(color[0:2], 16) / 255.0
    g = int(color[2:4], 16) / 255.0
    b = int(color[4:6], 16) / 255.0
    return r, g, b


def _luminance(rgb: tuple[float, float, float]) -> float:
    def adjust(channel: float) -> float:
        return math.pow((channel + 0.055) / 1.055, 2.4) if channel > 0.04045 else channel / 12.92

    r, g, b = (adjust(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(foreground: str, background: str = "FFFFFF") -> float:
    try:
        fg_l = _luminance(_hex_to_rgb(foreground))
        bg_l = _luminance(_hex_to_rgb(background))
    except ValueError:
        return 0.0
    lighter = max(fg_l, bg_l)
    darker = min(fg_l, bg_l)
    return (lighter + 0.05) / (darker + 0.05)


def inspect(formatter_payload: Dict[str, Any], cover_payload: Dict[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    def add_issue(code: str, description: str, where: str) -> None:
        issues.append({"code": code, "description": description, "where": where})

    document = formatter_payload.get("document", {})
    cover_summary = cover_payload.get("summary", {})
    totals = formatter_payload.get("totals", {})
    brand = formatter_payload.get("brand", {})
    named_ranges = formatter_payload.get("named_ranges", [])

    required_fields = {
        "project_name": document.get("project_name") or cover_summary.get("project_name"),
        "client": document.get("client") or cover_summary.get("client"),
        "project_number": document.get("project_number"),
        "date": document.get("date") or cover_summary.get("issued_at"),
    }
    for field, value in required_fields.items():
        if not value:
            add_issue("missing_field", f"Required field '{field}' is missing", field)

    subtotal = totals.get("subtotal")
    vat = totals.get("vat")
    grand = totals.get("grand_total") or totals.get("grand")
    if None in (subtotal, vat, grand):
        add_issue("totals_incomplete", "Totals fields must include subtotal/vat/grand_total", "totals")
    else:
        if abs((subtotal + vat) - grand) > 1.0:
            add_issue("totals_mismatch", "Subtotal + VAT does not equal grand total", "totals")

    primary_color = brand.get("primary_color") or brand.get("brand_primary_color")
    logo_ref = brand.get("logo_ref")
    font_size = brand.get("font_size")
    if not primary_color:
        add_issue("brand_color_missing", "Brand primary colour is required", "brand.primary_color")
    if not logo_ref:
        add_issue("brand_logo_missing", "Brand logo reference is required", "brand.logo_ref")
    if font_size is None or float(font_size) < 10:
        add_issue("font_size_low", "Minimum font size 10pt", "brand.font_size")
    if primary_color and _contrast_ratio(primary_color) < 4.5:
        add_issue("contrast_low", "Colour contrast ratio must be ≥ 4.5:1", "brand.primary_color")

    for entry in named_ranges:
        name = entry.get("name") if isinstance(entry, dict) else None
        value = entry.get("value") if isinstance(entry, dict) else None
        if not name:
            add_issue("named_range_missing", "Named range entry missing name", "named_ranges")
            continue
        if value in (None, ""):
            add_issue("named_range_empty", f"Named range '{name}' has no value", f"named_ranges.{name}")

    lint_errors = len(issues)
    payload = {
        "lint_errors": lint_errors,
        "issues": issues,
        "messages": [
            "DesignOps lint executed",  # [REAL-LOGIC] surfaced combined lint outcome
            "All checks passed" if lint_errors == 0 else f"Detected {lint_errors} issues",
        ],
    }

    tables = {}
    if issues:
        tables["lint_issues"] = pl.from_dicts(issues)

    artefacts = evidence.write_stage(
        "doc_lint_guard",
        payload,
        case_id=case_id,
        inputs={
            "document_fields": document,
            "cover_summary": cover_summary,
            "totals": totals,
            "brand": brand,
        },
        tables=tables,
    )

    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Doc lint guard evaluated brand/accessibility",  # [REAL-LOGIC] lint summary log
        ],
    }
