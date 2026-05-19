"""`src.filters` 단위 테스트 — step4.md AC 매핑.

매핑:
    AC timewindow now-1h pass, now-50h drop → test_timewindow_passes_within_hours
    AC keyword must_match pass → test_keyword_must_match_passes
    AC keyword exclude drop → test_keyword_exclude_drops
    AC keyword must_match 0 → test_keyword_no_match_drops (안전망)
    AC-2.2 category 재배정 → test_category_reassigns_to_narrower
    AC category keep when no match → test_category_keeps_when_no_match
    AC-4.2 dedup canonical hit → test_dedup_drops_canonical_hit
    AC-4.3 dedup fuzzy 0.85 → test_dedup_fuzzy_threshold_drops_similar
    AC dedup 같은 cron 안 같은 article → test_dedup_within_same_cron
    AC dedup 입력 순서 보존 → test_dedup_preserves_input_order
    AC pipeline 카테고리 3개 키 → test_pipeline_returns_all_three_category_keys
    AC pipeline fetch_failures 무시 → test_pipeline_accepts_fetch_failures
"""

from __future__ import annotations

from datetime import datetime, timedelta
from difflib import SequenceMatcher

import pytest

from src.config.loader import (
    CategoryFilter,
    Filters,
    GlobalFilters,
)
from src.fetchers.base import Article, Failure
from src.filters import category as category_filter
from src.filters import dedup as dedup_filter
from src.filters import keyword as keyword_filter
from src.filters import pipeline as pipeline_filter
from src.filters import timewindow as timewindow_filter
from src.history.store import History
from src.lib.time_helper import KST, now_kst
from src.lib.url_helper import canonicalize


# ---------- helper ----------


def _make_article(
    url: str = "https://example.com/news/abc",
    title: str = "샘플 제목",
    source_id: str = "rss_one",
    source_name: str = "RSS One",
    category: str = "ai_trend",
    published_at_kst: datetime | None = None,
    snippet: str = "샘플 본문 일부.",
) -> Article:
    canonical = canonicalize(url)
    if published_at_kst is None:
        published_at_kst = now_kst()
    return Article(
        canonical_url=canonical,
        title=title,
        source_id=source_id,
        source_name=source_name,
        category=category,
        published_at_kst=published_at_kst,
        snippet=snippet,
    )


def _make_filters(
    ai_must: list[str] | None = None,
    ai_exclude: list[str] | None = None,
    agri_must: list[str] | None = None,
    agri_exclude: list[str] | None = None,
    fb_must: list[str] | None = None,
    fb_exclude: list[str] | None = None,
) -> Filters:
    return Filters(
        categories={
            "ai_trend": CategoryFilter(
                label="AI 트렌드",
                must_match_any=ai_must if ai_must is not None else ["AI", "LLM", "Claude"],
                exclude_any=ai_exclude if ai_exclude is not None else ["부동산"],
                order=1,
            ),
            "agri_distribution": CategoryFilter(
                label="농산물·유통",
                must_match_any=agri_must if agri_must is not None else ["농산물", "유통", "GS리테일"],
                exclude_any=agri_exclude if agri_exclude is not None else [],
                order=2,
            ),
            "farmboss_keyword": CategoryFilter(
                label="팜보스 관심 키워드",
                must_match_any=fb_must if fb_must is not None else ["청도", "팜보스", "복숭아"],
                exclude_any=fb_exclude if fb_exclude is not None else [],
                order=3,
            ),
        },
        global_filters=GlobalFilters(
            time_window_hours=36,
            fuzzy_title_threshold=0.85,
            dedup_days=7,
        ),
    )


# ---------- 1. timewindow ----------


def test_timewindow_passes_within_hours() -> None:
    """now-1h 통과, now-50h 제외 (hours=36)."""
    now = datetime(2026, 5, 19, 12, 0, 0, tzinfo=KST)
    a_recent = _make_article(
        url="https://example.com/recent",
        published_at_kst=now - timedelta(hours=1),
    )
    a_old = _make_article(
        url="https://example.com/old",
        published_at_kst=now - timedelta(hours=50),
    )
    out = timewindow_filter.apply([a_recent, a_old], hours=36, now=now)
    urls = [a.canonical_url for a in out]
    assert "https://example.com/recent" in urls
    assert "https://example.com/old" not in urls


# ---------- 2. keyword must_match pass ----------


def test_keyword_must_match_passes() -> None:
    """must_match 매칭되면 통과."""
    filters = _make_filters()
    a = _make_article(
        title="Claude 의 새 기능 발표",
        snippet="Anthropic 발표",
        category="ai_trend",
    )
    out = keyword_filter.apply([a], filters=filters)
    assert len(out) == 1


# ---------- 3. keyword exclude drop ----------


def test_keyword_exclude_drops() -> None:
    """exclude_any 매칭 시 제외."""
    filters = _make_filters()
    a = _make_article(
        title="Claude 부동산 시장 영향",
        snippet="AI 기반 부동산 가격 예측",
        category="ai_trend",
    )
    out = keyword_filter.apply([a], filters=filters)
    assert out == []


# ---------- 4. keyword must_match 0 안전망 ----------


def test_keyword_no_match_drops() -> None:
    """must_match 0매칭이면 제외 (안전망)."""
    filters = _make_filters()
    a = _make_article(
        title="아무 관련 없는 기사",
        snippet="이 본문에는 카테고리 키워드 없음",
        category="ai_trend",
    )
    out = keyword_filter.apply([a], filters=filters)
    assert out == []


# ---------- 5. AC-2.2 카테고리 재배정 ----------


def test_category_reassigns_to_narrower() -> None:
    """Article.category=ai_trend 인데 본문에 '청도' → farmboss_keyword 재배정."""
    filters = _make_filters()
    a = _make_article(
        title="AI 기반 청도 복숭아 출하 예측",
        snippet="Claude 가 청도 농가 데이터를 분석",
        category="ai_trend",
    )
    out = category_filter.assign([a], filters=filters)
    assert len(out) == 1
    assert out[0].category == "farmboss_keyword"
    # 원본 카테고리 유지 검증 (frozen dataclass replace 결과).
    assert out[0].canonical_url == a.canonical_url
    assert out[0].title == a.title


# ---------- 6. 카테고리 매칭 없으면 원본 유지 ----------


def test_category_keeps_when_no_match() -> None:
    """category 키워드 매칭 없으면 Article.category 그대로 유지."""
    filters = _make_filters()
    a = _make_article(
        title="순수 AI 기사 (지역명 없음)",
        snippet="Claude API 발표",
        category="ai_trend",
    )
    out = category_filter.assign([a], filters=filters)
    assert len(out) == 1
    assert out[0].category == "ai_trend"


# ---------- 7. dedup canonical hit ----------


def test_dedup_drops_canonical_hit() -> None:
    """history.canonical_urls 에 이미 있는 url 은 제외."""
    history = History(
        canonical_urls=frozenset({"https://example.com/news/abc"}),
        titles=(),
    )
    a_dup = _make_article(url="https://example.com/news/abc", title="중복 기사")
    a_new = _make_article(url="https://example.com/news/def", title="신규 기사")
    out = dedup_filter.apply([a_dup, a_new], history=history, fuzzy_threshold=0.85)
    urls = [a.canonical_url for a in out]
    assert "https://example.com/news/abc" not in urls
    assert "https://example.com/news/def" in urls


# ---------- 8. dedup fuzzy 0.85 ----------


def test_dedup_fuzzy_threshold_drops_similar() -> None:
    """fuzzy ratio >= 0.85 인 두 제목 중 1건만 통과."""
    title_a = "청도 복숭아 출하 5일 앞당겨질 전망"
    title_b = "청도 복숭아 출하 5일 앞당겨질 듯"
    # 실측 ratio 가 0.85 이상이어야 본 테스트가 의미 있음 — fixture 검증.
    actual_ratio = SequenceMatcher(None, title_a, title_b).ratio()
    assert actual_ratio >= 0.85, (
        f"fixture 부적합: ratio={actual_ratio:.3f} (0.85+ 인 두 제목으로 교체 필요)"
    )

    a1 = _make_article(url="https://example.com/news/a", title=title_a)
    a2 = _make_article(url="https://example.com/news/b", title=title_b)

    history = History.empty()
    out = dedup_filter.apply([a1, a2], history=history, fuzzy_threshold=0.85)
    assert len(out) == 1
    assert out[0].canonical_url == "https://example.com/news/a"  # 첫 등장 통과


# ---------- 9. dedup 같은 cron 안 같은 article 2건 → 1건 ----------


def test_dedup_within_same_cron() -> None:
    """같은 cron 안에서 같은 canonical_url 2건 들어오면 1건만 통과."""
    a1 = _make_article(url="https://example.com/news/dup", title="같은 기사 A")
    a2 = _make_article(url="https://example.com/news/dup", title="같은 기사 A")
    history = History.empty()
    out = dedup_filter.apply([a1, a2], history=history, fuzzy_threshold=0.85)
    assert len(out) == 1


# ---------- 10. dedup 입력 순서 보존 ----------


def test_dedup_preserves_input_order() -> None:
    """입력 순서 그대로 출력 순서."""
    a1 = _make_article(url="https://example.com/news/1", title="첫 번째")
    a2 = _make_article(url="https://example.com/news/2", title="두 번째")
    a3 = _make_article(url="https://example.com/news/3", title="세 번째")
    history = History.empty()
    out = dedup_filter.apply([a1, a2, a3], history=history, fuzzy_threshold=0.85)
    assert [a.canonical_url for a in out] == [
        "https://example.com/news/1",
        "https://example.com/news/2",
        "https://example.com/news/3",
    ]


# ---------- 11. pipeline 카테고리 3개 키 ----------


def test_pipeline_returns_all_three_category_keys() -> None:
    """pipeline.apply 출력 dict 에 3개 카테고리 키 모두 존재 (0건이면 빈 list)."""
    filters = _make_filters()
    history = History.empty()
    out = pipeline_filter.apply(
        articles=[],
        history=history,
        loaded_filters=filters,
        global_filters=filters.global_filters,
    )
    assert set(out.keys()) == {"ai_trend", "agri_distribution", "farmboss_keyword"}
    assert out["ai_trend"] == []
    assert out["agri_distribution"] == []
    assert out["farmboss_keyword"] == []


# ---------- 12. pipeline fetch_failures 무시 ----------


def test_pipeline_accepts_fetch_failures() -> None:
    """fetch_failures 인자는 인터페이스 보존용 — 본 함수 동작에 영향 없음."""
    filters = _make_filters()
    history = History.empty()
    failures = [
        Failure(
            source_id="rss_dead",
            source_name="Dead Feed",
            error_kind="timeout",
            error_message="timeout after 10s",
        ),
    ]
    a = _make_article(title="Claude 신기능", snippet="AI 발표", category="ai_trend")
    out = pipeline_filter.apply(
        articles=[a],
        history=history,
        loaded_filters=filters,
        global_filters=filters.global_filters,
        fetch_failures=failures,
    )
    # ai_trend 에 1건 통과 (실패 list 는 영향 안 미침).
    assert len(out["ai_trend"]) == 1


# ---------- 13. pipeline 통합 end-to-end (bonus) ----------


def test_pipeline_end_to_end_categorizes_and_dedupes() -> None:
    """timewindow → keyword → category → dedup 4단계 통과 + 카테고리 그루핑."""
    filters = _make_filters()
    history = History(
        canonical_urls=frozenset({"https://example.com/old"}),
        titles=(),
    )

    now = now_kst()
    a_in_ai = _make_article(
        url="https://example.com/ai-1",
        title="Claude 모델 업데이트",
        snippet="Anthropic 발표",
        category="ai_trend",
        published_at_kst=now - timedelta(hours=2),
    )
    a_in_farmboss = _make_article(
        url="https://example.com/fb-1",
        title="청도 복숭아 출하 예측",
        snippet="AI 기반 출하",
        category="ai_trend",  # 본문 키워드로 farmboss_keyword 재배정 예상
        published_at_kst=now - timedelta(hours=3),
    )
    a_too_old = _make_article(
        url="https://example.com/too-old",
        title="Claude 옛날 기사",
        snippet="발표",
        category="ai_trend",
        published_at_kst=now - timedelta(hours=200),
    )
    a_already_sent = _make_article(
        url="https://example.com/old",  # canonicalize 통과 형태로
        title="이미 발송된 기사",
        snippet="AI",
        category="ai_trend",
        published_at_kst=now - timedelta(hours=1),
    )

    out = pipeline_filter.apply(
        articles=[a_in_ai, a_in_farmboss, a_too_old, a_already_sent],
        history=history,
        loaded_filters=filters,
        global_filters=filters.global_filters,
    )

    ai_urls = [a.canonical_url for a in out["ai_trend"]]
    fb_urls = [a.canonical_url for a in out["farmboss_keyword"]]

    assert "https://example.com/ai-1" in ai_urls
    assert "https://example.com/fb-1" in fb_urls  # 재배정
    assert "https://example.com/too-old" not in ai_urls  # 시간 윈도우 탈락
    assert "https://example.com/old" not in ai_urls  # dedup canonical hit
