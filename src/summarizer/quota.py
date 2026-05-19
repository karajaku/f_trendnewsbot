"""LLM API 일일 quota hard cap — CRITICAL #9 + AC-5.5 단일 진실.

ADR-004 (2026-05-19): Gemini 2.0 Flash 로 swap 후에도 hard cap 정책은 LLM provider 와
무관하게 동일 (input/output token 누적 + 호출 횟수). Gemini 무료 tier (1500 RPD) 보다
훨씬 보수적인 운영 cap.

cron 1회 실행 단위 in-memory 누적이 V1 정책 (process 1회 = day 1회). cap 초과 시
`QuotaExceededError` 즉시 raise — `run_daily.py` 가 catch 해 운영자 텔레그램 alert 발송
후 종료(AC-5.3). 상수는 본 모듈에 박힌 단일 진실 — 운영자가 코드 수정으로만 조정
(env var override 금지, requirements §6 운영 정책).
"""

from __future__ import annotations

from typing import TypedDict

# Hard cap 상수 — AC-5.5. env override 금지(운영자 수동 조정만, code review 필수).
HARD_CAP_INPUT_TOKENS: int = 100_000
HARD_CAP_OUTPUT_TOKENS: int = 20_000
HARD_CAP_CALLS: int = 30


class QuotaState(TypedDict):
    """`QuotaTracker.state` 의 반환 형태 — 로그·운영자 alert 표기에 사용."""

    tokens_in: int
    tokens_out: int
    calls: int
    cap_tokens_in: int
    cap_tokens_out: int
    cap_calls: int


class QuotaExceededError(RuntimeError):
    """일일 quota cap 초과 — `run_daily.main()` 이 catch 후 운영자 alert 발송 (AC-5.3)."""


class QuotaTracker:
    """일일 토큰·호출 누적기 — `client.summarize` 가 호출당 1회 `check_and_record` 호출.

    동작:
        1. 호출 직전 `check_and_record(tokens_in, tokens_out)` 호출.
        2. (누적 + 신규)가 cap 초과면 `QuotaExceededError` raise (누적은 갱신되지 않음).
        3. cap 내면 누적값 갱신 + `calls += 1`.

    교차 검증을 위해 `state` 프로퍼티로 현재 누적을 노출 — 로그·alert 본문에 사용.
    """

    def __init__(
        self,
        *,
        cap_tokens_in: int = HARD_CAP_INPUT_TOKENS,
        cap_tokens_out: int = HARD_CAP_OUTPUT_TOKENS,
        cap_calls: int = HARD_CAP_CALLS,
    ) -> None:
        if cap_tokens_in <= 0 or cap_tokens_out <= 0 or cap_calls <= 0:
            raise ValueError("quota cap 은 모두 양의 정수여야 합니다.")
        self._cap_tokens_in = cap_tokens_in
        self._cap_tokens_out = cap_tokens_out
        self._cap_calls = cap_calls
        self._tokens_in = 0
        self._tokens_out = 0
        self._calls = 0

    def check_and_record(self, tokens_in: int, tokens_out: int) -> None:
        """호출 1건의 토큰 누적을 검증·기록. cap 초과 시 raise + 누적 미반영."""
        if (
            not isinstance(tokens_in, int)
            or not isinstance(tokens_out, int)
            or isinstance(tokens_in, bool)
            or isinstance(tokens_out, bool)
        ):
            raise ValueError("tokens_in/out 은 int 이어야 합니다.")
        if tokens_in < 0 or tokens_out < 0:
            raise ValueError("tokens_in/out 은 음수일 수 없습니다.")

        # 호출 횟수 cap 우선 — 호출 자체가 너무 많은 폭주를 가장 먼저 차단.
        if self._calls + 1 > self._cap_calls:
            raise QuotaExceededError(
                f"daily API calls cap 초과: 누적 {self._calls}회 + 신규 1회 > cap {self._cap_calls}회"
            )
        if self._tokens_in + tokens_in > self._cap_tokens_in:
            raise QuotaExceededError(
                f"daily input tokens cap 초과: 누적 {self._tokens_in} + 신규 {tokens_in} > cap {self._cap_tokens_in}"
            )
        if self._tokens_out + tokens_out > self._cap_tokens_out:
            raise QuotaExceededError(
                f"daily output tokens cap 초과: 누적 {self._tokens_out} + 신규 {tokens_out} > cap {self._cap_tokens_out}"
            )

        # 모든 cap 통과 — 누적 반영.
        self._tokens_in += tokens_in
        self._tokens_out += tokens_out
        self._calls += 1

    @property
    def state(self) -> QuotaState:
        """현재 누적값·cap 을 dict 로 반환 — 로그·운영자 alert 본문용."""
        return QuotaState(
            tokens_in=self._tokens_in,
            tokens_out=self._tokens_out,
            calls=self._calls,
            cap_tokens_in=self._cap_tokens_in,
            cap_tokens_out=self._cap_tokens_out,
            cap_calls=self._cap_calls,
        )
