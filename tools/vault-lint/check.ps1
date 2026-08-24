$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$python = Join-Path $vaultRoot "tools\pymarkdown\.venv\Scripts\python.exe"
$pymarkdown = Join-Path $vaultRoot "tools\pymarkdown\.venv\Scripts\pymarkdown.exe"
$flint = Join-Path $vaultRoot "tools\flint\bin\flint.exe"
$lsLint = Join-Path $vaultRoot "tools\ls-lint\bin\ls-lint-windows-amd64.exe"
$validator = Join-Path $toolRoot "validate_vault.py"
$validatorTests = Join-Path $toolRoot "test_validate_vault.py"

$required = @($python, $pymarkdown, $flint, $lsLint, $validator, $validatorTests)
foreach ($executable in $required) {
    if (-not (Test-Path $executable)) {
        throw "Missing linter executable: $executable. Run the corresponding tools/<name>/install.ps1 script."
    }
}

$failed = @()
Push-Location $vaultRoot
try {
    Write-Host "PyMarkdown"
    & $pymarkdown --config .pymarkdown.yml scan --recurse --respect-gitignore .
    if ($LASTEXITCODE -ne 0) {
        $failed += "PyMarkdown"
    }

    Write-Host "Flint"
    $flintOutput = & $flint --config .flint.yml --color=false . 2>&1
    $flintExitCode = $LASTEXITCODE
    $flintOutput | ForEach-Object { Write-Host $_ }
    $flintText = $flintOutput -join [Environment]::NewLine
    if (
        $flintExitCode -ne 0 -or
        $flintText -match "(?m)^\s+\d+:\d+\s+error\s+"
    ) {
        $failed += "Flint"
    }

    Write-Host "Vault integrity"
    & $python $validator .
    if ($LASTEXITCODE -ne 0) {
        $failed += "Vault integrity"
    }

    Write-Host "Rule tests"
    & $python $validatorTests
    if ($LASTEXITCODE -ne 0) {
        $failed += "Rule tests"
    }

    Write-Host "ls-lint"
    & $lsLint --config .ls-lint.yml --workdir .
    if ($LASTEXITCODE -ne 0) {
        $failed += "ls-lint"
    }
}
finally {
    Pop-Location
}

if ($failed.Count -gt 0) {
    Write-Error ("Vault checks failed: " + ($failed -join ", "))
    exit 1
}

Write-Host "All vault checks passed."
