"""Breaker placement logic using OR-Tools for phase balance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

import polars as pl
from ortools.sat.python import cp_model

from . import evidence


@dataclass
class AssignmentResult:
    phase_totals: Dict[str, float]
    phase_width_units: Dict[str, float]
    layout: List[Dict[str, Any]]
    phase_balance: float
    clearance_violations: int


def _loads_frame(loads: List[Dict[str, Any]]) -> pl.DataFrame:
    frame = pl.from_dicts(loads)
    expected = {"id", "width_unit", "heat_w"}
    missing = expected - set(frame.columns)
    if missing:
        raise ValueError(f"Loads missing required keys: {sorted(missing)}")
    return frame.with_columns([
        pl.col("width_unit").cast(pl.Float64),
        pl.col("heat_w").cast(pl.Float64),
        pl.col("phase").cast(pl.Utf8).fill_null(""),
    ])


def _available_phases(frame: pl.DataFrame) -> List[str]:
    phases = [p for p in frame["phase"].unique().to_list() if p]
    if not phases:
        return ["A", "B", "C"]
    canonical = ["A", "B", "C"]
    ordered = [p for p in canonical if p in phases]
    ordered.extend([p for p in phases if p not in ordered])
    while len(ordered) < 3:
        for candidate in canonical:
            if candidate not in ordered:
                ordered.append(candidate)
                break
    return ordered[:3]


def _build_assignment(frame: pl.DataFrame, phases: List[str]) -> AssignmentResult:
    model = cp_model.CpModel()
    scale = 1000

    assign_vars: Dict[tuple[int, int], cp_model.IntVar] = {}
    fixed_totals = {phase: 0 for phase in phases}

    loads_list = list(frame.iter_rows(named=True))
    variable_rows: List[int] = []
    for idx, row in enumerate(loads_list):
        declared_phase = row.get("phase") or ""
        heat_val = int(round(float(row["heat_w"]) * scale))
        if declared_phase and declared_phase in phases:
            fixed_totals[declared_phase] += heat_val
            continue
        variable_rows.append(idx)
        for p_idx, phase in enumerate(phases):
            assign_vars[(idx, p_idx)] = model.NewBoolVar(f"assign_{idx}_{phase}")
        model.Add(sum(assign_vars[(idx, p_idx)] for p_idx in range(len(phases))) == 1)

    phase_heat_vars: Dict[str, cp_model.IntVar] = {}
    max_heat = model.NewIntVar(0, 10**9, "max_heat")
    min_heat = model.NewIntVar(0, 10**9, "min_heat")

    for p_idx, phase in enumerate(phases):
        total_expr = fixed_totals[phase]
        affine_terms = []
        for idx in variable_rows:
            heat_val = int(round(float(loads_list[idx]["heat_w"]) * scale))
            affine_terms.append(assign_vars[(idx, p_idx)] * heat_val)
        if affine_terms:
            phase_var = model.NewIntVar(0, 10**9, f"phase_heat_{phase}")
            model.Add(phase_var == total_expr + sum(affine_terms))
        else:
            phase_var = model.NewConstant(total_expr)
        phase_heat_vars[phase] = phase_var
        model.Add(phase_var <= max_heat)
        model.Add(phase_var >= min_heat)

    model.Minimize(max_heat - min_heat)  # [REAL-LOGIC] minimise heat imbalance across phases

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("Breaker placement optimisation failed")

    assigned_heat = {phase: solver.Value(var) / scale for phase, var in phase_heat_vars.items()}

    layout: List[Dict[str, Any]] = []
    phase_width_units = {phase: 0.0 for phase in phases}
    slot_index = 1

    for idx, row in enumerate(loads_list):
        chosen_phase = row.get("phase") or ""
        if not chosen_phase:
            for p_idx, phase in enumerate(phases):
                var = assign_vars.get((idx, p_idx))
                if var is not None and solver.BooleanValue(var):
                    chosen_phase = phase
                    break
        if not chosen_phase:
            chosen_phase = phases[(slot_index - 1) % len(phases)]
        width_unit = float(row["width_unit"])
        heat_w = float(row["heat_w"])
        phase_width_units[chosen_phase] += width_unit
        layout.append(
            {
                "slot": f"S{slot_index:02d}",
                "breaker_id": row["id"],
                "phase": chosen_phase,
                "heat_w": heat_w,
                "width_unit": width_unit,
            }
        )
        slot_index += 1

    heat_values = list(assigned_heat.values())
    if not heat_values:
        raise RuntimeError("No phase heat values computed")
    total_heat = sum(heat_values)
    phase_balance = 0.0
    if total_heat:
        phase_balance = (max(heat_values) - min(heat_values)) / total_heat

    return AssignmentResult(
        phase_totals=assigned_heat,
        phase_width_units=phase_width_units,
        layout=layout,
        phase_balance=phase_balance,
        clearance_violations=_check_clearance(layout),
    )


def _check_clearance(layout: List[Dict[str, Any]]) -> int:
    if not layout:
        return 0
    total_heat = sum(item["heat_w"] for item in layout)
    threshold = max(total_heat * 0.25, 1.0)
    violations = 0
    ordered = sorted(layout, key=lambda item: item["heat_w"], reverse=True)
    for idx in range(len(ordered) - 1):
        if ordered[idx]["heat_w"] + ordered[idx + 1]["heat_w"] > threshold:
            violations += 1
    return violations


def place(plan: Dict[str, Any], request: Mapping[str, Any], case_id: str = evidence.CASE_DEFAULT) -> Dict[str, Any]:
    if "slot_unit" not in plan:
        raise ValueError("Enclosure plan missing 'slot_unit'")
    loads: List[Dict[str, Any]] = list(request.get("loads", []))
    if not loads:
        raise ValueError("Breaker placement requires loads")

    loads_df = _loads_frame(loads)
    phases = _available_phases(loads_df)
    assignment = _build_assignment(loads_df, phases)

    payload = {
        "placements": assignment.layout,
        "phase_balance": float(round(assignment.phase_balance, 4)),
        "clearance_violations": int(assignment.clearance_violations),
        "phase_totals": assignment.phase_totals,
        "slot_unit": float(plan["slot_unit"]),
    }

    distribution_df = pl.DataFrame(
        [
            {
                "phase": phase,
                "heat_w": assignment.phase_totals.get(phase, 0.0),
                "width_unit": assignment.phase_width_units.get(phase, 0.0),
            }
            for phase in phases
        ]
    )

    artefacts = evidence.write_stage(
        "breaker_placer",
        payload,
        case_id=case_id,
        inputs={
            "loads_summary": {
                "count": int(loads_df.height),
                "phases": phases,
                "total_heat": float(loads_df["heat_w"].sum()),
                "total_width_unit": float(loads_df["width_unit"].sum()),
            }
        },
        tables={
            "phase_distribution": distribution_df,
            "layout": pl.from_dicts(assignment.layout),
        },
    )

    return {
        "payload": payload,
        "evidence": artefacts,
        "logs": [
            "Breaker placer balanced phases",  # [REAL-LOGIC] optimisation summary
        ],
    }
