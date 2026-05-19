# Step 3: fetchers — RSS·HTML·JSON 어댑터 + 소스 격리

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-5.1·AC-5.2 + §5 Resource flow

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) anti-pattern C (단일 try/except 금지)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-5.1, AC-5.2, §5 Resource flow loop
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §3-1 fetch 라이브러리
- step1 산출물: `lib/url_helper.canonicalize`, `lib/time_helper.parse_to_kst`
- step2 산출물: `config.loader`의 `Source` dataclass

## 작업 범위

- `src/fetchers/__init__.py` + 인터페이스 정의
- `src/fetchers/base.py` — `Fetcher` 추상 클래스 + `Article` dataclass
  - `Article(canonical_url, title, source_id, source_name, category, published_at_kst, snippet)`
  - `Fetcher.fetch(source: Source) -> list[Article]`
- `src/fetchers/rss.py` — feedparser 기반. published 시각은 KST 변환.
- `src/fetchers/html.py` — requests + bs4. selector는 `Source.tags`나 별도 필드로 향후 확장 (V1은 RSS 우선이라 사용 소스 최소화).
- `src/fetchers/json_api.py` — 일반 JSON API 어댑터. response 매핑은 hook 함수로 (V1은 1~2 소스만 사용).
- `src/fetchers/runner.py` — `run_all(sources: list[Source]) -> tuple[list[Article], list[Failure]]`
  - 소스 단위 try/except로 격리 (anti-pattern C 회피)
  - timeout 10초, retry 1회
  - `Failure(source_id, source_name, error_kind, error_message)` dataclass
- unit test: fetcher 인터페이스 mock + runner의 부분 실패 시나리오

## 영향받는 데이터 정의 목록

- 없음 (Article·Failure은 in-memory dataclass, sent.jsonl에는 다음 step에서 정의)

## Acceptance Criteria

- [ ] `fetchers.runner.run_all(sources)` 가 한 소스 예외 발생해도 다른 소스 fetch 계속, `tuple[list[Article], list[Failure]]` 반환 (AC-5.1)
- [ ] `Failure.error_kind` 가 `timeout`/`http_4xx`/`http_5xx`/`parse_error`/`other` 5종 중 하나
- [ ] `Article.canonical_url` 은 `lib/url_helper.canonicalize` 통과한 결과만 저장 (저장 시점 정규화)
- [ ] `Article.published_at_kst` 는 항상 tz-aware datetime (Asia/Seoul) — naive datetime 저장 금지
- [ ] `Article.source_name` 은 `Source.name` 그대로 (본문 출처 표기에 사용)
- [ ] RSS fetcher: feedparser 결과를 Article로 매핑, parser exception이 Failure로 변환되는 시나리오 unit test 통과
- [ ] HTML fetcher: requests timeout=10 (`requests.get(url, timeout=10)`), bs4로 본문 추출
- [ ] JSON API fetcher: response JSON 경로를 `Source` 필드로 받아 일반화
- [ ] runner unit test 6건: 정상 / 1개 timeout / 1개 4xx / 1개 5xx / 1개 parse_error / 전체 정상

## 금지사항

- 단일 try/except가 `for src in sources:` 전체를 감싸는 패턴 금지 (CLAUDE.md anti-pattern C) — qa-reviewer가 grep
- fetcher 안에서 dedup·필터 로직 실행 금지 (다음 step의 책임)
- fetcher 안에서 Claude API 호출 금지 (step5)
- `httpx` / `lxml` / `selectolax` 도입 금지 (V1 외)
- 동시 fetch (ThreadPoolExecutor 등) 도입 금지 (V1은 순차)

## 수동 테스트 절차

1. mock Source 4개 (rss/html/json/intentional_fail) 입력 → `run_all` 호출 → Failure 1건, Article 3건 이상 출력 확인
2. `pytest tests/test_fetchers.py` 모두 통과
3. (선택) 실제 RSS 1개 (`https://www.anthropic.com/news/rss.xml` 등)로 dry-run → Article 객체 정상 생성 확인

## 수동 QA Owner

`에이전트 정적 분석` — pytest와 mock 기반 검증으로 충분.

## 주 담당 에이전트

`tnb-implementer` — fetcher 도메인 로직.

## 회귀 위험

- fetcher가 raw URL을 그대로 Article.canonical_url에 저장하면 dedup이 작동 안 함. AC에 `canonicalize` 통과 명시했지만 step4 qa에서 재확인.
- `published_at_kst`가 naive 또는 UTC인 채로 다른 모듈로 흘러가면 시각 표기·dedup 윈도우 계산 모두 깨짐. tz-aware 강제는 type hint + runtime assert로 이중 방어.

## pending_manual_qa_scenarios 누적

- "실제 12~18개 소스 RSS feed 1회 fetch에서 published 시각이 모두 tz-aware KST로 변환되는지 step8 dry-run에서 시각 확인"
