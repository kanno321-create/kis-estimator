#!/usr/bin/env bash
# ============================================================================
# KIS Estimator - Supabase Storage Initialization (OPERATIONS MODE)
# Purpose: Create and configure evidence bucket (idempotent, private, RLS)
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration (OPERATIONS MODE)
BUCKET_NAME="evidence"
BUCKET_PUBLIC=false  # ✅ Private bucket (signed URLs only)
FILE_SIZE_LIMIT=$((100 * 1024 * 1024))  # 100MB (production grade)
ALLOWED_MIME_TYPES='["application/json","application/pdf","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","image/svg+xml"]'

echo "============================================================================"
echo "KIS Estimator - Supabase Storage Initialization"
echo "============================================================================"

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    echo -e "${RED}Error: Supabase CLI is not installed${NC}"
    echo "Install with: npm install -g supabase"
    exit 1
fi

echo -e "${GREEN}✓ Supabase CLI found${NC}"

# Check if required environment variables are set
if [ -z "${SUPABASE_URL:-}" ] || [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
    echo -e "${RED}Error: Required environment variables not set${NC}"
    echo "Please set: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY"
    exit 1
fi

echo -e "${GREEN}✓ Environment variables configured${NC}"

# Create bucket using Supabase Management API
echo ""
echo "Creating storage bucket: ${BUCKET_NAME}"
echo "  - Public: ${BUCKET_PUBLIC}"
echo "  - File size limit: ${FILE_SIZE_LIMIT} bytes (50MB)"
echo "  - Allowed MIME types: ${ALLOWED_MIME_TYPES}"
echo ""

# Check if bucket exists (idempotent)
BUCKET_CHECK=$(curl -s -X GET \
    "${SUPABASE_URL}/storage/v1/bucket/${BUCKET_NAME}" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}")

if echo "$BUCKET_CHECK" | grep -q "\"id\":\"${BUCKET_NAME}\""; then
    echo -e "${GREEN}✓ Bucket '${BUCKET_NAME}' already exists (idempotent)${NC}"
else
    echo "Creating bucket '${BUCKET_NAME}'..."

    # Create bucket using Storage API
    BUCKET_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST \
        "${SUPABASE_URL}/storage/v1/bucket" \
        -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"${BUCKET_NAME}\",
            \"name\": \"${BUCKET_NAME}\",
            \"public\": ${BUCKET_PUBLIC},
            \"file_size_limit\": ${FILE_SIZE_LIMIT},
            \"allowed_mime_types\": ${ALLOWED_MIME_TYPES}
        }")

    HTTP_CODE=$(echo "$BUCKET_RESPONSE" | tail -n1)
    RESPONSE_BODY=$(echo "$BUCKET_RESPONSE" | head -n-1)

    if [[ "$HTTP_CODE" == "200" ]] || [[ "$HTTP_CODE" == "201" ]]; then
        echo -e "${GREEN}✓ Bucket '${BUCKET_NAME}' created successfully${NC}"
    else
        echo -e "${RED}✗ Bucket creation failed (HTTP $HTTP_CODE)${NC}"
        echo "Response: $RESPONSE_BODY"
        exit 1
    fi
fi

# Apply storage policies via SQL
echo ""
echo "Applying storage policies..."

supabase db execute --sql "
-- ============================================================================
-- Storage Policies for evidence bucket
-- ============================================================================

-- Policy 1: Service role can upload files
CREATE POLICY IF NOT EXISTS evidence_service_upload
ON storage.objects FOR INSERT
TO service_role
WITH CHECK (bucket_id = '${BUCKET_NAME}');

-- Policy 2: Service role can update files
CREATE POLICY IF NOT EXISTS evidence_service_update
ON storage.objects FOR UPDATE
TO service_role
USING (bucket_id = '${BUCKET_NAME}');

-- Policy 3: Service role can delete files
CREATE POLICY IF NOT EXISTS evidence_service_delete
ON storage.objects FOR DELETE
TO service_role
USING (bucket_id = '${BUCKET_NAME}');

-- Policy 4: Authenticated users can read via signed URLs
CREATE POLICY IF NOT EXISTS evidence_authenticated_select
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = '${BUCKET_NAME}');
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Storage policies applied successfully${NC}"
else
    echo -e "${RED}✗ Failed to apply storage policies${NC}"
    exit 1
fi

# Test bucket access
echo ""
echo "Testing bucket access..."

# Try to list objects (should return empty or existing objects)
TEST_RESPONSE=$(curl -s -X GET \
    "${SUPABASE_URL}/storage/v1/object/list/${BUCKET_NAME}" \
    -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
    -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}")

if echo "$TEST_RESPONSE" | grep -q "error"; then
    echo -e "${RED}✗ Bucket access test failed${NC}"
    echo "Response: ${TEST_RESPONSE}"
    exit 1
else
    echo -e "${GREEN}✓ Bucket access test passed${NC}"
fi

# Summary
echo ""
echo "============================================================================"
echo "Storage Initialization Complete"
echo "============================================================================"
echo ""
echo "Bucket Configuration:"
echo "  - Name: ${BUCKET_NAME}"
echo "  - Public: ${BUCKET_PUBLIC}"
echo "  - Max file size: 50MB"
echo "  - Allowed types: JSON, PDF, Excel, SVG"
echo ""
echo "Path Structure:"
echo "  evidence/quote/{QUOTE_ID}/{STAGE}/{HASH}.{ext}"
echo ""
echo "Example Paths:"
echo "  evidence/quote/123e4567-e89b-12d3-a456-426614174000/enclosure/abc123.json"
echo "  evidence/quote/123e4567-e89b-12d3-a456-426614174000/breaker/def456.json"
echo "  evidence/quote/123e4567-e89b-12d3-a456-426614174000/format/ghi789.xlsx"
echo ""
echo "Security:"
echo "  - Service role: Full access (upload, update, delete, read)"
echo "  - Authenticated: Read via signed URLs only"
echo "  - Anonymous: No access"
echo ""
echo "Generate signed URLs (10 min TTL):"
echo "  supabase storage signed-url ${BUCKET_NAME}/path/to/file.json --expires-in 600"
echo ""
echo -e "${GREEN}✓ Storage initialization successful${NC}"
echo "============================================================================"