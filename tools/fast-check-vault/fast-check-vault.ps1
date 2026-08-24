$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$python = Join-Path $vaultRoot "tools\pymarkdown\.venv\Scripts\python.exe"
$script = Join-Path $toolRoot "fast_check_vault.py"
$installer = Join-Path $vaultRoot "tools\pymarkdown\install.ps1"

if (-not (Test-Path $python)) {
    if (-not (Test-Path $installer)) {
        throw "PyMarkdown is not installed. Run .\tools\pymarkdown\install.ps1 first."
    }
    & $installer
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the PyMarkdown environment used by fast skill runners."
    }
}

$env:PYTHONPATH = Join-Path $vaultRoot "tools\fast-common"
& $python $script @args
exit $LASTEXITCODE
