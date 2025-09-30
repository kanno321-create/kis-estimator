
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

# Compatibility functions
async def initialize():
    pass

async def cleanup():
    pass
