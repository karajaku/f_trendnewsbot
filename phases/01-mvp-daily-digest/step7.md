# Step 7: run_daily.py 통합 + GitHub Actions workflow + Secrets 가이드

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-1.1·1.4·1.5·7.1·7.2·7.3

**qa_blocking: true** — 통합 진입 파일 + Secrets는 두 핵심 경로(CLAUDE.md anti-pattern B + CRITICAL #5)를 동시에 건드린다. 회귀 복구 어려움.

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) anti-pattern B (통합 진입 비대화), CRITICAL #5 (시크릿)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-1, AC-7, §8
- [docs/canonical/ADR.md](../../docs/canonical/ADR.md) ADR-001 (cron), ADR-002 (artifact)
- step1~6 산출물 전부

## 작업 범위

### `src/run_daily.py` — 통합 진입

5단계 호출만. 도메인 규칙 누적 금지(AC-7.3).

```python
def main():
    setup_logging()
    config = load_all()                                  # step2
    secrets_check()                                       # 시크릿 환경변수 6+1개 검증
    try:
        articles, fetch_failures = fetchers.run_all(config.sources)        # step3
        history = history_store.load()                                      # step4
        by_category = filters.pipeline.apply(articles, history, ...)        # step4
        digest = summarizer.build(by_category, fetch_failures, ...)         # step5
        send_result = dispatchers.email_gmail.send(digest, config.recipients)  # step6
        history_store.record(digest.items, digest.meta)                     # step4
    except QuotaExceededError as e:
        dispatchers.ops_alert.send_ops_alert("quota_exceeded", e, ...)
        sys.exit(2)
    except SendError as e:
        dispatchers.ops_alert.send_ops_alert("smtp_failed", e, ...)
        sys.exit(3)
    except Exception as e:
        dispatchers.ops_alert.send_ops_alert("unexpected", e, ...)
        sys.exit(99)
```

### `.github/workflows/daily.yml`

- cron: `30 22 * * *` (UTC, 매일) — 주석에 "= KST 익일 07:20 매일(토·일·공휴일 포함, 2026-05-19 사용자 결정)" (AC-1.1, AC-1.4, tech §3-4 권장 시각)
- `workflow_dispatch` 입력: `dry_run: bool` (기본 false)
- jobs:
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` (3.12)
  3. `pip install -e ".[]"`
  4. `actions/download-artifact@v4` (digest-history, 실패 시 빈 history 계속)
  5. `RECIPIENTS_YML_BASE64` decode → `config/recipients.yml`
  6. `python -m src.run_daily`
  7. `actions/upload-artifact@v4` `if: always()` — 실패해도 history 업로드 시도
- Secrets/Variables 참조: `${{ secrets.ANTHROPIC_API_KEY }}` 등 §8 명세대로

### `docs/ops/secrets_setup.md` — 운영자 가이드 (신규)

- Gmail 앱 비밀번호 생성 절차 (2FA → 앱 비밀번호)
- GitHub Repository Settings → Secrets and variables → Actions → New secret
- 7개 Secret + 2개 Variable 등록 체크리스트
- `RECIPIENTS_YML_BASE64` 생성 절차 (`base64 -w0 config/recipients.yml | clip`)
- 첫 dry-run 실행 절차 (Actions tab → daily.yml → Run workflow → dry_run=true)

### `.env.example` 보강

- `CLAUDE_MODEL_ID=claude-haiku-4-5-20251001`
- 모든 환경변수에 한국어 한 줄 설명 주석

## 영향받는 데이터 정의 목록

- `.github/workflows/daily.yml` — 신규 (정적, git tracked)
- `docs/ops/secrets_setup.md` — 신규 운영 문서
- 새 의존: GitHub Actions Secrets·Variables (운영 환경 — 코드 외)

## Acceptance Criteria

- [ ] `run_daily.main()` 본문이 위 5단계 호출 + 3개 except 핸들러로 한정 — 도메인 규칙 누적 0줄 (AC-7.3, anti-pattern B)
- [ ] `secrets_check()` 가 §8 6개 Secret + 1개 Variable 누락 시 `ConfigError(missing_env=...)` raise 후 직원 메일 발송 시도 안 함
- [ ] `daily.yml` cron 라인 바로 위에 KST 환산 주석 "(KST 익일 07:20 매일, 토·일·공휴일 포함)" 존재 (AC-1.1, CRITICAL #7)
- [ ] `daily.yml` 의 jobs.steps 마지막에 `actions/upload-artifact@v4` 가 `if: always()` 로 실행 (history 보장)
- [ ] `workflow_dispatch.inputs.dry_run` 입력 존재 + true 일 때 `recipients.yml` 의 `ops_alert` 그룹만 수신 (직원 메일 발송 안 함)
- [ ] `docs/ops/secrets_setup.md` 가 7+2 환경변수 모두 등록 절차 + `RECIPIENTS_YML_BASE64` 생성·검증 절차 명시
- [ ] `git status` 에서 `config/recipients.yml` 이 untracked 상태 유지 (`.gitignore` 작동 확인)
- [ ] `python -m src.run_daily` 가 시크릿 없는 로컬에서 `ConfigError` 메시지 명확히 출력하고 종료

## 금지사항

- `run_daily.py` 본문에 fetcher/filter/summarizer/dispatcher 로직 직접 작성 금지 — 호출만 (AC-7.3)
- workflow에 `--no-verify` `--no-gpg-sign` 등 hook 우회 금지
- `daily.yml` 안에 시크릿 평문 echo 금지 — `***` masking 활용
- `recipients.yml` 을 workflow가 commit 하는 동작 금지 (artifact에만 쓰는 게 ADR-002 결정)
- 코드 변경 없이 PRD·ARCHITECTURE 갱신 금지 — 본 step은 정합성 step8에서 처리

## 수동 테스트 절차

1. 로컬에서 `.env` 미설정 상태로 `python -m src.run_daily` → `ConfigError(missing_env="ANTHROPIC_API_KEY", ...)` 출력 + exit code 1
2. `.env` 채워서 로컬 dry-run (mock SMTP·mock Anthropic) → 정상 종료 + history `sent.jsonl` 생성
3. `daily.yml` lint: `actionlint` 또는 GitHub Actions UI에서 syntax OK
4. (실제 운영자 환경) Repository Settings → Secrets 등록 → Actions tab → "Run workflow" `dry_run=true` 1회 → 운영자 본인 메일 도착 + history artifact 생성

## 수동 QA Owner

**`사용자` (qa_blocking)** — 운영자가 직접 Secrets 등록 + 첫 `dry_run=true` 실행 + 본인 메일함에서 다이제스트 시각 확인 + Actions UI에서 artifact 확인. 이 step의 사용자 검증 없이 step8 진입 금지.

## 주 담당 에이전트

`tnb-implementer` (코드 통합) + `tnb-docs-keeper` (secrets_setup.md) 협업.

## 회귀 위험

- `run_daily.py` 본문이 시간 지나면서 비대해질 위험 — qa-reviewer가 `def main():` 본문 line 수 ≤ 40 가드 추가 권장.
- `daily.yml` cron 시각을 변경할 때 KST 주석 갱신 누락 — qa-reviewer가 cron 라인 위 2줄 안에 "KST" 단어 검색.
- `RECIPIENTS_YML_BASE64` 디코드 실수로 `recipients.yml` 이 잘못된 yml → step2 loader가 명확한 에러로 잡음 (이미 AC).
- 운영자가 secrets_setup.md 따라가다 한 변수 누락 → `secrets_check()`가 명시적 에러로 차단.

## pending_manual_qa_scenarios 누적

- "운영자가 직접 7+2 환경변수 모두 등록 + dry_run=true 1회 실행 + 본인 메일 도착 확인 (step8 dry-run의 전제)"
- "Actions UI에서 cron 자동 실행 시각이 KST 07:30 ± 15분 안에 들어오는지 4주 모니터링 (step8 verification-record 에 평균·표준편차 기록)"
