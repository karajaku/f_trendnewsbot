# Claude OS — Setup Guide

> 역할: `templates/claude-os/`의 협업 인프라를 새 프로젝트에 이식하는 절차.
> 대상: Claude Code 협업 OS를 처음 적용하는 새 프로젝트의 첫 작업.

이 가이드는 myworld 프로젝트에서 검증된 협업 인프라를 다른 프로젝트로 옮겨오기 위한 단계별 절차다. 한 시간 안에 새 프로젝트가 동일한 협업 운영체계를 갖추게 된다.

---

## 사전 준비

새 프로젝트 디렉토리에 다음이 갖춰져 있어야 한다.

- Git 저장소 (`git init` 완료 또는 기존 저장소)
- Claude Code CLI 설치 + 로그인 완료
- PowerShell 7+ (Windows) 또는 pwsh (macOS/Linux) — 자동 setup 스크립트 실행용
- 운영 언어/런타임 정보를 한 줄로 정리해둘 것

---

## 1단계: 템플릿 복사

myworld 저장소의 `templates/claude-os/` 안의 **내용물 전부**를 새 프로젝트 루트로 복사한다. 폴더 자체가 아니라 폴더 **안의 파일·하위 폴더**를 새 프로젝트 루트에 직접 옮긴다.

PowerShell 예시:

```powershell
$source = "C:\Users\Jack\Documents\myworld\templates\claude-os"
$target = "C:\path\to\new-project"
Copy-Item -Path "$source\*" -Destination $target -Recurse -Force
```

복사 후 새 프로젝트 루트에는 다음이 들어 있어야 한다.

```
.claude/agents/tnb-*.md  (8개)
.claude/commands/*.md                  (5개 — new-feature, research, write-requirements, design-review, plan-phase)
docs/canonical/*.md                    (5개 — PRD, ARCHITECTURE, ADR, DEV_PROCESS, ask-user-question-guide)
docs/DOC_MAP.md
docs/AGENT_READ_ORDER.md
docs/DOC_GUIDE.md
phases/_template/                      (3개)
phases/_hotfix-log/                    (2개)
phases/index.json
scripts/validate_agent_profiles.ps1
scripts/validate_doc_status.ps1
CLAUDE.md
SETUP.md                               (이 파일 — 이식 후 삭제 가능)
setup.ps1
```

---

## 2단계: 변수 결정

새 프로젝트에 맞는 토큰을 결정한다. 정해진 값을 그대로 `setup.ps1`에 인자로 넘기면 모든 파일이 일괄 치환된다.

| 토큰 | 의미 | 예시 |
|---|---|---|
| `PROJECT_NAME` | 프로젝트 식별자 (kebab-case 또는 snake_case) | `gas-automation`, `data-pipeline` |
| `PROJECT_TAGLINE` | 프로젝트 한 줄 설명 (10~25자) | `Google Apps Script 사내 자동화 도구 모음` |
| `AGENT_PREFIX` | 에이전트 파일명 접두사 (보통 PROJECT_NAME과 동일) | `gas`, `pipeline` |
| `LANGUAGE` | 주 언어 | `JavaScript (Apps Script V8)`, `Python 3.12` |
| `RUNTIME` | 런타임/엔진/버전 | `Apps Script V8`, `Node 20`, `Godot 4.6.1` |
| `TARGET_PLATFORM` | 타깃 환경 | `Google Workspace`, `AWS Lambda`, `PC/Steam` |
| `DOMAIN_KIND` | 도메인 종류 (CLAUDE.md 헤더용) | `사내 자동화`, `데이터 파이프라인`, `2D 콜로니 시뮬레이션` |

`AGENT_PREFIX`는 짧고 충돌이 없어야 한다. 한 컴퓨터에서 여러 프로젝트의 Claude Code를 동시에 쓴다면 프로젝트마다 다른 prefix를 권장한다.

---

## 3단계: 자동 치환 실행

새 프로젝트 루트에서 `setup.ps1`을 실행한다. 결정한 변수를 매개변수로 넘긴다.

```powershell
pwsh -File setup.ps1 `
    -ProjectName "gas-automation" `
    -ProjectTagline "Google Apps Script 사내 자동화 도구 모음" `
    -AgentPrefix "gas" `
    -Language "JavaScript (Apps Script V8)" `
    -Runtime "Apps Script V8" `
    -TargetPlatform "Google Workspace" `
    -DomainKind "사내 자동화"
```

스크립트가 하는 일:

1. 모든 `*.md`, `*.json`, `*.ps1` 파일에서 `{{ TOKEN }}` 형식(두 중괄호 사이에 토큰 이름) placeholder를 일괄 치환.
2. `.claude/agents/tnb-*.md` 8개 파일명을 `{prefix}-*.md`로 rename.
3. `setup.ps1`과 `SETUP.md`는 치환 후 자체적으로 보존 (제거할지 묻기).
4. 치환 요약을 출력.

실행 후 git diff로 변경 내용을 확인한다.

---

## 4단계: 도메인 본문 작성

자동 치환은 메타데이터만 채운다. 다음 파일들은 **사람이 직접 도메인 본문을 채워야** 한다. 비어 있어도 협업 OS는 작동하지만, 채울수록 효과가 커진다.

### 4-1. CLAUDE.md — 핵심 아키텍처 규칙·흔한 작업·Anti-pattern

새 프로젝트의 CRITICAL 규칙을 작성한다. myworld의 9개 규칙 형식을 참고하되 도메인에 맞게 다시 쓴다. 예시(Apps Script):

```markdown
## 핵심 아키텍처 규칙

- CRITICAL: Apps Script V8 런타임 호환성 유지. 사용 불가 ES 기능 피한다.
- CRITICAL: 실행 시간 6분 제한. 무거운 작업은 trigger + Properties로 분할한다.
- CRITICAL: OAuth scope는 `appsscript.json`에 명시한 최소 범위만 요청한다.
- CRITICAL: Sheet/Document 자체를 데이터 저장소로 쓸 때 read/write 분리 명확히 한다.
```

흔한 작업 패턴과 Anti-pattern도 myworld 형식을 따라 5개씩 작성한다.

### 4-2. docs/canonical/PRD.md — 제품 목표·MVP 범위

새 프로젝트의 목표, MVP 범위, 성공 기준. 1~3페이지.

### 4-3. docs/canonical/ARCHITECTURE.md — 시스템 구조

폴더 구조, 모듈/서비스 분할, 데이터 흐름. 코드 구현 후 갱신이 보통.

### 4-4. docs/canonical/ADR.md — 장기 의사결정 기록

채택한 기술 스택, 트레이드오프, "왜 이렇게 결정했는가"의 누적 기록.

### 4-5. docs/DOC_MAP.md — Feature Groups 섹션

새 프로젝트의 기능 그룹을 정의한다. myworld의 daughter/character/world 같은 자리에 새 프로젝트의 도메인 그룹이 들어간다. 예시(Apps Script): `sheet-automation`, `gmail-workflow`, `form-handler`, `admin-tools`, `permissions`.

---

## 5단계: 첫 sanity check

검증 스크립트를 돌려서 인프라가 정상 작동하는지 확인한다.

```powershell
pwsh -File scripts/validate_agent_profiles.ps1
pwsh -File scripts/validate_doc_status.ps1
```

기대 결과:

- `validate_agent_profiles.ps1`: `OK — agent profiles in sync` (exit 0). `.claude/agents/`에 7개 에이전트가 있고 frontmatter가 갖춰져 있어야 한다.
- `validate_doc_status.ps1`: `OK - status frontmatter and phase ledger in sync` (exit 0). 처음에는 추적 대상 0건이 정상.

스크립트가 issue를 보고하면 메시지에 따라 수정한다. 가장 흔한 누락은 4단계에서 PRD/ARCHITECTURE/ADR을 비워둔 채로 첫 phase를 등록한 경우.

---

## 6단계: 첫 phase 만들어보기 (선택)

협업 OS가 살아 있는지 확인하려면 작은 phase를 하나 돌려본다.

```
Claude Code 세션에서:
/new-feature {작은-기능-이름}
→ 규모 판단 → 핫픽스라면 Hotfix DoD 출력, 소형 이상이면 Stage 라우팅 (Stage 0 Discovery / Stage 1 브리프 / Stage 2 Concept 등)
```

새 기능이 **대형**으로 분류되면 다음 순서로 진행된다:

```
/new-feature {기능명}      → 규모 진단, Stage 0 안내
/research {기능명}         → Stage 0 Discovery Research (외부 레퍼런스 + 코드 개괄)
/new-feature 다시 실행      → Stage 1 브리프 작성 (Discovery 시사점 인용)
/research {brief 경로}      → Stage 3 Tech Research (코드 깊이 분석 + API)
/write-requirements {brief} → Stage 4 requirements.md 작성 (Tech Research 시사점 인용)
/design-review {requirements} → 다중 에이전트 교차 리뷰
/plan-phase {requirements}  → Stage 5 Phase 계획 + step 분해
```

작은 변경 한 건을 끝까지 통과시켜보면 협업 OS가 의도대로 작동하는지 즉시 확인된다.

---

## 7단계: 마무리 정리

이식이 끝나면 다음을 삭제하거나 보관한다.

- `SETUP.md` — 이식 절차는 끝났으므로 삭제 권장. 향후 재이식 가능성이 있다면 `docs/_legacy/` 또는 별도 백업 폴더로 이동.
- `setup.ps1` — 동일하게 삭제 또는 백업.
- `.claude/agents/tnb-*.md` 8개 — 자동 치환 후 실제 prefix로 파일명이 바뀌어 있어야 한다. 남아 있는 `{{...}}` placeholder가 있다면 setup.ps1 재실행 또는 수동 정리.

git에 커밋한다:

```powershell
git add CLAUDE.md docs phases .claude scripts
git commit -m "Bootstrap Claude collaboration OS"
```

---

## 트러블슈팅

| 증상 | 원인·해결 |
|---|---|
| `setup.ps1` 실행 시 "execution policy" 오류 | `pwsh -ExecutionPolicy Bypass -File setup.ps1 ...` |
| `validate_agent_profiles.ps1`가 "missing required directory" | 1단계 복사가 누락된 디렉토리가 있음. `.claude/agents/`와 `docs/agent-profiles/`가 모두 있어야 함 (후자가 없으면 빈 폴더로 만들어도 됨) |
| 치환 후에도 `{{...}}` placeholder가 남아 있음 | `Get-ChildItem -Recurse -Filter *.md \| Select-String '{{'`로 누락 위치 확인. setup.ps1을 다시 실행하거나 수동 수정 |
| 에이전트 이름이 충돌 (다른 프로젝트와 동일 prefix) | 다른 prefix로 setup.ps1 재실행 또는 `.claude/agents/` 파일명 수동 변경 + 슬래시 커맨드 내 에이전트 호출 라인도 함께 갱신 |

---

## 다음 단계

협업 OS의 사용법은 myworld와 동일하다. 다음 문서를 참조한다.

- `CLAUDE.md` — 항상 첫 읽기
- `docs/DOC_MAP.md` — 문서 라우팅
- `docs/AGENT_READ_ORDER.md` — 작업 유형별 최소 읽기 순서
- `docs/canonical/DEV_PROCESS.md` — 7-stage 개발 프로세스 전체

협업 OS의 설계 원리는 myworld의 `docs/dev-process-meeting-2026-05-16.md` 참조 (이식하지 않음, 원본 저장소에 남김).
