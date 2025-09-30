"""Enclosure Service - Enclosure sizing and fit scoring"""
import logging
from api.integrations.mcp_client import mcp_client

logger = logging.getLogger(__name__)

async def solve(breakers: list[dict], materials: list[dict] = None) -> dict:
    """Solve optimal enclosure size"""
    result = await mcp_client.call(
        "enclosure.solve",
        {"breakers": breakers, "materials": materials or []},
    )
    return result

async def validate(fit_score: float) -> bool:
    """Validate fit_score >= 0.90"""
    return fit_score >= 0.90
