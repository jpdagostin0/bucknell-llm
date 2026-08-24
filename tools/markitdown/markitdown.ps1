$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $toolRoot ".venv\Scripts\markitdown.exe"

if (-not (Test-Path $executable)) {
    throw "MarkItDown is not installed. Run .\tools\markitdown\install.ps1 first."
}

& $executable @args
exit $LASTEXITCODE
