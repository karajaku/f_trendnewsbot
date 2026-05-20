# 죽은 외부 소스 7개 `enabled: false` 처리 — 매일 발송 본문의 "소스 7개 실패" 노이즈 제거

날짜: 2026-05-20
규모: 핫픽스 (1 config 파일, 계약 변경 없음)

## 증상

운영자 보고 (2026-05-20):

> 소스 14개 중 7개 정상, 7개 실패: Anthropic Blog, 농민신문, aT KAMIS 보도, GS리테일 IR, 농민신문 농촌경제, 청도군 보도, 안동농협공판장. 소스 실패는 항상 똑같은데 원인파악해서 해결해보자.

매일 다이제스트 본문 메타 헤더(AC-5.2)에 동일 7개 소스가 반복 노출. 코드 회귀가 아니라 외부 시드 URL 의 운영 검증이 step3 dry-run 시점에 충분히 이뤄지지 않은 채 `enabled: true` 로 동결된 결과.

## 원인

소스별 직접 응답 확인 (curl --max-time 10~20, browser UA 포함):

| source_id | type | 응답 | 분류 |
|---|---|---|---|
| `anthropic_blog` | rss | HTTP 404 (`/rss.xml`·`/feed.xml`·`/news/rss` 모두 404) | URL dead — Anthropic 공식 RSS 미제공 (DIYgod/RSSHub#18943 동일 호소) |
| `nongmin_news` | rss | HTTP 200 + body **1바이트** (Transfer-Encoding: chunked → 11바이트 data만 송신) | 서버측 RSS 무력화 |
| `nongmin_rural_economy` | rss | 동일 (같은 서버) | 동일 |
| `at_kamis` | rss | TCP 응답 없음, 20초+ timeout | endpoint dead |
| `gs_retail_ir` | html | `HtmlFetcher` V1 stub → `NotImplementedError` | V1 의도된 stub (`src/fetchers/html.py:39`) |
| `cheongdo_gov` | html | 동일 | 동일 |
| `andong_nh_market` | html | 동일 | 동일 |

`src/fetchers/runner.py` 의 소스 단위 격리(AC-5.1)는 정상 동작 중이며, `_classify_exception` 5종 분류도 정확. **코드 버그는 0건**. 매일 7건의 Failure 가 발생하는 것이 사용자 입장에서는 노이즈이므로 외부 의존이 복구될 때까지 disable 처리한다.

farmboss_keyword 카테고리는 소스가 1개(`thinkfood_farmboss`)만 남지만, `src/filters/category.py:33` 의 좁은-카테고리 우선 재배정이 다른 RSS 본문에서 "청도"·"GS리테일"·"복숭아"·"안동농협공판장" 등 키워드를 매칭해 자동 흡수하므로 카테고리가 비는 위험은 작음.

## 변경

- `config/sources.yml:11-15, 53-90, 95-127` — 죽은 7개 source 의 `enabled: true` → `false`. 각 항목 위에 disable 일자·사유·V2 복구 조건 코멘트 한 묶음 추가.
- `config/sources.yml:8-17` — 파일 헤더에 2026-05-20 운영 현황 박스(enabled 7 / disabled 7) 추가. 본 hotfix-log 경로를 참조로 박음.

코드(`src/`) 변경 없음. `sources.yml` 의 entry 수·id·name·category·type·time_window_hours 모두 보존 — `history/sent.jsonl` 의 `source_id` 호환성 유지(과거 발송분 dedup 정상).

## 수동 확인

- [ ] `python -m pytest -q` — 회귀 0건 (테스트는 `12 <= len(sources) <= 18` 만 검증, enabled 카운트 보지 않음. 14개 entry 보존 확인.)
- [ ] `python -m ruff check src/` — config 변경이라 영향 없지만 안전망.
- [ ] 다음 발송 본문 메타 헤더가 "소스 7개 정상 수집" (실패 0건) 으로 바뀌는지 확인.
- [ ] farmboss_keyword 카테고리에 기사가 0건일 경우 운영자 검토 후 키워드 보강 또는 V2 HtmlFetcher 작업 우선순위 조정.

## 회귀 위험

- **카테고리 풀 감소**: ai_trend 5→4, agri_distribution 5→2, farmboss_keyword 4→1. `category.py` 재배정으로 흡수 가능하지만 dry-run 1~2주 모니터링 후 부족하면 키워드(`config/filters.yml`) 보강 또는 V2 우선순위 재조정.
- **dedup 호환성**: id·source_name 무변경이라 영향 없음.
- **summarizer quota**: 입력 article 수 감소로 토큰 사용량은 줄어드는 방향. hard cap 무관.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음 (entry 수 14 유지, 스키마 무변경).
- [x] 공개 함수 시그니처 변경 없음 (코드 무변경).
- [x] save/저장 구조 변경 없음 (`history/sent.jsonl` 스키마·source_id 호환).
- [x] 모듈 경계 변경 없음.

## 후속 (V2 또는 별도 phase)

1. `HtmlFetcher` 구현 (per-source CSS selector 매핑 또는 readability 기반) — `gs_retail_ir`·`cheongdo_gov`·`andong_nh_market` 복구.
2. `at_kamis` 는 RSS 가 아니라 KAMIS Open-API (json_api) 로 전환 검토. `src/fetchers/json_api.py` 가 stub 인지 확인 필요.
3. `anthropic_blog`·`nongmin_*` 는 공식 RSS 가 복구되거나 신뢰할 만한 미러가 확인되기 전까지 disable 유지.
4. `docs/features/daily_digest/daily_digest_v1-requirements.md §6-1` 의 example sources 두 줄(anthropic_blog·nongmin_news)을 disable 사례로 갱신할지 검토 — 단, requirements 는 `frozen` 이므로 변경 시 별도 phase 필요.
