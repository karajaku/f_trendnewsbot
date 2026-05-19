# Gemini 2.5 thinking-mode 토큰 소진 truncate 회귀 — `thinking_budget=0` + max_output_tokens 8192 + finish_reason 검사

날짜: 2026-05-19
규모: 핫픽스 (1 파일, 계약 변경 없음)

## 증상

ADR-005 swap + GEMINI_MODEL_ID fallback 핫픽스 후 dry-run 재실행 (2026-05-19 21:09 KST, master 에 핫픽스 merge 완료 상태) 에서 운영자 단톡방에 다음 alert 도착:

```
RuntimeError: Gemini 응답 JSON 파싱 실패:
Unterminated string starting at: line 10 column 13 (char 307)
  File ".../src/summarizer/client.py", line 187, in _parse_response_json
```

핵심 단서: **char 307** — 한국어 약 100자 수준의 매우 짧은 위치에서 JSON 이 truncate. 단순 `max_output_tokens=4096` 한도 도달이면 한국어 7000~10000자 이후 잘려야 하므로, 토큰 한도 도달이 아니라 다른 원인으로 응답이 일찍 종료된 것으로 진단.

## 원인

**Gemini 2.5 라인의 thinking-mode 가 default 활성**. `ThinkingConfig.thinking_budget` 의 default 값이 모델 의존이며 2.5-flash 는 thinking 활성 + 자동 budget 할당. thinking 토큰이 `max_output_tokens` 의 일부 (수천 토큰) 를 소진하면 실제 JSON 응답이 그만큼 적게 할당되어 짧게 truncate.

ADR-004 시점의 `gemini-2.0-flash` 는 thinking-mode 미적용이라 4096 토큰 모두 응답에 할당 — 회귀 미발생. ADR-005 후 `gemini-2.5-flash` 로 전환하면서 thinking-mode 가 새 변수로 등장.

JSON 출력은 `response_mime_type="application/json"` + `response_schema=_RESPONSE_SCHEMA` 로 형식이 강제되므로 reasoning (thinking) 의 효과가 작다. 비활성이 응답 토큰 보장 측면에서 안전.

## 변경

`src/summarizer/client.py` 3건:

1. **`DEFAULT_MAX_OUTPUT_TOKENS` 상향** (line 46-51): 4096 → 8192. AC-5.5 의 20k 상한 내. 3 카테고리 × 다수 items × summary/score/company_impact + category_headlines + tl_dr_box 의 JSON 출력에 여유.

2. **`ThinkingConfig(thinking_budget=0)` 추가** (line 427-432 인근): `GenerateContentConfig` 에 `thinking_config=ThinkingConfig(thinking_budget=0)` 명시. 0 은 thinking 완전 비활성. response_schema 가 형식 강제하므로 품질 영향 작음.

3. **finish_reason 검사 + raw_text snippet 진단 로깅** (line 466-481 인근, `_parse_response_json` 직전): `response.candidates[0].finish_reason` 가 `STOP` 이 아니면 (`MAX_TOKENS` / `SAFETY` / `RECITATION` 등) `tokens_out`·`raw_len`·`head/tail snippet` 을 포함한 명확한 `RuntimeError` 로 raise. 추가로 `_parse_response_json` 의 JSONDecodeError 시에도 snippet 포함.

## 수동 확인

- [x] `python -m pytest -q` → 100 passed
- [x] `python -m ruff check src/` → All checks passed
- [x] `python -m mypy src/` → Success (34 files)
- [x] `ThinkingConfig` import 확인 — google-genai 의 `types.ThinkingConfig` 가용
- [x] `FinishReason.STOP` enum 값 확인 — `getattr(reason, "value", None)` 패턴이 enum·string 양쪽 호환

## 회귀 위험

- thinking 비활성으로 인한 분석 품질 저하 가능성: 점수·company_impact 의 추론 깊이가 일부 약화될 수 있음. 영향이 직원 피드백에서 명시되면 `thinking_budget=512~1024` 정도의 작은 값으로 재조정 검토.
- `_RESPONSE_SCHEMA` (`required` 필드, enum 등) 는 thinking 없이도 형식 강제 가능 → JSON 파싱 실패 위험은 thinking 활성 대비 오히려 낮음.
- finish_reason 검사가 enum 또는 string 표현 모두 처리 (`getattr(value)` + `str()` fallback) — google-genai SDK 의 향후 표현 변경에도 robust.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음 (`SummarizerClient.summarize()` 동일)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음

## 후속

다음 dry-run (4번째 시도) 에서 통과 여부 확인. 통과 시 phase 02 종료 + phase 01 step7 동시 통과 → step8 진입.
재차 실패 시 추가될 finish_reason / snippet 정보로 정확한 원인 진단.
