# Claude OS Template

도메인 무관 Claude Code 협업 운영체계 골격. myworld 프로젝트에서 검증된 협업 인프라를 다른 프로젝트로 그대로 이식하기 위한 템플릿이다.

## 무엇이 들어 있나

| 자산 | 역할 |
|---|---|
| `CLAUDE.md` | 프로젝트 작업 규칙·안전 규칙·라우팅 — placeholder로 골격만. 기획서 동기화 / Step 진입 자동화 / phase 단위 일괄 QA cadence 포함 |
| `docs/canonical/DEV_PROCESS.md` | 10-stage 개발 프로세스 (Discovery Research → 브리프 → Concept → Tech Research → 설계+리뷰 → phase 계획 → 구현 → QA → 완료 → canonical sync) |
| `docs/canonical/ask-user-question-guide.md` | `AskUserQuestion` 호출 작성 원칙 (모든 슬래시 커맨드가 호출 직전 참조) |
| `docs/canonical/{PRD,ARCHITECTURE,ADR}.md` | 빈 골격. 새 프로젝트에서 도메인 본문 작성 |
| `docs/DOC_MAP.md` | 문서 라우팅 지도 골격 |
| `docs/AGENT_READ_ORDER.md` | 작업 유형별 최소 읽기 순서 |
| `docs/DOC_GUIDE.md` | 문서 시스템 구조·계층·활용법 |
| `phases/_template/` | 새 phase 생성 시 복사하는 골격 (README, index.json, step.md). index.json에 `pending_manual_qa_scenarios`, step별 `qa_blocking` 필드 포함 |
| `phases/_hotfix-log/` | 핫픽스 경량 로그 (README, _template.md) |
| `phases/index.json` | phase 라우팅 source of truth (빈 상태) |
| `.claude/agents/` | 8개 specialized 에이전트 (orchestrator, implementer, ui-specialist, data-steward, qa-reviewer, docs-keeper, performance-investigator, research-investigator) + Output Schema |
| `.claude/commands/` | 5개 슬래시 커맨드 (`/new-feature`, `/research`, `/write-requirements`, `/design-review`, `/plan-phase`) |
| `scripts/validate_agent_profiles.ps1` | 에이전트 정의 drift 검증 |
| `scripts/validate_doc_status.ps1` | frontmatter status ↔ phase ledger 정합성 검증 |
| `SETUP.md` | 이식 절차 가이드 (이 파일과 별도) |
| `setup.ps1` | placeholder 자동 치환 + 사후 검증 |

## 빠른 시작

```powershell
# 1. 새 프로젝트 루트로 templates/claude-os/ 안의 내용을 복사
Copy-Item -Path "C:\path\to\myworld\templates\claude-os\*" -Destination "C:\path\to\new-project" -Recurse -Force

# 2. 새 프로젝트로 이동 후 setup.ps1 실행
cd C:\path\to\new-project
pwsh -File setup.ps1 `
    -ProjectName "my-project" `
    -ProjectTagline "한 줄 설명" `
    -AgentPrefix "my" `
    -Language "JavaScript" `
    -Runtime "Node 20" `
    -TargetPlatform "AWS Lambda" `
    -DomainKind "백엔드 서비스"

# 3. 도메인 본문 작성 + sanity check
pwsh -File scripts/validate_agent_profiles.ps1
pwsh -File scripts/validate_doc_status.ps1
```

상세 절차는 `SETUP.md`를 따른다.

## 설계 출처

myworld(Godot 2D 콜로니 시뮬레이션) 프로젝트의 협업 인프라에서 도메인 무관 부분만 추출. 원본의 9개 CRITICAL 규칙 중 3개(점진 확장 / 표시-규칙 일치 / 통합 지점 비대화 금지)는 일반화 가능하여 골격에 포함했고, 나머지는 도메인 본문 영역으로 비워두었다.

협업 패턴 6종 동시 운용:

- Sequential — `/new-feature`의 stage routing
- Information-based planning — `/research`의 Discovery(Stage 0) / Tech(Stage 3) 2단 리서치 → 브리프/requirements가 인용
- Operator — `/plan-phase`의 `{{AGENT_PREFIX}}-phase-orchestrator` 위임
- Split-and-merge — `/design-review`의 다중 병렬 교차 리뷰
- Frontmatter status machine — `draft → reviewed → applied → frozen`
- Recovery — `phases/_hotfix-log/`로 phase 외 변경도 추적

QA cadence 기본값은 **phase 단위 일괄 QA**다. step 단위 사용자 QA는 `qa_blocking: true` 예외에만 적용된다. 정적 확인 불가 시나리오는 phase index.json의 `pending_manual_qa_scenarios` 배열에 누적되어 phase 끝에서 일괄 보고된다.

## 라이선스/사용 조건

myworld 저장소 내부 자산. 새 프로젝트에 자유롭게 복사·수정해서 사용한다.
