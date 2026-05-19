"""`history/sent.jsonl` 한 줄 1 record 의 schema — requirements §6-4 (version: 1 동결).

스키마 변경 시:
1. `SentRecord.SCHEMA_VERSION` bump 가 아니라 새 version 번호로 신규 dataclass 추가 + 마이그레이션
   함수 추가 (점진 확장 원칙).
2. 본 모듈은 version 1 을 영구히 인식한다 — 알 수 없는 version 은 WARNING + None 반환
   (raise 금지 — 폭주 방지, requirements §6-4 정책).

직렬화 형태(`to_dict` / `from_dict`) 는 JSON 친화 — datetime 은 모두 ISO 문자열로 저장.
이 형식은 sent.jsonl 한 줄에 그대로 dump 가능.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# version 동결 — 변경은 새 record dataclass 추가로만 (마이그레이션 필요).
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SentItem:
    """sent.jsonl record 의 items[] 한 건 — requirements §6-4.

    Attributes:
        canonical_url: `lib/url_helper.canonicalize` 통과 결과.
        title: 기사 제목 raw (fuzzy match 용).
        source_id: `Source.id` 그대로 (소스 폐기 후에도 id 유지).
        category: `ai_trend | agri_distribution | farmboss_keyword`.
        published_at_kst: ISO 8601 문자열 (직렬화 안정성을 위해 datetime 이 아닌 str).
    """

    canonical_url: str
    title: str
    source_id: str
    category: str
    published_at_kst: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_url": self.canonical_url,
            "title": self.title,
            "source_id": self.source_id,
            "category": self.category,
            "published_at_kst": self.published_at_kst,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SentItem":
        return cls(
            canonical_url=str(d["canonical_url"]),
            title=str(d["title"]),
            source_id=str(d["source_id"]),
            category=str(d["category"]),
            published_at_kst=str(d["published_at_kst"]),
        )


@dataclass(frozen=True)
class SentRecord:
    """sent.jsonl 한 줄 1 record — requirements §6-4 동결.

    Attributes:
        version: 항상 1 (`SCHEMA_VERSION` 강제).
        sent_at_utc: 발송 UTC ISO 문자열 (예: `2026-05-19T22:30:14+00:00`).
        sent_at_kst: 발송 KST ISO 문자열 (예: `2026-05-20T07:30:14+09:00`).
        items: 발송된 기사 목록 (dedup 입력 단위).
        meta: 자유 dict — `failed_sources`, `claude_tokens_in/out`, 운영 메타.
    """

    version: int
    sent_at_utc: str
    sent_at_kst: str
    items: list[SentItem]
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 친화 dict — sent.jsonl 한 줄로 그대로 dump 가능.

        version 은 출력 시점에 `SCHEMA_VERSION` 으로 강제 (입력 인스턴스의 version 은 무시).
        """
        return {
            "version": SCHEMA_VERSION,
            "sent_at_utc": self.sent_at_utc,
            "sent_at_kst": self.sent_at_kst,
            "items": [it.to_dict() for it in self.items],
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SentRecord | None":
        """dict → SentRecord. version 검증 실패 시 None + WARNING (raise 금지).

        Returns:
            SentRecord — version == SCHEMA_VERSION 일 때.
            None — version 이 인식되지 않을 때 (WARNING 로그 1줄).
        """
        if not isinstance(d, dict):
            logger.warning(
                "SentRecord.from_dict — input is not a dict (got %s); skip.",
                type(d).__name__,
            )
            return None

        version = d.get("version")
        if version != SCHEMA_VERSION:
            logger.warning(
                "SentRecord.from_dict — unknown version=%r (expected %d); skip.",
                version, SCHEMA_VERSION,
            )
            return None

        try:
            raw_items = d.get("items") or []
            items = [SentItem.from_dict(it) for it in raw_items]
            meta = d.get("meta") or {}
            return cls(
                version=SCHEMA_VERSION,
                sent_at_utc=str(d["sent_at_utc"]),
                sent_at_kst=str(d["sent_at_kst"]),
                items=items,
                meta=dict(meta) if isinstance(meta, dict) else {},
            )
        except (KeyError, TypeError, ValueError) as e:
            logger.warning(
                "SentRecord.from_dict — malformed record, skip: %s", e,
            )
            return None
