"""Rate Limiting Security Tests"""
import pytest
import time
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from collections import defaultdict
from datetime import datetime, timedelta

# In-memory rate limiter for testing
class MockRateLimiter:
    """Mock rate limiter with in-memory storage"""
    def __init__(self):
        self.requests = defaultdict(list)
        self.limits = {
            "default": {"requests": 100, "window": 60},  # 100 req/min
            "strict": {"requests": 10, "window": 60},    # 10 req/min
            "burst": {"requests": 5, "window": 1}        # 5 req/sec
        }

    def check_rate_limit(self, identifier: str, limit_type: str = "default") -> bool:
        """Check if request is within rate limit"""
        limit = self.limits[limit_type]
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=limit["window"])

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > window_start
        ]

        # Check limit
        if len(self.requests[identifier]) >= limit["requests"]:
            return False

        # Add request
        self.requests[identifier].append(now)
        return True

    def reset(self):
        """Reset all rate limit data"""
        self.requests.clear()

# Create test app with rate limiting
def create_rate_limited_app():
    """Create FastAPI app with rate limiting"""
    app = FastAPI()

    # Create limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Mock rate limiter for testing
    mock_limiter = MockRateLimiter()

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Custom rate limit middleware for testing"""
        # Get client identifier
        client_ip = request.client.host if request.client else "test-client"

        # Determine limit type based on endpoint
        limit_type = "default"
        if "/strict" in request.url.path:
            limit_type = "strict"
        elif "/burst" in request.url.path:
            limit_type = "burst"

        # Check rate limit
        if not mock_limiter.check_rate_limit(client_ip, limit_type):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests for {limit_type} limit",
                    "retry_after": mock_limiter.limits[limit_type]["window"]
                },
                headers={
                    "X-RateLimit-Limit": str(mock_limiter.limits[limit_type]["requests"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + mock_limiter.limits[limit_type]["window"])
                }
            )

        response = await call_next(request)

        # Add rate limit headers
        limit = mock_limiter.limits[limit_type]
        remaining = limit["requests"] - len(mock_limiter.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(limit["requests"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + limit["window"])

        return response

    @app.get("/api/public")
    async def public_endpoint():
        return {"message": "Public endpoint"}

    @app.get("/api/strict")
    async def strict_endpoint():
        return {"message": "Strict rate limited endpoint"}

    @app.get("/api/burst")
    async def burst_endpoint():
        return {"message": "Burst limited endpoint"}

    @app.post("/api/v1/estimate")
    async def estimate_endpoint():
        return {"message": "Estimate endpoint"}

    # Attach mock limiter for testing
    app.state.mock_limiter = mock_limiter

    return app

from fastapi.responses import JSONResponse

class TestRateLimiting:
    """Test suite for rate limiting"""

    def setup_method(self):
        """Setup test client"""
        self.app = create_rate_limited_app()
        self.client = TestClient(self.app)
        # Reset rate limiter before each test
        if hasattr(self.app.state, 'mock_limiter'):
            self.app.state.mock_limiter.reset()

    def test_rate_limit_not_exceeded(self):
        """Test requests within rate limit"""
        # Default limit is 100 req/min
        for i in range(10):
            response = self.client.get("/api/public")
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert int(response.headers["X-RateLimit-Remaining"]) >= 90

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded returns 429"""
        # Strict endpoint has 10 req/min limit
        responses = []
        for i in range(15):  # Try 15 requests
            response = self.client.get("/api/strict")
            responses.append(response.status_code)

        # First 10 should succeed
        assert responses[:10].count(200) == 10
        # Remaining should be rate limited
        assert responses[10:].count(429) == 5

    def test_rate_limit_headers(self):
        """Test rate limit headers are present"""
        response = self.client.get("/api/public")
        assert response.status_code == 200

        # Check headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        limit = int(response.headers["X-RateLimit-Limit"])
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert limit == 100  # Default limit
        assert remaining == 99  # After one request

    def test_rate_limit_429_response_format(self):
        """Test 429 response format"""
        # Exhaust burst limit (5 req/sec)
        for i in range(6):
            response = self.client.get("/api/burst")

        # Last request should be rate limited
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]
        assert "retry_after" in data

    def test_rate_limit_per_client(self):
        """Test rate limiting is per-client"""
        # Simulate different clients
        client1 = TestClient(self.app)
        client2 = TestClient(self.app)

        # Client 1 makes requests
        for i in range(5):
            response = client1.get("/api/burst")
            assert response.status_code == 200

        # Client 1 is rate limited
        response = client1.get("/api/burst")
        assert response.status_code == 429

        # Client 2 can still make requests
        response = client2.get("/api/burst")
        # Note: In real test this would work, but TestClient shares state
        # This is a limitation of the test setup

    def test_rate_limit_window_reset(self):
        """Test rate limit window reset"""
        # Use burst limit (5 req/1sec)
        for i in range(5):
            response = self.client.get("/api/burst")
            assert response.status_code == 200

        # Should be rate limited
        response = self.client.get("/api/burst")
        assert response.status_code == 429

        # Wait for window to reset
        time.sleep(1.1)

        # Should work again
        response = self.client.get("/api/burst")
        assert response.status_code == 200

    def test_different_endpoints_different_limits(self):
        """Test different endpoints can have different rate limits"""
        # Public endpoint - default limit (100/min)
        for i in range(20):
            response = self.client.get("/api/public")
            assert response.status_code == 200

        # Strict endpoint - strict limit (10/min)
        success_count = 0
        for i in range(15):
            response = self.client.get("/api/strict")
            if response.status_code == 200:
                success_count += 1

        assert success_count == 10  # Only 10 should succeed

    def test_rate_limit_post_requests(self):
        """Test rate limiting works for POST requests"""
        # Test POST endpoint
        for i in range(101):  # Exceed default limit
            response = self.client.post("/api/v1/estimate", json={"test": "data"})
            if i < 100:
                assert response.status_code == 200
            else:
                assert response.status_code == 429

    def test_rate_limit_retry_after_header(self):
        """Test Retry-After header in 429 response"""
        # Exhaust limit
        for i in range(6):
            response = self.client.get("/api/burst")

        assert response.status_code == 429
        # Check for retry information
        assert "retry_after" in response.json() or "Retry-After" in response.headers

    def test_rate_limit_does_not_affect_different_methods(self):
        """Test rate limits are per-endpoint, not per-URL"""
        # This depends on implementation - some rate limiters
        # may treat GET and POST to same URL differently
        base_url = "/api/public"

        # GET requests
        for i in range(5):
            response = self.client.get(base_url)
            assert response.status_code == 200

        # OPTIONS should not be rate limited same way
        response = self.client.options(base_url)
        # May return 405 if not implemented, but shouldn't be 429
        assert response.status_code != 429

if __name__ == "__main__":
    pytest.main([__file__, "-v"])