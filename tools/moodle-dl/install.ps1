$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$environment = Join-Path $toolRoot ".venv"
$python = Join-Path $environment "Scripts\python.exe"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv, then rerun this script."
}

uv venv $environment --python 3.12
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create the Moodle-DL virtual environment."
}

uv pip install --python $python "moodle-dl==2.3.13"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install Moodle-DL."
}

Write-Host "Moodle-DL installed in $environment"
Write-Host "Run .\tools\moodle-dl\moodle-dl.ps1 --help to verify it."
