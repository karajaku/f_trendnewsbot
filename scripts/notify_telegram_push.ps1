# scripts/notify_telegram_push.ps1
#
# Claude Code PostToolUse/PostToolUseFailure 훅 — `git push` 완료 시 텔레그램 알림.
# stdin 으로 훅 JSON 을 받고, .env 또는 환경변수에서 토큰을 읽어 Telegram Bot API 로 전송.
#
# 호출 예: powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/notify_telegram_push.ps1 -Status success
# `-Status success`(PostToolUse) 또는 `-Status failure`(PostToolUseFailure) 로 결과 구분.
#
# 보안: 토큰·chat_id 는 .env(gitignored) 에서만 로드. 평문 로그 금지.
# 회귀: 토큰이 없거나 API 가 실패해도 silent exit 0 — git push 워크플로우를 방해하지 않음.

[CmdletBinding()]
param(
    [ValidateSet('success', 'failure')]
    [string]$Status = 'success'
)

$ErrorActionPreference = 'Stop'

# stdin JSON 파싱 (없거나 깨지면 silent skip)
try {
    $raw = [Console]::In.ReadToEnd()
    if (-not $raw) { exit 0 }
    $payload = $raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    exit 0
}

# tool_input.command 추출
$cmd = $null
try { $cmd = $payload.tool_input.command } catch {}
if (-not $cmd) { exit 0 }

# `git push` 가 아닌 명령은 if 필터로 이미 걸러지지만, 방어선으로 한 번 더
if ($cmd -notmatch '\bgit\s+push\b') { exit 0 }

# .env 로더 (KEY=VALUE 한 줄씩, # 코멘트 무시, "..." quote 제거)
function Read-DotEnv {
    param([string]$Path)
    $map = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $map }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        $eq = $t.IndexOf('=')
        if ($eq -lt 1) { continue }
        $k = $t.Substring(0, $eq).Trim()
        $v = $t.Substring($eq + 1).Trim()
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        $map[$k] = $v
    }
    return $map
}

# 프로젝트 루트의 .env 시도 (훅 cwd = project root)
$envMap = Read-DotEnv -Path (Join-Path -Path (Get-Location) -ChildPath '.env')

function Get-EnvValue {
    param([string]$Key)
    if ($envMap.ContainsKey($Key) -and $envMap[$Key]) { return $envMap[$Key] }
    $procVal = [Environment]::GetEnvironmentVariable($Key)
    if ($procVal) { return $procVal }
    return $null
}

$token = Get-EnvValue 'TELEGRAM_BOT_TOKEN'
if (-not $token -or $token.StartsWith('<')) { exit 0 }  # placeholder 또는 미설정

# 운영자 alert chat 우선 (개인용). 없으면 직원 단톡방으로 fallback 하지 않음 — 노이즈 방지.
$chatId = Get-EnvValue 'OPS_ALERT_CHAT_ID'
if (-not $chatId -or $chatId.StartsWith('<')) { exit 0 }

# 현재 브랜치 (best-effort)
$branch = ''
try {
    $branch = (& git rev-parse --abbrev-ref HEAD 2>$null)
    if ($branch) { $branch = $branch.Trim() }
} catch {}

# 프로젝트 식별자 — git remote URL 의 repo 이름 우선, 없으면 cwd 디렉토리 이름
$project = ''
try {
    $remoteUrl = (& git remote get-url origin 2>$null)
    if ($remoteUrl) {
        $rm = [regex]::Match($remoteUrl.Trim(), '[:/]([^/:]+?)(?:\.git)?/?\s*$')
        if ($rm.Success) { $project = $rm.Groups[1].Value }
    }
} catch {}
if (-not $project) {
    try { $project = Split-Path -Leaf (Get-Location) } catch {}
}

# remote 이름 추출 — `git push <remote> ...` 패턴
$remote = ''
$m = [regex]::Match($cmd, 'git\s+push\s+(?:-[^\s]+\s+)*([^\s\-][^\s]*)')
if ($m.Success) { $remote = $m.Groups[1].Value }

# KST timestamp
$kst = ''
try {
    $tz = [System.TimeZoneInfo]::FindSystemTimeZoneById('Korea Standard Time')
    $kst = [System.TimeZoneInfo]::ConvertTimeFromUtc([DateTime]::UtcNow, $tz).ToString('yyyy-MM-dd HH:mm:ss')
} catch {
    $kst = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
}

# HTML escape
Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue
function Html-Escape {
    param([string]$Text)
    if (-not $Text) { return '' }
    return [System.Web.HttpUtility]::HtmlEncode($Text)
}

$icon = if ($Status -eq 'success') { '✅' } else { '❌' }
$verb = if ($Status -eq 'success') { '완료' } else { '실패' }

$projectPrefix = if ($project) { "[$(Html-Escape $project)] " } else { '' }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("$icon ${projectPrefix}git push $verb (KST $kst)")
$lines.Add('')
$lines.Add("<b>명령:</b> <code>$(Html-Escape $cmd)</code>")
if ($branch) { $lines.Add("<b>브랜치:</b> $(Html-Escape $branch)") }
if ($remote) { $lines.Add("<b>remote:</b> $(Html-Escape $remote)") }

# 실패 시 stderr 일부 노출 (있으면)
if ($Status -eq 'failure') {
    $err = $null
    try {
        if ($payload.tool_response.stderr) { $err = [string]$payload.tool_response.stderr }
        elseif ($payload.tool_response.output) { $err = [string]$payload.tool_response.output }
        elseif ($payload.tool_response.error) { $err = [string]$payload.tool_response.error }
    } catch {}
    if ($err) {
        $errTrim = if ($err.Length -gt 400) { $err.Substring(0, 400) + '…' } else { $err }
        $lines.Add('')
        $lines.Add("<pre>$(Html-Escape $errTrim)</pre>")
    }
}

$text = ($lines -join "`n")

# 본문 byte 한도 (Telegram = 4096). 안전선
$bytes = [System.Text.Encoding]::UTF8.GetByteCount($text)
if ($bytes -gt 3800) {
    $text = $text.Substring(0, [Math]::Min(1500, $text.Length)) + "`n…(truncated)"
}

$apiUrl = "https://api.telegram.org/bot$token/sendMessage"
$body = @{
    chat_id = [int64]$chatId
    text = $text
    parse_mode = 'HTML'
    disable_web_page_preview = $true
} | ConvertTo-Json -Compress

$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

try {
    Invoke-RestMethod -Uri $apiUrl -Method Post -ContentType 'application/json; charset=utf-8' -Body $bodyBytes -TimeoutSec 8 | Out-Null
} catch {
    # silent — git push 흐름 방해 금지
}

exit 0
