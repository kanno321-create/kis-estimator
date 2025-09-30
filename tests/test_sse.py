"""SSE Tests - Server-Sent Events validation"""
import pytest
from httpx import AsyncClient
from api.main import app

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_sse_heartbeat():
    """Test SSE stream includes HEARTBEAT events"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-uuid") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            events = []
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                    events.append(event_type)
                    if event_type == "DONE":
                        break
            
            assert "HEARTBEAT" in events, "SSE stream must include HEARTBEAT"

@pytest.mark.asyncio
async def test_sse_meta_seq_monotonic():
    """Test SSE meta.seq is monotonically increasing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-uuid") as response:
            seqs = []
            async for line in response.aiter_lines():
                if '"seq":' in line:
                    # Extract seq value (simple parse)
                    import re
                    match = re.search(r'"seq":(\d+)', line)
                    if match:
                        seqs.append(int(match.group(1)))
                if line.startswith("event: DONE"):
                    break
            
            # Verify monotonic increase
            for i in range(1, len(seqs)):
                assert seqs[i] > seqs[i-1], f"Seq not monotonic: {seqs}"

@pytest.mark.asyncio
async def test_sse_meta_not_none():
    """Test SSE meta field is never None"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-uuid") as response:
            async for line in response.aiter_lines():
                if "data:" in line:
                    # Verify 'meta' is not null/None
                    assert '"meta":null' not in line.lower(), "meta must not be None"
                    assert '"meta": null' not in line.lower(), "meta must not be None"
                if line.startswith("event: DONE"):
                    break
