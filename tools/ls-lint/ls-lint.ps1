$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $toolRoot "bin\ls-lint-windows-amd64.exe"

if (-not (Test-Path $executable)) {
    throw "ls-lint is not installed. Run .\tools\ls-lint\install.ps1 first."
}

& $executable @args
exit $LASTEXITCODE
