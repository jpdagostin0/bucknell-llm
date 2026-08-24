$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"
$script = Join-Path $toolRoot "example_tool.py"

if (-not (Test-Path $python)) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "example-tool is not installed. Run .\tools\tool-template\install.ps1 first."
    }
    $python = $command.Source
}

& $python $script @args
exit $LASTEXITCODE
