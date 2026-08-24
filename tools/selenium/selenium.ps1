$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "selenium_cli.py"

if (-not (Test-Path $python)) {
    throw "selenium is not installed. Run .\tools\selenium\install.ps1 first."
}

& $python $script @args
exit $LASTEXITCODE
