"""애플 감성 v3 HTML + 텔레그램 인덱스 동시 생성 — 표시 로직과 규칙 단일 데이터 구조 공유.

CRITICAL #2 (표시 로직과 실제 규칙이 같은 helper/data 공유) 의 코드 측 단일 진실.
- 우선순위(priority) 매핑은 본 모듈의 `_score_to_priority` 1곳 — HTML·텔레그램·TL;DR 필터가 모두 사용.
- canonical_url 은 Article 생성 시 강제 — render 가 그대로 노출(AC-2.3-B, AC-3.3).
- 시각 표기는 `lib/time_helper.format_subject_date` / `_format_item_time` 으로 통일(AC-7.4).

샘플 동결 레퍼런스: `samples/2026-05-19-digest-preview-v3.html`. SAMPLE banner 만 제거.
신규 디자인 의존성(외부 CSS·이미지·jinja2 등) 추가 금지(AC-2.7 동결).

본 모듈은 dispatcher 로직(Pages publish · 텔레그램 send)을 호출하지 않는다 — step6.
"""

from __future__ import annotations

import html as _html
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.fetchers.base import Article, Failure
from src.lib.time_helper import KST, format_subject_date

from .client import CATEGORIES, ItemAnalysis, SummarizeResult

logger = logging.getLogger(__name__)

# 카테고리 메타 — eyebrow 색, label, 텔레그램 prefix (AC-2.7).
# HTML eyebrow 색은 v3 샘플의 cat-ai/agri/farmboss 클래스에 대응.
_CATEGORY_META: dict[str, dict[str, str]] = {
    "ai_trend": {
        "label": "AI 트렌드",
        "label_html": "AI 트렌드",
        "eyebrow_color": "#0a84ff",
        "class": "cat-ai",
        "tg_number": "①",
    },
    "agri_distribution": {
        "label": "농산물·유통",
        "label_html": "농산물 · 유통",
        "eyebrow_color": "#30a46c",
        "class": "cat-agri",
        "tg_number": "②",
    },
    "farmboss_keyword": {
        "label": "팜보스 관심 키워드",
        "label_html": "팜보스 관심 키워드",
        "eyebrow_color": "#d04545",
        "class": "cat-farmboss",
        "tg_number": "③",
    },
}

# 풋터 hallucination 경고 — AC-2.9 단일 진실.
_DISCLAIMER_TEXT = (
    '"회사 영향"은 봇이 회사 사업 컨텍스트를 토대로 생성한 분석입니다. '
    "원문에 없는 추론이 포함될 수 있으니, 의사결정 전 반드시 원문 링크를 함께 확인해 주세요."
)

# TL;DR 0건일 때 fallback 한 줄 — AC-2.11.
_TLDR_FALLBACK_TEXT = "오늘은 산업 동향 위주 (회사 직결 뉴스 없음)"

# 카테고리 0건일 때 노출 라인 — AC-2.1.
_EMPTY_CATEGORY_LINE = "오늘 새 뉴스 없음"

# 텔레그램 메시지 한도 (AC-2.3-A).
_TELEGRAM_MAX_BYTES = 4096


@dataclass(frozen=True)
class RenderedItem:
    """렌더된 기사 1건 — HTML·텔레그램이 같은 dataclass 공유 (CRITICAL #2)."""

    article: Article
    score: int
    summary: str
    company_impact: str
    priority: int  # 3 = ⭐⭐⭐, 2 = ⭐⭐, 1 = ⭐
    category_headline: str


@dataclass(frozen=True)
class RenderedDigest:
    """`build_digest` 의 결과 — dispatcher (step6) 가 그대로 발송.

    Attributes:
        html: GitHub Pages 본문 (애플 감성 v3, AC-2.7).
        telegram_text: 텔레그램 메시지 본문 (TL;DR + 카테고리 인덱스, AC-2.3-A).
        subject: 메시지 헤더 1줄 (AC-1.6 형식).
        item_count: 본문 표시된 항목 수.
        by_category: 카테고리별 RenderedItem (순서 보존).
        tldr_items: ⭐⭐⭐ 자동 추출 항목 (최대 3건, AC-2.11).
        meta: 카운트·실패 소스 등 운영 메타.
    """

    html: str
    telegram_text: str
    subject: str
    item_count: int
    by_category: dict[str, list[RenderedItem]]
    tldr_items: list[RenderedItem]
    meta: dict[str, Any] = field(default_factory=dict)


# ---------- 단일 진실 helper ----------


def _score_to_priority(score: int) -> int:
    """score 1~10 → priority 1~3 (AC-2.10).

    8~10 → 3 (⭐⭐⭐, ••●). 5~7 → 2 (⭐⭐, ••○). 1~4 → 1 (⭐, •○○).
    HTML 점 indicator·텔레그램 ⭐ 표기·TL;DR 자동 추출이 모두 본 함수의 결과를 사용.
    """
    if score >= 8:
        return 3
    if score >= 5:
        return 2
    return 1


def _priority_dots_html(priority: int) -> str:
    """priority → 점 3개 HTML (v3 샘플의 `.priority-dots` 구조 그대로)."""
    on = max(0, min(3, priority))  # 1→1, 2→2, 3→3
    dots: list[str] = []
    for i in range(3):
        cls = "d on" if i < on else "d"
        dots.append(f'<span class="{cls}"></span>')
    return f'<span class="priority-dots">{"".join(dots)}</span>'


def _priority_stars_text(priority: int) -> str:
    """priority → ⭐ 문자열 (텔레그램 표면 A)."""
    if priority == 3:
        return "⭐⭐⭐"
    if priority == 2:
        return "⭐⭐"
    return "⭐"


def _format_item_time(dt: datetime) -> str:
    """기사 publish 시각의 짧은 KST 표기 (v3 샘플 `06:12 KST` / `5/18 23:40 KST`).

    오늘이면 `HH:MM KST`, 다른 날이면 `M/D HH:MM KST`. 단일 helper 로 모든 항목 표기.
    """
    if dt.tzinfo is None:
        raise ValueError("article.published_at_kst 는 tz-aware 이어야 합니다.")
    kst_dt = dt.astimezone(KST)
    today_kst = datetime.now(KST).date()
    if kst_dt.date() == today_kst:
        return f"{kst_dt.hour:02d}:{kst_dt.minute:02d} KST"
    return f"{kst_dt.month}/{kst_dt.day} {kst_dt.hour:02d}:{kst_dt.minute:02d} KST"


def _format_subject(sent_at_kst: datetime, item_count: int) -> str:
    """AC-1.6 메시지 헤더 — `📰 [팜보스 트렌드] M/D(요일) 오늘의 뉴스 N건`."""
    if sent_at_kst.tzinfo is None:
        raise ValueError("sent_at_kst 는 tz-aware 이어야 합니다.")
    kst_dt = sent_at_kst.astimezone(KST)
    weekday_ko = ("월", "화", "수", "목", "금", "토", "일")[kst_dt.weekday()]
    return f"📰 [팜보스 트렌드] {kst_dt.month}/{kst_dt.day}({weekday_ko}) 오늘의 뉴스 {item_count}건"


def _format_pages_title(sent_at_kst: datetime) -> str:
    """Pages HTML `<title>` 태그 — `팜보스 트렌드 — 5월 19일` (v3 샘플)."""
    kst_dt = sent_at_kst.astimezone(KST)
    return f"팜보스 트렌드 — {kst_dt.month}월 {kst_dt.day}일"


def _format_hero_eyebrow(sent_at_kst: datetime) -> str:
    """Hero eyebrow — `2026 · 5 · 19 화요일 · KST 07:30` (v3 샘플)."""
    kst_dt = sent_at_kst.astimezone(KST)
    weekday_full = (
        "월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일",
    )[kst_dt.weekday()]
    hour_24 = kst_dt.hour
    return (
        f"{kst_dt.year} · {kst_dt.month} · {kst_dt.day} {weekday_full} "
        f"· KST {hour_24:02d}:{kst_dt.minute:02d}"
    )


def _format_failure_meta(fetch_failures: list[Failure], sources_total: int) -> tuple[str, str]:
    """실패 소스 메타 — (hero 메타 1줄, 텔레그램 헤더 1줄) — AC-5.2 단일 helper.

    Returns:
        (hero_html_inner, telegram_line). hero 는 split dot 표기를 위해 2 span 분리.
    """
    n_failed = len(fetch_failures)
    n_ok = max(0, sources_total - n_failed)
    if n_failed == 0:
        return (
            f"<span>소스 {sources_total}개 정상 수집</span>",
            f"(소스 {sources_total}개 정상 수집)",
        )
    failed_names = ", ".join(f.source_name for f in fetch_failures)
    return (
        (
            f"<span>소스 {sources_total}개 중 {n_ok}개 정상 수집</span>"
            f'<span class="dot">·</span>'
            f"<span>{n_failed}개 실패: {_html.escape(failed_names)}</span>"
        ),
        f"(소스 {sources_total}개 중 {n_ok}개 정상, {n_failed}개 실패: {failed_names})",
    )


def _build_rendered_items(
    by_category: dict[str, list[Article]],
    summarize_result: SummarizeResult,
) -> dict[str, list[RenderedItem]]:
    """Article + ItemAnalysis → RenderedItem (카테고리별 리스트).

    schema 위반 폐기된 article 은 본 단계에서도 누락(LLM이 분석 못 한 항목 노출 안 함).
    카테고리 순서·기사 순서는 입력 그대로 보존.
    """
    analyses_by_id: dict[str, ItemAnalysis] = {
        it.article_id: it for it in summarize_result.items
    }
    out: dict[str, list[RenderedItem]] = {c: [] for c in CATEGORIES}
    for cat in CATEGORIES:
        headline = summarize_result.category_headlines.get(cat, "")
        for art in by_category.get(cat, []):
            analysis = analyses_by_id.get(art.canonical_url)
            if analysis is None:
                # LLM 분석 누락 — render 도 제외 (CRITICAL #6 위반 방지: 요약 없는 본문 발송 금지).
                logger.warning(
                    "render — article %s 가 SummarizeResult 에 없음; 본문에서 제외.",
                    art.canonical_url,
                )
                continue
            out[cat].append(
                RenderedItem(
                    article=art,
                    score=analysis.score,
                    summary=analysis.summary,
                    company_impact=analysis.company_impact,
                    priority=_score_to_priority(analysis.score),
                    category_headline=headline,
                )
            )
    return out


def _select_tldr_items(rendered: dict[str, list[RenderedItem]]) -> list[RenderedItem]:
    """priority=3 항목을 score 내림차순으로 최대 3건 추출 (AC-2.11)."""
    all_priority_3 = [it for items in rendered.values() for it in items if it.priority == 3]
    all_priority_3.sort(key=lambda it: it.score, reverse=True)
    return all_priority_3[:3]


# ---------- HTML 빌더 ----------


def _hostname(url: str) -> str:
    """URL → 호스트명만 (v3 샘플의 `.src` span 표기용)."""
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower()
    except Exception:  # pragma: no cover
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _render_item_html(item: RenderedItem) -> str:
    """단일 article 항목 HTML — v3 샘플의 `<article class="item">` 구조 그대로."""
    art = item.article
    dots = _priority_dots_html(item.priority)
    pub_time = _html.escape(_format_item_time(art.published_at_kst))
    source_name = _html.escape(art.source_name)
    title_safe = _html.escape(art.title)
    summary_safe = _html.escape(item.summary)
    url_safe = _html.escape(art.canonical_url, quote=True)
    host_safe = _html.escape(_hostname(art.canonical_url))

    # 회사 영향 박스 — 빈 문자열이면 fallback (AC-2.5).
    if item.company_impact:
        impact_html = (
            f'<div class="impact"><strong>회사 영향 ·</strong> '
            f"{_html.escape(item.company_impact)}</div>"
        )
    else:
        impact_html = (
            '<div class="impact impact-empty">회사 직접 영향 없음</div>'
        )

    return (
        '    <article class="item">\n'
        '      <div class="topline">\n'
        f"        {dots}\n"
        f'        <span class="source-name">{source_name} · {pub_time}</span>\n'
        "      </div>\n"
        f"      <h3>{title_safe}</h3>\n"
        f'      <div class="body">{summary_safe}</div>\n'
        f"      {impact_html}\n"
        f'      <div class="link"><a href="{url_safe}">원문 읽기 →</a>'
        f'<span class="sep">·</span><span class="src">{host_safe}</span></div>\n'
        "    </article>\n"
    )


def _render_category_html(cat_id: str, items: list[RenderedItem], cat_index: int) -> str:
    """카테고리 섹션 HTML — v3 샘플의 `<section class="category">` 구조."""
    meta = _CATEGORY_META[cat_id]
    label = _html.escape(meta["label_html"])
    css_class = meta["class"]
    cat_num = f"Category {cat_index:02d}"

    # category headline — 비어있으면 표시 안 함 (AC-2.12).
    headline = ""
    if items:
        head = items[0].category_headline
        if head:
            headline = (
                f'    <p class="cat-headline">{_html.escape(head)}</p>\n'
            )

    if not items:
        # 카테고리 0건 — "오늘 새 뉴스 없음" 라인, 헤더는 유지 (AC-2.1).
        body = (
            f'    <p class="cat-headline" style="color:#86868b;font-style:italic;">'
            f"{_EMPTY_CATEGORY_LINE}</p>\n"
        )
    else:
        body = headline + "".join(_render_item_html(it) for it in items)

    return (
        f'  <section class="category {css_class}">\n'
        f'    <div class="cat-eyebrow">{cat_num}</div>\n'
        f'    <h2 class="cat-title">{label}</h2>\n'
        f"{body}"
        "  </section>\n\n"
    )


def _render_tldr_html(tldr_items: list[RenderedItem], total_count: int) -> str:
    """TL;DR 박스 HTML — v3 샘플의 `<section class="tldr">` 구조 (AC-2.11)."""
    if not tldr_items:
        return (
            '  <section class="tldr">\n'
            '    <div class="label">⚡ TL;DR</div>\n'
            '    <h2>오늘은 산업 동향 위주</h2>\n'
            f'    <div class="tldr-rest">{_html.escape(_TLDR_FALLBACK_TEXT)} '
            f"— 총 {total_count}건 정리.</div>\n"
            "  </section>\n\n"
        )

    parts = [
        '  <section class="tldr">\n',
        '    <div class="label">⚡ TL;DR</div>\n',
        f'    <h2>오늘 꼭 챙길 {len(tldr_items)}건</h2>\n',
    ]
    for i, it in enumerate(tldr_items, start=1):
        title_safe = _html.escape(it.article.title)
        # TL;DR reason 은 company_impact (빈 문자열이면 summary 첫 문장).
        reason = it.company_impact or it.summary
        reason_safe = _html.escape(reason)
        parts.append(
            f'    <div class="tldr-item">\n'
            f'      <div class="num">{i:02d}</div>\n'
            f'      <div class="title">{title_safe}</div>\n'
            f'      <div class="reason">{reason_safe}</div>\n'
            f"    </div>\n"
        )
    rest_count = total_count - len(tldr_items)
    if rest_count > 0:
        parts.append(
            f'    <div class="tldr-rest">그 외 {rest_count}건은 산업 동향 — '
            "본문에서 확인.</div>\n"
        )
    parts.append("  </section>\n\n")
    return "".join(parts)


def _render_hero_html(
    sent_at_kst: datetime,
    item_count: int,
    failure_hero_html: str,
) -> str:
    """Hero 섹션 — v3 샘플의 `<section class="hero">` 구조."""
    eyebrow_safe = _html.escape(_format_hero_eyebrow(sent_at_kst))
    return (
        '  <section class="hero">\n'
        f'    <div class="eyebrow">{eyebrow_safe}</div>\n'
        f'    <h1>오늘 챙길 <span class="accent">뉴스 {item_count}건</span>.</h1>\n'
        '    <p class="lede">AI·농산물 유통 동향, 그리고 팜보스 운영에 직결되는 변화.</p>\n'
        f'    <div class="meta">{failure_hero_html}</div>\n'
        "  </section>\n\n"
    )


def _render_footer_html(sent_at_kst: datetime) -> str:
    """Footer — v3 샘플 그대로 + hallucination 경고 (AC-2.6 + AC-2.9)."""
    kst_dt = sent_at_kst.astimezone(KST)
    return (
        "  <footer>\n"
        '    <p class="signature"><strong>팜보스 트렌드</strong> · '
        f"매일 KST 07:30 · {kst_dt.year} 팜보스 그룹</p>\n"
        f'    <p class="disclaimer">{_html.escape(_DISCLAIMER_TEXT)}</p>\n'
        '    <p class="disclaimer" style="margin-top:14px;">'
        "의견·소스 추가 요청은 단톡방에서. 운영: 팜보스 트렌드 봇.</p>\n"
        "  </footer>\n"
    )


# v3 샘플의 인라인 CSS 그대로 — SAMPLE banner block 만 제거.
_HTML_STYLE = """\
    :root {
      --ink: #1d1d1f;
      --ink-2: #424245;
      --mute: #86868b;
      --line: #d2d2d7;
      --bg: #ffffff;
      --tint: #06c;
      --tint-warm: #b4490e;
      --accent: #f5f5f7;
      --pri-3: #1d1d1f;
      --pri-2: #6e6e73;
      --pri-1: #aeaeb2;
    }
    * { box-sizing: border-box; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
    html, body { background: var(--bg); color: var(--ink);
                 font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                              "Helvetica Neue", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif;
                 line-height: 1.47; font-size: 17px; margin: 0; padding: 0; }
    body { font-weight: 400; letter-spacing: -0.022em; }

    .container { max-width: 720px; margin: 0 auto; padding: 64px 22px 96px; }

    /* Hero */
    .hero { padding: 32px 0 56px; text-align: center; }
    .hero .eyebrow { font-size: 13px; font-weight: 600; letter-spacing: 0.08em;
                     text-transform: uppercase; color: var(--mute); margin-bottom: 14px; }
    .hero h1 { font-size: 56px; line-height: 1.05; letter-spacing: -0.025em;
               font-weight: 700; margin: 0; color: var(--ink); }
    .hero h1 .accent { background: linear-gradient(135deg, #0a84ff 0%, #5e5ce6 100%);
                       -webkit-background-clip: text; background-clip: text;
                       -webkit-text-fill-color: transparent; }
    .hero .lede { margin-top: 22px; font-size: 21px; color: var(--ink-2); font-weight: 400;
                  letter-spacing: -0.018em; line-height: 1.4; }
    .hero .meta { margin-top: 20px; font-size: 14px; color: var(--mute);
                  display: flex; justify-content: center; gap: 18px; flex-wrap: wrap; }
    .hero .meta .dot { color: var(--line); }

    /* TL;DR */
    .tldr { margin: 56px 0 80px; padding: 40px 32px; background: var(--accent);
            border-radius: 18px; }
    .tldr .label { font-size: 12px; font-weight: 600; letter-spacing: 0.1em;
                   text-transform: uppercase; color: var(--tint); margin-bottom: 8px; }
    .tldr h2 { font-size: 28px; font-weight: 700; letter-spacing: -0.02em;
               margin: 0 0 22px; color: var(--ink); line-height: 1.15; }
    .tldr-item { padding: 18px 0; border-top: 1px solid rgba(0,0,0,0.08); }
    .tldr-item:first-of-type { border-top: none; padding-top: 0; }
    .tldr-item .num { font-size: 12px; font-weight: 700; color: var(--tint);
                      letter-spacing: 0.04em; margin-bottom: 4px; }
    .tldr-item .title { font-size: 19px; font-weight: 600; letter-spacing: -0.015em;
                        line-height: 1.3; color: var(--ink); margin-bottom: 6px; }
    .tldr-item .reason { font-size: 15px; color: var(--ink-2); line-height: 1.5; }
    .tldr-rest { margin-top: 18px; padding-top: 18px;
                 border-top: 1px solid rgba(0,0,0,0.08);
                 font-size: 14px; color: var(--mute); font-style: italic; }

    /* Category */
    section.category { margin: 80px 0 0; }
    .cat-eyebrow { font-size: 13px; font-weight: 600; letter-spacing: 0.08em;
                   text-transform: uppercase; color: var(--mute); margin-bottom: 8px; }
    .cat-ai .cat-eyebrow { color: #0a84ff; }
    .cat-agri .cat-eyebrow { color: #30a46c; }
    .cat-farmboss .cat-eyebrow { color: #d04545; }
    .cat-title { font-size: 36px; font-weight: 700; letter-spacing: -0.022em;
                 line-height: 1.1; margin: 0 0 12px; color: var(--ink); }
    .cat-headline { font-size: 18px; color: var(--ink-2); letter-spacing: -0.012em;
                    margin-bottom: 36px; line-height: 1.45; }

    /* Items */
    .item { padding: 32px 0; border-top: 1px solid var(--line); }
    .item:last-child { border-bottom: 1px solid var(--line); }
    .item .topline { display: flex; align-items: center; gap: 10px;
                     margin-bottom: 10px; font-size: 12px; letter-spacing: 0.04em;
                     text-transform: uppercase; color: var(--mute); font-weight: 600; }
    .priority-dots { display: inline-flex; gap: 3px; }
    .priority-dots .d { width: 6px; height: 6px; border-radius: 50%;
                        background: var(--pri-1); display: inline-block; }
    .priority-dots .d.on { background: var(--ink); }
    .item .source-name { color: var(--mute); }
    .item h3 { font-size: 24px; font-weight: 600; letter-spacing: -0.018em;
               line-height: 1.22; margin: 0 0 12px; color: var(--ink); }
    .item h3 .orig { color: var(--mute); font-weight: 400; font-size: 16px;
                     letter-spacing: -0.012em; margin-left: 4px; }
    .item .body { font-size: 17px; color: var(--ink-2); line-height: 1.55;
                  letter-spacing: -0.012em; }
    .item .impact { margin-top: 18px; padding: 16px 20px; background: var(--accent);
                    border-radius: 12px; font-size: 15px; color: var(--ink);
                    line-height: 1.5; letter-spacing: -0.01em; }
    .item .impact strong { font-weight: 600; }
    .item .impact-empty { color: var(--mute); background: transparent;
                          padding: 12px 0 0; font-size: 13px; font-style: italic; }
    .item .link { margin-top: 16px; font-size: 14px; }
    .item .link a { color: var(--tint); text-decoration: none; font-weight: 500; }
    .item .link a:hover { text-decoration: underline; }
    .item .link .sep { color: var(--line); margin: 0 6px; }
    .item .link .src { color: var(--mute); }

    /* Footer */
    footer { margin-top: 96px; padding-top: 32px; border-top: 1px solid var(--line);
             text-align: center; }
    footer .signature { font-size: 13px; color: var(--mute); letter-spacing: 0.02em; }
    footer .signature strong { color: var(--ink-2); font-weight: 600; }
    footer .disclaimer { margin-top: 20px; font-size: 12px; color: var(--mute);
                         line-height: 1.5; max-width: 560px; margin-left: auto;
                         margin-right: auto; }

    @media (max-width: 600px) {
      .container { padding: 36px 18px 64px; }
      .hero h1 { font-size: 40px; }
      .hero .lede { font-size: 18px; }
      .cat-title { font-size: 28px; }
      .item h3 { font-size: 20px; }
      .tldr { padding: 28px 22px; }
      .tldr h2 { font-size: 22px; }
    }
"""


def _render_full_html(
    sent_at_kst: datetime,
    item_count: int,
    failure_hero_html: str,
    tldr_html: str,
    categories_html: str,
) -> str:
    """전체 HTML 조립. `<meta name="robots">` (AC-2.8) 포함."""
    title_safe = _html.escape(_format_pages_title(sent_at_kst))
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="robots" content="noindex,nofollow">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>{title_safe}</title>\n"
        "  <style>\n"
        f"{_HTML_STYLE}"
        "  </style>\n"
        "</head>\n"
        "<body>\n\n"
        '<div class="container">\n\n'
        + _render_hero_html(sent_at_kst, item_count, failure_hero_html)
        + tldr_html
        + categories_html
        + _render_footer_html(sent_at_kst)
        + "\n</div>\n\n</body>\n</html>\n"
    )


# ---------- 텔레그램 빌더 ----------


def _render_telegram_text(
    subject: str,
    failure_line: str,
    tldr_items: list[RenderedItem],
    by_category: dict[str, list[RenderedItem]],
    total_count: int,
    pages_url: str,
) -> str:
    """텔레그램 인덱스 메시지 — AC-2.3-A form.

    `disable_web_page_preview=true` 는 dispatcher 측에서 설정.
    """
    lines: list[str] = [subject, failure_line, ""]

    # TL;DR 영역 — 메시지 상단 2~3줄 (AC-2.11).
    if tldr_items:
        lines.append(f"⚡ 오늘 꼭 챙길 {len(tldr_items)}건")
        for it in tldr_items:
            stars = _priority_stars_text(it.priority)
            lines.append(f"  {stars} {it.article.title}")
    else:
        lines.append("⚡ 오늘은 산업 동향 위주")
        lines.append(f"  {_TLDR_FALLBACK_TEXT} — 총 {total_count}건")
    lines.append("")

    # 카테고리 인덱스 — 헤드라인 한 줄씩.
    for cat in CATEGORIES:
        meta = _CATEGORY_META[cat]
        items = by_category.get(cat, [])
        n = len(items)
        lines.append(f"{meta['tg_number']} {meta['label']} ({n}건)")
        if not items:
            lines.append(f"  • {_EMPTY_CATEGORY_LINE}")
            continue
        first = items[0]
        rest = n - 1
        stars = _priority_stars_text(first.priority)
        if rest > 0:
            lines.append(f"  • {stars} {first.article.title} 외 {rest}건")
        else:
            lines.append(f"  • {stars} {first.article.title}")
    lines.append("")

    if pages_url:
        lines.append(f"전체 본문: {pages_url}")
    lines.append("의견·소스 제안은 단톡방 답글로.")

    text = "\n".join(lines)
    # AC-2.3-A 한도 검사 — 안전망. 4096 초과 시 잘라내고 알림 줄 추가.
    encoded_len = len(text.encode("utf-8"))
    if encoded_len > _TELEGRAM_MAX_BYTES:
        # bytes 기준 안전 자름 — 유니코드 boundary 보장 위해 char 단위 절단 후 길이 재확인.
        suffix = "\n…(중략, 전체 본문 링크 참조)"
        # 단순 char-trim — 한국어 평균 3바이트 가정, 여유 있게 잘라 재검증.
        while len(text.encode("utf-8")) + len(suffix.encode("utf-8")) > _TELEGRAM_MAX_BYTES and text:
            text = text[:-1]
        text = text + suffix
        logger.warning(
            "telegram_text — 한도 초과로 자름. 최종 bytes=%d", len(text.encode("utf-8")),
        )
    return text


# ---------- 공개 API ----------


def build_digest(
    by_category: dict[str, list[Article]],
    summarize_result: SummarizeResult,
    fetch_failures: list[Failure],
    sent_at_kst: datetime,
    sources_total: int,
    pages_url_template: str = "",
) -> RenderedDigest:
    """애플 감성 v3 HTML + 텔레그램 인덱스 동시 생성.

    Args:
        by_category: filters.pipeline.apply 결과.
        summarize_result: SummarizerClient.summarize 결과.
        fetch_failures: fetchers.runner.run_all 결과 failures.
        sent_at_kst: 발송 시각 (KST tz-aware).
        sources_total: 전체 소스 수 (성공+실패 합).
        pages_url_template: step6 dispatcher 가 채우는 Pages URL. render 시점에는
            placeholder 가능. 빈 문자열이면 텔레그램 본문에 URL 라인 생략.

    Returns:
        RenderedDigest — html / telegram_text / subject / by_category 등.
    """
    if sent_at_kst.tzinfo is None:
        raise ValueError("sent_at_kst 는 tz-aware 이어야 합니다.")
    if sources_total < 0:
        raise ValueError("sources_total 은 0 이상이어야 합니다.")

    rendered = _build_rendered_items(by_category, summarize_result)
    item_count = sum(len(v) for v in rendered.values())
    tldr_items = _select_tldr_items(rendered)

    # 실패 메타 — 단일 helper (AC-5.2).
    hero_failure_html, telegram_failure_line = _format_failure_meta(
        fetch_failures, sources_total
    )

    # HTML 빌드.
    tldr_html = _render_tldr_html(tldr_items, item_count)
    categories_html = "".join(
        _render_category_html(cat, rendered[cat], i)
        for i, cat in enumerate(CATEGORIES, start=1)
    )
    html_full = _render_full_html(
        sent_at_kst, item_count, hero_failure_html, tldr_html, categories_html,
    )

    # 텔레그램 빌드.
    subject = _format_subject(sent_at_kst, item_count)
    telegram_text = _render_telegram_text(
        subject,
        telegram_failure_line,
        tldr_items,
        rendered,
        item_count,
        pages_url_template,
    )

    meta: dict[str, Any] = {
        "sent_at_kst": format_subject_date(sent_at_kst),
        "sources_total": sources_total,
        "failed_sources": [
            {"id": f.source_id, "name": f.source_name, "kind": f.error_kind}
            for f in fetch_failures
        ],
        "dropped_items": summarize_result.dropped_items,
        "tokens_in": summarize_result.tokens_in,
        "tokens_out": summarize_result.tokens_out,
        "tldr_count": len(tldr_items),
    }

    return RenderedDigest(
        html=html_full,
        telegram_text=telegram_text,
        subject=subject,
        item_count=item_count,
        by_category=rendered,
        tldr_items=tldr_items,
        meta=meta,
    )
