"""URL 정규화 helper — dedup·발송·history 가 공유하는 단일 진실(AC-4.1)."""

from __future__ import annotations

from urllib.parse import (
    ParseResult,
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)

# 추적 파라미터: utm_* 접두는 별도 처리, 그 외 고정 키는 아래 집합.
# 키 비교는 case-insensitive (소문자로 비교).
_TRACKING_PARAM_KEYS: frozenset[str] = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}
)


def _is_tracking_param(key: str) -> bool:
    """추적 파라미터 여부 판정 (대소문자 무관)."""
    k = key.lower()
    if k.startswith("utm_"):
        return True
    return k in _TRACKING_PARAM_KEYS


def canonicalize(url: str) -> str:
    """URL 을 dedup·발송 공유용 canonical 형태로 정규화한다.

    적용 단계 (AC-4.1):
        1. URL 파싱 (urllib.parse.urlparse).
        2. host lowercase.
        3. 쿼리스트링에서 추적 파라미터 제거 — `utm_*` 접두 또는 `fbclid`/`gclid`/`mc_cid`/`mc_eid`/`ref` (대소문자 무관). 나머지 쿼리는 보존.
        4. fragment(`#...`) 제거.
        5. trailing slash 제거 (경로가 `/` 단독이면 보존).

    잘못된 URL(scheme 또는 netloc 누락)은 `ValueError` 를 발생시킨다.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")

    try:
        parsed: ParseResult = urlparse(url.strip())
    except Exception as e:  # pragma: no cover — urlparse 는 거의 예외를 안 던짐
        raise ValueError(f"invalid url: {url!r}") from e

    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"invalid url (scheme/netloc missing): {url!r}")

    # (2) host lowercase — userinfo·port 는 그대로 두고 host 부분만 lower.
    # netloc 는 `[user[:pass]@]host[:port]` 형식. split 으로 안전하게 분리.
    netloc = parsed.netloc
    userinfo = ""
    hostport = netloc
    if "@" in netloc:
        userinfo, hostport = netloc.rsplit("@", 1)
        userinfo = userinfo + "@"
    if ":" in hostport:
        host, port = hostport.rsplit(":", 1)
        hostport_lower = host.lower() + ":" + port
    else:
        hostport_lower = hostport.lower()
    netloc_lower = userinfo + hostport_lower

    # (3) 쿼리스트링에서 추적 파라미터 제거. parse_qsl 은 순서·중복 보존.
    kept_pairs: list[tuple[str, str]] = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_param(k)
    ]
    new_query = urlencode(kept_pairs, doseq=True)

    # (5) trailing slash 제거 (단, path 가 정확히 "/" 또는 빈 문자열이면 보존).
    path = parsed.path
    if path not in ("", "/") and path.endswith("/"):
        path = path.rstrip("/")

    # (4) fragment 제거 — 빈 문자열로.
    canonical = urlunparse(
        (
            parsed.scheme.lower(),
            netloc_lower,
            path,
            parsed.params,
            new_query,
            "",
        )
    )
    return canonical
