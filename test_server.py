#!/usr/bin/env python3
"""Simple test server for KIS Estimator"""
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="KIS Estimator Test Server")

@app.get("/healthz")
async def health():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "service": "kis-estimator-test",
        "version": "2.1.0"
    })

@app.get("/readyz")
async def readiness():
    """Readiness check endpoint"""
    # Check if environment variables are set
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY", "DATABASE_URL"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "missing_env_vars": missing
            }
        )

    return JSONResponse({
        "status": "ok",
        "database": "ok",
        "environment_vars": "configured"
    })

@app.get("/api/catalog")
async def catalog():
    """Catalog endpoint for testing"""
    return JSONResponse({
        "items": [
            {"id": 1, "name": "MCCB 800A", "price": 450000},
            {"id": 2, "name": "MCCB 400A", "price": 280000}
        ],
        "total": 2
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)