"""KST(Asia/Seoul) 시간 helper — 다이제스트 헤더·로그·history 가 공유하는 단일 진실 (CRITICAL #7, AC-1.2)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

# 월=0 ~ 일=6 — datetime.weekday() 와 동일 인덱싱.
_KOREAN_WEEKDAYS: tuple[str, ...] = ("월", "화", "수", "목", "금", "토", "일")


def now_kst() -> datetime:
    """현재 시각을 KST(Asia/Seoul) tz-aware datetime 으로 반환한다."""
    return datetime.now(KST)


def to_kst_string(dt: datetime) -> str:
    """tz-aware datetime 을 KST ISO 형식 문자열로 변환한다 (예: `2026-05-19T07:30:00+09:00`).

    naive datetime 은 KST 가정으로 해석할 위험이 있어 `ValueError` 로 거부 (AC-1.2 안전성).
    """
    if not isinstance(dt, datetime):
        raise ValueError("dt must be a datetime instance")
    if dt.tzinfo is None:
        raise ValueError("naive datetime is not allowed — attach tzinfo explicitly")
    return dt.astimezone(KST).isoformat()


def format_subject_date(dt: datetime) -> str:
    """KST 절대 시각을 다이제스트 헤더용 한국어 형식으로 표기한다 (AC-1.2).

    예: `2026-05-19 07:30 KST` → `"5월 19일 (월) 오전 7:30 KST"`.

    naive datetime 은 `ValueError` 로 거부한다.
    """
    if not isinstance(dt, datetime):
        raise ValueError("dt must be a datetime instance")
    if dt.tzinfo is None:
        raise ValueError("naive datetime is not allowed — attach tzinfo explicitly")

    kst_dt = dt.astimezone(KST)
    weekday_ko = _KOREAN_WEEKDAYS[kst_dt.weekday()]
    hour_24 = kst_dt.hour
    am_pm = "오전" if hour_24 < 12 else "오후"
    hour_12 = hour_24 % 12
    if hour_12 == 0:
        hour_12 = 12
    return (
        f"{kst_dt.month}월 {kst_dt.day}일 ({weekday_ko}) "
        f"{am_pm} {hour_12}:{kst_dt.minute:02d} KST"
    )


def parse_to_kst(s: str) -> datetime:
    """ISO 8601 datetime 문자열을 KST tz-aware datetime 으로 파싱한다.

    UTC `Z` suffix, `+00:00`, `+09:00` 모두 처리. naive 문자열(tzinfo 없음)은
    `ValueError` 로 거부 — fetcher 가 KST 임의 추정하지 않게 강제.
    """
    if not isinstance(s, str) or not s.strip():
        raise ValueError("input must be a non-empty string")

    # `Z` suffix 는 fromisoformat 이 3.11+ 부터 지원하나 안전하게 치환.
    candidate = s.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as e:
        raise ValueError(f"unsupported datetime format: {s!r}") from e

    if parsed.tzinfo is None:
        raise ValueError(
            f"naive datetime string not allowed (no timezone): {s!r}"
        )
    return parsed.astimezone(KST)
