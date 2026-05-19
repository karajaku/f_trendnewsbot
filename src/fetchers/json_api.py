"""JSON API 어댑터 — V1 stub.

V1 stub 사유:
    AC-5.1·5.2 는 어댑터 인터페이스·클래스 존재만 요구한다. 일반 JSON API 응답 매핑은
    소스마다 필드 키가 달라 V1 범위에서 의미가 없다. step3.md 산출물 명세에 따라
    클래스·시그니처는 만들어 두고 `fetch()` 호출 시 `NotImplementedError` 를 명확히
    raise 한다 — runner 가 `parse_error` Failure 로 변환해 다른 소스 fetch 를 막지 않는다.

V2 확장 방향 (당장 구현 금지):
    - Source 의 추가 필드(json_paths 등)로 list/title/url/published JSON 경로 매핑.
    - `requests.get(source.url, timeout=10, headers={"Accept": "application/json"})`.
    - `resp.json()` 응답에서 매핑된 경로로 entry list 추출 → Article 생성.
"""

from __future__ import annotations

import logging

from src.config.loader import Source

from .base import Article

logger = logging.getLogger(__name__)


class JsonApiFetcher:
    """JSON API 어댑터 (`Source.type == "json_api"`) — V1 stub.

    V1 에서는 호출 시 `NotImplementedError` 를 raise 한다. runner 가 이를 잡아
    `error_kind="parse_error"` Failure 로 변환한다. V2 에서 source-specific JSON 매핑
    도입 시 본 클래스를 확장한다 (시그니처 변경 없이 내부만 채움).
    """

    def fetch(self, source: Source) -> list[Article]:
        """V1 stub — 호출되면 NotImplementedError. runner 가 parse_error 로 잡음."""
        logger.debug(
            "json_api fetcher is a V1 stub — source_id=%s", source.id
        )
        raise NotImplementedError(
            f"JsonApiFetcher 는 V1 stub 입니다 (source_id={source.id!r}). "
            "V2 에서 source-specific JSON 매핑 도입 예정."
        )
