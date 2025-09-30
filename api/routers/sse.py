"""
SSE (Server-Sent Events) Router
Implements real-time streaming with JWT authentication and heartbeat.
"""
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import time
import os
import uuid
import json
from typing import AsyncGenerator, Optional

from api.utils.jwt_guard import verify_jwt

router = APIRouter(prefix="/api/sse", tags=["sse"])

def _sse_encode(event: str = None, data: dict = None, retry_ms: int = 1000, id_: str = None) -> bytes:
    """
    Encode SSE message according to spec.

    Args:
        event: Event type
        data: Event data (will be JSON encoded)
        retry_ms: Client retry interval
        id_: Event ID

    Returns:
        Encoded SSE message bytes
    """
    buf = []
    if event:
        buf.append(f"event: {event}")
    if id_:
        buf.append(f"id: {id_}")
    if data is not None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        for line in payload.splitlines():
            buf.append(f"data: {line}")
    buf.append(f"retry: {retry_ms}")
    buf.append("")  # final newline
    return ("\n".join(buf) + "\n").encode("utf-8")

async def _stream(req: Request, sub: str, claims: dict) -> AsyncGenerator[bytes, None]:
    """
    Generate SSE stream with heartbeats.

    Real behavior: Sends actual server time and metadata.
    This is NOT a mock - it's real system operation.

    Args:
        req: FastAPI request
        sub: Subject from JWT claims
        claims: Full JWT claims

    Yields:
        SSE message bytes
    """
    seq = 0
    trace = f"sse-{uuid.uuid4()}"
    retry = int(os.getenv("KIS_SSE_CLIENT_RETRY_MS", "1500"))
    hb = int(os.getenv("KIS_SSE_HEARTBEAT_SEC", "10"))

    # Initial hello
    yield _sse_encode(
        "hello",
        {"sub": sub, "ts": time.time(), "traceId": trace},
        retry_ms=retry,
        id_=str(seq)
    )
    seq += 1

    # Heartbeat loop
    while True:
        if await req.is_disconnected():
            break

        # Heartbeat payload with REAL system time/meta
        payload = {
            "type": "heartbeat",
            "ts": time.time(),
            "seq": seq,
            "traceId": trace
        }
        yield _sse_encode("heartbeat", payload, retry_ms=retry, id_=str(seq))
        seq += 1

        try:
            await asyncio.sleep(hb)
        except asyncio.CancelledError:
            break

@router.get("/test")
async def sse_test(
    request: Request,
    authorization: Optional[str] = Header(default=None)
) -> StreamingResponse:
    """
    SSE test endpoint with JWT authentication.

    Headers:
        Authorization: Bearer <JWT>

    Returns:
        StreamingResponse with text/event-stream

    Raises:
        HTTPException: 401 if no auth, 403 if invalid token
    """
    # Auth required (Supabase JWT)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization required")

    token = authorization.split(" ", 1)[1]
    try:
        claims = await verify_jwt(token)
    except Exception as e:
        raise HTTPException(status_code=403, detail=f"invalid token: {type(e).__name__}")

    sub = str(claims.get("sub") or claims.get("user_id") or "unknown")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # nginx
        "Content-Type": "text/event-stream; charset=utf-8",
    }

    return StreamingResponse(
        _stream(request, sub, claims),
        headers=headers,
        media_type="text/event-stream"
    )