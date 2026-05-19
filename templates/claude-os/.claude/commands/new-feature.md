# /new-feature

새 기능·시스템 개발의 시작점을 안내한다. 규모를 진단하고 올바른 DEV_PROCESS Stage로 진입한다.

**기능명**: $ARGUMENTS

---

## 실행 순서

### 1단계 — 사전 읽기

아래 파일을 읽는다:

- `docs/canonical/DEV_PROCESS.md`
- `docs/canonical/PRD.md`
- `docs/canonical/ask-user-question-guide.md` (AskUserQuestion 호출 시 따른다)
- `phases/index.json` (의존 관계 확인)

### 2단계 — 규모 판단

AskUserQuestion으로 아래 두 질문을 동시에 묻는다.

**질문 1**: "$ARGUMENTS"의 성격은?
- `새 시스템 추가` — 지금 없는 시스템을 새로 만든다
- `기존 시스템 기능 추가·변경` — 있는 시스템을 확장하거나 동작을 바꾼다
- `단일 버그 수정` — 원인 파일이 1-2개, 시스템 계약 변경 없음
- `아키텍처·save 계약 변경` — 복수 시스템에 영향, 저장 구조 또는 데이터 구조 변경

**질문 2**: 관련 문서가 이미 있는가?
- `없음 — 처음 시작`
- `discovery-research.md 있음`
- `discovery-research + brief 있음`
- `brief + tech-research + requirements.md 있음`

답변 기반 규모 판단 기준:

| 답변 조합 | 규모 |
|---|---|
| 단일 버그, 없음 | 핫픽스 |
| 기존 시스템 확장, 없음 또는 discovery만 | 소형 또는 중형 |
| 새 시스템, 없음 | 대형 |
| 아키텍처·save 계약 변경 | 대형 |
| brief + tech-research + requirements.md 있음 | Stage 5 (Phase 계획) 직행 |

규모별 리서치 적용:

| 규모 | Stage 0 Discovery | Stage 3 Tech |
|---|---|---|
| 핫픽스 | 적용 안 함 | 적용 안 함 |
| 소형 | 적용 안 함 | 적용 안 함 |
| 중형 | 선택 — 사용자에게 진행 여부 확인 | 선택 (권장) |
| 대형 | **필수** | **필수** |

판단 결과를 사용자에게 제시하고 "이 규모로 진행할까요?"를 확인한다. 사용자가 다르게 수정하면 수정된 규모를 따른다.

### 3단계 — Stage 라우팅

규모에 따라 아래 해당 섹션으로 이동한다.

- 핫픽스 → 핫픽스 경로
- 소형 → Stage 5 라우팅 (Phase 계획 안내)
- 중형 → Stage 2 Concept 검토 또는 Stage 4 Design Review 안내
- 대형, discovery 없음 → Stage 0 Discovery Research 안내
- 대형, discovery 있고 brief 없음 → Stage 1 브리프 작성
- 대형, brief 있고 tech-research 없음 → Stage 3 Tech Research 안내
- 대형, brief + tech-research 있음 → Stage 4 Design Review 안내

---

## 핫픽스 경로

Hotfix DoD를 출력하고 종료한다.

```
□ 버그 재현 조건 확인
□ 원인 파일/함수 특정
□ 최소 변경 (1-2파일)
□ 변경된 시스템의 직접 경로 수동 확인
□ git diff --check 통과
□ (visible text 변경 시) 등록 catalog/locale 키 등록 확인
```

시스템 계약 변경이 발견되면 소형 이상으로 재분류한다고 안내한다.

---

## Stage 0: Discovery Research 안내 (대형 필수)

대형 규모에서 discovery-research.md가 아직 없으면, 다음과 같이 안내한 뒤 종료한다:

```
대형 규모는 Stage 0 Discovery Research가 필수입니다.

다음 커맨드로 리서치를 시작하세요:
  /research {기능명}

산출물: docs/features/{group}/{feature}-discovery-research.md
이 결과가 Stage 1 브리프 작성의 근거가 됩니다.
```

중형 규모이면 AskUserQuestion으로 "Discovery Research를 먼저 진행할까요?"를 묻는다.

- "예" → 위와 동일하게 안내 후 종료
- "아니오" → Stage 1로 진행

대형 규모인데 사용자가 Discovery를 건너뛰려 하면 한 번 더 확인한다: "대형 규모는 Discovery가 권장됩니다. 그래도 건너뛰겠습니까?" 사용자가 명시적으로 동의하면 Stage 1로 진행한다.

---

## Stage 1: 브리프 작성 (대형)

`{feature}-discovery-research.md`가 있으면 먼저 Read하여 결론 섹션을 추출한다. 사용자에게 보여주고 "이 시사점을 브리프에 반영하면서 작성하겠습니다"라고 알린다.

AskUserQuestion으로 아래 항목을 묻는다:

1. **배경·필요성**: 왜 지금 이 기능이 필요한가?
2. **사용자 경험**: 이 기능이 있으면 사용자가 무엇을 경험하는가?
3. **핵심 규칙**: 핵심 수치, 조건, 인과관계가 있다면? (없으면 "미정" 가능)
4. *(자원/loop이 있는 도메인 한정)* **Resource flow loop**: 이 기능이 도입·확장하는 모든 자원·시스템·상태 각각의 input 시작점 / process / output 소비를 나열할 수 있는가? 미정 셀은 `???`로 표기.

사용자 답변과 Discovery 결과를 종합해 `docs/features/{group}/{feature}-brief.md`를 작성한다.

- `{group}`: discovery-research가 있으면 그 경로의 그룹을 그대로 따른다. 없으면 PRD.md 분류에서 가장 가까운 것을 선택. 판단 어려우면 사용자에게 확인.
- `{feature}`: $ARGUMENTS를 snake_case로 변환
- 파일 맨 위에 frontmatter:

```yaml
---
status: draft
review_count: 0
created_at: "{오늘 날짜 YYYY-MM-DD}"
based_on_discovery: "{discovery-research.md 경로 또는 null}"
last_reviewed_at: null
reviewer: null
---
```

- 파일 구조: frontmatter → 제목 → 배경 → 사용자 경험 → 핵심 규칙 → *(해당 도메인)* Resource flow loop 표 → (discovery 있을 때) 리서치 시사점
- "리서치 시사점" 섹션은 discovery-research.md의 결론 1~5개를 그대로 인용하고 각 항목 끝에 `(discovery-research.md 결론 #N)`을 붙인다
- 구현 방법, 의존 시스템 상세, 데이터 스키마는 포함하지 않는다

discovery-research를 인용한 경우:

- discovery-research.md의 frontmatter `status`를 `applied`로 변경
- `applied_at`에 오늘 날짜, `applied_by`에 brief.md 경로 추가

작성 완료 후:

1. 파일 경로를 사용자에게 알린다
2. `docs/DOC_MAP.md` 해당 그룹 섹션에 한 줄 등록한다
3. "Stage 2 Concept 검토를 지금 진행할까요?" 묻고, "예"면 Stage 2 섹션으로 이동. "아니오"면 종료.

---

## Stage 2: Concept 검토 (중형 이상)

`docs/canonical/PRD.md`와 `docs/canonical/ADR.md`를 읽고 브리프 또는 $ARGUMENTS 기능 방향과 충돌하는 항목을 확인한다.

`docs/design_review_questions.md`에 아래 섹션을 추가한다:

```markdown
## {기능명} Concept 검토 — {날짜}

### PRD 충돌 확인
- [ ] {충돌 없음 확인 또는 충돌 항목 기록}

### 미결 설계 질문
- {질문 1}
- {질문 2}
```

미결 질문이 있으면 사용자에게 보여주고 답변을 기다린다. 답변을 파일에 기록한다.

완료 후:

- 대형 규모: "Stage 3 Tech Research를 다음 단계로 진행합니다. `/research docs/features/{group}/{feature}-brief.md`를 실행하세요." 안내 후 종료
- 중형 규모: "Stage 3 Tech Research를 진행할까요?"를 묻고, "예"면 위와 동일하게 안내. "아니오"면 Stage 4 안내로 이동
- 소형 규모: 이 Stage에 진입하지 않음

---

## Stage 3: Tech Research 안내 (대형 필수)

`/research {brief 경로}`를 안내한다. 별도 커맨드로 분리되어 있으므로 `/new-feature`는 안내만 하고 종료한다.

```
다음 커맨드로 Tech Research를 시작하세요:
  /research docs/features/{group}/{feature}-brief.md

산출물: docs/features/{group}/{feature}-tech-research.md
이후 /write-requirements가 이 파일을 자동으로 읽고 근거로 인용합니다.
```

대형 규모에서 사용자가 건너뛰려 하면 한 번 더 확인. 동의하면 진행하되 `/write-requirements`가 나중에 거부할 수 있음을 안내한다.

---

## Stage 4: Design Review 안내 (중형 이상)

브리프 또는 requirements.md가 있는지 확인한다.

- requirements.md 있음: "/design-review {경로}를 실행하세요" 안내 후 종료
- brief만 있음:
  - 대형 규모인데 tech-research.md가 없으면 Stage 3 안내로 이동
  - 그 외: "`/write-requirements {brief 경로}`를 실행해 requirements.md를 먼저 작성하세요" 안내 후 종료
- brief도 없음: Stage 0 또는 Stage 1로 안내 후 이동

---

## Stage 5: Phase 계획 안내 (소형 이상)

brief + (대형이면) tech-research + requirements.md가 모두 있는 경우에만 이 Stage에 진입한다.

`{{AGENT_PREFIX}}-phase-orchestrator` 에이전트를 호출한다.

에이전트에게 전달할 정보:

- 기능명: $ARGUMENTS
- 규모: {판단 결과}
- related_docs: {확인된 brief + (있으면) discovery-research + (있으면) tech-research + requirements.md 경로}
- `phases/index.json` 현재 상태
- `docs/PHASE_MAP.md` 현재 상태

에이전트 요청 사항:

- `phases/{phase-name}/` 폴더 구조 계획
- `README.md` (related_docs 링크 필수)
- `index.json` (related_docs, depends_on, blocks, manual_qa_required, pending_manual_qa_scenarios 필드 포함)
- `step0.md` (`phases/_template/step.md` 형식 준수 — 수동 QA owner, 주 담당 에이전트 필드 포함)
- `phases/index.json` 엔트리 추가
- `docs/PHASE_MAP.md` 행 추가

에이전트 결과를 확인한 뒤 사용자에게 요약 보고한다:

- 생성된 phase 이름
- step 목록과 담당 에이전트
- 다음 할 일: "step0 구현을 시작하려면 담당 에이전트를 호출하세요"

---

## 제약

- 규모 판단 후 사용자 확인 없이 Stage를 건너뛰지 않는다
- 브리프 내용은 사용자 입력 없이 단독으로 지어내지 않는다 (discovery-research를 인용하더라도 사용자 답변이 우선)
- 소형 이상은 반드시 `phases/index.json`에 등록한다
- 모든 출력은 한국어
