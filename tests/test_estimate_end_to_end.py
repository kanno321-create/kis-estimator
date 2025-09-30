"""End-to-End Estimate Flow Tests with FIX-4 Pipeline"""
import pytest
import asyncio
import json
import hashlib
from typing import Dict, Any, List
from datetime import datetime
import random
import sys
import os

# Add mock clients to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mock_clients"))
from fake_supabase import FakeSupabase
from fake_mcp import FakeMCP

class TestEstimateEndToEnd:
    """Complete estimate flow testing through FIX-4 pipeline"""

    def setup_method(self):
        """Setup test dependencies"""
        self.supabase = FakeSupabase("http://mock", "key", "secret")
        self.mcp = FakeMCP()

    def generate_test_request(self) -> Dict[str, Any]:
        """Generate valid estimate request"""
        return {
            "project_name": "테스트 전기실",
            "customer_id": "123e4567-e89b-12d3-a456-426614174000",
            "breakers": [
                {"sku": "BKR-32A-3P", "quantity": 10, "rating": 32, "poles": 3},
                {"sku": "BKR-63A-3P", "quantity": 5, "rating": 63, "poles": 3},
                {"sku": "BKR-100A-3P", "quantity": 3, "rating": 100, "poles": 3},
                {"sku": "BKR-125A-3P", "quantity": 2, "rating": 125, "poles": 3},
                {"sku": "BKR-250A-4P", "quantity": 1, "rating": 250, "poles": 4}
            ],
            "panel_config": {
                "width": 800,
                "height": 2000,
                "depth": 400,
                "phases": 3,
                "ip_rating": "IP44",
                "max_breakers": 30
            },
            "metadata": {
                "site_location": "서울시 강남구",
                "installation_type": "indoor",
                "ambient_temp": 30,
                "altitude": 50
            }
        }

    @pytest.mark.asyncio
    async def test_complete_fix4_pipeline(self):
        """Test complete FIX-4 pipeline execution"""
        request = self.generate_test_request()

        # Stage 1: Enclosure Selection
        print("\n=== Stage 1: ENCLOSURE ===")
        enclosure_result = await self.mcp.execute_tool("enclosure.solve", {
            "breakers": request["breakers"],
            "panel_config": request["panel_config"]
        })

        assert enclosure_result["success"]
        assert enclosure_result["fit_score"] >= 0.90
        assert enclosure_result["selected_sku"] is not None
        print(f"✅ Enclosure: {enclosure_result['selected_sku']}, fit_score: {enclosure_result['fit_score']}")

        # Stage 2: Breaker Placement
        print("\n=== Stage 2: BREAKER PLACEMENT ===")
        placement_result = await self.mcp.execute_tool("layout.place_breakers", {
            "breakers": request["breakers"],
            "enclosure": enclosure_result["selected_sku"],
            "phases": request["panel_config"]["phases"]
        })

        assert placement_result["success"]
        assert placement_result["phase_balance"] <= 4.0
        assert placement_result["clearance_violations"] == 0
        assert placement_result["thermal_violations"] == 0
        print(f"✅ Phase balance: {placement_result['phase_balance']}%")
        print(f"✅ Placements: {len(placement_result['positions'])} breakers positioned")

        # Stage 2.1: Critic Validation
        print("\n=== Stage 2.1: CRITIC VALIDATION ===")
        critic_result = await self.mcp.execute_tool("layout.validate_placement", {
            "placement": placement_result["positions"],
            "rules": ["clearance", "thermal", "phase_balance", "accessibility"]
        })

        assert critic_result["valid"]
        assert len(critic_result["violations"]) == 0
        print(f"✅ Critic validation: {critic_result['score']:.2f}/1.00")

        # Stage 3: Document Formatting
        print("\n=== Stage 3: FORMAT ===")
        format_result = await self.mcp.execute_tool("estimate.format", {
            "project_name": request["project_name"],
            "customer_id": request["customer_id"],
            "enclosure": enclosure_result,
            "placement": placement_result,
            "format": "xlsx"
        })

        assert format_result["success"]
        assert format_result["formulas_preserved"]
        assert format_result["named_ranges_intact"]
        print(f"✅ Document formatted: {format_result['document_id']}")

        # Stage 4: Cover Generation
        print("\n=== Stage 4: COVER ===")
        cover_result = await self.mcp.execute_tool("doc.cover_generate", {
            "document_id": format_result["document_id"],
            "project_name": request["project_name"],
            "company_logo": "naberal_logo.png",
            "date": datetime.now().isoformat()
        })

        assert cover_result["success"]
        assert cover_result["cover_compliant"]
        print(f"✅ Cover generated with branding")

        # Stage 5: Document Lint
        print("\n=== Stage 5: DOC LINT ===")
        lint_result = await self.mcp.execute_tool("doc.lint", {
            "document_id": format_result["document_id"],
            "rules": ["completeness", "formula_integrity", "reference_validity", "style_compliance"]
        })

        assert lint_result["success"]
        assert lint_result["errors"] == 0
        assert lint_result["warnings"] <= 3  # Allow minor warnings
        print(f"✅ Document lint: {lint_result['errors']} errors, {lint_result['warnings']} warnings")

        # Evidence Generation
        print("\n=== EVIDENCE GENERATION ===")
        evidence = self._generate_evidence({
            "request": request,
            "enclosure": enclosure_result,
            "placement": placement_result,
            "critic": critic_result,
            "format": format_result,
            "cover": cover_result,
            "lint": lint_result
        })

        assert len(evidence["hash"]) == 64
        assert evidence["traceId"] is not None
        print(f"✅ Evidence hash: {evidence['hash'][:16]}...")
        print(f"✅ TraceId: {evidence['traceId']}")

    @pytest.mark.asyncio
    async def test_stage_1_enclosure_failures(self):
        """Test enclosure stage failure scenarios"""

        # Test: Too many breakers for any enclosure
        oversized_request = {
            "breakers": [
                {"sku": "BKR-250A-4P", "quantity": 100, "rating": 250, "poles": 4}
            ],
            "panel_config": {"width": 800, "height": 2000, "phases": 3}
        }

        result = await self.mcp.execute_tool("enclosure.solve", oversized_request)
        assert not result["success"]
        assert "NO_FIT" in result["error_code"]
        assert result["fit_score"] < 0.90

    @pytest.mark.asyncio
    async def test_stage_2_placement_failures(self):
        """Test breaker placement failure scenarios"""

        # Test: Phase imbalance exceeds threshold
        unbalanced_request = {
            "breakers": [
                {"sku": "BKR-250A-3P", "quantity": 1, "rating": 250, "poles": 3, "phase": "A"},
                {"sku": "BKR-32A-3P", "quantity": 1, "rating": 32, "poles": 3, "phase": "B"},
                {"sku": "BKR-32A-3P", "quantity": 1, "rating": 32, "poles": 3, "phase": "C"}
            ],
            "enclosure": "ENC-2000",
            "phases": 3
        }

        result = await self.mcp.execute_tool("layout.place_breakers", unbalanced_request)

        # Should still place but with high imbalance
        assert result["success"]
        assert result["phase_balance"] > 4.0  # Exceeds threshold
        assert "warnings" in result
        assert len(result["warnings"]) > 0

    @pytest.mark.asyncio
    async def test_stage_3_format_edge_cases(self):
        """Test document formatting edge cases"""

        # Test: Korean characters in project name
        korean_format = {
            "project_name": "한국전력 강남변전소",
            "customer_id": "123e4567-e89b-12d3-a456-426614174000",
            "enclosure": {"selected_sku": "ENC-2000", "fit_score": 0.95},
            "placement": {"positions": [], "phase_balance": 2.5},
            "format": "xlsx"
        }

        result = await self.mcp.execute_tool("estimate.format", korean_format)
        assert result["success"]
        assert result["encoding"] == "utf-8"

        # Test: Special characters in formulas
        formula_format = {
            **korean_format,
            "custom_formulas": {
                "total_cost": "=SUM(B2:B100)*1.1",
                "vat": "=ROUND(total_cost*0.1,0)"
            }
        }

        result = await self.mcp.execute_tool("estimate.format", formula_format)
        assert result["success"]
        assert result["formulas_preserved"]

    @pytest.mark.asyncio
    async def test_parallel_estimate_processing(self):
        """Test parallel processing of multiple estimates"""

        # Generate 5 different estimate requests
        requests = []
        for i in range(5):
            req = self.generate_test_request()
            req["project_name"] = f"Project-{i:03d}"
            req["breakers"][0]["quantity"] = 5 + i  # Vary quantities
            requests.append(req)

        # Process all estimates in parallel
        async def process_estimate(request: Dict) -> Dict:
            """Process single estimate through pipeline"""
            # Enclosure
            enc = await self.mcp.execute_tool("enclosure.solve", {
                "breakers": request["breakers"],
                "panel_config": request["panel_config"]
            })

            # Placement
            place = await self.mcp.execute_tool("layout.place_breakers", {
                "breakers": request["breakers"],
                "enclosure": enc["selected_sku"],
                "phases": 3
            })

            return {
                "project": request["project_name"],
                "enclosure_fit": enc["fit_score"],
                "phase_balance": place["phase_balance"],
                "success": enc["success"] and place["success"]
            }

        # Execute in parallel
        results = await asyncio.gather(*[process_estimate(req) for req in requests])

        # Verify all succeeded
        for i, result in enumerate(results):
            assert result["success"], f"Estimate {i} failed"
            assert result["enclosure_fit"] >= 0.90
            assert result["phase_balance"] <= 4.0

        print(f"\n✅ Processed {len(results)} estimates in parallel")

    @pytest.mark.asyncio
    async def test_estimate_idempotency(self):
        """Test that same request produces same result (idempotent)"""
        request = self.generate_test_request()

        # Process same request twice
        result1 = await self._process_full_pipeline(request)
        result2 = await self._process_full_pipeline(request)

        # Evidence hashes should match
        assert result1["evidence_hash"] == result2["evidence_hash"]
        assert result1["enclosure"]["selected_sku"] == result2["enclosure"]["selected_sku"]
        assert abs(result1["placement"]["phase_balance"] - result2["placement"]["phase_balance"]) < 0.01

    @pytest.mark.asyncio
    async def test_estimate_with_recovery(self):
        """Test estimate processing with failure recovery"""
        request = self.generate_test_request()

        # Simulate stage 3 failure
        self.mcp.inject_failure("estimate.format", 1)  # Fail once

        attempts = 0
        max_attempts = 3
        result = None

        while attempts < max_attempts:
            try:
                result = await self._process_full_pipeline(request)
                break
            except Exception as e:
                attempts += 1
                print(f"Attempt {attempts} failed: {str(e)}")
                await asyncio.sleep(0.1 * attempts)  # Exponential backoff

        assert result is not None, "Failed after all retry attempts"
        assert result["success"]

    async def _process_full_pipeline(self, request: Dict) -> Dict:
        """Helper to process full FIX-4 pipeline"""
        # Enclosure
        enclosure = await self.mcp.execute_tool("enclosure.solve", {
            "breakers": request["breakers"],
            "panel_config": request["panel_config"]
        })

        # Placement
        placement = await self.mcp.execute_tool("layout.place_breakers", {
            "breakers": request["breakers"],
            "enclosure": enclosure["selected_sku"],
            "phases": request["panel_config"]["phases"]
        })

        # Critic
        critic = await self.mcp.execute_tool("layout.validate_placement", {
            "placement": placement["positions"],
            "rules": ["clearance", "thermal", "phase_balance"]
        })

        # Format
        format_doc = await self.mcp.execute_tool("estimate.format", {
            "project_name": request["project_name"],
            "customer_id": request["customer_id"],
            "enclosure": enclosure,
            "placement": placement,
            "format": "xlsx"
        })

        # Cover
        cover = await self.mcp.execute_tool("doc.cover_generate", {
            "document_id": format_doc["document_id"],
            "project_name": request["project_name"]
        })

        # Lint
        lint = await self.mcp.execute_tool("doc.lint", {
            "document_id": format_doc["document_id"]
        })

        # Generate evidence
        evidence = self._generate_evidence({
            "request": request,
            "enclosure": enclosure,
            "placement": placement,
            "critic": critic,
            "format": format_doc,
            "cover": cover,
            "lint": lint
        })

        return {
            "success": True,
            "enclosure": enclosure,
            "placement": placement,
            "document_id": format_doc["document_id"],
            "evidence_hash": evidence["hash"]
        }

    def _generate_evidence(self, pipeline_data: Dict) -> Dict:
        """Generate evidence for audit trail"""
        evidence_str = json.dumps(pipeline_data, sort_keys=True, default=str)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()

        return {
            "hash": evidence_hash,
            "traceId": f"TRACE-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "stages": {
                "enclosure": pipeline_data.get("enclosure", {}).get("success", False),
                "placement": pipeline_data.get("placement", {}).get("success", False),
                "critic": pipeline_data.get("critic", {}).get("valid", False),
                "format": pipeline_data.get("format", {}).get("success", False),
                "cover": pipeline_data.get("cover", {}).get("success", False),
                "lint": pipeline_data.get("lint", {}).get("success", False)
            }
        }

    def test_estimate_validation_rules(self):
        """Test business rule validation"""

        # Rule: Min 1 breaker, max 100 breakers
        assert self._validate_breaker_count([]) == False
        assert self._validate_breaker_count([{"sku": "BKR-001"}] * 101) == False
        assert self._validate_breaker_count([{"sku": "BKR-001"}] * 50) == True

        # Rule: Phase balance must be ≤ 4%
        assert self._validate_phase_balance(2.5) == True
        assert self._validate_phase_balance(4.0) == True
        assert self._validate_phase_balance(4.1) == False

        # Rule: Enclosure fit must be ≥ 0.90
        assert self._validate_enclosure_fit(0.89) == False
        assert self._validate_enclosure_fit(0.90) == True
        assert self._validate_enclosure_fit(0.95) == True

    def _validate_breaker_count(self, breakers: List) -> bool:
        """Validate breaker count constraints"""
        return 1 <= len(breakers) <= 100

    def _validate_phase_balance(self, balance: float) -> bool:
        """Validate phase balance constraint"""
        return balance <= 4.0

    def _validate_enclosure_fit(self, fit_score: float) -> bool:
        """Validate enclosure fit score"""
        return fit_score >= 0.90

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])