# /research

Discovery Research(Stage 0) 또는 Tech Research(Stage 3)를 수행한다. 호출 시점의 파일 상태에 따라 모드를 자동 판단한다.

**입력**: $ARGUMENTS

- 비어 있거나 `feature-name` 형태이면 **Discovery 모드 후보**
- 기존 브리프 경로(`docs/features/{group}/{feature}-brief.md`)이면 **Technical 모드 후보**

---

## 실행 순서

### 1단계 — 사전 읽기

- `docs/canonical/DEV_PROCESS.md`의 Stage 0 Discovery Research / Stage 3 Tech Research 섹션
- `docs/DOC_MAP.md`
- `docs/canonical/ask-user-question-guide.md` (AskUserQuestion 호출 시 따른다)
- $ARGUMENTS가 파일 경로이면 해당 파일을 Read

### 2단계 — 모드 자동 판단

판단 규칙:

1. $ARGUMENTS가 비어 있음 → 사용자에게 기능명을 묻는다 → Discovery 모드 후보
2. $ARGUMENTS가 기능명 문자열 → Discovery 모드 후보
3. $ARGUMENTS가 `*-brief.md` 경로 → Technical 모드 후보
4. $ARGUMENTS가 그 외 파일 경로 → 즉시 중단. "/research는 기능명 또는 brief.md 경로만 받습니다." 안내

후보 모드에 해당하는 결과 파일이 이미 존재하면 AskUserQuestion으로 확인:

- Discovery 후보인데 `{feature}-discovery-research.md`가 이미 있으면: "이미 Discovery 결과가 있습니다. (a) 덮어쓰기 (b) 이어서 보강 (c) Technical 모드로 전환 (브리프가 있어야 함) (d) 중단" 묻기
- Technical 후보인데 `{feature}-tech-research.md`가 이미 있으면: "이미 Technical 결과가 있습니다. (a) 덮어쓰기 (b) 이어서 보강 (c) 중단" 묻기

Technical 후보로 진입했으나 `{feature}-brief.md`가 존재하지 않으면 즉시 중단. "Technical Research는 브리프가 필요합니다. /new-feature로 브리프를 먼저 작성하세요." 안내.

### 3단계 — 그룹·경로 결정

Discovery 모드:
- 기능명을 받았으면 `docs/canonical/PRD.md`의 그룹 분류에서 가장 가까운 group을 선택. 판단 어려우면 AskUserQuestion으로 확인.
- 결과 경로: `docs/features/{group}/{feature}-discovery-research.md`

Technical 모드:
- `{group}`, `{feature}`는 $ARGUMENTS 경로에서 그대로 따른다.
- 결과 경로: `docs/features/{group}/{feature}-tech-research.md`

### 4단계 — 리서치 질문 서명 (필수 DoD)

AskUserQuestion으로 아래 세 항목을 **동시에** 묻는다. 사용자 답변 없이는 다음 단계로 넘어가지 않는다.

**질문 1 — 핵심 리서치 질문**: 이 기능을 위해 반드시 확인해야 할 질문 2~5개를 나열하면?

Discovery 모드 예시: `유사 제품의 비슷한 시스템 사례`, `현재 코드에 비슷한 패턴이 있는지`, `사용자 관점에서 자주 묻는 디자인 함정`

Technical 모드 예시: `현재 X 계산 경로`, `유사 데이터 구조`, `save에 들어가는 상태 범위`

**질문 2 — 외부 자료 필요 여부**: 외부 참고 자료 조사가 필요한 항목이 있는가?

- Discovery 모드: 다른 제품 사례 / 논문 / 블로그
- Technical 모드: 런타임 API / 기술 참고 자료

없으면 "없음" 가능. 답이 "없음"이면 결과 문서의 해당 섹션은 "해당 없음"으로 채워진다.

**질문 3 — 시간 박스**: 이번 리서치에 허용하는 분량은?

- `짧음` — anchor 3~5개, 외부 자료 0~1건
- `보통 (권장)` — anchor 5~10개, 외부 자료 0~3건
- `깊음` — anchor 10개 이상, 외부 자료 다수 허용

답변을 모두 수집한 뒤 사용자에게 한 번에 보여주고 "이대로 진행할까요?"를 확인한다. 이 답변이 "사용자 서명"이며 결과 파일 "조사 질문" 섹션에 그대로 들어간다.

### 5단계 — 에이전트 위임

`{{AGENT_PREFIX}}-research-investigator` 에이전트를 Agent tool로 호출한다.

전달할 정보:

- `mode`: `discovery` 또는 `technical` (2단계 판단 결과)
- Discovery 모드: 기능명 + 결과 파일 경로
- Technical 모드: 브리프 경로 + 결과 파일 경로
- 사용자가 서명한 조사 질문 (4단계 결과 그대로)
- 외부 자료 조사 허용 여부 (4단계 질문 2)
- 시간 박스 (4단계 질문 3)

에이전트 요청 사항:

- 모드별 워크플로 준수 (에이전트 프로파일 정의 그대로)
- 결론 1~5개로 한정 (DoD)
- frontmatter `status: draft`, `mode: discovery | technical`
- `docs/DOC_MAP.md` 등록
- Discovery 모드: 코드베이스 anchor는 1~5개 수준의 개괄 (깊은 조사 금지)
- Technical 모드: 코드베이스 섹션은 반드시 비어 있지 않게

### 6단계 — 결과 확인

에이전트 응답의 `yaml` 블록을 파싱해 아래를 확인한다:

- `mode`가 5단계 요청 모드와 일치
- `overall_verdict`가 `complete` 또는 `partial`
- `conclusions_count`가 1~5 범위
- Technical 모드인데 `codebase_anchors`가 비어 있으면 DoD 위반 — 사용자에게 보고 후 재호출 권유
- `questions_open`이 있으면 사용자에게 후속 결정 필요 항목으로 보고

### 7단계 — 안내 출력

**Discovery 모드 완료 시**:

```
{feature}-discovery-research.md 생성 완료.

해소된 질문: {questions_resolved 요약}
열린 질문: {questions_open 요약}  ← 있으면 표기
다음 선택지:
- /new-feature {기능명} — 이 리서치 결과를 인용해 브리프를 작성합니다.
```

**Technical 모드 완료 시**:

```
{feature}-tech-research.md 생성 완료.

해소된 질문: {questions_resolved 요약}
열린 질문: {questions_open 요약}  ← 있으면 표기
다음 선택지:
- /write-requirements docs/features/{group}/{feature}-brief.md
  — tech-research.md를 자동으로 읽고 근거로 인용합니다.
- /design-review docs/features/{group}/{feature}-brief.md
  — 브리프에 대한 교차 리뷰부터 받고 싶을 때.
```

---

## 제약

- 사용자가 서명하지 않은 질문은 리서치 대상으로 추가하지 않는다.
- Discovery 모드는 깊은 코드 조사를 하지 않는다 (anchor 5개 이하). 깊은 조사는 Technical 모드에서.
- 에이전트가 결론을 6개 이상 내거나, 결론에 구체 구현 단계가 포함되면 거부하고 재작성 요청한다.
- 외부 자료 인용 시 URL과 retrieved 날짜를 함께 기록한다.
- 리서치 산출물은 항상 `docs/features/{group}/` 아래에 둔다. `phases/`에 두지 않는다.
- 모든 출력은 한국어.
