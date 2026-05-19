"""fetcher 도메인의 단일 진실 — `Article` / `Failure` dataclass + `Fetcher` Protocol.

CRITICAL #2 (표시 로직과 실제 규칙이 같은 helper 공유) 를 코드 측에서 강제하는 지점.

- `Article.canonical_url` 은 반드시 `lib/url_helper.canonicalize` 통과 결과여야 한다.
  `__post_init__` 에서 재호출해 입력 == canonicalize(입력) 이 아니면 `ValueError` raise.
  → dedup / 발송 / history 가 같은 정규화 helper 를 공유하도록 강제 (anti-pattern A 방지).
- `Article.published_at_kst` 는 항상 tz-aware datetime (Asia/Seoul 으로 변환 가능한 형태).
  naive datetime 은 생성 시점에 거부 — fetcher 가 KST 임의 추정으로 흘려보내는 길을 차단.

`Failure.error_kind` 는 runner 가 부여하는 짧은 분류 라벨. 발송 본문·운영자 alert 가
같은 문자열을 그대로 사용한다 (AC-5.2 "X개 실패: {이름}" 표기 helper 가 본 dataclass 사용).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from src.config.loader import Source
from src.lib.url_helper import canonicalize

# Failure.error_kind 5종 — step3.md AC + runner.run_all 분류 룰의 단일 진실.
ErrorKind = Literal["timeout", "http_4xx", "http_5xx", "parse_error", "other"]


@dataclass(frozen=True)
class Article:
    """fetcher 가 반환하는 단일 기사 — in-memory only.

    Attributes:
        canonical_url: `lib/url_helper.canonicalize` 통과 결과만 허용. 생성 시 재검증.
        title: 기사 제목 (raw, 정규화 안 함 — render·filter 가 별도 처리).
        source_id: `Source.id` 그대로 (history sent.jsonl 의 source_id 와 연결).
        source_name: `Source.name` 그대로 (본문 출처 표기에 사용).
        category: ai_trend | agri_distribution | farmboss_keyword (Source.category).
        published_at_kst: tz-aware datetime (Asia/Seoul). naive 거부.
        snippet: 본문 일부 (요약 LLM 입력·미리보기용). 최대 ~500자 가이드라인.
    """

    canonical_url: str
    title: str
    source_id: str
    source_name: str
    category: str
    published_at_kst: datetime
    snippet: str

    def __post_init__(self) -> None:
        # canonical_url 강제 — anti-pattern A 코드 측 방어선.
        if not isinstance(self.canonical_url, str) or not self.canonical_url.strip():
            raise ValueError("Article.canonical_url 은 비어있지 않은 문자열이어야 합니다.")
        try:
            normalized = canonicalize(self.canonical_url)
        except ValueError as e:
            raise ValueError(
                f"Article.canonical_url 이 url_helper.canonicalize 통과 형식이 아닙니다: "
                f"{self.canonical_url!r} ({e})"
            ) from e
        if normalized != self.canonical_url:
            raise ValueError(
                f"Article.canonical_url 은 lib.url_helper.canonicalize 결과여야 합니다. "
                f"입력={self.canonical_url!r}, 기대={normalized!r}"
            )

        # published_at_kst tz-aware 강제 — CRITICAL #7.
        if not isinstance(self.published_at_kst, datetime):
            raise ValueError(
                "Article.published_at_kst 는 datetime 인스턴스이어야 합니다."
            )
        if self.published_at_kst.tzinfo is None:
            raise ValueError(
                "Article.published_at_kst 는 tz-aware 이어야 합니다 (naive datetime 금지)."
            )


@dataclass(frozen=True)
class Failure:
    """소스 단위 fetch 실패 — runner 가 격리 처리 후 모아 반환.

    Attributes:
        source_id: `Source.id` (사용자 화면 표기는 source_name 우선이나 추적 키는 id).
        source_name: `Source.name` (AC-5.2 본문/Pages 헤더 노출 텍스트).
        error_kind: 5종 분류 라벨 — runner.run_all 가 부여.
        error_message: 짧은 한 줄 (스택트레이스 금지 — 시크릿/내부정보 유출 방지).
    """

    source_id: str
    source_name: str
    error_kind: ErrorKind
    error_message: str


class Fetcher(Protocol):
    """소스 type 별 어댑터 인터페이스.

    구현체는 네트워크 오류·파싱 오류를 그대로 raise 한다 (runner 가 격리·분류).
    어댑터 내부에서 dedup·필터·요약 등 다른 모듈 로직을 호출하면 안 된다 (step3.md 금지사항).
    """

    def fetch(self, source: Source) -> list[Article]:  # pragma: no cover — Protocol 시그니처
        ...
