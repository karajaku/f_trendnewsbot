# /plan-phase

requirements.md를 기반으로 Phase 개발 계획을 수립한다. Stage 5 진입점.

**대상 requirements 경로**: $ARGUMENTS

---

## 실행 순서

### 1단계 — 사전 읽기

아래 파일을 읽는다:

- `$ARGUMENTS` (requirements.md)
- `phases/index.json` (의존 관계 + 기존 phase 목록)
- `docs/PHASE_MAP.md` (현재 phase 상태 전체)
- requirements.md의 `based_on` 필드가 있으면 해당 brief.md도 읽는다
- `docs/canonical/ask-user-question-guide.md` (3단계 AskUserQuestion 호출 시 따른다)

### 2단계 — 선행 조건 확인

`$ARGUMENTS`의 frontmatter `status`를 확인한다:

- `draft` 상태이면: AskUserQuestion으로 "/design-review로 먼저 검토하길 권장합니다. 계속할까요?" 묻는다.
- `$ARGUMENTS`가 존재하지 않으면: 즉시 중단. "/write-requirements로 명세서를 먼저 작성하세요." 안내.

### 3단계 — Phase 정보 수집

AskUserQuestion으로 아래 세 항목을 **동시에** 묻는다:

**질문 1 — Phase 이름**: phases/ 아래 폴더명으로 쓸 이름은? (kebab-case 권장)

**질문 2 — 규모**: 예상 step 수는?

- `1 step — 소형` : 단일 step으로 완성
- `2-3 step — 중형` : 단계적 분해 필요
- `4+ step — 대형` : 세분화 필요

**질문 3 — 선행 의존**: 이 phase 시작 전에 완료되어야 하는 phase가 있는가?
(phases/index.json의 `dir` 값으로 지정, 없으면 "없음")

### 4단계 — Phase 계획 위임

`tnb-phase-orchestrator` 에이전트를 호출한다.

에이전트에게 전달할 컨텍스트:

- **Phase 이름**: 3단계 답변
- **규모 (예상 step 수)**: 3단계 답변
- **related_docs**:
  - `$ARGUMENTS` (requirements.md)
  - brief.md 경로 (requirements.md의 `based_on` 필드 값, 있는 경우)
- **depends_on**: 3단계 답변
- **phases/index.json 현재 내용**: 1단계에서 읽은 값 전달
- **docs/PHASE_MAP.md 현재 내용**: 1단계에서 읽은 값 전달

에이전트 요청 사항 (템플릿: `phases/_template/`):

| 파일 | 형식 | 필수 항목 |
|---|---|---|
| `phases/{phase}/README.md` | `_template/README.md` | 목표, 범위, related_docs 링크, 완료 기준 |
| `phases/{phase}/index.json` | `_template/index.json` | step 목록, depends_on, blocks, manual_qa_required, pending_manual_qa_scenarios |
| `phases/{phase}/step0.md` (+ 이후 step) | `_template/step.md` | 범위, acceptance criteria, 금지사항, 수동 QA owner, 주 담당 에이전트 |
| `phases/index.json` | — | 신규 phase 엔트리 추가 |
| `docs/PHASE_MAP.md` | — | 신규 행 추가 |

### 5단계 — 문서 상태 동결

에이전트 작업 완료 후 아래 파일의 frontmatter를 업데이트한다:

**requirements.md (`$ARGUMENTS`)**:
- `status`: `frozen`
- `frozen_at`: 오늘 날짜 (필드 추가)

**brief.md** (requirements.md의 `based_on` 필드 경로, 있는 경우):
- `status`: `frozen`
- `frozen_at`: 오늘 날짜 (필드 추가)

### 6단계 — 완료 보고

아래 내용을 출력한다:

```
Phase 계획 완료: {phase-name}

생성된 파일:
- phases/{phase-name}/README.md
- phases/{phase-name}/index.json
- phases/{phase-name}/step0.md (+ 추가 step 파일)

기획 문서 상태: frozen
- {brief.md 경로}
- {requirements.md 경로}

다음 할 일:
  step0 구현을 시작하려면 아래 에이전트를 호출하세요.
  담당: {step0.md의 주 담당 에이전트}
```

---

## 제약

- Phase 이름은 사용자 확인 없이 단독으로 결정하지 않는다.
- orchestrator가 생성한 파일 내용을 임의로 수정하지 않는다.
- `phases/index.json` 엔트리 누락 시 완료로 보고하지 않는다.
- `status: frozen` 업데이트는 orchestrator 작업 완료 확인 후 실행한다.
- 모든 출력은 한국어.
