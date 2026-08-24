$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "extract_pages.py"

if (-not (Test-Path $python)) {
    throw "pypdf is not installed. Run .\tools\pypdf\install.ps1 first."
}

& $python $script @args
exit $LASTEXITCODE
