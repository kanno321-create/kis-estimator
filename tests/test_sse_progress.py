"""SSE Progress Tests - Event order, sequence, heartbeat validation"""
import pytest
from httpx import AsyncClient
from api.main import app

pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio
async def test_sse_progress_sequence():
    """Test SSE events have monotonic sequence numbers"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        seqs = []
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-123") as response:
            assert response.status_code == 200
            
            line_count = 0
            async for line in response.aiter_lines():
                if '"seq":' in line:
                    import re
                    match = re.search(r'"seq":\s*(\d+)', line)
                    if match:
                        seqs.append(int(match.group(1)))
                
                line_count += 1
                if line_count > 30:  # Limit test duration
                    break
            
            # Verify sequences are monotonically increasing
            for i in range(1, len(seqs)):
                assert seqs[i] > seqs[i-1], f"Sequence not monotonic: {seqs}"


@pytest.mark.asyncio
async def test_sse_meta_never_none():
    """Test SSE meta field is never None"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-456") as response:
            line_count = 0
            async for line in response.aiter_lines():
                if "data:" in line:
                    # Verify meta is not null
                    assert '"meta":null' not in line.lower()
                    assert '"meta": null' not in line.lower()
                    assert '"meta":None' not in line
                
                line_count += 1
                if line_count > 30:
                    break


@pytest.mark.asyncio
async def test_sse_progress_stages():
    """Test SSE includes all required stages"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        stages = []
        async with client.stream("GET", "/v1/estimate/stream?quoteId=test-789") as response:
            line_count = 0
            async for line in response.aiter_lines():
                if '"stage":' in line:
                    import re
                    match = re.search(r'"stage":\s*"([^"]+)"', line)
                    if match:
                        stages.append(match.group(1))
                
                line_count += 1
                if line_count > 50:
                    break
            
            # Verify key stages are present
            expected_stages = ["input", "enclosure", "layout", "format"]
            for stage in expected_stages:
                assert stage in stages, f"Missing stage: {stage}"
