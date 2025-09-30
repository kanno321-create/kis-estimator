<<<<<<< HEAD
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
=======
"""
Layout Service
Breaker placement and phase balancing logic
"""

import logging
from typing import Any, Dict, List

from api.integrations.mcp_client import MCPGatewayClient

logger = logging.getLogger(__name__)

class LayoutService:
    """Service for breaker layout and placement"""

    def __init__(self):
        self.mcp_client = MCPGatewayClient()

    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing LayoutService...")
        await self.mcp_client.connect()

    async def cleanup(self):
        """Cleanup service"""
        logger.info("Cleaning up LayoutService...")
        await self.mcp_client.disconnect()

    async def place_breakers(
        self,
        breakers: List[Dict[str, Any]],
        enclosure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Place breakers with optimization"""
        return await self.mcp_client.call_tool(
            "layout.place_breakers",
            {"breakers": breakers, "enclosure": enclosure}
        )

    async def check_clearance(self, placement: Dict[str, Any]) -> Dict[str, Any]:
        """Check clearance violations"""
        return await self.mcp_client.call_tool(
            "layout.check_clearance",
            {"placement": placement}
        )

    async def balance_phases(self, placement: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate phase balance"""
        return await self.mcp_client.call_tool(
            "layout.balance_phases",
            {"placement": placement}
        )

layout_service = LayoutService()
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
