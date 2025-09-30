#!/bin/bash
# ==============================================================================
# KIS Estimator - Production Deployment Script (v2.1.0)
# ==============================================================================
#
# USAGE:
#   1. Set environment variables (see below)
#   2. bash DEPLOYMENT_SCRIPT.sh
#
# ROLLBACK:
#   bash DEPLOYMENT_SCRIPT.sh --rollback
#
# ==============================================================================

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

log_success() {
    echo -e "${GREEN}✅ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  ${NC}$1"
}

log_error() {
    echo -e "${RED}❌ ${NC}$1"
}

# ==============================================================================
# Step 0: Pre-flight Checks
# ==============================================================================

log_info "Step 0: Pre-flight Checks"

# Check if rollback mode
ROLLBACK_MODE=false
if [[ "${1:-}" == "--rollback" ]]; then
    ROLLBACK_MODE=true
    log_warning "ROLLBACK MODE ENABLED"
fi

# Required environment variables
REQUIRED_VARS=(
    "APP_ENV"
    "SUPABASE_URL"
    "SUPABASE_SERVICE_ROLE_KEY"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        log_error "Environment variable $var is not set"
        exit 1
    fi
done

# Security check (don't print actual keys)
if [[ ${#SUPABASE_SERVICE_ROLE_KEY} -lt 20 ]]; then
    log_error "SUPABASE_SERVICE_ROLE_KEY seems invalid (too short)"
    exit 1
fi

log_success "Environment variables validated"

# ==============================================================================
# Step 1: Create Deployment Logs Directory
# ==============================================================================

log_info "Step 1: Creating deployment logs directory"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEPLOY_DIR="out/prod_deploy/${TIMESTAMP}"
mkdir -p "${DEPLOY_DIR}"
echo "${TIMESTAMP}" > "${DEPLOY_DIR}/TIMESTAMP.txt"

log_success "Deployment directory created: ${DEPLOY_DIR}"

# ==============================================================================
# Step 2: Supabase Login and Link
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_info "Step 2: Supabase Login and Project Link"

    # Note: Supabase CLI login requires interactive authentication
    # For CI/CD, use SUPABASE_ACCESS_TOKEN instead
    if [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
        log_info "Using SUPABASE_ACCESS_TOKEN for authentication"
    else
        log_warning "SUPABASE_ACCESS_TOKEN not set, attempting interactive login"
        supabase login 2>&1 | tee "${DEPLOY_DIR}/supabase_login.log" || true
    fi

    # Link to production project
    if [[ -n "${SUPABASE_PROJECT_REF:-}" ]]; then
        log_info "Linking to project: ${SUPABASE_PROJECT_REF}"
        supabase link --project-ref "${SUPABASE_PROJECT_REF}" 2>&1 | tee "${DEPLOY_DIR}/supabase_link.log"
        log_success "Project linked successfully"
    else
        log_warning "SUPABASE_PROJECT_REF not set, skipping project link"
    fi
fi

# ==============================================================================
# Step 3: Database Schema Validation (Dry-Run)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_info "Step 3: Database Schema Validation (Dry-Run)"

    # DB Lint
    log_info "Running database lint..."
    supabase db lint 2>&1 | tee "${DEPLOY_DIR}/db_lint.log" || {
        log_warning "DB lint warnings detected (non-fatal)"
    }

    # DB Diff (show what will change)
    log_info "Running database diff..."
    supabase db diff 2>&1 | tee "${DEPLOY_DIR}/db_diff.log" || {
        log_warning "DB diff check completed with warnings"
    }

    log_success "Database validation completed"
fi

# ==============================================================================
# Step 4: Database Migration Push
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_info "Step 4: Pushing Database Migrations"

    # Confirmation prompt for production
    if [[ "${APP_ENV}" == "production" ]]; then
        echo ""
        log_warning "⚠️  PRODUCTION DATABASE MIGRATION ⚠️"
        echo ""
        read -p "Are you sure you want to push migrations to PRODUCTION? (yes/NO): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_error "Deployment cancelled by user"
            exit 1
        fi
    fi

    # Push migrations
    log_info "Pushing database migrations..."
    supabase db push 2>&1 | tee "${DEPLOY_DIR}/db_push.log"
    log_success "Database migrations pushed successfully"
fi

# ==============================================================================
# Step 5: Storage Bucket Initialization
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_info "Step 5: Initializing Storage Buckets"

    # Run storage initialization script
    if [[ -f "ops/supabase/storage_init.sh" ]]; then
        log_info "Running storage_init.sh..."
        bash ops/supabase/storage_init.sh 2>&1 | tee "${DEPLOY_DIR}/storage_init.log" || {
            log_warning "Storage initialization completed with warnings"
        }
        log_success "Storage buckets initialized"
    else
        log_warning "storage_init.sh not found, skipping"
    fi
fi

# ==============================================================================
# Step 6: Application Deployment
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_info "Step 6: Deploying Application"

    # Run production deployment script
    if [[ -f "ops/supabase/deploy_production.sh" ]]; then
        log_info "Running deploy_production.sh..."
        bash ops/supabase/deploy_production.sh 2>&1 | tee "${DEPLOY_DIR}/app_deploy.log"
        log_success "Application deployed successfully"
    else
        log_warning "deploy_production.sh not found, skipping"
    fi
fi

# ==============================================================================
# Step 7: Post-Deployment Validation
# ==============================================================================

log_info "Step 7: Post-Deployment Validation"

# Wait for application to be ready
log_info "Waiting for application to be ready (30s)..."
sleep 30

# Health check
log_info "Checking /healthz endpoint..."
HEALTHZ_RESPONSE=$(curl -s -w "\n%{http_code}" "${SUPABASE_URL}/healthz" || echo "000")
HEALTHZ_CODE=$(echo "$HEALTHZ_RESPONSE" | tail -n1)

if [[ "$HEALTHZ_CODE" == "200" ]]; then
    log_success "/healthz check passed (200 OK)"
    echo "$HEALTHZ_RESPONSE" | head -n-1 > "${DEPLOY_DIR}/healthz_response.json"
else
    log_error "/healthz check failed (HTTP $HEALTHZ_CODE)"
    echo "$HEALTHZ_RESPONSE" > "${DEPLOY_DIR}/healthz_error.log"
fi

# Readiness check
log_info "Checking /readyz endpoint..."
READYZ_RESPONSE=$(curl -s -w "\n%{http_code}" "${SUPABASE_URL}/readyz" || echo "000")
READYZ_CODE=$(echo "$READYZ_RESPONSE" | tail -n1)

if [[ "$READYZ_CODE" == "200" ]]; then
    log_success "/readyz check passed (200 OK)"
    echo "$READYZ_RESPONSE" | head -n-1 > "${DEPLOY_DIR}/readyz_response.json"

    # Validate response format
    READYZ_JSON=$(echo "$READYZ_RESPONSE" | head -n-1)
    if echo "$READYZ_JSON" | grep -q '"status":"ok"'; then
        log_success "Status: ok"
    fi
    if echo "$READYZ_JSON" | grep -q '"db":"ok"'; then
        log_success "DB: ok"
    fi
    if echo "$READYZ_JSON" | grep -q '"storage":"ok"'; then
        log_success "Storage: ok"
    fi
    if echo "$READYZ_JSON" | grep -q '"traceId"'; then
        log_success "TraceId: present"
    fi
else
    log_error "/readyz check failed (HTTP $READYZ_CODE)"
    echo "$READYZ_RESPONSE" > "${DEPLOY_DIR}/readyz_error.log"
fi

# ==============================================================================
# Step 8: Rollback (if requested)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "true" ]]; then
    log_warning "Step 8: ROLLBACK MODE"

    # Application rollback
    if [[ -f "ops/rollback/production_rollback.sh" ]]; then
        log_info "Running production_rollback.sh..."
        bash ops/rollback/production_rollback.sh 2>&1 | tee "${DEPLOY_DIR}/rollback.log"
        log_success "Rollback completed"
    else
        log_error "production_rollback.sh not found"
        exit 1
    fi

    # Verify rollback
    log_info "Verifying rollback..."
    sleep 10
    curl -s "${SUPABASE_URL}/readyz" | tee "${DEPLOY_DIR}/rollback_readyz.json"
fi

# ==============================================================================
# Step 9: Deployment Summary
# ==============================================================================

log_info "Step 9: Deployment Summary"

echo ""
echo "=========================================="
echo "  KIS Estimator Deployment Summary"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo "Environment: ${APP_ENV}"
echo "Mode: $([ "$ROLLBACK_MODE" == "true" ] && echo "ROLLBACK" || echo "DEPLOY")"
echo "Logs: ${DEPLOY_DIR}"
echo "=========================================="
echo ""

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    if [[ "$HEALTHZ_CODE" == "200" && "$READYZ_CODE" == "200" ]]; then
        log_success "🎉 DEPLOYMENT SUCCESSFUL!"
        echo ""
        echo "Next steps:"
        echo "  1. Monitor application logs"
        echo "  2. Check error rates and performance"
        echo "  3. Verify E2E tests: pytest tests/test_e2e_supabase.py -v"
        echo "  4. Keep rollback ready for 24 hours"
        echo ""
        exit 0
    else
        log_error "⚠️  DEPLOYMENT COMPLETED WITH WARNINGS"
        echo ""
        echo "Health checks failed. Please investigate:"
        echo "  - Check logs in: ${DEPLOY_DIR}"
        echo "  - Consider rollback: bash DEPLOYMENT_SCRIPT.sh --rollback"
        echo ""
        exit 1
    fi
else
    log_success "🔄 ROLLBACK COMPLETED"
    echo ""
    echo "Next steps:"
    echo "  1. Verify application is working with old version"
    echo "  2. Investigate deployment failure"
    echo "  3. Fix issues and retry deployment"
    echo ""
    exit 0
fi