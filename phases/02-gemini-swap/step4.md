# Phase 02 · Step 4 — pytest 회귀 + dry-run 검증 (qa_blocking)

> 목적: Gemini swap 결과를 unit·integration·실제 dry-run 3 단계로 검증. phase 01 step7 manual QA 재개 직전 단계.
> 주 담당 에이전트: tnb-implementer + tnb-qa-reviewer + 사용자 (운영자 액션 필요)

## 읽을 파일

- `tests/` 전체 (특히 `tests/summarizer/`)
- `phases/01-mvp-daily-digest/index.json` (step7 manual_qa_pending 항목 — 동일 절차 재실행)
- `docs/ops/secrets_setup.md` (Gemini 발급 절차 — step3에서 갱신됨)

## 작업 범위 (에이전트)

1. `tests/summarizer/` 회귀:
   - 기존 Anthropic mock (있다면) → google-genai mock으로 갱신
   - `response.text`·`response.usage_metadata.prompt_token_count` 형태 응답 mock
   - `ResourceExhausted` (또는 google.genai.errors.ClientError 429) → `QuotaExceededError` 변환 케이스 추가
2. 전체 pytest 회귀:
   - `pytest -q` → 99개 모두 pass (phase 01 step7 단계 기준)
   - 새 mock으로 summarizer 테스트도 통과
3. ruff·mypy 회귀:
   - `python -m ruff check src/`
   - `python -m mypy src/` (strict=false)
4. CI workflow yml 정합성 점검:
   - `python -c "import yaml; yaml.safe_load(open('.github/workflows/daily.yml', encoding='utf-8'))"` 파싱 OK
   - `GEMINI_API_KEY` 가 secrets·env 양쪽에 등장

## 작업 범위 (사용자 운영자 액션)

1. https://aistudio.google.com/app/apikey 접속 → Google 계정 로그인 → "Create API key" → 발급 (무료, 즉시).
2. GitHub repo → Settings → Secrets and variables → Actions:
   - Secrets: `ANTHROPIC_API_KEY` 삭제 + `GEMINI_API_KEY` 추가 (위에서 발급한 키)
   - Variables: `CLAUDE_MODEL_ID` 삭제 (있으면) + `GEMINI_MODEL_ID` 추가 (선택, 기본 `gemini-2.5-flash` — ADR-005 2026-05-19 swap. 항목 삭제 시 `run_daily.py` 가 빈 문자열을 `DEFAULT_MODEL` 로 fallback)
3. Actions 탭 → "daily" workflow → "Run workflow" → `dry_run: true` → Run.
4. 1~3분 후 운영자 단톡방 + Pages 확인 (아래 체크리스트).

## Acceptance Criteria

- AC-S4.1: pytest 회귀 전체 pass (회귀 0건).
- AC-S4.2: 운영자 단톡방에 정상 다이제스트 메시지 도착 (3 카테고리 헤드라인 + 요약 + Pages URL).
- AC-S4.3: 메시지의 Pages URL 클릭 시 Apple v3 디자인 HTML 페이지 렌더.
- AC-S4.4: gh-pages 브랜치에 `digest/2026-05-19.html` (또는 실행일자) 새 커밋 확인.
- AC-S4.5: Actions 로그 마지막 줄 `cron 종료 정상 — 발송 건수=N pages_url=...`.
- AC-S4.6: 직원 단톡방(TELEGRAM_CHAT_ID)에는 메시지 미도착 (dry-run이므로).
- AC-S4.7: sent.jsonl artifact 업로드 확인 (Actions run summary).

## 금지

- 코드 추가 변경 (step1~3에서 모두 완료). 회귀 발견 시 `phases/_hotfix-log/` 에 기록.

## 수동 테스트 (qa_blocking: true)

- 위 7개 AC 모두 사용자가 직접 확인. 통과 후 phase 02 status → completed.
- 통과 즉시 phase 01 step7도 동일 dry-run으로 검증된 셈 → phase 01 step7 → completed + step8 진입.

## QA owner

- 사용자 (운영자 액션 4개) + 에이전트 (pytest·ruff·mypy 자동 검증).
