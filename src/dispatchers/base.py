"""dispatcher 도메인의 단일 진실 — `SendResult` / 예외 + `Dispatcher` Protocol.

CRITICAL #4 (외부 소스 장애 격리) · #5 (시크릿 평문 노출 금지) 의 코드 측 방어선.

- 모든 dispatcher 는 `SendResult` 를 반환하거나 본 모듈의 예외 (`PagesPublishError` /
  `TelegramSendError`) 를 raise 한다. main() 통합 진입점이 `SendResult.success=False`
  를 운영자 alert 로 라우팅한다 (AC-5.4 · §7).
- `Dispatcher` Protocol 시그니처는 `send(digest: RenderedDigest) -> SendResult` —
  Pages publish 는 별도 시그니처(pages_url 반환)이므로 Protocol 을 따르지 않고 직접
  함수 형태. 텔레그램·ops_alert 는 모두 Protocol 호환.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, Protocol

# `RenderedDigest` 는 type-only import — 순환 import 방지.
# 실행 시점에는 본 base.py 가 summarizer 를 끌어오지 않는다.
if TYPE_CHECKING:
    from src.summarizer.render import RenderedDigest  # noqa: F401


@dataclass(frozen=True)
class SendResult:
    """발송 1회 결과 — main() 이 success 분기에 사용.

    Attributes:
        success: 발송 성공 여부.
        kind: ``"pages"`` | ``"telegram"`` | ``"ops_alert"``.
        error_kind: 실패 분류 라벨 (`auth` / `bad_request` / `network` /
            `http_5xx` / `too_long` / `timeout` / `other`). 성공 시 ``None``.
        error_message: 사람 읽을 수 있는 짧은 오류 메시지. 시크릿 평문 금지.
        retried: 재시도 횟수 (0 또는 1). AC-5.4 상한 1.
        extra: 부가 메타. Pages 는 ``{"pages_url": "..."}``.
    """

    success: bool
    kind: str
    error_kind: Optional[str] = None
    error_message: Optional[str] = None
    retried: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class Dispatcher(Protocol):
    """텔레그램·ops_alert 어댑터가 따르는 최소 Protocol.

    Pages publish 는 시그니처가 다르므로(외부 인자 다수) Protocol 외 함수 형태로 둔다.
    """

    def send(self, digest: "RenderedDigest") -> SendResult:  # pragma: no cover
        ...


class PagesPublishError(RuntimeError):
    """Pages publish 4단계 (write/commit/push/verify) 중 1개라도 실패하면 raise.

    Attributes:
        stage: ``"write"`` | ``"commit"`` | ``"push"`` | ``"verify"``.
        message: 짧은 오류 메시지 (시크릿 평문 금지).
    """

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        self.message = message
        super().__init__(f"[{stage}] {message}")


class TelegramSendError(RuntimeError):
    """텔레그램 Bot API 호출 실패 (retry 1회 후에도 실패) 시 raise.

    Attributes:
        error_kind: ``"auth"`` (401) | ``"bad_request"`` (400) |
            ``"network"`` (timeout/connection) | ``"http_5xx"`` |
            ``"too_long"`` (4096자 초과) | ``"other"``.
        message: 짧은 오류 메시지 (token/chat_id 평문 금지).
    """

    def __init__(self, error_kind: str, message: str) -> None:
        self.error_kind = error_kind
        self.message = message
        super().__init__(f"[{error_kind}] {message}")
