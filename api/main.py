"""
KIS Estimator API - FastAPI Main Application
Contract-First + Evidence-Gated System
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from api.routers import estimate, validation, documents, catalog, system
from api.services import (
    estimate_service,
    layout_service,
    enclosure_service,
    document_service,
    rag_service
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s'
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

        # Initialize services
        await estimate_service.initialize()
        await layout_service.initialize()
        await enclosure_service.initialize()
        await document_service.initialize()
        await rag_service.initialize()

        self.ready = True
        logger.info("KIS Estimator API started successfully")

    async def shutdown(self):
        """Cleanup application resources"""
        logger.info("Shutting down KIS Estimator API...")

        # Cleanup services
        await estimate_service.cleanup()
        await layout_service.cleanup()
        await enclosure_service.cleanup()
        await document_service.cleanup()
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "X-Evidence-SHA"]
)

# Configure trusted hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
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
async def readiness_check():
    """Readiness check endpoint"""
    if not app_context.ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"}
        )

    return JSONResponse(
        content={
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat()
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

# Include routers
app.include_router(estimate.router, prefix="/v1/estimate", tags=["Estimate"])
app.include_router(validation.router, prefix="/v1/validate", tags=["Validation"])
app.include_router(documents.router, prefix="/v1/documents", tags=["Documents"])
app.include_router(catalog.router, prefix="/v1/catalog", tags=["Catalog"])
app.include_router(system.router, prefix="/system", tags=["System"])

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