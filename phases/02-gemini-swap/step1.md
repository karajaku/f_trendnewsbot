# Phase 02 · Step 1 — ADR-004 신설 + pyproject deps swap

> 목적: V1 LLM provider 전환의 의사결정을 ADR에 박고, dependencies를 swap.
> 주 담당 에이전트: tnb-implementer

## 읽을 파일

- `docs/canonical/ADR.md` (ADR-001·ADR-003의 forward reference 표기 추가)
- `pyproject.toml`
- `phases/02-gemini-swap/index.json` (현재 step 진입 사유)

## 작업 범위

1. `docs/canonical/ADR.md` 끝에 **ADR-004** 추가:
   - 제목: "V1 LLM provider — Anthropic Claude Haiku 4.5 → Google Gemini 2.0 Flash"
   - 상태: `accepted (ADR-001의 AI 요약 모델 결정을 supersede)`
   - 맥락·결정·결과·대안 4섹션. 무료 tier rate limit (15 RPM / 1500 RPD) 명시. V1 호출 규모 비교.
2. `docs/canonical/ADR.md` 의 ADR-001 상태 footer 갱신:
   - 기존: `superseded — V1 발송 채널 결정은 ADR-003에 의해 변경 ... 언어·인프라·AI 모델 결정 부분은 여전히 유효.`
   - 변경: `superseded — 발송 채널은 ADR-003, AI 요약 모델은 ADR-004에 의해 변경. 언어·인프라 결정은 여전히 유효.`
3. `pyproject.toml` dependencies swap:
   - 제거: `"anthropic>=0.40.0"`
   - 추가: `"google-genai>=0.3.0"` (Google GenAI SDK — Gemini 2.0+ 권장)
   - 다른 dependency는 그대로.
4. `pip install -e .` 로컬 재설치로 SDK 변경 확인 (선택 — step4에서 어차피 재설치).

## Acceptance Criteria

- AC-S1.1: ADR-004 본문이 ADR 표준 형식 4섹션을 충족한다.
- AC-S1.2: ADR-001 상태 footer가 ADR-004 supersede 사실을 반영한다.
- AC-S1.3: `pyproject.toml` dependencies에 `anthropic` 이 없고 `google-genai` 가 있다.

## 금지

- src/ 코드 수정 (step2에서).
- env var 이름 변경 (step3에서).

## 수동 테스트

- 없음 (qa_blocking: false).

## QA owner

- 정적 검증만: `git diff` + `grep -F "anthropic" pyproject.toml` 0건.
