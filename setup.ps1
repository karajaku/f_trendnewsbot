#requires -Version 7.0
<#
.SYNOPSIS
    Bootstraps a new project with the Claude collaboration OS.

.DESCRIPTION
    Replaces placeholders of the form (double-brace TOKEN double-brace) across CLAUDE.md, docs/, phases/, .claude/, and scripts/.
    Renames .claude/agents/tnb-*.md files to use the real agent prefix.
    Prints a summary of the substitutions performed.

    Run from the new project root AFTER copying the contents of templates/claude-os/ in.

.EXAMPLE
    pwsh -File setup.ps1 `
        -ProjectName "gas-automation" `
        -ProjectTagline "Google Apps Script automation suite" `
        -AgentPrefix "gas" `
        -Language "JavaScript (Apps Script V8)" `
        -Runtime "Apps Script V8" `
        -TargetPlatform "Google Workspace" `
        -DomainKind "internal automation"

.NOTES
    Safe to re-run. Already-substituted files are left unchanged on the next pass.
#>

param(
    [Parameter(Mandatory = $true)] [string]$ProjectName,
    [Parameter(Mandatory = $true)] [string]$ProjectTagline,
    [Parameter(Mandatory = $true)] [string]$AgentPrefix,
    [Parameter(Mandatory = $true)] [string]$Language,
    [Parameter(Mandatory = $true)] [string]$Runtime,
    [Parameter(Mandatory = $true)] [string]$TargetPlatform,
    [Parameter(Mandatory = $true)] [string]$DomainKind,
    [string]$Root = (Get-Location).Path
)

$ErrorActionPreference = "Stop"

# Ensure UTF-8 for both file I/O and console output so non-ASCII content (Korean etc.) is preserved.
$OutputEncoding = [System.Text.Encoding]::UTF8
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
$PSDefaultParameterValues['Set-Content:Encoding'] = 'utf8'

Write-Host "=== Claude OS Setup ===" -ForegroundColor Cyan
Write-Host ("Root           : {0}" -f $Root)
Write-Host ("ProjectName    : {0}" -f $ProjectName)
Write-Host ("AgentPrefix    : {0}" -f $AgentPrefix)
Write-Host ""

# ---------- Validate AgentPrefix ----------
if ($AgentPrefix -notmatch '^[a-z][a-z0-9-]*$') {
    Write-Host "ERROR: AgentPrefix must be lowercase, start with a letter, and contain only [a-z0-9-]." -ForegroundColor Red
    Write-Host ("       Got: '{0}'" -f $AgentPrefix) -ForegroundColor Red
    exit 1
}

$today = (Get-Date).ToString('yyyy-MM-dd')

# ---------- Token map ----------
$tokens = [ordered]@{
    'f_trendnewsbot'     = $ProjectName
    '팜보스 매일 아침 AI·농산물 유통 트렌드 뉴스 자동 큐레이션 봇'  = $ProjectTagline
    'tnb'     = $AgentPrefix
    'Python 3.12'         = $Language
    'Python 3.12 + GitHub Actions'          = $Runtime
    'GitHub Actions cron + 이메일/메신저 전송'  = $TargetPlatform
    '뉴스 수집·요약·발송 자동화'      = $DomainKind
    '2026-05-19'            = $today
}

# ---------- Collect files ----------
$targetExtensions = @('*.md', '*.json', '*.ps1', '*.gitkeep')
$skipDirs = @('node_modules', '.git', 'build', 'dist')

$files = Get-ChildItem -LiteralPath $Root -Recurse -File -Include $targetExtensions |
    Where-Object {
        $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
        $first = ($rel -split '[\\/]', 2)[0]
        $skipDirs -notcontains $first
    }

Write-Host ("Scanning {0} files for placeholders..." -f $files.Count) -ForegroundColor Cyan

# ---------- Substitute ----------
$changedFiles = 0
$totalReplacements = 0
$perTokenCount = @{}
foreach ($k in $tokens.Keys) { $perTokenCount[$k] = 0 }

foreach ($f in $files) {
    $content = Get-Content -LiteralPath $f.FullName -Raw
    $originalContent = $content

    foreach ($k in $tokens.Keys) {
        $matches = [regex]::Matches($content, [regex]::Escape($k))
        if ($matches.Count -gt 0) {
            $perTokenCount[$k] += $matches.Count
            $totalReplacements += $matches.Count
            $content = $content -replace [regex]::Escape($k), $tokens[$k]
        }
    }

    if ($content -ne $originalContent) {
        Set-Content -LiteralPath $f.FullName -Value $content -NoNewline:$false -Encoding utf8
        $changedFiles++
    }
}

Write-Host ""
Write-Host "Substitution summary:" -ForegroundColor Cyan
foreach ($k in $tokens.Keys) {
    Write-Host ("  {0,-22} -> {1,-30} ({2} occurrences)" -f $k, $tokens[$k], $perTokenCount[$k])
}
Write-Host ("Files changed     : {0}" -f $changedFiles)
Write-Host ("Total replacements: {0}" -f $totalReplacements)
Write-Host ""

# ---------- Rename agent files ----------
# Template stores agent files as "tnb-{role}.md" literally in the file name.
# Substitute the placeholder in the file name itself.
$agentDir = Join-Path $Root ".claude/agents"
$renamed = 0
$skippedAgents = 0
if (Test-Path -LiteralPath $agentDir) {
    Write-Host "Renaming agent files..." -ForegroundColor Cyan
    $agentFiles = Get-ChildItem -LiteralPath $agentDir -File
    foreach ($af in $agentFiles) {
        if ($af.Name -like '*tnb*') {
            $newName = $af.Name -replace [regex]::Escape('tnb'), $AgentPrefix
            $newPath = Join-Path $af.DirectoryName $newName
            if (Test-Path -LiteralPath $newPath) {
                Write-Host ("  SKIP rename: target already exists: {0}" -f $newName) -ForegroundColor Yellow
            } else {
                Rename-Item -LiteralPath $af.FullName -NewName $newName
                Write-Host ("  renamed: {0} -> {1}" -f $af.Name, $newName)
                $renamed++
            }
        } elseif ($af.Name -like "$AgentPrefix-*.md") {
            $skippedAgents++
        }
    }
    Write-Host ("  agents already prefixed: {0}" -f $skippedAgents)
    Write-Host ("  agents renamed         : {0}" -f $renamed)
} else {
    Write-Host "NOTE: .claude/agents directory not found." -ForegroundColor Yellow
}
Write-Host ""

# ---------- Residual placeholder check ----------
# Re-scan from disk because earlier rename step changed some paths.
$residualFiles = Get-ChildItem -LiteralPath $Root -Recurse -File -Include $targetExtensions |
    Where-Object {
        $rel = $_.FullName.Substring($Root.Length).TrimStart('\', '/')
        $first = ($rel -split '[\\/]', 2)[0]
        $skipDirs -notcontains $first
    }

$residual = New-Object System.Collections.Generic.List[string]
foreach ($f in $residualFiles) {
    $content = Get-Content -LiteralPath $f.FullName -Raw
    if ($content -match '\{\{[A-Z_]+\}\}') {
        $hits = [regex]::Matches($content, '\{\{[A-Z_]+\}\}') | ForEach-Object { $_.Value } | Sort-Object -Unique
        $rel = $f.FullName.Substring($Root.Length).TrimStart('\', '/')
        $residual.Add(("{0} : {1}" -f $rel, ($hits -join ', '))) | Out-Null
    }
}

if ($residual.Count -gt 0) {
    Write-Host "WARNING: residual placeholders remain in the following files." -ForegroundColor Yellow
    Write-Host "         setup.ps1 only knows the standard token set; custom tokens need manual edits." -ForegroundColor Yellow
    foreach ($r in $residual) { Write-Host ("  - {0}" -f $r) -ForegroundColor Yellow }
    Write-Host ""
} else {
    Write-Host "All standard placeholders substituted." -ForegroundColor Green
    Write-Host ""
}

# ---------- Next steps ----------
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Fill in CLAUDE.md domain sections (CRITICAL rules, common tasks, anti-patterns)."
Write-Host "  2. Draft docs/canonical/PRD.md, ARCHITECTURE.md, ADR.md."
Write-Host "  3. Define feature groups in docs/DOC_MAP.md."
Write-Host "  4. Run validators:"
Write-Host "       pwsh -File scripts/validate_agent_profiles.ps1"
Write-Host "       pwsh -File scripts/validate_doc_status.ps1"
Write-Host "  5. Commit: git add . ; git commit -m 'Bootstrap Claude collaboration OS'"
Write-Host "  6. Delete or archive SETUP.md and setup.ps1 once the bootstrap is verified."
Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
exit 0
