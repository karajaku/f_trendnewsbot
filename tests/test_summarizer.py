"""`src.summarizer` 단위 테스트 — step5.md AC 매핑.

전부 mock 기반. 실제 Gemini API 호출은 금지 (step5 수동 테스트 절차 §1~5 + step8 dry-run).
ADR-004 (2026-05-19): Anthropic Claude Haiku 4.5 → Google Gemini 2.0 Flash swap. mock 구조도 동기.

매핑:
    AC-5.5 input cap → test_quota_raises_on_input_tokens_cap
    AC-5.5 output cap → test_quota_raises_on_output_tokens_cap
    AC-5.5 calls cap → test_quota_raises_on_calls_cap
    AC-2.10·2.12 mock 응답 JSON 파싱 → test_client_summarize_parses_mock_response
    AC-2.10 markdown fence 처리 → test_client_summarize_parses_markdown_fence
    AC-2.10·2.12 schema 위반 폐기 → test_client_summarize_drops_schema_violations
    AC-5.3 rate limit → QuotaExceededError → test_client_summarize_maps_rate_limit_to_quota_exceeded
    AC-2.10 score→priority 매핑 → test_render_priority_mapping
    AC-2.11 TL;DR 1건 → test_render_tldr_with_priority_3
    AC-2.11 TL;DR 0건 fallback → test_render_tldr_fallback_when_no_priority_3
    AC-2.1 카테고리 0건 → test_render_empty_category_keeps_header
    AC-2.8 robots meta → test_render_html_contains_robots_meta
    AC-2.3-A 텔레그램 한도 → test_render_telegram_text_within_limit
    §6-5 광고 문구 차단 → test_render_no_advertorial_lines
    AC-2.3-B canonical_url 노출 → test_render_includes_all_canonical_urls
    AC-2.1 글로벌 상한 컷 → test_render_caps_to_max_items_by_score
    AC-2.1 후보 ≤ 상한 무동작 → test_render_no_cap_when_candidates_within_max
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.fetchers.base import Article
from src.lib.time_helper import KST
from src.lib.url_helper import canonicalize
from src.summarizer.client import (
    CATEGORIES,
    SummarizeResult,
    SummarizerClient,
)
from src.summarizer.quota import (
    HARD_CAP_CALLS,
    QuotaExceededError,
    QuotaTracker,
)
from src.summarizer.render import (
    _score_to_priority,
    build_digest,
)


# ---------- fixtures ----------


def _kst(year: int, month: int, day: int, hour: int = 7, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=KST)


def _make_article(
    url: str,
    title: str,
    source_id: str,
    source_name: str,
    category: str,
    published: datetime | None = None,
    snippet: str = "기사 본문 일부.",
) -> Article:
    return Article(
        canonical_url=canonicalize(url),
        title=title,
        source_id=source_id,
        source_name=source_name,
        category=category,
        published_at_kst=published or _kst(2026, 5, 19, 6, 0),
        snippet=snippet,
    )


def _make_mock_gemini_response(
    items_payload: list[dict],
    category_headlines: dict[str, str] | None = None,
    *,
    prompt_tokens: int = 5000,
    output_tokens: int = 1200,
    wrap_fence: bool = False,
) -> MagicMock:
    """google-genai `models.generate_content` 응답 객체 mock.

    `response.text` 와 `response.usage_metadata.prompt_token_count / candidates_token_count`
    구조를 흉내냄 (google-genai 2.4+ 인터페이스).
    """
    payload = {
        "items": items_payload,
        "category_headlines": category_headlines
        or {cat: "" for cat in CATEGORIES},
    }
    text_body = json.dumps(payload, ensure_ascii=False)
    if wrap_fence:
        text_body = f"```json\n{text_body}\n```"

    resp = MagicMock()
    resp.text = text_body
    resp.usage_metadata = MagicMock(
        prompt_token_count=prompt_tokens,
        candidates_token_count=output_tokens,
    )
    # 2026-05-19 핫픽스: finish_reason 검사 (truncate 회귀 진단) — STOP 만 정상.
    candidate = MagicMock()
    candidate.finish_reason = MagicMock(value="STOP")
    resp.candidates = [candidate]
    return resp


def _make_summarize_result_for_articles(
    articles_by_cat: dict[str, list[Article]],
    score_overrides: dict[str, int] | None = None,
    headlines: dict[str, str] | None = None,
) -> SummarizeResult:
    """fixture Article 묶음에 대해 render 단위 검증용 SummarizeResult 직접 구성."""
    from src.summarizer.client import ItemAnalysis

    items: list[ItemAnalysis] = []
    score_overrides = score_overrides or {}
    for cat in CATEGORIES:
        for art in articles_by_cat.get(cat, []):
            sc = score_overrides.get(art.canonical_url, 5)
            items.append(
                ItemAnalysis(
                    article_id=art.canonical_url,
                    score=sc,
                    summary=f"{art.title} 요약.",
                    company_impact=(
                        "정다운(j) 산지 수매 일정 영향." if sc >= 8 else ""
                    ),
                )
            )
    return SummarizeResult(
        items=items,
        category_headlines=headlines or {cat: "" for cat in CATEGORIES},
        dropped_items=0,
        tokens_in=5000,
        tokens_out=1200,
    )


# ---------- quota tests ----------


def test_quota_raises_on_input_tokens_cap() -> None:
    """누적 input 토큰이 cap(100k)을 초과하면 즉시 `QuotaExceededError`. 누적은 미반영."""
    tracker = QuotaTracker()
    tracker.check_and_record(50_000, 1_000)
    # 다음 호출이 cap 을 1 만큼 초과해야 함 — 100_000 - 50_000 = 50_000 cap 남음.
    with pytest.raises(QuotaExceededError) as exc:
        tracker.check_and_record(50_001, 1_000)
    assert "input tokens cap 초과" in str(exc.value)
    # 누적 미반영 확인.
    assert tracker.state["tokens_in"] == 50_000
    assert tracker.state["calls"] == 1


def test_quota_raises_on_output_tokens_cap() -> None:
    """누적 output 토큰이 cap(20k)을 초과하면 즉시 raise."""
    tracker = QuotaTracker()
    tracker.check_and_record(1_000, 19_000)
    with pytest.raises(QuotaExceededError) as exc:
        tracker.check_and_record(1_000, 1_001)
    assert "output tokens cap 초과" in str(exc.value)
    assert tracker.state["tokens_out"] == 19_000


def test_quota_raises_on_calls_cap() -> None:
    """일일 호출 수가 cap(30)을 초과하면 즉시 raise."""
    tracker = QuotaTracker()
    for _ in range(HARD_CAP_CALLS):
        tracker.check_and_record(1, 1)
    assert tracker.state["calls"] == HARD_CAP_CALLS
    with pytest.raises(QuotaExceededError) as exc:
        tracker.check_and_record(1, 1)
    assert "calls cap 초과" in str(exc.value)


# ---------- client.summarize tests ----------


def _make_articles_simple() -> dict[str, list[Article]]:
    """1 카테고리당 1건씩 — client 검증 fixture."""
    a1 = _make_article(
        "https://example.com/a1",
        "Article 1",
        "rss_one",
        "Source One",
        "ai_trend",
    )
    a2 = _make_article(
        "https://example.com/a2",
        "Article 2",
        "rss_two",
        "Source Two",
        "agri_distribution",
    )
    a3 = _make_article(
        "https://example.com/a3",
        "Article 3",
        "rss_three",
        "Source Three",
        "farmboss_keyword",
    )
    return {
        "ai_trend": [a1],
        "agri_distribution": [a2],
        "farmboss_keyword": [a3],
    }


def test_client_summarize_parses_mock_response() -> None:
    """Gemini 응답을 JSON 으로 파싱해 `SummarizeResult` 반환."""
    arts = _make_articles_simple()
    items_payload = [
        {
            "id": arts["ai_trend"][0].canonical_url,
            "score": 9,
            "summary": "Google Gemini 신모델 출시.",
            "company_impact": "본 봇 운영 비용 영향 가능성.",
        },
        {
            "id": arts["agri_distribution"][0].canonical_url,
            "score": 6,
            "summary": "GS리테일 산지 직배송 확대.",
            "company_impact": "정다운(j) 납품 점검 필요.",
        },
        {
            "id": arts["farmboss_keyword"][0].canonical_url,
            "score": 3,
            "summary": "산업 동향 참고.",
            "company_impact": "",
        },
    ]
    headlines = {
        "ai_trend": "오늘은 LLM 출시 동시.",
        "agri_distribution": "GS·쿠팡 산지·콜드체인 확장.",
        "farmboss_keyword": "",
    }
    mock_resp = _make_mock_gemini_response(items_payload, headlines)

    with patch("src.summarizer.client.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_resp
        client = SummarizerClient(api_key="test-gemini-key-1234")
        result = client.summarize(arts, system_prompt="(system prompt body)")

    assert len(result.items) == 3
    assert result.dropped_items == 0
    assert result.tokens_in == 5000
    assert result.tokens_out == 1200
    assert result.category_headlines["ai_trend"] == "오늘은 LLM 출시 동시."
    assert result.category_headlines["farmboss_keyword"] == ""


def test_client_summarize_parses_markdown_fence() -> None:
    """응답이 ```json ... ``` 로 감싸져도 fence 제거 후 파싱 (방어선)."""
    arts = _make_articles_simple()
    items_payload = [
        {
            "id": arts["ai_trend"][0].canonical_url,
            "score": 7,
            "summary": "OK.",
            "company_impact": "",
        },
    ]
    mock_resp = _make_mock_gemini_response(
        items_payload, wrap_fence=True,
    )
    with patch("src.summarizer.client.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_resp
        client = SummarizerClient(api_key="test-gemini-key-1234")
        result = client.summarize(arts, system_prompt="(prompt)")

    assert len(result.items) == 1
    assert result.items[0].score == 7


def test_client_summarize_drops_schema_violations() -> None:
    """schema 위반 항목(필드 누락·score 범위 밖·id 불일치·company_impact 타입 오류)은 폐기 + dropped_items 증가."""
    arts = _make_articles_simple()
    items_payload = [
        # valid
        {
            "id": arts["ai_trend"][0].canonical_url,
            "score": 8,
            "summary": "valid.",
            "company_impact": "",
        },
        # 필드 누락
        {
            "id": arts["agri_distribution"][0].canonical_url,
            "score": 5,
            "summary": "missing impact",
        },
        # score 범위 밖
        {
            "id": arts["farmboss_keyword"][0].canonical_url,
            "score": 99,
            "summary": "out of range",
            "company_impact": "",
        },
        # id 불일치 (입력 article 에 없음)
        {
            "id": "https://nonexistent.example.com/x",
            "score": 5,
            "summary": "id mismatch",
            "company_impact": "",
        },
        # company_impact 타입 오류
        {
            "id": arts["ai_trend"][0].canonical_url,
            "score": 5,
            "summary": "impact not string",
            "company_impact": 42,
        },
    ]
    mock_resp = _make_mock_gemini_response(items_payload)
    with patch("src.summarizer.client.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_resp
        client = SummarizerClient(api_key="test-gemini-key-1234")
        result = client.summarize(arts, system_prompt="(prompt)")

    assert len(result.items) == 1
    assert result.dropped_items == 4


def test_client_summarize_maps_rate_limit_to_quota_exceeded() -> None:
    """Gemini API rate limit (429 / RESOURCE_EXHAUSTED) → `QuotaExceededError` 매핑 (AC-5.3).

    `run_daily.py` 의 `except QuotaExceededError` 분기가 받아 exit 2 + ops_alert.
    """
    from google.genai import errors as genai_errors

    arts = _make_articles_simple()
    err = genai_errors.ClientError(
        429,
        {"error": {"message": "Quota exceeded for model gemini-2.5-flash",
                   "status": "RESOURCE_EXHAUSTED"}},
    )

    with patch("src.summarizer.client.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.side_effect = err
        client = SummarizerClient(api_key="test-gemini-key-1234")
        with pytest.raises(QuotaExceededError) as exc_info:
            client.summarize(arts, system_prompt="(prompt)")

    assert "quota" in str(exc_info.value).lower() or "rate limit" in str(exc_info.value).lower()


# ---------- render tests ----------


def test_render_priority_mapping() -> None:
    """score 8/5/3 → priority 3/2/1 (AC-2.10 단일 진실)."""
    assert _score_to_priority(8) == 3
    assert _score_to_priority(10) == 3
    assert _score_to_priority(5) == 2
    assert _score_to_priority(7) == 2
    assert _score_to_priority(3) == 1
    assert _score_to_priority(1) == 1


def test_render_tldr_with_priority_3() -> None:
    """priority=3 항목 1건이면 TL;DR 1건 노출, html h2 에 표기."""
    a1 = _make_article(
        "https://example.com/big",
        "GS리테일 직배송 확대",
        "gs",
        "GS Retail",
        "agri_distribution",
    )
    by_cat: dict[str, list[Article]] = {
        "ai_trend": [],
        "agri_distribution": [a1],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(
        by_cat, score_overrides={a1.canonical_url: 9}
    )
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=1,
        max_items=10,
    )
    assert len(digest.tldr_items) == 1
    assert "오늘 꼭 챙길 1건" in digest.html
    # 텔레그램 본문에도 TL;DR 라인 포함.
    assert "⚡ 오늘 꼭 챙길 1건" in digest.telegram_text


def test_render_tldr_fallback_when_no_priority_3() -> None:
    """priority=3 항목 0건이면 TL;DR fallback 문구 노출 (AC-2.11)."""
    a1 = _make_article(
        "https://example.com/x",
        "산업 동향 기사",
        "src",
        "Source",
        "ai_trend",
    )
    by_cat: dict[str, list[Article]] = {
        "ai_trend": [a1],
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(
        by_cat, score_overrides={a1.canonical_url: 4}
    )
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=1,
        max_items=10,
    )
    assert digest.tldr_items == []
    # HTML / telegram 모두 fallback 문구 ("산업 동향") 포함.
    assert "산업 동향" in digest.html
    assert "산업 동향" in digest.telegram_text


def test_render_empty_category_keeps_header() -> None:
    """카테고리 0건이면 '오늘 새 뉴스 없음' 라인 + 카테고리 헤더 유지 (AC-2.1)."""
    by_cat: dict[str, list[Article]] = {
        "ai_trend": [],
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(by_cat)
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=3,
        max_items=10,
    )
    assert "오늘 새 뉴스 없음" in digest.html
    # 카테고리 헤더 3개 모두 살아있어야 함.
    assert "AI 트렌드" in digest.html
    assert "농산물" in digest.html
    assert "팜보스 관심 키워드" in digest.html


def test_render_html_contains_robots_meta() -> None:
    """HTML head 에 `<meta name=\"robots\" content=\"noindex,nofollow\">` 포함 (AC-2.8)."""
    by_cat: dict[str, list[Article]] = {c: [] for c in CATEGORIES}
    sr = _make_summarize_result_for_articles(by_cat)
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=0,
        max_items=10,
    )
    assert '<meta name="robots" content="noindex,nofollow">' in digest.html


def test_render_telegram_text_within_limit() -> None:
    """텔레그램 메시지는 4096 바이트 이내 (AC-2.3-A)."""
    # 의도적으로 많은 항목 — 한도 검사 안전망 작동 확인.
    arts: list[Article] = []
    for i in range(8):
        arts.append(
            _make_article(
                f"https://example.com/n{i}",
                f"기사 제목 {i} — " + ("긴 한국어 제목 " * 8),
                f"src_{i}",
                f"Source {i}",
                "ai_trend",
            )
        )
    by_cat: dict[str, list[Article]] = {
        "ai_trend": arts,
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(
        by_cat, score_overrides={a.canonical_url: 9 for a in arts}
    )
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=8,
        max_items=10,
    )
    assert len(digest.telegram_text.encode("utf-8")) <= 4096


def test_render_no_advertorial_lines() -> None:
    """본문 어디에도 '왜 중요'·'why it matters'·'당신에게 의미' 류 광고형 라인 없음 (§6-5)."""
    a1 = _make_article(
        "https://example.com/p1",
        "테스트 기사",
        "src",
        "Source",
        "ai_trend",
    )
    by_cat: dict[str, list[Article]] = {
        "ai_trend": [a1],
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(
        by_cat, score_overrides={a1.canonical_url: 9}
    )
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=1,
        max_items=10,
    )
    banned = ("why it matters", "당신에게 의미", "왜 중요")
    for phrase in banned:
        assert phrase.lower() not in digest.html.lower()
        assert phrase.lower() not in digest.telegram_text.lower()


def test_render_includes_all_canonical_urls() -> None:
    """모든 입력 Article 의 canonical_url 이 본문에 노출 (AC-2.3-B)."""
    arts = []
    urls_expected: list[str] = []
    for i in range(3):
        a = _make_article(
            f"https://example.com/x{i}?utm_source=foo",  # canonicalize 가 utm 제거.
            f"기사 {i}",
            f"src_{i}",
            f"Source {i}",
            "ai_trend",
        )
        arts.append(a)
        urls_expected.append(a.canonical_url)

    by_cat: dict[str, list[Article]] = {
        "ai_trend": arts,
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(by_cat)
    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=1,
        max_items=10,
    )
    for url in urls_expected:
        # utm 제거된 canonical 형태가 본문에 노출되어야 함.
        assert "utm_source" not in url
        assert url in digest.html


def test_render_caps_to_max_items_by_score() -> None:
    """후보 > max_items 이면 score 글로벌 상위 N건만 발송 (phase 03, AC-2.1).

    카테고리 경계를 넘어 글로벌 컷 — 고득점 카테고리 전량 + 저득점 카테고리 일부.
    """
    ai = [
        _make_article(f"https://example.com/ai{i}", f"AI 기사 {i}", f"ai{i}", f"AI {i}", "ai_trend")
        for i in range(6)
    ]
    agri = [
        _make_article(
            f"https://example.com/ag{i}", f"농산물 기사 {i}", f"ag{i}", f"Agri {i}", "agri_distribution"
        )
        for i in range(4)
    ]
    farm = [
        _make_article(
            f"https://example.com/fb{i}", f"팜보스 기사 {i}", f"fb{i}", f"Farm {i}", "farmboss_keyword"
        )
        for i in range(4)
    ]
    by_cat: dict[str, list[Article]] = {
        "ai_trend": ai,
        "agri_distribution": agri,
        "farmboss_keyword": farm,
    }
    overrides: dict[str, int] = {}
    for a in ai:
        overrides[a.canonical_url] = 4  # 저득점
    for a in agri:
        overrides[a.canonical_url] = 8  # 고득점
    for a in farm:
        overrides[a.canonical_url] = 9  # 최고득점
    sr = _make_summarize_result_for_articles(by_cat, score_overrides=overrides)

    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=3,
        max_items=10,
    )

    # 후보 14건 → 상한 10건.
    assert digest.item_count == 10
    # 글로벌 컷 — farmboss(9)·agri(8) 전량 + ai_trend(4) 상위 2건만.
    assert len(digest.by_category["farmboss_keyword"]) == 4
    assert len(digest.by_category["agri_distribution"]) == 4
    assert len(digest.by_category["ai_trend"]) == 2
    # 카테고리 내 상대 순서 보존 — 살아남은 ai_trend 2건은 입력 앞 2건.
    kept_ai = digest.by_category["ai_trend"]
    assert kept_ai[0].article.canonical_url == ai[0].canonical_url
    assert kept_ai[1].article.canonical_url == ai[1].canonical_url
    # 컷된 저득점 ai_trend 기사는 본문에서 빠짐.
    for dropped in ai[2:]:
        assert dropped.canonical_url not in digest.html
    # 운영 가시성 메타.
    assert digest.meta["candidate_count"] == 14
    assert digest.meta["max_items"] == 10


def test_render_no_cap_when_candidates_within_max() -> None:
    """후보 ≤ max_items 이면 컷 무동작 — 전량 발송 (phase 03)."""
    arts = [
        _make_article(f"https://example.com/n{i}", f"기사 {i}", f"s{i}", f"S {i}", "ai_trend")
        for i in range(5)
    ]
    by_cat: dict[str, list[Article]] = {
        "ai_trend": arts,
        "agri_distribution": [],
        "farmboss_keyword": [],
    }
    sr = _make_summarize_result_for_articles(by_cat)

    digest = build_digest(
        by_category=by_cat,
        summarize_result=sr,
        fetch_failures=[],
        sent_at_kst=_kst(2026, 5, 19, 7, 30),
        sources_total=1,
        max_items=10,
    )

    assert digest.item_count == 5
    assert len(digest.by_category["ai_trend"]) == 5
    assert digest.meta["candidate_count"] == 5
