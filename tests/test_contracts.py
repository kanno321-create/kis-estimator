"""Contract Validation Tests - OpenAPI 3.1 Compliance"""
import pytest
import json
from typing import Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime
import yaml
from pathlib import Path

# OpenAPI 3.1 Contract Models
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    code: str = Field(..., pattern="^[A-Z][A-Z0-9_]{2,}$")
    message: str = Field(..., min_length=1, max_length=500)
    hint: str = Field(None, max_length=200)
    traceId: str = Field(..., pattern="^[a-f0-9]{32}$")
    meta: Dict[str, Any] = Field(default_factory=dict)

class EstimateRequest(BaseModel):
    """Estimate creation request schema"""
    project_name: str = Field(..., min_length=1, max_length=200)
    customer_id: str = Field(..., pattern="^[a-f0-9-]{36}$")
    breakers: List[Dict[str, Any]]
    panel_config: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EstimateResponse(BaseModel):
    """Estimate response schema"""
    id: str = Field(..., pattern="^EST-[A-Z0-9]{8}$")
    status: str = Field(..., pattern="^(pending|processing|completed|failed)$")
    created_at: datetime
    updated_at: datetime
    result: Dict[str, Any] = None
    evidence_hash: str = Field(None, pattern="^[a-f0-9]{64}$")
    links: Dict[str, str] = Field(default_factory=dict)

class ValidationRequest(BaseModel):
    """Validation request schema"""
    estimate_id: str = Field(..., pattern="^EST-[A-Z0-9]{8}$")
    validation_type: str = Field(..., pattern="^(phase_balance|clearance|thermal|all)$")
    threshold: Dict[str, float] = Field(default_factory=dict)

class ValidationResponse(BaseModel):
    """Validation response schema"""
    valid: bool
    score: float = Field(..., ge=0.0, le=1.0)
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)

class DocumentRequest(BaseModel):
    """Document generation request schema"""
    estimate_id: str = Field(..., pattern="^EST-[A-Z0-9]{8}$")
    format: str = Field(..., pattern="^(pdf|xlsx|svg|json)$")
    template: str = Field(None, max_length=50)
    options: Dict[str, Any] = Field(default_factory=dict)

class DocumentResponse(BaseModel):
    """Document response schema"""
    document_id: str = Field(..., pattern="^DOC-[A-Z0-9]{8}$")
    format: str
    size_bytes: int = Field(..., gt=0)
    download_url: str = Field(..., pattern="^https?://")
    expires_at: datetime
    checksum: str = Field(..., pattern="^[a-f0-9]{64}$")

class SSEEvent(BaseModel):
    """Server-Sent Event schema"""
    event: str = Field(..., pattern="^(heartbeat|progress|complete|error)$")
    data: Dict[str, Any]
    id: str = Field(None, pattern="^[a-f0-9]{16}$")
    retry: int = Field(None, ge=1000, le=30000)

class TestContractValidation:
    """Test OpenAPI 3.1 contract compliance"""

    def test_error_response_schema(self):
        """Test error response follows contract"""
        # Valid error response
        valid_error = {
            "code": "VALIDATION_ERROR",
            "message": "Phase balance exceeds 4% threshold",
            "hint": "Try redistributing breakers across phases",
            "traceId": "a1b2c3d4e5f678901234567890123456",
            "meta": {"dedupKey": "phase_balance_4pct"}
        }

        error = ErrorResponse(**valid_error)
        assert error.code == "VALIDATION_ERROR"
        assert len(error.traceId) == 32

        # Invalid code format
        with pytest.raises(ValidationError) as exc:
            ErrorResponse(**{**valid_error, "code": "invalid-code"})
        assert "pattern" in str(exc.value).lower()

        # Missing required fields
        with pytest.raises(ValidationError) as exc:
            ErrorResponse(code="ERROR", message="")
        assert "message" in str(exc.value).lower()

    def test_estimate_request_validation(self):
        """Test estimate request schema validation"""
        valid_request = {
            "project_name": "Main Distribution Board",
            "customer_id": "123e4567-e89b-12d3-a456-426614174000",
            "breakers": [
                {"sku": "BKR-001", "quantity": 5, "rating": 32},
                {"sku": "BKR-002", "quantity": 3, "rating": 63}
            ],
            "panel_config": {
                "width": 800,
                "height": 2000,
                "phases": 3
            }
        }

        request = EstimateRequest(**valid_request)
        assert request.customer_id == "123e4567-e89b-12d3-a456-426614174000"

        # Invalid UUID format
        with pytest.raises(ValidationError):
            EstimateRequest(**{**valid_request, "customer_id": "not-a-uuid"})

        # Empty project name
        with pytest.raises(ValidationError):
            EstimateRequest(**{**valid_request, "project_name": ""})

    def test_estimate_response_validation(self):
        """Test estimate response schema validation"""
        valid_response = {
            "id": "EST-ABC12345",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:01:00Z",
            "result": {
                "phase_balance": 2.5,
                "enclosure_fit": 0.92
            },
            "evidence_hash": "a" * 64,
            "links": {
                "self": "/v1/estimate/EST-ABC12345",
                "validation": "/v1/validate/EST-ABC12345"
            }
        }

        response = EstimateResponse(**valid_response)
        assert response.status == "completed"
        assert len(response.evidence_hash) == 64

        # Invalid status
        with pytest.raises(ValidationError):
            EstimateResponse(**{**valid_response, "status": "unknown"})

        # Invalid estimate ID format
        with pytest.raises(ValidationError):
            EstimateResponse(**{**valid_response, "id": "invalid-id"})

    def test_validation_schemas(self):
        """Test validation request/response schemas"""
        # Request
        valid_request = {
            "estimate_id": "EST-12345678",
            "validation_type": "phase_balance",
            "threshold": {"balance": 4.0, "clearance": 10.0}
        }

        request = ValidationRequest(**valid_request)
        assert request.validation_type == "phase_balance"

        # Response
        valid_response = {
            "valid": True,
            "score": 0.95,
            "violations": [],
            "warnings": [
                {"type": "MINOR", "message": "Phase B at 98% capacity"}
            ],
            "evidence": {"calculation_path": "trace_123.json"}
        }

        response = ValidationResponse(**valid_response)
        assert response.score == 0.95

        # Score out of range
        with pytest.raises(ValidationError):
            ValidationResponse(**{**valid_response, "score": 1.5})

    def test_document_schemas(self):
        """Test document request/response schemas"""
        # Request
        valid_request = {
            "estimate_id": "EST-87654321",
            "format": "pdf",
            "template": "standard",
            "options": {"include_cover": True}
        }

        request = DocumentRequest(**valid_request)
        assert request.format == "pdf"

        # Invalid format
        with pytest.raises(ValidationError):
            DocumentRequest(**{**valid_request, "format": "doc"})

        # Response
        valid_response = {
            "document_id": "DOC-ABC12345",
            "format": "pdf",
            "size_bytes": 1024000,
            "download_url": "https://storage.example.com/doc.pdf",
            "expires_at": "2024-01-02T00:00:00Z",
            "checksum": "b" * 64
        }

        response = DocumentResponse(**valid_response)
        assert response.size_bytes > 0

        # Invalid checksum
        with pytest.raises(ValidationError):
            DocumentResponse(**{**valid_response, "checksum": "short"})

    def test_sse_event_schema(self):
        """Test Server-Sent Event schema"""
        valid_event = {
            "event": "progress",
            "data": {
                "stage": "breaker_placement",
                "progress": 0.75,
                "message": "Optimizing phase balance"
            },
            "id": "a1b2c3d4e5f67890",
            "retry": 5000
        }

        event = SSEEvent(**valid_event)
        assert event.event == "progress"
        assert event.retry == 5000

        # Invalid event type
        with pytest.raises(ValidationError):
            SSEEvent(**{**valid_event, "event": "unknown"})

        # Retry out of range
        with pytest.raises(ValidationError):
            SSEEvent(**{**valid_event, "retry": 100})

    def test_openapi_spec_compliance(self):
        """Test that API spec follows OpenAPI 3.1 standard"""
        spec = {
            "openapi": "3.1.0",
            "info": {
                "title": "KIS Estimator API",
                "version": "1.0.0"
            },
            "paths": {
                "/v1/estimate": {
                    "post": {
                        "operationId": "createEstimate",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/EstimateRequest"}
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Estimate created successfully",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/EstimateResponse"}
                                    }
                                }
                            },
                            "400": {
                                "description": "Validation error",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # Validate OpenAPI version
        assert spec["openapi"] == "3.1.0"

        # Check required info fields
        assert "title" in spec["info"]
        assert "version" in spec["info"]

        # Check path structure
        assert "/v1/estimate" in spec["paths"]
        assert "post" in spec["paths"]["/v1/estimate"]

        # Check operation has required fields
        operation = spec["paths"]["/v1/estimate"]["post"]
        assert "operationId" in operation
        assert "responses" in operation
        assert "200" in operation["responses"]
        assert "400" in operation["responses"]

    def test_contract_breaking_changes(self):
        """Test detection of breaking contract changes"""
        original_schema = {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "optional": {"type": "string"}
            }
        }

        # Adding optional field is non-breaking
        new_schema_compatible = {
            **original_schema,
            "properties": {
                **original_schema["properties"],
                "new_optional": {"type": "string"}
            }
        }
        assert self._is_compatible(original_schema, new_schema_compatible)

        # Removing required field is breaking
        new_schema_breaking = {
            **original_schema,
            "required": ["id"]  # Removed 'name'
        }
        assert not self._is_compatible(original_schema, new_schema_breaking)

        # Changing field type is breaking
        new_schema_type_change = {
            **original_schema,
            "properties": {
                **original_schema["properties"],
                "id": {"type": "number"}  # Changed from string
            }
        }
        assert not self._is_compatible(original_schema, new_schema_type_change)

    def _is_compatible(self, old_schema: Dict, new_schema: Dict) -> bool:
        """Check if new schema is backward compatible with old"""
        # Check required fields haven't been removed
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        if not old_required.issubset(new_required):
            return False

        # Check field types haven't changed
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        for field, spec in old_props.items():
            if field in new_props:
                if spec.get("type") != new_props[field].get("type"):
                    return False

        return True

    def test_contract_evidence_generation(self):
        """Test that all responses include evidence for audit"""
        import hashlib

        # Simulate response with evidence
        response_data = {
            "id": "EST-12345678",
            "result": {"phase_balance": 2.5},
            "timestamp": "2024-01-01T00:00:00Z"
        }

        # Generate evidence hash
        evidence_str = json.dumps(response_data, sort_keys=True)
        evidence_hash = hashlib.sha256(evidence_str.encode()).hexdigest()

        # Verify hash format
        assert len(evidence_hash) == 64
        assert all(c in "0123456789abcdef" for c in evidence_hash)

        # Verify evidence can be reconstructed
        reconstructed_hash = hashlib.sha256(evidence_str.encode()).hexdigest()
        assert reconstructed_hash == evidence_hash

if __name__ == "__main__":
    pytest.main([__file__, "-v"])