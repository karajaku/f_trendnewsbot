"""`src.history` 단위 테스트 — step4.md AC 매핑.

매핑:
    AC §6-4 SentRecord roundtrip → test_sent_record_roundtrip
    AC §6-4 unknown version → test_sent_record_unknown_version
    AC fresh-start → test_load_missing_file_returns_empty_with_warning
    AC dedup_days 윈도우 → test_load_filters_by_dedup_days_window
    AC record/load 라운드트립 → test_record_then_load_includes_canonical_urls
    AC malformed JSON skip → test_load_skips_malformed_json_line
    AC items 0건 → test_record_with_empty_items_loads_clean
    AC 디렉토리 자동 생성 → test_record_creates_directory
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from src.history.schema import SCHEMA_VERSION, SentItem, SentRecord
from src.history.store import History, LocalFileBackend
from src.lib.time_helper import now_kst, to_kst_string


# ---------- helper ----------


def _make_item(
    canonical_url: str = "https://example.com/news/abc-1",
    title: str = "샘플 기사 제목",
    source_id: str = "rss_one",
    category: str = "ai_trend",
    published_at_kst: str = "2026-05-19T07:00:00+09:00",
) -> SentItem:
    return SentItem(
        canonical_url=canonical_url,
        title=title,
        source_id=source_id,
        category=category,
        published_at_kst=published_at_kst,
    )


def _make_record(
    sent_at_kst_dt=None,
    items: list[SentItem] | None = None,
    meta: dict | None = None,
) -> SentRecord:
    """현재 KST 기준으로 SentRecord 생성. sent_at_kst_dt 미지정 시 now_kst."""
    from datetime import timezone as _tz

    if sent_at_kst_dt is None:
        sent_at_kst_dt = now_kst()
    sent_at_kst = to_kst_string(sent_at_kst_dt)
    sent_at_utc = sent_at_kst_dt.astimezone(_tz.utc).isoformat()

    return SentRecord(
        version=SCHEMA_VERSION,
        sent_at_utc=sent_at_utc,
        sent_at_kst=sent_at_kst,
        items=items if items is not None else [_make_item()],
        meta=meta if meta is not None else {},
    )


# ---------- 1. SentRecord roundtrip ----------


def test_sent_record_roundtrip() -> None:
    """to_dict → from_dict 가 정보 손실 없이 같은 dataclass 를 복원한다."""
    original = _make_record(
        items=[
            _make_item(
                canonical_url="https://example.com/a",
                title="제목1",
                source_id="rss_one",
                category="ai_trend",
            ),
            _make_item(
                canonical_url="https://example.com/b",
                title="제목2",
                source_id="rss_two",
                category="farmboss_keyword",
            ),
        ],
        meta={"failed_sources": [{"name": "X", "error": "timeout"}], "claude_tokens_in": 1234},
    )
    d = original.to_dict()
    restored = SentRecord.from_dict(d)

    assert restored is not None
    assert restored.version == SCHEMA_VERSION
    assert restored.sent_at_utc == original.sent_at_utc
    assert restored.sent_at_kst == original.sent_at_kst
    assert len(restored.items) == 2
    assert restored.items[0].canonical_url == "https://example.com/a"
    assert restored.items[1].title == "제목2"
    assert restored.meta == original.meta


# ---------- 2. unknown version ----------


def test_sent_record_unknown_version(caplog) -> None:
    """version=99 SentRecord → from_dict None + WARNING."""
    d = {
        "version": 99,
        "sent_at_utc": "2026-05-19T22:30:14+00:00",
        "sent_at_kst": "2026-05-20T07:30:14+09:00",
        "items": [],
        "meta": {},
    }
    with caplog.at_level(logging.WARNING):
        result = SentRecord.from_dict(d)

    assert result is None
    assert any("unknown version" in rec.message.lower() or "version" in rec.message
               for rec in caplog.records if rec.levelno == logging.WARNING)


# ---------- 3. fresh-start ----------


def test_load_missing_file_returns_empty_with_warning(tmp_path: Path, caplog) -> None:
    """파일 없으면 빈 History + WARNING 'fresh-start' 1줄."""
    backend = LocalFileBackend(root=tmp_path)
    assert not backend.path.exists()

    with caplog.at_level(logging.WARNING):
        history = backend.load(dedup_days=7)

    assert history == History.empty()
    assert any("fresh-start" in rec.message for rec in caplog.records if rec.levelno == logging.WARNING)


# ---------- 4. record then load ----------


def test_record_then_load_includes_canonical_urls(tmp_path: Path) -> None:
    """record 한 SentRecord 가 다시 load 시 canonical_urls/titles 에 포함됨."""
    backend = LocalFileBackend(root=tmp_path)
    rec = _make_record(
        items=[
            _make_item(canonical_url="https://example.com/x", title="X 제목"),
            _make_item(canonical_url="https://example.com/y", title="Y 제목"),
        ],
    )
    backend.record(rec)

    history = backend.load(dedup_days=7)

    assert "https://example.com/x" in history.canonical_urls
    assert "https://example.com/y" in history.canonical_urls
    assert "X 제목" in history.titles
    assert "Y 제목" in history.titles


# ---------- 5. dedup_days 윈도우 ----------


def test_load_filters_by_dedup_days_window(tmp_path: Path) -> None:
    """8일 전 record 는 제외, 5일 전 record 는 포함 (dedup_days=7)."""
    backend = LocalFileBackend(root=tmp_path)

    base = now_kst()
    rec_old = _make_record(
        sent_at_kst_dt=base - timedelta(days=8),
        items=[_make_item(canonical_url="https://example.com/old", title="OLD")],
    )
    rec_recent = _make_record(
        sent_at_kst_dt=base - timedelta(days=5),
        items=[_make_item(canonical_url="https://example.com/recent", title="RECENT")],
    )
    backend.record(rec_old)
    backend.record(rec_recent)

    history = backend.load(dedup_days=7)

    assert "https://example.com/recent" in history.canonical_urls
    assert "RECENT" in history.titles
    assert "https://example.com/old" not in history.canonical_urls
    assert "OLD" not in history.titles


# ---------- 6. record append 시 디렉토리 자동 생성 ----------


def test_record_creates_directory(tmp_path: Path) -> None:
    """history 디렉토리가 없어도 record 시 자동 생성."""
    backend = LocalFileBackend(root=tmp_path)
    assert not (tmp_path / "history").exists()

    rec = _make_record()
    backend.record(rec)

    assert (tmp_path / "history").is_dir()
    assert backend.path.exists()


# ---------- 7. items 0건 record ----------


def test_record_with_empty_items_loads_clean(tmp_path: Path) -> None:
    """items 0건 record 도 정상 record/load (canonical_urls/titles 둘 다 비어 있음)."""
    backend = LocalFileBackend(root=tmp_path)
    rec = _make_record(items=[])
    backend.record(rec)

    history = backend.load(dedup_days=7)

    assert history == History.empty()


# ---------- 8. malformed JSON line skip ----------


def test_load_skips_malformed_json_line(tmp_path: Path, caplog) -> None:
    """잘못된 JSON 한 줄 끼어 있으면 skip + WARNING, 나머지는 정상 load."""
    backend = LocalFileBackend(root=tmp_path)

    rec = _make_record(
        items=[_make_item(canonical_url="https://example.com/good", title="좋은 기사")],
    )
    backend.record(rec)

    # 잘못된 JSON line append.
    with backend.path.open("a", encoding="utf-8") as fh:
        fh.write("THIS_IS_NOT_JSON{{{\n")

    # 마지막에 다시 정상 record.
    rec2 = _make_record(
        items=[_make_item(canonical_url="https://example.com/good2", title="또 좋은 기사")],
    )
    backend.record(rec2)

    with caplog.at_level(logging.WARNING):
        history = backend.load(dedup_days=7)

    assert "https://example.com/good" in history.canonical_urls
    assert "https://example.com/good2" in history.canonical_urls
    assert any("malformed JSON" in rec.message or "json" in rec.message.lower()
               for rec in caplog.records if rec.levelno == logging.WARNING)


# ---------- 9. roundtrip via JSON file (보너스) ----------


def test_record_jsonl_format_is_valid_json(tmp_path: Path) -> None:
    """append 된 한 줄이 JSON parsing 가능하고 version 필드가 SCHEMA_VERSION."""
    backend = LocalFileBackend(root=tmp_path)
    rec = _make_record()
    backend.record(rec)

    lines = backend.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["version"] == SCHEMA_VERSION
    assert "sent_at_utc" in parsed
    assert "sent_at_kst" in parsed
    assert "items" in parsed
