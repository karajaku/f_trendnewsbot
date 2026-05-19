# {phase-name}

> 역할: {이 phase가 달성하려는 것 — 한 줄}
> 대상: `tnb-phase-orchestrator` (계획), 구현 에이전트, `tnb-qa-reviewer` (QA)

## 목표

{이 phase에서 완료해야 하는 것}

## 범위

**포함:**

- {포함 항목 1}
- {포함 항목 2}

**제외:**

- {제외 항목 1}

## Related Docs

추적 체인 연결 — 이 섹션이 없으면 추적 불가.

- `docs/features/{group}/{feature}-brief.md` — 사용자/제품 요구사항 원본
- `docs/features/{group}/{feature}-requirements.md` — 기술 스펙, acceptance criteria, data contract

## 완료 기준

Phase DoD (`docs/canonical/DEV_PROCESS.md` Stage 6 참조):

- 모든 step status = completed
- `docs/implementation_status.md` 해당 시스템 행 갱신
- `docs/PHASE_MAP.md` phase status 동기화
- `phases/index.json` status = "completed", completed_at 기록
- (데이터 정의 추가/변경 시) 관련 system map 동기화

## Step 목록

| Step | 범위 한 줄 요약 | 주 담당 에이전트 | 상태 |
|---|---|---|---|
| step0 | {요약} | tnb-{agent} | pending |

## 가드레일

- {이 phase에서 절대 하지 않는 것 1}
- {이 phase에서 절대 하지 않는 것 2}
