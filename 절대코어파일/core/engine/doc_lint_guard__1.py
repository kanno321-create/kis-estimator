#!/usr/bin/env python3
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from _util_io import write_json, read_json, make_evidence, log, write_text, arg_parser, MetricsCollector

# Required fields for documents
REQUIRED_FIELDS = {
    "cover": [("cover_data.project.title", "cover_data.project.title"),
              ("cover_data.project.client", "cover_data.project.client"),
              ("cover_data.financial.total", "cover_data.financial.total"),
              ("cover_data.signature.prepared_by", "cover_data.signature.prepared_by")],
    "placement": [("phase_imbalance_pct", "phase_imbalance_pct"),
                  ("clearances_violation", "clearances_violation"),
                  ("thermal_violation", "thermal_violation")],
    "enclosure": [("selected_sku.sku", "selected_sku.sku"),
                  ("selected_sku.fit_score", "selected_sku.fit_score")],
    "format": [("named_ranges.total", "named_ranges.total"),
               ("format_lint.errors", "format_lint.errors")]
}

def lint_documents(work_dir) -> dict:
    """Final document quality check with detailed error reporting."""
    work_path = Path(work_dir)

    errors = []
    warnings = []
    overflow_risks = []
    font_substitutions = []
    
    # Check all generated documents
    documents = {
        "enclosure": work_path / "enclosure" / "enclosure_plan.json",
        "placement": work_path / "placement" / "breaker_placement.json",
        "critic": work_path / "placement" / "breaker_critic.json",
        "format": work_path / "format" / "estimate_format.json",
        "cover": work_path / "cover" / "cover_tab.json",
        "spatial": work_path / "spatial" / "spatial_report.json"
    }
    
    doc_status = {}
    
    for doc_name, doc_path in documents.items():
        if not doc_path.exists():
            errors.append(f"Missing document: {doc_name}")
            doc_status[doc_name] = "MISSING"
            continue
        
        try:
            data = read_json(doc_path)
            doc_status[doc_name] = "OK"

            # Check required fields for each document type
            if doc_name in REQUIRED_FIELDS:
                for field_path, display_name in REQUIRED_FIELDS[doc_name]:
                    value = data
                    for part in field_path.split('.'):
                        value = value.get(part, {}) if isinstance(value, dict) else None
                        if value is None:
                            break

                    if value is None:
                        errors.append(f"Missing required field: {display_name} in {doc_name}")

            # Document-specific checks
            if doc_name == "enclosure":
                fit_score = data.get("selected_sku", {}).get("fit_score", 0)
                if fit_score < 0.93:
                    errors.append(f"Enclosure fit_score {fit_score:.3f} below 0.93 threshold")
                    errors.append({
                        "doc": "enclosure",
                        "field": "fit_score",
                        "value": fit_score,
                        "threshold": 0.93,
                        "cause": "Suboptimal enclosure selection"
                    })

            elif doc_name == "placement":
                imbalance = data.get("phase_imbalance_pct", 100)
                if imbalance > 4.0:
                    errors.append(f"Phase imbalance {imbalance:.2f}% exceeds 4.0%")
                if data.get("clearances_violation", 1) > 0:
                    errors.append(f"Clearance violations: {data.get('clearances_violation')}")
                if data.get("thermal_violation", 1) > 0:
                    errors.append(f"Thermal violations: {data.get('thermal_violation')}")

            elif doc_name == "critic":
                if not data.get("critic_pass", False) and not data.get("passed", False):
                    warnings.append(f"Critic validation failed: {len(data.get('violations', []))} violations")

            elif doc_name == "format":
                lint_errors = data.get("format_lint", {}).get("errors", 0)
                if lint_errors > 0:
                    errors.append(f"Format lint errors: {lint_errors}")
                    for err in data.get("format_lint", {}).get("error_details", [])[:3]:
                        errors.append(f"  - {err}")

            elif doc_name == "cover":
                if not data.get("compliance", {}).get("pass", True):
                    errors.append(f"Cover compliance failed")

            # Check for text overflow risks
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 250:
                    overflow_risks.append({
                        "doc": doc_name,
                        "field": key,
                        "length": len(value),
                        "text_preview": value[:50] + "..."
                    })

        except Exception as e:
            errors.append(f"Invalid JSON in {doc_name}: {str(e)}")
            doc_status[doc_name] = "INVALID"
    
    # Check evidence files
    evidence_count = 0
    for doc_path in documents.values():
        if doc_path.exists():
            svg_path = doc_path.with_suffix(".svg")
            json_path = doc_path.parent / (doc_path.stem + "_evidence.json")
            if svg_path.exists():
                evidence_count += 1
            if json_path.exists():
                evidence_count += 1
    
    # Comprehensive field completeness checks
    field_checks = {
        "project_name": False,
        "client": False,
        "totals": False,
        "signature": False,
        "date": False,
        "project_number": False
    }

    cover_file = documents["cover"]
    if cover_file.exists():
        try:
            cover_data = read_json(cover_file)
            project = cover_data.get("cover_data", {}).get("project", {})
            financial = cover_data.get("cover_data", {}).get("financial", {})
            signature = cover_data.get("cover_data", {}).get("signature", {})

            field_checks["project_name"] = bool(project.get("title"))
            field_checks["client"] = bool(project.get("client"))
            field_checks["date"] = bool(project.get("date"))
            field_checks["project_number"] = bool(project.get("number"))
            field_checks["totals"] = bool(financial.get("totals"))
            field_checks["signature"] = bool(signature.get("prepared_by"))
        except:
            pass

    incomplete_fields = [k for k, v in field_checks.items() if not v]
    if incomplete_fields:
        errors.append(f"Incomplete required fields: {', '.join(incomplete_fields)}")

    # Font substitution check (simulated)
    for doc_name in ["cover", "format"]:
        doc_path = documents.get(doc_name)
        if doc_path and doc_path.exists():
            # Simulate font check
            if "Arial" not in str(doc_path):  # Placeholder logic
                font_substitutions.append({
                    "doc": doc_name,
                    "original_font": "Calibri",
                    "substituted_font": "Arial",
                    "reason": "Font not embedded"
                })
    
    # Calculate quality metrics
    total_errors = len([e for e in errors if isinstance(e, str)])
    total_warnings = len(warnings)
    quality_score = max(0, 100 - (total_errors * 10) - (total_warnings * 2))

    # Final result
    result = {
        "ts": int(time.time()),
        "errors": total_errors,
        "warnings": total_warnings,
        "error_details": errors[:15],  # More detailed errors
        "warning_details": warnings[:10],
        "documents": doc_status,
        "evidence_files": evidence_count,
        "field_completeness": field_checks,
        "overflow_risks": overflow_risks[:5],
        "font_substitutions": font_substitutions,
        # 게이트 소비자 호환: pass(True/False) + validation_pass 동시 제공
        "pass": (total_errors == 0),
        "validation_pass": (total_errors == 0),
        "status": "PASS" if total_errors == 0 else "FAIL",
        "quality_score": quality_score,
        "validation_summary": {
            "documents_checked": len(documents),
            "documents_valid": sum(1 for v in doc_status.values() if v == "OK"),
            "required_fields_complete": sum(1 for v in field_checks.values() if v),
            "required_fields_total": len(field_checks)
        }
    }
    
    return result

def _generate_lint_report_svg(result: Dict) -> str:
    """Generate SVG visualization of lint results."""
    svg_parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="700" height="500" viewBox="0 0 700 500">',
        '<rect width="100%" height="100%" fill="#f9f9f9" stroke="#333" stroke-width="2"/>',
        '<text x="350" y="30" text-anchor="middle" font-size="22" font-weight="bold">Document Lint Report</text>'
    ]

    # Status indicator
    status_color = "#4caf50" if result["pass"] else "#f44336"
    status_text = "PASS" if result["pass"] else "FAIL"
    svg_parts.append(
        f'<rect x="300" y="50" width="100" height="35" fill="{status_color}" rx="5"/>'
    )
    svg_parts.append(
        f'<text x="350" y="73" text-anchor="middle" font-size="16" fill="white">{status_text}</text>'
    )

    # Quality score
    svg_parts.append(
        f'<text x="350" y="115" text-anchor="middle" font-size="18">Quality Score: {result["quality_score"]}/100</text>'
    )

    # Document status grid
    y_pos = 150
    svg_parts.append('<text x="50" y="' + str(y_pos) + '" font-size="16" font-weight="bold">Document Status:</text>')
    y_pos += 25

    for doc, status in result.get("documents", {}).items():
        color = "#4caf50" if status == "OK" else "#f44336" if status == "MISSING" else "#ff9800"
        svg_parts.append(
            f'<circle cx="70" cy="{y_pos}" r="6" fill="{color}"/>'
        )
        svg_parts.append(
            f'<text x="90" y="{y_pos + 5}" font-size="14">{doc}: {status}</text>'
        )
        y_pos += 25

    # Error summary
    y_pos = 150
    svg_parts.append(f'<text x="400" y="{y_pos}" font-size="16" font-weight="bold">Issues:</text>')
    y_pos += 25
    svg_parts.append(f'<text x="400" y="{y_pos}" font-size="14">Errors: {result["errors"]}</text>')
    y_pos += 20
    svg_parts.append(f'<text x="400" y="{y_pos}" font-size="14">Warnings: {result["warnings"]}</text>')
    y_pos += 20
    svg_parts.append(f'<text x="400" y="{y_pos}" font-size="14">Evidence Files: {result["evidence_files"]}</text>')

    # Field completeness bar
    y_pos = 380
    complete = sum(1 for v in result.get("field_completeness", {}).values() if v)
    total = len(result.get("field_completeness", {}))
    if total > 0:
        bar_width = 300
        filled_width = int((complete / total) * bar_width)
        svg_parts.append(f'<text x="50" y="{y_pos}" font-size="14">Field Completeness: {complete}/{total}</text>')
        y_pos += 20
        svg_parts.append(
            f'<rect x="50" y="{y_pos}" width="{bar_width}" height="20" fill="#e0e0e0" stroke="#333"/>'
        )
        svg_parts.append(
            f'<rect x="50" y="{y_pos}" width="{filled_width}" height="20" fill="#4caf50"/>'
        )

    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)

def main():
    """CLI entry point."""
    ap = arg_parser()
    args = ap.parse_args()
    work = Path(args.work) if hasattr(args, 'work') else Path("KIS/Work/current")

    metrics = MetricsCollector()

    with metrics.timer("doc_lint_guard"):
        result = lint_documents(work)
        out = work / "lint" / "doc_lint_result.json"
        write_json(out, result)

        # Generate JSON evidence
        evidence_data = {
            "errors": result["errors"],
            "warnings": result["warnings"],
            "documents_ok": sum(1 for v in result['documents'].values() if v == 'OK'),
            "documents_total": len(result['documents']),
            "quality_score": result["quality_score"],
            "status": "PASS" if result["pass"] else "FAIL"
        }
        make_evidence(out.with_suffix(""), evidence_data, "json")

        # Generate SVG report
        svg_content = _generate_lint_report_svg(result)
        svg_path = out.with_suffix(".svg")
        write_text(svg_path, svg_content)
        log(f"Lint report visualization saved to {svg_path}", "INFO")

        # Log summary
        if result["pass"]:
            log(f"OK doc-lint-guard (quality={result['quality_score']})")
        else:
            log(f"FAIL doc-lint-guard: {result['errors']} errors", "ERROR")

    metrics.save()
    return 0 if result["pass"] else 1

if __name__ == "__main__":
    exit(main())