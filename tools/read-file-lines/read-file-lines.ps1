$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$vaultRoot = Resolve-Path (Join-Path $toolRoot "..\..")
$script = Join-Path $toolRoot "read_file_lines.py"
$python = Join-Path $vaultRoot "tools\pymarkdown\.venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    $command = Get-Command python -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Python is required. Run .\tools\pymarkdown\install.ps1 first."
    }
    $python = $command.Source
}

& $python $script @args
exit $LASTEXITCODE
