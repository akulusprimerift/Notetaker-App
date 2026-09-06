param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$repositoryPath = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$docsPath = Join-Path $repositoryPath 'docs'
$markdownFiles = @(
    Get-Item -LiteralPath (Join-Path $repositoryPath 'README.md')
    Get-ChildItem -LiteralPath $docsPath -Filter '*.md' -Recurse -File
)
$linkCount = 0

foreach ($markdownFile in $markdownFiles) {
    $markdownText = Get-Content -LiteralPath $markdownFile.FullName -Raw
    foreach ($linkMatch in [regex]::Matches($markdownText, '\]\(([^)]+)\)')) {
        $linkTarget = $linkMatch.Groups[1].Value.Trim()
        if ($linkTarget -match '^(https?://|mailto:|#)') { continue }
        # Check file existence only; this project currently uses no local heading links.
        $fileTarget = [uri]::UnescapeDataString(($linkTarget -split '#', 2)[0].Trim('<', '>'))
        $targetPath = Join-Path $markdownFile.DirectoryName $fileTarget
        if (-not (Test-Path -LiteralPath $targetPath -PathType Leaf)) {
            throw "Broken local file link in $($markdownFile.Name): $linkTarget"
        }
        $linkCount++
    }
}

$brief = Get-Content -LiteralPath (Join-Path $docsPath 'product/phase-1-product-brief.md') -Raw
$experience = Get-Content -LiteralPath (Join-Path $docsPath 'product/phase-2-student-experience.md') -Raw
$scenarios = Get-Content -LiteralPath (Join-Path $docsPath 'product/phase-2-acceptance-scenarios.md') -Raw
$requiredIds = @([regex]::Matches($brief, '(?m)^\| ([A-Z]+-\d{2}) \|') | ForEach-Object { $_.Groups[1].Value })
$screenIds = @([regex]::Matches($experience, '(?m)^\| (S\d+) [^|]+\|') | ForEach-Object { $_.Groups[1].Value })
$scenarioRows = @([regex]::Matches($scenarios, '(?m)^\| (UX-\d{2}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|\r?$'))
if ($requiredIds.Count -eq 0 -or $screenIds.Count -eq 0 -or $scenarioRows.Count -eq 0) {
    throw 'Expected requirement, screen, or scenario tables were not found.'
}

$seenScenarios = @{}
$coveredRequirements = @{}
$coveredScreens = @{}
foreach ($scenarioRow in $scenarioRows) {
    $scenarioId = $scenarioRow.Groups[1].Value
    if ($seenScenarios.ContainsKey($scenarioId)) { throw "Duplicate scenario: $scenarioId" }
    $seenScenarios[$scenarioId] = $true
    foreach ($requirementId in ($scenarioRow.Groups[2].Value -split ',' | ForEach-Object { $_.Trim() })) {
        if ($requirementId -notin $requiredIds) { throw "Unknown requirement in ${scenarioId}: $requirementId" }
        $coveredRequirements[$requirementId] = $true
    }
    foreach ($screenId in ($scenarioRow.Groups[3].Value -split ',' | ForEach-Object { $_.Trim() })) {
        if ($screenId -notin $screenIds) { throw "Unknown screen in ${scenarioId}: $screenId" }
        $coveredScreens[$screenId] = $true
    }
    if ([string]::IsNullOrWhiteSpace($scenarioRow.Groups[4].Value) -or [string]::IsNullOrWhiteSpace($scenarioRow.Groups[5].Value)) {
        throw "Missing trigger or expected outcome in $scenarioId"
    }
}

$declaredScenarioCount = ([regex]::Matches($scenarios, '(?m)^\| UX-')).Count
if ($declaredScenarioCount -ne $scenarioRows.Count) { throw 'A scenario row is malformed.' }
foreach ($requirementId in $requiredIds) {
    if (-not $coveredRequirements.ContainsKey($requirementId)) { throw "Uncovered requirement: $requirementId" }
}
foreach ($screenId in $screenIds) {
    if (-not $coveredScreens.ContainsKey($screenId)) { throw "Uncovered screen: $screenId" }
}

Write-Output "PASS: $($markdownFiles.Count) planning Markdown files; $linkCount local file links resolve."
Write-Output "PASS: $($scenarioRows.Count) unique scenarios cover $($requiredIds.Count) core requirements and $($screenIds.Count) screens."
Write-Output 'Scope: file links and structural coverage only; application behavior and note quality are not tested.'
