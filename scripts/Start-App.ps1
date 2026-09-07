param([switch]$NewUnlockCode, [switch]$NoBuild, [switch]$WithSpeech, [string]$DockerPath)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not $DockerPath) {
    $taskDocker = Get-Command docker -ErrorAction SilentlyContinue
    if ($taskDocker) { $DockerPath = $taskDocker.Source }
    else {
        $taskCandidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'),
            (Join-Path $env:ProgramFiles 'Docker/Docker/resources/bin/docker.exe')
        )
        $DockerPath = $taskCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
}
if (-not $DockerPath) { throw 'Install Docker Desktop, then open it and start its Linux engine.' }
$taskEngine = & $DockerPath info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Open Docker Desktop and wait for its Linux engine, then run this script again.' }
if ($taskEngine -ne 'linux') { throw 'Switch Docker Desktop to Linux containers, then run this script again.' }
if (-not (Test-Path -LiteralPath '.local/services.env')) {
    & "$PSScriptRoot/Initialize-Services.ps1"
}
$taskArguments = @('compose', '--env-file', '.local/services.env', '--profile', 'app')
if ($WithSpeech) {
    if (-not (Test-Path -LiteralPath '.local/models/faster-whisper-small.en/model.bin')) {
        throw 'Provision the speech model with scripts/Provision-Speech.ps1 before using -WithSpeech.'
    }
    $taskArguments += @('--profile', 'speech')
}
$taskArguments += @('up', '-d', '--wait', '--wait-timeout', '120')
if (-not $NoBuild) { $taskArguments += '--build' }
& $DockerPath @taskArguments
if ($LASTEXITCODE -ne 0) { throw 'The app did not finish starting. Inspect the container status; existing data volumes were retained.' }
if ($NewUnlockCode) {
    & $DockerPath compose --env-file .local/services.env exec -T api python -m notetaker.manage unlock
    if ($LASTEXITCODE -ne 0) { throw 'The app started but a new workspace code could not be created.' }
}
Write-Output 'Open http://127.0.0.1:3000. Services continue running in Docker after this script exits.'
if ($NewUnlockCode) { Write-Output 'Paste the one-use code from .local/unlock-code.txt. Previous sessions were revoked; courses remain saved.' }
else { Write-Output 'If the workspace is locked, rerun with -NewUnlockCode to create a new one-use code.' }
