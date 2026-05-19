"""`src.fetchers` 단위 테스트 — step3.md AC 매핑.

전부 mock 기반. 실제 네트워크 호출은 금지 (step3.md 수동 테스트 절차 외).

매핑:
    AC §1 Article canonical_url 강제 → test_article_rejects_uncanonical_url
    AC §1 Article published_at_kst tz-aware 강제 → test_article_rejects_naive_datetime
    AC §3 RssFetcher 정상 feed mock → test_rss_fetcher_normal_feed
    AC §4 runner — disabled 소스 skip → test_run_all_skips_disabled_source
    AC §5 runner — timeout 격리 → test_run_all_isolates_timeout_failure
    AC §6 runner — html stub parse_error → test_run_all_html_stub_yields_parse_error
    AC §7 runner — 전체 정상 → test_run_all_all_sources_ok
    추가 — http 4xx/5xx 분류 → test_run_all_classifies_http_4xx, test_run_all_classifies_http_5xx
    추가 — feed bozo parse_error → test_rss_fetcher_bozo_feed_raises
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import requests

from src.config.loader import Source
from src.fetchers import run_all
from src.fetchers.base import Article, Failure
from src.fetchers.html import HtmlFetcher
from src.fetchers.json_api import JsonApiFetcher
from src.fetchers.rss import RssFetcher
from src.lib.time_helper import KST


# ---------- 테스트용 helper ----------


def _make_source(
    sid: str = "rss_one",
    name: str = "RSS One",
    url: str = "https://example.com/feed.xml",
    stype: str = "rss",
    cat: str = "ai_trend",
    enabled: bool = True,
) -> Source:
    return Source(
        id=sid,
        name=name,
        url=url,
        type=stype,  # type: ignore[arg-type]
        category=cat,  # type: ignore[arg-type]
        enabled=enabled,
        tags=[],
        time_window_hours=36,
    )


def _make_feedparser_entry(
    *,
    title: str = "Sample Title",
    link: str = "https://example.com/post/1",
    summary: str = "<p>Some <b>HTML</b> summary.</p>",
    published_struct: tuple[int, ...] = (2026, 5, 19, 7, 30, 0, 0, 139, 0),
) -> SimpleNamespace:
    """feedparser entry 모양의 SimpleNamespace 객체.

    published_parsed 는 time.struct_time 호환 — runner 가 datetime() 생성자로 받음.
    SimpleNamespace 는 attribute 접근만 지원하므로 tm_* 호환 객체로 별도 구성.
    """
    st = SimpleNamespace(
        tm_year=published_struct[0],
        tm_mon=published_struct[1],
        tm_mday=published_struct[2],
        tm_hour=published_struct[3],
        tm_min=published_struct[4],
        tm_sec=published_struct[5],
    )
    return SimpleNamespace(
        title=title,
        link=link,
        summary=summary,
        published_parsed=st,
        updated_parsed=None,
        published="",
        updated="",
    )


def _make_parsed_feed(entries: list[SimpleNamespace], *, bozo: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        entries=entries,
        bozo=bozo,
        bozo_exception=None if not bozo else ValueError("simulated bozo"),
    )


# ---------- 1. Article canonical_url 강제 ----------


def test_article_rejects_uncanonical_url() -> None:
    """utm 파라미터가 남아있는 URL 은 Article 생성 시 ValueError."""
    with pytest.raises(ValueError) as exc:
        Article(
            canonical_url="https://example.com/post?utm_source=newsletter",
            title="t",
            source_id="s",
            source_name="S",
            category="ai_trend",
            published_at_kst=datetime(2026, 5, 19, 7, 30, tzinfo=KST),
            snippet="",
        )
    assert "canonicalize" in str(exc.value)


def test_article_accepts_already_canonical_url() -> None:
    """canonicalize 통과 형태는 그대로 받아들임."""
    art = Article(
        canonical_url="https://example.com/post",
        title="t",
        source_id="s",
        source_name="S",
        category="ai_trend",
        published_at_kst=datetime(2026, 5, 19, 7, 30, tzinfo=KST),
        snippet="",
    )
    assert art.canonical_url == "https://example.com/post"


# ---------- 2. Article published_at_kst tz-aware 강제 ----------


def test_article_rejects_naive_datetime() -> None:
    """tzinfo 없는 datetime 은 ValueError."""
    with pytest.raises(ValueError) as exc:
        Article(
            canonical_url="https://example.com/post",
            title="t",
            source_id="s",
            source_name="S",
            category="ai_trend",
            published_at_kst=datetime(2026, 5, 19, 7, 30),  # naive
            snippet="",
        )
    assert "tz-aware" in str(exc.value) or "naive" in str(exc.value)


# ---------- 3. RssFetcher 정상 feed mock ----------


def test_rss_fetcher_normal_feed() -> None:
    """feedparser.parse 를 mock — entries 2건 → Article 2건."""
    fake_parsed = _make_parsed_feed(
        [
            _make_feedparser_entry(
                title="Article 1",
                link="https://example.com/a?utm_source=feed",  # utm 제거 검증
            ),
            _make_feedparser_entry(
                title="Article 2",
                link="https://example.com/b/",  # trailing slash 제거 검증
            ),
        ]
    )

    source = _make_source(sid="rss_one", url="https://example.com/feed.xml")

    with patch("src.fetchers.rss.feedparser.parse", return_value=fake_parsed):
        articles = RssFetcher().fetch(source)

    assert len(articles) == 2
    # canonicalize 적용 확인 — utm 제거 + trailing slash 제거.
    assert articles[0].canonical_url == "https://example.com/a"
    assert articles[1].canonical_url == "https://example.com/b"
    # published_at_kst tz-aware 확인.
    assert articles[0].published_at_kst.tzinfo is not None
    # source 메타가 그대로 옮겨졌는지.
    assert articles[0].source_id == "rss_one"
    assert articles[0].source_name == "RSS One"
    assert articles[0].category == "ai_trend"
    # snippet 의 HTML 태그가 strip 됐는지.
    assert "<" not in articles[0].snippet
    assert "Some" in articles[0].snippet


def test_rss_fetcher_skips_entry_without_required_fields() -> None:
    """title/link 없는 entry 는 skip — 전체 raise 금지."""
    bad_entry = SimpleNamespace(
        title="", link="", summary="", published_parsed=None,
        updated_parsed=None, published="", updated="",
    )
    good_entry = _make_feedparser_entry(title="OK", link="https://example.com/ok")
    fake_parsed = _make_parsed_feed([bad_entry, good_entry])

    source = _make_source(sid="rss_two")
    with patch("src.fetchers.rss.feedparser.parse", return_value=fake_parsed):
        articles = RssFetcher().fetch(source)

    assert len(articles) == 1
    assert articles[0].title == "OK"


def test_rss_fetcher_bozo_feed_raises() -> None:
    """entries 비고 bozo_exception 만 있으면 ValueError (runner 가 parse_error 로 잡음)."""
    fake_parsed = _make_parsed_feed([], bozo=True)
    source = _make_source(sid="rss_bozo")
    with patch("src.fetchers.rss.feedparser.parse", return_value=fake_parsed):
        with pytest.raises(ValueError) as exc:
            RssFetcher().fetch(source)
    assert "bozo" in str(exc.value)


# ---------- 4. runner — disabled 소스 skip ----------


def test_run_all_skips_disabled_source() -> None:
    """`enabled=False` 소스는 fetch 시도 안 함 + Failure 0."""
    enabled_src = _make_source(sid="rss_enabled", enabled=True)
    disabled_src = _make_source(sid="rss_disabled", enabled=False)

    fake_parsed = _make_parsed_feed(
        [_make_feedparser_entry(link="https://example.com/x")]
    )

    with patch("src.fetchers.rss.feedparser.parse", return_value=fake_parsed):
        articles, failures = run_all([enabled_src, disabled_src])

    assert len(articles) == 1
    assert articles[0].source_id == "rss_enabled"
    assert failures == []


# ---------- 5. runner — timeout 격리 (anti-pattern C 핵심) ----------


def test_run_all_isolates_timeout_failure() -> None:
    """한 소스가 Timeout raise → Failure 1건(timeout) + 다른 소스 Article 정상."""
    ok_src = _make_source(sid="rss_ok", name="OK")
    timeout_src = _make_source(sid="rss_timeout", name="Slow", url="https://slow.example.com/feed")

    fake_parsed = _make_parsed_feed(
        [_make_feedparser_entry(link="https://example.com/ok-post")]
    )

    def fake_parse(url: str) -> SimpleNamespace:
        if url == "https://slow.example.com/feed":
            raise requests.exceptions.Timeout("simulated timeout")
        return fake_parsed

    with patch("src.fetchers.rss.feedparser.parse", side_effect=fake_parse):
        articles, failures = run_all([ok_src, timeout_src])

    assert len(articles) == 1
    assert articles[0].source_id == "rss_ok"
    assert len(failures) == 1
    assert failures[0].source_id == "rss_timeout"
    assert failures[0].error_kind == "timeout"


# ---------- 6. runner — html stub parse_error ----------


def test_run_all_html_stub_yields_parse_error() -> None:
    """HtmlFetcher stub 호출되는 소스 → Failure 1건(parse_error) + 다른 소스 정상."""
    rss_src = _make_source(sid="rss_ok", stype="rss")
    html_src = _make_source(
        sid="html_stub", name="HTML Stub", stype="html",
        url="https://example.com/page", cat="ai_trend",
    )

    fake_parsed = _make_parsed_feed(
        [_make_feedparser_entry(link="https://example.com/ok-post")]
    )

    with patch("src.fetchers.rss.feedparser.parse", return_value=fake_parsed):
        articles, failures = run_all([rss_src, html_src])

    assert len(articles) == 1
    assert articles[0].source_id == "rss_ok"
    assert len(failures) == 1
    assert failures[0].source_id == "html_stub"
    assert failures[0].error_kind == "parse_error"


# ---------- 7. runner — 전체 정상 ----------


def test_run_all_all_sources_ok() -> None:
    """모든 소스가 정상 → Failures 0, Articles 합본."""
    src_a = _make_source(sid="rss_a", url="https://a.example.com/feed")
    src_b = _make_source(sid="rss_b", url="https://b.example.com/feed")

    parsed_a = _make_parsed_feed(
        [
            _make_feedparser_entry(link="https://a.example.com/p1"),
            _make_feedparser_entry(link="https://a.example.com/p2"),
        ]
    )
    parsed_b = _make_parsed_feed(
        [_make_feedparser_entry(link="https://b.example.com/p1")]
    )

    def fake_parse(url: str) -> SimpleNamespace:
        if url.startswith("https://a."):
            return parsed_a
        return parsed_b

    with patch("src.fetchers.rss.feedparser.parse", side_effect=fake_parse):
        articles, failures = run_all([src_a, src_b])

    assert failures == []
    assert len(articles) == 3
    assert {a.source_id for a in articles} == {"rss_a", "rss_b"}


# ---------- 추가: http 4xx / 5xx 분류 ----------


def _make_http_error(status: int) -> requests.exceptions.HTTPError:
    resp = requests.models.Response()
    resp.status_code = status
    return requests.exceptions.HTTPError(f"{status} error", response=resp)


def test_run_all_classifies_http_4xx() -> None:
    """HTTPError status 404 → http_4xx."""
    src = _make_source(sid="rss_404")
    with patch(
        "src.fetchers.rss.feedparser.parse",
        side_effect=_make_http_error(404),
    ):
        articles, failures = run_all([src])
    assert articles == []
    assert len(failures) == 1
    assert failures[0].error_kind == "http_4xx"


def test_run_all_classifies_http_5xx() -> None:
    """HTTPError status 503 → http_5xx."""
    src = _make_source(sid="rss_503")
    with patch(
        "src.fetchers.rss.feedparser.parse",
        side_effect=_make_http_error(503),
    ):
        articles, failures = run_all([src])
    assert articles == []
    assert len(failures) == 1
    assert failures[0].error_kind == "http_5xx"


# ---------- V1 stub 어댑터 자체가 NotImplementedError 인지 확인 ----------


def test_html_fetcher_stub_raises_not_implemented() -> None:
    src = _make_source(sid="html_x", stype="html")
    with pytest.raises(NotImplementedError):
        HtmlFetcher().fetch(src)


def test_json_api_fetcher_stub_raises_not_implemented() -> None:
    src = _make_source(sid="json_x", stype="json_api")
    with pytest.raises(NotImplementedError):
        JsonApiFetcher().fetch(src)


# ---------- Failure dataclass — error_kind 5종 라벨 (단일 진실) ----------


def test_failure_dataclass_holds_5_kind_labels() -> None:
    """`Failure.error_kind` 가 5종 라벨 중 하나 — runner 가 부여하는 값 (단일 진실)."""
    for kind in ("timeout", "http_4xx", "http_5xx", "parse_error", "other"):
        f = Failure(
            source_id="x",
            source_name="X",
            error_kind=kind,  # type: ignore[arg-type]
            error_message="msg",
        )
        assert f.error_kind == kind
