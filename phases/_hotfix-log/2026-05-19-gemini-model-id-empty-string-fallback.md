# `GEMINI_MODEL_ID` 빈 문자열 fallback 가드 — `os.environ.get(...) or DEFAULT_MODEL`

날짜: 2026-05-19
규모: 핫픽스 (1 코드 파일 + 2 안내 문서, 계약 변경 없음)

## 증상

ADR-005 swap 후 dry-run 재실행 (2026-05-19 19:55 KST, 사용자가 안내대로 `GEMINI_MODEL_ID` Variable 삭제) 에서 운영자 단톡방에 다음 alert 도착:

```
ValueError: model 은 비어있지 않은 문자열이어야 합니다.
  File ".../src/run_daily.py", line 153, in main
    model=os.environ.get("GEMINI_MODEL_ID", DEFAULT_MODEL),
  File ".../src/summarizer/client.py", line 373, in __init__
    raise ValueError("model 은 비어있지 않은 문자열이어야 합니다.")
```

ADR-005 무관 — 잠재 버그가 트리거됨.

## 원인

`.github/workflows/daily.yml:35`:

```yaml
GEMINI_MODEL_ID: ${{ vars.GEMINI_MODEL_ID }}
```

GitHub Actions Variables 의 `GEMINI_MODEL_ID` 가 미정의면 `vars.GEMINI_MODEL_ID` 는 **빈 문자열** 로 evaluate. workflow env 에 `GEMINI_MODEL_ID=""` 가 주입.

`src/run_daily.py:153`:

```python
model=os.environ.get("GEMINI_MODEL_ID", DEFAULT_MODEL),
```

`os.environ.get(key, default)` 는 **key 부재 시에만** default 적용. key 가 존재하면 빈 문자열도 그대로 반환. `SummarizerClient(model="")` → 의도된 `ValueError`.

ADR-005 안내 ("var 삭제 시 코드 default fallback 자동 적용") 의 가정이 잘못돼 있었음 — workflow yml 의 `${{ vars.X }}` 와 `os.environ.get()` 조합 때문에 미정의 var 가 빈 문자열로 통과되는 점을 놓침.

## 변경

- `src/run_daily.py:151-159` — `os.environ.get(...)` 결과를 `or DEFAULT_MODEL` 로 truthy 가드. 변수명 `model_id` 로 추출. 빈 문자열·None 모두 default fallback.
- `src/run_daily.py:66-74` `secrets_check()` docstring — "summarizer 측에 fallback" → "main() 호출부에서 truthy fallback" 정정.
- `docs/ops/secrets_setup.md:119` — Variables 표 `GEMINI_MODEL_ID` 행에 "삭제해도 안전 — `run_daily.py` 가 빈 문자열을 DEFAULT_MODEL 로 fallback" 한 줄 추가.
- `phases/02-gemini-swap/step4.md:33` — 사용자 운영자 액션 가이드의 Variables 안내에 동일 fallback 동작 명시.

## 수동 확인

- [x] `python -m pytest -q` → 100 passed (회귀 0)
- [x] `python -m ruff check src/` → All checks passed
- [x] `python -m mypy src/` → Success (34 files)
- [x] `Grep "os.environ.get.*GEMINI_MODEL_ID"` → run_daily.py 한 곳만, truthy 가드 적용 확인.

## 회귀 위험

- 비공식 환경 (로컬 `.env` 의 `GEMINI_MODEL_ID=`) 에서도 동일 truthy fallback 적용 → 더 robust.
- `DEFAULT_MODEL` 상수 (ADR-005 후 `gemini-2.5-flash`) 가 단일 진실 — 향후 ADR 갱신 시 1줄만 변경하면 됨.
- 호출 시그니처 무변경 (`SummarizerClient(api_key, model)` 동일).

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음

## 후속

이 가드는 phase 02 step4 dry-run 재실행 (3번째 시도) 에서 통과 여부 확인. 통과 시 phase 02 종료 + phase 01 step7 동시 통과.
