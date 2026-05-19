"""필터 인터페이스 — `Filter` Protocol.

각 필터(`timewindow`, `keyword`, `category`, `dedup`) 는 본 Protocol 의 시그니처를
부분적으로 구현한다 (인자 형태가 필터별로 다르므로 형식 강제는 약함). 본 Protocol 은
파이프라인에서 함수 객체로 다룰 때의 가독성용 단일 진실이다.
"""

from __future__ import annotations

from typing import Protocol

from src.fetchers.base import Article


class Filter(Protocol):
    """모든 필터 함수의 공통 형태.

    `apply(articles, **kwargs) -> list[Article]` — 입력 list 를 받아 통과된 항목만 반환.
    입력 순서는 보존한다 (dedup 의 "먼저 등장한 1건 통과" 규칙 등).
    """

    def apply(self, articles: list[Article]) -> list[Article]:  # pragma: no cover — Protocol 시그니처
        ...
