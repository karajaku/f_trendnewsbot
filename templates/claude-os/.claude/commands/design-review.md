# /design-review

기획문서를 5개 에이전트 관점에서 교차 리뷰하고, 리뷰 문서를 작성한 뒤 사용자 결정을 반영한다.

**대상 문서**: $ARGUMENTS

---

## 실행 순서

### 1단계 — 대상 문서 확인

`$ARGUMENTS` 파일을 Read tool로 읽는다. 파일이 존재하지 않으면 즉시 멈추고 사용자에게 알린다.

5단계에서 AskUserQuestion을 호출하기 전 `docs/canonical/ask-user-question-guide.md`를 읽고 그 원칙을 따른다.

### 2단계 — 5개 에이전트 병렬 리뷰

Agent tool로 아래 5개를 **단일 메시지에 병렬** 호출한다. 각 에이전트는 `$ARGUMENTS`를 읽고 자신의 관점에서만 리뷰하며 **파일을 수정하지 않는다**.

각 에이전트 호출 공통 지침:
- 대상 파일을 직접 읽는다.
- 출력: ① 긍정 평가 (2~3줄), ② 이슈 목록 (심각도: 높음/중간/낮음, 파일:줄번호 포함), ③ 권고사항
- 자연어 보고 끝에 자신의 `## Output Schema` (`.claude/agents/{{AGENT_PREFIX}}-*.md` 정의)에 맞는 ` ```yaml` 블록을 포함한다. 3단계 리뷰 문서 작성 시 파싱하여 이슈 테이블에 매핑한다.
- 최대 500단어. 추가 구현은 하지 않는다.
- 모든 출력은 한국어.

| 에이전트 | 리뷰 관점 |
|---|---|
| `{{AGENT_PREFIX}}-phase-orchestrator` | PM: scope 과부하, milestone 현실성, 완료 기준 검증 가능성, 단계 의존성 |
| `{{AGENT_PREFIX}}-implementer` | 개발자: 기술 타당성, 구현 복잡도, 통합 진입 파일 비대화 위험, 회귀 가능성 |
| `{{AGENT_PREFIX}}-qa-reviewer` | QA: acceptance criteria 완전성, manual QA 부하, 자동화 차단 항목, 테스트 불가 시나리오 |
| `{{AGENT_PREFIX}}-data-steward` | 데이터: schema 계약 일관성, 식별 키 누락, 데이터 fallback 규칙 준수 |
| `{{AGENT_PREFIX}}-ui-specialist` | UI: 표면 소유권 명확성, 리빌드 트리거, fallback 처리, 기존 layout 파괴 위험 |

> UI 표면이 없는 프로젝트라면 5번째를 `{{AGENT_PREFIX}}-performance-investigator` 또는 다른 도메인 특화 에이전트로 교체한다.

### 3단계 — 리뷰 문서 작성

`$ARGUMENTS`와 **같은 폴더**에 `design-review-{basename}.md`를 작성한다.

`design-review-{basename}.md` 파일 맨 위에 아래 frontmatter를 포함한다:

```yaml
---
status: reviewed
review_count: 1
created_at: "{오늘 날짜}"
last_reviewed_at: "{오늘 날짜}"
reviewer: "{{AGENT_PREFIX}}-phase-orchestrator, {{AGENT_PREFIX}}-implementer, {{AGENT_PREFIX}}-qa-reviewer, {{AGENT_PREFIX}}-data-steward, {{AGENT_PREFIX}}-ui-specialist"
---
```

리뷰 문서 작성 완료 후 **원본 파일(`$ARGUMENTS`)의 frontmatter를 업데이트**한다:
- `status`: `reviewed`
- `review_count`: 기존 값 +1 (frontmatter 없으면 1로 초기화)
- `last_reviewed_at`: 오늘 날짜
- `reviewer`: 리뷰한 에이전트 목록

frontmatter가 없는 기존 파일이면 파일 맨 위에 추가한다.

문서 구조:
```
# {원본파일명} 설계 리뷰

작성일: {오늘 날짜}
리뷰 대상: {$ARGUMENTS}

## 총괄 평가
긍정 평가 + 핵심 문제 요약

## 역할별 이슈

### PM
이슈 테이블 (심각도 | 이슈 | 권고)

### 개발자
이슈 테이블

### QA
이슈 테이블

### 데이터
이슈 테이블

### UI
이슈 테이블

## 우선순위 매트릭스
즉시 조정 | 단기 권고 | 별도 phase 분리 권고

## 즉시 적용 항목
사용자 결정 없이 바로 반영할 수 있는 수정 목록
```

### 4단계 — 즉시 적용

리뷰 문서의 "즉시 적용 항목" (누락 키, 명세 보완, 오타 등)을 **사용자 승인 없이 바로** 원본 문서에 반영한다.

### 5단계 — 구조적 변경 결정

구조적 변경(phase 분리, scope down, 단계 재순서 등)이 있으면 AskUserQuestion으로 항목당 하나씩 묻는다. 추천 옵션을 첫 번째에 두고 `(권고)` 표시를 붙인다.

### 6단계 — 승인 반영

사용자 결정에 따라 원본 문서, 관련 phase 파일(README.md, index.json, stepN.md), DOC_MAP.md를 업데이트한다.

반영 완료 후 **원본 파일(`$ARGUMENTS`)의 frontmatter를 업데이트**한다:
- `status`: `applied`
- `applied_at`: 오늘 날짜 (기존 frontmatter에 필드 추가)

---

## 제약

- 에이전트는 review-only 모드 — 파일 수정 없이 분석만 반환.
- 임시 역할 생성 금지 — 반드시 `.claude/agents/{{AGENT_PREFIX}}-*.md` 프로파일 사용.
- 리뷰 문서는 `phases/` 아래 저장하지 않는다 — 항상 `docs/features/{group}/` 아래.
- phase 분리 등 구조적 변경은 반드시 사용자 승인 후 반영.
- 모든 출력은 한국어.
