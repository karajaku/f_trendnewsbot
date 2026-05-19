# Phase 02 · Step 3 — env var rename ANTHROPIC_API_KEY → GEMINI_API_KEY

> 목적: 환경변수 이름과 운영자 가이드를 Gemini 기준으로 갱신. 기획 문서 동기화 (CLAUDE.md "기획서 동기화" 정책).
> 주 담당 에이전트: tnb-implementer

## 읽을 파일

- `src/run_daily.py` (REQUIRED_ENV_VARS 튜플)
- `.github/workflows/daily.yml` (env 블록·secrets 참조)
- `docs/ops/secrets_setup.md` (운영자 가이드 — 가장 큰 변경량)
- `docs/canonical/PRD.md` (운영 환경 섹션)
- `docs/canonical/ARCHITECTURE.md` (모듈 ownership · 의존 시스템)
- `docs/features/daily_digest/daily_digest_v1-requirements.md` §8 (env var 목록)

## 작업 범위

1. `src/run_daily.py`:
   - `REQUIRED_ENV_VARS` 에서 `"ANTHROPIC_API_KEY"` → `"GEMINI_API_KEY"`
   - `env["ANTHROPIC_API_KEY"]` 참조도 같이 변경
   - `os.environ.get("CLAUDE_MODEL_ID", DEFAULT_MODEL)` → `os.environ.get("GEMINI_MODEL_ID", DEFAULT_MODEL)` (변수명 일관성)
2. `.github/workflows/daily.yml`:
   - `env:` 블록 (또는 `with:`)의 `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}` → `GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}`
   - `CLAUDE_MODEL_ID` (variables 참조) → `GEMINI_MODEL_ID`
3. `docs/ops/secrets_setup.md`:
   - "Anthropic API key 발급" 섹션 → "Google Gemini API key 발급" (https://aistudio.google.com/app/apikey)
   - GitHub Secrets 등록 항목 표 갱신: `ANTHROPIC_API_KEY` 행 삭제 + `GEMINI_API_KEY` 행 추가
   - Variables 표의 `CLAUDE_MODEL_ID` → `GEMINI_MODEL_ID`
   - "확인 체크리스트" 6항목 중 LLM 관련 항목 표현 갱신
   - 마이그레이션 안내 추가: "기존에 `ANTHROPIC_API_KEY` Secret 등록한 경우 삭제 + `GEMINI_API_KEY` 추가"
4. `docs/canonical/PRD.md`:
   - "AI 요약 모델 — Anthropic Claude Haiku 4.5" 표기 → "Google Gemini 2.0 Flash (ADR-004)"
   - 운영 비용 섹션이 있다면 "무료 tier로 운영" 명시
5. `docs/canonical/ARCHITECTURE.md`:
   - 외부 의존 시스템 표 (Anthropic API 행) → Google Gemini API 행
   - summarizer 모듈 ownership 표의 SDK 이름 갱신
6. `docs/features/daily_digest/daily_digest_v1-requirements.md`:
   - §8 환경변수 목록 표: `ANTHROPIC_API_KEY` → `GEMINI_API_KEY`, `CLAUDE_MODEL_ID` → `GEMINI_MODEL_ID`
   - frontmatter `last_updated_at: "2026-05-19"` 갱신
   - `## Changelog` 섹션에 한 줄 추가: `- 2026-05-19: ADR-004 반영 — LLM provider Anthropic → Gemini 2.0 Flash, env var 이름 변경 (AC-5.5·§8)`
   - AC-5.5 본문에 `(2026-05-19 갱신)` 표기

## Acceptance Criteria

- AC-S3.1: 전체 grep으로 `ANTHROPIC_API_KEY` 0건, `CLAUDE_MODEL_ID` 0건 (docs/canonical/ADR.md 의 ADR-001·ADR-004 본문 사례 외).
- AC-S3.2: `GEMINI_API_KEY` 가 src/run_daily.py·workflow·secrets_setup·PRD·ARCHITECTURE·requirements 6개 위치에 모두 등장.
- AC-S3.3: requirements frontmatter `last_updated_at` + Changelog 한 줄 갱신.
- AC-S3.4: `python scripts/validate_doc_status.ps1` 통과.

## 금지

- src/summarizer/client.py 추가 수정 (step2에서 처리 완료).
- DEFAULT_MODEL 값 변경 (step2에서 처리 완료).

## 수동 테스트

- 없음 (qa_blocking: false). step4에서 dry-run 통합 검증.

## QA owner

- 정적 검증: ripgrep 패턴 매칭 + validate_doc_status.ps1.
