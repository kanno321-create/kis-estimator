"""
MCP Client - Model Context Protocol tool invocation
Handles retry logic, idempotency, and evidence logging
"""
import asyncio
import logging
import time
import uuid
from typing import Any, Literal

logger = logging.getLogger(__name__)

# MCP tool names type
MCPTool = Literal[
    "enclosure.solve",
    "enclosure.validate",
    "layout.place_breakers",
    "layout.check_clearance",
    "layout.balance_phases",
    "estimate.format",
    "estimate.export",
    "doc.cover_generate",
    "doc.apply_branding",
    "doc.lint",
    "doc.policy_check",
    "rag.ingest",
    "rag.normalize",
    "rag.index",
    "rag.verify",
    "contract.lint",
    "testgen.make",
    "regression.run",
    "sec.secrets_guard",
    "ops.rollbacks",
]


class MCPClientError(Exception):
    """MCP client errors"""
    pass


class MCPClient:
    """
    MCP tool invocation client with:
    - Exponential backoff retry (3 attempts)
    - Idempotency key tracking
    - Request/response evidence logging
    - Timeout management
    """

    def __init__(self, base_url: str = "http://localhost:3000", max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
        self.evidence_log = []  # Raw request/response logs

    async def call(
        self,
        tool: MCPTool,
        payload: dict[str, Any],
        *,
        idem_key: str | None = None,
        timeout_s: int = 30,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Call MCP tool with retry logic and evidence logging

        Args:
            tool: MCP tool name (e.g., "enclosure.solve")
            payload: Tool input parameters
            idem_key: Idempotency key (auto-generated if None)
            timeout_s: Request timeout in seconds
            trace_id: Distributed tracing ID

        Returns:
            Tool response dict

        Raises:
            MCPClientError: On failure after retries
        """
        idem_key = idem_key or str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())

        request = {
            "tool": tool,
            "payload": payload,
            "idem_key": idem_key,
            "trace_id": trace_id,
            "timestamp": time.time(),
        }

        # Log request to evidence
        self.evidence_log.append({"type": "request", "data": request})

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                # Stub: Replace with actual HTTP/MCP call
                response = await self._invoke_tool(tool, payload, timeout_s)

                # Log response to evidence
                self.evidence_log.append(
                    {
                        "type": "response",
                        "data": response,
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    }
                )

                return response

            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"MCP call failed (attempt {attempt + 1}/{self.max_retries}): {tool} - {error_msg}"
                )

                # Log error to evidence
                self.evidence_log.append(
                    {
                        "type": "error",
                        "tool": tool,
                        "error": error_msg,
                        "attempt": attempt + 1,
                        "trace_id": trace_id,
                    }
                )

                # Retry with exponential backoff
                if attempt < self.max_retries - 1:
                    backoff_s = 2**attempt  # 1s, 2s, 4s
                    logger.info(f"Retrying after {backoff_s}s...")
                    await asyncio.sleep(backoff_s)
                else:
                    # Final failure
                    raise MCPClientError(
                        f"MCP call failed after {self.max_retries} attempts: {tool}"
                    ) from e

    async def _invoke_tool(
        self, tool: MCPTool, payload: dict[str, Any], timeout_s: int
    ) -> dict[str, Any]:
        """
        Invoke MCP tool (stub implementation)

        In production, this would:
        1. Make HTTP POST to MCP server
        2. Handle streaming responses
        3. Parse MCP protocol messages
        """
        # Stub: Return mock responses based on tool
        if tool == "enclosure.solve":
            return {
                "fit_score": 0.92,
                "enclosure_sku": "ENC-IP44-800x600x250",
                "details": {
                    "width_mm": 800,
                    "height_mm": 600,
                    "depth_mm": 250,
                    "utilization": 0.75,
                },
            }

        elif tool == "layout.place_breakers":
            return {
                "layout": [
                    {"breaker_id": "b1", "position_x": 100, "position_y": 50, "phase": "R"},
                    {"breaker_id": "b2", "position_x": 200, "position_y": 50, "phase": "S"},
                ],
                "clearance_ok": True,
            }

        elif tool == "layout.balance_phases":
            return {
                "phase_r": 33.2,
                "phase_s": 33.5,
                "phase_t": 33.3,
                "phase_dev": 0.015,  # 1.5%
                "balanced": True,
            }

        elif tool == "estimate.format":
            return {
                "formatted": True,
                "formula_count": 25,
                "formula_loss": 0,
                "named_ranges_ok": True,
            }

        elif tool == "doc.lint":
            return {"errors": 0, "warnings": 1, "recommendations": ["Use consistent font sizing"]}

        elif tool == "doc.cover_generate":
            return {
                "cover_generated": True,
                "policy_violations": 0,
                "logo_ok": True,
                "branding_ok": True,
            }

        else:
            # Default stub response
            return {"success": True, "tool": tool}

    def get_evidence_log(self) -> list[dict]:
        """Get all logged requests/responses for evidence pack"""
        return self.evidence_log

    def clear_evidence_log(self):
        """Clear evidence log (e.g., between quotes)"""
        self.evidence_log = []


# Global client instance
mcp_client = MCPClient()

# Alias for compatibility
MCPGatewayClient = MCPClient
