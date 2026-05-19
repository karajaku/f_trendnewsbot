"""GitHub Pages publish — `gh-pages` 전용 branch 의 `digest/YYYY-MM-DD.html` 작성·commit·push + HTTP 200 확인.

ADR-003 의 코드 측 구현. 2026-05-19 결정으로 master branch 의 `docs/digest/` 가 아닌
`gh-pages` 전용 branch 로 분리 (사내 문서 외부 노출 방지 boundary). 4단계
(write → commit → push → verify) 중 어느 하나라도 실패하면 `PagesPublishError(stage=...)`
로 raise — main() 이 잡아 운영자 alert 로 라우팅 (AC-5.4).

흐름 (master 영향 0):

1. write: `git worktree add {tmp_dir} gh-pages` 로 `gh-pages` branch 를 별도 임시
   디렉토리에 checkout → `{tmp_dir}/digest/YYYY-MM-DD.html` 작성 + `{tmp_dir}/robots.txt`
   가 없으면 생성. `gh-pages` branch 가 없으면 운영자 초기 셋업이 필요 — 명시 에러.
2. commit: `git -C {tmp_dir} add` → `git -C {tmp_dir} commit -m "digest: YYYY-MM-DD"`
   (rerun 이면 `(rerun)` suffix). "nothing to commit" 은 rerun + 내용 동일 케이스로
   push 진입 허용.
3. push: `git -C {tmp_dir} push origin gh-pages` — branch 고정. `_current_branch`
   호출은 제거됨 (gh-pages 고정이라 불필요).
4. verify: `pages_base_url + "/digest/YYYY-MM-DD.html"` 에 HEAD 200 응답을 10초 간격
   polling, 최대 ``verify_timeout_seconds`` 초 (기본 60).

finally 블록은 단계 실패 여부와 무관하게 `git -C {repo_root} worktree remove {tmp_dir} --force`
로 임시 디렉토리를 정리한다 (cleanup 실패는 WARNING 로그만, raise 안 함).

- HTML 본문은 `RenderedDigest.html` 그대로 사용 (anti-pattern A 우회 방지). dispatcher 가
  후처리하지 않음. `<meta name="robots" content="noindex,nofollow">` 은 render 가 hard-code.
- robots.txt 는 디렉토리에 없으면 1회 생성. 내용 고정 (`User-agent: * / Disallow: /`).
- commit author/committer 는 환경변수로 봇 ID 지정 — 사용자 git config 안 건드림.

테스트 hook (`git_runner`, `http_checker`, `tmp_factory`) 로 실제 git·네트워크·디스크 격리
없이 단위 테스트 가능.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable

from .base import PagesPublishError

logger = logging.getLogger(__name__)


# --- 고정 상수 (req §6-1 · AC-6.6) ---

_ROBOTS_TXT_CONTENT = "User-agent: *\nDisallow: /\n"
_DIGEST_SUBDIR = "digest"
_GH_PAGES_BRANCH = "gh-pages"
_COMMIT_AUTHOR_NAME = "f_trendnewsbot"
_COMMIT_AUTHOR_EMAIL = "bot@f_trendnewsbot.local"
_VERIFY_POLL_INTERVAL_SECONDS = 10


def _run_git(
    args: list[str],
    *,
    cwd: Path,
    git_runner: Callable[..., Any],
    capture_output: bool = True,
    check: bool = False,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """git 호출 wrapper — author/committer 환경변수 강제 주입.

    `subprocess.run` 와 동일 시그니처 일부. test 에서 `git_runner` 를 mock 으로 대체.
    """
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", _COMMIT_AUTHOR_NAME)
    env.setdefault("GIT_AUTHOR_EMAIL", _COMMIT_AUTHOR_EMAIL)
    env.setdefault("GIT_COMMITTER_NAME", _COMMIT_AUTHOR_NAME)
    env.setdefault("GIT_COMMITTER_EMAIL", _COMMIT_AUTHOR_EMAIL)
    if extra_env:
        env.update(extra_env)
    return git_runner(
        ["git", *args],
        cwd=str(cwd),
        env=env,
        capture_output=capture_output,
        text=True,
        check=check,
    )


def _is_file_tracked(
    cwd: Path, rel_path: str, *, git_runner: Callable[..., Any]
) -> bool:
    """파일이 이미 git tracking 중인지 확인 — rerun 판정에 사용.

    `cwd` 는 worktree 디렉토리. gh-pages branch 가 checkout 된 곳에서 호출해야
    정확한 결과를 얻는다.
    """
    try:
        proc = _run_git(
            ["ls-files", "--error-unmatch", rel_path],
            cwd=cwd,
            git_runner=git_runner,
        )
    except FileNotFoundError:
        return False
    return getattr(proc, "returncode", 1) == 0


def _cleanup_worktree(
    repo_root: Path,
    tmp_dir: Path,
    *,
    git_runner: Callable[..., Any],
) -> None:
    """worktree 임시 디렉토리 정리. 실패는 WARNING 로그만 — 호출자에 영향 0."""
    try:
        proc = _run_git(
            ["worktree", "remove", str(tmp_dir), "--force"],
            cwd=repo_root,
            git_runner=git_runner,
        )
        if getattr(proc, "returncode", 1) != 0:
            logger.warning(
                "pages_publish — worktree cleanup 실패 (returncode=%s): %s",
                getattr(proc, "returncode", "?"),
                (getattr(proc, "stderr", "") or "").strip() or "unknown",
            )
    except Exception as e:  # noqa: BLE001 — cleanup 은 어떤 예외도 흡수.
        logger.warning("pages_publish — worktree cleanup 예외 흡수: %r", e)


def publish(
    digest: "Any",
    date_kst: date,
    repo_root: Path,
    pages_base_url: str,
    *,
    git_runner: Callable[..., Any] = subprocess.run,
    http_checker: Callable[..., Any] | None = None,
    verify_timeout_seconds: int = 60,
    sleep: Callable[[float], None] = time.sleep,
    tmp_factory: Callable[..., str] = tempfile.mkdtemp,
) -> str:
    """`gh-pages` branch 의 `digest/YYYY-MM-DD.html` 로 publish 후 HTTP 200 확인.

    Args:
        digest: `RenderedDigest` — ``digest.html`` 필드만 사용.
        date_kst: 발송 KST 날짜 (파일명·commit message 에 사용).
        repo_root: repo root 절대 경로 (worktree 명령의 작업 디렉토리).
        pages_base_url: Pages base URL (예: ``https://owner.github.io/f_trendnewsbot``).
            끝의 trailing slash 는 제거 후 사용.
        git_runner: `subprocess.run` 호환 callable. 테스트 hook.
        http_checker: `requests.head` 호환 callable. 테스트 hook. 미지정 시 lazy import.
        verify_timeout_seconds: HTTP 200 polling 최대 시간 (초). 기본 60.
        sleep: polling 간격 sleep. 테스트 hook (`lambda _: None` 으로 즉시 진행).
        tmp_factory: `tempfile.mkdtemp` 호환 callable. 테스트 hook —
            ``lambda prefix: str(tmp_path / prefix)`` 로 pytest tmp_path 격리 가능.

    Returns:
        publicly accessible Pages URL — ``{pages_base_url}/digest/YYYY-MM-DD.html``.

    Raises:
        PagesPublishError: stage 별 실패 사유 라벨링
            (``write`` / ``commit`` / ``push`` / ``verify``).
    """
    if not isinstance(date_kst, date):
        raise PagesPublishError("write", "date_kst 는 datetime.date 이어야 합니다.")
    if not pages_base_url or not pages_base_url.startswith(("http://", "https://")):
        raise PagesPublishError(
            "verify",
            f"pages_base_url 형식 오류 (http(s):// 필요): {pages_base_url!r}",
        )
    if http_checker is None:
        import requests as _requests  # 지연 import — 테스트에서 mock 시 영향 없음.

        http_checker = _requests.head

    repo_root = Path(repo_root)
    base_url = pages_base_url.rstrip("/")
    date_str = date_kst.strftime("%Y-%m-%d")
    rel_html = f"{_DIGEST_SUBDIR}/{date_str}.html"
    rel_robots = "robots.txt"
    final_url = f"{base_url}/{_DIGEST_SUBDIR}/{date_str}.html"

    # html_body 유효성은 worktree 생성 전에 1차 검증 — 무의미한 worktree 생성 회피.
    html_body = getattr(digest, "html", None)
    if not isinstance(html_body, str) or not html_body:
        raise PagesPublishError("write", "digest.html 이 비었거나 문자열이 아닙니다.")

    # tmp_factory 로 격리된 디렉토리 확보. 실패 시 write 단계 에러.
    try:
        tmp_dir = Path(tmp_factory(prefix="ghpages-"))
    except Exception as e:  # pragma: no cover — 디스크/권한 일반화
        raise PagesPublishError("write", f"임시 디렉토리 생성 실패: {e}") from e

    cleanup_done = False
    try:
        # --- 1) write — gh-pages worktree checkout + 파일 작성 ---
        try:
            worktree_proc = _run_git(
                ["worktree", "add", str(tmp_dir), _GH_PAGES_BRANCH],
                cwd=repo_root,
                git_runner=git_runner,
            )
            if getattr(worktree_proc, "returncode", 1) != 0:
                stderr = (getattr(worktree_proc, "stderr", "") or "").strip()
                raise PagesPublishError(
                    "write",
                    "gh-pages branch checkout 실패 — 운영자 초기 셋업"
                    "(orphan branch push) 필요할 수 있음: "
                    f"{stderr or 'unknown'}",
                )

            html_path = tmp_dir / rel_html
            robots_path = tmp_dir / rel_robots
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html_body, encoding="utf-8", newline="\n")
            if not robots_path.exists():
                robots_path.write_text(_ROBOTS_TXT_CONTENT, encoding="utf-8", newline="\n")
        except PagesPublishError:
            raise
        except Exception as e:  # pragma: no cover — 디스크/권한 오류 일반화
            raise PagesPublishError("write", f"파일 작성 실패: {e}") from e

        # --- 2) commit ---
        # rerun 판정: worktree 안의 html 이 이미 git tracked 면 (rerun) suffix.
        is_rerun = _is_file_tracked(tmp_dir, rel_html, git_runner=git_runner)
        commit_msg = f"digest: {date_str}" + (" (rerun)" if is_rerun else "")
        try:
            add_proc = _run_git(
                ["add", rel_html, rel_robots],
                cwd=tmp_dir,
                git_runner=git_runner,
            )
            if getattr(add_proc, "returncode", 1) != 0:
                raise PagesPublishError(
                    "commit",
                    f"git add 실패: {getattr(add_proc, 'stderr', '') or 'unknown'}",
                )
            commit_proc = _run_git(
                ["commit", "-m", commit_msg],
                cwd=tmp_dir,
                git_runner=git_runner,
            )
            if getattr(commit_proc, "returncode", 1) != 0:
                stderr = (getattr(commit_proc, "stderr", "") or "") + (
                    getattr(commit_proc, "stdout", "") or ""
                )
                # "nothing to commit" 은 rerun + 내용 동일 케이스 — push 단계로 진입 허용
                # (이미 게시된 상태일 수 있으므로 verify 까지는 시도).
                if "nothing to commit" in stderr.lower():
                    logger.info(
                        "pages_publish — commit skipped (nothing to commit, rerun=%s).",
                        is_rerun,
                    )
                else:
                    raise PagesPublishError("commit", f"git commit 실패: {stderr or 'unknown'}")
        except PagesPublishError:
            raise
        except Exception as e:  # pragma: no cover
            raise PagesPublishError("commit", f"commit 단계 예외: {e}") from e

        # --- 3) push — gh-pages 고정 (branch 탐지 제거) ---
        try:
            push_proc = _run_git(
                ["push", "origin", _GH_PAGES_BRANCH],
                cwd=tmp_dir,
                git_runner=git_runner,
            )
            if getattr(push_proc, "returncode", 1) != 0:
                stderr = getattr(push_proc, "stderr", "") or "unknown"
                raise PagesPublishError("push", f"git push 실패: {stderr}")
        except PagesPublishError:
            raise
        except Exception as e:  # pragma: no cover
            raise PagesPublishError("push", f"push 단계 예외: {e}") from e

        # --- 4) verify (HTTP 200 polling) ---
        deadline = time.monotonic() + max(0, int(verify_timeout_seconds))
        last_status: int | None = None
        last_exc: Exception | None = None
        while True:
            try:
                resp = http_checker(final_url, timeout=10, allow_redirects=True)
                last_status = getattr(resp, "status_code", None)
                if isinstance(last_status, int) and 200 <= last_status < 300:
                    logger.info(
                        "pages_publish — verified %s (HTTP %d).", final_url, last_status,
                    )
                    # verify 성공 시 즉시 cleanup → return.
                    _cleanup_worktree(repo_root, tmp_dir, git_runner=git_runner)
                    cleanup_done = True
                    return final_url
            except Exception as e:  # noqa: BLE001 — 모든 예외 polling 으로 흡수.
                last_exc = e
                last_status = None
            if time.monotonic() >= deadline:
                break
            sleep(_VERIFY_POLL_INTERVAL_SECONDS)

        detail = (
            f"HTTP status={last_status}"
            if last_status is not None
            else f"network error={last_exc!r}"
        )
        raise PagesPublishError(
            "verify",
            f"{verify_timeout_seconds}초 polling 후에도 200 미수신 ({final_url}, {detail})",
        )
    finally:
        # 어느 단계에서 raise 되든 worktree 정리. 정상 verify 성공 시는 이미 정리됨.
        if not cleanup_done:
            _cleanup_worktree(repo_root, tmp_dir, git_runner=git_runner)
