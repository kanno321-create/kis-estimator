"""Breaker placement critic evaluating optimisation quality."""

from __future__ import annotations

from typing import Any, Dict, List

import polars as pl

from . import evidence


THRESHOLD_BALANCE = 0.05


def review(placement_result: Dict[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    if "placements" not in placement_result:
        raise ValueError("Breaker placements missing 'placements'")

    issues: List[Dict[str, Any]] = []
    balance = float(placement_result.get("phase_balance", 0.0))
    clearance = int(placement_result.get("clearance_violations", 0))

    if balance > THRESHOLD_BALANCE:
        issues.append({
            "code": "phase_balance_high",
            "description": f"Phase balance {balance:.3f} exceeds threshold {THRESHOLD_BALANCE:.3f}",
        })
    if clearance > 0:
        issues.append({
            "code": "clearance_violation",
            "description": f"Detected {clearance} clearance violations",
        })

    score = max(0.0, 1.0 - balance - (0.1 * clearance))  # [REAL-LOGIC] penalise deviations from operational limits

    payload = {
        "score": round(score, 3),
        "issues": issues,
        "phase_balance": balance,
        "clearance_violations": clearance,
    }

    tables = {
        "critic_issues": pl.from_dicts(issues) if issues else pl.DataFrame({"code": [], "description": []}),
    }

    artefacts = evidence.write_stage(
        "breaker_critic",
        payload,
        case_id=case_id,
        inputs={"placement": {"phase_balance": balance, "clearance_violations": clearance}},
        tables=tables,
    )
    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Breaker critic evaluated placement quality",
        ],
    }
