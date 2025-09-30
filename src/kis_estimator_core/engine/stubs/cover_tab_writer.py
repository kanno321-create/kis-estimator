"""Cover tab writer generating presentation summary."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import polars as pl

from . import evidence


def generate(formatter_payload: Dict[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    document = formatter_payload.get("document", {})
    totals = formatter_payload.get("totals", {})
    brand = formatter_payload.get("brand", {})

    summary = {
        "project_name": document.get("project_name", formatter_payload.get("project_id", "UNKNOWN")),
        "client": document.get("client", "UNKNOWN"),
        "project_number": document.get("project_number", "N/A"),
        "estimator": "KIS-AI",
        "revision": "RC2",
        "currency": formatter_payload.get("requested_totals", {}).get("currency", "KRW"),
        "issued_at": datetime.utcnow().isoformat() + "Z",
        "totals": totals,
        "brand": brand,
    }

    payload = {
        "summary": summary,
        "notes": ["Cover tab writer generated summary"],
    }

    artefacts = evidence.write_stage(
        "cover_tab_writer",
        payload,
        case_id=case_id,
        inputs={
            "document": document,
            "totals": totals,
            "brand": brand,
        },
        tables={
            "totals": pl.DataFrame([{"label": key, "value": value} for key, value in totals.items()]),
        },
    )

    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Cover tab writer compiled presentation summary",  # [REAL-LOGIC] cover metadata assembled
        ],
    }
