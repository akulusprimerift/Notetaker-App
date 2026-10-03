param([switch]$Restart, [string]$DockerPath = 'docker')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskEnv = Join-Path $taskRoot '.local/services.env'
if (-not (Test-Path -LiteralPath $taskEnv)) { throw 'Run Initialize-Services.ps1 first.' }
$taskValues = @{}
foreach ($taskLine in (Get-Content -LiteralPath $taskEnv)) {
    $taskParts = $taskLine -split '=',2
    if ($taskParts.Count -eq 2) { $taskValues[$taskParts[0]] = $taskParts[1] }
}
$taskEnvironmentNames = @('NOTETAKER_DATABASE_URL','NOTETAKER_TEST_DATABASE_URL','S3_ACCESS_KEY',
    'S3_SECRET_KEY','NOTETAKER_S3_ACCESS_KEY','NOTETAKER_S3_SECRET_KEY','PYTHONPATH')
$taskPreviousEnvironment = @{}
foreach ($taskName in $taskEnvironmentNames) {
    $taskPreviousEnvironment[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process')
}
$taskProbe = Join-Path $taskRoot ('.local/sqlite/service-probe-' + [guid]::NewGuid().ToString('N') + '.sqlite3')
New-Item -ItemType Directory -Path (Split-Path -Parent $taskProbe) -Force | Out-Null
$env:NOTETAKER_DATABASE_URL='sqlite:///' + ($taskProbe -replace '\\','/')
$env:NOTETAKER_TEST_DATABASE_URL=$null
$env:S3_ACCESS_KEY=$taskValues.S3_ACCESS_KEY
$env:S3_SECRET_KEY=$taskValues.S3_SECRET_KEY
$env:NOTETAKER_S3_ACCESS_KEY=$taskValues.S3_ACCESS_KEY
$env:NOTETAKER_S3_SECRET_KEY=$taskValues.S3_SECRET_KEY
$env:PYTHONPATH='apps/api'
try {
& uv run --no-project --python .venv/Scripts/python.exe python -m notetaker.verify_services
if ($LASTEXITCODE -ne 0) { throw 'SQLite and real object/broker service probe failed.' }
$taskTestRoot = Join-Path $taskRoot ('.cache/service-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTestRoot | Out-Null
& uv run --no-project --python .venv/Scripts/python.exe python -m pytest -q --tb=short --basetemp "$taskTestRoot/temp" -o "cache_dir=$taskTestRoot/cache"
if ($LASTEXITCODE -ne 0) { throw 'SQLite backend tests failed.' }
if ($Restart) {
    & uv run --no-project --python .venv/Scripts/python.exe python -m notetaker.verify_restart --docker $DockerPath
    if ($LASTEXITCODE -ne 0) { throw 'Persistent-volume restart verification failed.' }
}
Write-Output 'SQLite backend tests and synthetic object/broker probes passed. Device-failure and real-lecture qualification remain separate.'
} finally {
    Remove-Item -LiteralPath $taskProbe -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath ($taskProbe + '-wal') -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath ($taskProbe + '-shm') -Force -ErrorAction SilentlyContinue
    foreach ($taskName in $taskEnvironmentNames) {
        [Environment]::SetEnvironmentVariable($taskName, $taskPreviousEnvironment[$taskName], 'Process')
    }
}
