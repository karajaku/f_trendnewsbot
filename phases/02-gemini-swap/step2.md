# Phase 02 · Step 2 — summarizer/client.py 재작성 (Gemini SDK)

> 목적: `SummarizerClient.summarize() → SummarizeResult` 인터페이스를 보존하면서 내부를 Anthropic SDK에서 google-genai SDK로 swap.
> 주 담당 에이전트: tnb-implementer

## 읽을 파일

- `src/summarizer/client.py` (현재 Anthropic 구현)
- `src/summarizer/quota.py` (QuotaExceededError·QuotaTracker — 그대로 유지)
- `src/summarizer/render.py` (caller — 인터페이스 영향 확인)
- `src/run_daily.py` (caller — 환경변수 이름은 step3에서 처리)
- `prompts/summarize.md` (system prompt — 본문 재사용 가능, 변경 없음)
- `docs/features/daily_digest/daily_digest_v1-requirements.md` §6-5 (요약 출력 schema)

## 작업 범위

1. `src/summarizer/client.py` 재작성:
   - import: `from anthropic import Anthropic` → `from google import genai` + `from google.genai import types`
   - `DEFAULT_MODEL` 상수: `"claude-haiku-4-5-20251001"` → `"gemini-2.0-flash"`
   - `SummarizerClient.__init__`:
     - `Anthropic(api_key=...)` → `genai.Client(api_key=...)`
     - logger의 model·key_prefix 표기는 동일 유지
   - `SummarizerClient.summarize()`:
     - `client.messages.create(...)` → `client.models.generate_content(model=..., contents=user_text, config=...)`
     - `config=types.GenerateContentConfig(system_instruction=system_prompt, response_mime_type="application/json", response_schema=...)` 로 JSON mode 강제
     - response_schema 정의: items[].{id, score, summary, company_impact} + category_headlines.{ai_trend, agri_distribution, farmboss_keyword}
     - Anthropic prompt caching (`cache_control: ephemeral`) 제거 — Gemini Context Caching은 별도 API(`client.caches.create`) 라 V1 단순성 위해 미사용
     - response 본문 추출: `response.text` (또는 `response.candidates[0].content.parts[0].text`)
     - token usage 추출: `response.usage_metadata.prompt_token_count / candidates_token_count`
     - `_strip_markdown_fence`·`_parse_response_json`·`_validate_and_filter_items`·`_validate_category_headlines` 헬퍼는 그대로 재사용 (Gemini JSON mode가 schema 보장하지만 방어선 유지)
2. `_quota_error_from_resource_exhausted` 신규 헬퍼:
   - `google.api_core.exceptions.ResourceExhausted` (또는 google-genai의 `google.genai.errors.ClientError` 중 429) 잡아서 `QuotaExceededError` 로 변환
   - run_daily.py의 `except QuotaExceededError` 분기가 그대로 동작하도록 (AC-5.3)
3. 본 모듈 안에서만 변경. `src/run_daily.py`·`workflows/daily.yml`·docs는 step3에서.
4. ruff 통과: `python -m ruff check src/summarizer/client.py`.

## Acceptance Criteria

- AC-S2.1: `SummarizerClient.summarize()` 시그니처와 `SummarizeResult` dataclass 형태가 step5(phase 01)와 100% 동일.
- AC-S2.2: 응답이 빈 items / 형식 위반 시에도 `dropped_items` 만 누적되고 전체 raise 없음 (AC-2.10 부분 성공).
- AC-S2.3: rate limit / quota 초과(429 또는 ResourceExhausted) 시 `QuotaExceededError` raise → run_daily.py의 exit 2 분기에 도달.
- AC-S2.4: ruff·mypy 통과.

## 금지

- env var 이름 변경 (step3).
- `prompts/summarize.md` 본문 수정 (Gemini JSON mode가 동일 schema 받음).
- `src/summarizer/quota.py` 변경 (QuotaTracker hard cap 정책은 LLM provider 무관).
- `render.py`·`run_daily.py` 호출 코드 수정.

## 수동 테스트

- 없음 (qa_blocking: false). step4에서 dry-run 통합 검증.

## QA owner

- 정적 검증: ruff·mypy + 기존 `tests/summarizer/` 가 있다면 mock 갱신 (Anthropic mock → Gemini mock).
