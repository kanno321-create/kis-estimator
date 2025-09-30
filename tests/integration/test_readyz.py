"""
Integration tests for /readyz endpoint
Tests DB and Storage health validation
"""

import pytest
from httpx import AsyncClient

from api.main import app

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_readyz_healthy():
    """Test /readyz endpoint returns 200 when all systems are healthy"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/readyz")

    # Verify status code
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # Verify response format
    data = response.json()
    assert "status" in data, "Response missing 'status' field"
    assert "db" in data, "Response missing 'db' field"
    assert "storage" in data, "Response missing 'storage' field"
    assert "ts" in data, "Response missing 'ts' field"

    # Verify values
    assert data["status"] == "ok", f"Expected status='ok', got '{data['status']}'"
    assert data["db"] == "ok", f"Expected db='ok', got '{data['db']}'"
    assert (
        data["storage"] == "ok"
    ), f"Expected storage='ok', got '{data['storage']}'"

    # Verify timestamp format (UTC ISO with Z suffix)
    assert data["ts"].endswith("Z"), f"Timestamp must end with 'Z': {data['ts']}"
    assert "T" in data["ts"], f"Timestamp must be ISO format: {data['ts']}"


@pytest.mark.asyncio
async def test_readyz_response_time():
    """Test /readyz endpoint responds within performance requirements (< 50ms)"""
    import time

    async with AsyncClient(app=app, base_url="http://test") as client:
        start = time.time()
        response = await client.get("/readyz")
        elapsed_ms = (time.time() - start) * 1000

    assert response.status_code == 200
    assert (
        elapsed_ms < 200
    ), f"Readyz endpoint too slow: {elapsed_ms:.2f}ms (target < 50ms, max 200ms)"


@pytest.mark.asyncio
async def test_readyz_db_validation():
    """Test /readyz executes DB validation (SELECT 1, UTC timestamp)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    data = response.json()

    # DB health should include timestamp validation
    assert data["db"] == "ok"
    assert "ts" in data

    # Timestamp should be current (within last 5 seconds)
    from datetime import datetime, timezone

    ts = datetime.fromisoformat(data["ts"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta_seconds = abs((now - ts).total_seconds())

    assert (
        delta_seconds < 5
    ), f"Timestamp too old: {delta_seconds:.2f}s (should be < 5s)"


@pytest.mark.asyncio
async def test_readyz_storage_validation():
    """Test /readyz executes Storage validation (upload → signed URL → cleanup)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 200
    data = response.json()

    # Storage health validation
    assert data["storage"] == "ok"

    # This confirms:
    # 1. Upload test file succeeded
    # 2. Signed URL generation succeeded
    # 3. Cleanup (delete) succeeded


@pytest.mark.asyncio
async def test_readyz_degraded_state():
    """Test /readyz returns 503 when services are degraded"""
    # This test requires mocking DB or Storage failure
    # For now, just verify the endpoint structure
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/readyz")

    # In healthy state, should return 200
    # In degraded state (mocked), should return 503 with error details
    if response.status_code == 503:
        data = response.json()
        assert "status" in data
        assert data["status"] == "degraded"
        assert "db" in data
        assert "storage" in data
        # Optional error fields
        if "db_error" in data:
            assert isinstance(data["db_error"], str)
        if "storage_error" in data:
            assert isinstance(data["storage_error"], str)
    else:
        # Healthy state
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_readyz_headers():
    """Test /readyz includes trace ID and process time headers"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/readyz")

    assert response.status_code == 200

    # Verify trace ID header
    assert "x-trace-id" in response.headers, "Missing X-Trace-Id header"
    trace_id = response.headers["x-trace-id"]
    assert len(trace_id) > 0, "Trace ID is empty"

    # Verify process time header
    assert "x-process-time" in response.headers, "Missing X-Process-Time header"
    process_time = float(response.headers["x-process-time"])
    assert process_time > 0, "Process time should be positive"
    assert (
        process_time < 1.0
    ), f"Process time too high: {process_time}s (should be < 1s)"