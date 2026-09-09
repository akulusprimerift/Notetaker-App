param([switch]$NoBuild, [switch]$WithSpeech, [string]$DockerPath, [string]$SpeechModelPath, [string]$WorkspacePath)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if ($WorkspacePath) { $taskRoot = [IO.Path]::GetFullPath($WorkspacePath) }
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
    if ($WorkspacePath) { throw 'The selected workspace must contain its existing .local/services.env configuration.' }
    & "$PSScriptRoot/Initialize-Services.ps1"
}
$taskArguments = @('compose', '--env-file', '.local/services.env', '--profile', 'app')
if ($WithSpeech) {
    if (-not $SpeechModelPath) { $SpeechModelPath = Join-Path $taskRoot '.local/models/faster-whisper-small.en' }
    $SpeechModelPath = [IO.Path]::GetFullPath($SpeechModelPath)
    if (-not (Test-Path -LiteralPath (Join-Path $SpeechModelPath 'model.bin'))) {
        throw 'Provision the speech model with scripts/Provision-Speech.ps1 before using -WithSpeech.'
    }
    $env:NOTETAKER_SPEECH_HOST_PATH = $SpeechModelPath.Replace('\', '/')
    $taskArguments += @('--profile', 'speech')
}
$taskArguments += @('up', '-d', '--wait', '--wait-timeout', '120')
if (-not $NoBuild) { $taskArguments += '--build' }
& $DockerPath @taskArguments
if ($LASTEXITCODE -ne 0) { throw 'The app did not finish starting. Inspect the container status; existing data volumes were retained.' }

Write-Output 'Open http://127.0.0.1:3000. Services continue running in Docker after this script exits.'
