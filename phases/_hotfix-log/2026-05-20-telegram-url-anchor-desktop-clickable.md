# 텔레그램 풋터 URL Desktop 클라이언트 auto-linkify 누락 — 명시 `<a>` 앵커로 전환

날짜: 2026-05-20
규모: 핫픽스 (2파일 + 회귀 테스트 1건, 계약 변경 없음)

## 증상

사용자(farmboss5774@gmail.com) 수동 확인: 2026-05-20 다이제스트 텔레그램 본문 끝 `전체 본문: https://karajaku.github.io/f_trendnewsbot/digest/2026-05-20.html` 라인이 **Telegram Desktop (Windows 네이티브)** 에서 클릭 가능한 하이퍼링크로 표시되지 않음 (plain text 로만 보임). 모바일·웹 클라이언트에서는 정상 자동 링크화됨.

## 원인

[src/dispatchers/telegram_send.py:_build_text](src/dispatchers/telegram_send.py) 가 `parse_mode="HTML"` 환경에서 URL 을 plain 문자열(``전체 본문: {pages_url}``)로만 append. Telegram 클라이언트는 HTML parse mode 에서도 후처리로 plain URL 을 auto-linkify 하지만, 본문에 다수의 특수문자(``📰 ⚡ ⭐ ① ② ③ ·``) 가 섞인 메시지에서 Desktop 클라이언트가 URL boundary 인식을 일관되게 처리하지 못하는 케이스 존재. iOS/Android/Web 은 정상 동작 → 클라이언트별 entity 후처리 차이.

`disable_web_page_preview=True` 는 미리보기 카드만 끄는 옵션이라 링크 자체와 무관 — 원인 아님.

## 변경

- [src/dispatchers/telegram_send.py:21-26](src/dispatchers/telegram_send.py#L21-L26) — `import html as _html` 추가 (URL 안전 escape 용).
- [src/dispatchers/telegram_send.py:_build_text](src/dispatchers/telegram_send.py) — append 형식 변경:
  - 기존: `f"{telegram_text}{sep}전체 본문: {pages_url}"`
  - 변경: `f'{telegram_text}{sep}전체 본문: <a href="{pages_url_safe}">{pages_url_safe}</a>'` — `_html.escape(pages_url, quote=True)` 통과로 `&`·`"` 안전 처리. parse_mode 가 이미 HTML 이라 추가 비용 없음.
  - docstring 에 Desktop 클라이언트 호환 사유 명시.
- [tests/test_dispatchers.py:test_send_payload_contains_disable_web_page_preview_and_parse_mode](tests/test_dispatchers.py) — 회귀 방지 assertion 1건 추가: `'전체 본문: <a href="...">...</a>'` 정확한 앵커 형태 검증.

## 수동 확인

- [ ] `python -m pytest -q tests/test_dispatchers.py` → 통과 (회귀 0)
- [ ] `python -m ruff check src/dispatchers/telegram_send.py` → All checks passed
- [ ] `python -m mypy src/dispatchers/telegram_send.py` → Success
- [ ] PR merge 후 다음 정기 발송 (또는 dry-run) 으로 텔레그램 단톡방 본문 풋터 URL 이 Desktop 에서 파란색 클릭 가능 링크로 표시되는지 사용자 시각 확인.

## 회귀 위험

- 본문 byte 수: `<a href="URL">URL</a>` 래핑으로 URL 길이 × 2 + 약 18 bytes 증가. GitHub Pages URL (~70 bytes) 기준 약 158 bytes 증가. 4096 한도 대비 무시 가능. 안전망 `_TELEGRAM_MAX_BYTES` 변경 없음.
- dedup 검사 (`pages_url in telegram_text`) 는 raw URL 문자열 매칭 → 앵커 안 href 와 anchor text 양쪽에 raw URL 이 그대로 포함되므로 idempotent 유지.
- `parse_mode="HTML"` 이미 사용 중 → 신규 의존성·옵션 없음.
- `pages_url` 에 `&` 가 포함된 경우 (현재 GitHub Pages URL 패턴에는 없음) `&amp;` 로 escape 되어 href 와 raw URL dedup 문자열이 불일치하지만, render 가 final URL 을 박지 않는 현재 설계상 dispatcher 가 두 번 호출되는 경로 없음 → 실제 영향 없음.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음 (`_build_text` private, `send()` 외부 signature 동일)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음
