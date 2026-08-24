$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "google_drive.py"

if (-not (Test-Path $python)) {
    throw "google-drive is not installed. Run .\tools\google-drive\install.ps1 first."
}

$env:PYTHONPATH = Join-Path $vaultRoot "tools\google-auth"
& $python $script @args
exit $LASTEXITCODE
