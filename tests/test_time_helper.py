"""`lib/time_helper` 단위 테스트 — AC-1.2, step1.md AC 4건 이상 매핑."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from src.lib.time_helper import (
    KST,
    format_subject_date,
    now_kst,
    to_kst_string,
)


def test_now_kst_returns_kst_aware_datetime() -> None:
    """`now_kst()` 는 `Asia/Seoul` ZoneInfo 가 붙은 tz-aware datetime 을 반환한다."""
    dt = now_kst()
    assert dt.tzinfo is not None
    assert dt.tzinfo == ZoneInfo("Asia/Seoul")
    # 모듈 상수 `KST` 와 동일 ZoneInfo 사용 (단일 진실).
    assert dt.tzinfo == KST


def test_format_subject_date_korean_format_for_known_kst_datetime() -> None:
    """KST 2026-05-19 07:30 (화요일) 입력에 대해 정확한 한국어 헤더 문자열을 반환한다."""
    dt = datetime(2026, 5, 19, 7, 30, tzinfo=KST)
    # 2026-05-19 의 weekday() == 1 (화요일) — 사전 검증.
    assert datetime(2026, 5, 19).weekday() == 1
    assert format_subject_date(dt) == "5월 19일 (화) 오전 7:30 KST"


def test_format_subject_date_rejects_naive_datetime() -> None:
    """tzinfo 없는 naive datetime 은 KST 추정 위험으로 거부한다."""
    naive = datetime(2026, 5, 19, 7, 30)
    with pytest.raises(ValueError):
        format_subject_date(naive)


def test_utc_input_converts_to_kst_next_day() -> None:
    """UTC 2026-05-19T22:30+00:00 입력은 KST 2026-05-20 07:30 으로 변환되어야 한다."""
    utc_dt = datetime(2026, 5, 19, 22, 30, tzinfo=timezone.utc)

    # to_kst_string 은 KST ISO 표기 — 날짜·시각·offset 모두 검증.
    iso = to_kst_string(utc_dt)
    assert iso.startswith("2026-05-20T07:30:00")
    assert iso.endswith("+09:00")

    # format_subject_date 의 한국어 헤더 표기로도 동일한 KST 시각이 나와야 함.
    # 2026-05-20 은 수요일 — datetime(2026,5,20).weekday() == 2.
    assert datetime(2026, 5, 20).weekday() == 2
    assert format_subject_date(utc_dt) == "5월 20일 (수) 오전 7:30 KST"
