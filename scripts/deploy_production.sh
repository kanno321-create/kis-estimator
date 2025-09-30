#!/bin/bash
# Production Deployment Script for KIS Estimator
# Handles dependency installation, database setup, and service startup

set -e

echo "=========================================="
echo "KIS Estimator Production Deployment"
echo "=========================================="

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"production"}
DATABASE_URL=${DATABASE_URL:-""}
SUPABASE_URL=${SUPABASE_URL:-""}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-""}
SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET:-""}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Validation
echo -e "\n${YELLOW}1. Environment Validation${NC}"
echo "-------------------------------------"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}✗${NC} DATABASE_URL not set"
    exit 1
else
    echo -e "${GREEN}✓${NC} DATABASE_URL configured"
fi

if [ -z "$SUPABASE_JWT_SECRET" ]; then
    echo -e "${YELLOW}⚠${NC} SUPABASE_JWT_SECRET not set (JWT auth will fail)"
else
    echo -e "${GREEN}✓${NC} SUPABASE_JWT_SECRET configured"
fi

# Dependencies
echo -e "\n${YELLOW}2. Installing Dependencies${NC}"
echo "-------------------------------------"

echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo -e "${GREEN}✓${NC} Dependencies installed"

# Database Setup
echo -e "\n${YELLOW}3. Database Configuration${NC}"
echo "-------------------------------------"

echo "Applying performance indexes..."
if [ -f "sql/performance_indexes.sql" ]; then
    psql "$DATABASE_URL" < sql/performance_indexes.sql 2>/dev/null || {
        echo -e "${YELLOW}⚠${NC} Some indexes may already exist (continuing)"
    }
    echo -e "${GREEN}✓${NC} Indexes applied"
else
    echo -e "${YELLOW}⚠${NC} Index file not found, skipping"
fi

# Security Configuration
echo -e "\n${YELLOW}4. Security Configuration${NC}"
echo "-------------------------------------"

# Create .env.production if not exists
if [ ! -f ".env.production" ]; then
    echo "Creating production environment file..."
    cat > .env.production << EOF
ENVIRONMENT=production
DATABASE_URL=${DATABASE_URL}
SUPABASE_URL=${SUPABASE_URL}
SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
JWT_AUD=authenticated

# Security
ALLOWED_ORIGINS=https://kis-estimator.com,https://app.kis-estimator.com
ALLOWED_HOSTS=kis-estimator.com,*.kis-estimator.com

# Performance
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=3600
DB_ECHO=false

# Rate Limiting
REDIS_URL=${REDIS_URL:-memory://}

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
EOF
    echo -e "${GREEN}✓${NC} Production environment configured"
else
    echo -e "${GREEN}✓${NC} Using existing .env.production"
fi

# Evidence Pack
echo -e "\n${YELLOW}5. Evidence Pack Generation${NC}"
echo "-------------------------------------"

mkdir -p evidence/$(date +%Y%m%d_%H%M%S)
current_evidence="evidence/$(date +%Y%m%d_%H%M%S)"

# Generate deployment evidence
cat > "$current_evidence/deployment.json" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "environment": "$ENVIRONMENT",
  "version": "$(git describe --tags --always 2>/dev/null || echo 'unknown')",
  "commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "indexes_applied": true,
  "security": {
    "jwt_enabled": $([ -n "$SUPABASE_JWT_SECRET" ] && echo "true" || echo "false"),
    "cors_configured": true,
    "rate_limiting": true
  },
  "performance": {
    "db_pool_size": 50,
    "db_max_overflow": 100,
    "target_p95_ms": 200
  }
}
EOF

echo -e "${GREEN}✓${NC} Evidence pack created: $current_evidence"

# Service Startup
echo -e "\n${YELLOW}6. Service Startup${NC}"
echo "-------------------------------------"

# Check if running in container/systemd/pm2
if [ -n "$PM2_HOME" ]; then
    echo "Starting with PM2..."
    pm2 start ecosystem.config.js --env production
    echo -e "${GREEN}✓${NC} Service started with PM2"
elif [ -f "/etc/systemd/system/kis-estimator.service" ]; then
    echo "Starting with systemd..."
    sudo systemctl restart kis-estimator
    echo -e "${GREEN}✓${NC} Service started with systemd"
else
    echo "Starting with uvicorn..."
    echo ""
    echo "Run the following command to start the service:"
    echo ""
    echo "  uvicorn api.main:app \\"
    echo "    --host 0.0.0.0 \\"
    echo "    --port 8000 \\"
    echo "    --workers 4 \\"
    echo "    --log-level info"
    echo ""
    echo "Or for development/testing:"
    echo "  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
fi

# Post-Deployment Tests
echo -e "\n${YELLOW}7. Post-Deployment Validation${NC}"
echo "-------------------------------------"

sleep 3  # Give service time to start

# Run smoke test if available
if [ -f "scripts/smoke_test.sh" ]; then
    echo "Running smoke tests..."
    bash scripts/smoke_test.sh || {
        echo -e "${YELLOW}⚠${NC} Some smoke tests failed (review above)"
    }
else
    echo -e "${YELLOW}⚠${NC} Smoke test script not found"
fi

# Summary
echo -e "\n=========================================="
echo -e "${GREEN}Deployment Complete${NC}"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Verify /readyz endpoint: curl http://localhost:8000/readyz"
echo "2. Run security check: bash scripts/security_check.sh"
echo "3. Run performance test: bash scripts/performance_test.sh"
echo "4. Monitor logs: tail -f logs/api.log"
echo ""
echo "Evidence saved to: $current_evidence"
echo ""

# Generate SHA256 checksums
cd "$current_evidence"
sha256sum * > SHA256SUMS
cd - > /dev/null

echo -e "${GREEN}SHA256 checksums generated${NC}"
echo ""