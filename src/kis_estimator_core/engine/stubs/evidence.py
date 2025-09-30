"""Evidence writer utilities for estimator stages."""

from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping

import polars as pl  # type: ignore

from ..util import guard, io

CASE_DEFAULT = "2025-0001"
_PNG_PIXEL = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQI12P4//8/AwAI/AL+XgKp5wAAAABJRU5ErkJggg=="
)


def _evidence_root(case_id: str = CASE_DEFAULT) -> Path:
    base = Path(__file__).resolve().parents[3] / "Work" / case_id / "output" / "evidence"
    return io.ensure_dir(base)


def _write_binary(path: Path, payload: bytes) -> Path:
    guard.ensure_whitelisted(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _sanitise(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


def write_stage(
    stage: str,
    payload: Mapping[str, object],
    *,
    case_id: str = CASE_DEFAULT,
    inputs: Mapping[str, MutableMapping[str, object]] | None = None,
    tables: Mapping[str, pl.DataFrame] | None = None,
) -> List[str]:
    """Persist evidence artefacts for a stage, including inputs and tables."""
    # [REAL-LOGIC] Ensure every stage produces structured artefacts for auditability
    root = _evidence_root(case_id)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
    artefacts: List[str] = []

    json_path = root / f"{stage}_{timestamp}.json"
    io.write_json(json_path, dict(payload))
    artefacts.append(str(json_path))

    svg_stub = root / f"{stage}_{timestamp}.svg"
    svg_content = (
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"320\" height=\"80\">"
        f"<rect width=\"320\" height=\"80\" fill=\"#f2f6ff\"/>"
        f"<text x=\"16\" y=\"30\" font-size=\"14\" fill=\"#003366\">{stage} snapshot</text>"
        f"<text x=\"16\" y=\"60\" font-size=\"12\" fill=\"#003366\">{timestamp}</text></svg>"
    ).encode("utf-8")
    _write_binary(svg_stub, svg_content)
    artefacts.append(str(svg_stub))

    png_stub = root / f"{stage}_{timestamp}.png"
    _write_binary(png_stub, _PNG_PIXEL)
    artefacts.append(str(png_stub))

    if inputs:
        for name, snapshot in inputs.items():
            snap_path = root / f"{stage}_{_sanitise(name)}_{timestamp}.json"
            io.write_json(snap_path, dict(snapshot))
            artefacts.append(str(snap_path))

    if tables:
        for name, frame in tables.items():
            table_path = root / f"{stage}_{_sanitise(name)}_{timestamp}.parquet"
            guard.ensure_whitelisted(table_path)
            frame.write_parquet(table_path)  # [REAL-LOGIC] Persist analytical tables for traceability
            artefacts.append(str(table_path))

    return artefacts
