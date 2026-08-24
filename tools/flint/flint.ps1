$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $toolRoot "bin\flint.exe"

if (-not (Test-Path $executable)) {
    throw "Flint is not installed. Run .\tools\flint\install.ps1 first."
}

& $executable @args
exit $LASTEXITCODE
