"""키워드 필터 — `categories[article.category].must_match_any` 매칭 안전망.

Article.title + Article.snippet 에 카테고리의 `must_match_any` 키워드 중 하나라도
substring 매칭(case-insensitive) 되면 통과. `exclude_any` 매칭 시 제외.

must_match 가 0건이면 통과 안 함 — 소스가 카테고리를 지정했더라도 본문 키워드 매칭이
0이면 거르는 안전망 (filters.yml §6-2 의 `must_match_any` 정의대로).

키워드 매칭 규칙은 본 모듈이 단일 진실 — 발송 본문에 "이 카테고리에 매칭된 키워드" 를
표기하는 helper 도 본 모듈의 `_matches_any` 를 재사용한다 (CRITICAL #2).
"""

from __future__ import annotations

import logging

from src.config.loader import Filters
from src.fetchers.base import Article

logger = logging.getLogger(__name__)


def _matches_any(haystack: str, keywords: list[str]) -> bool:
    """`haystack` 에 `keywords` 중 하나라도 substring 매칭(case-insensitive) 되면 True.

    빈 `keywords` 리스트는 항상 False (매칭 0건).
    """
    if not keywords:
        return False
    lower = haystack.lower()
    for kw in keywords:
        if not kw:
            continue
        if kw.lower() in lower:
            return True
    return False


def apply(articles: list[Article], filters: Filters) -> list[Article]:
    """카테고리별 must_match_any / exclude_any 적용.

    Args:
        articles: 필터링 대상 (입력 순서 보존).
        filters: `config.loader.load_filters` 결과.

    Returns:
        통과한 Article list — 입력 순서 보존.

    Notes:
        - Article.category 가 filters.categories 에 없는 경우 (구성 오류) 제외 + WARNING.
        - must_match_any 0매칭이면 통과 안 함 (안전망).
        - exclude_any 1개라도 매칭되면 제외.
        - 매칭 대상 = Article.title + " " + Article.snippet (case-insensitive substring).
    """
    kept: list[Article] = []
    for article in articles:
        cat_filter = filters.categories.get(article.category)
        if cat_filter is None:
            logger.warning(
                "keyword filter — unknown category, drop article: source_id=%s category=%s url=%s",
                article.source_id, article.category, article.canonical_url,
            )
            continue

        haystack = f"{article.title}\n{article.snippet}"

        # must_match_any 0건 매칭이면 안전망으로 제외.
        if not _matches_any(haystack, cat_filter.must_match_any):
            continue

        # exclude_any 1건 매칭이면 제외.
        if _matches_any(haystack, cat_filter.exclude_any):
            continue

        kept.append(article)

    logger.debug(
        "keyword filter — in=%d out=%d", len(articles), len(kept),
    )
    return kept
