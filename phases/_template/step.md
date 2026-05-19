# Step {N}: {step-name}

> 추적: `phases/{phase}/README.md` → `docs/features/{group}/{feature}-requirements.md`

## 읽을 파일

- `CLAUDE.md`
- `docs/canonical/DEV_PROCESS.md`
- `phases/{phase}/README.md`
- `docs/features/{group}/{feature}-requirements.md`
- {관련 코드/데이터 파일 — 검색 도구로 실제 경로 확인}

## 작업 범위

{이 step에서 변경하는 것을 구체적으로 기술. 애매하면 acceptance criteria로 대체.}

## 영향받는 데이터 정의 목록

> 데이터 변경 없으면 "없음"으로 표기

- `{data-file-path}` — {변경 내용: 신규 필드 / 값 추가 / 구조 변경}

## Acceptance Criteria

- [ ] {기준 1 — 검증 가능한 단일 조건}
- [ ] {기준 2}

## 금지사항

- {이 step에서 건드리지 않는 시스템/파일}
- {명시 요청 없이 하지 않는 것}

## 수동 테스트 절차

> 핵심 경로(golden path)와 경계 조건을 명시한다.

1. {테스트 시나리오 1 — 어디서 무엇을 실행하고 무엇을 확인하는지}
2. {테스트 시나리오 2}

## 수동 QA Owner

> `사용자` / `에이전트 정적 분석` / `둘 다`

{선택 및 이유: 런타임 실행이 필요하면 반드시 `사용자`. 파일/데이터 검증만이면 `에이전트 정적 분석`.}

## 주 담당 에이전트

> `tnb-implementer` / `tnb-ui-specialist` / `tnb-data-steward` / `tnb-docs-keeper` / `tnb-performance-investigator`

{선택. 혼합 step이면 역할 분담을 명시한다.}

## 회귀 위험

{이 step 변경으로 영향받을 수 있는 인접 시스템 또는 흐름}

---

## Step DoD 체크 (에이전트 확인용)

```
□ acceptance criteria 전부 충족
□ 수동 테스트 목록 기준으로 핵심 경로 회귀 없음 확인
□ 새 visible text → 등록 catalog/locale 파일에 모두 추가 (해당 시)
□ save/저장 계약 변경 시: 기존 데이터 normalize 경로 코드 확인
□ 새 루프/전체 스캔 추가 시: tick budget/backoff 여부 이 파일에 명시
□ 새 데이터 필드 → 정적(저장 제외) / 인스턴스 state(저장 포함) 구분 명시
□ 시스템 계약 변경 시: 관련 docs/ 갱신 + validate_*.ps1 갱신
□ phases/{phase}/index.json step status → implemented_pending_manual_qa
□ 사용자에게 Stage 5 수동 QA 요청을 명시적으로 보고
```
