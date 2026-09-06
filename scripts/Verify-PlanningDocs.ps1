param(
    [string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = 'Stop'
$repositoryPath = (Resolve-Path -LiteralPath $RepositoryRoot).Path
$docsPath = Join-Path $repositoryPath 'docs'
$markdownFiles = @(
    Get-Item -LiteralPath (Join-Path $repositoryPath 'README.md')
    Get-Item -LiteralPath (Join-Path $repositoryPath 'multimodal_academic_learning_system_spec.md')
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

$architecture = Get-Content -LiteralPath (Join-Path $docsPath 'architecture/phase-3-architecture.md') -Raw
$architectureVerification = Get-Content -LiteralPath (Join-Path $docsPath 'architecture/phase-3-verification.md') -Raw
$contractIds = @([regex]::Matches($architecture, '(?m)^## (ARC-\d{2}):') | ForEach-Object { $_.Groups[1].Value })
if ($contractIds.Count -eq 0 -or ($contractIds | Select-Object -Unique).Count -ne $contractIds.Count) {
    throw 'Missing or duplicate architecture contract IDs.'
}
$architectureRows = @([regex]::Matches($architectureVerification, '(?m)^\| (UX-\d{2}(?:, UX-\d{2})*) \| ([^|]+) \| ([^|]+) \|\r?$'))
if ($architectureRows.Count -eq 0 -or ([regex]::Matches($architectureVerification, '(?m)^\| UX-')).Count -ne $architectureRows.Count) {
    throw 'Missing or malformed architecture mapping rows.'
}
$mappedScenarios = @{}
$mappedContracts = @{}
foreach ($architectureRow in $architectureRows) {
    foreach ($scenarioId in ($architectureRow.Groups[1].Value -split ', ')) {
        if (-not $seenScenarios.ContainsKey($scenarioId)) { throw "Unknown mapped scenario: $scenarioId" }
        if ($mappedScenarios.ContainsKey($scenarioId)) { throw "Duplicate mapped scenario: $scenarioId" }
        $mappedScenarios[$scenarioId] = $true
    }
    foreach ($contractId in ($architectureRow.Groups[2].Value -split ',' | ForEach-Object { $_.Trim() })) {
        if ($contractId -notin $contractIds) { throw "Unknown architecture contract: $contractId" }
        $mappedContracts[$contractId] = $true
    }
    if ([string]::IsNullOrWhiteSpace($architectureRow.Groups[3].Value)) { throw 'Empty architecture responsibility.' }
}
foreach ($scenarioId in $seenScenarios.Keys) {
    if (-not $mappedScenarios.ContainsKey($scenarioId)) { throw "Scenario missing architecture mapping: $scenarioId" }
}
foreach ($contractId in $contractIds) {
    if (-not $mappedContracts.ContainsKey($contractId)) { throw "Unmapped architecture contract: $contractId" }
}

$specification = Get-Content -LiteralPath (Join-Path $repositoryPath 'multimodal_academic_learning_system_spec.md') -Raw
$specIds = @([regex]::Matches($specification, '(?m)^\| ([A-Z]+-\d{2}) \|') | ForEach-Object { $_.Groups[1].Value })
if ($specIds.Count -ne $requiredIds.Count -or ($specIds | Select-Object -Unique).Count -ne $specIds.Count -or (Compare-Object $requiredIds $specIds)) {
    throw 'Consolidated requirements do not match the Phase 1 baseline.'
}

$roadmap = Get-Content -LiteralPath (Join-Path $docsPath 'implementation/phase-5-roadmap.md') -Raw
$milestoneRows = @([regex]::Matches($roadmap, '(?m)^\| (M\d{2}) \| (P[01]) \| ([^|]+) \| ([^|]+) \|\r?$'))
$milestones = @{}
foreach ($row in $milestoneRows) {
    $milestone = $row.Groups[1].Value
    if ($milestones.ContainsKey($milestone)) { throw "Duplicate milestone: $milestone" }
    # Requiring dependencies earlier in the table also rejects cycles and self-dependencies.
    foreach ($dependency in ($row.Groups[3].Value.Trim() -split ', ')) {
        if ($dependency -ne 'None' -and -not $milestones.ContainsKey($dependency)) { throw "Unknown or forward dependency in ${milestone}: $dependency" }
    }
    if ($roadmap -notmatch "(?m)^### ${milestone}:") { throw "Milestone lacks a work/exit section: $milestone" }
    $milestones[$milestone] = $true
}
if ($milestones.Count -eq 0 -or ([regex]::Matches($roadmap, '(?m)^\| M\d{2} \|')).Count -ne $milestoneRows.Count) { throw 'Missing or malformed milestone rows.' }

$gateRows = @([regex]::Matches($roadmap, '(?m)^\| (G\d{2}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|\r?$'))
$gates = @{}
foreach ($row in $gateRows) {
    $gate = $row.Groups[1].Value
    if ($gates.ContainsKey($gate)) { throw "Duplicate qualification gate: $gate" }
    foreach ($milestone in ($row.Groups[4].Value.Trim() -split ', ')) {
        if (-not $milestones.ContainsKey($milestone)) { throw "Unknown due milestone in ${gate}: $milestone" }
    }
    if ($row.Groups[5].Value.Trim() -notmatch '^Open:') { throw "Qualification state needs evidence review: $gate" }
    $gates[$gate] = $true
}
if ($gates.Count -eq 0 -or ([regex]::Matches($roadmap, '(?m)^\| G\d{2} \|')).Count -ne $gateRows.Count) { throw 'Missing or malformed qualification gates.' }

$roadmapRows = @([regex]::Matches($roadmap, '(?m)^\| (UX-\d{2}(?:, UX-\d{2})*) \| (M\d{2}) \| ([^|]+) \|\r?$'))
$ownedScenarios = @{}
foreach ($row in $roadmapRows) {
    if (-not $milestones.ContainsKey($row.Groups[2].Value)) { throw 'Unknown acceptance owner milestone.' }
    foreach ($scenario in ($row.Groups[1].Value -split ', ')) {
        if (-not $seenScenarios.ContainsKey($scenario) -or $ownedScenarios.ContainsKey($scenario)) { throw "Unknown or duplicate roadmap scenario: $scenario" }
        $ownedScenarios[$scenario] = $true
    }
}
if ($ownedScenarios.Count -ne $seenScenarios.Count -or ([regex]::Matches($roadmap, '(?m)^\| UX-')).Count -ne $roadmapRows.Count) { throw 'Incomplete or malformed roadmap acceptance ownership.' }

$artifactPath = Join-Path $repositoryPath 'multimodal_academic_learning_system_architecture_v2.html'
$artifact = Get-Content -LiteralPath $artifactPath -Raw
$htmlIds = @{}
foreach ($match in [regex]::Matches($artifact, '\bid="([^"]+)"')) {
    $id = $match.Groups[1].Value
    if ($htmlIds.ContainsKey($id)) { throw "Duplicate HTML id: $id" }
    $htmlIds[$id] = $true
}
foreach ($id in @($milestones.Keys) + @($gates.Keys)) {
    if (-not $htmlIds.ContainsKey($id)) { throw "Architecture artifact is missing roadmap item: $id" }
}
foreach ($id in $htmlIds.Keys) {
    if (($id -match '^M\d{2}$' -and -not $milestones.ContainsKey($id)) -or ($id -match '^G\d{2}$' -and -not $gates.ContainsKey($id))) { throw "Artifact has unknown roadmap item: $id" }
}
$htmlLinks = 0
foreach ($match in [regex]::Matches($artifact, '\b(?:href|src)="([^"]+)"')) {
    $target = $match.Groups[1].Value
    if ($target.StartsWith('#')) {
        if (-not $htmlIds.ContainsKey($target.Substring(1))) { throw "Broken architecture anchor: $target" }
    } elseif ($target -notmatch '^(https?://|mailto:)') {
        if (-not (Test-Path -LiteralPath (Join-Path $repositoryPath $target) -PathType Leaf)) { throw "Broken architecture file link: $target" }
    }
    $htmlLinks++
}

Write-Output "PASS: $($markdownFiles.Count) planning Markdown files; $linkCount local file links resolve."
Write-Output "PASS: $($scenarioRows.Count) unique scenarios cover $($requiredIds.Count) core requirements and $($screenIds.Count) screens."
Write-Output "PASS: $($mappedScenarios.Count) student scenarios map to $($contractIds.Count) architecture contracts."
Write-Output "PASS: $($milestones.Count) ordered milestones own $($ownedScenarios.Count) scenarios; $($gates.Count) open gates have milestone owners."
Write-Output "PASS: consolidated requirements match; architecture roadmap IDs and $htmlLinks links resolve."
Write-Output 'Scope: file links and structural coverage only; application behavior and note quality are not tested.'
