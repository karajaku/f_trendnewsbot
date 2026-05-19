"""운영자 전용 텔레그램 chat 짧은 alert — §7 + AC-5.3 · 5.4.

- 직원 단톡방과 분리된 `OPS_ALERT_CHAT_ID` 로만 발송. 직원 단톡방 본문에 스택트레이스·운영
  메타가 누락되도록 하는 격리 helper.
- 재시도 0회 — alert 자체가 실패해도 stderr 로그만 + return None (무한루프 방지, AC-5.4).
- 본문 4096-byte 한도 초과 시 잘라낸다.
- 토큰·chat_id 평문 로깅 금지 — `mask_key` 통과.

본 모듈은 본문 형식의 단일 진실을 제공한다:
``[팜보스 트렌드 알림] {KST 시각} {REASON_LABEL}\\n{Error}\\n{traceback 마지막 5줄}\\n다음 cron: {KST}``.
"""

from __future__ import annotations

import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Callable

from src.lib.logging_setup import mask_key
from src.lib.time_helper import KST, format_subject_date

logger = logging.getLogger(__name__)

# §7 본문 형식 — 단일 진실.
_BOT_API_URL_TEMPLATE = "https://api.telegram.org/bot{token}/sendMessage"
_TELEGRAM_MAX_BYTES = 4096
_TRACEBACK_TAIL_LINES = 5

# reason → 사람용 한국어 라벨 (§7).
_REASON_LABELS: dict[str, str] = {
    "quota_exceeded": "QUOTA 초과",
    "pages_failed": "Pages publish 실패",
    "telegram_failed": "텔레그램 발송 실패",
    "unexpected": "예외",
}


def _format_traceback_tail(error: Exception | None) -> str:
    """예외 traceback 의 마지막 N줄. None 이면 빈 문자열."""
    if error is None:
        return ""
    tb_str = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )
    lines = [ln for ln in tb_str.splitlines() if ln.strip()]
    if not lines:
        return ""
    tail = lines[-_TRACEBACK_TAIL_LINES:]
    return "\n".join(tail)


def _format_alert_body(
    reason: str,
    error: Exception | None,
    now_kst: datetime,
    next_cron_kst: datetime | None,
) -> str:
    """§7 본문 — 한국어, 짧고 운영자 전용."""
    label = _REASON_LABELS.get(reason, reason)
    header = f"[팜보스 트렌드 알림] {format_subject_date(now_kst)} {label}"
    parts: list[str] = [header, ""]
    if error is not None:
        first_line = str(error).splitlines()[0] if str(error) else ""
        parts.append(f"{type(error).__name__}: {first_line}")
        tail = _format_traceback_tail(error)
        if tail:
            parts.append(tail)
    else:
        parts.append("(no error object)")
    parts.append("")
    if next_cron_kst is not None:
        parts.append(f"다음 cron: {format_subject_date(next_cron_kst)}")
    else:
        parts.append("다음 cron: 예정 시각 미상")

    body = "\n".join(parts)
    encoded_len = len(body.encode("utf-8"))
    if encoded_len > _TELEGRAM_MAX_BYTES:
        suffix = "\n…(중략)"
        while len(body.encode("utf-8")) + len(suffix.encode("utf-8")) > _TELEGRAM_MAX_BYTES and body:
            body = body[:-1]
        body = body + suffix
    return body


def send_ops_alert(
    reason: str,
    error: Exception | None,
    chat_id: int | str,
    bot_token: str,
    next_cron_kst: datetime | None = None,
    *,
    http_post: Callable[..., Any] | None = None,
    timeout_seconds: int = 10,
    now_kst_fn: Callable[[], datetime] | None = None,
) -> None:
    """운영자 chat 으로 짧은 alert 메시지 발송. 실패 시 stderr 로그만 + return.

    Args:
        reason: ``"quota_exceeded"`` | ``"pages_failed"`` | ``"telegram_failed"`` | ``"unexpected"``.
        error: 발생한 예외 (None 가능). traceback 마지막 5줄을 본문에 첨부.
        chat_id: `OPS_ALERT_CHAT_ID` (음수 정수 가능).
        bot_token: `TELEGRAM_BOT_TOKEN` (직원 발송과 동일 봇).
        next_cron_kst: 다음 cron 시각 (KST tz-aware). 없으면 ``"예정 시각 미상"``.
        http_post: `requests.post` 호환 callable. 테스트 hook.
        timeout_seconds: HTTP timeout (초).
        now_kst_fn: 현재 KST 시각 helper. 테스트 hook. 기본 `time_helper.KST` 기반.

    Returns:
        None — 성공·실패 모두 raise 없음. 실패 시 stderr 로그.
    """
    if not bot_token or not isinstance(bot_token, str):
        print(
            "[ops_alert] TELEGRAM_BOT_TOKEN 비어있음 — alert 발송 불가, stderr 종료.",
            file=sys.stderr,
        )
        return

    if http_post is None:
        import requests as _requests  # 지연 import.

        http_post = _requests.post

    if now_kst_fn is None:
        now_kst_fn = lambda: datetime.now(KST)  # noqa: E731

    try:
        now_kst = now_kst_fn()
        body = _format_alert_body(reason, error, now_kst, next_cron_kst)
    except Exception as e:  # noqa: BLE001
        print(
            f"[ops_alert] 본문 구성 실패 ({type(e).__name__}: {e}) — 발송 생략.",
            file=sys.stderr,
        )
        return

    # chat_id 변환 — int / str 모두 허용.
    try:
        chat_id_int: int | str
        if isinstance(chat_id, int):
            chat_id_int = chat_id
        else:
            chat_id_int = int(str(chat_id).strip())
    except Exception:  # noqa: BLE001
        print(
            f"[ops_alert] OPS_ALERT_CHAT_ID int 변환 실패 (prefix={mask_key(str(chat_id))}) "
            "— 발송 생략.",
            file=sys.stderr,
        )
        return

    url = _BOT_API_URL_TEMPLATE.format(token=bot_token)
    payload = {
        "chat_id": chat_id_int,
        "text": body,
        "disable_web_page_preview": True,
    }

    try:
        resp = http_post(url, json=payload, timeout=timeout_seconds)
        status = getattr(resp, "status_code", None)
        if status == 200:
            logger.info(
                "ops_alert — 발송 성공 (reason=%s, token_prefix=%s).",
                reason,
                mask_key(bot_token),
            )
            return
        # 실패 — stderr 만, 재시도 없음.
        print(
            f"[ops_alert] HTTP {status} 응답 — alert 발송 실패 "
            f"(reason={reason}, token_prefix={mask_key(bot_token)}). "
            "재시도 없음 (무한루프 방지).",
            file=sys.stderr,
        )
    except Exception as e:  # noqa: BLE001
        print(
            f"[ops_alert] 발송 중 예외 ({type(e).__name__}: {e}) "
            f"— reason={reason}, token_prefix={mask_key(bot_token)}. "
            "재시도 없음 (무한루프 방지).",
            file=sys.stderr,
        )
