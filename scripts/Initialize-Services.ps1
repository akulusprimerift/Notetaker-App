$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskLocal = Join-Path $taskRoot '.local'
New-Item -ItemType Directory -Path $taskLocal -Force | Out-Null
$taskEnvFile = Join-Path $taskLocal 'services.env'
$taskS3File = Join-Path $taskLocal 's3.json'
if ((Test-Path -LiteralPath $taskEnvFile) -or (Test-Path -LiteralPath $taskS3File)) {
    throw 'Service credentials already exist. Preserve them; this command never rotates or overwrites them.'
}
function New-LocalSecret { [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24)).ToLowerInvariant() }
$taskPassword = New-LocalSecret
$taskAccess = New-LocalSecret
$taskSecret = New-LocalSecret
@("POSTGRES_PASSWORD=$taskPassword", "S3_ACCESS_KEY=$taskAccess", "S3_SECRET_KEY=$taskSecret") | Set-Content -LiteralPath $taskEnvFile -Encoding utf8
@{identities=@(@{name='notetaker-local';credentials=@(@{accessKey=$taskAccess;secretKey=$taskSecret});actions=@('Admin','Read','Write','List','Tagging')})} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $taskS3File -Encoding utf8
Write-Output 'Created private local service configuration in .local. No credentials were printed.'
