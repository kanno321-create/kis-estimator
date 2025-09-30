#!/bin/bash
# ==============================================================================
# KIS Estimator - Final Production Deployment Script
# Version: 2.1.0-estimator
# Date: 2025-09-30
# ==============================================================================
#
# USAGE:
#   1. Configure environment variables (see CONFIGURATION section)
#   2. bash PRODUCTION_DEPLOY_FINAL.sh
#
# ROLLBACK:
#   bash PRODUCTION_DEPLOY_FINAL.sh --rollback
#
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Color Codes
# ==============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
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

log_step() {
    echo ""
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Check if rollback mode
ROLLBACK_MODE=false
if [[ "${1:-}" == "--rollback" ]]; then
    ROLLBACK_MODE=true
    log_warning "🔄 ROLLBACK MODE ENABLED"
fi

log_step "Step 0: Environment Setup & Validation"

# ===== Environment Variables =====
export APP_ENV="${APP_ENV:-production}"
export SUPABASE_URL="${SUPABASE_URL:-}"
export SUPABASE_SERVICE_ROLE_KEY="${SUPABASE_SERVICE_ROLE_KEY:-}"
export DATABASE_URL="${DATABASE_URL:-}"
export EVIDENCE_BUCKET="${EVIDENCE_BUCKET:-evidence}"
export SIGNED_URL_TTL_SEC="${SIGNED_URL_TTL_SEC:-600}"

# Required variables check
REQUIRED_VARS=(
    "SUPABASE_URL"
    "SUPABASE_SERVICE_ROLE_KEY"
    "DATABASE_URL"
)

log_info "Validating environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var}" ]]; then
        log_error "Environment variable $var is not set"
        echo ""
        echo "Please set the following environment variables:"
        echo "  export APP_ENV=production"
        echo "  export SUPABASE_URL=\"https://<prod-project-ref>.supabase.co\""
        echo "  export SUPABASE_SERVICE_ROLE_KEY=\"<prod-service-role-key>\""
        echo "  export DATABASE_URL=\"postgresql://postgres:<DB_PASSWORD>@db.<prod-project-ref>.supabase.co:5432/postgres\""
        echo "  export EVIDENCE_BUCKET=\"evidence\""
        echo "  export SIGNED_URL_TTL_SEC=600"
        echo ""
        exit 1
    fi
done

# Security validation
if [[ ${#SUPABASE_SERVICE_ROLE_KEY} -lt 20 ]]; then
    log_error "SUPABASE_SERVICE_ROLE_KEY seems invalid (too short)"
    exit 1
fi

log_success "Environment variables validated"

# Display configuration (masked)
log_info "Configuration:"
echo "  APP_ENV: ${APP_ENV}"
echo "  SUPABASE_URL: ${SUPABASE_URL}"
echo "  DATABASE_URL: ${DATABASE_URL%%@*}@***"  # Mask password
echo "  EVIDENCE_BUCKET: ${EVIDENCE_BUCKET}"
echo "  SIGNED_URL_TTL_SEC: ${SIGNED_URL_TTL_SEC}"
echo "  SERVICE_ROLE_KEY: ${SUPABASE_SERVICE_ROLE_KEY:0:20}***"  # Mask key

# ==============================================================================
# Step 1: Create Deployment Logs Directory
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 1: Creating Deployment Logs Directory"

    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DEPLOY_DIR="out/prod_deploy/${TIMESTAMP}"
    mkdir -p "${DEPLOY_DIR}"
    echo "${TIMESTAMP}" > "${DEPLOY_DIR}/TIMESTAMP.txt"

    log_success "Deployment directory created: ${DEPLOY_DIR}"

    # Save environment configuration (without sensitive data)
    cat > "${DEPLOY_DIR}/deployment_config.txt" <<EOF
Deployment Configuration
========================
Timestamp: ${TIMESTAMP}
Environment: ${APP_ENV}
Supabase URL: ${SUPABASE_URL}
Evidence Bucket: ${EVIDENCE_BUCKET}
Signed URL TTL: ${SIGNED_URL_TTL_SEC}s
EOF

    log_success "Configuration saved to ${DEPLOY_DIR}/deployment_config.txt"
fi

# ==============================================================================
# Step 2: Supabase Login and Link
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 2: Supabase Login and Project Link"

    # Extract project ref from SUPABASE_URL
    SUPABASE_PROJECT_REF=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co|\1|')

    if [[ -z "$SUPABASE_PROJECT_REF" ]]; then
        log_error "Could not extract project ref from SUPABASE_URL"
        exit 1
    fi

    log_info "Project ref: ${SUPABASE_PROJECT_REF}"

    # Login (if SUPABASE_ACCESS_TOKEN is set, use it)
    if [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]]; then
        log_info "Using SUPABASE_ACCESS_TOKEN for authentication"
    else
        log_warning "SUPABASE_ACCESS_TOKEN not set, attempting interactive login"
        supabase login 2>&1 | tee "${DEPLOY_DIR}/supabase_login.log" || {
            log_warning "Login may have failed, continuing..."
        }
    fi

    # Link to project
    log_info "Linking to project: ${SUPABASE_PROJECT_REF}"
    supabase link --project-ref "${SUPABASE_PROJECT_REF}" 2>&1 | tee "${DEPLOY_DIR}/supabase_link.log"
    log_success "Project linked successfully"
fi

# ==============================================================================
# Step 3: Database Schema Validation (Dry-Run)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 3: Database Schema Validation (Dry-Run)"

    # DB Lint
    log_info "Running database lint..."
    supabase db lint 2>&1 | tee "${DEPLOY_DIR}/db_lint.log" || {
        log_warning "DB lint warnings detected (non-fatal)"
    }

    # DB Diff
    log_info "Running database diff..."
    supabase db diff 2>&1 | tee "${DEPLOY_DIR}/db_diff.log" || {
        log_warning "DB diff completed with warnings"
    }

    log_success "Database validation completed"

    # Display lint/diff summary
    log_info "Lint/Diff Summary:"
    echo "  Logs: ${DEPLOY_DIR}/db_lint.log"
    echo "  Logs: ${DEPLOY_DIR}/db_diff.log"
fi

# ==============================================================================
# Step 4: Database Schema Push
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 4: Pushing Database Schema"

    # Production confirmation
    if [[ "${APP_ENV}" == "production" ]]; then
        echo ""
        log_warning "⚠️  PRODUCTION DATABASE MIGRATION ⚠️"
        log_warning "This will apply migrations to PRODUCTION database"
        echo ""
        echo "Files to be applied:"
        echo "  - db/schema.sql"
        echo "  - db/policies.sql"
        echo "  - db/functions.sql"
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
    log_step "Step 5: Initializing Storage Buckets"

    # Create evidence bucket (idempotent)
    log_info "Creating evidence bucket (idempotent)..."
    supabase storage create-bucket "${EVIDENCE_BUCKET}" --public=false 2>&1 | tee "${DEPLOY_DIR}/storage_create.log" || {
        log_info "Bucket may already exist (continuing...)"
    }

    # Run storage initialization script if exists
    if [[ -f "ops/supabase/storage_init.sh" ]]; then
        log_info "Running storage_init.sh..."
        bash ops/supabase/storage_init.sh 2>&1 | tee "${DEPLOY_DIR}/storage_init.log" || {
            log_warning "Storage initialization completed with warnings"
        }
        log_success "Storage initialization script executed"
    else
        log_warning "storage_init.sh not found, skipping"
    fi

    log_success "Storage buckets initialized"
fi

# ==============================================================================
# Step 6: Catalog Seed (Optional)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 6: Catalog Seed (Optional)"

    # Check for catalog CSV
    if [[ -f "seed/catalog_items.csv" ]]; then
        log_info "Found catalog CSV, seeding data..."

        psql "$DATABASE_URL" -c "\copy shared.catalog_items(sku,name,category,unit,price) FROM 'seed/catalog_items.csv' CSV HEADER" \
            2>&1 | tee "${DEPLOY_DIR}/catalog_seed.log" || {
            log_warning "Catalog seed may have failed or data already exists"
        }

        log_success "Catalog seed completed"
    elif [[ -f "seed/catalog_items.json" ]]; then
        log_info "Found catalog JSON (manual import required)"
        log_warning "JSON import requires custom function, skipping for now"
    else
        log_info "No catalog seed files found, skipping"
    fi
fi

# ==============================================================================
# Step 7: E2E Integrity Tests (Recommended)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 7: E2E Integrity Tests (Recommended)"

    if command -v pytest &> /dev/null; then
        log_info "Running E2E Supabase tests..."

        # Set environment for tests
        export SUPABASE_ANON_KEY="${SUPABASE_ANON_KEY:-}"
        export SUPABASE_DB_URL="${DATABASE_URL}"

        pytest -q tests/test_e2e_supabase.py 2>&1 | tee "${DEPLOY_DIR}/test_e2e_supabase.log" || {
            log_error "E2E tests failed!"
            log_warning "Consider rolling back the deployment"

            read -p "Continue despite test failures? (yes/NO): " continue_confirm
            if [[ "$continue_confirm" != "yes" ]]; then
                log_error "Deployment aborted by user"
                exit 1
            fi
        }

        log_success "E2E tests completed"
    else
        log_warning "pytest not found, skipping E2E tests"
    fi
fi

# ==============================================================================
# Step 8: Application Deployment
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 8: Application Deployment"

    # Run production deployment script if exists
    if [[ -f "ops/supabase/deploy_production.sh" ]]; then
        log_info "Running deploy_production.sh..."
        bash ops/supabase/deploy_production.sh 2>&1 | tee "${DEPLOY_DIR}/app_deploy.log" || {
            log_error "Application deployment failed!"

            read -p "Continue to validation anyway? (yes/NO): " continue_confirm
            if [[ "$continue_confirm" != "yes" ]]; then
                log_error "Deployment aborted"
                exit 1
            fi
        }
        log_success "Application deployment completed"
    else
        log_warning "deploy_production.sh not found"
        log_info "Manual application deployment may be required"
    fi
fi

# ==============================================================================
# Step 9: Post-Deployment Validation
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    log_step "Step 9: Post-Deployment Validation"

    # Wait for application to be ready
    log_info "Waiting for application to be ready (30 seconds)..."
    sleep 30

    # Construct API URL
    API_URL="${SUPABASE_URL}"

    # Health check
    log_info "Checking /healthz endpoint..."
    HEALTHZ_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/healthz" 2>&1 || echo "ERROR\n000")
    HEALTHZ_CODE=$(echo "$HEALTHZ_RESPONSE" | tail -n1)
    HEALTHZ_BODY=$(echo "$HEALTHZ_RESPONSE" | head -n-1)

    if [[ "$HEALTHZ_CODE" == "200" ]]; then
        log_success "/healthz check passed (200 OK)"
        echo "$HEALTHZ_BODY" | tee "${DEPLOY_DIR}/healthz_response.json"
    else
        log_error "/healthz check failed (HTTP $HEALTHZ_CODE)"
        echo "$HEALTHZ_RESPONSE" | tee "${DEPLOY_DIR}/healthz_error.log"
    fi

    # Readiness check
    log_info "Checking /readyz endpoint..."
    READYZ_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_URL}/readyz" 2>&1 || echo "ERROR\n000")
    READYZ_CODE=$(echo "$READYZ_RESPONSE" | tail -n1)
    READYZ_BODY=$(echo "$READYZ_RESPONSE" | head -n-1)

    if [[ "$READYZ_CODE" == "200" ]]; then
        log_success "/readyz check passed (200 OK)"
        echo "$READYZ_BODY" | tee "${DEPLOY_DIR}/readyz_response.json"

        # Validate response fields
        if echo "$READYZ_BODY" | grep -q '"status":"ok"'; then
            log_success "Status: ok"
        fi
        if echo "$READYZ_BODY" | grep -q '"db":"ok"'; then
            log_success "DB: ok"
        fi
        if echo "$READYZ_BODY" | grep -q '"storage":"ok"'; then
            log_success "Storage: ok"
        fi
        if echo "$READYZ_BODY" | grep -q '"traceId"'; then
            log_success "TraceId: present"
        fi
    else
        log_error "/readyz check failed (HTTP $READYZ_CODE)"
        echo "$READYZ_RESPONSE" | tee "${DEPLOY_DIR}/readyz_error.log"
    fi

    # Final status
    if [[ "$HEALTHZ_CODE" == "200" && "$READYZ_CODE" == "200" ]]; then
        DEPLOYMENT_STATUS="SUCCESS"
    else
        DEPLOYMENT_STATUS="FAILED"
    fi
fi

# ==============================================================================
# Step 10: Rollback (if requested)
# ==============================================================================

if [[ "$ROLLBACK_MODE" == "true" ]]; then
    log_step "Step 10: ROLLBACK MODE"

    # Create rollback directory
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DEPLOY_DIR="out/prod_deploy/rollback_${TIMESTAMP}"
    mkdir -p "${DEPLOY_DIR}"

    log_warning "Executing production rollback..."

    # Run rollback script
    if [[ -f "ops/rollback/production_rollback.sh" ]]; then
        log_info "Running production_rollback.sh..."
        bash ops/rollback/production_rollback.sh 2>&1 | tee "${DEPLOY_DIR}/rollback.log"
        log_success "Rollback script executed"
    else
        log_error "production_rollback.sh not found!"
        log_info "Manual rollback required:"
        echo "  1. Revert application deployment"
        echo "  2. Restore database from PITR/snapshot"
        echo "  3. Verify /readyz endpoint"
        exit 1
    fi

    # Verify rollback
    log_info "Verifying rollback (waiting 10 seconds)..."
    sleep 10

    API_URL="${SUPABASE_URL}"
    READYZ_RESPONSE=$(curl -s "${API_URL}/readyz" 2>&1 || echo "ERROR")
    echo "$READYZ_RESPONSE" | tee "${DEPLOY_DIR}/rollback_readyz.json"

    if echo "$READYZ_RESPONSE" | grep -q '"status":"ok"'; then
        log_success "Rollback verification passed"
        DEPLOYMENT_STATUS="ROLLBACK_SUCCESS"
    else
        log_error "Rollback verification failed"
        DEPLOYMENT_STATUS="ROLLBACK_FAILED"
    fi
fi

# ==============================================================================
# Step 11: Deployment Summary
# ==============================================================================

log_step "Step 11: Deployment Summary"

echo ""
echo "=========================================="
echo "  KIS Estimator Deployment Summary"
echo "=========================================="
echo "Timestamp: ${TIMESTAMP}"
echo "Environment: ${APP_ENV}"
echo "Mode: $([ "$ROLLBACK_MODE" == "true" ] && echo "ROLLBACK" || echo "DEPLOY")"
echo "Status: ${DEPLOYMENT_STATUS}"
echo "Logs: ${DEPLOY_DIR}"
echo "=========================================="
echo ""

if [[ "$ROLLBACK_MODE" == "false" ]]; then
    if [[ "$DEPLOYMENT_STATUS" == "SUCCESS" ]]; then
        log_success "🎉 DEPLOYMENT SUCCESSFUL!"
        echo ""
        echo "✅ Next Steps:"
        echo "  1. Monitor application logs"
        echo "  2. Check error rates and performance"
        echo "  3. Verify E2E tests: pytest tests/test_e2e_supabase.py -v"
        echo "  4. Keep rollback ready for 24 hours"
        echo ""
        echo "📊 Monitoring:"
        echo "  Health: ${API_URL}/healthz"
        echo "  Ready: ${API_URL}/readyz"
        echo ""
        exit 0
    else
        log_error "⚠️  DEPLOYMENT COMPLETED WITH WARNINGS OR ERRORS"
        echo ""
        echo "❌ Issues Detected:"
        echo "  - Check logs in: ${DEPLOY_DIR}"
        echo "  - Review health check failures"
        echo ""
        echo "🔄 Rollback Available:"
        echo "  bash PRODUCTION_DEPLOY_FINAL.sh --rollback"
        echo ""
        exit 1
    fi
else
    if [[ "$DEPLOYMENT_STATUS" == "ROLLBACK_SUCCESS" ]]; then
        log_success "🔄 ROLLBACK COMPLETED SUCCESSFULLY"
        echo ""
        echo "✅ Next Steps:"
        echo "  1. Verify application is working with previous version"
        echo "  2. Investigate deployment failure"
        echo "  3. Fix issues and retry deployment"
        echo ""
        exit 0
    else
        log_error "⚠️  ROLLBACK COMPLETED WITH WARNINGS"
        echo ""
        echo "❌ Manual Intervention May Be Required:"
        echo "  - Check rollback logs in: ${DEPLOY_DIR}"
        echo "  - Verify database state"
        echo "  - Contact DevOps team if needed"
        echo ""
        exit 1
    fi
fi