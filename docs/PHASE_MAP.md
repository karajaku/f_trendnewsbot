# Phase Map

> 역할: 모든 phase의 라이프사이클(계획·진행·완료·아카이브)을 사람 시야에서 한 페이지로 정리한다. `phases/index.json`이 코드용 source of truth이고 이 문서는 사람용 요약.
> 대상: Stage 5 phase 계획 작성자, 사용자 진행 상황 점검, 신규 합류자 onboarding.

작성일: 2026-05-19

---

## 활성 / 대기 Phase

(없음 — 2026-05-19 시점)

## 완료 Phase

| ID | dir | feature_group | status | 핵심 산출물 | 종료 보고서 |
|---|---|---|---|---|---|
| 01 | [01-mvp-daily-digest](../phases/01-mvp-daily-digest/) | `daily_digest` | completed (2026-05-19) | V1 매일 다이제스트 봇 — 부트스트랩 + fetcher + filter + summarizer + dispatcher (Pages + 텔레그램) + run_daily 통합 + GitHub Actions cron + dry-run 검증 + canonical sync (8 step) | (phase 01 README + step1~8.md) |
| 02 | [02-gemini-swap](../phases/02-gemini-swap/) | `daily_digest` | completed (2026-05-19) | LLM provider swap — Anthropic Claude Haiku 4.5 → Google Gemini 2.5 Flash (ADR-004 + ADR-005). 무료 tier 영구 운영 (4 step + 5건 hotfix 누적 회고) | [final-report.md](../phases/02-gemini-swap/final-report.md) |

## Archived Phase

(없음)

---

## Phase 라이프사이클

```
pending  ─▶  in_progress  ─▶  implemented_pending_manual_qa (선택)  ─▶  completed
           │                                                          │
           ↓                                                          ↓
        paused (사용자 명시 시)                                   archived (archive_target=true 시)
```

`status` 변경 시 반드시 `phases/index.json` 동기화. 본 PHASE_MAP은 `phases/index.json` 변경 후 행 업데이트.

## Phase 별 step 상세

각 phase의 step 목록·acceptance·진행은 `phases/{dir}/README.md` + `phases/{dir}/index.json` 참조.

### 01-mvp-daily-digest (V1) — completed 2026-05-19

| step | summary | qa_blocking | status |
|---|---|---|---|
| 1 | 부트스트랩 — pyproject·폴더·lib helpers | false | completed |
| 2 | config 로딩 — sources/filters 스키마 (recipients.yml 폐기, ADR-003) | false | completed |
| 3 | fetchers — RSS·HTML·JSON 어댑터 + 소스 격리 | false | completed |
| 4 | filters + history backend — dedup·timewindow·category + artifact 연동 | **true** | completed |
| 5 | summarizer — google-genai SDK (ADR-005) + JSON mode + hard cap + render (Apple v3 HTML + 텔레그램 인덱스) | false | completed |
| 6 | dispatchers — Pages publish (gh-pages 브랜치) + 텔레그램 Bot API + 운영자 alert chat (ADR-003) | false | completed |
| 7 | run_daily 통합 + GitHub Actions workflow (cron + Pages 권한) + Secrets 가이드 | **true** | completed (phase 02 step4 dry-run 으로 동시 검증) |
| 8 | dry-run + verification-record + canonical sync (PRD·ARCHITECTURE·PHASE_MAP·implementation_status) | **true** | completed |

phase 도중 발견 hotfix 2건: [`2026-05-19-pages-gh-branch-boundary.md`](../phases/_hotfix-log/2026-05-19-pages-gh-branch-boundary.md), [`2026-05-19-windows-tzdata.md`](../phases/_hotfix-log/2026-05-19-windows-tzdata.md)

### 02-gemini-swap — completed 2026-05-19

| step | summary | qa_blocking | status |
|---|---|---|---|
| 1 | ADR-004 신설 + pyproject deps swap (anthropic 제거, google-genai 추가) | false | completed |
| 2 | summarizer/client.py google-genai 재작성 + JSON mode + ResourceExhausted → QuotaExceededError 매핑 | false | completed |
| 3 | env var rename ANTHROPIC_API_KEY → GEMINI_API_KEY / CLAUDE_MODEL_ID → GEMINI_MODEL_ID (6개 위치 동시) | false | completed |
| 4 | tests/summarizer 회귀 + ruff/mypy + workflow yml 파싱 + 실제 dry-run (6회차 통과) | **true** | completed |

phase 도중 발견 hotfix 5건: [dispatcher mypy](../phases/_hotfix-log/2026-05-19-dispatcher-mypy-typing.md) · [gemini-2.0-flash deprecated (ADR-005 신설)](../phases/_hotfix-log/2026-05-19-gemini-2-0-flash-deprecated.md) · [GEMINI_MODEL_ID 빈 문자열 fallback](../phases/_hotfix-log/2026-05-19-gemini-model-id-empty-string-fallback.md) · [Gemini 2.5 thinking-mode truncate](../phases/_hotfix-log/2026-05-19-gemini-2-5-thinking-mode-truncate.md) · [텔레그램 풋터 중복](../phases/_hotfix-log/2026-05-19-telegram-footer-duplicate-base-url.md)
