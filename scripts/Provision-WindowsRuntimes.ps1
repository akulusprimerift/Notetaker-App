# Build-machine provisioning only. Downloads executables, never student models.
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskSources = @(
    @{ File='.local/windows-runtime-vendor/postgresql-17.11.zip'; Url='https://sbp.enterprisedb.com/getfile.jsp?fileid=1260491'; Hash='4b8db0930c38f6ef845db919551dedda3b6b845aeb0927b3d79a6e8e9e4537cf' },
    @{ File='.local/windows-runtime-vendor/seaweed-4.47.zip'; Url='https://github.com/seaweedfs/seaweedfs/releases/download/4.47/windows_amd64.zip'; Hash='8809359079e62fcd60574ff661449160899622c52072f3f569d346669079efe9' },
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
