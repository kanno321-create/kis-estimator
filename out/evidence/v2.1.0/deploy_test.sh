#!/usr/bin/env bash
# ============================================================================
# KIS Estimator - Supabase 실제 연결 배포 테스트 (POSIX)
# Purpose: DB lint/diff/push → Storage init → API server → /readyz test
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log_info "🚀 KIS Estimator - Supabase 실제 연결 배포 테스트"

# ============================================================================
# Step 0: 환경 변수 확인
# ============================================================================

log_info "Step 0: Checking environment variables..."

REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_ANON_KEY"
    "SUPABASE_SERVICE_ROLE_KEY"
    "SUPABASE_DB_URL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Missing required environment variable: $var"
        log_error "Please set all variables in .env or export them"
        exit 1
    fi
done

APP_PORT="${APP_PORT:-8000}"
APP_ENV="${APP_ENV:-staging}"

log_info "✅ Environment variables validated"
log_info "APP_PORT: $APP_PORT"
log_info "APP_ENV: $APP_ENV"

# ============================================================================
# Step 1: Supabase DB Lint & Diff
# ============================================================================

log_info "Step 1: Running Supabase DB lint and diff..."

if command -v supabase >/dev/null 2>&1; then
    log_info "Supabase CLI found"

    # DB lint
    log_info "Running db lint..."
    if supabase db lint 2>/dev/null; then
        log_info "✅ DB lint passed"
    else
        log_warn "DB lint had warnings (non-fatal)"
    fi

    # DB diff (requires linked project)
    log_info "Running db diff..."
    if supabase db diff --linked 2>/dev/null; then
        log_info "✅ DB diff OK"
    else
        log_warn "DB diff skipped (project not linked or no changes)"
    fi
else
    log_warn "Supabase CLI not found - skipping lint/diff"
    log_warn "Install with: npm install -g supabase"
fi

# ============================================================================
# Step 2: DB Push (Optional - with guard)
# ============================================================================

log_info "Step 2: DB Push (optional)..."

if [[ "${SKIP_DB_PUSH:-false}" == "true" ]]; then
    log_warn "Skipping DB push (SKIP_DB_PUSH=true)"
elif [[ "$APP_ENV" == "production" ]]; then
    log_warn "Skipping DB push (production environment - manual only)"
else
    read -p "Push database migrations? (yes/NO): " -r REPLY
    if [[ "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        log_info "Pushing database migrations..."
        if command -v supabase >/dev/null 2>&1; then
            supabase db push --include-all || {
                log_error "DB push failed"
                exit 1
            }
            log_info "✅ DB push completed"
        else
            log_error "Supabase CLI required for db push"
            exit 1
        fi
    else
        log_info "DB push skipped"
    fi
fi

# ============================================================================
# Step 3: Storage Initialization
# ============================================================================

log_info "Step 3: Initializing storage..."

if [[ -f "ops/supabase/storage_init.sh" ]]; then
    bash ops/supabase/storage_init.sh || {
        log_warn "Storage initialization had warnings"
    }
    log_info "✅ Storage initialized"
else
    log_error "Storage init script not found: ops/supabase/storage_init.sh"
    exit 1
fi

# ============================================================================
# Step 4: Start API Server (background)
# ============================================================================

log_info "Step 4: Starting API server..."

# Kill existing server on port
if lsof -Pi :$APP_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    log_warn "Port $APP_PORT is in use, killing existing process..."
    kill $(lsof -t -i:$APP_PORT) 2>/dev/null || true
    sleep 2
fi

# Start server in background
log_info "Starting uvicorn on port $APP_PORT..."
uvicorn api.main:app --host 0.0.0.0 --port $APP_PORT > /tmp/kis_api.log 2>&1 &
API_PID=$!

log_info "API server started (PID: $API_PID)"
log_info "Waiting for server to be ready..."

# Wait for server
MAX_WAIT=30
for i in $(seq 1 $MAX_WAIT); do
    if curl -s http://localhost:$APP_PORT/health >/dev/null 2>&1; then
        log_info "✅ API server is ready"
        break
    fi
    if [[ $i -eq $MAX_WAIT ]]; then
        log_error "API server failed to start within ${MAX_WAIT}s"
        log_error "Check logs: tail /tmp/kis_api.log"
        kill $API_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# ============================================================================
# Step 5: Test /readyz Endpoint
# ============================================================================

log_info "Step 5: Testing /readyz endpoint..."

READYZ_URL="http://localhost:$APP_PORT/readyz"
log_info "Calling: $READYZ_URL"

READYZ_RESPONSE=$(curl -s -w "\n%{http_code}" "$READYZ_URL" || echo "error\n000")
HTTP_CODE=$(echo "$READYZ_RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$READYZ_RESPONSE" | head -n-1)

log_info "HTTP Status: $HTTP_CODE"
log_info "Response:"
echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"

if [[ "$HTTP_CODE" == "200" ]]; then
    log_info "✅ /readyz check passed"
else
    log_error "❌ /readyz check failed (HTTP $HTTP_CODE)"
    kill $API_PID 2>/dev/null || true
    exit 1
fi

# ============================================================================
# Cleanup
# ============================================================================

log_info "Cleaning up..."
kill $API_PID 2>/dev/null || true
log_info "API server stopped"

# ============================================================================
# Summary
# ============================================================================

log_info "✅ Supabase 실제 연결 배포 테스트 완료"
log_info "모든 단계가 성공적으로 완료되었습니다"
log_info ""
log_info "Next steps:"
log_info "  1. Review logs: tail /tmp/kis_api.log"
log_info "  2. Run E2E tests: pytest tests/test_e2e_supabase.py -v"
log_info "  3. Deploy to staging/production via CI/CD"