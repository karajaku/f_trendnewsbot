# 문서 시스템 가이드

> 역할: f_trendnewsbot 문서 시스템의 구조, 계층, 활용법을 설명하는 설명서.
> 대상: 새 작업을 시작하기 전 문서 체계를 파악할 때. 새 문서를 추가하거나 기존 문서를 갱신할 때.

---

## 1. 이 문서 시스템이 존재하는 이유

f_trendnewsbot 프로젝트는 Claude와 협업하며 개발한다. Claude는 매 대화마다 컨텍스트가 초기화된다.

따라서 다음 두 가지가 동시에 필요하다.

- **Claude가 읽을 문서**: 작업 전 최소한의 맥락을 빠르게 파악할 수 있어야 한다.
- **사람이 읽을 문서**: 설계 결정의 이유와 현재 상태를 추적할 수 있어야 한다.

이 문서 시스템은 그 두 가지 요구를 동시에 충족하도록 설계됐다.

---

## 2. 문서 계층과 신뢰 우선순위

충돌이 생기면 아래 순서로 우선한다. 위가 높을수록 권위가 강하다.

```
CLAUDE.md                  ← 항상 최우선. 프로젝트 안전 규칙과 도메인 제약.
  ↓
Canonical Contracts        ← 제품 목표, 아키텍처, 장기 결정. 자주 바뀌지 않는다.
  ↓
System Maps                ← 현재 구현 owner와 흐름. 코드 탐색 기준.
  ↓
Feature Requirements       ← 특정 기능의 acceptance criteria와 데이터 계약.
  ↓
Phase Steps                ← 현재 진행 중인 구현 계획. 가장 세부적이고 자주 바뀐다.
  ↓
설계 참조                   ← 방향 확인용. source of truth가 아니다.
  ↓
Historical Evidence        ← 과거 검증 증거. 현재 계약이 아니다.
  ↓
_legacy/                   ← 더 이상 읽지 않는다.
```

**핵심 원칙**: 더 구체적이고 최신인 문서가 추상적이고 오래된 문서를 이긴다.

---

## 3. 각 문서 유형 설명

### CLAUDE.md

모든 작업의 첫 번째 읽기. 프로젝트 전체에 걸친 안전 규칙, 도메인 제약, 개발 프로세스.

이 파일의 규칙은 다른 어떤 문서도 무효화할 수 없다.

### Canonical Contracts (`docs/canonical/`)

현재 제품 기준을 정의한다. 큰 설계 변경이나 새 시스템 추가 전 반드시 확인.

| 파일 | 언제 읽나 |
|---|---|
| `PRD.md` | 제품 목표와 MVP 범위 확인 시 |
| `ARCHITECTURE.md` | 코드 구조, 시스템 ownership 확인 시 |
| `ADR.md` | "왜 이렇게 결정했는가" 확인 시 |
| `DEV_PROCESS.md` | 개발 프로세스 전체 흐름 확인 시 |

### System Maps (`docs/system-maps/`)

"이 기능의 코드가 어디 있는가", "누가 이 UI를 소유하는가"를 찾을 때.

Canonical보다 더 자주 갱신된다. 코드 탐색의 출발점이다.

### Feature Requirements (`docs/features/{group}/`)

특정 기능의 구현 기준. acceptance criteria, 데이터 계약, UI 표면, 저장/로드 조건을 포함한다.

기능을 구현하거나 검증할 때 이 문서를 source of truth로 삼는다.

### Phase Steps (`phases/{phase}/`)

현재 진행 중인 구현의 세부 계획. `phases/index.json`이 라우팅 source of truth.

### Historical Evidence (`docs/history/`)

과거 preflight, verification, manual QA record. **현재 계약이 아니다.**

---

## 4. 작업 전 읽기 흐름

### 모든 작업 공통

```
CLAUDE.md → docs/DOC_MAP.md → 작업 유형별 문서
```

상세한 작업 유형별 읽기 순서는 `docs/AGENT_READ_ORDER.md`를 따른다.

### Phase 이어받기

```
phases/index.json → 대상 phase README → index.json → stepN.md
```

### 새 기능 구현

```
Canonical Contracts → System Map → Feature Requirements → Phase Step
```

---

## 5. 새 문서 만들기

새 문서를 만들 때 반드시 두 단계를 완료한다.

### 단계 1: 파일 상단 헤더 작성

```markdown
# 문서 제목

> 역할: 이 문서가 무엇을 하는 문서인가 — 한 줄로.
> 대상: 어떤 작업/상황에서 이 문서를 읽어야 하는가.
```

### 단계 2: DOC_MAP.md 등록

해당 섹션 표에 한 줄 추가한다.

---

## 6. 자주 하는 실수

### 실수 1: Historical Evidence를 현재 계약으로 읽기

`docs/history/`의 verification 문서는 "그때 맞았다"는 증거지, "지금도 맞다"는 기준이 아니다.

### 실수 2: DOC_MAP 없이 새 문서 추가하기

새 문서를 만들고 DOC_MAP에 등록하지 않으면 Claude가 다음 대화에서 그 문서의 존재를 모른다.

### 실수 3: 설계 참조 문서를 Feature Requirements처럼 사용하기

설계 분석 문서는 방향 참조용이다. 구현 acceptance criteria는 `docs/features/` 아래 요구사항 문서를 사용한다.

### 실수 4: Phase Step 없이 큰 기능 구현하기

큰 기능은 반드시 `phases/`에 step으로 나눠 상태를 추적한다. 중간에 멈추거나 재개할 때 컨텍스트를 복원할 수 없다.

---

## 관련 문서

| 문서 | 역할 |
|---|---|
| `CLAUDE.md` | 프로젝트 작업 규칙 전체 |
| `docs/DOC_MAP.md` | 모든 문서 목록과 위치 지도 |
| `docs/AGENT_READ_ORDER.md` | 작업 유형별 최소 읽기 순서 |
