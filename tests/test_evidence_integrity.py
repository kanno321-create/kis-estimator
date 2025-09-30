"""Evidence Integrity Tests - SHA256 verification"""
import hashlib
import pytest
from api.services.document_service import upload_evidence, verify_evidence_integrity

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_evidence_sha256_integrity():
    """Test uploaded evidence SHA256 matches DB record"""
    quote_id = "test-evidence-123"
    stage = "enclosure"
    test_data = b"TEST_EVIDENCE_DATA"
    ext = "json"
    
    # Upload evidence
    upload_result = await upload_evidence(quote_id, stage, test_data, ext)
    stored_hash = upload_result["sha256"]
    
    # Calculate expected hash
    expected_hash = hashlib.sha256(test_data).hexdigest()
    
    # Verify hashes match
    assert stored_hash == expected_hash, "Uploaded SHA256 must match computed hash"
    
    # Verify integrity check
    verify_result = await verify_evidence_integrity(quote_id, stage)
    assert verify_result["valid"] is True, "Evidence integrity check must pass"
    assert verify_result["stored_hash"] == expected_hash
    assert verify_result["computed_hash"] == expected_hash


@pytest.mark.asyncio
async def test_evidence_path_structure():
    """Test evidence path follows required structure"""
    quote_id = "test-path-123"
    stage = "format"
    test_data = b"PATH_TEST_DATA"
    ext = "pdf"
    
    result = await upload_evidence(quote_id, stage, test_data, ext)
    path = result["path"]
    
    # Verify path structure: evidence/quote/{id}/{stage}/{sha256}.{ext}
    assert path.startswith(f"evidence/quote/{quote_id}/{stage}/")
    assert path.endswith(f".{ext}")
    
    # Extract SHA256 from path
    sha256_part = path.split("/")[-1].replace(f".{ext}", "")
    assert len(sha256_part) == 64
    assert sha256_part == result["sha256"]
