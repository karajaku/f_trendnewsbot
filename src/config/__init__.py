"""`src.config` — V1 정적 설정(`config/*.yml`) 로더 패키지.

requirements §6-1 (`sources.yml`) / §6-2 (`filters.yml`) 의 단일 진실. ADR-003 에 따라
V1 에서 `recipients.yml` 은 로드하지 않는다 — 직원 수신자는 텔레그램 단톡방 멤버십으로 관리.
"""

from src.config.loader import (
    CategoryFilter,
    ConfigError,
    Filters,
    GlobalFilters,
    LoadedConfig,
    Source,
    load_all,
    load_filters,
    load_sources,
)

__all__ = [
    "CategoryFilter",
    "ConfigError",
    "Filters",
    "GlobalFilters",
    "LoadedConfig",
    "Source",
    "load_all",
    "load_filters",
    "load_sources",
]
