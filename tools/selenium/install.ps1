$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the Selenium virtual environment."
}

uv pip install --python $python "mcp-server-selenium==0.1.8" "mcp[cli]<2"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install mcp-server-selenium."
}

Write-Host "Selenium installed in $environment"
Write-Host "Run .\tools\selenium\selenium.ps1 ping to verify the published package."
