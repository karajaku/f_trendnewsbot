# dispatcher 3건 mypy 회귀 핫픽스 — base.py 의 type-only import + payload dict[str, Any] 명시

날짜: 2026-05-19
규모: 핫픽스 (3파일, 계약 변경 없음)

## 증상

phase 02 step4 자동 검증 단계에서 `python -m mypy src/` 실행 시 다음 3건 실패:

```
src\dispatchers\base.py:23: error: Cannot assign to a type  [misc]
src\dispatchers\base.py:23: note: Error code "misc" not covered by "type: ignore[assignment]" comment
src\dispatchers\ops_alert.py:162: error: Argument "json" to "post" has incompatible type "dict[str, object]"; expected "JsonType"  [arg-type]
src\dispatchers\telegram_send.py:162: error: Argument "json" to "post" has incompatible type "dict[str, object]"; expected "JsonType"  [arg-type]
```

phase 02 swap **이전** commit (7461eed~1) 에서도 동일 회귀 재현 확인 → phase 01 step6 dispatchers 도입 시점부터 잠복하던 회귀. step2 commit 노트의 "mypy 통과" 기록은 실제 검증 누락으로 추정. phase 02 swap 과 무관.

## 원인

1. `src/dispatchers/base.py:23` — `try: from ... import RenderedDigest / except: RenderedDigest = Any` 패턴이 모듈 수준에서 type 에 변수를 할당하려 함. mypy 가 `[misc]` 로 판정하는데 기존 `# type: ignore[assignment]` 가 해당 코드 미커버.
2. `src/dispatchers/ops_alert.py:162`, `src/dispatchers/telegram_send.py:162` — `payload = {...}` 의 dict literal value 가 혼합 타입 (`int | str, str, bool`) 이라 mypy 가 `dict[str, object]` 로 추론. requests stubs 의 `post(json=...)` 가 narrow 한 `JsonType` 을 기대해 충돌.

## 변경

- `src/dispatchers/base.py:16-22` — `try/except` 폴백 제거, `if TYPE_CHECKING:` 으로 단순화. 런타임 변수 `RenderedDigest` 가 사라지지만 Protocol 메서드는 이미 `"RenderedDigest"` forward reference 형태라 영향 없음.
- `src/dispatchers/ops_alert.py:155` — `payload: dict[str, Any] = {...}` 명시 annotate. `Any` 는 같은 파일에서 이미 import 됨.
- `src/dispatchers/telegram_send.py:143` — 동일 패턴, `payload: dict[str, Any] = {...}` 명시 annotate.

## 수동 확인

- [x] `python -m mypy src/` → `Success: no issues found in 34 source files`
- [x] `python -m pytest -q` → 100 passed (회귀 0)
- [x] `python -m ruff check src/` → All checks passed
- [x] visible text 변경 없음 (catalog/locale 무관)

## 회귀 위험

- `RenderedDigest = Any` 폴백 제거로 `summarizer.render` import 실패 시 base.py 가 import error 가 나는 시나리오가 이론적으로 있으나, base.py 는 모든 dispatcher 호출 경로에서 summarizer 와 함께 진입하므로 의존성이 끊어진 상태로 base.py 단독 import 되는 경로 없음.
- payload type 명시는 런타임 동작 무영향, dict 키·값 그대로 유지.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음 (Protocol 시그니처 동일)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음
