$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "gradescope.py"

if (-not (Test-Path $python)) {
    throw "gradescope is not installed. Run .\tools\gradescope\install.ps1 first."
}

& $python $script @args
exit $LASTEXITCODE
