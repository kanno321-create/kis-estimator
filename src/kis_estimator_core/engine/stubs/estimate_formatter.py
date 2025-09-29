"""Estimate formatter producing financial outputs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import polars as pl

from ..util import templates
from . import evidence


def _loads_frame(loads: list[dict[str, Any]]) -> pl.DataFrame:
    frame = pl.from_dicts(loads)
    if "heat_w" not in frame.columns or "width_unit" not in frame.columns:
        raise ValueError("Loads must include 'heat_w' and 'width_unit'")
    return frame.with_columns([
        pl.col("heat_w").cast(pl.Float64),
        pl.col("width_unit").cast(pl.Float64),
        pl.col("kva").cast(pl.Float64).fill_null(0.0),
    ])


def _document_fields(request: Dict[str, Any]) -> Dict[str, Any]:
    document = request.get("document", {})
    project_id = request["project_id"]
    project_name = document.get("project_name") or project_id
    client = document.get("client") or request.get("client", "KIS-CLIENT")
    project_number = document.get("project_number") or f"KIS-{project_id}"
    date = document.get("date") or datetime.utcnow().date().isoformat()
    return {
        "project_id": project_id,
        "project_name": project_name,
        "client": client,
        "project_number": project_number,
        "date": date,
    }


def _brand_profile(request: Dict[str, Any]) -> Dict[str, Any]:
    brand = request.get("brand", {})
    profile = {
        "primary_color": brand.get("primary_color") or brand.get("brand_primary_color") or "003366",
        "logo_ref": brand.get("logo_ref") or "assets/logo.svg",
        "font_size": float(brand.get("font_size") or 11.0),
    }
    return profile


def format_estimate(request: Dict[str, Any], breaker_review: Dict[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    loads = request.get("loads", [])
    if not loads:
        raise ValueError("Estimate formatter requires loads")

    loads_df = _loads_frame(loads)
    doc = _document_fields(request)
    brand = _brand_profile(request)

    base_cost = float(loads_df["heat_w"].sum() * 4200)
    width_cost = float(loads_df["width_unit"].sum() * 90000)
    labor_cost = float(loads_df.height * 85000)
    materials = base_cost + width_cost
    labor = labor_cost
    subtotal = materials + labor
    vat = round(subtotal * 0.1, 2)
    grand_total = round(subtotal + vat, 2)

    totals = {
        "materials": round(materials, 2),
        "labor": round(labor, 2),
        "subtotal": round(subtotal, 2),
        "vat": vat,
        "grand_total": grand_total,
    }

    named_ranges = [
        {"name": "ProjectName", "value": doc["project_name"]},
        {"name": "Client", "value": doc["client"]},
        {"name": "ProjectNumber", "value": doc["project_number"]},
        {"name": "Date", "value": doc["date"]},
        {"name": "Subtotal", "value": totals["subtotal"]},
        {"name": "VAT", "value": totals["vat"]},
        {"name": "GrandTotal", "value": totals["grand_total"]},
    ]

    injected = templates.inject_named_ranges({"project_id": request["project_id"]}, [nr["name"] for nr in named_ranges])

    payload = {
        "project_id": request["project_id"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "totals": totals,
        "document": doc,
        "brand": brand,
        "named_ranges": named_ranges,
        "named_range_log": injected.get("log", []),
        "breaker_score": breaker_review.get("critic", {}).get("score", breaker_review.get("score", 0.0)),
    }

    payload["requested_totals"] = request.get("requested_totals", {})
    artefacts = evidence.write_stage(
        "estimate_formatter",
        payload,
        case_id=case_id,
        inputs={
            "document": doc,
            "brand": brand,
            "breaker_review": breaker_review,
        },
        tables={
            "loads": loads_df,
        },
    )

    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Estimate formatter produced financial summary",  # [REAL-LOGIC] totals derived from loads
        ],
    }
