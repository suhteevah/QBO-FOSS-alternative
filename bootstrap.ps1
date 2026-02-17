# ──────────────────────────────────────────────────────────────
# OpenLedger — One-Shot Bootstrap Installer (Windows)
# ──────────────────────────────────────────────────────────────
#
# Usage (one-liner in PowerShell):
#   irm https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.ps1 | iex
#
# Or save and run:
#   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/suhteevah/QBO-FOSS-alternative/main/bootstrap.ps1" -OutFile bootstrap.ps1; .\bootstrap.ps1
#
# Options (set before running):
#   $env:OPENLEDGER_MODE = "docker"   # Force Docker install
#   $env:OPENLEDGER_MODE = "dev"      # Force dev/SQLite install
#   $env:OPENLEDGER_DIR  = ".\mydir"  # Custom install directory
#
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Continue"

function Write-Log   { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[!!] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[XX] $msg" -ForegroundColor Red; exit 1 }
function Write-Info  { param($msg) Write-Host "[..] $msg" -ForegroundColor Blue }

Write-Host ""
Write-Host "  +=====================================================+" -ForegroundColor Cyan
Write-Host "  |           OpenLedger - One-Shot Install              |" -ForegroundColor Cyan
Write-Host "  |   FOSS GAAP-Compliant AI Bookkeeping Platform        |" -ForegroundColor Cyan
Write-Host "  +=====================================================+" -ForegroundColor Cyan
Write-Host ""

$RepoUrl    = "https://github.com/suhteevah/QBO-FOSS-alternative.git"
$InstallDir = if ($env:OPENLEDGER_DIR) { $env:OPENLEDGER_DIR } else { "openledger" }
$Mode       = if ($env:OPENLEDGER_MODE) { $env:OPENLEDGER_MODE } else { "auto" }

# ── Step 1: Detect Environment ───────────────────────────────

$HasDocker  = $false
$HasPython  = $false
$HasNode    = $false
$PythonCmd  = ""

# Check Docker
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        try { docker compose version 2>$null | Out-Null; $HasDocker = $true } catch {}
        if (-not $HasDocker) {
            try { docker-compose version 2>$null | Out-Null; $HasDocker = $true } catch {}
        }
    }
} catch {}

# Check Python 3.11+
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $major = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
        $minor = & $cmd -c "import sys; print(sys.version_info.minor)" 2>$null
        if ([int]$major -ge 3 -and [int]$minor -ge 11) {
            $HasPython = $true
            $PythonCmd = $cmd
            break
        }
    } catch {}
}

# Check Node.js 18+
try {
    $nodeVer = (node -v).Replace("v", "").Split(".")[0]
    if ([int]$nodeVer -ge 18) { $HasNode = $true }
} catch {}

Write-Info "Environment detected:"
$dockerIcon = if ($HasDocker) { "[OK]" } else { "[XX]" }
$pythonIcon = if ($HasPython) { "[OK] ($PythonCmd)" } else { "[XX]" }
$nodeIcon   = if ($HasNode)   { "[OK] ($(node -v))" } else { "[XX]" }
Write-Host "    Docker:       $dockerIcon"
Write-Host "    Python 3.11+: $pythonIcon"
Write-Host "    Node.js 18+:  $nodeIcon"
Write-Host ""

# ── Step 2: Choose Install Mode ──────────────────────────────

if ($Mode -eq "auto") {
    if ($HasDocker) {
        $Mode = "docker"
        Write-Info "Auto-selected: Docker (production) mode"
    } elseif ($HasPython -and $HasNode) {
        $Mode = "dev"
        Write-Info "Auto-selected: Dev/SQLite mode (no Docker found)"
    } else {
        Write-Err @"
Cannot install: need either Docker OR (Python 3.11+ AND Node.js 18+)

  Option A - Install Docker Desktop:
    https://www.docker.com/products/docker-desktop/

  Option B - Install Python + Node:
    Python: https://www.python.org/downloads/
    Node:   https://nodejs.org/
"@
    }
}

if ($Mode -eq "docker" -and -not $HasDocker) { Write-Err "Docker mode requested but Docker is not available" }
if ($Mode -eq "dev" -and -not $HasPython)    { Write-Err "Dev mode requires Python 3.11+" }
if ($Mode -eq "dev" -and -not $HasNode)      { Write-Err "Dev mode requires Node.js 18+" }

# ── Step 3: Check for git ────────────────────────────────────

try { git --version | Out-Null } catch { Write-Err "git is required. Install from: https://git-scm.com/" }

# ── Step 4: Clone or Update Repo ─────────────────────────────

if (Test-Path "$InstallDir\.git") {
    Write-Info "Existing installation found - pulling latest..."
    Set-Location $InstallDir
    git pull --ff-only origin main 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Warn "Could not pull (offline or uncommitted changes)" }
} else {
    Write-Info "Cloning OpenLedger into .\$InstallDir..."
    git clone $RepoUrl $InstallDir
    Set-Location $InstallDir
    Write-Log "Repository cloned"
}

# ── Step 5: Run Installer ────────────────────────────────────

if ($Mode -eq "docker") {
    Write-Info "Running Docker production installer..."
    & .\install.ps1
} else {
    Write-Info "Running dev/SQLite installer..."
    & .\install-dev.ps1
}
