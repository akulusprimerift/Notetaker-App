param([string]$UvPath = "$env:USERPROFILE/.local/bin/uv.exe")
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Set up the project Python environment first; see the M01 runbook.' }
& $UvPath --cache-dir .cache/uv pip install --python .venv/Scripts/python.exe --require-hashes -r apps/api/requirements-speech.lock
if ($LASTEXITCODE -ne 0) { throw 'Speech dependency installation failed.' }
$env:HF_HUB_DISABLE_XET='1'
@'
from huggingface_hub import snapshot_download
snapshot_download('Systran/faster-whisper-small.en', revision='d1d751a5f8271d482d14ca55d9e2deeebbae577f',
    local_dir='.local/models/faster-whisper-small.en',
    allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*'])
print('Pinned English speech model provisioned locally. No lecture content was sent.')
'@ | & .venv/Scripts/python.exe -
if ($LASTEXITCODE -ne 0) { throw 'Model provisioning failed. Recording remains independent of the speech model.' }
