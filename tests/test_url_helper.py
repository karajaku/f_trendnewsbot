"""`lib/url_helper.canonicalize` 단위 테스트 — AC-4.1, step1.md AC 6건 매핑."""

from __future__ import annotations

import pytest

from src.lib.url_helper import canonicalize


def test_canonicalize_normal_url_preserved() -> None:
    """정상 URL 은 변경 없이 그대로 반환되어야 한다 (host 이미 소문자, 추적/fragment/slash 없음)."""
    url = "https://example.com/articles/123"
    assert canonicalize(url) == "https://example.com/articles/123"


def test_canonicalize_strips_tracking_params_and_keeps_regular_query() -> None:
    """`utm_*`/`fbclid` 같은 추적 파라미터는 제거하고 일반 쿼리는 보존한다."""
    url = (
        "https://example.com/post"
        "?utm_source=newsletter&utm_medium=email&fbclid=xyz"
        "&id=42&page=3"
    )
    result = canonicalize(url)
    assert result == "https://example.com/post?id=42&page=3"


def test_canonicalize_drops_fragment() -> None:
    """`#section` fragment 는 dedup 비교 단위가 아니므로 제거한다."""
    url = "https://example.com/news/article-1#section-2"
    assert canonicalize(url) == "https://example.com/news/article-1"


def test_canonicalize_trailing_slash_handling() -> None:
    """경로 끝 trailing slash 는 제거하되, 경로가 `/` 단독이면 보존한다."""
    # trailing slash 제거.
    assert canonicalize("https://example.com/articles/") == "https://example.com/articles"
    # 루트 경로 `/` 는 보존 — 빈 경로와 구분.
    assert canonicalize("https://example.com/") == "https://example.com/"


def test_canonicalize_lowercases_host_only() -> None:
    """대문자 host 는 소문자로, 경로의 대소문자는 그대로 유지한다."""
    url = "HTTPS://Example.COM/Path/To/Page"
    assert canonicalize(url) == "https://example.com/Path/To/Page"


def test_canonicalize_rejects_empty_and_invalid_urls() -> None:
    """빈 문자열·scheme/netloc 누락 URL 은 `ValueError` 로 거부한다."""
    with pytest.raises(ValueError):
        canonicalize("")
    with pytest.raises(ValueError):
        canonicalize("   ")
    with pytest.raises(ValueError):
        # scheme 누락
        canonicalize("example.com/path")
    with pytest.raises(ValueError):
        # netloc 누락 (scheme 만 있음)
        canonicalize("https://")
