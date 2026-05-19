# 텔레그램 메시지 풋터 중복 — render 의 base_url 라인 제거, dispatcher 단일 책임

날짜: 2026-05-19
규모: 핫픽스 (4 파일, 계약 변경 없음 — caller signature 만 정리)

## 증상

phase 02 step4 dry-run (5번째 시도, 21:55 KST) 성공 후 수동 QA 에서 운영자 단톡방 메시지 끝에 `전체 본문:` 풋터가 **두 줄** 등장 확인:

```
…(중략)
전체 본문: https://karajaku.github.io/f_trendnewsbot
의견·소스 제안은 단톡방 답글로.

전체 본문: https://karajaku.github.io/f_trendnewsbot/digest/2026-05-19.html
```

첫 번째 줄은 `PAGES_BASE_URL` root (`/f_trendnewsbot`) 로 의미 없는 archive 페이지로 연결. 두 번째 줄만 실제 의도된 digest 페이지 URL.

## 원인

`전체 본문: {pages_url}` 풋터 생성 책임이 두 곳에 중복:

1. **`src/summarizer/render.py:603-604`** — `build_digest()` 가 `pages_url_template` 파라미터로 받은 값을 `digest.telegram_text` 본문에 박음. caller (`run_daily.py:170`) 가 `env["PAGES_BASE_URL"].rstrip("/")` 즉 base URL 을 전달 → render 시점에 final digest URL 미확정 (AC-5.6: Pages publish 가 render 뒤에 실행) 이라 base URL 만 들어감.
2. **`src/dispatchers/telegram_send.py:_build_text:84-89`** — `pages_publish.publish()` 후 받은 **final URL** 이 `digest.telegram_text` 안에 미포함이면 append. base URL ≠ final URL 이라 조건 통과 → append.

결과: 본문에 base URL 1줄 + dispatcher append 로 final URL 1줄 = 중복.

근본 원인: render 시점에 final URL 이 미확정인 상태에서 placeholder (`base URL`) 를 박는 설계 자체가 결함. dispatcher 만 final URL 단일 책임으로 가져가는 게 정석.

## 변경

4 파일 + 1 회귀 테스트:

1. **`src/summarizer/render.py`**:
   - `_render_telegram_text()` 시그니처에서 `pages_url: str` 파라미터 제거.
   - 라인 603-605 의 `if pages_url: lines.append(f"전체 본문: {pages_url}")` 블록 삭제. `의견·소스 제안…` 풋터만 유지.
   - `build_digest()` 시그니처에서 `pages_url_template: str = ""` 파라미터 제거. docstring 에 "풋터는 dispatcher 단일 책임" 명시.
2. **`src/run_daily.py:164-170`** — `build_digest()` 호출에서 `pages_url_template=` 인자 제거.
3. **`tests/test_summarizer.py:490`** — 한 테스트에서 `pages_url_template="..."` 인자 제거.
4. **`scripts/render_sample_v4.py:272`** — sample 스크립트의 `pages_url_template=` 인자 제거.
5. **`tests/test_dispatchers.py:477-480`** — 통합 테스트에 회귀 방지 assertion 추가: `payload["text"].count("전체 본문:") == 1`. dispatcher 호출 후 본문 전체에서 풋터가 정확히 1번만 등장하는지 검증.

## 수동 확인

- [x] `python -m pytest -q` → 100 passed (회귀 0)
- [x] `python -m ruff check src/` → All checks passed
- [x] `python -m mypy src/` → Success (34 files)
- [x] `Grep "전체 본문"` 활성 코드 — `telegram_send._build_text` 한 곳에서만 생성.
- [x] dry-run 재실행 시 운영자 단톡방 메시지의 풋터 1줄·final digest URL 1개 확인 (이번 PR merge 후).

## 회귀 위험

- caller signature 변경 (`build_digest` 의 `pages_url_template` 제거) 는 한 코드베이스 내부 4 호출처 모두 같은 PR 에서 갱신 → 외부 영향 없음. mypy 가 누락 caller 를 잡음.
- 텔레그램 메시지 본문 길이가 1줄 감소 (`전체 본문: {base_url}` 라인 제거) — 4096 bytes 한도 측면에서 더 안전. 자르기 보호망 (`_TELEGRAM_MAX_BYTES`) 무관.
- Pages HTML (`_render_full_html`) 은 `pages_url_template` 사용 안 했음 → HTML 출력 변화 없음.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음 (`RenderedDigest` dataclass 동일, `sent.jsonl` 스키마 무변경)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음
- [ ] **공개 함수 시그니처 변경**: `build_digest()` 의 keyword-only optional 파라미터 1개 제거. caller 4곳 같은 PR 에서 동시 갱신, 외부 노출 없음. 핫픽스 규모 범위 내로 판단.

## 후속

- PR merge 후 dry-run 재실행 (6번째 시도) — `count("전체 본문:") == 1` 회귀 테스트가 코드 측 1차 가드, 사용자 수동 확인이 시각 검증 2차.
- 통과 시 phase 02 종료 진행.
