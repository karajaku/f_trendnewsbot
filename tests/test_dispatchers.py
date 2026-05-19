"""dispatcher 단위 테스트 — Pages publish + 텔레그램 send + 운영자 alert.

step6 AC 매핑:
- AC-2.3-A: parse_mode=HTML, disable_web_page_preview=True
- AC-2.8: HTML head <meta name="robots"> — render 책임이므로 본 테스트에선 publish가
  digest.html 을 후처리하지 않음만 확인 (디스크 write 결과 == digest.html 원본)
- AC-5.4: retry 1회 + ops_alert 무한루프 방지 (재시도 0회, stderr 만)
- AC-5.6: Pages publish 4단계 순서 (write → commit → push → verify)
- AC-6.6: robots.txt 신규 생성 (User-agent: * / Disallow: /)
- §7: ops_alert 별도 chat, 본문 형식

mock 전략:
- `subprocess.run` 은 publish() 의 `git_runner` 인자로 직접 주입한다.
- `requests.head` 는 publish() 의 `http_checker` 인자로 직접 주입한다.
- `requests.post` 는 telegram_send/ops_alert 의 `http_post` 인자로 직접 주입한다.
- 시간 polling 은 `sleep=lambda _: None` 으로 즉시 진행.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.dispatchers import (
    PagesPublishError,
    SendResult,
    TelegramSendError,
)
from src.dispatchers import pages_publish, telegram_send, ops_alert
from src.lib.time_helper import KST


# ---------------------------------------------------------------------------
# 공통 헬퍼 — Pages 4단계 git mock + RenderedDigest 더블.
# ---------------------------------------------------------------------------


@dataclass
class _FakeDigest:
    """RenderedDigest 의 최소 인터페이스 (html / telegram_text)."""

    html: str = "<html><head><meta name='robots' content='noindex,nofollow'></head><body>x</body></html>"
    telegram_text: str = "TL;DR\n- 항목1\n- 항목2"


def _proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _make_git_runner_success(tracked: bool = False) -> MagicMock:
    """publish() 4단계 git 호출에 응답하는 mock subprocess.run.

    호출 순서 (구현 기준, gh-pages worktree 흐름):
        1) git worktree add {tmp_dir} gh-pages → returncode 0
        2) git ls-files --error-unmatch digest/YYYY-MM-DD.html → tracked 여부
        3) git add digest/... robots.txt
        4) git commit -m ...
        5) git push origin gh-pages
        6) git worktree remove {tmp_dir} --force (cleanup)
    """
    def _side_effect(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
        # args[0] == "git", args[1] == 서브커맨드
        sub = args[1] if len(args) > 1 else ""
        if sub == "worktree":
            # worktree add | worktree remove 둘 다 성공.
            return _proc(returncode=0)
        if sub == "ls-files":
            return _proc(returncode=0 if tracked else 1)
        if sub == "add":
            return _proc(returncode=0)
        if sub == "commit":
            return _proc(returncode=0)
        if sub == "push":
            return _proc(returncode=0)
        return _proc(returncode=0)

    mock = MagicMock(side_effect=_side_effect)
    return mock


def _http_head_ok() -> MagicMock:
    """status_code=200 응답 mock."""
    resp = MagicMock()
    resp.status_code = 200
    return MagicMock(return_value=resp)


def _http_head_404() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 404
    return MagicMock(return_value=resp)


# ===========================================================================
# Pages publish — 4 케이스
# ===========================================================================


class TestPagesPublish:
    """`pages_publish.publish` — gh-pages worktree 흐름.

    write (worktree add + 파일 작성) → commit → push gh-pages → verify → cleanup.
    """

    @staticmethod
    def _tmp_factory(tmp_path: Path) -> Any:
        """`tempfile.mkdtemp` 호환 hook — pytest tmp_path 안에 격리.

        worktree add 가 빈 디렉토리에 checkout 한 척, mock git_runner 가 가짜 응답을 주는
        동안 실제 디스크 write/read 는 tmp_path 안에서 일어난다.
        """
        counter = {"i": 0}

        def factory(prefix: str = "tmp-") -> str:
            counter["i"] += 1
            p = tmp_path / f"{prefix}{counter['i']}"
            p.mkdir(parents=True, exist_ok=True)
            return str(p)

        return factory

    def test_publish_normal_4_stages_returns_url(self, tmp_path: Path) -> None:
        """정상: worktree add → write → add/commit → push gh-pages → verify → cleanup."""
        git_runner = _make_git_runner_success(tracked=False)
        http_checker = _http_head_ok()
        digest = _FakeDigest()
        tmp_factory = self._tmp_factory(tmp_path)

        url = pages_publish.publish(
            digest=digest,
            date_kst=date(2026, 5, 19),
            repo_root=tmp_path,
            pages_base_url="https://owner.github.io/f_trendnewsbot",
            git_runner=git_runner,
            http_checker=http_checker,
            verify_timeout_seconds=2,
            sleep=lambda _s: None,
            tmp_factory=tmp_factory,
        )

        # 1) URL 형식.
        assert url == "https://owner.github.io/f_trendnewsbot/digest/2026-05-19.html"

        # 2) html 파일 작성 — gh-pages worktree (tmp_factory) 내부에 작성됐는지 검증.
        #    master branch 의 docs/digest/ 에는 절대 생기지 않아야 한다 (boundary).
        assert not (tmp_path / "docs" / "digest" / "2026-05-19.html").exists()
        worktree_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("ghpages-")]
        assert len(worktree_dirs) == 1, "tmp_factory worktree 디렉토리 1개 생성 기대"
        html_path = worktree_dirs[0] / "digest" / "2026-05-19.html"
        assert html_path.exists()
        assert html_path.read_text(encoding="utf-8") == digest.html

        # 3) git 호출 순서 검증 — worktree add → ls-files → add → commit → push → worktree remove.
        subcommands = [call.args[0][1] for call in git_runner.call_args_list]
        # 호출 부커맨드 시퀀스. worktree 가 처음·끝에 등장해야 함 (add/remove 둘 다 'worktree').
        assert subcommands[0] == "worktree"  # worktree add
        assert "ls-files" in subcommands
        assert "add" in subcommands
        assert "commit" in subcommands
        assert "push" in subcommands
        assert subcommands[-1] == "worktree"  # worktree remove (cleanup)
        # rev-parse 는 더 이상 호출되지 않아야 (branch 탐지 제거됨).
        assert "rev-parse" not in subcommands

        # 4) push 인자: origin gh-pages (branch 고정).
        push_calls = [c for c in git_runner.call_args_list if c.args[0][1] == "push"]
        assert len(push_calls) == 1
        assert push_calls[0].args[0] == ["git", "push", "origin", "gh-pages"]

        # 5) worktree add 인자: gh-pages branch checkout.
        worktree_add_call = git_runner.call_args_list[0]
        assert worktree_add_call.args[0][:3] == ["git", "worktree", "add"]
        assert worktree_add_call.args[0][-1] == "gh-pages"

        # 6) http_checker 1회 호출 (HEAD 200 즉시 통과).
        assert http_checker.call_count == 1

    def test_publish_git_push_failure_raises_push_stage(self, tmp_path: Path) -> None:
        """git push 단계에서 returncode!=0 → PagesPublishError(stage='push')."""
        def _side_effect(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
            sub = args[1]
            if sub == "worktree":
                return _proc(returncode=0)  # add 와 remove 둘 다 성공
            if sub == "ls-files":
                return _proc(returncode=1)  # not tracked
            if sub == "add":
                return _proc(returncode=0)
            if sub == "commit":
                return _proc(returncode=0)
            if sub == "push":
                return _proc(returncode=128, stderr="fatal: remote rejected")
            return _proc(returncode=0)

        git_runner = MagicMock(side_effect=_side_effect)
        http_checker = _http_head_ok()
        tmp_factory = self._tmp_factory(tmp_path)

        with pytest.raises(PagesPublishError) as exc_info:
            pages_publish.publish(
                digest=_FakeDigest(),
                date_kst=date(2026, 5, 19),
                repo_root=tmp_path,
                pages_base_url="https://owner.github.io/f_trendnewsbot",
                git_runner=git_runner,
                http_checker=http_checker,
                verify_timeout_seconds=2,
                sleep=lambda _s: None,
                tmp_factory=tmp_factory,
            )

        assert exc_info.value.stage == "push"
        # http_checker 는 호출되지 않아야 함 — push 실패 시 verify 진입 금지.
        assert http_checker.call_count == 0
        # cleanup (worktree remove) 은 finally 블록에서 호출돼야 한다.
        worktree_calls = [
            c for c in git_runner.call_args_list if c.args[0][1] == "worktree"
        ]
        # 1회 add + 1회 remove = 2회 최소.
        assert len(worktree_calls) == 2
        assert worktree_calls[-1].args[0][2] == "remove"

    def test_publish_verify_timeout_all_404_raises_verify_stage(
        self, tmp_path: Path
    ) -> None:
        """push 성공이지만 verify polling 내내 404 → PagesPublishError(stage='verify')."""
        git_runner = _make_git_runner_success(tracked=False)
        http_checker = _http_head_404()
        tmp_factory = self._tmp_factory(tmp_path)

        with pytest.raises(PagesPublishError) as exc_info:
            pages_publish.publish(
                digest=_FakeDigest(),
                date_kst=date(2026, 5, 19),
                repo_root=tmp_path,
                pages_base_url="https://owner.github.io/f_trendnewsbot",
                git_runner=git_runner,
                http_checker=http_checker,
                verify_timeout_seconds=2,  # 짧은 timeout으로 빠르게 종료
                sleep=lambda _s: None,
                tmp_factory=tmp_factory,
            )

        assert exc_info.value.stage == "verify"
        # 최소 1회 이상 polling 시도.
        assert http_checker.call_count >= 1
        # cleanup 호출 확인 (verify 실패 후 finally).
        worktree_calls = [
            c for c in git_runner.call_args_list if c.args[0][1] == "worktree"
        ]
        assert worktree_calls[-1].args[0][2] == "remove"

    def test_publish_creates_robots_txt_when_missing(self, tmp_path: Path) -> None:
        """robots.txt 가 없는 worktree → publish 후 신규 생성 (gh-pages tmp_dir 안)."""
        git_runner = _make_git_runner_success(tracked=False)
        http_checker = _http_head_ok()
        tmp_factory = self._tmp_factory(tmp_path)

        pages_publish.publish(
            digest=_FakeDigest(),
            date_kst=date(2026, 5, 19),
            repo_root=tmp_path,
            pages_base_url="https://owner.github.io/f_trendnewsbot",
            git_runner=git_runner,
            http_checker=http_checker,
            verify_timeout_seconds=2,
            sleep=lambda _s: None,
            tmp_factory=tmp_factory,
        )

        # gh-pages worktree 디렉토리 안에서 robots.txt 확인.
        worktree_dirs = [p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("ghpages-")]
        assert len(worktree_dirs) == 1
        robots_path = worktree_dirs[0] / "robots.txt"
        assert robots_path.exists()
        content = robots_path.read_text(encoding="utf-8")
        assert "User-agent: *" in content
        assert "Disallow: /" in content
        # master branch boundary — repo_root/docs/digest/ 에는 robots.txt 가 생성되면 안 됨.
        assert not (tmp_path / "docs" / "digest" / "robots.txt").exists()

    def test_publish_worktree_add_failure_raises_write_stage(self, tmp_path: Path) -> None:
        """gh-pages branch 가 없어 `git worktree add` 자체가 실패 → PagesPublishError(stage='write').

        메시지에 '운영자 초기 셋업' 안내 문구가 포함되어야 한다 (gh-pages orphan branch push 필요).
        """
        def _side_effect(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
            sub = args[1]
            if sub == "worktree":
                op = args[2] if len(args) > 2 else ""
                if op == "add":
                    return _proc(
                        returncode=128,
                        stderr="fatal: invalid reference: gh-pages",
                    )
                # remove (cleanup) 도 실패해도 raise 하지 않음.
                return _proc(returncode=0)
            return _proc(returncode=0)

        git_runner = MagicMock(side_effect=_side_effect)
        http_checker = _http_head_ok()
        tmp_factory = self._tmp_factory(tmp_path)

        with pytest.raises(PagesPublishError) as exc_info:
            pages_publish.publish(
                digest=_FakeDigest(),
                date_kst=date(2026, 5, 19),
                repo_root=tmp_path,
                pages_base_url="https://owner.github.io/f_trendnewsbot",
                git_runner=git_runner,
                http_checker=http_checker,
                verify_timeout_seconds=2,
                sleep=lambda _s: None,
                tmp_factory=tmp_factory,
            )

        assert exc_info.value.stage == "write"
        assert "운영자 초기 셋업" in exc_info.value.message
        # add → commit → push → verify 어느 단계도 진입하지 않아야 한다.
        subcommands = [call.args[0][1] for call in git_runner.call_args_list]
        assert "add" not in subcommands
        assert "commit" not in subcommands
        assert "push" not in subcommands
        # http_checker 미호출 (verify 진입 금지).
        assert http_checker.call_count == 0


# ===========================================================================
# Telegram send — 7 케이스
# ===========================================================================


def _telegram_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


class TestTelegramSend:
    """`telegram_send.send` — Bot API sendMessage + retry 1회."""

    def test_send_200_returns_success_send_result(self) -> None:
        """정상 200 → SendResult(success=True, kind='telegram', retried=0)."""
        http_post = MagicMock(return_value=_telegram_response(200))

        result = telegram_send.send(
            digest=_FakeDigest(),
            pages_url="https://owner.github.io/f_trendnewsbot/digest/2026-05-19.html",
            chat_id=-1001234567890,
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            http_post=http_post,
        )

        assert isinstance(result, SendResult)
        assert result.success is True
        assert result.kind == "telegram"
        assert result.retried == 0
        assert http_post.call_count == 1

    def test_send_chat_id_invalid_400_raises_bad_request(self) -> None:
        """chat_id 무효 400 — bad_request 는 retry 무의미 → 즉시 raise."""
        http_post = MagicMock(return_value=_telegram_response(400))

        with pytest.raises(TelegramSendError) as exc_info:
            telegram_send.send(
                digest=_FakeDigest(),
                pages_url="https://example.com/d.html",
                chat_id=-1001234567890,
                bot_token="123456:abcdefghijklmnopqrstuvwxyz",
                http_post=http_post,
            )

        assert exc_info.value.error_kind == "bad_request"

    def test_send_token_invalid_401_raises_auth(self) -> None:
        """토큰 무효 401 → auth 분류 raise."""
        http_post = MagicMock(return_value=_telegram_response(401))

        with pytest.raises(TelegramSendError) as exc_info:
            telegram_send.send(
                digest=_FakeDigest(),
                pages_url="https://example.com/d.html",
                chat_id=-1001234567890,
                bot_token="invalid_token_123",
                http_post=http_post,
            )

        assert exc_info.value.error_kind == "auth"

    def test_send_first_timeout_then_200_succeeds_with_retried_1(self) -> None:
        """첫 시도 ConnectionTimeout → retry 후 200 → SendResult(success=True, retried=1)."""
        attempts: list[int] = []

        def _side_effect(*args: Any, **kwargs: Any) -> MagicMock:
            attempts.append(1)
            if len(attempts) == 1:
                raise TimeoutError("connection timed out")
            return _telegram_response(200)

        http_post = MagicMock(side_effect=_side_effect)

        result = telegram_send.send(
            digest=_FakeDigest(),
            pages_url="https://example.com/d.html",
            chat_id=-1001234567890,
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            http_post=http_post,
        )

        assert result.success is True
        assert result.retried == 1
        assert http_post.call_count == 2

    def test_send_two_timeouts_raises_network(self) -> None:
        """두 번 다 timeout → TelegramSendError('network')."""
        http_post = MagicMock(side_effect=TimeoutError("timed out"))

        with pytest.raises(TelegramSendError) as exc_info:
            telegram_send.send(
                digest=_FakeDigest(),
                pages_url="https://example.com/d.html",
                chat_id=-1001234567890,
                bot_token="123456:abcdefghijklmnopqrstuvwxyz",
                http_post=http_post,
            )

        assert exc_info.value.error_kind == "network"
        assert http_post.call_count == 2  # 1회 + retry 1회

    def test_send_text_over_4096_bytes_raises_too_long_without_http_call(self) -> None:
        """text 길이 4097 bytes → TelegramSendError('too_long'), http_post 호출 안 됨."""
        http_post = MagicMock()
        # ASCII 1byte 문자 * 4097
        oversized = "A" * 4097
        digest = _FakeDigest(telegram_text=oversized)

        with pytest.raises(TelegramSendError) as exc_info:
            telegram_send.send(
                digest=digest,
                pages_url="",  # url append 없이도 이미 4097
                chat_id=-1001234567890,
                bot_token="123456:abcdefghijklmnopqrstuvwxyz",
                http_post=http_post,
            )

        assert exc_info.value.error_kind == "too_long"
        # 핵심: dispatcher 최종 방어선 — HTTP 호출 자체가 발생하면 안 됨.
        assert http_post.call_count == 0

    def test_send_payload_contains_disable_web_page_preview_and_parse_mode(self) -> None:
        """요청 body 에 disable_web_page_preview=True, parse_mode='HTML' 포함 (AC-2.3-A)."""
        http_post = MagicMock(return_value=_telegram_response(200))

        telegram_send.send(
            digest=_FakeDigest(),
            pages_url="https://example.com/d.html",
            chat_id=-1001234567890,
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            http_post=http_post,
        )

        # 첫 호출의 keyword 인자 `json` 검사.
        _args, kwargs = http_post.call_args
        payload = kwargs["json"]
        assert payload["parse_mode"] == "HTML"
        assert payload["disable_web_page_preview"] is True
        assert payload["chat_id"] == -1001234567890
        assert "text" in payload
        # text 안에 pages_url 풋터가 부착됐는지 — render 와 dispatcher 가 같은 helper(_build_text) 공유.
        assert "https://example.com/d.html" in payload["text"]


# ===========================================================================
# Ops alert — 3 케이스
# ===========================================================================


def _fixed_now_kst() -> datetime:
    """결정적 KST 시각 — 본문 시간 표기 검증을 안정화."""
    return datetime(2026, 5, 19, 7, 30, tzinfo=KST)


class TestOpsAlert:
    """`ops_alert.send_ops_alert` — 운영자 chat 전용 + 재시도 0회."""

    def test_send_ops_alert_normal_returns_none_and_calls_http_once(self) -> None:
        """정상 발송 → None 반환, http_post 1회 호출."""
        http_post = MagicMock(return_value=_telegram_response(200))

        result = ops_alert.send_ops_alert(
            reason="telegram_failed",
            error=RuntimeError("boom"),
            chat_id=-1009876543210,
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            next_cron_kst=datetime(2026, 5, 20, 7, 30, tzinfo=KST),
            http_post=http_post,
            now_kst_fn=_fixed_now_kst,
        )

        assert result is None
        assert http_post.call_count == 1
        _args, kwargs = http_post.call_args
        # chat_id 가 운영자 chat 으로 분리됐는지.
        assert kwargs["json"]["chat_id"] == -1009876543210
        # 본문에 reason 라벨 + KST 시각이 포함.
        body = kwargs["json"]["text"]
        assert "[팜보스 트렌드 알림]" in body
        assert "텔레그램 발송 실패" in body

    def test_send_ops_alert_http_failure_logs_stderr_no_raise(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """http_post 가 RequestException → stderr 로그만, raise 안 함 (None 반환). 재시도 0회."""
        http_post = MagicMock(side_effect=ConnectionError("network down"))

        result = ops_alert.send_ops_alert(
            reason="unexpected",
            error=ValueError("inner"),
            chat_id=-1009876543210,
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            next_cron_kst=None,
            http_post=http_post,
            now_kst_fn=_fixed_now_kst,
        )

        # raise 없이 None.
        assert result is None
        # 1회만 호출 — 재시도 없음 (AC-5.4 무한루프 방지).
        assert http_post.call_count == 1
        # stderr 에 실패 메시지가 찍혔는지.
        captured = capsys.readouterr()
        assert "ops_alert" in captured.err
        assert "재시도 없음" in captured.err

    def test_send_ops_alert_chat_id_string_negative_int_is_coerced(self) -> None:
        """chat_id 가 음수 정수 문자열 "-1001234567890" → int 변환되어 payload 에 들어감."""
        http_post = MagicMock(return_value=_telegram_response(200))

        ops_alert.send_ops_alert(
            reason="quota_exceeded",
            error=None,
            chat_id="-1001234567890",
            bot_token="123456:abcdefghijklmnopqrstuvwxyz",
            next_cron_kst=None,
            http_post=http_post,
            now_kst_fn=_fixed_now_kst,
        )

        _args, kwargs = http_post.call_args
        assert kwargs["json"]["chat_id"] == -1001234567890
        # 본문에 "다음 cron: 예정 시각 미상" 분기 표시 (next_cron_kst=None 경로).
        assert "예정 시각 미상" in kwargs["json"]["text"]
