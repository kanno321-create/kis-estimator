"""MCP I/O Pydantic Models"""
from pydantic import BaseModel

class EnclosureSolveInput(BaseModel):
    breakers: list[dict]
    materials: list[dict] = []
    ip_required: str = "IP44"

class EnclosureSolveOutput(BaseModel):
    fit_score: float
    enclosure_sku: str
    details: dict

class LayoutPlaceInput(BaseModel):
    breakers: list[dict]
    panel_size: dict

class LayoutPlaceOutput(BaseModel):
    layout: list[dict]
    clearance_ok: bool

class PhaseBalanceOutput(BaseModel):
    phase_r: float
    phase_s: float
    phase_t: float
    phase_dev: float
    balanced: bool
