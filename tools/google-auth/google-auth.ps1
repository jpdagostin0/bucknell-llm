$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "google_auth.py"

if (-not (Test-Path $python)) {
    throw "google-auth is not installed. Run .\tools\google-auth\install.ps1 first."
}

$env:PYTHONPATH = $toolRoot
& $python $script @args
exit $LASTEXITCODE
