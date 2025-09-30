<<<<<<< HEAD
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
=======
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
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
