# Step 4: filters + history backend — timewindow·keyword·category·dedup + artifact 연동

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.2·AC-4.1~4.4 + §6-4

**qa_blocking: true** — dedup·history는 발송 이력의 신뢰원. 회귀 시 직원이 같은 기사를 두 번 받는 사고 발생. 이 step만 사용자 QA 후 completed.

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) CRITICAL #2 (표시-규칙 helper 공유), CRITICAL #8 (dedup)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.2, AC-4 전체, §6-4 sent.jsonl
- [docs/canonical/ADR.md](../../docs/canonical/ADR.md) ADR-002 artifact 결정
- step1 산출물: `lib/url_helper.canonicalize`, `lib/time_helper.now_kst`
- step2 산출물: `config.loader`의 `GlobalFilters`, `CategoryFilter`
- step3 산출물: `Article` dataclass

## 작업 범위

### Filters

- `src/filters/__init__.py`, `src/filters/base.py` — Filter 인터페이스
- `src/filters/timewindow.py` — `apply(articles, hours)`로 최근 N시간 기사만 통과
- `src/filters/keyword.py` — `Source.tags` + `Article.title/snippet`에 카테고리 매칭
- `src/filters/category.py` — 한 기사가 복수 카테고리 매칭 시 좁은 쪽 1곳 (`farmboss_keyword` > `agri_distribution` > `ai_trend`)
- `src/filters/dedup.py` — canonical URL set 기반 차단 + 제목 fuzzy match (difflib.SequenceMatcher)
- `src/filters/pipeline.py` — `apply(articles, history, filters, global_filters) -> dict[CategoryId, list[Article]]`

### History backend

- `src/history/__init__.py`, `src/history/store.py`
  - `HistoryBackend` 인터페이스 (`load() -> History`, `record(items, meta) -> None`)
  - `ArtifactBackend` 구현 (V1)
  - `History.canonical_urls` (set), `History.titles_for_fuzzy` (list), filter by `dedup_days`
  - 첫 실행 (artifact 없음) 시 빈 History 반환, 로그에 "fresh-start" 명시
- `src/history/schema.py` — `SentRecord` (version, sent_at_utc/kst, items[], meta) dataclass
  - JSON serialize/deserialize, `version: 1` 강제
  - 알 수 없는 version은 무시 (폭주 방지)

### 의존성 추가

- `.github/workflows/daily.yml`에 `actions/download-artifact@v4` + `actions/upload-artifact@v4` 사용 가이드를 step7에서 통합 — 본 step에서는 backend 인터페이스 + 로컬 file backend(테스트용) 까지

## 영향받는 데이터 정의 목록

- `history/sent.jsonl` — 신규 정의 (인스턴스 state, artifact 영속, requirements §6-4 스키마)
- `.gitignore` — 이미 `history/*.jsonl` 차단 — 추가 작업 없음

## Acceptance Criteria

- [ ] `filters/dedup.py`가 `url_helper.canonicalize` 호출로만 정규화 — 자체 URL 자르기 코드 0줄 (AC-7.4)
- [ ] 7일 윈도우 안 canonical URL 재등장 시 제외 (AC-4.2)
- [ ] 제목 fuzzy match `difflib.SequenceMatcher.ratio() >= 0.85`로 동일 기사 1건만 통과 (AC-4.3, threshold는 GlobalFilters에서 주입)
- [ ] `filters/category.py`가 복수 매칭 기사를 우선순위(`farmboss_keyword` > `agri_distribution` > `ai_trend`) 1곳에만 배정 (AC-2.2)
- [ ] `filters/pipeline.apply` 출력 type = `dict[CategoryId, list[Article]]`, 카테고리 3개 모두 키 존재 (0건이면 빈 list)
- [ ] `history.ArtifactBackend.load()`가 artifact 없을 때 빈 History 반환 + 로그에 "fresh-start" WARNING 한 줄
- [ ] `history.store.SentRecord`의 JSON serialize 결과가 requirements §6-4 스키마와 1:1 일치 (version: 1 포함)
- [ ] 알 수 없는 version의 SentRecord는 load 시 무시 + WARNING 한 줄 (RuntimeError 발생 금지)
- [ ] unit test 12건 이상: timewindow 경계 / keyword 매칭 / 카테고리 우선순위 / dedup URL hit / dedup URL miss / fuzzy threshold 경계 / fresh-start / SentRecord roundtrip / unknown version / pipeline 통합 / 7일 윈도우 / Source 비활성화

## 금지사항

- dedup 안에서 자체 URL 자르기 (CLAUDE.md anti-pattern A) — `url_helper.canonicalize` 호출 외에는 URL 손대지 않음
- summarizer·dispatcher 모듈 생성 금지
- `httpx` 추가 의존성 금지
- `sent.jsonl` 스키마 변경 시 version bump 없이 진행 금지 (점진 확장 원칙)
- artifact upload·download 코드를 본 step에 직접 작성 금지 (step7의 workflow 통합 책임)

## 수동 테스트 절차

1. fixture: 어제 보낸 URL 1개 + 오늘 raw 5개(그 중 1개가 어제 URL canonical 동일) → `pipeline.apply` 호출 → 4개만 통과
2. fixture: 두 기사 제목 fuzzy ratio 0.87 (같은 사건 다른 헤드) → 1건만 통과
3. fixture: 한 기사가 ai_trend + farmboss_keyword 모두 매칭 → farmboss_keyword에만 배정
4. fixture: artifact 없는 상태 → `ArtifactBackend.load()` → empty History + 로그 "fresh-start"
5. fixture: version=99 SentRecord → load 시 무시 + WARNING, 빈 history로 부팅
6. `pytest tests/test_filters.py tests/test_history.py` 12건 통과

## 수동 QA Owner

**`사용자` (qa_blocking)** — dedup 사고는 직원 신뢰를 즉시 깎는다. 사용자가 다음을 직접 확인:

- step 완료 직후 step4 산출물 코드 리뷰
- fixture 1·2를 사용자가 추가 1건 더 작성·실행해 직관 검증
- `sent.jsonl` 한 줄 sample을 사용자에게 보여주고 스키마 OK 확인

## 주 담당 에이전트

`tnb-implementer` — filter·dedup·history 도메인 로직. data contract 변경은 `tnb-data-steward` 협업.

## 회귀 위험

- fuzzy threshold 0.85가 false positive 만들면 다른 기사가 dedup으로 사라짐. dry-run 1주 후 보강 필요 (AC-4.3 명시).
- artifact upload 실패로 다음날 history 미반영 → 중복 발송. step7 workflow에서 `if: always()` 등으로 upload 보장 검토.
- `published_at_kst` naive datetime이 fuzzy/timewindow 비교에 들어오면 TypeError. step3에서 tz-aware 강제했지만 본 step에서 assert로 이중 방어.

## pending_manual_qa_scenarios 누적

- "step7 workflow 통합 후 첫 실행(artifact 없음)이 fresh-start로 부팅되고 두 번째 실행이 dedup 적용되는지 사용자 phase 끝 dry-run에서 확인"
- "fuzzy threshold 0.85 실측 — 1주일 dry-run 후 false positive/negative 분포 verification-record에 기록"
