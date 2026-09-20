[CmdletBinding()]
param(
    [switch]$SkipBrowser
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot

function Add-PythonCandidate {
    param(
        [System.Collections.Generic.List[object]]$List,
        [string]$Path,
        [string[]]$Arguments = @()
    )

    if ($Path -and (Test-Path -LiteralPath $Path)) {
        $List.Add([pscustomobject]@{ Path = $Path; Arguments = $Arguments })
    }
}

$pythonCandidates = [System.Collections.Generic.List[object]]::new()
Add-PythonCandidate $pythonCandidates (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe')
Add-PythonCandidate $pythonCandidates (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe')

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) { Add-PythonCandidate $pythonCandidates $pyLauncher.Source @('-3.12') }

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) { Add-PythonCandidate $pythonCandidates $pythonCommand.Source }

$selectedPython = $null
foreach ($candidate in $pythonCandidates) {
    try {
        $version = (& $candidate.Path @($candidate.Arguments) --version 2>&1 | Out-String).Trim()
        if ($LASTEXITCODE -eq 0 -and $version -match '^Python 3\.(11|12|13)') {
            if ($candidate.Arguments.Count -eq 0) {
                $selectedPython = $candidate.Path
            } else {
                $selectedPython = $candidate.Path
                $selectedPythonArgs = $candidate.Arguments
            }
            Write-Host "Using $version from $($candidate.Path)"
            break
        }
    } catch {
        continue
    }
}

if (-not $selectedPython) {
    throw 'Python 3.11+ was not found. Install Python 3.12 from python.org or run: winget install --id Python.Python.3.12 -e --scope user'
}

$venv = Join-Path $repoRoot 'services\backend\.venv'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host 'Creating services/backend/.venv ...'
    & $selectedPython @($selectedPythonArgs) -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'Python could not create services/backend/.venv.' }
}

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    throw 'pnpm was not found. Install Node.js 20+ and pnpm 9+ before running setup.'
}

Write-Host 'Installing backend dependencies ...'
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Backend pip bootstrap failed.' }
& $venvPython -m pip install -e 'services/backend[dev]'
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

Write-Host 'Installing frontend dependencies ...'
pnpm install --frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }

if (-not $SkipBrowser) {
    Write-Host 'Installing Playwright Chromium ...'
    pnpm --filter web exec playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw 'Playwright Chromium installation failed.' }
}

Write-Host "Setup complete. Use .\scripts\verify.ps1 to run the complete release gate."
