"""
Integration tests for Evidence Upload Flow
Tests: upload → SHA256 verification → signed URL → download
"""

import hashlib
import json
import uuid

import pytest

from api.services.document_service import (
    create_signed_url,
    upload_evidence,
    verify_evidence_integrity,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_evidence_upload_success():
    """Test successful evidence upload with SHA256 validation"""
    # Arrange
    quote_id = str(uuid.uuid4())
    stage = "enclosure"
    test_data = {"test": "evidence data", "timestamp": "2025-09-30T10:00:00Z"}
    file_bytes = json.dumps(test_data, ensure_ascii=False).encode("utf-8")
    ext = "json"

    # Act
    result = await upload_evidence(quote_id, stage, file_bytes, ext)

    # Assert
    assert "path" in result, "Result missing 'path' field"
    assert "sha256" in result, "Result missing 'sha256' field"
    assert "quote_id" in result, "Result missing 'quote_id' field"
    assert "stage" in result, "Result missing 'stage' field"
    assert "id" in result, "Result missing 'id' field"

    # Verify path format: evidence/quote/{quote_id}/{stage}/{sha256}.{ext}
    expected_path_prefix = f"evidence/quote/{quote_id}/{stage}/"
    assert result["path"].startswith(
        expected_path_prefix
    ), f"Path should start with '{expected_path_prefix}'"
    assert result["path"].endswith(
        f".{ext}"
    ), f"Path should end with '.{ext}'"

    # Verify SHA256 hash
    expected_hash = hashlib.sha256(file_bytes).hexdigest()
    assert (
        result["sha256"] == expected_hash
    ), f"SHA256 mismatch: expected {expected_hash}, got {result['sha256']}"

    # Verify quote_id and stage
    assert result["quote_id"] == quote_id
    assert result["stage"] == stage


@pytest.mark.asyncio
async def test_evidence_upload_invalid_stage():
    """Test evidence upload rejects invalid stage"""
    quote_id = str(uuid.uuid4())
    invalid_stage = "invalid_stage_name"
    file_bytes = b"test data"
    ext = "json"

    with pytest.raises(ValueError) as exc_info:
        await upload_evidence(quote_id, invalid_stage, file_bytes, ext)

    assert "Invalid stage" in str(exc_info.value)


@pytest.mark.asyncio
async def test_evidence_upload_invalid_extension():
    """Test evidence upload rejects invalid file extension"""
    quote_id = str(uuid.uuid4())
    stage = "enclosure"
    file_bytes = b"test data"
    invalid_ext = "exe"

    with pytest.raises(ValueError) as exc_info:
        await upload_evidence(quote_id, stage, file_bytes, invalid_ext)

    assert "Invalid extension" in str(exc_info.value)


@pytest.mark.asyncio
async def test_signed_url_generation():
    """Test signed URL generation for evidence artifact"""
    # First upload evidence
    quote_id = str(uuid.uuid4())
    stage = "breaker"
    test_data = {"breaker": "placement data"}
    file_bytes = json.dumps(test_data).encode("utf-8")
    ext = "json"

    result = await upload_evidence(quote_id, stage, file_bytes, ext)
    path = result["path"]

    # Generate signed URL
    signed_url = create_signed_url(path, ttl=600)

    # Verify URL format
    assert signed_url.startswith("http"), "Signed URL should start with http(s)"
    assert (
        "evidence/quote" in signed_url
    ), "Signed URL should contain evidence path"

    # Verify URL is accessible (optional, requires actual HTTP request)
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(signed_url)
    #     assert response.status_code == 200


@pytest.mark.asyncio
async def test_evidence_integrity_verification():
    """Test evidence integrity verification by SHA256 comparison"""
    # Upload evidence
    quote_id = str(uuid.uuid4())
    stage = "critic"
    test_data = {"violations": [], "warnings": ["thermal margin low"]}
    file_bytes = json.dumps(test_data, ensure_ascii=False).encode("utf-8")
    ext = "json"

    upload_result = await upload_evidence(quote_id, stage, file_bytes, ext)
    stored_hash = upload_result["sha256"]

    # Verify integrity
    verify_result = await verify_evidence_integrity(quote_id, stage)

    # Assert
    assert verify_result["valid"] is True, "Evidence integrity check should pass"
    assert (
        verify_result["path"] == upload_result["path"]
    ), "Path mismatch"
    assert (
        verify_result["stored_hash"] == stored_hash
    ), "Stored hash mismatch"
    assert (
        verify_result["computed_hash"] == stored_hash
    ), "Computed hash should match stored hash"


@pytest.mark.asyncio
async def test_complete_evidence_flow():
    """
    Test complete evidence flow:
    1. Upload evidence → 2. Verify SHA256 → 3. Generate signed URL → 4. Verify download
    """
    # Step 1: Upload evidence
    quote_id = str(uuid.uuid4())
    stage = "format"
    test_data = {
        "quote_id": quote_id,
        "customer": "Test Customer",
        "total": 5000000,
        "currency": "KRW",
    }
    file_bytes = json.dumps(test_data, ensure_ascii=False).encode("utf-8")
    expected_hash = hashlib.sha256(file_bytes).hexdigest()
    ext = "json"

    upload_result = await upload_evidence(quote_id, stage, file_bytes, ext)

    # Step 2: Verify SHA256 matches
    assert upload_result["sha256"] == expected_hash, "SHA256 hash verification failed"

    # Step 3: Verify integrity
    integrity_result = await verify_evidence_integrity(quote_id, stage)
    assert integrity_result["valid"] is True, "Integrity check failed"
    assert (
        integrity_result["stored_hash"] == expected_hash
    ), "Stored hash mismatch"
    assert (
        integrity_result["computed_hash"] == expected_hash
    ), "Computed hash mismatch"

    # Step 4: Generate signed URL
    signed_url = create_signed_url(upload_result["path"], ttl=600)
    assert signed_url is not None, "Signed URL generation failed"
    assert len(signed_url) > 0, "Signed URL is empty"

    # Step 5: Verify signed URL is accessible (optional, requires actual download)
    # This would require actually downloading the file via HTTP
    # For now, just verify URL format
    assert "evidence/quote" in signed_url


@pytest.mark.asyncio
async def test_multiple_stage_evidence():
    """Test uploading evidence for multiple FIX-4 pipeline stages"""
    quote_id = str(uuid.uuid4())
    stages = ["enclosure", "breaker", "critic", "format", "cover", "lint"]

    uploaded_evidence = {}

    for stage in stages:
        test_data = {"stage": stage, "quote_id": quote_id, "data": f"test_{stage}"}
        file_bytes = json.dumps(test_data).encode("utf-8")
        ext = "json"

        result = await upload_evidence(quote_id, stage, file_bytes, ext)

        # Verify each upload
        assert result["stage"] == stage
        assert result["quote_id"] == quote_id
        uploaded_evidence[stage] = result

    # Verify all stages have different paths and hashes
    paths = [ev["path"] for ev in uploaded_evidence.values()]
    hashes = [ev["sha256"] for ev in uploaded_evidence.values()]

    assert len(paths) == len(set(paths)), "Paths should be unique"
    assert len(hashes) == len(set(hashes)), "Hashes should be unique"


@pytest.mark.asyncio
async def test_evidence_path_structure():
    """Test evidence path follows required structure"""
    quote_id = str(uuid.uuid4())
    stage = "enclosure"
    file_bytes = b"test evidence data"
    ext = "json"

    result = await upload_evidence(quote_id, stage, file_bytes, ext)
    path = result["path"]

    # Parse path structure: evidence/quote/{quote_id}/{stage}/{sha256}.{ext}
    parts = path.split("/")

    assert parts[0] == "evidence", "Path should start with 'evidence'"
    assert parts[1] == "quote", "Second part should be 'quote'"
    assert parts[2] == quote_id, f"Third part should be quote_id: {quote_id}"
    assert parts[3] == stage, f"Fourth part should be stage: {stage}"

    # Filename: {sha256}.{ext}
    filename = parts[4]
    assert filename.endswith(f".{ext}"), f"Filename should end with .{ext}"

    # SHA256 part should be 64 hex characters
    sha256_part = filename.replace(f".{ext}", "")
    assert len(sha256_part) == 64, "SHA256 should be 64 characters"
    assert sha256_part.isalnum(), "SHA256 should be hexadecimal"
    assert sha256_part.islower(), "SHA256 should be lowercase"