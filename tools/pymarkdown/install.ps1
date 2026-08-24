$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the PyMarkdown virtual environment."
}

uv pip install --python $python "pymarkdownlnt==0.9.39" "pyyaml==6.0.3"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install PyMarkdown."
}

Write-Host "PyMarkdown installed in $environment"
Write-Host "Run .\tools\pymarkdown\pymarkdown.ps1 version to verify it."
