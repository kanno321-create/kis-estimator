"""
<<<<<<< HEAD
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
=======
MCP Gateway Client
Typed client for MCP tool orchestration with retry and idempotency
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MCPToolCall(BaseModel):
    """MCP tool call request model"""
    tool_name: str
    parameters: Dict[str, Any]
    idempotency_key: Optional[str] = None
    timeout: int = 30

class MCPToolResponse(BaseModel):
    """MCP tool call response model"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    evidence_sha: str
    trace_id: str

class MCPGatewayClient:
    """Client for MCP Gateway integration"""

    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.retry_attempts = 3
        self.retry_delay = 1.0
        self.call_cache = {}  # Idempotency cache

    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
            logger.info("MCP Gateway client connected")

    async def disconnect(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("MCP Gateway client disconnected")

    async def call_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Call an MCP tool through the gateway

        Tools available:
        - enclosure.solve, enclosure.validate
        - layout.place_breakers, layout.check_clearance, layout.balance_phases
        - estimate.format, estimate.export
        - doc.cover_generate, doc.apply_branding, doc.lint, doc.policy_check
        - rag.ingest, rag.normalize, rag.index, rag.verify
        - contract.lint, db.modeler, testgen.make
        - regression.run, sec.secrets_guard, ops.rollbacks
        """
        # Generate idempotency key if not provided
        if not idempotency_key:
            idempotency_key = str(uuid.uuid4())

        # Check cache
        cache_key = f"{tool_name}:{idempotency_key}"
        if cache_key in self.call_cache:
            logger.info(f"Returning cached result for {cache_key}")
            return self.call_cache[cache_key]

        # Prepare request
        request_data = {
            "tool": tool_name,
            "parameters": parameters,
            "idempotency_key": idempotency_key,
            "trace_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Generate evidence
        evidence_data = {
            "tool": tool_name,
            "input": parameters,
            "timestamp": request_data["timestamp"],
            "trace_id": request_data["trace_id"]
        }

        # Retry logic
        for attempt in range(self.retry_attempts):
            try:
                result = await self._execute_tool_call(request_data, timeout)

                # Store evidence
                evidence_data["output"] = result
                evidence_sha = self._generate_evidence_hash(evidence_data)

                # Cache successful result
                self.call_cache[cache_key] = result

                # Log success
                logger.info(
                    f"Tool {tool_name} executed successfully. "
                    f"Evidence SHA: {evidence_sha}"
                )

                return result

            except Exception as e:
                logger.warning(
                    f"Tool {tool_name} failed (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )

                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    # Final failure - hard fail as per requirements
                    error_msg = f"Tool {tool_name} failed after {self.retry_attempts} attempts"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

    async def _execute_tool_call(
        self,
        request_data: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """Execute actual tool call to gateway"""
        # In production, this would call the actual MCP Gateway
        # For now, return mock responses based on tool name

        tool_name = request_data["tool"]
        parameters = request_data["parameters"]

        # Mock responses for each tool
        mock_responses = {
            "enclosure.solve": {
                "fit_score": 0.95,
                "sku": "ENC-2000x800x400",
                "dimensions": {"width": 2000, "height": 800, "depth": 400},
                "ip_rating": "IP54"
            },
            "enclosure.validate": {
                "valid": True,
                "fit_score": 0.95,
                "warnings": []
            },
            "layout.place_breakers": {
                "placement": [
                    {"breaker_id": "b1", "position": {"x": 100, "y": 100}, "phase": "R"},
                    {"breaker_id": "b2", "position": {"x": 200, "y": 100}, "phase": "S"},
                    {"breaker_id": "b3", "position": {"x": 300, "y": 100}, "phase": "T"}
                ],
                "utilization": 0.75
            },
            "layout.check_clearance": {
                "violations": 0,
                "clearances_ok": True
            },
            "layout.balance_phases": {
                "phase_r_load": 100,
                "phase_s_load": 98,
                "phase_t_load": 102,
                "imbalance": 0.02
            },
            "estimate.format": {
                "document_id": str(uuid.uuid4()),
                "formula_preserved": 1.0,
                "format": "excel"
            },
            "doc.cover_generate": {
                "cover_id": str(uuid.uuid4()),
                "title": "견적서",
                "customer": parameters.get("customer", {})
            },
            "doc.apply_branding": {
                "branded": True,
                "logo_applied": True,
                "colors_applied": True
            },
            "doc.lint": {
                "errors": 0,
                "warnings": 0,
                "valid": True
            },
            "doc.policy_check": {
                "violations": 0,
                "compliant": True
            },
            "rag.ingest": {
                "documents_processed": 10,
                "success": True
            },
            "rag.verify": {
                "citation_coverage": 1.0,
                "sources_valid": True
            },
            "regression.run": {
                "total": 20,
                "passed": 20,
                "failed": 0,
                "success_rate": 1.0
            }
        }

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Return mock response
        tool_base = tool_name.split(".")[0]
        if tool_name in mock_responses:
            return mock_responses[tool_name]
        elif tool_base in ["enclosure", "layout", "estimate", "doc", "rag"]:
            return {"success": True, "result": {}}
        else:
            return {"success": True, "result": parameters}

    def _generate_evidence_hash(self, evidence_data: Dict[str, Any]) -> str:
        """Generate SHA256 hash for evidence"""
        json_str = json.dumps(evidence_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def validate_evidence(self, evidence_sha: str) -> bool:
        """Validate evidence integrity"""
        # In production, this would check against stored evidence
        return len(evidence_sha) == 64 and all(c in "0123456789abcdef" for c in evidence_sha)

    async def get_tool_metadata(self, tool_name: str) -> Dict[str, Any]:
        """Get metadata for a specific tool"""
        metadata = {
            "enclosure.solve": {
                "description": "Solve enclosure dimensions",
                "required_params": ["panels"],
                "quality_gate": "fit_score >= 0.90"
            },
            "layout.place_breakers": {
                "description": "Place breakers with optimization",
                "required_params": ["breakers", "enclosure"],
                "quality_gate": "phase_imbalance <= 0.03"
            },
            "doc.lint": {
                "description": "Validate document quality",
                "required_params": ["document"],
                "quality_gate": "errors = 0"
            },
            "regression.run": {
                "description": "Run regression test suite",
                "required_params": ["test_suite"],
                "quality_gate": "20/20 PASS"
            }
        }

        return metadata.get(tool_name, {
            "description": f"Tool {tool_name}",
            "required_params": [],
            "quality_gate": None
        })

# Singleton instance
mcp_client = MCPGatewayClient()
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
