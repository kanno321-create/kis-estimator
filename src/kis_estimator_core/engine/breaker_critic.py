#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Dict, List, Tuple
from _util_io import write_json, read_json, make_evidence, log, write_text, arg_parser, MetricsCollector

# Critical thresholds - constants
MAX_LIMITS = {
    "phase_imbalance_pct": 4.0,
    "clearances_violation": 0,
    "thermal_violation": 0,
    "row_heat_w": 650,
    "panel_heat_w": 2500,
    "min_clearance_mm": 50
}

def critique_placement(work_dir) -> dict:
    """Critique breaker placement against design rules."""
    work_path = Path(work_dir)

    # Load placement result
    placement_file = work_path / "placement" / "breaker_placement.json"
    if not placement_file.exists():
        return {"error": "No placement file found", "violations": [], "warnings": []}

    placement = read_json(placement_file)

    violations = []
    warnings = []
    violation_details = []

    # Check phase imbalance
    imbalance = placement.get("phase_imbalance_pct", 0)
    if imbalance > MAX_LIMITS["phase_imbalance_pct"]:
        violation = {
            "type": "phase_imbalance",
            "severity": "critical",
            "value": imbalance,
            "limit": MAX_LIMITS["phase_imbalance_pct"],
            "message": f"Phase imbalance {imbalance:.2f}% exceeds {MAX_LIMITS['phase_imbalance_pct']}% limit",
            "cause": "Uneven distribution of single-phase loads",
            "recommendation": "Redistribute single-phase breakers across phases"
        }
        violations.append(violation["message"])
        violation_details.append(violation)
    elif imbalance > MAX_LIMITS["phase_imbalance_pct"] * 0.875:  # 3.5%
        warnings.append(f"Phase imbalance {imbalance:.2f}% approaching limit")

    # Check clearance violations
    clearance_violations = placement.get("clearances_violation", 0)
    if clearance_violations > MAX_LIMITS["clearances_violation"]:
        violation = {
            "type": "clearance",
            "severity": "critical",
            "count": clearance_violations,
            "message": f"Found {clearance_violations} clearance violations",
            "cause": "Breakers placed too close together",
            "min_required_mm": MAX_LIMITS["min_clearance_mm"]
        }
        violations.append(violation["message"])
        violation_details.append(violation)

    # Check thermal violations
    thermal_violations = placement.get("thermal_violation", 0)
    if thermal_violations > MAX_LIMITS["thermal_violation"]:
        violation = {
            "type": "thermal",
            "severity": "critical",
            "count": thermal_violations,
            "message": f"Found {thermal_violations} thermal violations",
            "cause": "Excessive heat concentration in rows",
            "max_row_heat_w": MAX_LIMITS["row_heat_w"]
        }
        violations.append(violation["message"])
        violation_details.append(violation)

    # Check total panel heat
    total_heat = placement.get("total_heat_w", 0)
    if total_heat > MAX_LIMITS["panel_heat_w"]:
        violation = {
            "type": "panel_thermal",
            "severity": "critical",
            "value": total_heat,
            "limit": MAX_LIMITS["panel_heat_w"],
            "message": f"Total heat {total_heat:.1f}W exceeds panel rating {MAX_LIMITS['panel_heat_w']}W",
            "cause": "Too many high-current breakers"
        }
        violations.append(violation["message"])
        violation_details.append(violation)
    elif total_heat > MAX_LIMITS["panel_heat_w"] * 0.8:
        warnings.append(f"Total heat {total_heat:.1f}W approaching limit")

    # Check individual slot positions
    slots = placement.get("slots", [])
    for slot in slots:
        position = slot.get("position", {})
        row = position.get("row", 0)
        col = position.get("col", 0)

        # Validate position bounds
        if row < 0 or row > 20:
            violation = {
                "type": "position",
                "severity": "error",
                "slot_id": slot.get("id"),
                "breaker_id": slot.get("breaker_id"),
                "position": f"row={row}, col={col}",
                "message": f"Breaker {slot.get('breaker_id')} at invalid row {row}",
                "cause": "Position outside panel boundaries"
            }
            violations.append(violation["message"])
            violation_details.append(violation)

    # Calculate critique score
    score = 100
    score -= len(violations) * 20
    score -= len(warnings) * 5
    score = max(0, score)

    critique_result = {
        "ts": placement.get("ts", 0),
        "placement_file": str(placement_file),
        "violations": violations,
        "warnings": warnings,
        "violation_details": violation_details,
        "phase_imbalance_pct": imbalance,
        "total_heat_w": total_heat,
        "passed": len(violations) == 0,
        "score": score,
        "thresholds": MAX_LIMITS,
        "critic_pass": len(violations) == 0,  # Compatibility
        "metrics": {  # Compatibility
            "phase_imbalance_pct": imbalance,
            "clearance_violations": clearance_violations,
            "thermal_violations": thermal_violations,
            "total_heat_w": total_heat,
            "slot_count": len(slots)
        }
    }

    return critique_result

def _generate_critique_svg(critique_result: Dict, violations: List[Dict]) -> str:
    """Generate SVG visualization highlighting violations."""
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">',
        '<rect width="100%" height="100%" fill="#f8f8f8" stroke="#333" stroke-width="2"/>',
        '<text x="300" y="30" text-anchor="middle" font-size="20" font-weight="bold">Placement Critique</text>'
    ]

    # Draw status indicator
    status_color = "#4caf50" if critique_result["passed"] else "#f44336"
    status_text = "PASSED" if critique_result["passed"] else "FAILED"
    svg_parts.append(
        f'<rect x="250" y="50" width="100" height="30" fill="{status_color}" rx="5"/>'
    )
    svg_parts.append(
        f'<text x="300" y="70" text-anchor="middle" font-size="14" fill="white">{status_text}</text>'
    )

    # Draw score
    svg_parts.append(
        f'<text x="300" y="110" text-anchor="middle" font-size="16">Score: {critique_result["score"]}/100</text>'
    )

    # Draw violations
    y_pos = 150
    for i, violation in enumerate(violations[:5]):  # Show first 5 violations
        if isinstance(violation, dict):
            svg_parts.append(
                f'<circle cx="50" cy="{y_pos}" r="8" fill="#f44336"/>'
            )
            msg = violation.get("message", "")[:50] if violation.get("message") else ""
            svg_parts.append(
                f'<text x="70" y="{y_pos + 5}" font-size="12">{violation.get("type", "unknown")}: {msg}...</text>'
            )
            y_pos += 30

    # Draw metrics
    svg_parts.append(
        f'<text x="50" y="320" font-size="14">Phase Imbalance: {critique_result.get("phase_imbalance_pct", 0):.2f}%</text>'
    )
    svg_parts.append(
        f'<text x="50" y="340" font-size="14">Total Heat: {critique_result.get("total_heat_w", 0):.1f}W</text>'
    )

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)

def main():
    ap = arg_parser()
    args = ap.parse_args()
    work = Path(args.work) if hasattr(args, 'work') else Path("KIS/Work/current")

    metrics = MetricsCollector()

    with metrics.timer("breaker_critic"):
        result = critique_placement(work)
        out = work / "placement" / "breaker_critic.json"
        write_json(out, result)

        # Generate JSON evidence
        evidence_data = {
            "pass": result["passed"],
            "score": result["score"],
            "violations_count": len(result["violations"]),
            "warnings_count": len(result["warnings"]),
            "phase_imbalance": result["phase_imbalance_pct"]
        }
        make_evidence(out.with_suffix(""), evidence_data, "json")

        # Generate SVG visualization if there are violations
        if result.get("violation_details"):
            svg_content = _generate_critique_svg(result, result["violation_details"])
            svg_path = out.with_suffix(".svg")
            write_text(svg_path, svg_content)
            log(f"Critique visualization saved to {svg_path}", "INFO")

        # Log summary
        if result["passed"]:
            log(f"OK Placement passed all checks (score={result['score']})")
        else:
            log(f"FAIL Placement has {len(result['violations'])} violations", "ERROR")

    metrics.save()
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    exit(main())