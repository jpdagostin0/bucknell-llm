$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $toolRoot "linear_cli.js"
$nodeRecord = Join-Path $toolRoot "state\node-path.txt"

if (-not (Test-Path (Join-Path $toolRoot "node_modules\@linear\sdk"))) {
    throw "linear is not installed. Run .\tools\linear\install.ps1 first."
}

function Find-Node {
    if (Test-Path $nodeRecord) {
        $recorded = (Get-Content -Path $nodeRecord -Raw).Trim()
        if ($recorded -and (Test-Path $recorded)) {
            return $recorded
        }
    }
    $command = Get-Command node -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $candidates = @(
        Join-Path $env:USERPROFILE ".unsloth\node\node.exe"
        Join-Path $env:USERPROFILE "miniconda3\envs\agi\node.exe"
        Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe"
        Join-Path ${env:ProgramFiles} "nodejs\node.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    throw "Node.js 18+ is required. Run .\tools\linear\install.ps1 first."
}

$node = Find-Node
& $node $script @args
exit $LASTEXITCODE
