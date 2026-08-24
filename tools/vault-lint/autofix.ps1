$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$pymarkdown = Join-Path $vaultRoot "tools\pymarkdown\.venv\Scripts\pymarkdown.exe"

if (-not (Test-Path $pymarkdown)) {
    throw "PyMarkdown is not installed. Run .\tools\pymarkdown\install.ps1 first."
}

Push-Location $vaultRoot
try {
    & $pymarkdown --config .pymarkdown.yml fix --recurse --respect-gitignore .
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
