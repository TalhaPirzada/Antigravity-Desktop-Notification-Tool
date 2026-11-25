# PowerShell Installer for Antigravity Desktop Notifier (Windows)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Installing Antigravity Desktop Notifier (Windows)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cliBin = Join-Path $scriptDir "bin\agy-notify"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Warning "Python is required but was not found in PATH. Please install Python 3."
    Exit 1
}

Write-Host "`n[INFO] Registering Antigravity lifecycle hooks..." -ForegroundColor Yellow
python "$cliBin" install

Write-Host "`n[INFO] Running diagnostics..." -ForegroundColor Yellow
python "$cliBin" doctor

Write-Host "`n[INFO] Testing notification..." -ForegroundColor Yellow
python "$cliBin" test complete

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "Installation complete. Windows Toast notifications active." -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
