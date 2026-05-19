"""Step5 산출물 시각 검증용 — v3 mockup 8건을 fixture 로 `render.build_digest()` 호출.

`samples/2026-05-19-digest-preview-v4-from-render.html` 생성 + subject·telegram_text 출력.
실제 Anthropic API 호출 0회 — 모두 fixture data.

실행:
    python scripts/render_sample_v4.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Windows 콘솔(cp949) 에서도 KST emoji·한글 안전 출력 — stdout UTF-8 강제.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    pass

from src.fetchers.base import Article, Failure
from src.lib.time_helper import KST
from src.lib.url_helper import canonicalize
from src.summarizer.client import CATEGORIES, ItemAnalysis, SummarizeResult
from src.summarizer.render import build_digest


def _kst(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=KST)


def _art(
    url: str,
    title: str,
    sid: str,
    sname: str,
    cat: str,
    pub: datetime,
    snippet: str,
) -> Article:
    return Article(
        canonical_url=canonicalize(url),
        title=title,
        source_id=sid,
        source_name=sname,
        category=cat,
        published_at_kst=pub,
        snippet=snippet,
    )


def build_fixtures() -> tuple[
    dict[str, list[Article]], SummarizeResult, list[Failure],
]:
    """v3 mockup 의 8건 — Anthropic 4.7 / GPT-5 mini / Gemini 3 Pro / GS / aT / 쿠팡 / 청도 / 안동."""
    sent_at = _kst(5, 19, 7, 30)

    # AI 트렌드 3건.
    a_anthropic = _art(
        "https://www.anthropic.com/news/claude-opus-4-7",
        "Claude Opus 4.7, 1M 컨텍스트를 기본으로",
        "anthropic_blog",
        "Anthropic Blog",
        "ai_trend",
        _kst(5, 19, 6, 12),
        "1백만 토큰 컨텍스트를 추가 비용 없이 기본 제공.",
    )
    a_openai = _art(
        "https://openai.com/blog/gpt-5-mini-pricing",
        "OpenAI, GPT-5 mini 토큰 단가 30% 인하",
        "openai_blog",
        "OpenAI Blog",
        "ai_trend",
        _kst(5, 18, 23, 40),
        "GPT-5 mini 입력·출력 토큰 단가를 30% 인하.",
    )
    a_gemini = _art(
        "https://deepmind.google/gemini-3-pro-benchmark",
        "Gemini 3 Pro 멀티모달 벤치마크 공개",
        "deepmind_blog",
        "Google DeepMind",
        "ai_trend",
        _kst(5, 19, 2, 55),
        "Gemini 3 Pro MMMU 84.2점, MathVista 78.5점.",
    )

    # 농산물·유통 3건.
    a_gs = _art(
        "https://www.gsretail.com/news/2026-05-18-fresh-policy",
        "GS리테일, 1차 밴드 산지 직배송 30%→40%로 확대",
        "gsretail_ir",
        "GS리테일 IR",
        "agri_distribution",
        _kst(5, 18, 17, 30),
        "봄철 신선식품 운영 정책 일부를 조정해 산지 직배송 비중을 30%에서 40%로 확대.",
    )
    a_at = _art(
        "https://www.kamis.or.kr/customer/price/weekly/202605-w3.html",
        "5월 셋째 주 시세 — 복숭아 +8.3%, 딸기 −6.1%",
        "at_kamis",
        "aT 유통정보",
        "agri_distribution",
        _kst(5, 19, 5, 10),
        "복숭아 도매 평균가 전주 대비 8.3% 상승, 딸기 6.1% 하락.",
    )
    a_coupang = _art(
        "https://news.coupang.com/2026/05/18/cold-chain-expansion",
        "쿠팡, 신선식품 콜드체인 자체 운영 5개 권역 추가",
        "coupang_news",
        "쿠팡 보도자료",
        "agri_distribution",
        _kst(5, 18, 19, 20),
        "기존 7개 권역에 더해 충북·강원·전남 등 5개 권역에 콜드체인 자체 운영 거점을 추가.",
    )

    # 팜보스 관심 키워드 2건.
    a_cheongdo = _art(
        "https://www.nongmin.com/news/2026/05/19/cheongdo-peach",
        "청도 복숭아, 출하 시기 평년 대비 5일 앞당겨질 전망",
        "nongmin",
        "농민신문",
        "farmboss_keyword",
        _kst(5, 19, 5, 40),
        "청도군 농업기술센터 발표 — 5월 일조량이 평년 대비 14% 많아 복숭아 개화·결실이 빨라졌다.",
    )
    a_andong = _art(
        "https://www.nonghyup.com/andong/news/2026-05",
        "안동농협공판장, 중도매인 정산 주기 5→3영업일 시범 운영",
        "nonghyup_andong",
        "안동농협공판장",
        "farmboss_keyword",
        _kst(5, 19, 3, 25),
        "안동농협공판장이 중도매인 정산 주기를 기존 5영업일에서 3영업일로 단축하는 시범을 5월 한 달간 운영한다.",
    )

    by_category: dict[str, list[Article]] = {
        "ai_trend": [a_anthropic, a_openai, a_gemini],
        "agri_distribution": [a_gs, a_at, a_coupang],
        "farmboss_keyword": [a_cheongdo, a_andong],
    }

    # 점수 분포 — v3 mockup 그대로:
    # ⭐⭐⭐: GS(9), 청도(9) = 2건
    # ⭐⭐: Anthropic(7), aT(6), 안동(7) = 3건
    # ⭐: OpenAI(3), Gemini(3), 쿠팡(4) = 3건
    items: list[ItemAnalysis] = [
        ItemAnalysis(
            article_id=a_anthropic.canonical_url,
            score=7,
            summary=(
                "1백만 토큰 컨텍스트를 추가 비용 없이 기본 제공한다고 발표. 가격은 "
                "기존 Opus 4.6 대비 동일 유지하며 prompt caching 효율은 약 12% 개선."
            ),
            company_impact="본 봇 운영 비용 감소 가능성. 4분기 모델 교체 검토 시 후보.",
        ),
        ItemAnalysis(
            article_id=a_openai.canonical_url,
            score=3,
            summary=(
                "GPT-5 mini의 입력·출력 토큰 단가를 30% 인하한다고 공지. 시행일은 "
                "5월 22일이며 기존 API 호출 패턴은 변경되지 않는다."
            ),
            company_impact="",
        ),
        ItemAnalysis(
            article_id=a_gemini.canonical_url,
            score=3,
            summary=(
                "Gemini 3 Pro가 MMMU 84.2점, MathVista 78.5점을 기록했다고 발표. "
                "비교 기준 모델은 GPT-5o와 Claude Opus 4.6."
            ),
            company_impact="",
        ),
        ItemAnalysis(
            article_id=a_gs.canonical_url,
            score=9,
            summary=(
                "봄철 신선식품 운영 정책 일부를 조정해 산지 직배송 비중을 30%에서 40%로 "
                "확대. 1차 밴드 파트너 납품 기준·일정도 1~2일 단축된다."
            ),
            company_impact=(
                "정다운(j) GS 1차 밴드 파트너로서 납품 일정·계약 조건 재검토 가능성. "
                "장석중 이사 영업 미팅 점검 필요."
            ),
        ),
        ItemAnalysis(
            article_id=a_at.canonical_url,
            score=6,
            summary=(
                "복숭아 도매 평균가 전주 대비 8.3% 상승, 딸기 6.1% 하락. 출하 지역별 "
                "편차 큰 한 주였으며 경북 산지 출하량은 평년 대비 12% 적었다."
            ),
            company_impact=(
                "청도·밀양 산지 수매가 협상에 직접 영향. 팜보스(f) 온라인 가격 책정 참고."
            ),
        ),
        ItemAnalysis(
            article_id=a_coupang.canonical_url,
            score=4,
            summary=(
                "기존 7개 권역에 더해 충북·강원·전남 등 5개 권역에 콜드체인 자체 운영 "
                "거점을 추가. 신선식품 직매입 비중 확대 일환."
            ),
            company_impact=(
                "쿠팡 직매입 확대 = 정다운 입점 채널 협상 카드 변화 가능성. "
                "팜보스(f) 온라인 경쟁 채널 추적."
            ),
        ),
        ItemAnalysis(
            article_id=a_cheongdo.canonical_url,
            score=9,
            summary=(
                "청도군 농업기술센터 발표 — 5월 일조량이 평년 대비 14% 많아 복숭아 "
                "개화·결실이 빨라졌다. 첫 출하는 6월 마지막 주로 예상된다."
            ),
            company_impact=(
                "정다운(j) 청도 산지 수매 일정·물량 사전 조율 필요. 팜보스(f) 온라인 "
                "사전 예약·콘텐츠 캠페인 일정도 당겨야 함."
            ),
        ),
        ItemAnalysis(
            article_id=a_andong.canonical_url,
            score=7,
            summary=(
                "안동농협공판장이 중도매인 정산 주기를 기존 5영업일에서 3영업일로 "
                "단축하는 시범을 5월 한 달간 운영한다. 전산 시스템 갱신 후 7월 본격 도입 검토."
            ),
            company_impact="시경(s) 안동공판장 중도매 현금 흐름 개선. 7월 본격 도입 일정 추적.",
        ),
    ]

    category_headlines = {
        "ai_trend": "오늘은 주요 LLM 3사 업데이트가 동시에 — Anthropic·OpenAI·Google.",
        "agri_distribution": (
            "GS리테일·쿠팡 두 곳이 산지·콜드체인을 확장. 정다운 납품·물류와 직간접 연결."
        ),
        "farmboss_keyword": "청도·안동농협 직결 뉴스 2건. 둘 다 운영 일정에 영향.",
    }

    summarize_result = SummarizeResult(
        items=items,
        category_headlines=category_headlines,
        dropped_items=0,
        tokens_in=6800,
        tokens_out=1450,
    )

    # 실패 소스 1개 (v3 mockup hero 의 '한국농어민신문 일시 장애' 라인 재현).
    failures: list[Failure] = [
        Failure(
            source_id="agrinet",
            source_name="한국농어민신문",
            error_kind="timeout",
            error_message="connect timeout",
        ),
    ]

    return by_category, summarize_result, failures


def main() -> None:
    by_category, summarize_result, failures = build_fixtures()
    sent_at = datetime(2026, 5, 19, 7, 30, tzinfo=KST)

    digest = build_digest(
        by_category=by_category,
        summarize_result=summarize_result,
        fetch_failures=failures,
        sent_at_kst=sent_at,
        sources_total=12,
        pages_url_template="https://farmboss-trend.github.io/digest/2026-05-19/",
    )

    out_path = Path(__file__).resolve().parent.parent / "samples" / "2026-05-19-digest-preview-v4-from-render.html"
    out_path.write_text(digest.html, encoding="utf-8")

    print(f"[OK] HTML saved to: {out_path}")
    print(f"     item_count={digest.item_count} tldr_count={len(digest.tldr_items)}")
    print()
    print("=== subject ===")
    print(digest.subject)
    print()
    print("=== telegram_text ===")
    print(digest.telegram_text)


if __name__ == "__main__":
    main()
