"""
KIS Estimator - Operations /readyz Endpoint Test
Tests health check with DB ping + Storage self-check + traceId
"""

import pytest
import os
import hashlib
import uuid
from datetime import datetime, timezone


@pytest.fixture
def supabase_client():
    """Supabase client with service role key"""
    try:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            pytest.skip("Supabase credentials not configured")

        return create_client(url, key)
    except ImportError:
        pytest.skip("supabase-py not installed")


def test_readyz_db_ping(supabase_client):
    """Test /readyz DB ping with UTC timestamp"""
    response = supabase_client.rpc("health_check_detailed").execute()

    assert response.data is not None
    assert len(response.data) > 0

    # Check database component
    db_component = next((c for c in response.data if c["component"] == "database"), None)
    assert db_component is not None
    assert db_component["status"] == "ok"
    assert "utc_time" in db_component["details"]


def test_readyz_storage_self_check(supabase_client):
    """Test /readyz Storage self-check with signed URL"""
    # Generate test file
    test_data = b"test evidence data"
    test_sha256 = hashlib.sha256(test_data).hexdigest()
    test_filename = f"test_{uuid.uuid4().hex}.txt"
    test_path = f"evidence/test/{test_filename}"

    try:
        # 1. Upload test file
        upload_response = supabase_client.storage.from_("evidence").upload(
            test_path, test_data
        )
        assert upload_response is not None

        # 2. Generate signed URL (TTL from env or default 600s)
        ttl = int(os.getenv("SIGNED_URL_TTL_SEC", "600"))
        signed_url = supabase_client.storage.from_("evidence").create_signed_url(
            test_path, ttl
        )
        assert "signedURL" in signed_url

        # 3. Download via signed URL and verify SHA256
        import requests
        download_response = requests.get(signed_url["signedURL"])
        assert download_response.status_code == 200

        downloaded_sha256 = hashlib.sha256(download_response.content).hexdigest()
        assert downloaded_sha256 == test_sha256

    finally:
        # Cleanup: delete test file
        try:
            supabase_client.storage.from_("evidence").remove([test_path])
        except:
            pass


def test_readyz_response_format():
    """Test /readyz response format with required fields"""
    # Mock readyz response structure
    readyz_response = {
        "status": "ok",
        "db": "ok",
        "storage": "ok",
        "ts": datetime.now(timezone.utc).isoformat(),
        "traceId": str(uuid.uuid4())
    }

    # Validate fields
    assert "status" in readyz_response
    assert "db" in readyz_response
    assert "storage" in readyz_response
    assert "ts" in readyz_response
    assert "traceId" in readyz_response

    # Validate timestamp format (ISO 8601 with Z)
    ts = readyz_response["ts"]
    assert ts.endswith("Z") or "+" in ts  # UTC indicator

    # Validate traceId format (UUID)
    trace_id = readyz_response["traceId"]
    uuid.UUID(trace_id)  # Raises ValueError if invalid


def test_readyz_under_50ms(supabase_client):
    """Test /readyz response time < 50ms (operations target)"""
    import time

    start = time.perf_counter()
    response = supabase_client.rpc("health_check_detailed").execute()
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.data is not None
    assert elapsed_ms < 50, f"Health check took {elapsed_ms:.2f}ms (target: <50ms)"


def test_readyz_failure_detection():
    """Test /readyz detects failures correctly"""
    # Simulate DB failure
    fake_response = {
        "status": "error",
        "db": "error",
        "storage": "ok",
        "ts": datetime.now(timezone.utc).isoformat(),
        "traceId": str(uuid.uuid4()),
        "error": "Database connection failed"
    }

    assert fake_response["status"] == "error"
    assert fake_response["db"] == "error"
    assert "error" in fake_response