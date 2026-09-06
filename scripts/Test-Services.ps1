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
$env:NOTETAKER_DATABASE_URL="postgresql+psycopg://notetaker:$($taskValues.POSTGRES_PASSWORD)@127.0.0.1:5432/notetaker"
$env:NOTETAKER_TEST_DATABASE_URL=$env:NOTETAKER_DATABASE_URL
$env:NOTETAKER_PREVIEW='false'
$env:S3_ACCESS_KEY=$taskValues.S3_ACCESS_KEY
$env:S3_SECRET_KEY=$taskValues.S3_SECRET_KEY
$env:PYTHONPATH='apps/api'
& .venv/Scripts/python.exe -m notetaker.verify_services
if ($LASTEXITCODE -ne 0) { throw 'Real service probe failed. Do not mark M01 services verified.' }
& .venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL integration tests failed.' }
Write-Output 'Real PostgreSQL application tests and synthetic object/broker probes passed. Capture durability still requires M02.'
