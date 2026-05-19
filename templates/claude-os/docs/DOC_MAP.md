# {{PROJECT_NAME}} Document Map

작성일: {{TODAY}}

## 역할

이 문서는 `{{PROJECT_NAME}}` 문서 지형을 빠르게 고르는 상위 지도다. 긴 설명은 원문 문서에 맡기고, Claude가 다음에 읽을 파일을 적은 토큰으로 선택하게 하는 것이 목적이다.

## 역할 판정표

문서를 고를 때는 파일 이름보다 아래 역할을 먼저 본다.

| 역할 | 의미 | 우선 읽기 상황 |
| --- | --- | --- |
| Entry | 작업 시작점과 라우팅 | 모든 작업의 첫 탐색 |
| Canonical Contract | 현재 제품/아키텍처/장기 결정 기준 | 큰 설계, 새 시스템, 규칙 변경 |
| System Map | 구현 owner, 데이터 owner, UI/layout owner 지도 | 실제 코드/데이터 위치를 좁힐 때 |
| Feature Requirements | 기능별 acceptance, 데이터 계약, UI 표면, 저장/로드 기준 | 기능 구현이나 검증 범위 결정 |
| Execution Ledger | phase 상태, step 범위, 완료/차단 기록 | phase 이어받기 |
| Historical Evidence | 과거 preflight, checklist, manual record, completion ledger | 당시 검증 근거를 확인할 때 |

## 기본 입구

| 파일 | 역할 | 언제 읽나 |
| --- | --- | --- |
| `CLAUDE.md` | 프로젝트 작업 규칙, 안전 규칙, 도메인 제약 | 항상 처음 |
| `docs/DOC_MAP.md` | 에이전트용 짧은 문서 지도 | 문서 탐색 시작점 |
| `docs/DOC_GUIDE.md` | 문서 시스템 구조·계층·활용법 설명서 | 처음 합류 또는 문서 체계 파악 필요 시 |
| `docs/AGENT_READ_ORDER.md` | 작업 유형별 최소 읽기 순서 | Claude prompt 구성 |
| `phases/index.json` | phase 라우팅 source of truth | 이어받기/다음 단계 판단 |

## Canonical Contracts

항상 최신 기준으로 우선 신뢰하는 문서다.

| 파일 | 소유 내용 |
| --- | --- |
| `docs/canonical/PRD.md` | 제품 목표, MVP 범위, 성공 기준 |
| `docs/canonical/ARCHITECTURE.md` | 시스템 구조, ownership, 데이터/UI/save/performance 구조 |
| `docs/canonical/ADR.md` | 장기 의사결정 |
| `docs/canonical/DEV_PROCESS.md` | 개발 프로세스 단일 정의 — 7단계 흐름, 산출물, DoD, 추적 체인 |

## Feature Groups

> setup 후 새 프로젝트의 도메인 그룹을 여기에 정의한다. 아래는 예시 행 — 실제 사용 전 도메인에 맞게 교체한다.

| Group id | 소유 범위 | 폴더 |
| --- | --- | --- |
| `{group-1}` | {도메인 1의 책임 범위} | `docs/features/{group-1}/` |
| `{group-2}` | {도메인 2의 책임 범위} | `docs/features/{group-2}/` |

각 그룹 폴더가 만들어지면 아래에 해당 그룹의 문서 목록 표를 추가한다.

## Execution And Agent Docs

| 파일 | 역할 |
| --- | --- |
| `.claude/agents/{{AGENT_PREFIX}}-*.md` | Claude Code 서브에이전트 등록 파일 (source of truth) |
| `phases/index.json` | phase 라우팅 source of truth |

## 작업별 빠른 라우팅

| 작업 유형 | 먼저 읽을 지도 | 다음 파일 |
| --- | --- | --- |
| phase 이어받기 | `docs/AGENT_READ_ORDER.md`, `docs/PHASE_MAP.md` | `phases/index.json`, 대상 phase README/index/step |
| 코드 구현 | `docs/canonical/ARCHITECTURE.md`, 관련 system map | 관련 requirements + 실제 코드 owner |
| 데이터 변경 | `docs/DATA_MAP.md` (있는 경우) | 관련 data 파일 + loader 코드 |
| 문서 작업 | `docs/canonical/` 3종 | `phases/index.json` |
| sub-agent 위임 | `.claude/agents/{{AGENT_PREFIX}}-*.md` | — |
