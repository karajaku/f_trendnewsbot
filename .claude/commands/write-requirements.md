# /write-requirements

브리프를 기반으로 명세서(`{feature}-requirements.md`)를 작성한다. Stage 4 산출물.

**대상 브리프 경로**: $ARGUMENTS

---

## 실행 순서

### 1단계 — 사전 읽기

아래 파일을 읽는다:

- `$ARGUMENTS` (brief.md)
- `$ARGUMENTS`와 같은 폴더에 `design-review-{basename}.md`가 있으면 함께 읽는다
- `$ARGUMENTS`와 같은 폴더의 `{feature}-tech-research.md`가 있으면 함께 읽는다 (2단계에서 규모별 처리)
- `docs/canonical/DEV_PROCESS.md` Stage 4 requirements.md 포함 항목 확인
- `docs/canonical/ask-user-question-guide.md` (3단계 AskUserQuestion 호출 시 따른다)

### 2단계 — 선행 조건 확인

`$ARGUMENTS`의 frontmatter `status`를 확인한다:

- `draft` 상태이면: AskUserQuestion으로 "/design-review를 먼저 실행하길 권장합니다. 계속할까요?" 묻는다.
- `reviewed` 또는 `applied` 상태이면: 바로 다음 단계 진행.
- `$ARGUMENTS`가 존재하지 않으면: 즉시 중단. "/new-feature로 브리프를 먼저 작성하세요." 안내.
- frontmatter가 없는 파일이면: "브리프 파일에 frontmatter가 없습니다. /new-feature로 생성된 파일인지 확인하세요." 안내.

**Tech Research 산출물 확인** (Stage 3 연동):

같은 폴더에서 `{feature}-tech-research.md`(브리프 파일명에서 `-brief.md` → `-tech-research.md`)를 찾는다.

- 파일이 있으면: 본문을 읽고 "결론 — requirements.md 반영 시사점" 섹션을 추출해 4단계에서 인용한다.
- 파일이 없을 때 규모별 처리:
  - **대형 규모**: 즉시 중단. "대형 규모는 tech-research.md가 필요합니다. /research $ARGUMENTS를 먼저 실행하세요." 안내. 사용자가 "그래도 강제로 진행"이라고 명시적으로 요청하면 진행하되, 결과 파일의 `based_on`에 "tech-research.md 생략(사용자 강제 진행)"을 기록한다.
  - **중형 규모**: AskUserQuestion으로 "tech-research.md가 없습니다. 지금 /research를 먼저 실행할까요, 아니면 그대로 진행할까요?"를 묻는다. 사용자 선택에 따른다.
  - **소형 규모**: 그대로 진행한다.

규모 판단이 불확실하면 AskUserQuestion으로 "이 기능의 규모는?" (대형 / 중형 / 소형)을 먼저 묻는다.

### 3단계 — 추가 정보 수집

AskUserQuestion으로 아래 네 항목을 **동시에** 묻는다:

**질문 1 — 의존 시스템**: 이 기능이 직접 의존하는 시스템을 나열하면?

**질문 2 — 범위 외**: 이번 구현에서 명시적으로 제외하는 것은?
(없으면 "없음" 가능)

**질문 3 — Acceptance Criteria**: 이 기능이 "완료"된 조건 2-5개를 나열하면?

**질문 4 — 데이터 계약**: 아래 중 해당하는 항목이 있는가?
- 신규/확장 데이터 정의 파일
- 저장 구조(save) 변경
- 식별 키 / 텍스트 키 추가
(없으면 "없음" 가능)

### 4단계 — 명세서 작성

`docs/features/{group}/{feature}-requirements.md`를 아래 형식으로 작성한다.

`{group}`, `{feature}`는 `$ARGUMENTS` 경로에서 그대로 따른다.

```yaml
---
status: draft
review_count: 0
created_at: "{오늘 날짜 YYYY-MM-DD}"
based_on: "{$ARGUMENTS 경로}"
last_reviewed_at: null
reviewer: null
---
```

포함 항목 (DEV_PROCESS.md Stage 4 기준):

- **배경** — brief에서 발췌
- **사용자 경험** — brief에서 발췌
- **핵심 규칙** — brief에서 발췌
- *(자원/loop이 있는 도메인 한정)* **Resource flow loop** — brief의 표를 그대로 가져오되, brief에서 `???` 였던 셀이 있다면 본 requirements 단계에서 **모두 해소**되어야 한다. 셀 하나라도 `???` 남아 있으면 사용자에게 결정을 받고 채운다. 한 셀이라도 미정 상태로 requirements를 `applied`로 전환할 수 없다.
- **리서치 시사점** — tech-research.md가 있으면 결론 섹션 1~5개를 그대로 인용하고 각 항목 끝에 `(tech-research.md 결론 #N)`을 붙인다. 없으면 섹션 자체를 생략한다
- **의존 시스템** — 3단계 답변
- **범위 외** — 3단계 답변
- **Acceptance Criteria** — 3단계 답변 (체크박스 목록 `- [ ]` 형식)
- **데이터 계약** — 3단계 답변 (없으면 "없음" 기재, 섹션은 유지)
- *(UI 포함 기능)* **UI 표면 명세** — 브리프에 UI 언급 있으면 추가로 묻는다

requirements.md가 이미 존재하면 덮어쓰기 전 AskUserQuestion으로 사용자 확인.

### 4.5단계 — tech-research.md 상태 업데이트

tech-research.md를 근거로 인용한 경우(4단계에서 "리서치 시사점" 섹션을 채운 경우):

- tech-research.md의 frontmatter `status`를 `applied`로 변경
- `applied_at` 필드에 오늘 날짜 추가
- frontmatter에 `applied_by: "{feature}-requirements.md"` 추가하여 인용 경로를 남긴다

### 5단계 — 후처리

1. `docs/DOC_MAP.md` 해당 그룹 섹션에 한 줄 등록한다.
2. 생성된 파일 경로와 함께 아래 안내를 출력한다:

```
{feature}-requirements.md 생성 완료.

다음 선택지:
- /design-review {파일경로} — requirements.md 교차 리뷰 (권장)
- /plan-phase {파일경로} — Stage 5 Phase 계획 시작
```

---

## 제약

- 의존 시스템, 범위 외, acceptance criteria는 사용자 입력 없이 지어내지 않는다.
- `based_on` 경로는 `$ARGUMENTS` 값 그대로 기록한다.
- tech-research.md "결론"이 6개 이상이거나 구현 단계가 포함돼 있으면 인용을 중단하고 사용자에게 보고: "tech-research.md가 DoD를 어겼습니다. /research를 다시 실행하길 권장합니다."
- 대형 규모에서 tech-research.md를 강제로 생략한 경우, requirements.md의 acceptance criteria가 코드베이스 anchor 없이 추측에 기반하지 않도록 주의한다.
- 모든 출력은 한국어.
