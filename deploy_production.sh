#!/bin/bash
# KIS Estimator Production Deployment Script
# Updated to use port 8001 (port 8000 occupied)
set -euo pipefail

echo "[INFO] Starting KIS Estimator Production Deployment at $(date -Is)"

# Load production environment
if [ -f ".env.production" ]; then
    echo "[INFO] Loading production environment variables"
    source .env.production
else
    echo "[ERROR] .env.production not found"
    exit 1
fi

# Export BASE_URL for use by other scripts
export BASE_URL="${BASE_URL:-http://localhost:8001}"
export SERVICE_URL="${SERVICE_URL:-http://localhost:8001}"

echo "[INFO] BASE_URL=$BASE_URL"
echo "[INFO] SERVICE_URL=$SERVICE_URL"
echo "[INFO] APP_PORT=$APP_PORT"

# Verify server is running on correct port
echo "[INFO] Verifying server on port $APP_PORT..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    # Use /healthz endpoint (not /health)
    if curl -s -f "http://localhost:$APP_PORT/healthz" >/dev/null 2>&1; then
        echo "[INFO] Server is responding on port $APP_PORT"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "[WARN] Server not responding (attempt $RETRY_COUNT/$MAX_RETRIES), waiting..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "[ERROR] Server is not responding after $MAX_RETRIES attempts"
    exit 1
fi

echo "[INFO] Deployment completed successfully"
echo "[INFO] Production URL: $BASE_URL"
exit 0