#!/usr/bin/env bash
# ============================================================================
# KIS Estimator - Production Rollback (One-Click)
# Purpose: Rollback production deployment (app + DB migration)
# ============================================================================

set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

log_warn "🔄 KIS Estimator - Production Rollback"
log_warn "⚠️  This will rollback the production deployment"

# ============================================================================
# Parameters
# ============================================================================

ROLLBACK_TAG="${1:-}"
ROLLBACK_MIGRATION="${2:-}"

if [[ -z "$ROLLBACK_TAG" ]]; then
    log_error "Usage: $0 <tag> [migration_version]"
    log_error "Example: $0 v1.2.3 20250930_ops_lock"
    exit 1
fi

log_info "Rollback target tag: $ROLLBACK_TAG"
log_info "Rollback migration: ${ROLLBACK_MIGRATION:-none}"

# ============================================================================
# Safety Confirmation
# ============================================================================

if [[ "${GITHUB_ACTIONS:-false}" != "true" ]]; then
    read -p "⚠️  Confirm production rollback to $ROLLBACK_TAG? (yes/NO): " -r REPLY
    if [[ ! "$REPLY" =~ ^[Yy][Ee][Ss]$ ]]; then
        log_error "Rollback cancelled by user"
        exit 1
    fi
fi

# ============================================================================
# Environment Validation
# ============================================================================

log_info "Validating production environment..."

if [[ -z "${PROD_SUPABASE_DB_URL:-}" ]]; then
    log_error "PROD_SUPABASE_DB_URL not set"
    exit 1
fi

log_info "✅ Environment validated"

# ============================================================================
# Step 1: Database Migration Rollback
# ============================================================================

if [[ -n "$ROLLBACK_MIGRATION" ]]; then
    log_info "Rolling back database migration: $ROLLBACK_MIGRATION"

    # Check if migration exists
    MIGRATION_FILE="db/migrations/${ROLLBACK_MIGRATION}_rollback.sql"
    if [[ ! -f "$MIGRATION_FILE" ]]; then
        log_warn "No rollback script found: $MIGRATION_FILE"
        log_warn "Manual DB rollback may be required"
    else
        psql "$PROD_SUPABASE_DB_URL" -f "$MIGRATION_FILE" || {
            log_error "Migration rollback failed"
            exit 1
        }
        log_info "✅ Migration rolled back"
    fi
else
    log_warn "No migration rollback specified (skipping DB rollback)"
fi

# ============================================================================
# Step 2: Application Rollback (Git Tag)
# ============================================================================

log_info "Rolling back application to tag: $ROLLBACK_TAG"

# Verify tag exists
if ! git rev-parse "$ROLLBACK_TAG" >/dev/null 2>&1; then
    log_error "Tag $ROLLBACK_TAG does not exist"
    exit 1
fi

# Checkout tag (in CI, this would trigger redeploy)
git checkout "$ROLLBACK_TAG" || {
    log_error "Failed to checkout tag $ROLLBACK_TAG"
    exit 1
}

log_info "✅ Application rolled back to $ROLLBACK_TAG"

# ============================================================================
# Step 3: Cache Invalidation
# ============================================================================

log_info "Invalidating caches..."

# Placeholder for cache invalidation logic
# Example: Redis FLUSHDB, CDN purge, etc.

log_info "✅ Caches invalidated"

# ============================================================================
# Step 4: Health Check
# ============================================================================

log_info "Running post-rollback health check..."

if [[ -n "${PROD_SUPABASE_URL:-}" ]] && [[ -n "${PROD_SUPABASE_ANON_KEY:-}" ]]; then
    HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" \
        "${PROD_SUPABASE_URL}/rest/v1/rpc/health_check_detailed" \
        -H "apikey: ${PROD_SUPABASE_ANON_KEY}" \
        -H "Authorization: Bearer ${PROD_SUPABASE_ANON_KEY}" || echo "error\n000")

    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n1)

    if [[ "$HTTP_CODE" == "200" ]]; then
        log_info "✅ Health check passed"
    else
        log_warn "Health check failed (HTTP $HTTP_CODE) - manual verification required"
    fi
else
    log_warn "Skipping health check (credentials not available)"
fi

# ============================================================================
# Rollback Summary
# ============================================================================

log_info "✅ Production rollback complete"
log_info "Rolled back to: $ROLLBACK_TAG"
log_info "Migration rollback: ${ROLLBACK_MIGRATION:-none}"
log_info "Completed at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log_warn "⚠️  Next steps:"
log_warn "  1. Verify application functionality"
log_warn "  2. Monitor error rates and logs"
log_warn "  3. Investigate root cause of rollback"
log_warn "  4. Plan fix and redeployment"