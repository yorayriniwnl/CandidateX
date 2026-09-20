[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

function Invoke-NativeGate {
    param(
        [string]$Name,
        [string]$Command,
        [string[]]$Arguments
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

$venvPython = Join-Path $repoRoot 'services\backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw 'services/backend/.venv is missing. Run .\scripts\setup.ps1 first.'
}

$pnpm = Get-Command pnpm -ErrorAction Stop
$env:CCI_PYTHON = $venvPython
$env:Path = "$(Split-Path -Parent $venvPython);$env:Path"

Write-Host "`n=== Compose deployment contract ===" -ForegroundColor Cyan
$composePath = Join-Path $repoRoot 'docker-compose.yml'
$composeText = Get-Content -LiteralPath $composePath -Raw
if ($composeText -notmatch '(?m)^\s*CCI_API_URL:\s*http://backend:8000\s*$') {
    throw 'docker-compose.yml must route the server-side bridge to http://backend:8000.'
}
if ($composeText -notmatch '(?m)^\s*NEXT_PUBLIC_API_URL:\s*http://localhost:8000\s*$') {
    throw 'docker-compose.yml must retain the browser-facing NEXT_PUBLIC_API_URL.'
}
if ($composeText -notmatch '(?ms)^\s*depends_on:\s*\r?\n\s*backend:\s*\r?\n\s*condition:\s*service_healthy') {
    throw 'docker-compose.yml must make the web service wait for a healthy backend.'
}
Write-Host 'Compose bridge, browser URL, and health dependency are configured.' -ForegroundColor Green

Invoke-NativeGate 'Backend test suite' $venvPython @('-m', 'pytest', 'services/backend/tests', '-q')
Invoke-NativeGate 'Next.js route type generation' $pnpm.Source @('--filter', 'web', 'exec', 'next', 'typegen')
Invoke-NativeGate 'Frontend TypeScript check' $pnpm.Source @('--filter', 'web', 'exec', 'tsc', '--noEmit', '--incremental', 'false')
Invoke-NativeGate 'Next.js production build' $pnpm.Source @('--filter', 'web', 'build')
Invoke-NativeGate 'Playwright browser suite' $pnpm.Source @('--filter', 'web', 'test')

Write-Host "`nAll local release gates passed." -ForegroundColor Green
