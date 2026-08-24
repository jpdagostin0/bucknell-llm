$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$state = Join-Path $toolRoot "state"
$nodeRecord = Join-Path $state "node-path.txt"

function Find-Node {
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
    throw "Node.js 18+ is required. Install Node, then rerun this script."
}

function Find-Npm([string]$nodePath) {
    $command = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    $sibling = Join-Path (Split-Path -Parent $nodePath) "npm.cmd"
    if (Test-Path $sibling) {
        return $sibling
    }
    throw "npm was not found next to $nodePath."
}

$node = Find-Node
$npm = Find-Npm $node
New-Item -ItemType Directory -Force -Path $state | Out-Null
Set-Content -Path $nodeRecord -Value $node -Encoding utf8

Push-Location $toolRoot
try {
    & $npm install --omit=dev
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Linear CLI dependencies."
    }
}
finally {
    Pop-Location
}

Write-Host "linear installed with $node"
Write-Host "Run .\tools\linear\linear.ps1 commands to verify it."
