"""
KIS Estimator API - FastAPI Main Application
Contract-First + Evidence-Gated System
"""

import hashlib
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.db import init_db, close_db, check_db_health
from api.storage import storage_client
from api.security_config import get_allowed_origins, get_allowed_hosts, EXPOSE_HEADERS
from api.auth import verify_token

# Routers
from api.routers import estimate, validate, documents, catalog, sse, evidence

# Services
from api.services import (
    estimate_service,
    layout_service,
    enclosure_service,
    document_service,
    rag_service,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application metadata
APP_NAME = "KIS Estimator API"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Contract-First Estimator System with Evidence-Gated validation"

class ErrorResponse(BaseModel):
    """Standard error response model"""
    code: str
    message: str
    hint: Optional[str] = None
    traceId: str
    meta: Dict[str, Any]

class AppContext:
    """Application context manager"""
    def __init__(self):
        self.start_time = time.time()
        self.ready = False

    async def startup(self):
        """Initialize application resources"""
        logger.info("Starting KIS Estimator API...")

        # Initialize database connection
        await init_db()

        # Initialize services (check if methods exist)
        if hasattr(estimate_service, 'initialize'):
            await estimate_service.initialize()
        if hasattr(layout_service, 'initialize'):
            await layout_service.initialize()
        if hasattr(enclosure_service, 'initialize'):
            await enclosure_service.initialize()
        if hasattr(document_service, 'initialize'):
            await document_service.initialize()
        if hasattr(rag_service, 'initialize'):
            await rag_service.initialize()

        self.ready = True
        logger.info("KIS Estimator API started successfully")

    async def shutdown(self):
        """Cleanup application resources"""
        logger.info("Shutting down KIS Estimator API...")

        # Close database connections
        await close_db()

        # Cleanup services (check if methods exist)
        if hasattr(estimate_service, 'cleanup'):
            await estimate_service.cleanup()
        if hasattr(layout_service, 'cleanup'):
            await layout_service.cleanup()
        if hasattr(enclosure_service, 'cleanup'):
            await enclosure_service.cleanup()
        if hasattr(document_service, 'cleanup'):
            await document_service.cleanup()
        if hasattr(rag_service, 'cleanup'):
            await rag_service.cleanup()

        self.ready = False
        logger.info("KIS Estimator API shut down successfully")

# Initialize application context
app_context = AppContext()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    await app_context.startup()
    yield
    await app_context.shutdown()

# Create FastAPI application
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS with whitelist
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=EXPOSE_HEADERS
)

# Configure trusted hosts with whitelist
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_allowed_hosts()
)

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri=os.getenv("REDIS_URL", "memory://")
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Rate limit exceeded handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=jsonable_encoder(ErrorResponse(
            code="RATE_LIMIT_EXCEEDED",
            message="Too many requests",
            hint="Please wait before making more requests",
            traceId=getattr(request.state, "trace_id", str(uuid.uuid4())),
            meta={"dedupKey": f"rate_limit_{request.url.path}_{time.time()}"}
        ))
    )

# Middleware for trace ID injection
@app.middleware("http")
async def inject_trace_id(request: Request, call_next):
    """Inject trace ID into all requests and responses"""
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))

    # Add trace ID to logger context
    logger_adapter = logging.LoggerAdapter(logger, {"trace_id": trace_id})
    request.state.logger = logger_adapter
    request.state.trace_id = trace_id

    # Process request
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Add headers to response
    response.headers["X-Trace-Id"] = trace_id
    response.headers["X-Process-Time"] = str(process_time)

    # Log request completion
    logger_adapter.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    return response

# Middleware for idempotency
@app.middleware("http")
async def handle_idempotency(request: Request, call_next):
    """Handle idempotency for write operations"""
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        idempotency_key = request.headers.get("Idempotency-Key")

        if idempotency_key and request.method == "POST":
            # Check for duplicate request (simplified - use Redis in production)
            # This is a placeholder for actual idempotency implementation
            pass

    response = await call_next(request)
    return response

# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(ErrorResponse(
            code="VALIDATION_ERROR",
            message="Invalid request parameters",
            hint=str(exc.errors()[0]["msg"]) if exc.errors() else None,
            traceId=getattr(request.state, "trace_id", str(uuid.uuid4())),
            meta={"dedupKey": f"validation_{request.url.path}_{time.time()}"}
        ))
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(ErrorResponse(
            code=exc.detail.get("code", "HTTP_ERROR") if isinstance(exc.detail, dict) else "HTTP_ERROR",
            message=exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail),
            hint=exc.detail.get("hint") if isinstance(exc.detail, dict) else None,
            traceId=getattr(request.state, "trace_id", str(uuid.uuid4())),
            meta={"dedupKey": f"http_{request.url.path}_{exc.status_code}"}
        ))
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(ErrorResponse(
            code="INTERNAL_ERROR",
            message="An internal error occurred",
            hint="Please contact support with the trace ID",
            traceId=getattr(request.state, "trace_id", str(uuid.uuid4())),
            meta={"dedupKey": f"internal_{request.url.path}_{time.time()}"}
        ))
    )

# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint - must respond < 50ms"""
    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime": time.time() - app_context.start_time
        }
    )

# Readiness check endpoint
@app.get("/readyz")
async def readiness_check(request: Request):
    """
    Readiness check endpoint with DB and Storage validation.
    Requirements:
    - DB: SELECT 1, current UTC timestamp
    - Storage: Upload test file → generate signed URL → cleanup
    - Response: {"status":"ok","db":"ok","storage":"ok","ts":"<UTC-ISO>Z","traceId":"..."}
    """
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))

    if not app_context.ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "message": "Application not ready",
                "traceId": trace_id
            }
        )

    # Check database health
    db_health = await check_db_health()

    # Check storage health
    storage_health = await storage_client.check_storage_health()

    # Check SSE route availability
    sse_status = "ok"
    try:
        from fastapi.routing import APIRoute
        from api.routers import sse as sse_module
        sse_routes = [r for r in sse_module.router.routes if isinstance(r, APIRoute) and r.path.endswith("/test")]
        if not sse_routes:
            sse_status = "missing"
    except Exception:
        sse_status = "missing"

    # Overall status
    all_ok = (
        db_health.get("status") == "ok"
        and storage_health.get("status") == "ok"
    )

    if not all_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "db": db_health.get("status"),
                "storage": storage_health.get("status"),
                "db_error": db_health.get("error"),
                "storage_error": storage_health.get("error"),
                "ts": datetime.now(timezone.utc).isoformat() + "Z",
                "traceId": trace_id,
                "checks": {"sse": sse_status}
            }
        )

    return JSONResponse(
        content={
            "status": "ok",
            "db": "ok",
            "storage": "ok",
            "ts": db_health.get("timestamp", datetime.now(timezone.utc).isoformat() + "Z"),
            "traceId": trace_id,
            "checks": {"sse": sse_status}
        }
    )

# OpenAPI spec endpoint
@app.get("/openapi")
async def get_openapi_spec():
    """Return OpenAPI specification"""
    with open("openapi.yaml", "r") as f:
        return Response(content=f.read(), media_type="application/yaml")

# Evidence generation helper
def generate_evidence_hash(data: Dict[str, Any]) -> str:
    """Generate SHA256 hash for evidence"""
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()

# Include routers with JWT authentication
# All API endpoints require authentication except health/ready/root
app.include_router(
    estimate.router,
    prefix="/v1/estimate",
    tags=["Estimate"],
    dependencies=[Depends(verify_token)]
)
app.include_router(
    validate.router,
    prefix="/v1/validate",
    tags=["Validation"],
    dependencies=[Depends(verify_token)]
)
app.include_router(
    documents.router,
    prefix="/v1/documents",
    tags=["Documents"],
    dependencies=[Depends(verify_token)]
)
app.include_router(
    catalog.router,
    prefix="/v1/catalog",
    tags=["Catalog"],
    dependencies=[Depends(verify_token)]
)

# SSE router (no prefix override - already has /api/sse in router definition)
app.include_router(sse.router)

# Evidence router (admin-only, JWT auth handled by router dependencies)
app.include_router(evidence.router, tags=["Evidence"])

# Parser router (admin-only, JWT auth handled by router dependencies)
from api.routers import parser_routes
app.include_router(parser_routes.router, tags=["Parser"])

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "docs": "/docs",
        "openapi": "/openapi",
        "health": "/healthz",
        "ready": "/readyz"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )