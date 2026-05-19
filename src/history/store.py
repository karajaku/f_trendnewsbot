"""history backend — 발송 이력 로드/append 의 단일 진실 (CRITICAL #8).

`HistoryBackend` Protocol 은 `load(dedup_days) -> History` / `record(SentRecord) -> None` 두
함수만 노출한다. V1 운영은 GitHub Actions artifact 가 `sent.jsonl` 을 옮기지만(step7
workflow), 코드 측 backend 인터페이스는 동일 — local file path 에 read/append 한다.

`History` 는 dedup 입력의 단일 진실:
- `canonical_urls: frozenset[str]` — URL 1차 비교용.
- `titles: tuple[str, ...]` — 제목 fuzzy match (difflib.SequenceMatcher) 용. 입력 순서 보존.

CRITICAL #2 (helper 공유): canonical_url 은 SentItem 단계에서 이미 canonicalize 통과 가정
(Article 생성 시 강제 + dispatcher 가 record 시 그대로 전달). 본 모듈은 정규화 0줄.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Protocol

from src.lib.time_helper import now_kst, parse_to_kst

from .schema import SCHEMA_VERSION, SentRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class History:
    """dedup 입력 형태 — 발송 이력 N일 분.

    Attributes:
        canonical_urls: 발송된 canonical_url 의 frozenset (1차 dedup 비교).
        titles: 발송된 제목 tuple — fuzzy match 2차 검사용.
    """

    canonical_urls: frozenset[str]
    titles: tuple[str, ...]

    @classmethod
    def empty(cls) -> "History":
        return cls(canonical_urls=frozenset(), titles=())


class HistoryBackend(Protocol):
    """history backend 인터페이스 — V1 은 `LocalFileBackend` 1종."""

    def load(self, dedup_days: int) -> History:  # pragma: no cover — Protocol
        ...

    def record(self, record: SentRecord) -> None:  # pragma: no cover — Protocol
        ...


class LocalFileBackend:
    """`{root}/history/sent.jsonl` 에 한 줄 1 SentRecord 로 append 하는 로컬 backend.

    Args:
        root: 리포 루트 디렉토리. `history/sent.jsonl` 이 그 아래로 매핑.

    Notes:
        - V1 운영은 step7 workflow 가 actions/{download,upload}-artifact 로 같은 파일을
          이동시킨다 — 본 backend 는 그 파일을 read/append 하는 같은 진실을 공유.
        - 파일 없으면 빈 History + WARNING "fresh-start" (첫 실행 부팅).
    """

    def __init__(self, root: Path) -> None:
        self._root = Path(root)
        self._path = self._root / "history" / "sent.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def load(self, dedup_days: int) -> History:
        """`sent.jsonl` 을 읽어 최근 `dedup_days` 일 안의 record 만 `History` 로 구성.

        Args:
            dedup_days: 발송 KST 기준 최근 N일 (양의 정수).

        Returns:
            `History` — canonical_urls / titles. 파일 없거나 모든 record 가 만료된
            경우 빈 History.

        실패 처리:
            - 파일 없음 → 빈 History + WARNING "fresh-start" 1회.
            - JSON 파싱 실패 한 줄 → 그 줄만 skip + WARNING.
            - 알 수 없는 version → schema.from_dict 가 None + WARNING (raise 금지).
            - sent_at_kst 가 (now - dedup_days) 이전 → 무시.
        """
        if not isinstance(dedup_days, int) or dedup_days <= 0:
            raise ValueError(f"dedup_days must be a positive int, got {dedup_days!r}")

        if not self._path.exists():
            logger.warning(
                "history fresh-start — sent.jsonl not found at %s; starting with empty history.",
                self._path,
            )
            return History.empty()

        cutoff = now_kst() - timedelta(days=dedup_days)

        canonical_urls: list[str] = []
        titles: list[str] = []

        try:
            with self._path.open("r", encoding="utf-8") as fh:
                for lineno, raw_line in enumerate(fh, start=1):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "history load — malformed JSON line skipped: file=%s line=%d err=%s",
                            self._path, lineno, e,
                        )
                        continue

                    record = SentRecord.from_dict(d)
                    if record is None:
                        # schema.from_dict 가 이미 WARNING 출력.
                        continue

                    # 윈도우 검사 — sent_at_kst 가 cutoff 이전이면 skip.
                    try:
                        sent_dt = parse_to_kst(record.sent_at_kst)
                    except ValueError as e:
                        logger.warning(
                            "history load — invalid sent_at_kst, record skipped: file=%s line=%d err=%s",
                            self._path, lineno, e,
                        )
                        continue
                    if sent_dt < cutoff:
                        continue

                    for it in record.items:
                        canonical_urls.append(it.canonical_url)
                        titles.append(it.title)
        except OSError as e:
            # 파일은 있는데 read 못 함 — 운영자 가시성을 위해 WARNING + 빈 History.
            logger.warning(
                "history load — OSError reading %s: %s; starting with empty history.",
                self._path, e,
            )
            return History.empty()

        return History(
            canonical_urls=frozenset(canonical_urls),
            titles=tuple(titles),
        )

    def record(self, record: SentRecord) -> None:
        """`sent.jsonl` 에 한 줄 append. 디렉토리 자동 생성.

        Args:
            record: `SentRecord` (version 은 dump 시 SCHEMA_VERSION 으로 강제).

        Notes:
            - JSON 직렬화는 `ensure_ascii=False` — 한국어 제목 그대로 저장.
            - flush 후 파일 핸들 닫음 (artifact upload 직전 OS 버퍼 비움).
        """
        # 버전 강제 — to_dict() 가 SCHEMA_VERSION 으로 덮어쓴다.
        payload = record.to_dict()
        if payload["version"] != SCHEMA_VERSION:
            # to_dict 가 SCHEMA_VERSION 강제이므로 도달 불가 — 방어선.
            raise RuntimeError(
                f"SentRecord version mismatch (got {payload['version']}, expected {SCHEMA_VERSION})"
            )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
        logger.debug(
            "history record append — path=%s items=%d", self._path, len(record.items),
        )
