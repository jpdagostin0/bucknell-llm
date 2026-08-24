$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$bin = Join-Path $toolRoot "bin"
$version = "v0.0.6"
$archiveName = "flint_0.0.6_Windows_x86_64.zip"
$archive = Join-Path $toolRoot $archiveName

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI is required. Install gh, then rerun this script."
}

New-Item -ItemType Directory -Force -Path $bin | Out-Null
gh release download $version --repo hay-kot/flint --pattern $archiveName --dir $toolRoot --clobber
if ($LASTEXITCODE -ne 0) {
    throw "Failed to download Flint $version."
}

Expand-Archive -LiteralPath $archive -DestinationPath $bin -Force
Remove-Item -LiteralPath $archive

$executable = Get-ChildItem -LiteralPath $bin -Filter "flint.exe" -Recurse | Select-Object -First 1
if (-not $executable) {
    throw "The Flint archive did not contain flint.exe."
}
if ($executable.DirectoryName -ne $bin) {
    Copy-Item -LiteralPath $executable.FullName -Destination (Join-Path $bin "flint.exe") -Force
}

Write-Host "Flint $version installed in $bin"
Write-Host "Run .\tools\flint\flint.ps1 --help to verify it."
