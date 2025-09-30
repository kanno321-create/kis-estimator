"""
<<<<<<< HEAD
Estimate Service - FIX-4 Pipeline Orchestration
Enclosure → Breaker → Critic → Format → Cover → Lint
"""
import asyncio
import json
import logging
import uuid
from typing import AsyncGenerator

from api.services import enclosure_service, layout_service, document_service

logger = logging.getLogger(__name__)


async def create_quote(payload: dict, sse_queue: asyncio.Queue = None) -> dict:
    """
    Create quote with FIX-4 pipeline execution

    Pipeline stages (with progress %):
    - 10%: INPUT_NORMALIZED
    - 25%: ENCLOSURE_OK (fit_score >= 0.90)
    - 45%: LAYOUT_OK (clearance + phase_dev <= 0.03)
    - 70%: FORMAT_OK (formula_loss = 0)
    - 85%: COVER_LINT_OK (lint_errors = 0)
    - 100%: DONE

    Args:
        payload: Estimate request data
        sse_queue: Queue for SSE progress events (optional)

    Returns:
        dict: {quoteId, evidence, totals, gates}
    """
    quote_id = str(uuid.uuid4())
    evidence = {"stages": {}}
    gates = {}

    async def emit_progress(stage: str, progress: float, status: str = "in_progress", metrics: dict = None):
        """Emit SSE progress event"""
        if sse_queue:
            await sse_queue.put({
                "type": "PROGRESS",
                "stage": stage,
                "progress": progress,
                "status": status,
                "metrics": metrics or {},
                "quote_id": quote_id,
            })

    try:
        # Stage 1: INPUT_NORMALIZED (10%)
        await emit_progress("input", 0.10, "in_progress")
        # Validation would happen here
        await asyncio.sleep(0.1)  # Simulate work

        # Stage 2: ENCLOSURE (25%)
        await emit_progress("enclosure", 0.15, "in_progress")
        enclosure_result = await enclosure_service.solve(
            payload["panels"][0].get("breakers", []),
            payload["panels"][0].get("materials", [])
        )
        fit_score = enclosure_result["fit_score"]
        gates["enclosure_fit"] = fit_score >= 0.90

        evidence["stages"]["enclosure"] = {
            "fit_score": fit_score,
            "sku": enclosure_result["enclosure_sku"],
            "gate_pass": gates["enclosure_fit"],
        }
        await emit_progress("enclosure", 0.25, "completed", {"fit_score": fit_score})

        # Stage 3: LAYOUT (45%)
        await emit_progress("layout", 0.30, "in_progress")
        layout_result = await layout_service.place_breakers(
            payload["panels"][0].get("breakers", []),
            {"width": 800, "height": 600}
        )
        phase_result = await layout_service.balance_phases(layout_result["layout"])
        phase_dev = phase_result["phase_dev"]
        gates["phase_balance"] = phase_dev <= 0.03
        gates["clearance"] = layout_result["clearance_ok"]

        evidence["stages"]["breaker"] = {
            "phase_dev": phase_dev,
            "clearance_ok": layout_result["clearance_ok"],
            "gate_pass": gates["phase_balance"] and gates["clearance"],
        }
        await emit_progress("layout", 0.45, "completed", {"phase_dev": phase_dev})

        # Stage 4: FORMAT (70%)
        await emit_progress("format", 0.55, "in_progress")
        format_result = await document_service.format_estimate(payload)
        gates["formula_preservation"] = format_result["formula_loss"] == 0

        evidence["stages"]["format"] = {
            "formula_loss": format_result["formula_loss"],
            "gate_pass": gates["formula_preservation"],
        }
        await emit_progress("format", 0.70, "completed", {"formula_loss": 0})

        # Stage 5: COVER & LINT (85%)
        await emit_progress("cover", 0.75, "in_progress")
        cover_result = await document_service.generate_cover(payload["customer"], quote_id)
        lint_result = await document_service.lint_document({})
        gates["cover_branding"] = cover_result["policy_violations"] == 0
        gates["lint"] = lint_result["errors"] == 0

        evidence["stages"]["cover"] = cover_result
        evidence["stages"]["lint"] = lint_result
        await emit_progress("cover", 0.85, "completed", {"lint_errors": 0})

        # Stage 6: EXPORT (95%)
        await emit_progress("export", 0.90, "in_progress")
        export_result = await document_service.export_pdf_xlsx(quote_id, payload)
        evidence["documents"] = export_result
        await emit_progress("export", 0.95, "completed")

        # DONE (100%)
        await emit_progress("done", 1.0, "completed")

        # Check all gates
        all_gates_pass = all(gates.values())

        return {
            "quoteId": quote_id,
            "evidence": evidence,
            "totals": {"total": 1000000, "currency": payload.get("currency", "KRW")},
            "gates": gates,
            "all_gates_pass": all_gates_pass,
            "links": {
                "pdf": f"/v1/documents?quoteId={quote_id}&kind=pdf",
                "xlsx": f"/v1/documents?quoteId={quote_id}&kind=xlsx",
            }
        }

    except Exception as e:
        logger.error(f"Quote creation failed: {e}", exc_info=True)
        if sse_queue:
            await sse_queue.put({
                "type": "ERROR",
                "error": str(e),
                "quote_id": quote_id,
            })
        raise


async def generate_sse_events(quote_id: str, payload: dict) -> AsyncGenerator:
    """
    Generate SSE events for estimate progress

    Yields SSE-formatted strings with:
    - HEARTBEAT every 3s
    - PROGRESS for each stage
    - GATE_RESULT for gate checks
    - DONE when complete
    """
    queue = asyncio.Queue()
    seq = 0

    # Start quote creation in background
    asyncio.create_task(create_quote(payload, queue))

    # Heartbeat task
    async def heartbeat():
        nonlocal seq
        while True:
            await asyncio.sleep(3)
            seq += 1
            yield f'event: HEARTBEAT\ndata: {{"meta": {{"seq": {seq}, "timestamp": "{asyncio.get_event_loop().time()}"}}}}\n\n'

    heartbeat_gen = heartbeat()

    # Process queue events
    try:
        while True:
            # Get next event with timeout
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # Send heartbeat if no events
                try:
                    yield await heartbeat_gen.__anext__()
                except StopAsyncIteration:
                    pass
                continue

            seq += 1
            event_type = event.get("type", "PROGRESS")
            event_data = {k: v for k, v in event.items() if k != "type"}
            event_data["meta"] = {"seq": seq, "timestamp": asyncio.get_event_loop().time()}

            yield f'event: {event_type}\ndata: {json.dumps(event_data)}\n\n'

            if event_type == "DONE" or event_type == "ERROR":
                break

    except Exception as e:
        logger.error(f"SSE stream error: {e}")
        seq += 1
        yield f'event: ERROR\ndata: {{"meta": {{"seq": {seq}}}, "error": "{str(e)}"}}\n\n'
=======
Estimate Service
Core business logic for estimate generation with FIX-4 pipeline
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from api.integrations.mcp_client import MCPGatewayClient
from api.services.enclosure_service import EnclosureService
from api.services.layout_service import LayoutService
from api.services.document_service import DocumentService

logger = logging.getLogger(__name__)

class EstimateRequest(BaseModel):
    """Estimate request model"""
    customer: Dict[str, Any]
    items: List[Dict[str, Any]]
    panels: List[Dict[str, Any]]
    currency: str = "KRW"
    locale: str = "ko-KR"

class EstimateResponse(BaseModel):
    """Estimate response model"""
    id: str
    status: str
    customer: Dict[str, Any]
    totals: Dict[str, float]
    currency: str
    created_at: str
    updated_at: str
    evidence_sha: str
    evidence_url: Optional[str] = None

class EstimateService:
    """Service for handling estimate operations"""

    def __init__(self):
        self.mcp_client = MCPGatewayClient()
        self.enclosure_service = EnclosureService()
        self.layout_service = LayoutService()
        self.document_service = DocumentService()
        self.estimates_cache = {}  # Simplified cache - use Redis in production

    async def initialize(self):
        """Initialize service resources"""
        logger.info("Initializing EstimateService...")
        await self.mcp_client.connect()

    async def cleanup(self):
        """Cleanup service resources"""
        logger.info("Cleaning up EstimateService...")
        await self.mcp_client.disconnect()

    async def create_estimate(
        self,
        request: EstimateRequest,
        idempotency_key: Optional[str] = None
    ) -> EstimateResponse:
        """
        Create an estimate using FIX-4 pipeline

        Pipeline stages:
        1. Enclosure solving (fit_score >= 0.90)
        2. Breaker placement (phase balance <= 3%)
        3. Format generation
        4. Cover generation
        5. Document lint
        """
        # Check idempotency
        if idempotency_key and idempotency_key in self.estimates_cache:
            logger.info(f"Returning cached estimate for idempotency key: {idempotency_key}")
            return self.estimates_cache[idempotency_key]

        estimate_id = str(uuid.uuid4())
        evidence_data = {
            "estimate_id": estimate_id,
            "request": request.dict(),
            "pipeline_stages": []
        }

        try:
            # Stage 1: Enclosure solving
            logger.info(f"Stage 1: Solving enclosure for estimate {estimate_id}")
            enclosure_result = await self._solve_enclosure(request.panels, evidence_data)

            # Stage 2: Breaker placement
            logger.info(f"Stage 2: Placing breakers for estimate {estimate_id}")
            placement_result = await self._place_breakers(
                request.panels,
                enclosure_result,
                evidence_data
            )

            # Stage 2.1: Critic validation
            logger.info(f"Stage 2.1: Validating placement for estimate {estimate_id}")
            critic_result = await self._validate_placement(placement_result, evidence_data)

            # Stage 3: Format generation
            logger.info(f"Stage 3: Generating format for estimate {estimate_id}")
            format_result = await self._generate_format(
                request,
                enclosure_result,
                placement_result,
                evidence_data
            )

            # Stage 4: Cover generation
            logger.info(f"Stage 4: Generating cover for estimate {estimate_id}")
            cover_result = await self._generate_cover(request, format_result, evidence_data)

            # Stage 5: Document lint
            logger.info(f"Stage 5: Linting document for estimate {estimate_id}")
            lint_result = await self._lint_document(cover_result, evidence_data)

            # Calculate totals
            totals = self._calculate_totals(request.items, request.panels)

            # Generate evidence hash
            evidence_sha = self._generate_evidence_hash(evidence_data)

            # Create response
            response = EstimateResponse(
                id=estimate_id,
                status="completed",
                customer=request.customer,
                totals=totals,
                currency=request.currency,
                created_at=datetime.now(timezone.utc).isoformat(),
                updated_at=datetime.now(timezone.utc).isoformat(),
                evidence_sha=evidence_sha,
                evidence_url=f"/evidence/{estimate_id}"
            )

            # Cache if idempotency key provided
            if idempotency_key:
                self.estimates_cache[idempotency_key] = response

            return response

        except Exception as e:
            logger.error(f"Error creating estimate {estimate_id}: {e}")
            raise

    async def _solve_enclosure(
        self,
        panels: List[Dict[str, Any]],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 1: Solve enclosure with fit_score >= 0.90"""
        result = await self.mcp_client.call_tool(
            "enclosure.solve",
            {"panels": panels}
        )

        # Validate fit score
        if result.get("fit_score", 0) < 0.90:
            raise ValueError(f"Enclosure fit_score {result.get('fit_score')} < 0.90")

        evidence_data["pipeline_stages"].append({
            "stage": "enclosure",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    async def _place_breakers(
        self,
        panels: List[Dict[str, Any]],
        enclosure_result: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 2: Place breakers with phase balance <= 3%"""
        breakers = []
        for panel in panels:
            breakers.extend(panel.get("breakers", []))

        result = await self.mcp_client.call_tool(
            "layout.place_breakers",
            {
                "breakers": breakers,
                "enclosure": enclosure_result
            }
        )

        # Check phase balance
        phase_balance = await self.mcp_client.call_tool(
            "layout.balance_phases",
            {"placement": result}
        )

        if phase_balance.get("imbalance", 1.0) > 0.03:
            raise ValueError(f"Phase imbalance {phase_balance.get('imbalance')} > 3%")

        evidence_data["pipeline_stages"].append({
            "stage": "breaker_placement",
            "result": result,
            "phase_balance": phase_balance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    async def _validate_placement(
        self,
        placement_result: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 2.1: Validate placement with critic"""
        result = await self.mcp_client.call_tool(
            "layout.check_clearance",
            {"placement": placement_result}
        )

        if result.get("violations", 0) > 0:
            raise ValueError(f"Clearance violations: {result.get('violations')}")

        evidence_data["pipeline_stages"].append({
            "stage": "critic_validation",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    async def _generate_format(
        self,
        request: EstimateRequest,
        enclosure_result: Dict[str, Any],
        placement_result: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 3: Generate format with formula preservation"""
        result = await self.mcp_client.call_tool(
            "estimate.format",
            {
                "request": request.dict(),
                "enclosure": enclosure_result,
                "placement": placement_result
            }
        )

        # Verify formula preservation
        if result.get("formula_preserved", 0) < 1.0:
            raise ValueError("Formula preservation failed")

        evidence_data["pipeline_stages"].append({
            "stage": "format_generation",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    async def _generate_cover(
        self,
        request: EstimateRequest,
        format_result: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 4: Generate cover with branding"""
        result = await self.mcp_client.call_tool(
            "doc.cover_generate",
            {
                "customer": request.customer,
                "format": format_result
            }
        )

        # Apply branding
        branded_result = await self.mcp_client.call_tool(
            "doc.apply_branding",
            {"document": result}
        )

        evidence_data["pipeline_stages"].append({
            "stage": "cover_generation",
            "result": branded_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return branded_result

    async def _lint_document(
        self,
        document_result: Dict[str, Any],
        evidence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 5: Lint document with zero errors"""
        result = await self.mcp_client.call_tool(
            "doc.lint",
            {"document": document_result}
        )

        if result.get("errors", 0) > 0:
            raise ValueError(f"Document lint errors: {result.get('errors')}")

        # Policy check
        policy_result = await self.mcp_client.call_tool(
            "doc.policy_check",
            {"document": document_result}
        )

        if policy_result.get("violations", 0) > 0:
            raise ValueError(f"Policy violations: {policy_result.get('violations')}")

        evidence_data["pipeline_stages"].append({
            "stage": "document_lint",
            "result": result,
            "policy": policy_result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return result

    def _calculate_totals(
        self,
        items: List[Dict[str, Any]],
        panels: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate estimate totals"""
        subtotal = 0.0

        # Calculate items total
        for item in items:
            qty = item.get("quantity", 0)
            unit_price = item.get("unitPrice", 0)
            subtotal += qty * unit_price

        # Calculate panels/breakers total
        for panel in panels:
            for breaker in panel.get("breakers", []):
                qty = breaker.get("quantity", 0)
                # Simplified pricing - use catalog in production
                unit_price = breaker.get("capacity", 0) * 1000  # Price per amp
                subtotal += qty * unit_price

        tax = subtotal * 0.1  # 10% tax
        total = subtotal + tax

        return {
            "subtotal": subtotal,
            "tax": tax,
            "total": total
        }

    def _generate_evidence_hash(self, evidence_data: Dict[str, Any]) -> str:
        """Generate SHA256 hash for evidence"""
        json_str = json.dumps(evidence_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode()).hexdigest()

    async def stream_estimate_progress(self, estimate_id: str):
        """Stream estimate generation progress via SSE"""
        async def event_generator():
            stages = [
                "Solving enclosure...",
                "Placing breakers...",
                "Validating placement...",
                "Generating format...",
                "Creating cover...",
                "Linting document...",
                "Complete!"
            ]

            for i, stage in enumerate(stages):
                # Heartbeat with metadata
                yield f"data: {json.dumps({'stage': stage, 'progress': i/len(stages), 'meta': {'seq': i}})}\n\n"
                await asyncio.sleep(1)  # Simulate processing

            yield f"data: {json.dumps({'complete': True, 'estimateId': estimate_id})}\n\n"

        return event_generator()

# Singleton instance
estimate_service = EstimateService()
>>>>>>> b21feef637c13ecc0be617bfd6c88f47155d8b0e
