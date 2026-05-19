# Phase 02 — Gemini Swap · 종료 보고서

> 역할: phase 02 (LLM provider swap) 의 phase 끝 일괄 QA 보고. CLAUDE.md "phase 끝 일괄 보고 항목" 5가지를 모두 포함한다.
> 대상: 운영자(사용자), phase 01 step8 진입자, 향후 ADR-005 6개월 후 재검토 트리거 발동 시 retrospective 참조자.

작성일: 2026-05-19
상태: completed

---

## 1. 변경 파일 diff 요약 (카테고리별)

phase 02 의 6개 commit 으로 분리 처리.

### 코드 변경

| 파일 | 변경 요지 | commit |
|---|---|---|
| `src/summarizer/client.py` | Anthropic SDK → google-genai 재작성 + JSON mode + ResourceExhausted/429 매핑 + `ThinkingConfig(thinking_budget=0)` 비활성 + `DEFAULT_MAX_OUTPUT_TOKENS 4096 → 8192` + `finish_reason` 검사 + raw_text snippet 진단 로깅 + `DEFAULT_MODEL: gemini-2.0-flash → gemini-2.5-flash` (ADR-005) | step1~3, ADR-005, thinking-mode hotfix |
| `src/run_daily.py` | env `ANTHROPIC_API_KEY` → `GEMINI_API_KEY`, `CLAUDE_MODEL_ID` → `GEMINI_MODEL_ID` rename + `os.environ.get() or DEFAULT_MODEL` truthy fallback 가드 + `build_digest()` 인자 정리 | step3, empty-string fallback hotfix, footer-dup hotfix |
| `src/summarizer/render.py` | `build_digest()` / `_render_telegram_text()` 시그니처에서 `pages_url_template` 제거 + telegram_text 풋터 라인 삭제 (dispatcher 단일 책임) | footer-dup hotfix |
| `src/dispatchers/base.py` | `try/except RenderedDigest=Any` 제거 → `if TYPE_CHECKING:` 단순화 (mypy `[misc]` 회귀) | dispatcher mypy hotfix |
| `src/dispatchers/ops_alert.py`, `telegram_send.py` | `payload: dict[str, Any]` 명시 annotate (requests stubs `JsonType` 충돌 해소) | dispatcher mypy hotfix |

### 설정·문서·테스트 변경

| 파일 | 변경 요지 |
|---|---|
| `pyproject.toml` | `anthropic` 제거 + `google-genai>=0.3.0` 추가 |
| `.env.example` | `ANTHROPIC_API_KEY → GEMINI_API_KEY` / `CLAUDE_MODEL_ID → GEMINI_MODEL_ID=gemini-2.5-flash` |
| `.github/workflows/daily.yml` | env var rename 동기화 |
| `.gitignore` | `.claude/settings.local.json` 추가 (개인 PC 자동화 설정 분리) |
| `docs/canonical/ADR.md` | ADR-004 신설 (provider swap) + ADR-005 신설 (모델 ID swap) + ADR-001/004 상태 `superseded` |
| `docs/features/daily_digest/daily_digest_v1-requirements.md` | §8 환경변수 표 rename + 모델 ID `gemini-2.5-flash` + Changelog 2건 추가 |
| `docs/ops/secrets_setup.md` | Secrets 표 rename + ADR-005 출처 표기 + `GEMINI_MODEL_ID` 삭제해도 fallback 안전 명시 |
| `CLAUDE.md` | anti-pattern D 예시 갱신 (`GEMINI_API_KEY`) |
| `scripts/validate_doc_status.ps1` | `paused` phase 의 related_docs frozen 검증 면제 (hotfix, 의미 없는 검증 회피) |
| `scripts/render_sample_v4.py` | `pages_url_template` 인자 제거 |
| `tests/test_summarizer.py` | Anthropic mock → google-genai mock + finish_reason=STOP 명시 + `pages_url_template` 인자 제거 |
| `tests/test_dispatchers.py` | 회귀 방지 assertion 추가 (`payload["text"].count("전체 본문:") == 1`) |
| `phases/02-gemini-swap/` | step1~4 정의 + index.json + final-report (본 문서) |
| `phases/_hotfix-log/` | 핫픽스 로그 5건 추가 |

전체 diff 통계: 약 70개 파일 변경, 약 +500 / -50 lines (소형 phase 규모).

---

## 2. step별 산출물 + AC cross-check

| step | 상태 | 산출물 | AC 매핑 | dry-run 검증 |
|---|---|---|---|---|
| step1 | completed | ADR-004 + pyproject deps swap (anthropic → google-genai) | AC-5.5 | static (pyproject 빌드 OK) |
| step2 | completed | `summarizer/client.py` google-genai 재작성, JSON mode + response_schema + ResourceExhausted → `QuotaExceededError` 매핑 | AC-2.3 / 2.4 / 2.7 / 2.10 / 2.11 / 2.12 / 3.1 / 5.5 | unit test 100 passed (mock 응답 + quota error) |
| step3 | completed | env var rename 6개 위치 동시 (run_daily / workflow / secrets_setup / PRD / ARCHITECTURE / requirements / CLAUDE.md / .env.example) + validate_doc_status hotfix | AC-7.1 / 7.2 / 7.3 | static (validate_doc_status OK) |
| step4 | completed | tests/summarizer 회귀 + ruff/mypy 정합 + workflow yml 파싱 + **dry-run 6회차 실제 발송** | AC-1.3 + Phase DoD 전체 | run 26099906586 (22:22 KST, 2026-05-19) 정상 종료 — 27건 발송 + Pages publish + 사용자 시각 확인 ✓ |

phase DoD: 모두 충족 (모든 step status = completed, related_docs frozen 동기, hotfix log 5건 모두 기록, dry-run 실측 통과, ADR-005 신설).

---

## 3. pending_manual_qa_scenarios — 비어 있음

phase 02 끝 시점에 사용자가 직접 런타임에서 확인해야 할 시나리오: **0건**.

dry-run 6회차 (`run 26099906586`) 에서 사용자 시각 확인 4건 모두 통과:

- 운영자 단톡방 메시지 정상 도착 (3 카테고리 헤드라인 + Pages URL)
- Pages URL 클릭 → Apple v3 디자인 HTML 렌더
- 직원 단톡방 미발송 (dry-run 모드)
- 텔레그램 풋터 `전체 본문:` 정확히 1줄 등장 (중복 회귀 해소 확인)

---

## 4. phase 도중 발견·핫픽스 처리된 회귀 — 5건

| # | 회귀 | 원인 | 핫픽스 로그 |
|---|---|---|---|
| 1 | dispatcher 3건 mypy 회귀 (base.py `[misc]` + ops_alert/telegram_send `JsonType` 충돌) | phase 01 step6 잠복 (phase 02 swap 무관, pre-swap commit 에서도 재현) | [2026-05-19-dispatcher-mypy-typing.md](../_hotfix-log/2026-05-19-dispatcher-mypy-typing.md) |
| 2 | `gemini-2.0-flash` 404 NOT_FOUND (신규 사용자 deprecated) | Google 정책 변경 — ADR-004 의 "6개월 후 재검토 트리거" 첫 항목이 1일 만에 발동 | [2026-05-19-gemini-2-0-flash-deprecated.md](../_hotfix-log/2026-05-19-gemini-2-0-flash-deprecated.md) — ADR-005 신설 동반 |
| 3 | `GEMINI_MODEL_ID=""` → `SummarizerClient` ValueError | workflow `vars` 미정의 → env 빈 문자열 주입. `os.environ.get(key, default)` 가 빈 문자열 통과 (default 무시) | [2026-05-19-gemini-model-id-empty-string-fallback.md](../_hotfix-log/2026-05-19-gemini-model-id-empty-string-fallback.md) |
| 4 | char 307 위치 JSON truncate (`Unterminated string`) | Gemini 2.5 라인의 thinking-mode 가 default 활성 — `max_output_tokens` 4096 의 일부가 thinking 에 소진 | [2026-05-19-gemini-2-5-thinking-mode-truncate.md](../_hotfix-log/2026-05-19-gemini-2-5-thinking-mode-truncate.md) |
| 5 | 텔레그램 메시지 풋터 `전체 본문:` 라인 2줄 중복 | render 가 base URL 박고 dispatcher 가 final URL append → 합산 중복 | [2026-05-19-telegram-footer-duplicate-base-url.md](../_hotfix-log/2026-05-19-telegram-footer-duplicate-base-url.md) |

회고: 5건 중 **3건은 phase 02 swap 무관** (#1, #3, #5 — 잠재 버그), **2건은 swap 부산물** (#2, #4 — Google 정책 + Gemini 2.5 thinking-mode). phase 02 는 LLM provider swap 이라는 단일 책임이었으나 dry-run 검증 과정에서 phase 01 잠재 버그까지 함께 노출·해소된 부수 이익.

---

## 5. 다음 phase 진입 입력 — phase 01 step8

### phase 01 status 변경

- `paused` → `in_progress` (resumed_at: 2026-05-19)
- `active_step`: 7 → 8

### phase 01 step7 동시 closure

step7 (run_daily + workflow + secrets) 는 phase 02 step4 의 dry-run 6회차와 **동일한 코드 경로** 로 검증된 셈 — 같은 `run_daily.py` 본문, 같은 workflow yml, 같은 secrets 6개. step7 → `completed` (manual_qa_note 에 dry-run 참조 명시).

### step8 진입 입력

step8 의 작업 범위 (phase 01 step8.md 기준):

- `docs/canonical/PRD.md` 정시성 기준 갱신 (07:30 ± 15분 95%)
- `docs/canonical/ARCHITECTURE.md` 모듈 ownership 표 실측 갱신 + 성능 기준선 (Gemini 2.5-flash 응답 시간 측정값) 반영
- `docs/PHASE_MAP.md` phase status 동기화 (phase 01 in_progress, phase 02 completed)
- `docs/history/daily_digest/daily_digest_v1-manual-verification-record.md` 생성 — dry-run 6회차 결과 (27건, 1m30s, 풋터 1줄, AC 4건 통과) 기록
- `docs/implementation_status.md` 신규 시스템 등록 — daily_digest V1

step8 에 helper 명세 변경·신규 식별 키·save 버전 bump 등은 없음 (LLM swap 만으로 contract 변경 없음).

### 운영자에게 1주 dry-run 기록 시점 안내

- AC-4.3 fuzzy threshold 0.85 실측 — 1주일 일일 run 누적 후 false positive/negative 분포를 verification-record 에 추가 기록 (현재는 1회 sample).
- AC-6.4 단톡방 멤버 단계적 공개 — Day 0~6 운영자만, Day 7~13 3이사 추가, Day 14+ 전 직원. 시작일 (2026-05-19) 기록 → 2026-05-25 부터 3이사 초대 시점.

### 향후 LLM provider 재검토 트리거 (ADR-004 → ADR-005 승계)

- Gemini 2.5-flash 무료 tier 정책 변경 (한도 축소·종료·유료 전환)
- 신규 사용자 가입 차단 (ADR-005 의 발동 패턴 재발)
- Gemini 응답 품질이 직원 피드백에서 명시적으로 문제 제기됨
- Google API 의 한국 IP·관할 정책 변경
- **추가** (ADR-005 후속 — 본 phase 회고에서 식별): Gemini 라인의 thinking-mode 정책 변경 (response_schema 호환 변화·기본값 변경)

trigger 시 ADR-006 으로 재검토 (Gemini 3 라인 / Groq / paid tier 비교).

---

## 6. 자동화 인프라 변경 (phase 도중 도입)

phase 02 종료 시점에 운영자 PC 에 다음 자동화 인프라 1회 셋업 완료:

- `gh` CLI 2.92 설치 (winget)
- `gh auth login` 완료 (`repo` + `workflow` scope)
- `.claude/settings.local.json` 작성 (PowerShell `gh *` 12개 명령 permission 등록, gitignore 처리)

향후 phase 부터 PR 생성·merge·workflow 트리거·실행 로그 조회까지 Claude 가 한 사이클로 자동 수행 가능. 사용자 액션은 외부 SaaS UI (Google AI Studio / GitHub Settings) 작업에만 한정.
