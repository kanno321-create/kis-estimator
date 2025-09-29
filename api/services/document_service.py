"""
Document Service
Document generation and formatting logic
"""

import logging
from typing import Any, Dict, Optional

from api.integrations.mcp_client import MCPGatewayClient

logger = logging.getLogger(__name__)

class DocumentService:
    """Service for document generation"""

    def __init__(self):
        self.mcp_client = MCPGatewayClient()

    async def initialize(self):
        """Initialize service"""
        logger.info("Initializing DocumentService...")
        await self.mcp_client.connect()

    async def cleanup(self):
        """Cleanup service"""
        logger.info("Cleaning up DocumentService...")
        await self.mcp_client.disconnect()

    async def generate_pdf(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate PDF document"""
        return await self.mcp_client.call_tool(
            "estimate.export",
            {"format": "pdf", "data": quote_data}
        )

    async def generate_excel(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Excel document"""
        return await self.mcp_client.call_tool(
            "estimate.export",
            {"format": "xlsx", "data": quote_data}
        )

    async def generate_cover(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Generate document cover"""
        return await self.mcp_client.call_tool(
            "doc.cover_generate",
            {"customer": customer}
        )

    async def apply_branding(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Apply company branding"""
        return await self.mcp_client.call_tool(
            "doc.apply_branding",
            {"document": document}
        )

    async def lint_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document quality"""
        result = await self.mcp_client.call_tool(
            "doc.lint",
            {"document": document}
        )
        
        if result.get("errors", 0) > 0:
            raise ValueError(f"Document lint errors: {result.get('errors')}")
        
        return result

document_service = DocumentService()