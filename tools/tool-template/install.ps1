$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $toolRoot ".venv\Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv (Join-Path $toolRoot ".venv") --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the example-tool virtual environment."
}

Write-Host "example-tool environment is ready. This template has no extra packages."
Write-Host "Run .\tools\tool-template\example-tool.ps1 ping"
