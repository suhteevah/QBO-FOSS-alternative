# OpenLedger — Quick Start (dev mode, Windows)
# Starts both backend and frontend in separate windows

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "Starting OpenLedger..." -ForegroundColor Cyan
Write-Host ""

# Start backend in a new PowerShell window
Write-Host "[1/2] Starting API server on port 8000..." -ForegroundColor Green
$backendCmd = "Set-Location '$scriptDir'; .\venv\Scripts\Activate.ps1; uvicorn openledger.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Start frontend in a new PowerShell window
Write-Host "[2/2] Starting frontend on port 3000..." -ForegroundColor Green
$frontendCmd = "Set-Location '$scriptDir\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "OpenLedger is running!" -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""

Start-Process "http://localhost:3000"
