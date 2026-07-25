<#!
.SYNOPSIS
    Guided local launcher for CQRP's FYERS data-only PAPER workflow.

.DESCRIPTION
    Starts the daily token helper (when requested), local Streamlit dashboard,
    and 60-second market-data/PAPER worker. No FYERS order endpoint is used.
#>

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $projectRoot "venv-python314-backup\Scripts\python.exe"
$dashboard = Join-Path $projectRoot "dashboard\app.py"
$worker = Join-Path $projectRoot "scripts\run_fyers_paper_worker.py"
$tokenHelper = Join-Path $projectRoot "generate_fyers_token.py"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "CQRP Python environment was not found: $pythonExe"
}

Clear-Host
Write-Host "CQRP Local FYERS + PAPER Launcher" -ForegroundColor Cyan
Write-Host "Data collection and paper-trade simulation only. No FYERS orders are sent." -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Generate a new FYERS daily token"
Write-Host "2. I already saved today's token locally"
$choice = Read-Host "Choose 1 or 2"

if ($choice -eq "1") {
    Write-Host ""
    Write-Host "Complete FYERS login and 2FA. Keep this window open until the token is shown." -ForegroundColor Cyan
    & $pythonExe $tokenHelper
    Write-Host ""
    Write-Host "Copy the token shown above. Do not paste it into this launcher." -ForegroundColor Yellow
} elseif ($choice -ne "2") {
    throw "Choose either 1 or 2."
}

Write-Host ""
Write-Host "Starting the local dashboard..." -ForegroundColor Cyan
$dashboardProcess = Start-Process -FilePath $pythonExe -WorkingDirectory $projectRoot -PassThru -ArgumentList @("-m", "streamlit", "run", $dashboard)
Start-Sleep -Seconds 5
Start-Process "http://localhost:8501"

Write-Host ""
Write-Host "In the dashboard: open Configuration > Fyers, paste today's token, and click Save Fyers." -ForegroundColor Yellow
Read-Host "Press Enter here only after the token has been saved locally"

Write-Host "Starting the 60-second FYERS PAPER worker..." -ForegroundColor Cyan
$workerCommand = "& '$pythonExe' '$worker' --interval-seconds 60"
$workerProcess = Start-Process -FilePath "powershell.exe" -WorkingDirectory $projectRoot -PassThru -ArgumentList @("-NoExit", "-Command", $workerCommand)

Write-Host ""
Write-Host "CQRP is running locally." -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8501"
Write-Host "Dashboard process ID: $($dashboardProcess.Id)"
Write-Host "Worker process ID: $($workerProcess.Id)"
Write-Host "The worker captures only during NSE weekday hours, 09:15-15:30 IST."
Write-Host "To stop it, close the worker PowerShell window and stop the Streamlit process."
Read-Host "Press Enter to close this launcher"
