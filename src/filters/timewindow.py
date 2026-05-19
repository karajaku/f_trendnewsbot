"""시간 윈도우 필터 — 최근 N시간 안에 published 된 기사만 통과.

`now` 는 테스트 hook. 기본값은 `lib.time_helper.now_kst()` — 발송·로그·history 가
공유하는 단일 진실 (CRITICAL #6, CRITICAL #2).

published_at_kst 가 (now - hours) 이전이면 제외. naive datetime 은 Article 생성 시
이미 거부되었으므로 본 모듈에서 별도 방어 코드 불필요.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from src.fetchers.base import Article
from src.lib.time_helper import now_kst

logger = logging.getLogger(__name__)


def apply(
    articles: list[Article],
    hours: int,
    *,
    now: datetime | None = None,
) -> list[Article]:
    """`articles` 중 `published_at_kst >= (now - hours)` 인 것만 반환.

    Args:
        articles: 필터링 대상 (입력 순서 보존).
        hours: 시간 윈도우 (양의 정수). filters.yml `global.time_window_hours` 또는
               source.time_window_hours.
        now: 비교 기준 시각 (tz-aware). 미지정 시 `lib.time_helper.now_kst()`.

    Returns:
        통과한 Article list — 입력 순서 보존.
    """
    if not isinstance(hours, int) or hours <= 0:
        raise ValueError(f"hours must be a positive int, got {hours!r}")

    if now is None:
        now = now_kst()
    if now.tzinfo is None:
        raise ValueError("now must be tz-aware datetime")

    cutoff = now - timedelta(hours=hours)

    kept: list[Article] = []
    for article in articles:
        # Article.__post_init__ 가 tz-aware 강제 — 여기서는 그대로 비교.
        if article.published_at_kst >= cutoff:
            kept.append(article)

    logger.debug(
        "timewindow filter — in=%d out=%d hours=%d cutoff=%s",
        len(articles), len(kept), hours, cutoff.isoformat(),
    )
    return kept
