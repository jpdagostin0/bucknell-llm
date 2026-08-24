$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the google-auth virtual environment."
}

uv pip install --python $python `
    "PyYAML==6.0.2" `
    "google-auth==2.40.3" `
    "google-auth-oauthlib==1.2.2" `
    "google-auth-httplib2==0.2.0" `
    "google-api-python-client==2.179.0"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install google-auth dependencies."
}

Write-Host "google-auth installed in $environment"
Write-Host "Run .\tools\google-auth\google-auth.ps1 commands to verify it."
