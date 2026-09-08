param([string]$PythonPath, [switch]$NewUnlockCode)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not $PythonPath) { $PythonPath = Join-Path $taskRoot '.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $PythonPath)) { throw 'Create the Python environment first; see docs/implementation/phase-6-m01.md.' }
if (-not (Test-Path -LiteralPath 'node_modules/next')) { throw 'Install frontend dependencies with bun install --frozen-lockfile --ignore-scripts first.' }
foreach ($taskPort in @(3000,8010)) {
    $taskProbe = [Net.Sockets.TcpClient]::new()
    try { $taskProbe.Connect('127.0.0.1',$taskPort); throw "Port $taskPort is already occupied. Stop the earlier preview before starting another." }
    catch [Net.Sockets.SocketException] { }
    finally { $taskProbe.Dispose() }
}
New-Item -ItemType Directory -Path .local -Force | Out-Null
$env:NOTETAKER_PREVIEW='true'
$env:NOTETAKER_DATABASE_URL='sqlite:///.local/workspace.db'
$env:PYTHONPATH='apps/api'
$env:API_ORIGIN='http://127.0.0.1:8010'
$env:NEXT_TELEMETRY_DISABLED='1'
& $PythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed; services were not started.' }
if ($NewUnlockCode -or -not (Test-Path -LiteralPath '.local/unlock-code.txt')) {
    & $PythonPath -m notetaker.manage unlock
    if ($LASTEXITCODE -ne 0) { throw 'Unlock setup failed.' }
}
$taskApi = Start-Process -FilePath $PythonPath -ArgumentList @('-m','uvicorn','notetaker.main:app','--app-dir','apps/api','--host','127.0.0.1','--port','8010','--no-access-log') -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput '.local/api.stdout.log' -RedirectStandardError '.local/api.stderr.log'
Write-Output 'Open http://127.0.0.1:3000. A new unlock code is in .local/unlock-code.txt when requested. Ctrl+C stops the preview.'
try { & node node_modules/next/dist/bin/next dev apps/web --hostname 127.0.0.1 --port 3000 }
finally { if (-not $taskApi.HasExited) { Stop-Process -Id $taskApi.Id } }
