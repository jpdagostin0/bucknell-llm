$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the gradescope virtual environment."
}

uv pip install --python $python "gradescopeapi==1.8.1" "PyYAML==6.0.2"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install gradescopeapi."
}

Write-Host "gradescope installed in $environment"
Write-Host "Run .\tools\gradescope\gradescope.ps1 ping to verify cookies from .env.yml."
