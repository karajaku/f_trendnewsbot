"""`config/*.yml` 로더 — V1 정적 설정의 dataclass 변환·schema validation.

requirements §6-1 (`sources.yml`) / §6-2 (`filters.yml`) 을 단일 진실로 한다.
recipients.yml 은 ADR-003 에 따라 V1 에서 로드하지 않는다 — 직원 수신자는 텔레그램
단톡방 멤버십으로 관리되며 `recipients.example.yml` 은 V2 재도입 대비 형식 예시일 뿐이다.

스키마 위반은 모두 `ConfigError(path, line, reason)` 로 보고한다 — 사람 실수
(id 중복·잘못된 enum·범위 밖 임계치 등)를 빠르게 잡기 위한 입력 검증 helper.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, get_args

import yaml

# ---------- enum 정의 ----------

SourceType = Literal["rss", "html", "json_api"]
SourceCategory = Literal["ai_trend", "agri_distribution", "farmboss_keyword"]

_SOURCE_TYPES: tuple[str, ...] = get_args(SourceType)
_SOURCE_CATEGORIES: tuple[str, ...] = get_args(SourceCategory)

# id 정규식 — requirements §6-1.
_SOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

# 기본값 — filters.yml 의 global.time_window_hours 와 일관.
_DEFAULT_TIME_WINDOW_HOURS = 36


# ---------- 예외 ----------


class ConfigError(Exception):
    """설정 파일 schema/형식 오류.

    Attributes:
        path: 오류가 발생한 yml 파일 경로 문자열.
        line: 가능한 경우 yml 라인 번호 (1-based). 알 수 없으면 None.
        reason: 사람 읽을 수 있는 오류 사유 (한국어 가능).
    """

    def __init__(self, path: str, line: int | None, reason: str) -> None:
        self.path = path
        self.line = line
        self.reason = reason
        loc = f"{path}" + (f":{line}" if line is not None else "")
        super().__init__(f"[ConfigError] {loc} — {reason}")


# ---------- dataclass ----------


@dataclass(frozen=True)
class Source:
    """단일 뉴스 소스 entry — requirements §6-1.

    `id` 변경은 history sent.jsonl 의 source_id 매칭을 깨뜨리므로 한 번 정해진
    값은 deprecated 시에도 재사용 금지.
    """

    id: str
    name: str
    url: str
    type: SourceType
    category: SourceCategory
    enabled: bool
    tags: list[str]
    time_window_hours: int = _DEFAULT_TIME_WINDOW_HOURS


@dataclass(frozen=True)
class CategoryFilter:
    """카테고리별 필터 설정 — requirements §6-2."""

    label: str
    must_match_any: list[str]
    exclude_any: list[str]
    order: int


@dataclass(frozen=True)
class GlobalFilters:
    """전역 필터 임계치 — requirements §6-2 `global` 블록."""

    time_window_hours: int
    fuzzy_title_threshold: float
    dedup_days: int


@dataclass(frozen=True)
class Filters:
    """`filters.yml` 전체 — 카테고리별 + 전역."""

    categories: dict[str, CategoryFilter]
    global_filters: GlobalFilters


@dataclass(frozen=True)
class LoadedConfig:
    """`load_all()` 의 반환 형태 — sources + filters."""

    sources: list[Source]
    filters: Filters


# ---------- 내부 helper ----------


def _resolve_repo_root() -> Path:
    """`src/config/loader.py` 기준으로 리포 루트(= `pyproject.toml` 위치) 추정."""
    return Path(__file__).resolve().parent.parent.parent


def _read_yaml(path: Path) -> Any:
    """yml 파일을 안전하게 로드. 파일 없음·yml 파싱 오류는 `ConfigError` 로 변환."""
    if not path.exists():
        raise ConfigError(str(path), None, "파일이 존재하지 않습니다.")
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except yaml.YAMLError as e:
        line = None
        mark = getattr(e, "problem_mark", None)
        if mark is not None:
            # yaml.error.Mark.line 은 0-based.
            line = mark.line + 1
        raise ConfigError(str(path), line, f"YAML 파싱 실패: {e}") from e


def _require_mapping(data: Any, path: Path, what: str) -> dict[str, Any]:
    """최상위 yml 객체가 dict 인지 확인."""
    if not isinstance(data, dict):
        raise ConfigError(str(path), None, f"{what} 은 mapping(dict) 이어야 합니다.")
    return data


# ---------- 공개 API ----------


def load_sources(path: Path) -> list[Source]:
    """`config/sources.yml` 을 읽어 `list[Source]` 로 변환한다.

    schema validation:
        - `sources` 키 존재 + list 타입.
        - 각 entry 의 필수 필드(id/name/url/type/category/enabled/tags) 존재.
        - `id` 정규식 `^[a-z][a-z0-9_]*$` 통과.
        - `id` 중복 금지 (모든 중복 id 를 한 번에 모아 보고).
        - `type` ∈ `{rss, html, json_api}`.
        - `category` ∈ `{ai_trend, agri_distribution, farmboss_keyword}`.
        - `time_window_hours` 는 optional, 미지정 시 36. 양의 정수.
        - `tags` 는 list[str].
    """
    data = _read_yaml(path)
    root = _require_mapping(data, path, "sources.yml 최상위")

    raw_sources = root.get("sources")
    if not isinstance(raw_sources, list):
        raise ConfigError(str(path), None, "`sources` 키는 list 이어야 합니다.")
    if not raw_sources:
        raise ConfigError(str(path), None, "`sources` list 가 비어 있습니다.")

    sources: list[Source] = []
    seen_ids: dict[str, int] = {}
    duplicate_ids: list[str] = []

    for idx, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise ConfigError(
                str(path), None, f"sources[{idx}] 는 mapping(dict) 이어야 합니다."
            )

        # 필수 필드 검사 — `enabled` 는 boolean 이므로 in 체크.
        required = ("id", "name", "url", "type", "category", "enabled", "tags")
        missing = [k for k in required if k not in raw]
        if missing:
            raise ConfigError(
                str(path),
                None,
                f"sources[{idx}] 필수 필드 누락: {', '.join(missing)}",
            )

        sid = raw["id"]
        if not isinstance(sid, str) or not _SOURCE_ID_PATTERN.match(sid):
            raise ConfigError(
                str(path),
                None,
                (
                    f"sources[{idx}].id={sid!r} 가 정규식 `^[a-z][a-z0-9_]*$` 를 "
                    "통과하지 못합니다 (소문자 영문 시작, 영문소문자/숫자/언더스코어만 허용)."
                ),
            )

        if sid in seen_ids:
            duplicate_ids.append(sid)
        else:
            seen_ids[sid] = idx

        stype = raw["type"]
        if stype not in _SOURCE_TYPES:
            raise ConfigError(
                str(path),
                None,
                (
                    f"sources[{idx}].type={stype!r} 는 정의되지 않은 값입니다. "
                    f"허용: {list(_SOURCE_TYPES)}"
                ),
            )

        scat = raw["category"]
        if scat not in _SOURCE_CATEGORIES:
            raise ConfigError(
                str(path),
                None,
                (
                    f"sources[{idx}].category={scat!r} 는 정의되지 않은 값입니다. "
                    f"허용: {list(_SOURCE_CATEGORIES)}"
                ),
            )

        enabled = raw["enabled"]
        if not isinstance(enabled, bool):
            raise ConfigError(
                str(path),
                None,
                f"sources[{idx}].enabled 는 boolean 이어야 합니다 (got {type(enabled).__name__}).",
            )

        tags = raw["tags"]
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise ConfigError(
                str(path),
                None,
                f"sources[{idx}].tags 는 list[str] 이어야 합니다.",
            )

        name = raw["name"]
        url = raw["url"]
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(str(path), None, f"sources[{idx}].name 은 비어있지 않은 문자열이어야 합니다.")
        if not isinstance(url, str) or not url.strip():
            raise ConfigError(str(path), None, f"sources[{idx}].url 은 비어있지 않은 문자열이어야 합니다.")

        twh = raw.get("time_window_hours", _DEFAULT_TIME_WINDOW_HOURS)
        if not isinstance(twh, int) or isinstance(twh, bool) or twh <= 0:
            raise ConfigError(
                str(path),
                None,
                f"sources[{idx}].time_window_hours 는 양의 정수이어야 합니다 (got {twh!r}).",
            )

        sources.append(
            Source(
                id=sid,
                name=name,
                url=url,
                type=stype,  # type: ignore[arg-type]
                category=scat,  # type: ignore[arg-type]
                enabled=enabled,
                tags=list(tags),
                time_window_hours=twh,
            )
        )

    if duplicate_ids:
        # 모든 중복 id 를 한 번에 모아 보고 — step2.md AC.
        unique_dups = sorted(set(duplicate_ids))
        raise ConfigError(
            str(path),
            None,
            f"중복된 source id: {', '.join(unique_dups)}",
        )

    return sources


def load_filters(path: Path) -> Filters:
    """`config/filters.yml` 을 읽어 `Filters` 로 변환한다.

    schema validation:
        - 최상위에 `categories` (dict) + `global` (dict) 키 존재.
        - `categories` 에 3개 카테고리(`ai_trend`/`agri_distribution`/`farmboss_keyword`) 모두 존재.
        - 각 카테고리는 `label` (str) + `must_match_any` (list[str]) + `exclude_any` (list[str]) + `order` (int) 필드 존재.
        - `global.time_window_hours` 양의 정수.
        - `global.fuzzy_title_threshold` ∈ [0.0, 1.0].
        - `global.dedup_days` 양의 정수.
    """
    data = _read_yaml(path)
    root = _require_mapping(data, path, "filters.yml 최상위")

    raw_categories = root.get("categories")
    if not isinstance(raw_categories, dict):
        raise ConfigError(str(path), None, "`categories` 키는 mapping 이어야 합니다.")

    missing_cats = [c for c in _SOURCE_CATEGORIES if c not in raw_categories]
    if missing_cats:
        raise ConfigError(
            str(path),
            None,
            f"필수 카테고리 누락: {', '.join(missing_cats)} (요구: {list(_SOURCE_CATEGORIES)})",
        )

    categories: dict[str, CategoryFilter] = {}
    for cat_key in _SOURCE_CATEGORIES:
        raw_cat = raw_categories[cat_key]
        if not isinstance(raw_cat, dict):
            raise ConfigError(
                str(path),
                None,
                f"categories.{cat_key} 는 mapping 이어야 합니다.",
            )

        for required_field in ("label", "must_match_any", "exclude_any", "order"):
            if required_field not in raw_cat:
                raise ConfigError(
                    str(path),
                    None,
                    f"categories.{cat_key} 필수 필드 누락: {required_field}",
                )

        label = raw_cat["label"]
        mma = raw_cat["must_match_any"]
        exa = raw_cat["exclude_any"]
        order = raw_cat["order"]

        if not isinstance(label, str) or not label.strip():
            raise ConfigError(
                str(path), None, f"categories.{cat_key}.label 은 비어있지 않은 문자열이어야 합니다."
            )
        if not isinstance(mma, list) or not all(isinstance(s, str) for s in mma):
            raise ConfigError(
                str(path), None, f"categories.{cat_key}.must_match_any 는 list[str] 이어야 합니다."
            )
        if not isinstance(exa, list) or not all(isinstance(s, str) for s in exa):
            raise ConfigError(
                str(path), None, f"categories.{cat_key}.exclude_any 는 list[str] 이어야 합니다."
            )
        if not isinstance(order, int) or isinstance(order, bool):
            raise ConfigError(
                str(path), None, f"categories.{cat_key}.order 는 정수이어야 합니다."
            )

        categories[cat_key] = CategoryFilter(
            label=label,
            must_match_any=list(mma),
            exclude_any=list(exa),
            order=order,
        )

    raw_global = root.get("global")
    if not isinstance(raw_global, dict):
        raise ConfigError(str(path), None, "`global` 키는 mapping 이어야 합니다.")

    for required_field in ("time_window_hours", "fuzzy_title_threshold", "dedup_days"):
        if required_field not in raw_global:
            raise ConfigError(
                str(path), None, f"global.{required_field} 필수 필드 누락"
            )

    twh = raw_global["time_window_hours"]
    ftt = raw_global["fuzzy_title_threshold"]
    dd = raw_global["dedup_days"]

    if not isinstance(twh, int) or isinstance(twh, bool) or twh <= 0:
        raise ConfigError(
            str(path), None, f"global.time_window_hours 는 양의 정수이어야 합니다 (got {twh!r})."
        )
    if not isinstance(ftt, (int, float)) or isinstance(ftt, bool):
        raise ConfigError(
            str(path), None, f"global.fuzzy_title_threshold 는 숫자이어야 합니다 (got {ftt!r})."
        )
    if not (0.0 <= float(ftt) <= 1.0):
        raise ConfigError(
            str(path),
            None,
            f"global.fuzzy_title_threshold={ftt!r} 는 [0.0, 1.0] 범위 밖입니다.",
        )
    if not isinstance(dd, int) or isinstance(dd, bool) or dd <= 0:
        raise ConfigError(
            str(path), None, f"global.dedup_days 는 양의 정수이어야 합니다 (got {dd!r})."
        )

    return Filters(
        categories=categories,
        global_filters=GlobalFilters(
            time_window_hours=twh,
            fuzzy_title_threshold=float(ftt),
            dedup_days=dd,
        ),
    )


def load_all(root: Path | None = None) -> LoadedConfig:
    """`config/sources.yml` + `config/filters.yml` 을 함께 로드한다.

    ADR-003 에 따라 V1 에서는 `recipients.yml` 을 읽지 않는다 — 직원 수신자는 텔레그램
    단톡방 멤버십으로 관리한다.
    """
    base = (root or _resolve_repo_root()) / "config"
    sources = load_sources(base / "sources.yml")
    filters = load_filters(base / "filters.yml")
    return LoadedConfig(sources=sources, filters=filters)
