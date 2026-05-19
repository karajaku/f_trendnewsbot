"""`src.config.loader` 단위 테스트 — step2.md AC 9건 매핑.

테스트는 모두 `tmp_path` pytest fixture 로 동적 yml 을 생성한다. 실제 `config/*.yml`
은 건드리지 않는다. 단, 정상 로드 1건과 farmboss_keyword 시드 12개 검증 1건은
프로젝트 루트의 실제 `config/*.yml` 을 직접 load_all() 로 검증한다 — requirements
§6-2 동결 키워드가 그대로 살아있는지 회귀 방지.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from src.config.loader import (
    ConfigError,
    load_all,
    load_filters,
    load_sources,
)

# ---------- 테스트용 helper ----------


_VALID_FILTERS_YML = dedent(
    """\
    categories:
      ai_trend:
        label: "AI 트렌드"
        must_match_any: ["AI", "LLM"]
        exclude_any: []
        order: 1
      agri_distribution:
        label: "농산물·유통"
        must_match_any: ["농산물"]
        exclude_any: []
        order: 2
      farmboss_keyword:
        label: "팜보스 관심 키워드"
        must_match_any:
          - "정다운"
          - "팜보스"
          - "시경"
          - "닥터상달"
          - "GS리테일"
          - "청도"
          - "경산"
          - "밀양"
          - "복숭아"
          - "감"
          - "딸기"
          - "안동농협공판장"
        exclude_any: []
        order: 3
    global:
      time_window_hours: 36
      fuzzy_title_threshold: 0.85
      dedup_days: 7
    """
)


def _src_entry(
    sid: str = "anthropic_blog",
    stype: str = "rss",
    cat: str = "ai_trend",
) -> str:
    return dedent(
        f"""\
        - id: {sid}
          name: "{sid}"
          url: "https://example.com/{sid}.xml"
          type: {stype}
          category: {cat}
          enabled: true
          tags: ["t1"]
        """
    )


def _write_sources(path: Path, body: str) -> Path:
    path.write_text("sources:\n" + body, encoding="utf-8")
    return path


def _write_filters(path: Path, body: str = _VALID_FILTERS_YML) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------- 1. 정상 로드 ----------


def test_load_all_with_repo_config_returns_seed_in_range(tmp_path: Path) -> None:
    """실제 리포 `config/*.yml` 을 로드해 12~18 소스 + 카테고리 3개 검증 (AC 시드 범위)."""
    cfg = load_all()
    assert 12 <= len(cfg.sources) <= 18
    assert set(cfg.filters.categories.keys()) == {
        "ai_trend",
        "agri_distribution",
        "farmboss_keyword",
    }
    assert cfg.filters.global_filters.fuzzy_title_threshold == 0.85
    assert cfg.filters.global_filters.time_window_hours == 36
    assert cfg.filters.global_filters.dedup_days == 7
    # source id 는 모두 정규식 통과 + 중복 없음 (load_sources 가 이미 검증하지만 안전망)
    ids = [s.id for s in cfg.sources]
    assert len(ids) == len(set(ids))


def test_load_sources_normal_tmp_yml(tmp_path: Path) -> None:
    """tmp_path 에 정상 sources.yml 작성 후 dataclass 변환 확인."""
    body = (
        _src_entry("anthropic_blog", "rss", "ai_trend")
        + _src_entry("openai_blog", "html", "ai_trend")
        + _src_entry("nongmin_news", "rss", "agri_distribution")
        + _src_entry("cheongdo_gov", "json_api", "farmboss_keyword")
    )
    src_path = _write_sources(tmp_path / "sources.yml", body)
    sources = load_sources(src_path)
    assert len(sources) == 4
    assert sources[0].id == "anthropic_blog"
    assert sources[0].type == "rss"
    assert sources[0].category == "ai_trend"
    # 기본 time_window_hours = 36
    assert sources[0].time_window_hours == 36
    assert sources[1].type == "html"
    assert sources[3].type == "json_api"


# ---------- 2. id 중복 ----------


def test_load_sources_duplicate_ids_reports_all(tmp_path: Path) -> None:
    """중복된 id 가 여러 개면 모두 한 메시지에 보고된다."""
    body = (
        _src_entry("dup_a", "rss", "ai_trend")
        + _src_entry("dup_a", "rss", "agri_distribution")  # 중복 1
        + _src_entry("dup_b", "html", "ai_trend")
        + _src_entry("dup_b", "rss", "farmboss_keyword")  # 중복 2
        + _src_entry("unique_one", "rss", "ai_trend")
    )
    src_path = _write_sources(tmp_path / "sources.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_sources(src_path)
    msg = str(exc.value)
    assert "dup_a" in msg
    assert "dup_b" in msg
    assert "unique_one" not in msg


# ---------- 3. 잘못된 type ----------


def test_load_sources_invalid_type_value(tmp_path: Path) -> None:
    """`type=xml` 같은 enum 밖 값은 ConfigError."""
    body = _src_entry("bad_one", "xml", "ai_trend")
    src_path = _write_sources(tmp_path / "sources.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_sources(src_path)
    assert "type" in str(exc.value)
    assert "xml" in str(exc.value)


# ---------- 4. 잘못된 category ----------


def test_load_sources_invalid_category_value(tmp_path: Path) -> None:
    """`category=politics` 같은 enum 밖 값은 ConfigError."""
    body = _src_entry("bad_two", "rss", "politics")
    src_path = _write_sources(tmp_path / "sources.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_sources(src_path)
    assert "category" in str(exc.value)
    assert "politics" in str(exc.value)


# ---------- 5. id 정규식 위반 ----------


@pytest.mark.parametrize(
    "bad_id",
    [
        "Anthropic_Blog",  # 대문자
        "1stsource",       # 숫자 시작
        "hyphen-id",        # hyphen 금지
        "with space",       # 공백
        "",                  # 빈 문자열
    ],
)
def test_load_sources_invalid_id_pattern(tmp_path: Path, bad_id: str) -> None:
    """id 정규식 `^[a-z][a-z0-9_]*$` 위반 케이스들."""
    body = _src_entry(bad_id, "rss", "ai_trend")
    src_path = _write_sources(tmp_path / "sources.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_sources(src_path)
    assert "id" in str(exc.value)


# ---------- 6. filters 카테고리 누락 ----------


def test_load_filters_missing_category(tmp_path: Path) -> None:
    """3 카테고리 중 하나라도 빠지면 ConfigError + 누락된 카테고리 이름 노출."""
    body = dedent(
        """\
        categories:
          ai_trend:
            label: "AI 트렌드"
            must_match_any: ["AI"]
            exclude_any: []
            order: 1
          agri_distribution:
            label: "농산물·유통"
            must_match_any: ["농산물"]
            exclude_any: []
            order: 2
          # farmboss_keyword 누락
        global:
          time_window_hours: 36
          fuzzy_title_threshold: 0.85
          dedup_days: 7
        """
    )
    fp = _write_filters(tmp_path / "filters.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_filters(fp)
    assert "farmboss_keyword" in str(exc.value)


# ---------- 7. fuzzy_title_threshold 범위 밖 ----------


@pytest.mark.parametrize("bad_value", ["1.5", "-0.1", "2"])
def test_load_filters_fuzzy_threshold_out_of_range(tmp_path: Path, bad_value: str) -> None:
    """fuzzy_title_threshold 가 [0.0, 1.0] 밖이면 ConfigError."""
    body = _VALID_FILTERS_YML.replace(
        "fuzzy_title_threshold: 0.85", f"fuzzy_title_threshold: {bad_value}"
    )
    fp = _write_filters(tmp_path / "filters.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_filters(fp)
    assert "fuzzy_title_threshold" in str(exc.value)


# ---------- 8. 파일 없음 ----------


def test_load_sources_missing_file(tmp_path: Path) -> None:
    """존재하지 않는 yml 파일은 ConfigError."""
    missing = tmp_path / "does_not_exist.yml"
    with pytest.raises(ConfigError) as exc:
        load_sources(missing)
    assert "존재하지 않습니다" in str(exc.value)


def test_load_filters_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing_filters.yml"
    with pytest.raises(ConfigError) as exc:
        load_filters(missing)
    assert "존재하지 않습니다" in str(exc.value)


# ---------- 9. farmboss_keyword 시드 동결 검증 ----------


def test_farmboss_keyword_seed_frozen_in_repo_config() -> None:
    """requirements §6-2 / tech-research 결론 #5 — 12개 시드 동결.

    실제 리포 `config/filters.yml` 의 farmboss_keyword 시드가 12개이며 핵심 표본
    키워드를 모두 포함하는지 회귀 방지.
    """
    cfg = load_all()
    farmboss = cfg.filters.categories["farmboss_keyword"]
    assert farmboss.label == "팜보스 관심 키워드"
    assert farmboss.order == 3
    assert len(farmboss.must_match_any) == 12
    for required in (
        "정다운",
        "팜보스",
        "시경",
        "닥터상달",
        "GS리테일",
        "청도",
        "경산",
        "밀양",
        "복숭아",
        "감",
        "딸기",
        "안동농협공판장",
    ):
        assert required in farmboss.must_match_any, f"동결 시드 누락: {required}"


# ---------- 보너스: yml 문법 오류 ----------


def test_load_sources_broken_yaml_syntax(tmp_path: Path) -> None:
    """yml 문법 자체가 깨졌으면 ConfigError + 라인 번호 가능하면 포함."""
    fp = tmp_path / "broken.yml"
    fp.write_text("sources:\n  - id: a\n    bad: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_sources(fp)
    assert "YAML 파싱 실패" in str(exc.value) or "파싱" in str(exc.value)


# ---------- 보너스: 필수 필드 누락 ----------


def test_load_sources_missing_required_field(tmp_path: Path) -> None:
    """필수 필드(url) 누락 케이스."""
    body = dedent(
        """\
        - id: missing_url_src
          name: "no url here"
          type: rss
          category: ai_trend
          enabled: true
          tags: []
        """
    )
    fp = _write_sources(tmp_path / "sources.yml", body)
    with pytest.raises(ConfigError) as exc:
        load_sources(fp)
    assert "url" in str(exc.value)
