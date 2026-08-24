$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the pypdf virtual environment."
}

uv pip install --python $python "pypdf==6.16.1"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install pypdf."
}

Write-Host "pypdf installed in $environment"
