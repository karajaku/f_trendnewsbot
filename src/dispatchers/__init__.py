"""dispatcher 패키지 — Pages publish + 텔레그램 Bot API + 운영자 alert (ADR-003).

서브모듈:
- `base`: `SendResult` / `Dispatcher` Protocol / `PagesPublishError` / `TelegramSendError`.
- `pages_publish`: GitHub Pages 정적 호스팅 (commit·push + HTTP 200 polling).
- `telegram_send`: 텔레그램 Bot API `sendMessage` 호출 + retry 1회.
- `ops_alert`: 운영자 전용 chat 짧은 alert (재시도 없음 — AC-5.4 무한루프 방지).

main()(step7) 이 호출 순서를 강제한다 (AC-5.6): Pages publish → 텔레그램 발송.
"""

from .base import (
    Dispatcher,
    PagesPublishError,
    SendResult,
    TelegramSendError,
)

__all__ = [
    "Dispatcher",
    "PagesPublishError",
    "SendResult",
    "TelegramSendError",
]
