$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the gmail virtual environment."
}

uv pip install --python $python `
    "simplegmail==5.0.0" `
    "PyYAML==6.0.2" `
    "google-auth==2.40.3" `
    "google-auth-oauthlib==1.2.2"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install gmail dependencies."
}

Write-Host "gmail installed in $environment"
Write-Host "Run .\tools\gmail\gmail.ps1 commands to verify it."
