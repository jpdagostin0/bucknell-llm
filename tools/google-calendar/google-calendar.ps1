$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "google_calendar.py"

if (-not (Test-Path $python)) {
    throw "google-calendar is not installed. Run .\tools\google-calendar\install.ps1 first."
}

$env:PYTHONPATH = Join-Path $vaultRoot "tools\google-auth"
& $python $script @args
exit $LASTEXITCODE
