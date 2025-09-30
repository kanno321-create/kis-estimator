"""Estimate Router - Quote estimation with FIX-4 pipeline and SSE"""
import logging
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.services import estimate_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/estimate", tags=["estimate"])


class EstimateRequest(BaseModel):
    customer: dict
    panels: list
    currency: str = "KRW"
    locale: str = "ko-KR"


@router.post("")
async def create_estimate(req: EstimateRequest):
    """
    FIX-4 Pipeline: Enclosure → Breaker → Critic → Format → Cover → Lint
    
    Quality Gates:
    - Enclosure: fit_score >= 0.90
    - Layout: phase_dev <= 0.03, clearance_ok = true
    - Format: formula_loss = 0
    - Lint: errors = 0
    """
    result = await estimate_service.create_quote(req.model_dump())
    
    return result, 201


@router.get("/{id}")
async def get_estimate(id: str):
    """Retrieve estimate by ID"""
    # Stub: Would query database
    return {"id": id, "status": "draft"}


@router.get("/stream")
async def stream_estimate(quoteId: str):
    """
    SSE stream for estimate progress
    
    Events:
    - HEARTBEAT: Every 3s (meta.seq monotonic)
    - PROGRESS: Stage progress (0-100%)
    - GATE_RESULT: Gate pass/fail
    - DONE: Pipeline complete
    
    All events include meta.seq (never None)
    """
    # Stub payload for demonstration
    payload = {
        "customer": {"name": "Test Customer"},
        "panels": [{"name": "Main", "breakers": []}],
        "currency": "KRW"
    }
    
    return StreamingResponse(
        estimate_service.generate_sse_events(quoteId, payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
