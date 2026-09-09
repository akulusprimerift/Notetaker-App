$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$directory = Join-Path $root '.local/native-vendor'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$archivePath = Join-Path $directory 'ollama-windows-amd64.zip'
$expected = '52CB36A62E7E501F61514F60212DEC7117B6C098811357585E02FFFE32D2FCD7'
if (-not (Test-Path -LiteralPath $archivePath)) {
    Invoke-WebRequest 'https://github.com/ollama/ollama/releases/download/v0.33.3/ollama-windows-amd64.zip' -OutFile $archivePath
}
if ((Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash -ne $expected) { throw 'Bundled runtime checksum mismatch' }
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
$destination = [IO.Path]::GetFullPath((Join-Path $directory 'ollama'))
try {
    foreach ($entry in $archive.Entries) {
        # CPU runtime only. Keep notices; no GPU driver dependency or model weights.
        if ($entry.FullName.EndsWith('/') -or $entry.FullName -match '^lib/ollama/(cuda_v\d+|vulkan)/') { continue }
        $target = [IO.Path]::GetFullPath((Join-Path $destination $entry.FullName))
        if (-not $target.StartsWith($destination + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe vendor archive path' }
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $target, $true)
    }
} finally { $archive.Dispose() }
uv run --no-project python scripts/native_notices.py
if ($LASTEXITCODE) { throw 'Dependency notice collection failed' }
$notices = Join-Path $directory 'notices'
Invoke-WebRequest 'https://raw.githubusercontent.com/ollama/ollama/v0.33.3/LICENSE' -OutFile (Join-Path $notices 'OLLAMA-LICENSE.txt')
Invoke-WebRequest 'https://www.gnu.org/licenses/lgpl-3.0.txt' -OutFile (Join-Path $notices 'LGPL-3.0.txt')
Invoke-WebRequest 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile (Join-Path $notices 'GPL-3.0.txt')
