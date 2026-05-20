# Step 1: 발송 건수 글로벌 상한 (score 상위 N건 컷)

> 추적: [phases/03-digest-item-cap/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.1

## 읽을 파일

- `CLAUDE.md` (anti-pattern A·B, 기획서 동기화 정책)
- `docs/canonical/DEV_PROCESS.md` Stage 6 (Step DoD), Stage 7 (기획서 동기화)
- `phases/03-digest-item-cap/README.md`
- `docs/features/daily_digest/daily_digest_v1-requirements.md` — AC-2.1, AC-2.10(score), AC-2.11(TL;DR), §5 Digest row 메타
- `docs/features/daily_digest/daily_digest_v1-brief.md` — §3 비-목표
- `config/filters.yml` — `global` 블록 현 구조 확인
- `src/config/loader.py` — `GlobalFilters` dataclass + `load_filters` 검증 흐름 확인
- `src/summarizer/render.py` — `build_digest`, `_build_rendered_items`, RenderedItem(score 보유 여부), TL;DR/item_count 산출 경로 확인
- `src/run_daily.py` — `build_digest` 호출 지점 확인
- `tests/` — render/loader 관련 테스트 존재 여부 확인 (`test_summarizer.py` 있음, `test_render`는 step에서 확인)

## 작업 범위

1. **config** — `config/filters.yml`의 `global` 블록에 `max_items: 10` 신설. 주석으로 "일일 발송 글로벌 상한 (score 상위 N건)" 명시.
2. **loader** — `src/config/loader.py`의 `GlobalFilters` dataclass에 `max_items: int` 필드 추가. `load_filters`에서 양의 정수 검증(`>= 1`, 아니면 명확한 에러). optional 처리 방침은 기존 `global` 블록 필드 default 패턴을 따른다.
3. **render** — `src/summarizer/render.py`에 `_select_top_items` helper 추가: RenderedItem 리스트를 score 내림차순으로 정렬해 상위 N건만 반환. 동점은 입력 순서 유지(stable sort). `build_digest`는 `_build_rendered_items` 직후 이 helper로 컷을 적용하고, 이후 item_count·TL;DR·HTML·텔레그램 텍스트 전부가 컷된 결과를 읽도록 한다. `build_digest` 시그니처에 `max_items: int` 파라미터 추가.
4. **run_daily** — `src/run_daily.py`의 `build_digest` 호출에 `max_items=filters.global_.max_items`(실제 필드 경로는 loader 확인 후) 전달. 위임 한 줄만 — 컷 로직을 run_daily 본문에 두지 않는다.
5. **기획서 동기화** — `daily_digest_v1-requirements.md` AC-2.1을 글로벌 상한으로 개정(아래 "기획서 동기화" 절), `daily_digest_v1-brief.md` §3 비-목표를 갱신. 두 문서 frontmatter `last_updated_at` + `## Changelog` 한 줄.
6. **테스트** — render 컷 동작 + loader `max_items` 검증 회귀 테스트 추가. 기존 `test_summarizer.py` mock 구조에 맞춰 작성하거나 신규 `test_render` 파일 (실제 `tests/` 구조 확인 후 결정).

## 영향받는 데이터 정의 목록

- `config/filters.yml` — `global` 블록에 `max_items` 신규 필드 (정적 설정, 저장 제외)
- `src/config/loader.py` `GlobalFilters` dataclass — `max_items: int` 신규 필드

## 기획서 동기화 (필수 — CLAUDE.md 정책)

AC-2.1 변경은 시스템 계약 변경이다. 다음을 같은 step에서 처리한다:

- **requirements.md AC-2.1**: "카테고리당 5~10건" → 글로벌 상한 반영. 예) "전체 발송 건수는 `filters.yml`의 `global.max_items`(기본 10)건을 상한으로 한다. score(AC-2.10 회사 영향 점수) 내림차순 글로벌 상위 N건만 발송하며, 카테고리별 최소 건수는 보장하지 않는다. 카테고리가 컷 결과 0건이면 '오늘 새 뉴스 없음' 표기." AC 끝에 `(2026-05-20 추가)` 표기.
- **brief.md §3 비-목표**: "카테고리당 11건 이상" 류 문구를 글로벌 상한 도입에 맞게 한 줄 갱신 (또는 "후속 phase 분리: `03-digest-item-cap` 참조" 추가).
- 두 문서 frontmatter `last_updated_at: "2026-05-20"`, `## Changelog`에 `- 2026-05-20: 일일 발송 건수 글로벌 상한 도입 (phase 03 — 운영자 피드백, AC-2.1 개정)` 한 줄.

## Acceptance Criteria

- [x] `config/filters.yml` `global` 블록에 `max_items: 10` 존재, 의미 주석 포함
- [x] `GlobalFilters` dataclass에 `max_items: int` 필드, `load_filters`가 양의 정수(`>= 1`) 검증 — 0·음수·비정수 입력 시 명확한 에러
- [x] `render.py`에 `_select_top_items` helper — score 내림차순, 동점 입력 순서 유지(stable), 상위 N건 반환
- [x] `build_digest`가 `_build_rendered_items` 직후 컷을 1회 적용, 이후 item_count·TL;DR·HTML·텔레그램 텍스트가 모두 컷된 동일 결과 사용 (표면 일관)
- [x] 후보 건수 ≤ `max_items`이면 전량 발송 (컷 무동작), 후보 0건이면 기존 "오늘 새 뉴스 없음" 분기 유지
- [x] `run_daily.py`가 `build_digest`에 `max_items` 전달 — run_daily 본문에 컷 로직 없음
- [x] requirements.md AC-2.1 개정 + brief §3 갱신 + 두 문서 frontmatter·Changelog 갱신
- [x] render 컷 동작 + loader `max_items` 검증 회귀 테스트 추가, 전체 테스트 통과
- [x] ruff / mypy 통과 (프로젝트 lint 기준)

## 금지사항

- 요약 전 컷으로 변경 금지 — 요약 후 score 기준 컷 동결 (README 설계 결정)
- dispatcher·TL;DR·item_count에 자체 컷 코드 추가 금지 — `_select_top_items` 단일 helper만 (anti-pattern A)
- `run_daily.py` 본문에 컷 규칙 누적 금지 — `build_digest` 인자 전달만 (anti-pattern B)
- `max_items` 하드코딩 금지 — `filters.yml` + loader 검증 통과 값만
- 카테고리별 최소 건수 보장 로직 추가 금지 (범위 외)
- `filters/pipeline.py`·`summarizer/client.py` 입력 cap 변경 금지 (범위 외)
- 소스·키워드 목록 재조정 금지 (별개 작업)

## 수동 테스트 절차

> 핵심 경로(golden path)와 경계 조건.

1. **컷 동작**: 후보 기사 약 45건 상태로 `run_daily.py` dry-run → 텔레그램 메시지·Pages HTML·item_count가 모두 ≤ 10건인지 확인. 발송된 항목이 score 상위 N건인지(Pages HTML의 ⭐ 표시로 검증).
2. **경계 — 후보 ≤ N**: 후보가 max_items 이하인 날 (또는 fixture) → 컷이 무동작, 전량 발송.
3. **경계 — 후보 0건**: 모든 카테고리 0건 → 기존 "오늘 새 뉴스 없음" 표기 정상.
4. **설정 검증**: `filters.yml`의 `global.max_items`를 0 또는 음수로 바꿔 loader 실행 → 명확한 에러로 즉시 중단.
5. **표면 일관**: 텔레그램 "외 N건" 표기·TL;DR 추출·Pages 카테고리 헤더가 모두 컷 후 결과 기준인지 cross-check.

## 수동 QA Owner

`둘 다` — 에이전트 정적 분석으로 컷 helper·loader 검증·표면 일관 코드 inspection·테스트 통과를 확인하고 step status를 `completed`로 전환한다. 실발송 건수 육안 확인(텔레그램 메시지/Pages가 실제로 ~10건으로 줄었는지, score 상위가 맞는지)은 정적으로 단정 불가 → phase index.json `pending_manual_qa_scenarios`에 누적 후 phase 끝 사용자 일괄 QA.

## 주 담당 에이전트

`tnb-implementer` — 도메인 로직(render 컷) + 데이터(filters.yml·loader) 혼합 step. data 항목(`filters.yml` 신규 필드·`GlobalFilters` dataclass)은 별도로 점검한다. 표시 컷이라 UI 전용 계산 분리 금지(CLAUDE.md).

## 회귀 위험

- `build_digest` 시그니처 변경 → 모든 호출부(run_daily, 테스트) 동기화 필요. 호출부 누락 시 즉시 에러로 드러남.
- TL;DR(AC-2.11)은 ⭐⭐⭐ 항목을 추출한다. 컷이 ⭐⭐⭐ 항목을 잘라내면 TL;DR이 줄어들 수 있음 — 의도된 동작(컷 후 결과 기준)이나, 컷 순서가 TL;DR 추출보다 앞서는지 확인.
- 카테고리 헤드라인(AC-2.12)·"외 N건" 표기가 컷 전 카운트를 쓰면 표면 불일치 — 컷 후 결과만 읽는지 점검.
- `GlobalFilters`에 기존 다른 필드가 있으면 default 처리 패턴 일관성 유지.

## pending_manual_qa_scenarios 누적 (phase 끝 일괄 QA 입력)

본 step에서 다음 시나리오를 phase index.json `pending_manual_qa_scenarios`에 누적한다:

- "dry-run 또는 실발송 1회 → 텔레그램 메시지·Pages HTML 발송 건수가 실제로 ~10건(≤ max_items)으로 줄었는지 육안 확인"
- "발송된 ~10건이 score 상위(⭐⭐⭐/⭐⭐ 우선)인지, 중요 뉴스가 컷에서 누락되지 않았는지 운영자 체감 확인"
- "TL;DR 박스·카테고리 헤더·'외 N건' 표기가 컷 후 건수와 일관되는지 확인"

---

## Step DoD 체크 (에이전트 확인용)

```
☑ acceptance criteria 전부 충족
☑ 수동 테스트 목록 기준으로 핵심 경로 회귀 없음 확인 (정적 inspection)
☑ 새 visible text 없음 — 컷은 기존 항목 수만 줄임 (해당 없음)
☑ save/저장 계약 변경 없음 — filters.yml은 정적 설정
☑ 새 루프/전체 스캔: _select_top_items의 정렬은 후보 N건(≤45) 대상 — budget 무관, 명시
☑ 새 데이터 필드 max_items → 정적(저장 제외) 설정으로 명시
☑ 시스템 계약 변경(AC-2.1) → requirements.md·brief 갱신 완료, validate_*.ps1 해당 없음(설정 스키마 validator 없으면)
☑ phases/03-digest-item-cap/index.json step1 status → completed (정적 검증 통과 시)
☑ pending_manual_qa_scenarios에 실발송 건수 육안 확인 시나리오 누적
```
