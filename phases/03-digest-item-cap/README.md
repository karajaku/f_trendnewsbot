# 03-digest-item-cap

> 역할: 매일 다이제스트 발송 건수를 ~45건에서 하루 ~10건(중요도 상위)으로 제한한다. score 기준 글로벌 top-N 컷을 `render.build_digest`에 한 번 적용해 모든 표면(텔레그램·Pages·TL;DR·item_count)을 동일하게 줄인다.
> 대상: `tnb-phase-orchestrator` (계획), `tnb-implementer` (구현, data 항목 별도 확인), `tnb-qa-reviewer` (정적 검토), 사용자 (phase 끝 실발송 건수 육안 QA).

## 배경

2026-05-20 소스·키워드 운영 보강(`phases/_hotfix-log/2026-05-20-sources-keywords-expansion.md`)으로 ai_trend enabled 소스가 4→8개, 카테고리 키워드가 약 2배 확장되면서 일일 다이제스트가 ~45건으로 늘었다. 그 hotfix-log의 "후속" 3번 항목이 이미 "후보 기사 2배 → quota/비용 재검토"를 예측했다. 운영자 피드백("뉴스 45건은 너무 많아 주요 뉴스로 줄일 필요가 있어 하루 10건이면 충분")에 따라 발송 건수 상한을 도입한다.

현재 코드에는 건수 상한이 전혀 없다 — `src/filters/pipeline.py`(timewindow→keyword→category→dedup)에 컷이 없고, `src/summarizer/render.py`의 `build_digest`에도 상한이 없어 dedup 통과 전량이 발송된다.

## 목표

- `config/filters.yml`의 `global` 블록에 `max_items` 설정(기본 10) 신설.
- score 내림차순 글로벌 상위 N건만 발송하는 컷을 `render.build_digest` 안 `_build_rendered_items` 직후에 적용.
- item_count·TL;DR·HTML·텔레그램 메시지가 모두 같은 컷 결과를 읽어 전 표면 일관(CLAUDE.md CRITICAL #2).
- 시스템 계약(AC-2.1 "카테고리당 5~10건" → 글로벌 상한)을 requirements.md·brief §3 비-목표와 동기화.

## 범위

**포함:**

- `config/filters.yml` — `global.max_items` 신설
- `src/config/loader.py` — `GlobalFilters` dataclass에 `max_items` 필드 + `load_filters` 검증(양의 정수)
- `src/summarizer/render.py` — `_select_top_items` helper 추가, `build_digest`가 `_build_rendered_items` 직후 글로벌 top-N 컷 적용. `build_digest` 시그니처에 `max_items` 파라미터 추가
- `src/run_daily.py` — `build_digest` 호출에 `max_items` 전달 (위임 한 줄, 본문 규칙 누적 아님)
- `docs/features/daily_digest/daily_digest_v1-requirements.md` — AC-2.1 개정 + Changelog + frontmatter `last_updated_at`
- `docs/features/daily_digest/daily_digest_v1-brief.md` — §3 비-목표 한 줄 갱신 + Changelog + frontmatter `last_updated_at`
- 테스트 — render/loader 회귀 (현재 `tests/`에 `test_render`는 없고 `test_summarizer.py` 존재 — step에서 실제 경로 확인 후 컷 동작 테스트 추가)

**제외:**

- 요약 전 컷 (요약 후 컷 채택 — 사유: 중요도 신호는 LLM score뿐, 요약 전 컷은 최신순만 가능. Gemini 일일 hard cap(AC-5.5 입력 10만 토큰)은 45건도 여유 → 요약 후 컷이 안전·정확)
- 카테고리별 최소 건수 보장 (글로벌 top-N만, 카테고리 0건이면 AC-2.1의 "오늘 새 뉴스 없음" 기존 분기 사용)
- `filters/pipeline.py`·`summarizer/client.py` 입력 cap 변경
- 소스·키워드 목록 재조정 (별개 작업)
- 발송 채널·dispatcher 변경

## 설계 결정

- **컷 위치**: `render.build_digest` 안 `_build_rendered_items` 직후. RenderedItem이 score를 보유하므로 이 시점에 글로벌 정렬·컷이 가능하다. 컷 한 번이면 item_count·TL;DR·HTML·텔레그램이 모두 같은 `rendered` dict를 읽어 전 표면 일관(CLAUDE.md anti-pattern A 회피).
- **선택 규칙**: 글로벌 top-N by score 내림차순. 동점은 입력 순서 유지(stable sort). 카테고리별 최소 보장 없음.
- **설정값**: `config/filters.yml`의 `global.max_items` (기본 10). `load_filters`가 양의 정수 검증.

## Related Docs

추적 체인 연결 — 이 섹션이 없으면 추적 불가.

- [docs/features/daily_digest/daily_digest_v1-brief.md](../../docs/features/daily_digest/daily_digest_v1-brief.md) — 사용자/제품 요구사항 원본 (§3 비-목표 갱신 대상)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) — 기술 스펙, AC-2.1 개정 대상
- [phases/_hotfix-log/2026-05-20-sources-keywords-expansion.md](../_hotfix-log/2026-05-20-sources-keywords-expansion.md) — 45건 직접 원인, "후속" 3번 항목이 본 phase를 예측

## 완료 기준

Phase DoD (`docs/canonical/DEV_PROCESS.md` Stage 8 참조):

- 모든 step status = completed
- `daily_digest_v1-requirements.md` AC-2.1 개정 + Changelog + frontmatter 갱신
- `daily_digest_v1-brief.md` §3 비-목표 갱신 + Changelog + frontmatter 갱신
- `docs/implementation_status.md` 해당 시스템 행 갱신 (tnb-docs-keeper 위임)
- `docs/PHASE_MAP.md` phase 03 행 추가 (tnb-docs-keeper 위임)
- `phases/index.json` status = "completed", completed_at 기록
- `pending_manual_qa_scenarios` 일괄 보고 후 사용자 OK (실발송 건수 육안 확인)

## Step 목록

| Step | 범위 한 줄 요약 | 주 담당 에이전트 | qa_blocking | 상태 |
|---|---|---|---|---|
| step1 | filters.yml `global.max_items` 신설 + loader 검증 + render 글로벌 top-N 컷 + run_daily 위임 + 기획서 동기화 + 회귀 테스트 | tnb-implementer (data 항목 별도 확인) | false | pending |

`qa_blocking` 불필요 사유: 본 phase는 save 계약·core 경로·통합 진입 파일 본문을 건드리지 않는다. `run_daily.py`는 `build_digest` 호출 인자 한 줄만 추가(위임), 컷 로직 전부는 `render.py` 모듈 내부. render 표시 경로만 변경되므로 회귀 복구가 어렵지 않다. 실발송 건수 육안 확인은 phase 끝 일괄 QA(`pending_manual_qa_scenarios`)로 처리.

## 가드레일

- 표시 컷은 단일 helper(`_select_top_items`)로만 적용 — dispatcher·TL;DR·item_count가 자체 컷 코드를 두지 않는다 (CLAUDE.md anti-pattern A)
- `run_daily.py` 본문에 컷 규칙 누적 금지 — `build_digest`에 `max_items` 전달만 (CLAUDE.md anti-pattern B)
- `max_items`는 설정 파일·loader 검증을 통과한 값만 사용 — 하드코딩 금지
- 요약 전 컷으로 변경 금지 (요약 후 score 기준 컷 동결 — 위 설계 결정)
- AC-2.1 변경은 requirements.md 본문 + Changelog + frontmatter를 함께 갱신 (CLAUDE.md 기획서 동기화 정책)
- 기존 "오늘 새 뉴스 없음" 0건 분기 보존 — 컷이 0건을 만들어도 기존 분기로 처리
