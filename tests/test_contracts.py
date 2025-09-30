"""Contract Validation Tests - OpenAPI 3.1 Schema Validation"""
import yaml
import pytest
from pathlib import Path

OPENAPI_PATH = Path(__file__).parent.parent / "openapi.yaml"

@pytest.fixture(scope="module")
def openapi_spec():
    """Load OpenAPI specification"""
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_openapi_version(openapi_spec):
    """Verify OpenAPI 3.1.0"""
    assert openapi_spec["openapi"] == "3.1.0"

def test_required_paths(openapi_spec):
    """Verify all required paths exist"""
    paths = openapi_spec["paths"]
    required_paths = [
        "/v1/estimate",
        "/v1/estimate/{id}",
        "/v1/estimate/stream",
        "/v1/validate",
        "/v1/documents",
        "/v1/documents/export",
        "/v1/catalog",
        "/v1/catalog/items"
    ]
    for path in required_paths:
        assert path in paths, f"Missing path: {path}"

def test_error_schema(openapi_spec):
    """Verify Error schema includes all required fields"""
    error_schema = openapi_spec["components"]["schemas"]["Error"]
    required_fields = ["code", "message", "traceId", "meta"]
    
    assert "required" in error_schema
    for field in required_fields:
        assert field in error_schema["required"], f"Missing required field: {field}"
    
    # Verify meta.dedupKey
    meta_schema = error_schema["properties"]["meta"]
    assert "dedupKey" in meta_schema["required"]

def test_estimate_post_operation(openapi_spec):
    """Verify POST /v1/estimate operation"""
    estimate_post = openapi_spec["paths"]["/v1/estimate"]["post"]
    
    assert estimate_post["operationId"] == "createEstimate"
    assert "requestBody" in estimate_post
    assert "responses" in estimate_post
    assert "201" in estimate_post["responses"]
    assert "400" in estimate_post["responses"]

def test_sse_stream_operation(openapi_spec):
    """Verify GET /v1/estimate/stream (SSE)"""
    sse_get = openapi_spec["paths"]["/v1/estimate/stream"]["get"]
    
    assert sse_get["operationId"] == "streamEstimate"
    assert "200" in sse_get["responses"]

def test_validate_operation(openapi_spec):
    """Verify POST /v1/validate"""
    validate_post = openapi_spec["paths"]["/v1/validate"]["post"]
    
    assert validate_post["operationId"] == "validateInput"
    assert "requestBody" in validate_post

def test_documents_operations(openapi_spec):
    """Verify documents endpoints"""
    docs_get = openapi_spec["paths"]["/v1/documents"]["get"]
    docs_export_post = openapi_spec["paths"]["/v1/documents/export"]["post"]
    
    assert docs_get["operationId"] == "listDocuments"
    assert docs_export_post["operationId"] == "exportDocuments"

def test_catalog_operations(openapi_spec):
    """Verify catalog endpoints"""
    catalog_get = openapi_spec["paths"]["/v1/catalog"]["get"]
    catalog_items_post = openapi_spec["paths"]["/v1/catalog/items"]["post"]
    
    assert catalog_get["operationId"] == "listCatalog"
    assert catalog_items_post["operationId"] == "upsertCatalogItems"
