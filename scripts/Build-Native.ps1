param([switch]$PrepareVendor, [string]$MakeNsis)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
if ($PrepareVendor) { & "$PSScriptRoot/Prepare-NativeVendor.ps1" }
Remove-Item Env:NOTETAKER_DEBUG_CONSOLE -ErrorAction SilentlyContinue
uv run --no-project python -m PyInstaller --noconfirm --distpath .local/native-qualified --workpath .local/native-qualified-build apps/native/notetaker.spec
if ($LASTEXITCODE) { throw 'Native package build failed' }
$bundle = Join-Path $root '.local/native-qualified/Notetaker'
$unexpected = Get-ChildItem -LiteralPath $bundle -Recurse -File | Where-Object { $_.Name -match 'WebEngine|WebView|chrome|electron' }
if ($unexpected) { throw "Browser engine found in native package: $($unexpected.FullName)" }
Copy-Item -LiteralPath 'docs/native-download.md' -Destination (Join-Path $bundle 'READ-ME.md')
Copy-Item -LiteralPath 'apps/api/requirements-native.lock' -Destination (Join-Path $bundle 'dependency-lock.txt')
Compress-Archive -Path "$bundle/*" -DestinationPath .local/native-qualified/Notetaker-Windows-x64.zip -Force
Get-FileHash .local/native-qualified/Notetaker-Windows-x64.zip -Algorithm SHA256 | Format-List
if ($MakeNsis) {
    & $MakeNsis apps/native/installer.nsi
    if ($LASTEXITCODE) { throw 'Installer build failed' }
}
$artifacts = Get-ChildItem .local/native-qualified -File | Where-Object { $_.Extension -in '.zip','.exe' }
$artifacts | ForEach-Object { "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower())  $($_.Name)" } | Set-Content .local/native-qualified/SHA256SUMS.txt
