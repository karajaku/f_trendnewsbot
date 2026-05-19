"""f_trendnewsbot 일일 진입점 — cron 또는 workflow_dispatch 에서 호출.

CLAUDE.md anti-pattern B (통합 진입 비대화) — 본 모듈은 5 단계 호출 + 4개 예외
분기만 담는다. 도메인 규칙(fetcher·필터·요약·발송)은 각 모듈 안에 있다.

호출 순서 (AC-5.6 강제):
    1. setup_logging → config.load_all → secrets_check
    2. fetchers.runner.run_all
    3. history.load + filters.pipeline.apply
    4. SummarizerClient.summarize + summarizer.render.build_digest
    5. dispatchers.pages_publish.publish (성공 후에만 텔레그램 발송)
    6. dispatchers.telegram_send.send → history.record

예외 분기 (CRITICAL #9 quota·CRITICAL #4 외부 장애 격리):
    - QuotaExceededError    → ops_alert + exit 2
    - PagesPublishError     → ops_alert + exit 3
    - TelegramSendError     → ops_alert + exit 4
    - ConfigError           → stderr only + exit 1 (token 부재 가능 — alert 불가)
    - 기타 Exception        → ops_alert (best-effort) + exit 99
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from src.config.loader import load_all
from src.dispatchers import ops_alert, pages_publish, telegram_send
from src.dispatchers.base import PagesPublishError, TelegramSendError
from src.fetchers.runner import run_all as fetchers_run_all
from src.filters.pipeline import apply as filters_apply
from src.history.schema import SentItem, SentRecord
from src.history.store import LocalFileBackend
from src.lib.logging_setup import mask_key, setup_logging
from src.lib.time_helper import now_kst, to_kst_string
from src.summarizer.client import DEFAULT_MODEL, SummarizerClient
from src.summarizer.quota import QuotaExceededError
from src.summarizer.render import build_digest

logger = logging.getLogger(__name__)

# requirements §8 — Secrets 2 + Variables 4. GEMINI_MODEL_ID 는 default 있어 optional.
# ADR-004 (2026-05-19): ANTHROPIC_API_KEY → GEMINI_API_KEY swap (Anthropic → Gemini provider).
REQUIRED_ENV_VARS: tuple[str, ...] = (
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "OPS_ALERT_CHAT_ID",
    "PAGES_BASE_URL",
)


class ConfigError(RuntimeError):
    """필수 환경변수·config 누락. main() 이 stderr 로 명확히 보고 후 exit 1."""

    def __init__(self, missing_env: list[str]) -> None:
        self.missing_env = list(missing_env)
        super().__init__(f"missing env vars: {self.missing_env}")


def secrets_check() -> dict[str, str]:
    """필수 환경변수 5개를 검증 후 dict 반환. 누락 시 ConfigError.

    `GEMINI_MODEL_ID` 는 optional — `DEFAULT_MODEL` fallback 이 summarizer 측에 있다.
    """
    missing = [k for k in REQUIRED_ENV_VARS if not os.environ.get(k)]
    if missing:
        raise ConfigError(missing)
    return {k: os.environ[k] for k in REQUIRED_ENV_VARS}


def _history_backend(repo_root: Path) -> LocalFileBackend:
    """history backend single source of truth — load·record 가 동일 path 공유 (CRITICAL #8)."""
    return LocalFileBackend(repo_root)


def _build_sent_record(
    digest_by_category: dict,
    sent_at_kst: datetime,
    fetch_failures: list,
    summarize_meta: dict,
) -> SentRecord:
    """RenderedDigest 의 항목을 SentRecord 로 변환. 발송 성공 후 history.record 입력."""
    items: list[SentItem] = []
    for cat, rendered_items in digest_by_category.items():
        for ri in rendered_items:
            art = ri.article
            items.append(
                SentItem(
                    canonical_url=art.canonical_url,
                    title=art.title,
                    source_id=art.source_id,
                    category=cat,
                    published_at_kst=to_kst_string(art.published_at_kst),
                )
            )
    return SentRecord(
        version=1,
        sent_at_utc=sent_at_kst.astimezone(timezone.utc).isoformat(),
        sent_at_kst=to_kst_string(sent_at_kst),
        items=items,
        meta={
            "failed_sources": [
                {"id": f.source_id, "name": f.source_name, "kind": f.error_kind}
                for f in fetch_failures
            ],
            **summarize_meta,
        },
    )


def main(argv: list[str] | None = None) -> int:
    """단일 진입점. 본문은 5단계 호출 + 4개 except 핸들러로 한정 (AC-7.3, anti-pattern B)."""
    setup_logging()
    parser = argparse.ArgumentParser(prog="run_daily")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="직원 단톡방 대신 운영자 chat 으로만 발송 (workflow_dispatch dry_run=true 와 동일).",
    )
    args = parser.parse_args(argv)

    sent_at = now_kst()
    repo_root = Path(__file__).resolve().parent.parent
    env: dict[str, str] = {}

    try:
        config = load_all(root=repo_root)
        env = secrets_check()
        logger.info(
            "cron 시작 KST=%s dry_run=%s api_key=%s",
            sent_at.isoformat(), args.dry_run, mask_key(env["GEMINI_API_KEY"]),
        )

        articles, fetch_failures = fetchers_run_all(config.sources)
        backend = _history_backend(repo_root)
        history = backend.load(config.filters.global_filters.dedup_days)
        by_category = filters_apply(
            articles,
            history,
            config.filters,
            config.filters.global_filters,
            fetch_failures=fetch_failures,
        )

        client = SummarizerClient(
            api_key=env["GEMINI_API_KEY"],
            model=os.environ.get("GEMINI_MODEL_ID", DEFAULT_MODEL),
        )
        system_prompt = (repo_root / "prompts" / "summarize.md").read_text(encoding="utf-8")
        summarize_result = client.summarize(by_category, system_prompt)

        digest = build_digest(
            by_category=by_category,
            summarize_result=summarize_result,
            fetch_failures=fetch_failures,
            sent_at_kst=sent_at,
            sources_total=len(config.sources),
            pages_url_template=env["PAGES_BASE_URL"].rstrip("/"),
        )

        # AC-5.6: Pages publish 성공 후에만 텔레그램 발송.
        pages_url = pages_publish.publish(
            digest=digest,
            date_kst=sent_at.date(),
            repo_root=repo_root,
            pages_base_url=env["PAGES_BASE_URL"],
        )
        target_chat = env["OPS_ALERT_CHAT_ID"] if args.dry_run else env["TELEGRAM_CHAT_ID"]
        telegram_send.send(digest, pages_url, target_chat, env["TELEGRAM_BOT_TOKEN"])

        record = _build_sent_record(
            digest.by_category, sent_at, fetch_failures,
            {
                "dropped_items": summarize_result.dropped_items,
                "tokens_in": summarize_result.tokens_in,
                "tokens_out": summarize_result.tokens_out,
                "pages_url": pages_url,
            },
        )
        backend.record(record)
        logger.info("cron 종료 정상 — 발송 건수=%d pages_url=%s", digest.item_count, pages_url)
        return 0

    except QuotaExceededError as e:
        ops_alert.send_ops_alert(
            "quota_exceeded", e,
            env.get("OPS_ALERT_CHAT_ID", ""), env.get("TELEGRAM_BOT_TOKEN", ""),
            next_cron_kst=None,
        )
        return 2
    except PagesPublishError as e:
        ops_alert.send_ops_alert(
            "pages_failed", e,
            env.get("OPS_ALERT_CHAT_ID", ""), env.get("TELEGRAM_BOT_TOKEN", ""),
            next_cron_kst=None,
        )
        return 3
    except TelegramSendError as e:
        ops_alert.send_ops_alert(
            "telegram_failed", e,
            env.get("OPS_ALERT_CHAT_ID", ""), env.get("TELEGRAM_BOT_TOKEN", ""),
            next_cron_kst=None,
        )
        return 4
    except ConfigError as e:
        # secrets 부재 시 ops_alert 토큰도 없을 수 있어 stderr 만.
        sys.stderr.write(f"ConfigError: {e}\n")
        logger.error("config error — 발송 시도 안 함: %s", e)
        return 1
    except Exception as e:  # noqa: BLE001
        logger.error("unexpected — %s\n%s", e, traceback.format_exc())
        ops_alert.send_ops_alert(
            "unexpected", e,
            env.get("OPS_ALERT_CHAT_ID", ""), env.get("TELEGRAM_BOT_TOKEN", ""),
            next_cron_kst=None,
        )
        return 99


if __name__ == "__main__":
    sys.exit(main())
