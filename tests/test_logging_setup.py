"""`lib/logging_setup` 단위 테스트 — AC-7.2 시크릿 마스킹 + 멱등 setup 4건 이상."""

from __future__ import annotations

import logging

from src.lib.logging_setup import mask_key, setup_logging


def test_mask_key_long_secret_shows_only_prefix_and_ellipsis() -> None:
    """6자 이상 시크릿은 앞 6자 + `...` 형식으로만 노출된다."""
    assert mask_key("sk-ant-abc123def456") == "sk-ant..."


def test_mask_key_short_input_returns_triple_asterisk() -> None:
    """5자 이하 입력은 prefix 노출 시 키 절반 이상이 새므로 `***` 로 마스킹한다."""
    assert mask_key("abcde") == "***"
    assert mask_key("a") == "***"


def test_mask_key_none_and_empty_return_empty_string() -> None:
    """`None` 과 빈 문자열은 로그에서 자연스럽게 생략되도록 빈 문자열을 반환한다."""
    assert mask_key("") == ""
    assert mask_key(None) == ""


def test_setup_logging_is_idempotent_on_repeated_calls() -> None:
    """`setup_logging` 을 두 번 호출해도 root logger handler 개수가 늘지 않아야 한다."""
    root = logging.getLogger()
    # 다른 테스트의 영향 차단 — 기존 root handler 수를 기준선으로 잡는다.
    before = len(root.handlers)

    setup_logging("INFO")
    after_first = len(root.handlers)

    setup_logging("DEBUG")
    after_second = len(root.handlers)

    # 첫 호출에서 우리 handler 1개 추가됐을 수 있고, 두 번째 호출은 절대 추가되지 않아야 한다.
    assert after_second == after_first
    # 첫 호출은 base 대비 0~1 개 증가 (이미 누가 호출했으면 0, 처음이면 1).
    assert after_first - before in (0, 1)
