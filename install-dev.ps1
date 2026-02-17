# ──────────────────────────────────────────────────────────────
# OpenLedger — Lightweight Dev/Demo Installer (Windows, No Docker)
# ──────────────────────────────────────────────────────────────
# Usage:  .\install-dev.ps1
#
# Prerequisites: Python 3.11+ and Node.js 18+
# Uses SQLite (no PostgreSQL needed) — perfect for demos & dev
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "  +=====================================================+" -ForegroundColor Cyan
    Write-Host "  |      OpenLedger - Dev / Demo Installer               |" -ForegroundColor Cyan
    Write-Host "  |   No Docker - SQLite - Zero External Deps            |" -ForegroundColor Cyan
    Write-Host "  +=====================================================+" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Log   { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[XX] $msg" -ForegroundColor Red; exit 1 }
function Write-Info  { param($msg) Write-Host "[..] $msg" -ForegroundColor Blue }

Write-Banner

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# ── Step 1: Check Prerequisites ──────────────────────────────

Write-Info "Checking prerequisites..."

# Python
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        $major = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
        $minor = & $cmd -c "import sys; print(sys.version_info.minor)" 2>$null
        if ([int]$major -ge 3 -and [int]$minor -ge 11) {
            $pythonCmd = $cmd
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Err "Python 3.11+ is required. Download from https://www.python.org/downloads/"
}
Write-Log "Python $ver found ($pythonCmd)"

# Node.js
try {
    $nodeVer = (node -v).Replace("v", "").Split(".")[0]
    if ([int]$nodeVer -lt 18) { throw "too old" }
    Write-Log "Node.js $(node -v) found"
} catch {
    Write-Err "Node.js 18+ is required. Download from https://nodejs.org/"
}

try {
    npm -v | Out-Null
    Write-Log "npm $(npm -v) found"
} catch {
    Write-Err "npm not found"
}

# ── Step 2: Python Virtual Environment ───────────────────────

if (-not (Test-Path "venv")) {
    Write-Info "Creating Python virtual environment..."
    & $pythonCmd -m venv venv
    Write-Log "Virtual environment created"
} else {
    Write-Log "Virtual environment already exists"
}

# Activate
if (Test-Path "venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
} elseif (Test-Path "venv/bin/activate") {
    & "./venv/bin/activate"
}

Write-Info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
Write-Log "Python dependencies installed"

# ── Step 3: Configure Environment ────────────────────────────

$needsEnv = (-not (Test-Path .env)) -or ((Get-Content .env -Raw -ErrorAction SilentlyContinue) -match "postgresql")

if ($needsEnv) {
    Write-Info "Creating SQLite development .env..."

    $secretKey = & $pythonCmd -c "import secrets; print(secrets.token_hex(32))"
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssK"

    @"
# -- OpenLedger Dev/Demo Configuration --
# Generated on $timestamp
# Using SQLite - no PostgreSQL needed

# Database (SQLite for dev/demo)
DATABASE_URL=sqlite+aiosqlite:///./openledger.db
DATABASE_URL_SYNC=sqlite:///./openledger.db

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

# Debug mode (enables /docs, CORS *, verbose logging)
DEBUG=true
"@ | Out-File -FilePath .env -Encoding utf8

    Write-Log "SQLite .env created"
} else {
    Write-Log "Existing .env found"
}

# ── Step 4: Install Frontend Dependencies ────────────────────

Write-Info "Installing frontend dependencies..."
Set-Location frontend
npm install --silent 2>$null
Set-Location $scriptDir
Write-Log "Frontend dependencies installed"

# ── Step 5: Build Frontend ───────────────────────────────────

Write-Info "Building frontend..."
Set-Location frontend
npm run build
Set-Location $scriptDir
Write-Log "Frontend built successfully"

# ── Done ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "  ====================================================" -ForegroundColor Green
Write-Host "    OpenLedger installed successfully!" -ForegroundColor Green
Write-Host "  ====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  To start the app:" -ForegroundColor White
Write-Host ""
Write-Host "    # Terminal 1 - Backend API" -ForegroundColor Cyan
Write-Host "    .\venv\Scripts\Activate.ps1"
Write-Host "    uvicorn openledger.main:app --host 0.0.0.0 --port 8000 --reload"
Write-Host ""
Write-Host "    # Terminal 2 - Frontend Dev Server" -ForegroundColor Cyan
Write-Host "    cd frontend; npm run dev"
Write-Host ""
Write-Host "  Or use the quick-start command:" -ForegroundColor White
Write-Host "    .\start.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Access:" -ForegroundColor White
Write-Host "    Frontend:  http://localhost:3000"
Write-Host "    API Docs:  http://localhost:8000/docs"
Write-Host ""
Write-Host "  The database (SQLite) auto-creates on first run" -ForegroundColor Yellow
Write-Host "  with a full GAAP chart of accounts." -ForegroundColor Yellow
Write-Host ""

$openBrowser = Read-Host "Start the app now? (y/n)"
if ($openBrowser -eq "y") {
    Write-Info "Starting backend and frontend..."
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir'; .\venv\Scripts\Activate.ps1; uvicorn openledger.main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$scriptDir\frontend'; npm run dev"
    Start-Sleep -Seconds 4
    Start-Process "http://localhost:3000"
}
