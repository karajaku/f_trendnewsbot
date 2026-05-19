# Agent Read Order

작성일: 2026-05-19

## 역할

이 문서는 Claude가 작업 시작 전에 읽을 최소 파일 순서를 정한다. 목표는 전체 `docs/`를 한 번에 읽지 않고, entry → canonical → map → active work 순서로 좁히는 것이다.

## 공통 규칙

- 항상 `CLAUDE.md`를 먼저 읽는다.
- 기본 탐색은 `docs/DOC_MAP.md`와 작업별 map 문서에서 시작한다.
- phase 이어받기는 `phases/index.json`을 source of truth로 둔다.
- 오래된 preflight/checklist/manual record는 현재 계약이 아니라 검증 증거로 취급한다.
- step 파일에 명시된 파일이 있으면 그 목록을 우선한다.

## 기본 시작

```text
1. CLAUDE.md
2. docs/DOC_MAP.md
3. 작업 유형별 섹션으로 이동 (아래 Feature Group / Phase Continuation 등)
```

canonical docs(`PRD.md`, `ARCHITECTURE.md`, `ADR.md`)는 새 시스템 추가·아키텍처 결정·설계 충돌 확인 시만 읽는다. 기존 코드 수정·버그 수정·phase 이어받기에서는 생략한다.

## Phase Continuation

```text
1. CLAUDE.md
2. docs/DOC_MAP.md
3. docs/PHASE_MAP.md
4. phases/index.json
5. phases/{target-phase}/README.md
6. phases/{target-phase}/index.json
7. phases/{target-phase}/stepN.md
8. stepN.md에 명시된 docs/code/data
```

주의:

- `paused` phase는 사용자가 명시적으로 재개를 요청했을 때만 진행한다.
- top-level `phases/index.json`과 phase별 `index.json`이 충돌하면 top-level ledger를 우선하고, 충돌 사실을 보고한다.
- manual QA pending 상태는 완료로 바꾸지 않는다.

## Code Implementation

```text
1. CLAUDE.md
2. docs/DOC_MAP.md
3. docs/canonical/ARCHITECTURE.md
4. 관련 system map (docs/system-maps/)
5. 관련 requirements (docs/features/{group}/)
6. 검색 도구로 실제 코드/데이터 owner 확인
7. 필요한 phase step
```

> setup 후 도메인별 Feature Group 섹션을 여기에 추가한다. 아래는 형식 예시.

## Feature Group: `{group-name}`

```text
1. CLAUDE.md
2. docs/DOC_MAP.md
3. docs/features/{group-name}/{핵심 requirements}.md
4. 관련 코드/데이터 owner
```

검사 포인트:

- {이 그룹에서 자주 부딪치는 함정 1}
- {이 그룹에서 자주 부딪치는 함정 2}

## Docs-Only Work

```text
1. CLAUDE.md
2. docs/DOC_MAP.md
3. docs/canonical/PRD.md
4. docs/canonical/ARCHITECTURE.md
5. docs/canonical/ADR.md
6. phases/index.json
```

문서 구조 변경은 기존 파일 이동 전에 계획 문서와 map을 먼저 만든다.

---

## 프로세스 단계별 읽기 순서

Stage 0 (브리프 작성), Stage 2 (Design Review) 등 단계별 읽기 순서와 산출물:
`docs/canonical/DEV_PROCESS.md` 참조.
