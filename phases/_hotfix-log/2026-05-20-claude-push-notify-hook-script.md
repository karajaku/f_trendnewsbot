# Claude Code `git push` 텔레그램 알림 훅 헬퍼 스크립트 추가

날짜: 2026-05-20
규모: 핫픽스급 운영 도구 추가 (1파일 신규, 계약 변경 없음, 코드 변경 없음)

## 동기

운영자(다중 프로젝트 진행)가 Claude Code 세션에서 `git push` 가 끝났을 때 결과를 즉시 알 수 있도록 텔레그램 알림이 필요하다는 요청 (2026-05-20). 훅 자체는 개인 환경 설정 (`.claude/settings.local.json` — gitignored) 에서 enable 하지만, 훅이 호출할 PowerShell 헬퍼는 프로젝트에 commit 해 두면 다른 contributor 도 같은 알림을 1줄 enable 만으로 켤 수 있고, 향후 다른 프로젝트에 그대로 복사 재사용 가능.

## 변경

- `scripts/notify_telegram_push.ps1` (신규) — Claude Code `PostToolUse` / `PostToolUseFailure` 훅이 stdin JSON 으로 호출하는 PowerShell 스크립트.
  - `git push *` 명령만 처리 (방어선 regex + 훅 측 `if: "Bash(git push *)"` 이중 필터)
  - `.env` 파일에서 `TELEGRAM_BOT_TOKEN` + `OPS_ALERT_CHAT_ID` 로드 (환경변수 fallback)
  - 메시지 본문: `[프로젝트명] git push 성공/실패` + 명령 + 브랜치 + remote + KST 타임스탬프 (실패 시 stderr 일부)
  - 프로젝트명: `git remote get-url origin` 의 repo 이름 우선, 없으면 `Split-Path -Leaf (Get-Location)` fallback — 다중 프로젝트에서 같은 chat 으로 알림 보내도 prefix 로 식별
  - 인증 실패·토큰 미설정·API 5xx 등 모든 실패 경로에서 `exit 0` — 사용자 git push 워크플로우 비차단 (격리 원칙)
  - 토큰·chat_id 평문 로깅 금지 (`Invoke-RestMethod` 기본 동작)

훅 등록 자체 (`.claude/settings.local.json`) 는 개인 설정이라 gitignored — 다른 contributor 가 enable 하려면 README 또는 별도 docs 안내 필요 (이번 PR 범위 외).

## 수동 확인

- [x] pipe-test: 토큰 미설정 / 비-git-push 명령 / 깨진 JSON / 가짜 토큰 4 케이스 모두 silent `exit 0` 확인.
- [x] live API getMe — `@farmboss_settle_dev_bot` 토큰 유효.
- [x] live API sendMessage — `OPS_ALERT_CHAT_ID=-5036800207` (basic group `f_정산봇_개발방`) message_id 정상 수신.
- [x] 실제 `git push origin hotfix-2026-05-20-bundle` 후 훅 발화 + `[f_trendnewsbot]` prefix 메시지 도착 확인.

## 회귀 위험

- **운영 파이프라인 영향 없음**: 이 스크립트는 GitHub Actions cron 에서 호출되지 않음. 로컬 Claude Code 세션의 hook 만이 invoker. `src/`·`dispatchers/` 어느 모듈도 import 하지 않음.
- **시크릿 노출**: 스크립트 본문에 토큰 placeholder 없음. `.env` 는 이미 `.gitignore` 등재. 메시지 본문에 토큰 echo 없음.
- **PowerShell 5.1 인코딩**: 스크립트는 UTF-8 BOM 으로 저장 (한국어 라벨·이모지 정상 파싱). 향후 누가 BOM 없이 재저장하면 PS5.1 에서 ANSI 로 읽혀 깨질 수 있음 — 발견 즉시 BOM 복원.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음 (코드 변경 0건)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음
- [x] 운영 파이프라인 진입점 (`src/run_daily.py`) 무영향

## 후속

- 다른 contributor 가 enable 할 수 있도록 `docs/` 에 한 줄 안내 (어느 docs 가 알맞은지는 별도 결정).
- 다른 프로젝트에 복사할 때 토큰·chat_id 만 `.env` 에 채우면 동작 — 스크립트 자체는 unchanged.
