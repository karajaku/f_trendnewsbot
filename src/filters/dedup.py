"""dedup 필터 — canonical_url + 제목 fuzzy match 로 중복 제거 (AC-4.1~4.3).

helper 공유 원칙(CRITICAL #2):

- URL 정규화는 본 모듈에서 호출하지 않는다 — Article.__post_init__ 가 이미
  `lib.url_helper.canonicalize` 통과를 강제했다. dedup 안에서 자체 URL 자르기 0줄
  (anti-pattern A 방어).
- 비교 기준(canonical_url / title) 은 history.store.History 와 같은 dataclass 를 공유한다.

룰:

1. 입력 articles 중 canonical_url 이 history.canonical_urls 에 이미 있으면 제외 (1차).
2. 같은 cron 안에서 이전에 본 canonical_url 과 같으면 제외 (같은 cron 안 중복).
3. 제목이 history.titles 또는 이번 cron 안 이전 통과 제목과
   `difflib.SequenceMatcher.ratio() >= fuzzy_threshold` 이면 제외 (2차).
4. 입력 순서 보존.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Iterable

from src.fetchers.base import Article
from src.history.store import History

logger = logging.getLogger(__name__)


def apply(
    articles: Iterable[Article],
    history: History,
    fuzzy_threshold: float = 0.85,
) -> list[Article]:
    """canonical_url 1차 + 제목 fuzzy 2차 + 같은 cron 안 중복 1건만 통과.

    Args:
        articles: 입력 article 시퀀스 (입력 순서 보존).
        history: 발송 이력 (`history.store.LocalFileBackend.load` 결과).
        fuzzy_threshold: difflib.SequenceMatcher.ratio 임계치 (0.0~1.0).
                         filters.yml `global.fuzzy_title_threshold` 가 단일 진실.

    Returns:
        통과한 Article list — 입력 순서 보존.

    Notes:
        - canonical_url 은 Article 생성 시 이미 url_helper.canonicalize 통과
          (Article.__post_init__). 본 함수는 정규화 0줄.
        - history.titles + 같은 cron 안 이전 통과 제목 모두에 대해 fuzzy 검사.
    """
    if not isinstance(fuzzy_threshold, (int, float)) or not (0.0 <= float(fuzzy_threshold) <= 1.0):
        raise ValueError(
            f"fuzzy_threshold must be in [0.0, 1.0], got {fuzzy_threshold!r}"
        )

    input_list = list(articles)
    n_in = len(input_list)

    seen_urls: set[str] = set(history.canonical_urls)
    seen_titles: list[str] = list(history.titles)
    out: list[Article] = []

    n_url_hit = 0
    n_fuzzy_hit = 0

    for art in input_list:
        if art.canonical_url in seen_urls:
            n_url_hit += 1
            continue

        # fuzzy 2차 — 이력 + 이번 cron 안 이전 통과 제목 합쳐서 비교.
        is_dup = False
        for prev in seen_titles:
            if SequenceMatcher(None, art.title, prev).ratio() >= fuzzy_threshold:
                is_dup = True
                break
        if is_dup:
            n_fuzzy_hit += 1
            continue

        seen_urls.add(art.canonical_url)
        seen_titles.append(art.title)
        out.append(art)

    logger.debug(
        "dedup filter — in=%d out=%d url_hit=%d fuzzy_hit=%d threshold=%.2f",
        n_in, len(out), n_url_hit, n_fuzzy_hit, float(fuzzy_threshold),
    )
    return out
