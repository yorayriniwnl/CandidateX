<#
.SYNOPSIS
    Starts CandidateX locally (FastAPI backend and Next.js frontend).
#>
[CmdletBinding()]
param(
    [switch]$Dev
)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
Set-Location $repoRoot

# Ensure Node & pnpm are in PATH
$nodePath = "C:\Program Files\nodejs"
$npmPath = "$env:APPDATA\npm"
if (Test-Path $nodePath) {
    $env:PATH = "$nodePath;$npmPath;$env:PATH"
}

# Ensure .env exists
if (-not (Test-Path (Join-Path $repoRoot '.env'))) {
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item (Join-Path $repoRoot '.env.example') (Join-Path $repoRoot '.env')
    $secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    (Get-Content (Join-Path $repoRoot '.env')) -replace 'SECRET_KEY=', "SECRET_KEY=$secret" | Set-Content (Join-Path $repoRoot '.env')
}

$python = Join-Path $repoRoot 'services\backend\.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Error "Virtual environment not found at services\backend\.venv. Run scripts\setup.ps1 first."
    exit 1
}

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "   Candidate Capability Intelligence (CandidateX) " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "[*] Starting FastAPI Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green

$backendProcess = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'cci.main:app', '--app-dir', 'services/backend/src', '--host', '127.0.0.1', '--port', '8000') -PassThru -NoNewWindow

Write-Host "[*] Waiting for backend to become healthy..." -ForegroundColor Yellow
$healthy = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2
        if ($resp.status -eq 'healthy') {
            $healthy = $true
            break
        }
    } catch {}
}

if (-not $healthy) {
    Write-Warning "Backend is still initializing or encountered an issue. Check backend logs."
} else {
    Write-Host "[+] Backend is healthy!" -ForegroundColor Green
}

Write-Host "[*] Starting Next.js Web Frontend on http://localhost:3000 ..." -ForegroundColor Green

if ($Dev) {
    $frontendProcess = Start-Process -FilePath "pnpm" -ArgumentList @('--filter', 'web', 'dev', '--webpack', '--port', '3000') -PassThru -NoNewWindow
} else {
    $frontendProcess = Start-Process -FilePath "pnpm" -ArgumentList @('--filter', 'web', 'start', '--port', '3000') -PassThru -NoNewWindow
}

Write-Host "`nCandidateX is running locally:" -ForegroundColor Cyan
Write-Host "  - Frontend Web UI:    http://localhost:3000" -ForegroundColor White
Write-Host "  - Live Analysis:      http://localhost:3000/analyze" -ForegroundColor White
Write-Host "  - Backend API:        http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  - Swagger API Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  - System Health:      http://127.0.0.1:8000/health" -ForegroundColor White
Write-Host "`nPress Ctrl+C to stop both services." -ForegroundColor DarkGray

try {
    Wait-Process -Id $backendProcess.Id, $frontendProcess.Id
} finally {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
}
