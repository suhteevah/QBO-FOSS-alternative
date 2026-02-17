# ──────────────────────────────────────────────────────────────
# OpenLedger — One-Click Production Installer (Windows / Docker)
# ──────────────────────────────────────────────────────────────
# Usage:  .\install.ps1
#
# Prerequisites: Docker Desktop for Windows installed and running
# This script will:
#   1. Verify Docker is available
#   2. Generate a secure .env if one doesn't exist
#   3. Build and start all containers (PostgreSQL + API + Frontend)
#   4. Run database migrations
#   5. Print access information
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "  +=====================================================+" -ForegroundColor Cyan
    Write-Host "  |         OpenLedger - Production Installer            |" -ForegroundColor Cyan
    Write-Host "  |   FOSS GAAP-Compliant AI Bookkeeping Platform        |" -ForegroundColor Cyan
    Write-Host "  +=====================================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Log   { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[XX] $msg" -ForegroundColor Red; exit 1 }
function Write-Info  { param($msg) Write-Host "[..] $msg" -ForegroundColor Blue }

Write-Banner

# ── Step 1: Check Prerequisites ──────────────────────────────

Write-Info "Checking prerequisites..."

try {
    docker version | Out-Null
} catch {
    Write-Err "Docker is not installed or not running. Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
}

$composeCmd = $null
try {
    docker compose version | Out-Null
    $composeCmd = "docker compose"
} catch {
    try {
        docker-compose version | Out-Null
        $composeCmd = "docker-compose"
    } catch {
        Write-Err "Docker Compose not found. Update Docker Desktop or install Docker Compose."
    }
}

Write-Log "Docker and Docker Compose found"

# ── Step 2: Generate .env if needed ──────────────────────────

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$needsEnv = (-not (Test-Path .env)) -or ((Get-Content .env -Raw) -match "change-me-in-production")

if ($needsEnv) {
    Write-Info "Generating production .env file..."

    $secretKey = -join ((1..64) | ForEach-Object { "{0:x}" -f (Get-Random -Minimum 0 -Maximum 16) })
    $pgPassword = -join ((1..32) | ForEach-Object { "{0:x}" -f (Get-Random -Minimum 0 -Maximum 16) })
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"

    @"
# -- OpenLedger Production Configuration --
# Generated on $timestamp

# Database
POSTGRES_USER=openledger
POSTGRES_PASSWORD=$pgPassword
POSTGRES_DB=openledger
DATABASE_URL=postgresql+asyncpg://openledger:${pgPassword}@db:5432/openledger
DATABASE_URL_SYNC=postgresql://openledger:${pgPassword}@db:5432/openledger

# Security
SECRET_KEY=$secretKey

# AI (optional - leave empty to disable AI features)
ANTHROPIC_API_KEY=
SONNET_MODEL=claude-sonnet-4-20250514

# OCR
OCR_ENGINE=tesseract

# Accounting
ACCOUNTING_BASIS=accrual
DEFAULT_FISCAL_YEAR_START=1

# Debug (set to false for production)
DEBUG=false
"@ | Out-File -FilePath .env -Encoding utf8

    Write-Log "Production .env created with secure random secrets"
    Write-Warn "Edit .env to add your ANTHROPIC_API_KEY for AI features"
} else {
    Write-Log "Existing .env found - using current configuration"
}

# ── Step 3: Build & Start Containers ─────────────────────────

Write-Info "Building and starting containers (this may take a few minutes on first run)..."

if ($composeCmd -eq "docker compose") {
    docker compose down --remove-orphans 2>$null
    docker compose build --no-cache
    docker compose up -d
} else {
    docker-compose down --remove-orphans 2>$null
    docker-compose build --no-cache
    docker-compose up -d
}

Write-Log "Containers started"

# ── Step 4: Wait for Database ────────────────────────────────

Write-Info "Waiting for PostgreSQL to be ready..."
$retries = 30
while ($retries -gt 0) {
    try {
        if ($composeCmd -eq "docker compose") {
            $result = docker compose exec -T db pg_isready -U openledger 2>&1
        } else {
            $result = docker-compose exec -T db pg_isready -U openledger 2>&1
        }
        if ($LASTEXITCODE -eq 0) { break }
    } catch {}
    $retries--
    Start-Sleep -Seconds 1
}

if ($retries -le 0) {
    Write-Err "PostgreSQL failed to start. Check logs with: $composeCmd logs db"
}
Write-Log "PostgreSQL is ready"

Write-Info "Running database migrations..."
try {
    if ($composeCmd -eq "docker compose") {
        docker compose exec -T api alembic upgrade head
    } else {
        docker-compose exec -T api alembic upgrade head
    }
    Write-Log "Migrations applied"
} catch {
    Write-Warn "Migrations skipped (tables may already exist)"
}

# ── Step 5: Health Check ─────────────────────────────────────

Write-Info "Verifying services..."
Start-Sleep -Seconds 3

try {
    $apiCheck = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    if ($apiCheck.StatusCode -eq 200) {
        Write-Log "API is healthy (port 8000)"
    }
} catch {
    Write-Warn "API may still be starting - check http://localhost:8000/health"
}

try {
    $feCheck = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 5
    if ($feCheck.StatusCode -eq 200) {
        Write-Log "Frontend is healthy (port 3000)"
    }
} catch {
    Write-Warn "Frontend may still be starting - check http://localhost:3000"
}

# ── Done ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ====================================================" -ForegroundColor Green
Write-Host "    OpenLedger installed successfully!" -ForegroundColor Green
Write-Host "  ====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:3000"
Write-Host "  API Docs:  http://localhost:8000/docs  (if DEBUG=true)"
Write-Host "  API:       http://localhost:8000/api"
Write-Host ""
Write-Host "  Manage:" -ForegroundColor White
Write-Host "    Stop:     $composeCmd down" -ForegroundColor Cyan
Write-Host "    Logs:     $composeCmd logs -f" -ForegroundColor Cyan
Write-Host "    Restart:  $composeCmd restart" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "    1. Open http://localhost:3000 and register your admin account"
Write-Host "    2. Set ANTHROPIC_API_KEY in .env for AI features, then restart"
Write-Host "    3. Import bank transactions via CSV/XLSX"
Write-Host ""

# Optionally open the browser
$openBrowser = Read-Host "Open http://localhost:3000 in your browser? (y/n)"
if ($openBrowser -eq "y") {
    Start-Process "http://localhost:3000"
}
