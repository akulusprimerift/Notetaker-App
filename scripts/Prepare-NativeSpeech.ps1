$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$env:HF_HUB_DISABLE_XET = '1'
@'
from huggingface_hub import snapshot_download
snapshot_download('Systran/faster-whisper-small.en', revision='d1d751a5f8271d482d14ca55d9e2deeebbae577f',
    local_dir='.local/models/faster-whisper-small.en',
    allow_patterns=['config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt'])
'@ | uv run --no-project python -
if ($LASTEXITCODE) { throw 'Bundled speech model provisioning failed.' }
