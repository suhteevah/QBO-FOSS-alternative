<#
.SYNOPSIS
    Builds the OpenLedger Python backend into a sidecar executable for Tauri
    on Windows.

.DESCRIPTION
    1. Runs PyInstaller using desktop/pyinstaller.spec to produce a single-file
       openledger-server.exe.
    2. Detects the Rust target triple for the current machine.
    3. Copies the binary into src-tauri/binaries/ with the triple suffix so
       that Tauri can locate it at runtime.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File desktop\build-sidecar.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$SpecFile    = Join-Path $ScriptDir "pyinstaller.spec"
$BinDir      = Join-Path $ScriptDir "src-tauri" "binaries"

# ── 1. Run PyInstaller ──────────────────────────────────────────────────────
Write-Host "==> Building sidecar with PyInstaller ..." -ForegroundColor Cyan

Push-Location $ProjectRoot
try {
    python -m PyInstaller --clean --noconfirm $SpecFile
} finally {
    Pop-Location
}

$Artifact = Join-Path $ProjectRoot "dist" "openledger-server.exe"
if (-not (Test-Path $Artifact)) {
    Write-Error "PyInstaller did not produce $Artifact"
    exit 1
}

# ── 2. Detect target triple ─────────────────────────────────────────────────
# On Windows the Rust default target is almost always x86_64-pc-windows-msvc
# but we detect it properly in case the user has a different default.
$RustcTarget = (rustc -vV | Select-String "^host:" | ForEach-Object { $_ -replace "^host:\s*", "" }).Trim()
if (-not $RustcTarget) {
    Write-Host "Could not detect Rust target triple, defaulting to x86_64-pc-windows-msvc" -ForegroundColor Yellow
    $RustcTarget = "x86_64-pc-windows-msvc"
}

Write-Host "==> Detected target triple: $RustcTarget" -ForegroundColor Cyan

# ── 3. Copy to Tauri binaries ───────────────────────────────────────────────
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

$Destination = Join-Path $BinDir "openledger-server-${RustcTarget}.exe"
Copy-Item -Force $Artifact $Destination

Write-Host "==> Sidecar ready: $Destination" -ForegroundColor Green
Write-Host "    Size: $([math]::Round((Get-Item $Destination).Length / 1MB, 1)) MB"
