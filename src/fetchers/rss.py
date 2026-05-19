"""RSS/Atom feed 어댑터 — `feedparser.parse` 를 한 번 호출하고 Article 로 매핑한다.

설계 메모:

- 본 어댑터는 네트워크 호출(`feedparser.parse(url)`) 만 담당하고 timeout·retry 정책은
  runner 가 일괄 관리한다. feedparser 는 내부적으로 `urllib` 을 쓰며 timeout 옵션을
  직접 받지 않으므로 socket 기본 timeout 을 runner 에서 일시 조정한다.
- entry 한 건 파싱 실패는 skip (전체 raise 금지) — feedparser 가 deprecated/이상한
  필드를 가진 entry 에서 raise 하더라도 다른 entry 처리를 계속한다.
- feed 자체가 망가져 entries 가 비고 `bozo_exception` 만 있는 경우 runner 가
  `parse_error` 로 분류할 수 있도록 `ValueError` 를 raise.

CRITICAL #2 (helper 공유) 준수:
- URL 정규화는 `lib.url_helper.canonicalize` 만 호출.
- 시각 파싱은 `lib.time_helper.parse_to_kst` 우선, struct_time 은 stdlib datetime
  + `ZoneInfo("Asia/Seoul")` 로 KST 변환 (KST = lib.time_helper.KST 재사용).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import feedparser

from src.config.loader import Source
from src.lib.time_helper import KST, parse_to_kst
from src.lib.url_helper import canonicalize

from .base import Article

logger = logging.getLogger(__name__)

# snippet 최대 길이 — step3.md "본문 일부, 최대 ~500자" 가이드라인.
_SNIPPET_MAX_CHARS = 500


def _entry_published_at_kst(entry: Any) -> datetime | None:
    """feedparser entry 에서 published 시각을 KST tz-aware datetime 으로 추출.

    우선순위:
        1. `published_parsed` (time.struct_time, UTC 가정 — feedparser 표준).
        2. `updated_parsed` (동일 처리).
        3. `published` 문자열 → `lib.time_helper.parse_to_kst`.
        4. `updated` 문자열 → 동일.

    어느 것도 못 얻으면 None 반환 (호출측이 skip 결정).
    """
    for struct_attr in ("published_parsed", "updated_parsed"):
        st = getattr(entry, struct_attr, None)
        if st is None:
            continue
        try:
            # feedparser 는 struct_time 을 UTC 로 정규화해서 돌려준다 (문서 명시).
            utc_dt = datetime(
                st.tm_year, st.tm_mon, st.tm_mday,
                st.tm_hour, st.tm_min, st.tm_sec,
                tzinfo=timezone.utc,
            )
            return utc_dt.astimezone(KST)
        except (TypeError, ValueError):
            continue

    for str_attr in ("published", "updated"):
        s = getattr(entry, str_attr, None)
        if not isinstance(s, str) or not s.strip():
            continue
        try:
            return parse_to_kst(s)
        except ValueError:
            continue

    return None


def _entry_snippet(entry: Any) -> str:
    """entry.summary / entry.description 에서 snippet 추출. HTML 태그 단순 strip."""
    raw = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
    if not isinstance(raw, str):
        return ""
    # 매우 가벼운 HTML 태그 제거 — bs4 를 RSS 에 끌어쓰는 것은 과함.
    # `<.*?>` greedy 회피 위해 non-greedy + DOTALL.
    import re
    no_tags = re.sub(r"<[^>]*>", "", raw)
    # 연속 공백을 단일 공백으로 압축 (가독성).
    compact = re.sub(r"\s+", " ", no_tags).strip()
    if len(compact) > _SNIPPET_MAX_CHARS:
        return compact[:_SNIPPET_MAX_CHARS]
    return compact


class RssFetcher:
    """RSS/Atom feed 어댑터 (`Source.type == "rss"`)."""

    def fetch(self, source: Source) -> list[Article]:
        """`feedparser.parse(source.url)` 후 entries 를 Article 로 매핑.

        Raises:
            ValueError: feed parse 자체가 실패 (entries 비어있고 bozo_exception 존재).
                       runner 가 `parse_error` Failure 로 변환한다.
        """
        parsed = feedparser.parse(source.url)

        entries = getattr(parsed, "entries", None) or []
        bozo = bool(getattr(parsed, "bozo", False))
        bozo_exc = getattr(parsed, "bozo_exception", None)

        # feed 자체가 망가져 entries 가 비고 bozo 만 있는 경우 — runner 가 parse_error 로 잡도록 raise.
        if not entries and bozo and bozo_exc is not None:
            raise ValueError(
                f"feedparser bozo: {type(bozo_exc).__name__}: {bozo_exc}"
            )

        articles: list[Article] = []
        for idx, entry in enumerate(entries):
            try:
                title = getattr(entry, "title", None)
                link = getattr(entry, "link", None)
                if not isinstance(title, str) or not title.strip():
                    logger.debug(
                        "skip entry without title — source_id=%s idx=%d", source.id, idx
                    )
                    continue
                if not isinstance(link, str) or not link.strip():
                    logger.debug(
                        "skip entry without link — source_id=%s idx=%d title=%r",
                        source.id, idx, title[:60],
                    )
                    continue

                try:
                    canonical_url = canonicalize(link)
                except ValueError as e:
                    logger.debug(
                        "skip entry with invalid url — source_id=%s idx=%d err=%s",
                        source.id, idx, e,
                    )
                    continue

                published_at_kst = _entry_published_at_kst(entry)
                if published_at_kst is None:
                    logger.debug(
                        "skip entry without published time — source_id=%s idx=%d",
                        source.id, idx,
                    )
                    continue

                snippet = _entry_snippet(entry)

                articles.append(
                    Article(
                        canonical_url=canonical_url,
                        title=title.strip(),
                        source_id=source.id,
                        source_name=source.name,
                        category=source.category,
                        published_at_kst=published_at_kst,
                        snippet=snippet,
                    )
                )
            except Exception as e:  # pragma: no cover — entry 단위 방어선
                # entry 한 건 실패가 전체 feed 를 막지 않도록 skip + DEBUG 로그.
                logger.debug(
                    "skip entry due to unexpected error — source_id=%s idx=%d err=%s",
                    source.id, idx, e,
                )
                continue

        logger.debug(
            "rss fetch ok — source_id=%s articles=%d", source.id, len(articles)
        )
        return articles
