"""카테고리 재배정 — AC-2.2 좁은 쪽 우선순위.

Source.category 는 1차 카테고리이지만, 한 기사가 다른 카테고리 키워드(예: "청도",
"GS리테일") 를 본문에 포함하면 좁은 카테고리로 재배정한다. 우선순위:

    farmboss_keyword > agri_distribution > ai_trend

본 모듈은 `dataclasses.replace` 로 새 Article 인스턴스를 만든다 (Article 은 frozen).
키워드 매칭 helper 는 `keyword._matches_any` 를 그대로 재사용 — 키워드 검사 룰은 한 곳에서만
관리 (CRITICAL #2).
"""

from __future__ import annotations

import logging
from dataclasses import replace

from src.config.loader import Filters
from src.fetchers.base import Article

from .keyword import _matches_any

logger = logging.getLogger(__name__)

# AC-2.2 우선순위 — 좁은 쪽이 앞.
_PRIORITY_ORDER: tuple[str, ...] = (
    "farmboss_keyword",
    "agri_distribution",
    "ai_trend",
)


def assign(articles: list[Article], filters: Filters) -> list[Article]:
    """각 기사를 좁은 카테고리로 재배정.

    배정 규칙:
        1. 우선순위 순(`farmboss_keyword` → `agri_distribution` → `ai_trend`) 으로 카테고리 키워드 검사.
        2. 처음 매칭된 카테고리로 배정. 매칭 0건이면 Article.category 그대로 유지.
        3. exclude_any 는 본 모듈에서 검사하지 않음 — keyword 단계의 책임.

    Args:
        articles: 카테고리 재배정 대상 (입력 순서 보존).
        filters: `config.loader.load_filters` 결과.

    Returns:
        재배정된 Article list (원본은 frozen 이므로 새 인스턴스). 입력 순서 보존.
    """
    out: list[Article] = []
    for article in articles:
        haystack = f"{article.title}\n{article.snippet}"

        new_cat = article.category
        for candidate in _PRIORITY_ORDER:
            cat_filter = filters.categories.get(candidate)
            if cat_filter is None:
                continue
            if _matches_any(haystack, cat_filter.must_match_any):
                new_cat = candidate
                break

        if new_cat != article.category:
            logger.debug(
                "category reassigned — url=%s %s -> %s",
                article.canonical_url, article.category, new_cat,
            )
            out.append(replace(article, category=new_cat))
        else:
            out.append(article)

    return out
