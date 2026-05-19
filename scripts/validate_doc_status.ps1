param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$issues = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Add-Issue { param([string]$M) $issues.Add($M) | Out-Null }
function Add-Warning { param([string]$M) $warnings.Add($M) | Out-Null }

$ValidStatuses = @('draft', 'reviewed', 'applied', 'frozen')

function Read-Frontmatter {
    param([string]$Path)
    $raw = Get-Content -LiteralPath $Path -Raw
    if ($raw -notmatch '(?ms)\A---\r?\n(.*?)\r?\n---') {
        return $null
    }
    $body = $Matches[1]
    $map = [ordered]@{}
    foreach ($line in $body -split "`r?`n") {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*$') {
            $key = $Matches[1]
            $val = $Matches[2].Trim()
            if ($val -match '^"(.*)"$') { $val = $Matches[1] }
            elseif ($val -match "^'(.*)'$") { $val = $Matches[1] }
            $map[$key] = $val
        }
    }
    return $map
}

function Get-RelativePath {
    param([string]$Full)
    $rootResolved = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\', '/')
    $fullResolved = (Resolve-Path -LiteralPath $Full).Path
    if ($fullResolved.StartsWith($rootResolved)) {
        return $fullResolved.Substring($rootResolved.Length + 1).Replace('\', '/')
    }
    return $fullResolved
}

# ----- 1. Scan docs/features for frontmatter-bearing files -----
$featuresRoot = Join-Path $Root 'docs/features'
$featureFiles = @()
if (Test-Path -LiteralPath $featuresRoot) {
    $featureFiles = Get-ChildItem -LiteralPath $featuresRoot -Recurse -Filter '*.md' -File
}

$featureFmCache = @{}
$frozenDocs = New-Object System.Collections.Generic.HashSet[string]
$trackedDocs = 0

foreach ($f in $featureFiles) {
    $rel = Get-RelativePath -Full $f.FullName
    $fm = Read-Frontmatter -Path $f.FullName
    if ($null -eq $fm -or -not $fm.Contains('status')) {
        continue
    }
    $trackedDocs++
    $featureFmCache[$rel] = $fm
    $status = $fm['status']

    if ($ValidStatuses -notcontains $status) {
        Add-Issue "$rel : invalid status '$status' (expected one of: $($ValidStatuses -join ', '))"
        continue
    }

    # 1a. Transition-required fields
    switch ($status) {
        'reviewed' {
            if (-not $fm.Contains('last_reviewed_at') -or [string]::IsNullOrWhiteSpace($fm['last_reviewed_at']) -or $fm['last_reviewed_at'] -eq 'null') {
                Add-Issue "$rel : status=reviewed but last_reviewed_at is missing/null"
            }
            if (-not $fm.Contains('reviewer') -or [string]::IsNullOrWhiteSpace($fm['reviewer']) -or $fm['reviewer'] -eq 'null') {
                Add-Issue "$rel : status=reviewed but reviewer is missing/null"
            }
        }
        'applied' {
            if (-not $fm.Contains('applied_at') -or [string]::IsNullOrWhiteSpace($fm['applied_at']) -or $fm['applied_at'] -eq 'null') {
                Add-Issue "$rel : status=applied but applied_at is missing"
            }
        }
        'frozen' {
            if (-not $fm.Contains('frozen_at') -or [string]::IsNullOrWhiteSpace($fm['frozen_at']) -or $fm['frozen_at'] -eq 'null') {
                Add-Issue "$rel : status=frozen but frozen_at is missing"
            }
            $frozenDocs.Add($rel) | Out-Null
        }
    }

    # 1b. reviewed/applied/frozen requirements.md must have a sibling design-review-{basename}.md
    #     Exclude design-review-*.md files themselves to avoid recursive sibling requirements.
    $name = $f.Name
    if (($name -like '*-requirements.md' -or $name -like '*-rdd.md' -or $name -like '*-brief.md') -and
        -not ($name -like 'design-review-*')) {
        if ($status -in @('reviewed', 'applied', 'frozen')) {
            $base = [System.IO.Path]::GetFileNameWithoutExtension($name)
            $reviewSibling = Join-Path $f.DirectoryName ("design-review-$base.md")
            if (-not (Test-Path -LiteralPath $reviewSibling)) {
                Add-Issue "$rel : status=$status but sibling design-review-$base.md is missing"
            }
        }
    }
}

# ----- 2. phases/index.json cross-check -----
$phaseIndexPath = Join-Path $Root 'phases/index.json'
$phaseIndex = $null
if (Test-Path -LiteralPath $phaseIndexPath) {
    try {
        $phaseIndex = Get-Content -LiteralPath $phaseIndexPath -Raw | ConvertFrom-Json
    } catch {
        Add-Issue ("phases/index.json : JSON parse error: {0}" -f $_.Exception.Message)
    }
}

$relatedDocCount = 0
if ($null -ne $phaseIndex -and $phaseIndex.PSObject.Properties.Name -contains 'phases') {
    foreach ($phase in $phaseIndex.phases) {
        if (-not $phase.PSObject.Properties.Name.Contains('related_docs')) { continue }
        if ($null -eq $phase.related_docs) { continue }

        foreach ($docPath in $phase.related_docs) {
            $relatedDocCount++
            $normalized = $docPath -replace '\\', '/'
            $abs = Join-Path $Root $normalized

            if (-not (Test-Path -LiteralPath $abs)) {
                Add-Issue ("phases/index.json phase '{0}' : related_docs entry not found on disk: {1}" -f $phase.dir, $normalized)
                continue
            }

            $fm = if ($featureFmCache.ContainsKey($normalized)) {
                $featureFmCache[$normalized]
            } else {
                Read-Frontmatter -Path $abs
            }

            if ($null -eq $fm -or -not $fm.Contains('status')) {
                Add-Warning ("phases/index.json phase '{0}' : related_docs entry has no status frontmatter: {1}" -f $phase.dir, $normalized)
                continue
            }

            $phaseStatus = $phase.status
            $docStatus = $fm['status']

            if ($phaseStatus -in @('completed', 'in_progress', 'active', 'paused', 'implemented_pending_manual_qa')) {
                if ($docStatus -ne 'frozen') {
                    Add-Issue ("phase '{0}' (status={1}) expects related_doc status=frozen but {2} is status={3}" -f $phase.dir, $phaseStatus, $normalized, $docStatus)
                }
            }
        }
    }
}

# ----- Output -----
Write-Host "=== validate_doc_status ===" -ForegroundColor Cyan
Write-Host ("feature docs with status frontmatter : {0}" -f $trackedDocs)
Write-Host ("frozen feature docs                  : {0}" -f $frozenDocs.Count)
Write-Host ("phases with related_docs             : {0}" -f $relatedDocCount)
Write-Host ""

if ($warnings.Count -gt 0) {
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($w in $warnings) { Write-Host ("  - {0}" -f $w) -ForegroundColor Yellow }
    Write-Host ""
}

if ($issues.Count -gt 0) {
    Write-Host "Issues:" -ForegroundColor Red
    foreach ($i in $issues) { Write-Host ("  - {0}" -f $i) -ForegroundColor Red }
    Write-Host ""
    Write-Host ("FAIL ({0} issue(s), {1} warning(s))" -f $issues.Count, $warnings.Count) -ForegroundColor Red
    exit 1
}

if ($warnings.Count -gt 0) {
    Write-Host ("OK with warnings ({0})" -f $warnings.Count) -ForegroundColor Yellow
} else {
    Write-Host "OK - status frontmatter and phase ledger in sync" -ForegroundColor Green
}
exit 0
