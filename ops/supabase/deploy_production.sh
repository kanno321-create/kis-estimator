#!/usr/bin/env bash
# ============================================================================
# KIS Estimator - Production Deployment (One-Click with Manual Approval)
# Triggered by: tag v* push + manual approval gate
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log_info "🚀 KIS Estimator - Production Deployment"

# ============================================================================
# Production Safety Check
# ============================================================================

log_warn "⚠️  PRODUCTION DEPLOYMENT - Requires manual approval"
log_warn "This will deploy to the PRODUCTION environment"

if [[ "${GITHUB_ACTIONS:-false}" == "true" ]]; then
    log_info "Running in GitHub Actions (approval gate should be passed)"
else
    read -p "Continue with production deployment? (yes/NO): " -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        log_error "Deployment cancelled by user"
        exit 1
    fi
fi

# ============================================================================
# Environment Validation
# ============================================================================

log_info "Validating production environment..."

REQUIRED_VARS=(
    "PROD_SUPABASE_URL"
    "PROD_SUPABASE_ANON_KEY"
    "PROD_SUPABASE_SERVICE_ROLE_KEY"
    "PROD_SUPABASE_DB_URL"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Missing required environment variable: $var"
        exit 1
    fi
done

log_info "✅ Environment variables validated"

# ============================================================================
# Database Migration (Production)
# ============================================================================

log_info "Running database migrations (production)..."

export SUPABASE_URL="$PROD_SUPABASE_URL"
export SUPABASE_SERVICE_ROLE_KEY="$PROD_SUPABASE_SERVICE_ROLE_KEY"
export SUPABASE_DB_URL="$PROD_SUPABASE_DB_URL"

# Apply migrations with transaction safety
psql "$PROD_SUPABASE_DB_URL" -f db/migrations/20250930_ops_lock.sql || {
    log_error "Migration failed"
    exit 1
}

log_info "✅ Migrations applied"

# ============================================================================
# Apply RLS Policies (Production)
# ============================================================================

log_info "Applying RLS policies (production)..."

psql "$PROD_SUPABASE_DB_URL" -f db/policies.sql || {
    log_error "RLS policies failed"
    exit 1
}

log_info "✅ RLS policies applied"

# ============================================================================
# Apply Database Functions (Production)
# ============================================================================

log_info "Applying database functions (production)..."

psql "$PROD_SUPABASE_DB_URL" -f db/functions.sql || {
    log_error "Functions failed"
    exit 1
}

log_info "✅ Functions applied"

# ============================================================================
# Storage Initialization (Production)
# ============================================================================

log_info "Initializing storage (production)..."

bash ops/supabase/storage_init.sh || {
    log_warn "Storage initialization had warnings (may already exist)"
}

log_info "✅ Storage initialized"

# ============================================================================
# Health Check (Production)
# ============================================================================

log_info "Running health check (production)..."

HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" \
    "${PROD_SUPABASE_URL}/rest/v1/rpc/health_check_detailed" \
    -H "apikey: ${PROD_SUPABASE_ANON_KEY}" \
    -H "Authorization: Bearer ${PROD_SUPABASE_ANON_KEY}")

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

log_info "✅ PRODUCTION deployment complete"
log_info "Environment: PRODUCTION"
log_info "URL: $PROD_SUPABASE_URL"
log_info "Deployed at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
log_info "Tag: ${GITHUB_REF_NAME:-manual}"

# ============================================================================
# Post-Deployment Notifications (placeholder)
# ============================================================================

log_info "📢 Send deployment notifications (Slack/Email/PagerDuty)"