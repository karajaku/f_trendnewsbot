# Gemini 모델 ID swap — `gemini-2.0-flash` deprecated → `gemini-2.5-flash` (ADR-005)

날짜: 2026-05-19
규모: 핫픽스 (5+1 파일, 단순 default 값 swap, 계약 변경 없음 — 단 ADR-005 신설을 동반)

## 증상

phase 02 step4 dry-run (2026-05-19 19:36 KST, 신규 GCP project + 신규 `GEMINI_API_KEY` 발급 후 재실행) 에서 운영자 단톡방에 다음 alert 도착:

```
ClientError 404 NOT_FOUND
"This model models/gemini-2.0-flash is no longer available to new users.
 Please update your code to use a newer model for the latest features and improvements."
```

직전 시도 (이전 project, 같은 모델) 는 `limit: 0` quota error 였다 — 두 증상 모두 신규 사용자에게 2.0-flash 사용권이 부여되지 않는 Google 정책 변경.

## 원인

`docs/canonical/ADR.md` ADR-004 의 "6개월 후 재검토 트리거" 첫 번째 항목 (`Gemini 무료 tier 정책 변경`) 이 1일 만에 발동. Google 이 2.0-flash 의 신규 사용자 가입 창구를 닫고 2.5 라인 (현재 `gemini-2.5-flash`) 으로 유도. provider (Google Gemini) 결정 자체는 유효 — SDK·prompt·JSON mode 자산 그대로 재사용 가능.

## 변경

활성 default 5건 + 사용자 액션 가이드 1건 일괄 swap:

- `src/summarizer/client.py:42` — `DEFAULT_MODEL: str = "gemini-2.0-flash"` → `"gemini-2.5-flash"` + ADR-005 출처 코멘트.
- `tests/test_summarizer.py:336` — quota error mock fixture 의 모델명 문자열 일관성 swap.
- `docs/features/daily_digest/daily_digest_v1-requirements.md:369` — §8 환경변수 표 `GEMINI_MODEL_ID` 기본값 표기 + Changelog 한 줄 추가.
- `docs/ops/secrets_setup.md:119` — Variables 표 `GEMINI_MODEL_ID` 값 + ADR-005 출처 표기.
- `.env.example:22` — default 값 + ADR-005 출처 코멘트.
- `phases/02-gemini-swap/step4.md:33` — 사용자 운영자 액션 가이드 (Variables 기본값 표기) 갱신.

신규 작성:
- `docs/canonical/ADR.md` ADR-005 신설 (76줄). ADR-004 status `accepted` → `superseded` (provider 결정은 유효).
- 본 hotfix log.

## 수동 확인

- [x] `python -m pytest -q` → 100 passed (test fixture 모델명 swap 후 회귀 없음)
- [x] `python -m ruff check src/` → All checks passed
- [x] `python -m mypy src/` → Success (34 files)
- [x] `Grep gemini-2\.0-flash` → 잔여 매칭 모두 ADR 본문·hotfix log·phase ledger 의 audit trail 만 (활성 default 0건)

## 회귀 위험

- `gemini-2.5-flash` 가 사용자 GCP project 에서 가용해야 함. 사용자 액션 (4) 단계에서 AI Studio model picker 또는 dry-run 결과로 검증. 만약 2.5-flash 도 가용 불가면 → ADR-005 갱신 + 후속 ADR-006 발행 (Groq / paid tier / 2.5-flash-lite 등 재검토).
- `tests/test_summarizer.py` 의 mock fixture 모델명은 호출 검증과 무관하므로 회귀 영향 없음.
- `prompts/summarize.md` 본문은 모델 ID 와 무관 → 변경 없음.
- caller (`run_daily.py`, `render.py`) 의 `summarize()` 시그니처 무변경.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음 (`SummarizeResult` dataclass·`sent.jsonl` 스키마 불변)
- [x] 공개 함수 시그니처 변경 없음 (`SummarizerClient.summarize()` 동일)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음

> Note: ADR-005 신설을 동반하지만 본질은 default 값 1개의 swap. 코드 변경 자체는 hotfix 규모. ADR 은 결정의 audit trail 로서 별도 산출물.
