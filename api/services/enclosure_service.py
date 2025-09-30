
"""
Enclosure Service
Enclosure solving and validation logic
"""

import logging
from typing import Any, Dict, List

from api.integrations.mcp_client import MCPGatewayClient

logger = logging.getLogger(__name__)

class EnclosureService:
    """Service for enclosure calculations"""

    def __init__(self):
        self.mcp_client = MCPGatewayClient()

    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing EnclosureService...")
        await self.mcp_client.connect()

    async def cleanup(self):
        """Cleanup service"""
        logger.info("Cleaning up EnclosureService...")
        await self.mcp_client.disconnect()

    async def solve_enclosure(self, panels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Solve optimal enclosure dimensions"""
        result = await self.mcp_client.call_tool(
            "enclosure.solve",
            {"panels": panels}
        )
        
        # Validate fit score
        if result.get("fit_score", 0) < 0.90:
            raise ValueError(f"Enclosure fit_score {result.get('fit_score')} < 0.90")
        
        return result

    async def validate_enclosure(
        self,
        enclosure: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate enclosure against requirements"""
        return await self.mcp_client.call_tool(
            "enclosure.validate",
            {"enclosure": enclosure, "requirements": requirements}
        )

enclosure_service = EnclosureService()

# Compatibility functions
async def initialize():
    pass

async def cleanup():
    pass
