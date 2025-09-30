#!/bin/bash
# 안전한 튜닝 적용 스크립트

echo "[INFO] 안전한 튜닝 설정 적용 시작..."

# DB 풀 확장 + 커넥션 생존성
export KIS_DB_POOL_MIN=20
export KIS_DB_POOL_MAX=100
export KIS_DB_POOL_MAX_OVERFLOW=50
export KIS_DB_CONN_TIMEOUT_SEC=5
export KIS_DB_CONN_RECYCLE_SEC=300
export KIS_DB_TCP_KEEPALIVE=1

# 서버 워커/소켓/타임아웃
export KIS_SRV_WORKERS=8
export KIS_SRV_KEEPALIVE=75
export KIS_SRV_GRACEFUL_TIMEOUT=30
export KIS_SRV_CLIENT_TIMEOUT=15
export KIS_SRV_BACKLOG=2048

# HTTP 클라이언트 재시도/타임아웃
export KIS_HTTPX_TIMEOUT_CONN=2
export KIS_HTTPX_TIMEOUT_READ=8
export KIS_HTTPX_RETRY_TOTAL=3
export KIS_HTTPX_RETRY_BACKOFF=0.5

# SSE 경로 가드
export KIS_SSE_RESUBSCRIBE_JITTER_MS=250-750
export KIS_SSE_HEARTBEAT_SEC=10

echo "[INFO] 튜닝 설정 완료:"
echo "  - DB 풀: min=$KIS_DB_POOL_MIN, max=$KIS_DB_POOL_MAX, overflow=$KIS_DB_POOL_MAX_OVERFLOW"
echo "  - 서버: workers=$KIS_SRV_WORKERS, keepalive=$KIS_SRV_KEEPALIVE, timeout=$KIS_SRV_CLIENT_TIMEOUT"
echo "  - HTTP: conn_timeout=$KIS_HTTPX_TIMEOUT_CONN, read_timeout=$KIS_HTTPX_TIMEOUT_READ, retry=$KIS_HTTPX_RETRY_TOTAL"