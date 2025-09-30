# Learnings: Supabase Integration Patterns for KIS Estimator

## Database Schema Patterns

### TIMESTAMPTZ with UTC Enforcement
```sql
-- ALWAYS use TIMESTAMPTZ with explicit UTC conversion
created_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
updated_at TIMESTAMPTZ NOT NULL DEFAULT (now() AT TIME ZONE 'utc')

-- Trigger function for automatic updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = (now() AT TIME ZONE 'utc');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Why**: Ensures consistent UTC timestamps across all environments, prevents timezone-related bugs.

### SHA256 Validation Pattern
```sql
-- Enforce SHA256 format at database level
sha256 TEXT NOT NULL CHECK (length(sha256) = 64 AND sha256 ~ '^[a-f0-9]+$')

-- Validation function
CREATE OR REPLACE FUNCTION public.check_sha256(hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN hash IS NOT NULL
        AND length(hash) = 64
        AND hash ~ '^[a-f0-9]{64}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;
```

**Why**: Prevents invalid hash storage, enables integrity verification at DB layer.

### RLS Policy Design
```sql
-- Enable RLS on all tables
ALTER TABLE estimator.quotes ENABLE ROW LEVEL SECURITY;

-- Service role: Full access (bypasses RLS)
-- No policy needed - service_role bypasses by default

-- Authenticated: Read-only
CREATE POLICY "documents_authenticated_select"
ON estimator.documents
FOR SELECT
TO authenticated
USING (true);

-- Anon: No direct access (use signed URLs)
```

**Pattern**: Service role writes, authenticated reads, anon uses signed URLs only.

## Storage Organization Patterns

### Path Structure
```
evidence/quote/{QUOTE_ID}/{STAGE}/{SHA256}.{ext}
```

**Example**:
```
evidence/quote/123e4567-e89b-12d3-a456-426614174000/enclosure/abc123def456.json
evidence/quote/123e4567-e89b-12d3-a456-426614174000/breaker/789ghi012jkl.json
evidence/quote/123e4567-e89b-12d3-a456-426614174000/format/mno345pqr678.xlsx
```

**Benefits**:
- Quote isolation (easy cleanup)
- Stage organization (FIX-4 pipeline alignment)
- Hash-based naming (integrity verification)
- Extension preserved (MIME type validation)

### Idempotent Script Pattern
```bash
#!/bin/bash
set -euo pipefail

# Check if resource exists
RESOURCE_EXISTS=$(check_resource 2>/dev/null | grep -c "^resource$" || true)

if [ "$RESOURCE_EXISTS" -eq 1 ]; then
    echo "✅ Resource already exists (skipping)"
else
    create_resource || echo "⚠️ Creation may have failed (might already exist)"
    echo "✅ Resource created"
fi
```

**Pattern**: Check → Create (with error handling) → Verify

## CI/CD Integration Patterns

### Two-Stage Deployment
```yaml
# Stage 1: PR - Check only (dry-run)
supabase-check:
  if: github.event_name == 'pull_request'
  steps:
    - supabase db lint
    - supabase db diff --linked  # Shows what would change

# Stage 2: Main - Deploy
supabase-deploy:
  if: github.ref == 'refs/heads/main'
  needs: [test, supabase-check]
  steps:
    - supabase link
    - supabase db push  # Actual deployment
    - verify deployment
```

**Why**: Prevents accidental production changes, enables PR review of schema changes.

### Secret Management
```yaml
# Required GitHub Secrets
SUPABASE_PROJECT_REF       # Project identifier
SUPABASE_ACCESS_TOKEN      # API token
SUPABASE_DB_PASSWORD       # Database password
SUPABASE_SERVICE_ROLE_KEY  # Full access key (CRITICAL)
```

**Security**: Service role key = full database access, never expose in logs.

## Rollback Strategies

### Three-Tier Approach

**Tier 1: CLI Rollback** (Best - if migration not pushed)
```bash
supabase migration down
```

**Tier 2: Manual SQL** (Good - if migration pushed)
```bash
# 1. Backup first
supabase db dump > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Create rollback script with DROP statements in reverse order
# (Drop child tables before parent tables to respect foreign keys)

# 3. Execute rollback
psql $SUPABASE_DB_URL < rollback.sql

# 4. Verify
supabase db diff --linked
```

**Tier 3: Backup Restore** (Last resort)
```bash
supabase db restore < backup_before_deploy.sql
```

**Critical**: Always backup before rollback.

## Performance Considerations

### Index Strategy
```sql
-- Foreign keys: Always index
CREATE INDEX idx_quote_items_quote_id ON estimator.quote_items(quote_id);

-- Timestamps: Index for queries
CREATE INDEX idx_quotes_created_at ON estimator.quotes(created_at DESC);

-- Status: Index for filtering
CREATE INDEX idx_quotes_status ON estimator.quotes(status);

-- Conditional indexes: Save space
CREATE INDEX idx_catalog_active ON shared.catalog_items(is_active) 
WHERE is_active = true;
```

**Rule**: Index foreign keys, query columns, and filter conditions.

### Function Security
```sql
-- SECURITY DEFINER: Runs with function owner's privileges
CREATE OR REPLACE FUNCTION public.calculate_quote_totals(p_quote_id UUID)
RETURNS JSONB AS $$
...
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Use SECURITY DEFINER**: When function needs elevated privileges (e.g., bypassing RLS).

## Testing Patterns

### Migration Validation
```bash
# 1. File existence
test -f db/migrations/20250930_init.sql

# 2. Non-empty
test -s db/migrations/20250930_init.sql

# 3. Contains expected statements
grep -c "CREATE TABLE" db/migrations/20250930_init.sql
# Expected: 7

grep -c "CREATE FUNCTION" db/migrations/20250930_init.sql
# Expected: 5

grep -c "CREATE POLICY" db/migrations/20250930_init.sql
# Expected: 6
```

### Storage Bucket Validation
```bash
# 1. List buckets
supabase storage list | grep evidence

# 2. Test upload (with service role key)
echo "test" > test.txt
supabase storage cp test.txt evidence/test/test.txt

# 3. Generate signed URL
supabase storage signed-url evidence/test/test.txt --expires-in 600

# 4. Cleanup
supabase storage rm evidence/test/test.txt
rm test.txt
```

## Common Pitfalls & Solutions

### Pitfall 1: Timezone Confusion
**Problem**: `created_at TIMESTAMP DEFAULT now()` uses local timezone
**Solution**: Always use `TIMESTAMPTZ DEFAULT (now() AT TIME ZONE 'utc')`

### Pitfall 2: RLS Not Enabled
**Problem**: Service role bypasses RLS, but authenticated/anon roles blocked
**Solution**: Enable RLS + create policies for each role

### Pitfall 3: Foreign Key Order
**Problem**: Cannot drop parent table before child tables
**Solution**: Drop in reverse order, use CASCADE carefully

### Pitfall 4: Migration Already Applied
**Problem**: Re-running migration fails with "already exists" errors
**Solution**: Use `CREATE ... IF NOT EXISTS`, handle errors gracefully

### Pitfall 5: Storage Policy Missing
**Problem**: Upload succeeds but download fails (403 Forbidden)
**Solution**: Create SELECT policy for authenticated role on storage.objects

## Best Practices Summary

1. **Always UTC**: Use TIMESTAMPTZ with explicit UTC conversion
2. **Always RLS**: Enable row-level security on all user-facing tables
3. **Always Index**: Foreign keys, timestamps, status columns
4. **Always Validate**: SHA256 format, enum values, CHECK constraints
5. **Always Backup**: Before rollback, before major changes
6. **Always Test**: Lint, diff, dry-run before production push
7. **Always Document**: Runbook, rollback procedures, secrets required
8. **Always Idempotent**: Scripts should handle "already exists" gracefully

## Tool Commands Cheat Sheet

```bash
# Supabase CLI
supabase link --project-ref <ref>           # Link project
supabase db lint --file <file>              # Lint SQL
supabase db diff --linked                   # Show schema diff
supabase db push                            # Push migrations
supabase db dump > backup.sql               # Backup
supabase db restore < backup.sql            # Restore
supabase storage ls <bucket>                # List objects
supabase storage cp <src> <dst>             # Upload
supabase storage signed-url <path> --expires-in 600  # Signed URL

# PostgreSQL
psql $SUPABASE_DB_URL -c "SELECT ..."      # Execute SQL
psql $SUPABASE_DB_URL < script.sql         # Run script

# GitHub Secrets
gh secret set <name> --body "<value>"       # Set secret
gh secret list                              # List secrets
```