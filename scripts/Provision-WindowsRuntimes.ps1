# Build-machine provisioning only. Downloads executables, never student models.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskSources = @(
    @{ File='.local/native-vendor/ollama-windows-amd64.zip'; Url='https://github.com/ollama/ollama/releases/download/v0.33.3/ollama-windows-amd64.zip'; Hash='52cb36a62e7e501f61514f60212dec7117b6c098811357585e02fffe32d2fcd7' }
)
foreach ($taskSource in $taskSources) {
    $taskPath = Join-Path $taskRoot $taskSource.File
    New-Item -ItemType Directory -Force (Split-Path -Parent $taskPath) | Out-Null
    if (-not (Test-Path -LiteralPath $taskPath)) {
        Invoke-WebRequest $taskSource.Url -OutFile $taskPath
    }
    if ((Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash -ne $taskSource.Hash) {
        throw 'Runtime archive integrity check failed. The file was retained for inspection.'
    }
    Write-Output ('Verified ' + $taskSource.File)
}
