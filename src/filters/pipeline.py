"""필터 파이프라인 — timewindow → keyword → category → dedup → 카테고리 그루핑.

run_daily.py 의 단일 진입점. 통합 진입 본문에 새 필터 로직을 누적하지 않는다
(anti-pattern B 방어). 각 단계는 같은 헬퍼/데이터를 공유:

- Article.canonical_url 은 url_helper.canonicalize 통과 결과 (생성 시 강제).
- timewindow 의 비교 기준 시각은 lib.time_helper.now_kst 가 단일 진실.
- keyword/category 의 매칭 helper 는 `_matches_any` 한 곳.
- dedup 은 history.store.History 와 같은 dataclass 를 공유.
"""

from __future__ import annotations

import logging
from typing import Iterable

from src.config.loader import Filters, GlobalFilters
from src.fetchers.base import Article, Failure
from src.history.store import History

from . import category as category_filter
from . import dedup as dedup_filter
from . import keyword as keyword_filter
from . import timewindow as timewindow_filter

logger = logging.getLogger(__name__)

# 카테고리 3종 — config.loader._SOURCE_CATEGORIES 와 같은 단일 진실(중복 정의지만
# 모듈 경계 명시를 위해 본 모듈에 노출). 추후 4번째 카테고리 도입 시 두 곳 모두 갱신.
CATEGORIES: tuple[str, ...] = ("ai_trend", "agri_distribution", "farmboss_keyword")


def apply(
    articles: Iterable[Article],
    history: History,
    loaded_filters: Filters,
    global_filters: GlobalFilters,
    fetch_failures: list[Failure] | None = None,  # 인터페이스 보존, 본 함수는 사용 안 함
) -> dict[str, list[Article]]:
    """입력 articles 를 4단계 필터 후 카테고리별 dict 로 반환.

    Args:
        articles: fetcher.run_all 결과 articles (입력 순서 보존).
        history: history backend.load 결과.
        loaded_filters: config.loader.load_filters 결과 (카테고리별 must/exclude).
        global_filters: filters.yml global 블록 (time_window / fuzzy / dedup_days).
        fetch_failures: 인터페이스 보존을 위한 placeholder — 본 함수는 사용 안 함.
                        (summarizer/render 가 다이제스트 메타에 같은 list 를 그대로 노출.)

    Returns:
        dict[category, list[Article]]. 카테고리 키 3종(CATEGORIES) 모두 존재
        (0건이면 빈 list).

    Notes:
        - 단계 순서: timewindow → keyword → category(재배정) → dedup.
        - 각 단계 통과 건수는 INFO 로그 1줄 (운영 시 디버깅).
    """
    initial_list = list(articles)
    n0 = len(initial_list)

    tw = timewindow_filter.apply(initial_list, hours=global_filters.time_window_hours)
    kw = keyword_filter.apply(tw, filters=loaded_filters)
    cat = category_filter.assign(kw, filters=loaded_filters)
    dd = dedup_filter.apply(
        cat,
        history=history,
        fuzzy_threshold=global_filters.fuzzy_title_threshold,
    )

    logger.info(
        "filter pipeline: in=%d, timewindow=%d, keyword=%d, category=%d, dedup=%d",
        n0, len(tw), len(kw), len(cat), len(dd),
    )

    by_cat: dict[str, list[Article]] = {c: [] for c in CATEGORIES}
    for art in dd:
        if art.category in by_cat:
            by_cat[art.category].append(art)
        else:
            # category 재배정 후에도 알 수 없는 카테고리가 들어오면 운영 가시성용 WARNING.
            logger.warning(
                "pipeline — article with unknown category dropped: url=%s category=%s",
                art.canonical_url, art.category,
            )

    return by_cat
