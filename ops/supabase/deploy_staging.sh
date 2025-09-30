#!/usr/bin/env bash
# ============================================================================
# KIS Estimator - Staging Deployment (One-Click)
# Triggered by: main branch push
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log_info "🚀 KIS Estimator - Staging Deployment"

# ============================================================================
# Environment Validation
# ============================================================================

log_info "Validating staging environment..."

REQUIRED_VARS=(
    "STAGING_SUPABASE_URL"
    "STAGING_SUPABASE_ANON_KEY"
    "STAGING_SUPABASE_SERVICE_ROLE_KEY"
    "STAGING_SUPABASE_DB_URL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Missing required environment variable: $var"
        exit 1
    fi
done

log_info "✅ Environment variables validated"

# ============================================================================
# Database Migration (Staging)
# ============================================================================

log_info "Running database migrations (staging)..."

export SUPABASE_URL="$STAGING_SUPABASE_URL"
export SUPABASE_SERVICE_ROLE_KEY="$STAGING_SUPABASE_SERVICE_ROLE_KEY"
export SUPABASE_DB_URL="$STAGING_SUPABASE_DB_URL"

# Apply migrations
psql "$STAGING_SUPABASE_DB_URL" -f db/migrations/20250930_ops_lock.sql || {
    log_error "Migration failed"
    exit 1
}

log_info "✅ Migrations applied"

# ============================================================================
# Apply RLS Policies
# ============================================================================

log_info "Applying RLS policies..."

psql "$STAGING_SUPABASE_DB_URL" -f db/policies.sql || {
    log_error "RLS policies failed"
    exit 1
}

log_info "✅ RLS policies applied"

# ============================================================================
# Apply Database Functions
# ============================================================================

log_info "Applying database functions..."

psql "$STAGING_SUPABASE_DB_URL" -f db/functions.sql || {
    log_error "Functions failed"
    exit 1
}

log_info "✅ Functions applied"

# ============================================================================
# Storage Initialization
# ============================================================================

log_info "Initializing storage..."

bash ops/supabase/storage_init.sh || {
    log_warn "Storage initialization had warnings (may already exist)"
}

log_info "✅ Storage initialized"

# ============================================================================
# Health Check
# ============================================================================

log_info "Running health check..."

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${STAGING_SUPABASE_URL}/rest/v1/rpc/health_check_detailed" \
    -H "apikey: ${STAGING_SUPABASE_ANON_KEY}" \
    -H "Authorization: Bearer ${STAGING_SUPABASE_ANON_KEY}")

HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)

if [[ "$HTTP_CODE" == "200" ]]; then
    log_info "✅ Health check passed"
else
    log_error "Health check failed (HTTP $HTTP_CODE)"
    exit 1
fi

# ============================================================================
# Deployment Summary
# ============================================================================

log_info "✅ Staging deployment complete"
log_info "Environment: STAGING"
log_info "URL: $STAGING_SUPABASE_URL"
log_info "Deployed at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"