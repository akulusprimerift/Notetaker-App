param([string]$OutputPath = '.local/synthetic-cs.wav', [int]$Rate = 0)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
# Windows' installed speech synthesizer only; no microphone or external speech service.
$taskVoice = New-Object -ComObject SAPI.SpVoice
$taskStream = New-Object -ComObject SAPI.SpFileStream
$taskStream.Format.Type = 22 # 22.05 kHz, 16-bit, mono PCM.
$taskOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputPath))
try {
    $taskStream.Open($taskOutput,3,$false)
    $taskVoice.AudioOutputStream = $taskStream
    $taskVoice.Rate = $Rate
    $taskText = Get-Content -Raw -LiteralPath 'evaluations/fixtures/speech-cs-synthetic.txt'
    [void]$taskVoice.Speak($taskText)
    $taskText | Set-Content -LiteralPath ($taskOutput + '.txt') -NoNewline
    @{ source='Windows SAPI'; voice=$taskVoice.Voice.GetDescription(); rate=$Rate; microphone=$false } |
        ConvertTo-Json | Set-Content -LiteralPath ($taskOutput + '.json')
} finally {
    $taskStream.Close()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskStream)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($taskVoice)
}
Write-Output "Generated synthetic speech at $taskOutput. No microphone accessed."
