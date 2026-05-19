"""소스 단위 격리 runner — anti-pattern C (단일 try/except 전체 감싸기) 의 코드 측 대응.

`run_all(sources)` 는 다음을 보장한다:

1. 한 소스 fetch 예외가 다른 소스 fetch 를 막지 않는다 (AC-5.1, CRITICAL #4).
2. 예외 종류를 `Failure.error_kind` 5종 분류로 변환한다 (AC-5.2 표기 helper 와 단일 진실).
3. `source.enabled is False` 인 소스는 skip — Failure 도 만들지 않는다.
4. timeout 10초·retry 1회 — 동일한 소스에 한해 최대 2회 시도, 두 번째 실패 시 Failure 1건.

dispatcher / render 가 "소스 N개 중 M개 정상 수집, X개 실패: {이름}" 표기 시 본 runner 의
반환값을 그대로 사용한다. error_kind 라벨은 발송 본문·운영자 alert 가 공유하는 단일 문자열.
"""

from __future__ import annotations

import logging
import socket
from typing import Callable

import requests

from src.config.loader import Source

from .base import Article, ErrorKind, Failure, Fetcher
from .html import HtmlFetcher
from .json_api import JsonApiFetcher
from .rss import RssFetcher

logger = logging.getLogger(__name__)

# 소스 단위 timeout (초) + retry 횟수 (최초 시도 외 추가 시도 횟수).
_FETCH_TIMEOUT_SECONDS = 10.0
_FETCH_RETRY_ATTEMPTS = 1


def _select_fetcher(source: Source) -> Fetcher:
    """`Source.type` 에 따라 어댑터 인스턴스를 반환한다.

    enum 은 config.loader 에서 이미 검증되었으므로 알 수 없는 type 은 방어적 fallback.
    """
    if source.type == "rss":
        return RssFetcher()
    if source.type == "html":
        return HtmlFetcher()
    if source.type == "json_api":
        return JsonApiFetcher()
    # config.loader 가 enum 검증을 통과시켰는데 여기까지 오면 데이터 계약 버그.
    raise ValueError(
        f"unknown Source.type={source.type!r} for source_id={source.id!r}"
    )


def _classify_exception(exc: BaseException) -> tuple[ErrorKind, str]:
    """예외 → (error_kind, error_message) 5종 분류.

    error_message 는 스택트레이스 금지 (CRITICAL #5 시크릿 노출 방지) — 한 줄 요약만.
    """
    # 1) timeout — requests.Timeout 은 ConnectionError 의 하위가 아니므로 먼저 검사.
    if isinstance(exc, requests.exceptions.Timeout) or isinstance(exc, socket.timeout):
        return "timeout", f"timeout: {type(exc).__name__}"

    # 2) HTTPError — status code 기준 4xx/5xx 분기.
    if isinstance(exc, requests.exceptions.HTTPError):
        status = None
        resp = getattr(exc, "response", None)
        if resp is not None:
            status = getattr(resp, "status_code", None)
        if isinstance(status, int):
            if 400 <= status < 500:
                return "http_4xx", f"http {status}"
            if 500 <= status < 600:
                return "http_5xx", f"http {status}"
        return "other", f"http error (no status): {type(exc).__name__}"

    # 3) NotImplementedError — V1 stub 어댑터.
    if isinstance(exc, NotImplementedError):
        return "parse_error", "fetcher is a V1 stub (NotImplementedError)"

    # 4) ValueError — RssFetcher 가 feed 자체 parse 실패 시 raise.
    if isinstance(exc, ValueError):
        # 한 줄 요약만 — 시크릿/내부 정보 유출 회피.
        return "parse_error", f"parse error: {str(exc)[:200]}"

    # 5) 그 외 — requests.ConnectionError·socket.gaierror 등.
    return "other", f"{type(exc).__name__}: {str(exc)[:200]}"


def _fetch_one(source: Source, fetcher: Fetcher) -> list[Article]:
    """단일 소스를 retry 포함해서 시도. 최종 실패 시 마지막 예외를 그대로 raise.

    socket 기본 timeout 을 일시적으로 설정해 feedparser 등 timeout 옵션을 받지 않는
    경로에도 적용. requests 기반 어댑터는 자체 `timeout=10` 인자를 쓸 것 (V2 어댑터 가이드).
    """
    original_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_FETCH_TIMEOUT_SECONDS)
    try:
        last_exc: BaseException | None = None
        for attempt in range(_FETCH_RETRY_ATTEMPTS + 1):
            try:
                return fetcher.fetch(source)
            except Exception as e:
                last_exc = e
                if attempt < _FETCH_RETRY_ATTEMPTS:
                    logger.debug(
                        "fetch retry — source_id=%s attempt=%d err=%s",
                        source.id, attempt + 1, type(e).__name__,
                    )
                    continue
                raise
        # 도달 불가 — 위 루프가 return 또는 raise 로 끝남.
        assert last_exc is not None  # pragma: no cover
        raise last_exc  # pragma: no cover
    finally:
        socket.setdefaulttimeout(original_timeout)


def run_all(
    sources: list[Source],
    *,
    fetcher_factory: Callable[[Source], Fetcher] | None = None,
) -> tuple[list[Article], list[Failure]]:
    """모든 소스를 **순차로** fetch. 소스 단위 try/except 격리.

    Args:
        sources: load_sources 결과.
        fetcher_factory: 테스트용 fetcher 주입 hook. 미지정 시 `_select_fetcher`.

    Returns:
        (articles, failures): 정상 수집된 Article 합본 + 실패 Failure 합본.
        AC-5.2 본문/Pages 헤더 표기는 본 반환값을 그대로 입력으로 받는다.

    Notes:
        - `source.enabled is False` 인 소스는 fetch 시도조차 안 함 + Failure 도 안 만듦.
        - 동시 fetch (ThreadPoolExecutor 등) 도입 금지 (step3.md 금지사항, V1 순차).
    """
    factory = fetcher_factory or _select_fetcher

    articles: list[Article] = []
    failures: list[Failure] = []

    for source in sources:
        if source.enabled is False:
            logger.debug(
                "skip disabled source — source_id=%s name=%r", source.id, source.name
            )
            continue

        try:
            fetcher = factory(source)
        except Exception as e:
            # type 분기 자체 실패 — config.loader 가 enum 검증을 했으므로 드문 경로.
            kind, msg = _classify_exception(e)
            failures.append(
                Failure(
                    source_id=source.id,
                    source_name=source.name,
                    error_kind=kind,
                    error_message=msg,
                )
            )
            logger.info(
                "fetch failed (factory) — source_id=%s kind=%s msg=%s",
                source.id, kind, msg,
            )
            continue

        # 소스 단위 try/except — anti-pattern C 회피의 핵심 지점.
        try:
            results = _fetch_one(source, fetcher)
        except Exception as e:
            kind, msg = _classify_exception(e)
            failures.append(
                Failure(
                    source_id=source.id,
                    source_name=source.name,
                    error_kind=kind,
                    error_message=msg,
                )
            )
            logger.info(
                "fetch failed — source_id=%s kind=%s msg=%s",
                source.id, kind, msg,
            )
            continue

        articles.extend(results)
        logger.debug(
            "fetch ok — source_id=%s articles=%d", source.id, len(results)
        )

    return articles, failures
