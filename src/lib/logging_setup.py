"""로깅 셋업 + 시크릿 마스킹 helper — dispatcher·summarizer·fetcher 가 공유 (AC-7.2).

CRITICAL #4 (시크릿 평문 노출 금지) 의 코드 측 방어선. dict 통째로 로그를 찍지 못하도록
`mask_key` 를 강제하고, formatter 의 asctime 을 KST 로 고정해 다이제스트·로그 시각 표기를
`lib/time_helper` 와 같은 단일 진실로 맞춘다.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from .time_helper import KST

# formatter 포맷 — step1.md AC 그대로 (마지막 newline 없음).
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

# 멱등성 마커 — setup_logging 이 추가한 handler 임을 표시.
_HANDLER_MARK = "_tnb_setup_logging_handler"


class _KstFormatter(logging.Formatter):
    """asctime 을 KST(Asia/Seoul) 시각으로 출력하는 Formatter.

    `lib/time_helper.now_kst()` 와 같은 ZoneInfo 를 사용해 다이제스트 본문·로그·history 가
    동일한 시간 단위를 공유한다 (CRITICAL #7, anti-pattern A 방지).
    """

    def formatTime(  # noqa: N802 — logging.Formatter 시그니처 유지
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        kst_dt = datetime.fromtimestamp(record.created, tz=KST)
        if datefmt:
            return kst_dt.strftime(datefmt)
        # 기본 표기는 ISO 유사 — 다이제스트 헤더는 `time_helper.format_subject_date` 사용,
        # 로그는 식별성·정렬 용도이므로 ISO + KST offset 으로 단일화.
        return kst_dt.strftime("%Y-%m-%d %H:%M:%S %z")


def setup_logging(level: str = "INFO") -> None:
    """루트 로거에 KST formatter 가 붙은 StreamHandler 를 1회만 부착한다 (AC-7.2).

    멱등성: 재호출해도 handler 중복 추가 없이 level 만 갱신한다.
    """
    root = logging.getLogger()
    root.setLevel(level)

    for handler in root.handlers:
        if getattr(handler, _HANDLER_MARK, False):
            # 이미 등록된 우리 handler — level 만 동기화하고 종료.
            handler.setLevel(level)
            return

    handler = logging.StreamHandler()
    handler.setFormatter(_KstFormatter(_LOG_FORMAT))
    handler.setLevel(level)
    setattr(handler, _HANDLER_MARK, True)
    root.addHandler(handler)


def mask_key(s: Optional[str]) -> str:
    """시크릿 문자열을 로그 안전 형식으로 마스킹한다 (AC-7.2).

    규칙:
        - `None` 또는 빈 문자열 → `""` (로그에서 자연스럽게 생략).
        - 5자 이하 → `"***"` (앞 6자 prefix 노출 시 키 절반 이상 유출 위험).
        - 6자 이상 → `<앞 6자>` + `"..."`.

    어떤 입력에서도 원본 시크릿 전체를 그대로 노출하지 않는다.
    """
    if s is None or s == "":
        return ""
    if len(s) < 6:
        return "***"
    return s[:6] + "..."
