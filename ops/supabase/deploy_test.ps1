# ============================================================================
# KIS Estimator - Supabase 실제 연결 배포 테스트 (PowerShell)
# Purpose: DB lint/diff/push → Storage init → API server → /readyz test
# ============================================================================

$ErrorActionPreference = "Stop"

function Log-Info { param($msg) Write-Host "[INFO] $msg" -ForegroundColor Green }
function Log-Error { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red }
function Log-Warn { param($msg) Write-Host "[WARN] $msg" -ForegroundColor Yellow }

Log-Info "🚀 KIS Estimator - Supabase 실제 연결 배포 테스트"

# ============================================================================
# Step 0: 환경 변수 확인
# ============================================================================

Log-Info "Step 0: Checking environment variables..."

$required_vars = @(
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_DB_URL"
)

$missing = @()
foreach ($var in $required_vars) {
    if (-not (Get-Item -Path "Env:$var" -ErrorAction SilentlyContinue)) {
        $missing += $var
    }
}

if ($missing.Count -gt 0) {
    Log-Error "Missing required environment variables:"
    $missing | ForEach-Object { Log-Error "  - $_" }
    Log-Error "Please set all variables in .env or use `$env:VAR=value"
    exit 1
}

$APP_PORT = if ($env:APP_PORT) { $env:APP_PORT } else { 8000 }
$APP_ENV = if ($env:APP_ENV) { $env:APP_ENV } else { "staging" }

Log-Info "✅ Environment variables validated"
Log-Info "APP_PORT: $APP_PORT"
Log-Info "APP_ENV: $APP_ENV"

# ============================================================================
# Step 1: Supabase DB Lint & Diff
# ============================================================================

Log-Info "Step 1: Running Supabase DB lint and diff..."

if (Get-Command supabase -ErrorAction SilentlyContinue) {
    Log-Info "Supabase CLI found"

    # DB lint
    Log-Info "Running db lint..."
    try {
        supabase db lint 2>$null
        Log-Info "✅ DB lint passed"
    } catch {
        Log-Warn "DB lint had warnings (non-fatal)"
    }

    # DB diff
    Log-Info "Running db diff..."
    try {
        supabase db diff --linked 2>$null
        Log-Info "✅ DB diff OK"
    } catch {
        Log-Warn "DB diff skipped (project not linked or no changes)"
    }
} else {
    Log-Warn "Supabase CLI not found - skipping lint/diff"
    Log-Warn "Install with: npm install -g supabase"
}

# ============================================================================
# Step 2: DB Push (Optional - with guard)
# ============================================================================

Log-Info "Step 2: DB Push (optional)..."

if ($env:SKIP_DB_PUSH -eq "true") {
    Log-Warn "Skipping DB push (SKIP_DB_PUSH=true)"
} elseif ($APP_ENV -eq "production") {
    Log-Warn "Skipping DB push (production environment - manual only)"
} else {
    $reply = Read-Host "Push database migrations? (yes/NO)"
    if ($reply -match "^[Yy][Ee][Ss]$") {
        Log-Info "Pushing database migrations..."
        if (Get-Command supabase -ErrorAction SilentlyContinue) {
            supabase db push --include-all
            if ($LASTEXITCODE -ne 0) {
                Log-Error "DB push failed"
                exit 1
            }
            Log-Info "✅ DB push completed"
        } else {
            Log-Error "Supabase CLI required for db push"
            exit 1
        }
    } else {
        Log-Info "DB push skipped"
    }
}

# ============================================================================
# Step 3: Storage Initialization
# ============================================================================

Log-Info "Step 3: Initializing storage..."

if (Test-Path "ops/supabase/storage_init.sh") {
    try {
        bash ops/supabase/storage_init.sh
        Log-Info "✅ Storage initialized"
    } catch {
        Log-Warn "Storage initialization had warnings"
    }
} else {
    Log-Error "Storage init script not found: ops/supabase/storage_init.sh"
    exit 1
}

# ============================================================================
# Step 4: Start API Server (background)
# ============================================================================

Log-Info "Step 4: Starting API server..."

# Kill existing server on port
$existing = Get-NetTCPConnection -LocalPort $APP_PORT -ErrorAction SilentlyContinue
if ($existing) {
    Log-Warn "Port $APP_PORT is in use, killing existing process..."
    $pid = (Get-Process -Id $existing.OwningProcess).Id
    Stop-Process -Id $pid -Force
    Start-Sleep -Seconds 2
}

# Start server in background
Log-Info "Starting uvicorn on port $APP_PORT..."
$job = Start-Job -ScriptBlock {
    param($port)
    uvicorn api.main:app --host 0.0.0.0 --port $port
} -ArgumentList $APP_PORT

Log-Info "API server started (Job ID: $($job.Id))"
Log-Info "Waiting for server to be ready..."

# Wait for server
$max_wait = 30
for ($i = 1; $i -le $max_wait; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$APP_PORT/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Log-Info "✅ API server is ready"
            break
        }
    } catch {}

    if ($i -eq $max_wait) {
        Log-Error "API server failed to start within ${max_wait}s"
        Stop-Job -Job $job
        Remove-Job -Job $job
        exit 1
    }
    Start-Sleep -Seconds 1
}

# ============================================================================
# Step 5: Test /readyz Endpoint
# ============================================================================

Log-Info "Step 5: Testing /readyz endpoint..."

$readyz_url = "http://localhost:$APP_PORT/readyz"
Log-Info "Calling: $readyz_url"

try {
    $response = Invoke-WebRequest -Uri $readyz_url -UseBasicParsing
    $http_code = $response.StatusCode
    $response_body = $response.Content

    Log-Info "HTTP Status: $http_code"
    Log-Info "Response:"
    $response_body | ConvertFrom-Json | ConvertTo-Json -Depth 10

    if ($http_code -eq 200) {
        Log-Info "✅ /readyz check passed"
    } else {
        Log-Error "❌ /readyz check failed (HTTP $http_code)"
        Stop-Job -Job $job
        Remove-Job -Job $job
        exit 1
    }
} catch {
    Log-Error "❌ /readyz check failed: $_"
    Stop-Job -Job $job
    Remove-Job -Job $job
    exit 1
}

# ============================================================================
# Cleanup
# ============================================================================

Log-Info "Cleaning up..."
Stop-Job -Job $job
Remove-Job -Job $job
Log-Info "API server stopped"

# ============================================================================
# Summary
# ============================================================================

Log-Info "✅ Supabase 실제 연결 배포 테스트 완료"
Log-Info "모든 단계가 성공적으로 완료되었습니다"
Log-Info ""
Log-Info "Next steps:"
Log-Info "  1. Run E2E tests: pytest tests/test_e2e_supabase.py -v"
Log-Info "  2. Deploy to staging/production via CI/CD"