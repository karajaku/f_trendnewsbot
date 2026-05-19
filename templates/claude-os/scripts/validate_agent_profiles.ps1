param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$AgentPrefix = "{{AGENT_PREFIX}}"
)

$ErrorActionPreference = "Stop"

$issues = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

function Add-Issue {
    param([string]$Message)
    $issues.Add($Message)
}

function Add-Warning {
    param([string]$Message)
    $warnings.Add($Message)
}

if ($AgentPrefix -match '\{\{') {
    Write-Host "ERROR: AgentPrefix still contains a placeholder. Did setup.ps1 run?" -ForegroundColor Red
    Write-Host ("       Got: '{0}'" -f $AgentPrefix) -ForegroundColor Red
    exit 1
}

$canonicalDir = Join-Path $Root ".claude/agents"
$profileDir = Join-Path $Root "docs/agent-profiles"

if (-not (Test-Path -LiteralPath $canonicalDir)) {
    Add-Issue "missing required directory: .claude/agents"
}

# docs/agent-profiles is optional — many projects skip the concept-profile mirror.
$hasProfileDir = Test-Path -LiteralPath $profileDir

if ($issues.Count -gt 0) {
    foreach ($i in $issues) { Write-Host "ISSUE: $i" }
    exit 1
}

$canonicalFiles = Get-ChildItem -LiteralPath $canonicalDir -Filter "$AgentPrefix-*.md" -File
$profileFiles = @()
if ($hasProfileDir) {
    $profileFiles = Get-ChildItem -LiteralPath $profileDir -Filter "*.md" -File
}

# 1) 1:1 pairing (only enforced when docs/agent-profiles exists)
$canonicalMap = @{}
foreach ($f in $canonicalFiles) {
    $shortName = $f.BaseName -replace "^$AgentPrefix-", ''
    $canonicalMap[$shortName] = $f
}

if ($hasProfileDir) {
    $profileMap = @{}
    foreach ($f in $profileFiles) {
        $profileMap[$f.BaseName] = $f
    }

    foreach ($name in $canonicalMap.Keys) {
        if (-not $profileMap.ContainsKey($name)) {
            Add-Warning "missing concept profile: docs/agent-profiles/$name.md (canonical exists: .claude/agents/$AgentPrefix-$name.md)"
        }
    }
    foreach ($name in $profileMap.Keys) {
        if (-not $canonicalMap.ContainsKey($name)) {
            Add-Issue "orphan concept profile: docs/agent-profiles/$name.md has no canonical .claude/agents/$AgentPrefix-$name.md"
        }
    }
}

# 2) Canonical frontmatter sanity check (description/tools/model present)
$requiredKeys = @('name', 'description', 'tools', 'model')
foreach ($f in $canonicalFiles) {
    $content = Get-Content -LiteralPath $f.FullName -Raw
    if ($content -notmatch '(?ms)^---\r?\n(.*?)\r?\n---') {
        Add-Issue "missing YAML frontmatter: .claude/agents/$($f.Name)"
        continue
    }
    $fm = $Matches[1]
    foreach ($key in $requiredKeys) {
        if ($fm -notmatch "(?m)^\s*$key\s*:") {
            Add-Issue ".claude/agents/$($f.Name) frontmatter missing key: $key"
        }
    }
}

# 3) Description advisory — emit canonical description for human eyeballing
$descriptions = @{}
foreach ($f in $canonicalFiles) {
    $content = Get-Content -LiteralPath $f.FullName -Raw
    if ($content -match '(?ms)^---\r?\n(.*?)\r?\n---') {
        $fm = $Matches[1]
        if ($fm -match '(?m)^\s*description\s*:\s*(.+?)\s*$') {
            $descriptions[$f.BaseName] = $Matches[1].Trim()
        }
    }
}

# Output
Write-Host "=== validate_agent_profiles ===" -ForegroundColor Cyan
Write-Host ("agent prefix    : {0}" -f $AgentPrefix)
Write-Host ("canonical files : {0}" -f $canonicalFiles.Count)
Write-Host ("profile files   : {0}" -f $profileFiles.Count)
Write-Host ""

if ($descriptions.Count -gt 0) {
    Write-Host "Canonical descriptions:" -ForegroundColor Cyan
    foreach ($k in ($descriptions.Keys | Sort-Object)) {
        Write-Host ("  {0}: {1}" -f $k, $descriptions[$k])
    }
    Write-Host ""
}

if ($warnings.Count -gt 0) {
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($w in $warnings) { Write-Host ("  - {0}" -f $w) -ForegroundColor Yellow }
    Write-Host ""
}

if ($issues.Count -gt 0) {
    Write-Host "Issues:" -ForegroundColor Red
    foreach ($i in $issues) { Write-Host ("  - {0}" -f $i) -ForegroundColor Red }
    Write-Host ""
    Write-Host ("FAIL ({0} issue(s))" -f $issues.Count) -ForegroundColor Red
    exit 1
}

Write-Host "OK - agent profiles in sync" -ForegroundColor Green
exit 0
