# f_trendnewsbot Document Map

작성일: 2026-05-19

## 역할

이 문서는 `f_trendnewsbot` 문서 지형을 빠르게 고르는 상위 지도다. 긴 설명은 원문 문서에 맡기고, Claude가 다음에 읽을 파일을 적은 토큰으로 선택하게 하는 것이 목적이다.

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
| `docs/PHASE_MAP.md` | 사람용 phase 라이프사이클 요약 | 진행 상황 점검·onboarding |
| `docs/design_review_questions.md` | Stage 2 Concept 검토 결과 누적 | Stage 4 requirements 진입 직전 충돌 확인 |

## Canonical Contracts

항상 최신 기준으로 우선 신뢰하는 문서다.

| 파일 | 소유 내용 |
| --- | --- |
| `docs/canonical/PRD.md` | 제품 목표, MVP 범위, 성공 기준 |
| `docs/canonical/ARCHITECTURE.md` | 시스템 구조, ownership, 데이터/UI/save/performance 구조 |
| `docs/canonical/ADR.md` | 장기 의사결정 |
| `docs/canonical/DEV_PROCESS.md` | 개발 프로세스 단일 정의 — 7단계 흐름, 산출물, DoD, 추적 체인 |

## Feature Groups

| Group id | 소유 범위 | 폴더 |
| --- | --- | --- |
| `daily_digest` | V1 매일 1회 다이제스트 전체 흐름(fetcher → filter → summarizer → dispatcher → history)을 묶는 우산 그룹. V1 brief·tech-research·requirements가 모두 이 그룹에 위치. | `docs/features/daily_digest/` |
| `fetchers` | 외부 소스(RSS·HTML·JSON API)에서 raw article 수집. 소스 단위 격리. (V2 분리 시 사용) | `docs/features/fetchers/` |
| `filters` | 시간 윈도우·키워드·dedup 필터. 발송 이력과 dedup 정확도 책임. | `docs/features/filters/` |
| `summarizer` | Claude API 호출, 카테고리별 점수·요약, 다이제스트 본문 렌더. | `docs/features/summarizer/` |
| `dispatchers` | 채널별 발송 (V1 Gmail SMTP, 향후 메신저). 수신자 관리. | `docs/features/dispatchers/` |
| `history` | 발송 이력 영속화·조회. dedup의 신뢰원. | `docs/features/history/` |
| `ops` | GitHub Actions cron·시크릿·운영 비용·관측. | `docs/features/ops/` |

각 그룹 폴더는 첫 phase가 해당 그룹을 건드릴 때 생성한다. 그룹 폴더가 생기면 아래에 해당 그룹의 문서 목록 표를 추가한다.

### `daily_digest` 그룹 문서

| 파일 | 역할 | 상태 |
| --- | --- | --- |
| `daily_digest_v1-discovery-research.md` | Stage 0 외부 레퍼런스·코드베이스 개괄 | draft → applied (brief 인용 후) |
| `daily_digest_v1-brief.md` | Stage 1 V1 브리프 (배경·UX·핵심 규칙) | draft → applied (requirements 인용 후) → frozen (Stage 5) |
| `daily_digest_v1-tech-research.md` | Stage 3 코드/외부 API 깊이 조사 | draft → applied (requirements 인용 후) |
| `daily_digest_v1-requirements.md` | Stage 4 acceptance criteria · data contract | draft → reviewed → applied → frozen |
| `design-review-daily_digest_v1-requirements.md` | Stage 4 자가 교차 검토 보고 (requirements sibling) | reviewed |
| `design-review-daily_digest_v1-brief.md` | Stage 2 Concept 검토 sibling (brief 대응) | reviewed |

## 회사 도메인 문서

뉴스봇 코드 외에 팜보스 회사 자체 문서가 같은 저장소에 공존한다. 필터 키워드·관심 산지·조직 이해에 직결되므로 PRD·필터 설계 시 참조한다.

| 파일 | 역할 |
| --- | --- |
| `docs/팜보스_회사소개.md` | 3법인 구조·핵심 인물·주요 산지·경영 철학 요약 (회사 정체성 우선 읽기) |
| `docs/_extracted/` | 직원 업무 가이드 텍스트 사본 (검색용) |
| `docs/f-공통직원업무매뉴얼/` | 원본 .docx 모음 (수정 금지) |

## Execution And Agent Docs

| 파일 | 역할 |
| --- | --- |
| `.claude/agents/tnb-*.md` | Claude Code 서브에이전트 등록 파일 (source of truth) |
| `phases/index.json` | phase 라우팅 source of truth |

## 작업별 빠른 라우팅

| 작업 유형 | 먼저 읽을 지도 | 다음 파일 |
| --- | --- | --- |
| phase 이어받기 | `docs/AGENT_READ_ORDER.md`, `docs/PHASE_MAP.md` | `phases/index.json`, 대상 phase README/index/step |
| 코드 구현 | `docs/canonical/ARCHITECTURE.md`, 관련 system map | 관련 requirements + 실제 코드 owner |
| 데이터 변경 | `docs/DATA_MAP.md` (있는 경우) | 관련 data 파일 + loader 코드 |
| 문서 작업 | `docs/canonical/` 3종 | `phases/index.json` |
| sub-agent 위임 | `.claude/agents/tnb-*.md` | — |
