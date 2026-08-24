$ErrorActionPreference = "Stop"

$toolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$executable = Join-Path $toolRoot ".venv\Scripts\moodle-dl.exe"
$state = Join-Path $toolRoot "state"

if (-not (Test-Path $executable)) {
    throw "Moodle-DL is not installed. Run .\tools\moodle-dl\install.ps1 first."
}

New-Item -ItemType Directory -Force -Path $state | Out-Null

$moodleArguments = @($args) + @("--path", $state)
& $executable @moodleArguments
exit $LASTEXITCODE
