$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bin = Join-Path $toolRoot "bin"
$version = "v2.3.1"
$assetName = "ls-lint-windows-amd64.exe"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is required. Install gh, then rerun this script."
}

New-Item -ItemType Directory -Force -Path $bin | Out-Null
gh release download $version --repo loeffel-io/ls-lint --pattern $assetName --dir $bin --clobber
if ($LASTEXITCODE -ne 0) {
    throw "Failed to download ls-lint $version."
}

Write-Host "ls-lint $version installed in $bin"
Write-Host "Run .\tools\ls-lint\ls-lint.ps1 --help to verify it."
