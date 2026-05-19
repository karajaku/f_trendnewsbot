# 01-mvp-daily-digest

> 역할: V1 MVP — 매일 KST 07:30 자동 발송, 3카테고리(AI 트렌드·농산물 유통·팜보스 관심 키워드) 큐레이션 이메일 다이제스트 봇을 그린필드 상태에서 동작 가능한 상태까지 만든다.
> 대상: `tnb-phase-orchestrator` (계획), `tnb-implementer` / `tnb-data-steward` / `tnb-docs-keeper` (구현), `tnb-qa-reviewer` (QA), 사용자 (phase 끝 일괄 QA).

## 목표

저장소가 그린필드(코드 0)인 상태에서 출발해, V1 requirements의 AC-1~AC-7 모두를 충족하는 일일 다이제스트 봇을 GitHub Actions cron에서 자동 발송 가능한 상태로 완성한다.

phase 종료 시점에 다음이 가능해야 한다 (ADR-003 채널 갱신 반영):

1. GitHub Actions에서 `workflow_dispatch`로 dry-run 1회 발송 → 운영자 전용 단톡방에 텔레그램 메시지 도착 + GitHub Pages에 HTML 페이지 게시.
2. cron 자동 발송 1회 → 다이제스트 단톡방에 메시지, Pages URL 활성, history artifact 생성, dedup 적용.
3. 한 소스 일부러 죽이고 dry-run → 텔레그램 메시지·Pages 헤더에 "실패 X개: {소스명}" 노출, 발송은 계속.
4. Pages publish 실패 시뮬레이션 (git push 권한 박탈) → 텔레그램 직원 단톡방 발송 안 됨, 운영자 alert chat에만 alert.

## 범위

**포함:**

- 부트스트랩 — `pyproject.toml`, 폴더 구조, `lib/url_helper.py`, `lib/time_helper.py`, `lib/logging_setup.py`
- config 로딩 — `sources.yml`, `filters.yml` 스키마·로더 (V1은 `recipients.yml` 없음 — ADR-003)
- fetchers — `base.py`(인터페이스), `rss.py`, `html.py`, `json_api.py`, 소스 단위 격리
- filters — `timewindow.py`, `keyword.py`, `category.py`, `dedup.py`
- history backend — `store.py`, GitHub Actions artifact 다운로드·업로드
- summarizer — Anthropic SDK client, Prompt caching, hard cap, `prompts/summarize.md`, `render.py`(HTML + 텔레그램 인덱스 텍스트)
- dispatchers — `base.py`(인터페이스), `pages_publish.py`(`docs/digest/YYYY-MM-DD.html` commit·push + 게시 확인), `telegram_send.py`(Bot API sendMessage + 운영자 alert)
- `run_daily.py` 통합 (5단계 호출만, Pages publish → 텔레그램 발송 순서 강제)
- GitHub Actions workflow (`daily.yml` cron + `workflow_dispatch`) + Secrets 등록 가이드 + Pages 설정 가이드
- 1회 dry-run (운영자 단톡방·Pages URL 확인) + verification-record 작성

**제외:**

- 이메일 발송·Gmail SMTP·BCC 관리 (V1 제거, ADR-003)
- 슬랙·카카오워크·Teams·카카오톡 dispatcher (V2 이후)
- 사용자별 카테고리 가중치 (V2+)
- 웹 대시보드·검색 UI (V3)
- 한국 공휴일 자동 스킵 (V1·V2 모두 미적용 — 2026-05-19 사용자 결정, requirements AC-1.5)
- 점수·요약 분리 호출 (V2, requirements §3 결론 #2)
- 외부 KV store backend (Reject, ADR-002 §대안 D)
- private repo Pages (Reject, ADR-003 §대안 E — public + noindex로 충분)

## V1 발송 시작 단톡방 멤버 일정 (AC-6.4, 2026-05-19 사용자 결정, ADR-003 갱신)

| 시점 | 단톡방 멤버 | 운영자 액션 |
|---|---|---|
| Day 0~6 (1주차) | 운영자 본인만 | 단톡방 생성, 봇 초대, `TELEGRAM_CHAT_ID` 확인 |
| Day 7~13 (2주차) | 운영자 + 김종만·정은주·장석중 3이사 | 단톡방에 이사 3명 초대, 안내 메시지 1회 |
| Day 14+ | 전 직원 | 단톡방에 직원 일괄 초대 |

이 일정은 step8 verification-record에 시작일·초대 시각·실측 결과 기록. 이사진 검토 결과에 따라 단축·연장은 운영자 재량.

## Related Docs

추적 체인 연결 — 이 섹션이 없으면 추적 불가.

- [docs/features/daily_digest/daily_digest_v1-brief.md](../../docs/features/daily_digest/daily_digest_v1-brief.md) — 사용자/제품 요구사항 원본
- [docs/features/daily_digest/daily_digest_v1-discovery-research.md](../../docs/features/daily_digest/daily_digest_v1-discovery-research.md) — Stage 0 시사점
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) — Stage 3 시사점
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) — 기술 스펙, acceptance criteria, data contract
- [docs/features/daily_digest/design-review-daily_digest_v1-requirements.md](../../docs/features/daily_digest/design-review-daily_digest_v1-requirements.md) — Stage 4 자가 교차 검토 + 사용자 일괄 검토 대기 항목
- [docs/features/daily_digest/design-review-daily_digest_v1-brief.md](../../docs/features/daily_digest/design-review-daily_digest_v1-brief.md) — Stage 2 Concept 검토 결과 sibling

## 완료 기준

Phase DoD (`docs/canonical/DEV_PROCESS.md` Stage 8 참조):

- 모든 step status = completed
- `docs/canonical/PRD.md` 정시성 기준 갱신 (07:30 ± 15분 95%)
- `docs/canonical/ARCHITECTURE.md` 모듈 ownership 표 실제 코드 경로로 갱신 + 성능 기준선 실측 반영
- `docs/PHASE_MAP.md` phase status 동기화
- `phases/index.json` status = "completed", completed_at 기록
- `docs/history/daily_digest/daily_digest_v1-manual-verification-record.md` 생성 (Stage 7 "중요 기능" — 새 시스템 추가)
- `docs/implementation_status.md` 신규 시스템 등록
- `pending_manual_qa_scenarios` 일괄 보고 후 사용자 OK

## Step 목록

| Step | 범위 한 줄 요약 | 주 담당 에이전트 | qa_blocking | 상태 |
|---|---|---|---|---|
| step1 | 부트스트랩 — pyproject·폴더·lib helpers | tnb-implementer | false | pending |
| step2 | config 로딩 — sources/filters 스키마 (recipients.yml 폐기) | tnb-data-steward | false | pending |
| step3 | fetchers — RSS·HTML·JSON 어댑터 + 소스 격리 | tnb-implementer | false | pending |
| step4 | filters + history backend — dedup·timewindow·category + artifact 연동 | tnb-implementer | true | pending |
| step5 | summarizer — Claude SDK + prompt caching + hard cap + render (HTML + 텔레그램 인덱스) | tnb-implementer | false | pending |
| step6 | dispatchers — Pages publish + 텔레그램 Bot API + 운영자 alert chat (ADR-003) | tnb-implementer | false | pending |
| step7 | run_daily.py 통합 + GitHub Actions workflow (cron + Pages 권한) + Secrets 가이드 | tnb-implementer + tnb-docs-keeper | true | pending |
| step8 | dry-run + verification-record + canonical sync(PRD·ARCHITECTURE 갱신) | tnb-qa-reviewer + tnb-docs-keeper | true | pending |

`qa_blocking: true`인 step 3개:
- **step4** — dedup·history는 발송 이력의 신뢰원. 회귀 시 직원이 같은 기사를 두 번 받는 사고 발생. 사용자 수동 QA 필수.
- **step7** — `run_daily.py` 통합 + Secrets 설정은 통합 진입 파일·시크릿 두 가지 핵심 경로를 동시에 건드림. 회귀 복구 어려움.
- **step8** — dry-run·verification-record는 phase 전체의 사용자 일괄 QA 게이트. PRD 갱신 포함.

## 가드레일

- 코드 어디에도 시크릿 평문 노출 금지 (CLAUDE.md CRITICAL #5) — `TELEGRAM_BOT_TOKEN`·`ANTHROPIC_API_KEY` 등 모두 환경변수
- `run_daily.py` 본문에 도메인 규칙 누적 금지 — 5단계 호출만 (CLAUDE.md anti-pattern B)
- `url_helper.canonicalize` / `time_helper.to_kst_string`를 우회한 자체 정규화 코드 금지 (CLAUDE.md anti-pattern A)
- 한 소스 실패가 전체 발송을 막는 try/except 금지 (CLAUDE.md anti-pattern C)
- "why it matters" 류 LLM 코멘트 라인 생성 금지 (requirements §2)
- 첫 dry-run 전까지 직원 단톡방에 발송 금지 — 운영자 전용 단톡방으로만 (AC-6.4 Day 0~6)
- Pages 게시 성공 확인 없이 텔레그램 메시지 발송 금지 (AC-5.6 — URL 404 회피)
- Pages HTML에 사내 정보(시세·매출·인사) 게시 금지 — 본문은 외부 뉴스 큐레이션만 (Pages public + noindex)
- PRD·ARCHITECTURE 갱신은 step8에서 일괄(이전 step에서 canonical 문서 직접 수정 금지)
