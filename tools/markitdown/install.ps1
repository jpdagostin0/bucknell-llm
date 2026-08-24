$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the MarkItDown virtual environment."
}

uv pip install --python $python "markitdown[pdf,docx]==0.1.7"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install MarkItDown."
}

Write-Host "MarkItDown installed in $environment"
Write-Host "Run .\tools\markitdown\markitdown.ps1 --help to verify it."
