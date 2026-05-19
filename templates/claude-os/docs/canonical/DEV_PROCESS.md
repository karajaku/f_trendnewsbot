# 개발 프로세스

> 역할: {{PROJECT_NAME}} 프로젝트의 단일 권위 개발 프로세스 정의 — 기획부터 완료까지 각 단계, 산출물, DoD, 추적 체인을 명시한다.
> 대상: 새 기능/버그 수정 시작 전, phase 계획 수립 시, 에이전트 선택 시, DoD 확인 시. 모든 규모의 모든 작업.

작성일: {{TODAY}}

---

## 핵심 원칙

1. **추적 가능성**: 모든 산출물은 생성 원인과 다음 단계 연결을 파일 내 링크로 명시한다.
2. **단일 진입점**: `phases/index.json`이 모든 실행 상태의 source of truth다.
3. **완료 기준 선행**: 구현 전에 acceptance criteria를 먼저 작성한다.
4. **QA 주체 분리**: 런타임 수동 확인은 사용자만 할 수 있다. 에이전트는 사용자 확인 없이 phase status를 `completed`로 바꿀 수 없다 (개별 step은 정적 검증 통과 시 자동 `completed`, 단 `qa_blocking: true`인 step은 예외).
5. **최소 변경**: 명시 요청 없이 큰 리팩터링은 하지 않는다.
6. **정보 기반 기획**: 브리프와 명세는 빈 종이가 아닌 리서치에 기반한다. 대형 기능은 Discovery Research(Stage 0) → Brief → Tech Research(Stage 3) → Requirements 순으로 정보가 누적된다.

---

## 규모 분류 — 모든 작업의 첫 번째 판단

| 규모 | 기준 | 진입 단계 | phase 생성 | Discovery Research (Stage 0) | Tech Research (Stage 3) |
|---|---|---|---|---|---|
| **핫픽스** | 1-2파일, 단일 버그, 시스템 계약 변경 없음 | Stage 6 직행 | 없음 | 적용 안 함 | 적용 안 함 |
| **소형** | 단일 시스템, 1 step 이하, 계약 변경 최소 | Stage 5 → | 필요 | 적용 안 함 | 적용 안 함 |
| **중형** | 복수 시스템, 2-5 step | Stage 4 → | 필요 | 선택 | 선택 (권장) |
| **대형** | 새 시스템 추가 또는 아키텍처 변경 | Stage 0 → | 필요 | **필수** | **필수** |

소형 phase의 Stage 5는 단일 step 파일 + index.json 생성으로 축약할 수 있다. Stage 6과 같은 세션에서 진행해도 된다.

시스템 계약 변경이 발견되면 핫픽스를 소형 이상으로 재분류한다.

---

## 전체 흐름

```
[아이디어 / 필요성]
        ↓
[ 규모 분류 ]───핫픽스──→ Stage 6 → Hotfix DoD → 끝
        │
      소형 이상
        ↓
Stage 0: Discovery Research    (대형 필수 · 중형 선택)
        ↓
Stage 1: 브리프 작성           (대형만)
        ↓
Stage 2: Concept 검토          (중형 이상)
        ↓
Stage 3: Tech Research         (대형 필수 · 중형 선택)
        ↓
Stage 4: 설계 & Design Review  (중형 이상)
        ↓
Stage 5: Phase 계획            (소형 이상)
        ↓
Stage 6: 구현                  (step 단위 반복)
        ↓
Stage 7: Review & QA           (step 단위 반복 + phase 끝 일괄)
        ↓
Stage 8: Phase 완료
        ↓
Stage 9: Canonical Sync        (트리거 조건 충족 시만)
```

리서치가 2회 분리된 이유:

- **Stage 0 Discovery Research**는 브리프 작성을 정보 기반으로 만든다. 디자인 레퍼런스(다른 제품 사례, 외부 자료)와 코드베이스의 "이미 있는 비슷한 시스템" 개괄을 다룬다. 결론은 브리프에 인용된다.
- **Stage 3 Tech Research**는 requirements 작성을 정보 기반으로 만든다. 코드베이스 깊이 조사(데이터 정의/loader, save 경계, 통합 진입 파일 통합 지점)와 런타임 API 가능성을 다룬다. 결론은 requirements.md에 인용된다.

---

## 산출물 상태 추적

`docs/features/` 아래 기획 문서(brief, research, requirements, design-review)는 YAML frontmatter로 상태를 추적한다. step.md 상태는 `phases/{phase}/index.json`이 관리하므로 제외.

### Frontmatter 스키마

```yaml
---
status: draft          # draft | reviewed | applied | frozen
review_count: 0
created_at: "YYYY-MM-DD"
last_reviewed_at: null
reviewer: null
# applied_at: null    (applied 전환 시 추가)
# frozen_at: null     (frozen 전환 시 추가)
---
```

### 상태 전환 — 누가 언제 업데이트하는가

| 상태 | 전환 시점 | 담당 |
|---|---|---|
| `draft` | 문서 최초 생성 시 | `/new-feature` (brief), `/research` (discovery-research, tech-research), `/write-requirements` (requirements) |
| `reviewed` | `/design-review` 리뷰 완료 직후 | `/design-review` 커맨드 |
| `applied` | 리뷰 결과 원본 문서 반영 완료 직후, 또는 research 문서가 후속 단계에서 근거로 인용된 직후 | `/design-review`, `/new-feature`, `/write-requirements` 커맨드 |
| `frozen` | `/plan-phase` 커맨드가 phase 계획 확정 시 | `/plan-phase` 커맨드 |

`reviewed` 전환 시: `review_count +1`, `last_reviewed_at`, `reviewer` 갱신
`applied` 전환 시: `applied_at` 필드 추가
`frozen` 전환 시: `frozen_at` 필드 추가

`discovery-research.md`와 `tech-research.md`는 `draft → applied` 두 상태만 사용한다. `reviewed`, `frozen`은 적용하지 않는다.

---

## Stage 0: Discovery Research

**대상 규모**: 대형 필수, 중형 선택
**담당**: `/research` 커맨드 (discovery 모드) → `{{AGENT_PREFIX}}-research-investigator` 에이전트

**목적**: 브리프 작성 전에 (1) 외부 디자인 레퍼런스와 (2) 현재 코드베이스에 이미 존재하는 비슷한 시스템을 가볍게 조사한다. 브리프가 "정보 없는 종이"가 아니라 현실 기반으로 작성되도록 한다.

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `{feature}-discovery-research.md` | `docs/features/{group}/` | 신규 — frontmatter `status: draft` 포함 |
| `docs/DOC_MAP.md` | — | 업데이트 — 해당 그룹 섹션에 한 줄 등록 |

**복수 산출물 예외**: 디스커버리 리서치가 성격이 다른 두 측면(예: 자체 시스템 깊이 audit + 외부 제품 비교)을 다뤄 한 파일에 묶기 어색하면 복수 파일로 나눠도 된다. 단 (a) brief frontmatter의 `based_on_discovery` 배열에 모든 파일을 명시 인용하고 (b) 각 파일이 자체 DoD를 충족해야 한다.

### discovery-research.md 포함 항목

- **조사 질문** — `/research` 호출 시 사용자가 서명한 질문 그대로
- **디자인 레퍼런스** (필수) — 다른 제품 사례, 논문, 기사. URL + retrieved 날짜. 사용자가 외부 조사를 허용하지 않은 경우 "해당 없음" 명시
- **코드베이스 개괄** (필수) — 현재 레포에 이미 존재하는 비슷한 시스템·데이터 정의·UI 개괄. `file:line` anchor 1~5개 수준 (깊은 조사는 Stage 3에서)
- **결론 — 브리프 반영 시사점** (필수) — 1~5개 bullet. 사용자 경험 방향성, 차별점, 코드베이스 호환성, 회피해야 할 함정 등. 구현 단계는 포함하지 않는다

### Stage 0 DoD

```
□ 사용자가 핵심 리서치 질문 2~5개를 서명 (AskUserQuestion 결과)
□ 디자인 레퍼런스 섹션 존재 (없으면 "해당 없음" 명시)
□ 코드베이스 개괄 섹션이 비어 있지 않음 (file:line anchor 1건 이상 또는 "유사 시스템 없음" 명시)
□ 결론 1~5개, 구현 단계 미포함
□ docs/DOC_MAP.md 등록
□ frontmatter status: draft
```

### 완료 조건

- 위 DoD 6항 충족
- `{{AGENT_PREFIX}}-research-investigator`의 `overall_verdict`가 `complete` 또는 `partial`
- `partial`이면 `questions_open`을 사용자에게 보고

### 상태 전환

- `/research` discovery 모드 작성 직후: `status: draft`
- `/new-feature`가 브리프 작성 시 이 문서를 인용하면: `status: applied`, `applied_at` 추가

---

## Stage 1: 브리프 작성

**대상 규모**: 대형
**담당**: 사용자 (가능하면 `/new-feature` 안내 + Discovery Research 결과 인용)

**목적**: 시스템에 필요한 요구사항을 빠르게 목록화하여 기획·구현 방향을 논의하고 확정한다. 기획서보다 작고, 구현 방법은 포함하지 않는다.

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `{feature}-brief.md` | `docs/features/{group}/` | 신규 — frontmatter `status: draft` 포함 |
| `{feature}-discovery-research.md` | `docs/features/{group}/` | 업데이트 — `status: applied` (인용 시) |

### 브리프 포함 항목

- **배경**: 왜 이 기능이 필요한가
- **사용자 경험**: 이 기능이 있으면 사용자가 무엇을 경험하는가
- **핵심 규칙**: 핵심 수치, 조건, 인과관계
- **(자원/loop이 있는 도메인) Resource flow loop**: 브리프가 도입·확장하는 모든 자원·시스템·상태에 대해 input → process → output 표를 작성. 셀이 미정이면 `???`로 명시. 게임/시뮬레이션이 아닌 도메인은 생략 가능.
- **리서치 시사점**: Discovery Research가 있으면 결론 섹션을 그대로 인용. 없으면 섹션 생략

**포함하지 않는 것**: 구현 방법, 의존 시스템 상세, 데이터 스키마, acceptance criteria — 이것들은 Stage 4에서 작성한다.

### 완료 조건

- 항목 모두 작성됨 (리서치 없는 경우 리서치 시사점 제외)
- 구현 방법 언급 없음
- `/design-review`에 넘길 수 있는 상태

---

## Stage 2: Concept 검토

**대상 규모**: 중형 이상

**목적**: 브리프가 `PRD.md`·`ADR.md`와 충돌하지 않는지 확인한다.

### 읽을 파일

`docs/canonical/PRD.md`, `docs/canonical/ADR.md`

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `docs/design_review_questions.md` | 루트 | 업데이트 |

`design_review_questions.md`에 `## [기능명] Concept 검토 — [날짜]` 섹션 추가 후 PRD 충돌 없음/미결 질문을 기록한다. 이 기록이 Stage 2 통과 증거다.

### 완료 조건

- PRD·ADR과 충돌 없음 확인
- 미결 설계 질문 식별 완료
- 결과가 `design_review_questions.md`에 기록됨

---

## Stage 3: Tech Research

**대상 규모**: 대형 필수, 중형 선택
**담당**: `/research` 커맨드 (technical 모드) → `{{AGENT_PREFIX}}-research-investigator` 에이전트

**목적**: 브리프와 Concept 검토 결과를 바탕으로, `requirements.md` 작성에 필요한 기술적 조사를 수행한다. 코드베이스 깊이 분석과 런타임 API 가능성을 다룬다. 설계는 하지 않는다.

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `{feature}-tech-research.md` | `docs/features/{group}/` | 신규 — frontmatter `status: draft` 포함 |
| `docs/DOC_MAP.md` | — | 업데이트 — 해당 그룹 섹션에 한 줄 등록 |

### tech-research.md 포함 항목

- **조사 질문** — `/research` 호출 시 사용자가 서명한 질문 그대로
- **코드베이스 조사** (필수) — 기존 유사 시스템, 데이터 정의/loader, 텍스트/i18n 키 네이밍 선례, save 경계 시사점, 통합 진입 파일 통합 지점. `file:line` anchor로 인용
- **런타임 API · 외부 기술 자료** (선택) — API 가능성, 외부 기술 참고. URL + retrieved 날짜 포함. 사용자가 허용하지 않았으면 "해당 없음"
- **결론 — requirements.md 반영 시사점** (필수) — 1~5개 bullet. 제약·의존·위험·네이밍 선택 등 시사점만. 구현 단계는 포함하지 않는다

### Stage 3 DoD

```
□ 사용자가 핵심 리서치 질문 2~5개를 서명 (AskUserQuestion 결과)
□ 코드베이스 조사 섹션이 비어 있지 않음 (file:line anchor 1건 이상)
□ 런타임 API · 외부 기술 자료 섹션 존재 (없으면 "해당 없음" 명시)
□ 결론 1~5개, 구현 단계 미포함
□ docs/DOC_MAP.md 등록
□ frontmatter status: draft
```

### 완료 조건

- 위 DoD 6항 충족
- `{{AGENT_PREFIX}}-research-investigator`의 `overall_verdict`가 `complete` 또는 `partial`
- `partial`이면 `questions_open`을 사용자에게 보고

### 상태 전환

- `/research` technical 모드 작성 직후: `status: draft`
- `/write-requirements`가 이 문서를 인용하면: `status: applied`, `applied_at` 추가

---

## Stage 4: 설계 & Design Review

**대상 규모**: 중형 이상
**담당**: `/write-requirements` (명세서 작성) + `/design-review` 커맨드 (다중 에이전트 교차 리뷰)

**목적**: 브리프와 (있으면) Tech Research 결과를 기반으로 구현 명세를 확정하고, 교차 리뷰로 결함을 조기 발견한다.

### 선행 조건

- 대형 규모: `{feature}-tech-research.md`가 존재해야 한다. 없으면 `/write-requirements`가 거부한다.
- 중형 규모: `tech-research.md`가 있으면 자동으로 읽어 인용한다. 없으면 진행 가능하지만 권장하지 않는다.
- 소형 규모: `tech-research.md`는 요구되지 않는다.

### 산출물

| 파일 | 위치 | 상태 | 담당 커맨드 |
|---|---|---|---|
| `{feature}-requirements.md` | `docs/features/{group}/` | 신규 — frontmatter `status: draft` 포함 | `/write-requirements` |
| `{feature}-design-review.md` | `docs/features/{group}/` | 신규 — frontmatter `status: reviewed` (생성 즉시) | `/design-review` |
| `{feature}-tech-research.md` | `docs/features/{group}/` | 업데이트 — `status: applied`, `applied_at` 추가 (인용 시) | `/write-requirements` |
| `docs/canonical/ADR.md` | — | 업데이트 (아키텍처 결정 포함 시) |

### requirements.md 포함 항목

- **의존 시스템**: 영향받거나 영향 주는 시스템 목록
- **범위 외**: 명시적으로 제외하는 것
- **리서치 시사점**: tech-research.md 결론을 그대로 인용 (있는 경우)
- **(자원/loop이 있는 도메인) Resource flow loop**: brief의 표를 그대로 가져오되 모든 `???` 셀이 해소되어야 함. 한 셀이라도 `???` 남으면 requirements를 `applied`로 전환할 수 없다.
- acceptance criteria
- data contract:
  - 신규/확장 데이터 정의 파일명과 loader 연결 지점
  - 정적 / 인스턴스 state 구분
  - 식별 키 / 텍스트 키 네이밍 패턴
  - optional 필드 default 처리 방침
  - 관련 validation script 목록 또는 신규 작성 계획
- UI 표면 명세 (UI 포함 시)

### 완료 조건

- requirements.md 동결
- 설계 질문 전부 해소
- data contract 명시 완료

---

## Stage 5: Phase 계획

**대상 규모**: 소형 이상
**담당**: `/plan-phase` 커맨드 → `{{AGENT_PREFIX}}-phase-orchestrator` 위임

**목적**: 구현 단위(Phase)를 step으로 분해하고, 각 step의 acceptance criteria를 확정한다.

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `phases/{phase}/README.md` | — | 신규 — 목표, 범위, related_docs 링크, 완료 기준 |
| `phases/{phase}/index.json` | — | 신규 — step 목록 + 상태 + depends_on/blocks + `pending_manual_qa_scenarios: []` |
| `phases/{phase}/step{N}.md` | — | 신규 — 범위, acceptance criteria, 금지사항, 수동 테스트, 수동 QA owner, 주 담당 에이전트 |
| `phases/index.json` | — | 업데이트 — 신규 phase 엔트리 등록 필수 |
| `docs/PHASE_MAP.md` | — | 업데이트 — phase 행 추가 |

### README.md 필수 항목

- `related_docs`: brief + (있으면) discovery-research + (있으면) tech-research + requirements.md 링크 (추적 체인 연결)
- 목표, 범위, 완료 기준

### index.json phase 엔트리 스키마

```json
{
  "dir": "{phase-name}",
  "status": "pending",
  "feature_group": "...",
  "related_docs": ["docs/features/.../...-brief.md", "docs/features/.../...-requirements.md"],
  "depends_on": [],
  "blocks": [],
  "manual_qa_required": true,
  "archive_target": true,
  "pending_manual_qa_scenarios": []
}
```

`pending_manual_qa_scenarios`는 phase 시작 시 빈 배열로 초기화한다. 에이전트가 정적으로 확인 불가한 시나리오가 step 진행 중 발견되면 한 줄씩 누적한다. phase 끝 일괄 보고의 핵심 입력.

### step.md 필수 항목

- 읽을 파일
- 작업 범위
- 영향받는 데이터 정의 목록 (data 변경 시)
- acceptance criteria
- 금지사항
- 수동 테스트 절차 (핵심 경로 명시)
- **수동 QA owner**: `사용자` / `에이전트 정적 분석` / `둘 다`
- **주 담당 에이전트**

### step 상태 머신 (phase 단위 일괄 QA 기본)

기본 흐름 (모든 step):
```
pending → in_progress → completed         (정적 검증 통과 시 바로 전환)
                     ↘ error / blocked / paused
```

에이전트가 정적으로 확인 불가한 시나리오 (런타임 실행·시각/동작·시간 의존)는 step status를 차단하지 않고 phase index.json의 `pending_manual_qa_scenarios` 배열에 한 줄씩 누적한다. phase 끝에서 사용자가 일괄 수동 QA.

예외 — step 단위 QA 강제 (`qa_blocking: true` step):
```
pending → in_progress → implemented_pending_manual_qa → completed
                     ↘ error / blocked / paused
```

이 예외는 save 계약·core 경로·통합 진입 파일 본문을 건드려 phase 끝까지 미루면 회귀 복구가 어려운 step, 또는 사용자가 "여기서 일시 정지" 명시한 step에만 적용. phase index.json의 해당 step 항목에 `qa_blocking: true` 명시.

phase 종료 직전 일괄 사용자 검토는 Stage 7 QA Cadence 참조.

### 완료 조건

- 모든 step 정의됨
- 각 step에 acceptance criteria + 수동 QA owner 명시됨
- `phases/index.json`에 phase 엔트리 등록됨
- `related_docs`의 brief.md + requirements.md frontmatter → `status: frozen` 업데이트

### 스켈레톤 허용 — 다단 phase 계획 시

복수 phase가 직렬·병렬로 묶인 큰 계획에서는 **즉시 진입 직전 phase의 step.md만 표준 형태(읽을 파일·작업 범위·AC·금지·수동 테스트·QA owner·주 담당 에이전트)로 완비**하고, 후속 phase의 step.md는 다음 항목만 갖춘 스켈레톤으로 둘 수 있다:

- 제목 + 추적 한 줄(`README.md → requirements.md`)
- index.json의 `summary` 인용 또는 1~2문장 요약
- `maps_to_ac` 또는 핵심 AC 연결
- 주 담당 에이전트 + QA owner
- (선택) 가드레일 1~3줄

스켈레톤은 해당 phase 진입 직전(Stage 6 시작 전)에 `_template/step.md` 형식으로 보강 의무. phase README의 "완료 기준"이나 phase index.json `creation_note`에 "후속 phase step.md 보강은 진입 직전" 정책을 명시한 경우만 적용한다.

---

## Stage 6: 구현 (step 단위 반복)

### 에이전트 선택 기준

| 작업 성격 | 담당 에이전트 |
|---|---|
| 도메인 로직 전담 | `{{AGENT_PREFIX}}-implementer` |
| UI/표면 레이아웃 전담 | `{{AGENT_PREFIX}}-ui-specialist` |
| data/schema/설정 전담 | `{{AGENT_PREFIX}}-data-steward` |
| 도메인 로직 + 데이터 혼합 | `{{AGENT_PREFIX}}-implementer` (data 항목 별도 확인) |
| 도메인 로직 + UI 표시 혼합 | `{{AGENT_PREFIX}}-implementer` (UI 전용 계산 분리 금지 — CLAUDE.md 규칙) |
| 순수 UI 레이아웃 변경 | `{{AGENT_PREFIX}}-ui-specialist` |

step 작성 시 `step{N}.md`의 "주 담당 에이전트" 필드에 미리 지정한다.

### 산출물

| 파일 | 위치 | 조건 |
|---|---|---|
| 코드 | `scripts/`, `data/`, `scenes/` (도메인에 따라 경로 변경) | 항상 |
| `validate_{phase}_contract.ps1` | `scripts/` | 시스템 계약 변경 시 신규/갱신 |
| `phases/{phase}/index.json` | — | 항상 — step status 갱신 |
| 관련 docs | `docs/system-maps/`, `docs/features/` | 계약 변경 시 |

### 시스템 계약 변경 정의

다음 중 하나 이상이면 계약 변경:

- 데이터 정의 파일에 새 최상위 필드 추가/제거
- 공개 함수 시그니처 변경 또는 신규 공개 함수 추가
- save/저장 구조 변경 (신규 키, 제거 키, 타입 변경)
- 모듈 간 경계(예: 통합 진입 파일이 소유하는 상태)가 바뀌는 경우

### Step DoD (에이전트가 확인)

```
□ step.md의 acceptance criteria 전부 충족
□ step.md의 수동 테스트 목록 기준으로 핵심 경로 회귀 없음 확인
□ 새 visible/공개 text → 등록 catalog/locale 파일에 모두 추가 (해당 시)
□ save/저장 계약 변경 시: 기존 데이터 normalize 경로 코드 확인
□ 새 루프/전체 스캔 추가 시: tick budget/backoff 여부 step.md에 명시
□ 새 데이터 필드 → 정적(저장 제외) / 인스턴스 state(저장 포함) 구분 명시
□ 시스템 계약 변경 시: 관련 docs/ 갱신 + validate_*.ps1 갱신
□ phases/{phase}/index.json step status 갱신:
   - 기본: → completed (정적 검증 통과 시 바로 전환)
   - 에이전트 정적 확인 불가 시나리오는 같은 index.json의 pending_manual_qa_scenarios 배열에 한 줄 추가
   - qa_blocking: true step (예외): → implemented_pending_manual_qa (사용자 QA 요청 보고)
```

### step 수정 절차

| 수정 종류 | 절차 |
|---|---|
| 범위 축소 | step.md에 `scope_note` 추가 + index.json `scope_revision_note` 기록. 사용자 확인 없이 진행 가능 |
| step 번호 재정렬 / step 추가 | `{{AGENT_PREFIX}}-phase-orchestrator` 재호출 또는 사용자 확인 |
| acceptance criteria 변경 | 사용자 확인 필수. brief/requirements.md 변경 없이 step.md만 수정 불가 |

---

## Stage 7: Review & QA

**목적**: 구현 검증, 회귀 탐지

### 기획서 동기화 (Design doc sync)

구현 도중 brief.md / requirements.md / sub-brief / 통합 brief 에 박혀 있지 않은 **신규 내용** (신규 UI element / 신규 입력 / 신규 catalog/schema field / 신규 사용자 명령 / 신규 규칙 / 신규 분기 등) 이 추가되면 반드시 기획 문서를 동기화한다. 구현만 하고 기획서를 비워두는 것은 차단 조건.

**필수 절차** (구현 PR DoD 에 포함):

1. **기획 문서 먼저 업데이트** — 신규 항목을 해당 brief / requirements / sub-brief 본문에 한 단락 또는 한 항목으로 추가.
2. **frontmatter 갱신** — `last_updated_at: "YYYY-MM-DD"` 필드 추가/갱신.
3. **Changelog 섹션** — 기획 문서 맨 아래에 `## Changelog` (없으면 신설) + 한 줄: `- YYYY-MM-DD: 변경 내용 한 줄 (사유 + 영향 범위)`.
4. **Acceptance Criteria 영향 확인** — AC 본문이 영향 받으면 해당 AC 끝에 `(YYYY-MM-DD 추가)` 표기. 신규 AC 가 필요하면 추가.
5. **표시 텍스트/i18n 동시 등록** — 신규 사용자 입력/UI 라벨이 추가됐다면 같은 PR 에서 등록 (도메인별 localization/문구 catalog).
6. **별도 phase 분리 판단** — 추가 내용이 1~3 step 이상의 규모면 새 phase 생성, 기존 기획서에는 "후속 phase 분리: `{phase-name}` 참조" 한 줄만 추가하고 본문 상세는 새 phase 의 README/requirements 에 둔다.

### Step 진입 자동화

한 step 완료 후 다음 step 진입에 **사용자 확인을 묻지 않는다.** 다음 "차단 조건" 중 하나만 해당할 때 멈추고 사용자에게 확인 요청:

| 차단 조건 | 행동 |
|---|---|
| 회귀 발견 (사용자 보고 또는 에이전트 검증 실패) | 즉시 핫픽스 → `phases/_hotfix-log/` 기록 → 사용자에게 진행 여부 확인 |
| 단정 불가능한 design decision (sub-brief/tech-research/requirements에 박힌 결정만으로 결정 못 하는 분기) | 멈추고 옵션 1~3개 제시, 사용자 결정 |
| core 가정 흔들림 (save 계약·core 경로·통합 진입 파일 본문·anti-pattern 위반 위험) | 멈추고 위험 보고 |
| `qa_blocking: true` step | 해당 step만 일시 정지, 다른 step은 자동 진행 |
| phase 종료 직전 | 마지막 step 완료 후 phase 끝 일괄 QA 보고 |

위 조건에 해당하지 않으면 step → step 자동 진행. 각 step 완료 시 한 줄 결과 보고 (산출물 경로·핵심 결정·다음 step 라벨)만 출력하고 즉시 다음 step 진입.

### QA Cadence — phase 단위 일괄 QA 기본

step 단위 사용자 QA가 개발 속도를 저해한다는 피드백에 따라 **phase 단위 일괄 QA**가 기본값.

| 분류 | 조건 | QA 시점 |
|---|---|---|
| **기본 (모든 phase)** | 별도 조건 없음 | **phase 끝에서 한 번** — 각 step은 에이전트 정적 검증(산출물 정합성·validator 통과·schema 파싱·코드 inspection 회귀 확인·헤드리스 빌드 등) 통과 시 바로 `completed`. 에이전트 정적 확인 불가 시나리오는 phase index.json `pending_manual_qa_scenarios` 배열에 누적. phase 끝에 일괄 보고. |
| **예외 — qa_blocking step** | 사용자가 "이 step 후 일시 정지" 명시 / save 계약·core 경로·통합 진입 파일 본문 건드림 / phase 끝까지 미루면 회귀 복구 곤란 | **해당 step에서 일시 정지** — `implemented_pending_manual_qa` → 사용자 QA → `completed`. phase index.json의 step 항목에 `qa_blocking: true` 플래그 명시. |

**phase index.json 필수 필드**:

- `pending_manual_qa_scenarios: Array[String]` — 빈 배열로 초기화. 에이전트가 정적 확인 불가한 시나리오를 step 진행 중 누적. phase 끝 일괄 보고의 핵심 입력.
- 각 step 항목의 `qa_blocking: bool` (optional, 기본 false) — true일 때만 step 단위 QA 강제.
- 기존 `manual_qa_required: bool`는 phase 전체에 사용자 QA가 한 번이라도 필요한지 (즉 phase 끝 일괄 QA를 받을지) 의미로 유지. 정적 분석 only phase는 `manual_qa_required: false`.

**phase 끝 사용자 보고 항목** (모든 phase 공통):

1. 전체 변경 파일 diff 요약 (카테고리별)
2. step별 산출물·acceptance criteria 충족 cross-check 표
3. `pending_manual_qa_scenarios` — 사용자가 런타임에서 직접 확인해야 할 시나리오 목록 (시각/동작·시간 의존·UI 렌더·save round-trip 등)
4. phase 도중 발견·핫픽스 처리된 회귀 (`phases/_hotfix-log/` 링크)
5. 다음 phase 진입 입력 (helper 명세·신규 식별 키·SAVE_VERSION bump 시점 등)

### 담당 분리

| 역할 | 담당 | 내용 |
|---|---|---|
| 정적 검토 | `{{AGENT_PREFIX}}-qa-reviewer` | acceptance criteria 항목별 코드 검토, 데이터 키 등록 확인, git diff --check, 데이터 파싱 검증 |
| 런타임 수동 실행 | **사용자 (필수, 에이전트 대체 불가)** | 런타임 동작, 시각적 확인, 핵심 경로 수동 테스트 |

### 수동 QA 체크리스트 (사용자 — phase 끝 일괄)

phase 끝 일괄 보고를 받은 시점에 phase index.json의 `pending_manual_qa_scenarios` 배열을 순회하며 다음 항목을 함께 확인:

```
□ pending_manual_qa_scenarios 배열의 각 시나리오를 런타임에서 재현
□ i18n/locale 전환 후 새 키 렌더 이상 없음, text clipping/fallback key 노출 없음 (visible text 변경 시)
□ 핵심 사용자 경로 회귀 없음 (성능·UI flicker 등 도메인별 추가 항목)
□ save → load 후 phase 내 신규 instance state 복원됨 (save 계약 변경 시)
□ phase 도중 발견된 핫픽스 (_hotfix-log/) 의 회귀 위험 종목 재확인
```

### 완료 조건

- **기본 흐름**: 각 step은 에이전트 정적 검증 통과 시 바로 `completed`로 전환. phase 끝에서 사용자가 `pending_manual_qa_scenarios` 일괄 QA 통과를 확인한 뒤 phase status `completed`로 전환.
- **qa_blocking step (예외)**: 해당 step만 사용자가 수동 QA 통과를 명시 확인한 뒤 `completed`로 전환. 그 외 step은 기본 흐름 유지.

### 산출물

| 파일 | 위치 | 조건 |
|---|---|---|
| `phases/{phase}/index.json` | — | 항상 — step status → `completed` |
| `{feature}-manual-verification-record.md` | `docs/history/{feature}/` | 중요 기능 해당 시 신규 |

### "중요 기능" 기준 — verification-record 생성 필수

다음 중 하나 이상이면 필수:

- 새 시스템 추가
- 기존 save 계약 변경
- 복수 phase가 의존하는 shared 시스템 수정
- 핵심 사용자 흐름에 영향
- HUD/UI 렌더 경로 변경

해당 없으면 step.md의 Pending Acceptance 항목 기록으로 대체 가능.

---

## Stage 8: Phase 완료

**담당**: `{{AGENT_PREFIX}}-docs-keeper`

**목적**: 추적 문서 동기화, phase 종결

### 산출물

| 파일 | 위치 | 상태 |
|---|---|---|
| `docs/implementation_status.md` | — | 업데이트 — 해당 시스템 행 갱신 |
| `docs/PHASE_MAP.md` | — | 업데이트 — phase status 동기화 |
| `phases/index.json` | — | 업데이트 — status = `"completed"`, `completed_at` 기록 |
| `docs/HISTORICAL_DOCS.md` | — | 업데이트 (중요 phase) |

### Phase DoD

**이 목록의 모든 항목 완료 전까지 Phase 완료 선언 금지:**

```
□ phases/{phase}/index.json에서 모든 step status = completed 확인 (게이트)
□ docs/implementation_status.md 해당 시스템 행 갱신
□ docs/PHASE_MAP.md phase status 동기화
□ phases/index.json status = "completed", completed_at 기록
□ (데이터 정의 추가/변경 시) DATA_MAP.md 또는 관련 시스템맵 동기화
□ (아키텍처/save 계약 변경 시) Stage 9 Canonical Sync 완료 또는 불필요 사유 명시
□ (중요 phase) HISTORICAL_DOCS.md 아카이브 등록
```

---

## Stage 9: Canonical Sync

**담당**: `{{AGENT_PREFIX}}-docs-keeper`
**실행**: 트리거 조건 충족 시만

**목적**: 아키텍처·데이터 계약 변경 시 canonical 문서를 코드 현실에 맞춘다.

### 트리거 조건 (하나 이상이면 실행)

- 새 시스템 추가
- 기존 시스템 ownership 변경
- save/저장 계약 변경
- 새 데이터 정의 파일 추가
- 핵심 loader/초기화 코드에 신규 호출 추가

### 산출물

| 파일 | 위치 | 조건 |
|---|---|---|
| `docs/canonical/ARCHITECTURE.md` | — | 시스템 추가/변경 시 |
| `docs/system-maps/` 관련 파일 | — | ownership 변경 시 |
| `docs/DATA_MAP.md` | — | 데이터 정의 추가/loader 변경 시 |

---

## 핫픽스 경로

**대상**: 1-2파일, 단일 버그, 시스템 계약 변경 없음
**phase 생성 없음**, `phases/index.json` 미등록
**경량 추적**: 완료 후 `phases/_hotfix-log/YYYY-MM-DD-{slug}.md` 한 건 작성 (`phases/_hotfix-log/_template.md` 복사). 계약 변경 발견 시 이 로그를 폐기하고 소형 이상으로 재분류.

### 핫픽스 DoD

```
□ 버그 재현 조건 확인
□ 원인 파일/함수 특정
□ 최소 변경 (1-2파일)
□ 변경된 시스템의 직접 경로 수동 확인
□ git diff --check 통과
□ (visible text 변경 시) 등록 catalog/locale 키 등록 확인
```

시스템 계약 변경이 없으면 `docs/implementation_status.md` 갱신 생략 가능.
시스템 계약 변경이 발견되면 소형 이상으로 재분류한다.

---

## Paused Phase 재개

재개는 사용자의 명시적 요청이 있을 때만 진행한다.

```
1. phases/index.json에서 active_step + 중간 step 상태 확인
2. requirements.md 변경 여부 확인 (신규 ADR 발생 시 Stage 4 재검토)
3. pause 이후 새로 추가된 의존성 phase 완료 여부 확인
4. active_step의 step.md acceptance criteria 재확인
5. Stage 6(구현)부터 재개
```

---

## 추적 체인 (Traceability Chain)

모든 단계의 산출물은 아래 체인으로 연결된다. 체인이 끊기면 추적이 불가능해진다.

```
{feature}-discovery-research.md       (/research discovery — 대형 필수, 중형 선택)
  └─→ {feature}-brief.md              (Discovery 결론 인용)
        ├─→ {feature}-tech-research.md       (/research technical — 대형 필수, 중형 선택)
        ├─→ {feature}-design-review.md       (/design-review 입력·출력)
        └─→ {feature}-requirements.md        (기술 스펙, data contract — tech-research 시사점 인용)
              └─→ phases/{phase}/README.md   (related_docs 링크 필수)
                    └─→ phases/{phase}/step{N}.md   (acceptance criteria)
                          ├─→ scripts/ · data/ · scenes/   (코드 — 도메인 경로)
                          └─→ scripts/validate_{phase}_contract.ps1
                                └─→ phases/{phase}/index.json   (step status)
                                      └─→ docs/history/{feature}/*-verification-record.md
                                            ├─→ docs/implementation_status.md
                                            ├─→ docs/PHASE_MAP.md
                                            └─→ docs/HISTORICAL_DOCS.md
```

### 체인 유지 규칙

1. `phases/{phase}/README.md`의 `related_docs`에 brief + (있으면) discovery-research + (있으면) tech-research + requirements.md 링크 필수
2. `step{N}.md`에 영향받는 데이터 정의 목록 명시 → data 추적선 유지
3. `validate_*.ps1`은 시스템 계약 변경 시 반드시 갱신
4. 완료된 phase의 `related_docs` 파일이 이동/삭제되면 링크 업데이트 필수
5. `{feature}-design-review.md`는 설계 증거로만 읽는다. 현재 계약으로 오독하지 않는다.

---

## 단계별 산출물 집계 (대형 기준)

| 단계 | 신규 파일 | 수정 파일 |
|---|---|---|
| Stage 0 Discovery Research | `{feature}-discovery-research.md` | `docs/DOC_MAP.md` |
| Stage 1 브리프 | `{feature}-brief.md` | `design_review_questions.md`, `discovery-research.md` (status → applied) |
| Stage 2 Concept | — | `design_review_questions.md` |
| Stage 3 Tech Research | `{feature}-tech-research.md` | `docs/DOC_MAP.md` |
| Stage 4 설계 | `{feature}-requirements.md`, `{feature}-design-review.md` | `ADR.md` (선택), `tech-research.md` (status → applied) |
| Stage 5 Phase 계획 | `README.md`, `index.json`, `step1~N.md` | `phases/index.json`, `PHASE_MAP.md` |
| Stage 6 구현 (×N) | 코드, `validate_*.ps1` (계약 변경 시) | `phases/{phase}/index.json`, 관련 docs |
| Stage 7 QA (×N) | `*-verification-record.md` (조건 충족 시) | `phases/{phase}/index.json` |
| Stage 8 완료 | — | `implementation_status.md`, `PHASE_MAP.md`, `phases/index.json`, `HISTORICAL_DOCS.md` |
| Stage 9 Sync (선택) | — | `ARCHITECTURE.md`, `system-maps/`, `DATA_MAP.md` |

중형은 Stage 0·3을 건너뛸 수 있고(권장하지 않음), Stage 1 브리프 대신 곧장 Stage 2 진입도 가능하다. 소형은 Stage 5부터 시작한다. 핫픽스는 Stage 6 직행.
