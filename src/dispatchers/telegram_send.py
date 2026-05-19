"""텔레그램 Bot API `sendMessage` — 직원 다이제스트 단톡방 발송 + retry 1회.

ADR-003 의 코드 측 구현. AC-2.3-A · 5.4 · 6.1 매핑.

- 메시지 본문: `digest.telegram_text + "\\n\\n전체 본문: {pages_url}"` — Pages publish 가 성공해
  URL 이 확정된 후에만 호출된다 (AC-5.6, main() 이 순서 강제).
- `parse_mode="HTML"`, `disable_web_page_preview=True` 고정 (AC-2.3-A).
- text 길이는 byte 길이 ≤ 4096 검증 (텔레그램 한도). 초과 시 `TelegramSendError("too_long")` —
  실제 send 호출 안 함.
- 응답 코드 분류:
    * 200 → success.
    * 401 → `auth` (토큰 무효).
    * 400 → `bad_request` (chat_id 무효 등).
    * timeout / connection error → `network` (retry 가능).
    * 5xx → `http_5xx` (retry 가능).
    * 그 외 → `other`.
- retry: 1회 (AC-5.4). 두 번째 실패 시 `TelegramSendError`.
- 토큰·chat_id 평문 로깅 금지 — `mask_key` 통과.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from src.lib.logging_setup import mask_key

from .base import SendResult, TelegramSendError

logger = logging.getLogger(__name__)

# 텔레그램 메시지 한도 — bytes 기준 (utf-8) 4096.
_TELEGRAM_MAX_BYTES = 4096

# Bot API endpoint template.
_BOT_API_URL_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"

# retry 대상 error_kind — 일시 장애.
_RETRYABLE_ERROR_KINDS: frozenset[str] = frozenset({"network", "http_5xx"})


class ConfigError(Exception):
    """chat_id 가 int 변환 불가 등 환경설정 오류 — main() 이 운영자 alert 로 라우팅."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def _classify_response(status_code: int | None) -> tuple[str, str]:
    """HTTP status → (error_kind, human_message)."""
    if status_code == 401:
        return "auth", "텔레그램 봇 토큰 인증 실패 (401)"
    if status_code == 400:
        return "bad_request", "텔레그램 요청 거부 (400) — chat_id 또는 본문 형식 확인"
    if status_code is not None and 500 <= status_code < 600:
        return "http_5xx", f"텔레그램 서버 오류 ({status_code})"
    return "other", f"텔레그램 응답 코드 {status_code}"


def _coerce_chat_id(chat_id: int | str) -> int:
    """chat_id 를 int 로 강제 변환 — 텔레그램 Bot API 가 음수 정수 chat_id 사용."""
    if isinstance(chat_id, int):
        return chat_id
    if isinstance(chat_id, str):
        s = chat_id.strip()
        if not s:
            raise ConfigError("TELEGRAM_CHAT_ID 가 빈 문자열입니다.")
        try:
            return int(s)
        except ValueError as e:
            raise ConfigError(
                f"TELEGRAM_CHAT_ID int 변환 실패 (현재 값 prefix={s[:3]!r}...)"
            ) from e
    raise ConfigError(f"TELEGRAM_CHAT_ID 타입 오류: {type(chat_id).__name__}")


def _build_text(telegram_text: str, pages_url: str) -> str:
    """digest.telegram_text 에 Pages URL 풋터 1줄을 덧붙인다.

    `digest.telegram_text` 자체에 ``전체 본문:`` 라인이 placeholder 로 들어 있을 수도 있으나,
    render 가 빈 pages_url 인 경우에만 해당 라인을 생략하므로(step5) dispatcher 는 단순히 append.
    중복 부착을 피하기 위해 telegram_text 가 이미 final pages_url 을 포함하면 그대로 사용.
    """
    if pages_url and pages_url in telegram_text:
        return telegram_text
    if not pages_url:
        return telegram_text
    sep = "\n\n" if not telegram_text.endswith("\n") else "\n"
    return f"{telegram_text}{sep}전체 본문: {pages_url}"


def send(
    digest: "Any",
    pages_url: str,
    chat_id: int | str,
    bot_token: str,
    *,
    http_post: Callable[..., Any] | None = None,
    retry_count: int = 1,
    timeout_seconds: int = 10,
) -> SendResult:
    """텔레그램 Bot API `sendMessage` 호출.

    Args:
        digest: `RenderedDigest` — ``telegram_text`` 필드만 사용.
        pages_url: Pages publish 가 반환한 URL. 빈 문자열이면 본문에 URL 라인 생략.
        chat_id: 직원 단톡방 ID. 문자열이면 int 변환 시도 (실패 시 `ConfigError`).
        bot_token: BotFather 발급 토큰. 평문 로그 금지.
        http_post: `requests.post` 호환 callable. 테스트 hook.
        retry_count: retry 최대 횟수. AC-5.4 = 1.
        timeout_seconds: 개별 호출 timeout (초). 기본 10.

    Returns:
        성공 시 `SendResult(success=True, kind="telegram", retried=N)`.

    Raises:
        ConfigError: chat_id 변환 실패 또는 bot_token 빈 문자열.
        TelegramSendError: retry 후에도 실패. error_kind 분류 포함.
    """
    if not bot_token or not isinstance(bot_token, str):
        raise ConfigError("TELEGRAM_BOT_TOKEN 이 비었습니다.")
    chat_id_int = _coerce_chat_id(chat_id)

    if http_post is None:
        import requests as _requests  # 지연 import.

        http_post = _requests.post

    telegram_text = getattr(digest, "telegram_text", None)
    if not isinstance(telegram_text, str):
        raise TelegramSendError("other", "digest.telegram_text 가 문자열이 아닙니다.")

    text = _build_text(telegram_text, pages_url)
    encoded_len = len(text.encode("utf-8"))
    if encoded_len > _TELEGRAM_MAX_BYTES:
        # 실제 send 호출 안 함 — render 가 안전망에서 자르긴 했지만 dispatcher 가 최종 방어선.
        raise TelegramSendError(
            "too_long",
            f"텔레그램 본문 한도 초과 ({encoded_len} bytes > {_TELEGRAM_MAX_BYTES}).",
        )

    url = _BOT_API_URL_TEMPLATE.format(token=bot_token)
    payload: dict[str, Any] = {
        "chat_id": chat_id_int,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    logger.info(
        "telegram_send — POST sendMessage (token_prefix=%s, chat_id=%d, bytes=%d).",
        mask_key(bot_token),
        chat_id_int,
        encoded_len,
    )

    last_error_kind = "other"
    last_error_msg = "unknown"
    attempts = max(1, retry_count + 1)
    for attempt in range(attempts):
        try:
            resp = http_post(url, json=payload, timeout=timeout_seconds)
            status = getattr(resp, "status_code", None)
            if status == 200:
                return SendResult(
                    success=True,
                    kind="telegram",
                    retried=attempt,
                    extra={"status_code": 200},
                )
            error_kind, msg = _classify_response(status)
            last_error_kind, last_error_msg = error_kind, msg
            if error_kind not in _RETRYABLE_ERROR_KINDS:
                # 401·400·other 즉시 raise — retry 무의미.
                if attempt + 1 < attempts and error_kind in _RETRYABLE_ERROR_KINDS:
                    continue
                raise TelegramSendError(error_kind, msg)
        except TelegramSendError:
            raise
        except Exception as e:  # noqa: BLE001
            # timeout / connection error → network.
            last_error_kind = "network"
            last_error_msg = f"{type(e).__name__}: {e}"
            logger.warning(
                "telegram_send — attempt %d failed: %s",
                attempt + 1,
                last_error_msg,
            )

        # retry 가능한 분기.
        if attempt + 1 >= attempts:
            break

    raise TelegramSendError(last_error_kind, last_error_msg)
