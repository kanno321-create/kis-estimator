"""
SSE Authentication Tests
Tests for /api/sse/test endpoint with JWT authentication.
"""
import os
import pytest
from httpx import AsyncClient
from api.main import app

pytestmark = pytest.mark.asyncio

async def test_sse_no_auth():
    """Test SSE endpoint without authentication - should return 401"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/sse/test")
        assert response.status_code == 401

async def test_sse_invalid_auth():
    """Test SSE endpoint with invalid token - should return 403"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(
            "/api/sse/test",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 403

@pytest.mark.skipif(not os.environ.get("KIS_JWT"), reason="No real JWT provided")
async def test_sse_with_valid_jwt():
    """Test SSE endpoint with valid JWT - should return 200 and stream"""
    token = os.environ["KIS_JWT"]

    async with AsyncClient(app=app, base_url="http://test", timeout=10.0) as ac:
        async with ac.stream(
            "GET",
            "/api/sse/test",
            headers={"Authorization": f"Bearer {token}"}
        ) as response:
            assert response.status_code == 200
            assert response.headers.get("content-type", "").startswith("text/event-stream")
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"

            # Read first few lines
            lines = []
            async for line in response.aiter_lines():
                lines.append(line)
                if len(lines) >= 10:  # Read first 10 lines
                    break

            # Check for hello event
            assert any("event: hello" in line for line in lines)
            assert any("data:" in line and "traceId" in line for line in lines)

async def test_readyz_includes_sse_check():
    """Test that /readyz includes SSE status check"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/readyz")

        # May return 503 if DB/storage not available, but should still have sse check
        data = response.json()

        assert "checks" in data
        assert "sse" in data["checks"]
        # SSE router should be registered, so status should be "ok"
        assert data["checks"]["sse"] == "ok"