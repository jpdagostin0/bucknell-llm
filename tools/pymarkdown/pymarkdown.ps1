$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $toolRoot ".venv\Scripts\pymarkdown.exe"

if (-not (Test-Path $executable)) {
    throw "PyMarkdown is not installed. Run .\tools\pymarkdown\install.ps1 first."
}

& $executable @args
exit $LASTEXITCODE
