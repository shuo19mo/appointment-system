[CmdletBinding()]
param(
  [switch]$Force,
  [switch]$Run,
  [switch]$NoVerify,
  [switch]$Test
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir '..\..\..\..')
Set-Location $ProjectRoot

function Find-Python {
  $candidates = @()
  if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($version in '3.13','3.12','3.11') {
      try {
        $path = & py "-$version" -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $path) { $candidates += $path.Trim() }
      } catch { }
    }
  }
  if (Get-Command python -ErrorAction SilentlyContinue) { $candidates += (Get-Command python).Source }
  foreach ($candidate in $candidates) {
    $minor = [int](& $candidate -c "import sys; print(sys.version_info.minor)")
    $major = [int](& $candidate -c "import sys; print(sys.version_info.major)")
    if ($major -eq 3 -and $minor -ge 11) { return $candidate }
  }
  return $null
}

$Python = Find-Python
if (-not $Python) { throw 'Python 3.11+ is required.' }
if ($Force -and (Test-Path .venv)) { Remove-Item -Recurse -Force .venv }
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (Test-Path $VenvPython) {
  $venvSupported = & $VenvPython -c "import sys; print(int(sys.version_info >= (3, 11)))" 2>$null
  if ($venvSupported -ne '1') { Remove-Item -Recurse -Force .venv }
}
if (-not (Test-Path $VenvPython)) { & $Python -m venv .venv }

& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPython -m pip install -r requirements.txt
if ($Test) { & $VenvPython -m pip install -r requirements-dev.txt }

if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Warning 'Created .env. Set DEEPSEEK_API_KEY before verification.'
}
New-Item -ItemType Directory -Force -Path data | Out-Null
if (-not $NoVerify) { & $VenvPython (Join-Path $ScriptDir 'verify_env.py') }
if ($Test) {
  & $VenvPython -m pytest -q
  & $VenvPython -m compileall -q agents api config db services web app.py
}

Write-Host '[OK] Education scheduling environment is ready.' -ForegroundColor Green
if ($Run) { & $VenvPython -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload }
