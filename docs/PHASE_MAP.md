# Phase Map

> 역할: 모든 phase의 라이프사이클(계획·진행·완료·아카이브)을 사람 시야에서 한 페이지로 정리한다. `phases/index.json`이 코드용 source of truth이고 이 문서는 사람용 요약.
> 대상: Stage 5 phase 계획 작성자, 사용자 진행 상황 점검, 신규 합류자 onboarding.

작성일: 2026-05-19

---

## 활성 / 대기 Phase

| ID | dir | feature_group | status | 핵심 산출물 | related_docs |
|---|---|---|---|---|---|
| 01 | [01-mvp-daily-digest](../phases/01-mvp-daily-digest/) | `daily_digest` | pending | V1 매일 다이제스트 봇 (8 step) | [brief](features/daily_digest/daily_digest_v1-brief.md) · [discovery](features/daily_digest/daily_digest_v1-discovery-research.md) · [tech](features/daily_digest/daily_digest_v1-tech-research.md) · [requirements](features/daily_digest/daily_digest_v1-requirements.md) · [design-review](features/daily_digest/daily_digest_v1-design-review.md) |

## 완료 Phase

(없음 — 첫 phase는 01-mvp-daily-digest 진행 시점)

## Archived Phase

(없음)

---

## Phase 라이프사이클

```
pending  ─▶  in_progress  ─▶  implemented_pending_manual_qa (선택)  ─▶  completed
           │                                                          │
           ↓                                                          ↓
        paused (사용자 명시 시)                                   archived (archive_target=true 시)
```

`status` 변경 시 반드시 `phases/index.json` 동기화. 본 PHASE_MAP은 `phases/index.json` 변경 후 행 업데이트.

## Phase 별 step 상세

각 phase의 step 목록·acceptance·진행은 `phases/{dir}/README.md` + `phases/{dir}/index.json` 참조.

### 01-mvp-daily-digest (V1)

| step | summary | qa_blocking | status |
|---|---|---|---|
| 1 | 부트스트랩 — pyproject·폴더·lib helpers | false | pending |
| 2 | config 로딩 — sources/filters/recipients 스키마 | false | pending |
| 3 | fetchers — RSS·HTML·JSON 어댑터 + 소스 격리 | false | pending |
| 4 | filters + history backend (artifact 연동) | **true** | pending |
| 5 | summarizer — Claude SDK·prompt caching·hard cap·render | false | pending |
| 6 | dispatchers — Gmail SMTP + BCC + 운영자 alert | false | pending |
| 7 | run_daily 통합 + GitHub Actions workflow + Secrets 가이드 | **true** | pending |
| 8 | dry-run + verification-record + canonical sync | **true** | pending |

`qa_blocking: true` 3개 step만 사용자 수동 QA 후 다음 step 진입. 나머지는 에이전트 정적 검증 통과 시 자동 진행 (CLAUDE.md "QA cadence" 기본값).
