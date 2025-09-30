"""Enclosure solver upgraded with real calculations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import duckdb
import polars as pl

from ..util import guard
from . import evidence

CATALOG_DIR = Path(__file__).resolve().parents[3] / "Templates" / "catalog"
ENCLOSURE_CATALOG = CATALOG_DIR / "enclosures.csv"


def _validate_request(request: Dict[str, Any]) -> None:
    required_keys = ["loads", "enclosure", "ip_min"]
    for key in required_keys:
        if key not in request:
            raise ValueError(f"Estimate request missing '{key}'")
    enclosure = request.get("enclosure", {})
    for dim in ("required_w", "required_h", "required_d"):
        if dim not in enclosure:
            raise ValueError(f"Enclosure requirements missing '{dim}'")
    if not request.get("loads"):
        raise ValueError("No loads provided for enclosure solver")


def _loads_frame(loads: List[Dict[str, Any]]) -> pl.DataFrame:
    frame = pl.from_dicts(loads)
    expected_columns = {"id", "width_unit", "heat_w"}
    missing = expected_columns - set(frame.columns)
    if missing:
        raise ValueError(f"Load entries missing required fields: {sorted(missing)}")
    return frame.with_columns([
        pl.col("width_unit").cast(pl.Float64),
        pl.col("heat_w").cast(pl.Float64),
    ])


def _load_catalog() -> pl.DataFrame:
    guard.ensure_whitelisted(ENCLOSURE_CATALOG)
    return pl.read_csv(ENCLOSURE_CATALOG)


def _ip_to_int(ip_code: str) -> int:
    digits = "".join(filter(str.isdigit, str(ip_code)))
    return int(digits or 0)


def solve(request: Dict[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    _validate_request(request)
    loads = request["loads"]
    enclosure_req = request["enclosure"]
    ip_min = request.get("ip_min", "IP54")

    loads_df = _loads_frame(loads)
    totals = loads_df.select([
        pl.count().alias("count"),
        pl.sum("width_unit").alias("total_width_unit"),
        pl.sum("heat_w").alias("total_heat_w"),
    ]).to_dict(as_series=False)
    total_width = float(totals["total_width_unit"][0])
    total_heat = float(totals["total_heat_w"][0])

    enclosures_df = _load_catalog()
    if enclosures_df.is_empty():
        raise RuntimeError("Enclosure catalog is empty")

    con = duckdb.connect()
    con.register("enclosures", enclosures_df.to_arrow())

    req_w = float(enclosure_req["required_w"])
    req_h = float(enclosure_req["required_h"])
    req_d = float(enclosure_req["required_d"])
    ip_required = _ip_to_int(ip_min)

    query = """
    SELECT
        model,
        W,
        H,
        D,
        ip_rating,
        max_heat_w,
        slot_unit,
        price,
        LEAST(? / NULLIF(W, 0), 1) AS w_util_ratio,
        LEAST(? / NULLIF(H, 0), 1) AS h_util_ratio,
        LEAST(? / NULLIF(D, 0), 1) AS d_util_ratio,
        LEAST(? / NULLIF(max_heat_w, 0), 1) AS heat_util_ratio,
        CAST(REPLACE(ip_rating, 'IP', '') AS INTEGER) AS ip_numeric
    FROM enclosures
    WHERE W >= ?
      AND H >= ?
      AND D >= ?
      AND max_heat_w >= ?
      AND CAST(REPLACE(ip_rating, 'IP', '') AS INTEGER) >= ?
    """
    params = [req_w, req_h, req_d, total_heat, req_w, req_h, req_d, total_heat, ip_required]
    candidates_arrow = con.execute(query, params).fetch_arrow_table()
    con.close()

    candidates_df = pl.from_arrow(candidates_arrow)
    if candidates_df.is_empty():
        raise RuntimeError("No enclosure candidates satisfy requirements")

    min_price = float(candidates_df["price"].min())
    max_price = float(candidates_df["price"].max())
    price_range = max(max_price - min_price, 1e-6)

    candidates_df = candidates_df.with_columns([
        pl.min_horizontal(
            pl.col("w_util_ratio"),
            pl.col("h_util_ratio"),
            pl.col("d_util_ratio"),
            pl.col("heat_util_ratio"),
        ).alias("fit_score"),
        ((pl.col("price") - min_price) / price_range).alias("price_norm"),
    ])
    candidates_df = candidates_df.with_columns([
        (0.5 * pl.col("price_norm") + 0.5 * (1 - pl.col("fit_score"))).alias("balanced_score")  # [REAL-LOGIC] combine cost and fit for ranking
    ])

    sorted_by_price = candidates_df.sort("price")
    sorted_by_fit = candidates_df.sort("fit_score", descending=True)
    sorted_by_balanced = candidates_df.sort("balanced_score")

    def _select_unique(frames: List[pl.DataFrame]) -> List[Dict[str, Any]]:
        seen: set[str] = set()
        result: List[Dict[str, Any]] = []
        for frame in frames:
            for row in frame.iter_rows(named=True):
                model = str(row["model"])
                if model in seen:
                    continue
                seen.add(model)
                result.append(row)
                if len(result) == 3:
                    return result
        return result

    top_rows = _select_unique([sorted_by_price, sorted_by_fit, sorted_by_balanced, candidates_df])
    chosen = sorted_by_balanced.to_dicts()[0]

    payload = {
        "chosen_model": chosen["model"],
        "fit_score": float(chosen["fit_score"]),
        "gaps": {
            "W": round(1 - float(chosen["w_util_ratio"]), 4),
            "H": round(1 - float(chosen["h_util_ratio"]), 4),
            "D": round(1 - float(chosen["d_util_ratio"]), 4),
            "HEAT": round(1 - float(chosen["heat_util_ratio"]), 4),
        },
        "utilisation": {
            "W": float(chosen["w_util_ratio"]),
            "H": float(chosen["h_util_ratio"]),
            "D": float(chosen["d_util_ratio"]),
            "HEAT": float(chosen["heat_util_ratio"]),
        },
        "ip_rating": chosen["ip_rating"],
        "slot_unit": float(chosen["slot_unit"]),
        "max_heat_w": float(chosen["max_heat_w"]),
        "price": float(chosen["price"]),
    }

    candidate_table = candidates_df.with_columns([
        (1 - pl.col("w_util_ratio")).alias("w_gap"),
        (1 - pl.col("h_util_ratio")).alias("h_gap"),
        (1 - pl.col("d_util_ratio")).alias("d_gap"),
        (1 - pl.col("heat_util_ratio")).alias("heat_gap"),
    ])

    artefacts = evidence.write_stage(
        "enclosure_solver",
        payload,
        case_id=case_id,
        inputs={
            "requirements": {
                "required_w": req_w,
                "required_h": req_h,
                "required_d": req_d,
                "ip_min": ip_min,
                "total_width_unit": total_width,
                "total_heat_w": total_heat,
                "load_count": int(totals["count"][0]),
            },
        },
        tables={
            "candidates": candidate_table,
        },
    )

    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Enclosure solver computed fit score",  # [REAL-LOGIC] Operational log for traceability
        ],
    }
