#!/usr/bin/env python3
"""
간단한 API 서버 - readyz 엔드포인트 테스트용
"""
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
import os
import psycopg2
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv('.env.local')

app = FastAPI(title="KIS Estimator Simple API", version="1.0.0")

@app.get("/readyz")
async def readyz(
    authorization: str = Header(None),
    x_trace_id: str = Header(None, alias="x-trace-id")
):
    """Health check endpoint"""

    # Database connection test
    db_status = "unknown"
    db_error = None

    try:
        conn_str = os.getenv('SUPABASE_DB_URL')
        if conn_str:
            conn = psycopg2.connect(conn_str)
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            db_status = "connected"
        else:
            db_status = "not configured"
            db_error = "Missing SUPABASE_DB_URL"
    except Exception as e:
        db_status = "error"
        db_error = str(e)[:100]

    response_data = {
        "status": "ready" if db_status == "connected" else "degraded",
        "database": {
            "status": db_status,
            "error": db_error
        },
        "trace_id": x_trace_id or "no-trace",
        "environment": {
            "has_supabase_url": bool(os.getenv('SUPABASE_URL')),
            "has_db_url": bool(os.getenv('SUPABASE_DB_URL')),
            "has_anon_key": bool(os.getenv('SUPABASE_ANON_KEY')),
            "has_service_key": bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        }
    }

    return JSONResponse(
        content=response_data,
        status_code=200 if db_status == "connected" else 503
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "KIS Estimator API",
        "version": "1.0.0",
        "endpoints": [
            "/readyz - Health check",
            "/docs - API documentation"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)