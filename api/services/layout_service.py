"""Layout Service - Breaker placement and phase balancing"""
import logging
from api.integrations.mcp_client import mcp_client

logger = logging.getLogger(__name__)

async def place_breakers(breakers: list[dict], panel_size: dict) -> dict:
    """Place breakers with clearance validation"""
    result = await mcp_client.call(
        "layout.place_breakers",
        {"breakers": breakers, "panel_size": panel_size},
    )
    return result

async def check_clearance(layout: list[dict]) -> bool:
    """Check clearance violations"""
    # Stub: would call MCP tool
    return True

async def balance_phases(layout: list[dict]) -> dict:
    """Calculate phase balance"""
    result = await mcp_client.call("layout.balance_phases", {"layout": layout})
    return result
