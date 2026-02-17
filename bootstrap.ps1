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

# ── Step 2: Install Docker if needed ──────────────────────────

function Install-Docker {
    Write-Info "Docker not found - attempting automatic install..."
    Write-Host ""

    $installed = $false

    # Try winget first (built into Windows 10 1709+ and Windows 11)
    try {
        winget --version 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Installing Docker Desktop via winget..."
            winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
            if ($LASTEXITCODE -eq 0) { $installed = $true }
        }
    } catch {}

    # Try Chocolatey as fallback
    if (-not $installed) {
        try {
            choco --version 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Info "Installing Docker Desktop via Chocolatey..."
                choco install docker-desktop -y
                if ($LASTEXITCODE -eq 0) { $installed = $true }
            }
        } catch {}
    }

    if (-not $installed) {
        Write-Err @"
Could not auto-install Docker Desktop.

Please install manually:
  https://www.docker.com/products/docker-desktop/

Or install winget (App Installer) from the Microsoft Store, then re-run this script.
"@
    }

    Write-Log "Docker Desktop installed"
    Write-Info "Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue

    Write-Info "Waiting for Docker to start (this may take a minute)..."
    $ready = $false
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 3
        try {
            docker info 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
        } catch {}
        Write-Host "." -NoNewline
    }
    Write-Host ""

    if ($ready) {
        # Re-check compose
        try { docker compose version 2>$null | Out-Null; $script:HasDocker = $true } catch {}
        if (-not $script:HasDocker) {
            try { docker-compose version 2>$null | Out-Null; $script:HasDocker = $true } catch {}
        }
        if ($script:HasDocker) {
            Write-Log "Docker is installed and running!"
        } else {
            Write-Err "Docker installed but Docker Compose is missing. Please update Docker Desktop."
        }
    } else {
        Write-Warn "Docker Desktop installed but not yet responding."
        Write-Warn "Please start Docker Desktop manually, then re-run this script."
        exit 1
    }
}

# ── Step 3: Choose Install Mode ──────────────────────────────

if ($Mode -eq "auto") {
    if ($HasDocker) {
        $Mode = "docker"
        Write-Info "Auto-selected: Docker (production) mode"
    } elseif ($HasPython -and $HasNode) {
        $Mode = "dev"
        Write-Info "Auto-selected: Dev/SQLite mode (no Docker found)"
    } else {
        Write-Host ""
        Write-Info "Neither Docker nor Python+Node found."
        Write-Info "Installing Docker for production mode..."
        Install-Docker
        $Mode = "docker"
    }
}

# If Docker mode requested but Docker missing, install it
if ($Mode -eq "docker" -and -not $HasDocker) { Install-Docker }
if ($Mode -eq "dev" -and -not $HasPython)    { Write-Err "Dev mode requires Python 3.11+" }
if ($Mode -eq "dev" -and -not $HasNode)      { Write-Err "Dev mode requires Node.js 18+" }

# ── Step 4: Check for git ────────────────────────────────────

try { git --version | Out-Null } catch { Write-Err "git is required. Install from: https://git-scm.com/" }

# ── Step 5: Clone or Update Repo ─────────────────────────────

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

# ── Step 6: Run Installer ────────────────────────────────────

if ($Mode -eq "docker") {
    Write-Info "Running Docker production installer..."
    & .\install.ps1
} else {
    Write-Info "Running dev/SQLite installer..."
    & .\install-dev.ps1
}
