"""뉴스 소스 fetcher 패키지 — RSS·HTML·JSON_API 어댑터 + 소스 단위 격리 runner.

CRITICAL #4 (외부 소스 장애 격리)·anti-pattern C (단일 try/except 금지) 의 코드 측 정착.
공개 표면 정의:

- `Article` / `Failure` — runner 결과 dataclass (in-memory only, sent.jsonl 변환은 step4).
- `Fetcher` — 어댑터 Protocol (`fetch(source) -> list[Article]`).
- `RssFetcher` / `HtmlFetcher` / `JsonApiFetcher` — Source.type 별 어댑터.
- `run_all(sources)` — 소스 단위 격리 runner, `(list[Article], list[Failure])` 반환.

V1 에서 `HtmlFetcher`·`JsonApiFetcher` 는 source-specific selector/매핑이 확정되기
전까지 stub 상태 (`NotImplementedError`). runner 가 `parse_error` Failure 로 변환한다.
"""

from __future__ import annotations

from .base import Article, Failure, Fetcher
from .html import HtmlFetcher
from .json_api import JsonApiFetcher
from .rss import RssFetcher
from .runner import run_all

__all__ = [
    "Article",
    "Failure",
    "Fetcher",
    "RssFetcher",
    "HtmlFetcher",
    "JsonApiFetcher",
    "run_all",
]
