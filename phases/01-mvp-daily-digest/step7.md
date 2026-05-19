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

5단계 호출만 + dispatcher 순서 강제 (ADR-003, AC-5.6). 도메인 규칙 누적 금지(AC-7.3).

```python
def main():
    setup_logging()
    config = load_all()                                  # step2 (sources.yml + filters.yml만)
    secrets_check()                                       # 시크릿 환경변수 5+2개 검증
    try:
        articles, fetch_failures = fetchers.run_all(config.sources)        # step3
        history = history_store.load()                                      # step4
        by_category = filters.pipeline.apply(articles, history, ...)        # step4
        digest = summarizer.build(by_category, fetch_failures, ...)         # step5
        # AC-5.6: Pages publish 성공 확인 후에만 텔레그램 발송
        pages_url = dispatchers.pages_publish.publish(digest, today_kst())  # step6 (ADR-003)
        dispatchers.telegram_send.send(digest, pages_url, ...)              # step6 (ADR-003)
        history_store.record(digest.items, digest.meta)                     # step4
    except QuotaExceededError as e:
        dispatchers.ops_alert.send_ops_alert("quota_exceeded", e, ...)
        sys.exit(2)
    except PagesPublishError as e:
        dispatchers.ops_alert.send_ops_alert("pages_failed", e, ...)
        sys.exit(3)
    except TelegramSendError as e:
        dispatchers.ops_alert.send_ops_alert("telegram_failed", e, ...)
        sys.exit(4)
    except Exception as e:
        dispatchers.ops_alert.send_ops_alert("unexpected", e, ...)
        sys.exit(99)
```

### `.github/workflows/daily.yml`

- cron: `30 22 * * *` (UTC, 매일) — 주석에 "= KST 익일 07:20 매일(토·일·공휴일 포함, 2026-05-19 사용자 결정)" (AC-1.1, AC-1.4, tech §3-4 권장 시각)
- `workflow_dispatch` 입력: `dry_run: bool` (기본 false). true 일 때 텔레그램 chat 목적지가 `OPS_ALERT_CHAT_ID`로 강제 (운영자만 받음)
- `permissions:` — `contents: write` (Pages publish를 위해 dispatcher가 git push 권한 필요, ADR-003)
- jobs:
  1. `actions/checkout@v4` (`fetch-depth: 0` 또는 충분히 — git history 필요)
  2. `actions/setup-python@v5` (3.12)
  3. `pip install -e ".[]"`
  4. `actions/download-artifact@v4` (digest-history, 실패 시 빈 history 계속)
  5. `python -m src.run_daily`
  6. `actions/upload-artifact@v4` `if: always()` — 실패해도 history 업로드 시도
- Secrets/Variables 참조: `${{ secrets.ANTHROPIC_API_KEY }}`, `${{ secrets.TELEGRAM_BOT_TOKEN }}`, `${{ vars.TELEGRAM_CHAT_ID }}` 등 §8 명세대로 (`RECIPIENTS_YML_BASE64` 제거됨)

### GitHub Pages 활성화 (1회 수동 설정, ADR-003)

운영자가 repo Settings에서 1회 설정:
1. Settings → Pages → Source: `Deploy from a branch`
2. Branch: `master` (또는 `main`), Folder: `/docs`
3. Save → 1~2분 후 `https://{owner}.github.io/f_trendnewsbot/`이 활성
4. dispatcher가 `docs/digest/YYYY-MM-DD.html`을 push하면 자동 배포

### `docs/ops/secrets_setup.md` — 운영자 가이드 (신규, ADR-003 갱신)

- **텔레그램 봇 발급**: `@BotFather` → `/newbot` → 봇 이름 결정(예: `farmboss_trend_bot`) → 토큰 받음
- **다이제스트 단톡방 생성**: 운영자가 단톡방 1개 만들고 봇 초대 (단톡방 검색 가능 여부 OFF, 비공개 그룹)
- **운영자 alert chat**: 봇과 1:1 chat 1개 또는 운영자 전용 다른 단톡방
- **chat_id 획득**: `curl https://api.telegram.org/bot{TOKEN}/getUpdates` 또는 `@RawDataBot` 활용 → `chat.id` 추출 (단톡방은 음수)
- **GitHub Pages 활성화**: Settings → Pages → Source `Deploy from a branch`, `master`, `/docs`
- **GitHub Repository Settings → Secrets and variables → Actions**:
  - Secrets 등록: `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`
  - Variables 등록: `TELEGRAM_CHAT_ID`, `OPS_ALERT_CHAT_ID`, `PAGES_BASE_URL`, `CLAUDE_MODEL_ID`
- **첫 dry-run 실행**: Actions tab → daily.yml → Run workflow → `dry_run=true` → 운영자 단톡방에 메시지 + Pages URL 확인

### `.env.example` 보강 (ADR-003 갱신)

```
ANTHROPIC_API_KEY=<your_anthropic_key>          # Claude API 인증
TELEGRAM_BOT_TOKEN=<bot_token_from_BotFather>   # 텔레그램 Bot API 인증
TELEGRAM_CHAT_ID=<negative_int>                  # 직원 다이제스트 단톡방 ID
OPS_ALERT_CHAT_ID=<int>                          # 운영자 alert 전용 chat ID
PAGES_BASE_URL=https://<owner>.github.io/f_trendnewsbot  # Pages base URL
CLAUDE_MODEL_ID=claude-haiku-4-5-20251001       # 모델 ID (변경 시 PR 없이 교체)
```

GMAIL_* / RECIPIENTS_YML_BASE64 / OPS_REPLY_TO는 V1에서 제거 (ADR-003).

## 영향받는 데이터 정의 목록

- `.github/workflows/daily.yml` — 신규 (정적, git tracked, `permissions.contents: write` 명시)
- `docs/ops/secrets_setup.md` — 신규 운영 문서 (텔레그램·Pages 가이드)
- 새 의존: GitHub Actions Secrets/Variables (운영 환경 — 코드 외), GitHub Pages 설정 (1회 수동)

## Acceptance Criteria

- [ ] `run_daily.main()` 본문이 위 5단계 호출 + 3개 except 핸들러로 한정 — 도메인 규칙 누적 0줄 (AC-7.3, anti-pattern B)
- [ ] `secrets_check()` 가 §8 2개 Secret + 4개 Variable 누락 시 `ConfigError(missing_env=...)` raise 후 직원 발송 시도 안 함
- [ ] `daily.yml` cron 라인 바로 위에 KST 환산 주석 "(KST 익일 07:20 매일, 토·일·공휴일 포함)" 존재 (AC-1.1, CRITICAL #7)
- [ ] `daily.yml` 의 jobs.steps 마지막에 `actions/upload-artifact@v4` 가 `if: always()` 로 실행 (history 보장)
- [ ] `workflow_dispatch.inputs.dry_run` 입력 존재 + true 일 때 텔레그램 chat 목적지가 `OPS_ALERT_CHAT_ID`로 강제 (직원 단톡방 발송 안 함)
- [ ] `daily.yml`에 `permissions: contents: write` 명시 (Pages publish git push 권한)
- [ ] `docs/ops/secrets_setup.md` 가 텔레그램 봇 발급·단톡방 chat_id 획득·Pages 활성화·6개 환경변수 등록 절차 모두 명시
- [ ] `python -m src.run_daily` 가 시크릿 없는 로컬에서 `ConfigError(missing_env=...)` 메시지 명확히 출력하고 종료
- [ ] `run_daily.main()` 본문이 Pages publish → 텔레그램 send 순서로 호출 (AC-5.6 강제)

## 금지사항

- `run_daily.py` 본문에 fetcher/filter/summarizer/dispatcher 로직 직접 작성 금지 — 호출만 (AC-7.3)
- workflow에 `--no-verify` `--no-gpg-sign` 등 hook 우회 금지
- `daily.yml` 안에 시크릿 평문 echo 금지 — `***` masking 활용
- `recipients.yml` 을 workflow가 commit 하는 동작 금지 (artifact에만 쓰는 게 ADR-002 결정)
- 코드 변경 없이 PRD·ARCHITECTURE 갱신 금지 — 본 step은 정합성 step8에서 처리

## 수동 테스트 절차

1. 로컬에서 `.env` 미설정 상태로 `python -m src.run_daily` → `ConfigError(missing_env="ANTHROPIC_API_KEY" 또는 "TELEGRAM_BOT_TOKEN" ...)` 출력 + exit code 1
2. `.env` 채워서 로컬 dry-run (mock 텔레그램·mock Anthropic·로컬 git repo) → 정상 종료 + history `sent.jsonl` 생성 + `docs/digest/YYYY-MM-DD.html` 작성
3. `daily.yml` lint: `actionlint` 또는 GitHub Actions UI에서 syntax OK + `permissions: contents: write` 확인
4. (실제 운영자 환경) BotFather 토큰 발급 → 단톡방 생성·봇 초대·chat_id 획득 → Repository Settings → Secrets·Variables 등록 → Pages 활성화 → Actions tab → "Run workflow" `dry_run=true` 1회 → 운영자 단톡방에 메시지 + Pages URL 도착 + history artifact 생성

## 수동 QA Owner

**`사용자` (qa_blocking)** — 운영자가 직접 BotFather 토큰 발급·단톡방 생성·Pages 활성화·Secrets 등록 + 첫 `dry_run=true` 실행 + 본인 단톡방에서 메시지·Pages URL 도착 시각 확인 + Actions UI에서 artifact 확인. 이 step의 사용자 검증 없이 step8 진입 금지.

## 주 담당 에이전트

`tnb-implementer` (코드 통합) + `tnb-docs-keeper` (secrets_setup.md) 협업.

## 회귀 위험

- `run_daily.py` 본문이 시간 지나면서 비대해질 위험 — qa-reviewer가 `def main():` 본문 line 수 ≤ 50 가드 추가 권장 (Pages·텔레그램 분리 호출로 약간 늘어남).
- `daily.yml` cron 시각을 변경할 때 KST 주석 갱신 누락 — qa-reviewer가 cron 라인 위 2줄 안에 "KST" 단어 검색.
- `permissions: contents: write` 누락 시 dispatcher의 git push 401 — `daily.yml` 검토 시 필수 키.
- BotFather 토큰을 운영자가 평문 파일에 저장 → 유출. secrets_setup.md에 "GitHub Secrets 외 다른 곳 저장 금지" 명시.
- chat_id를 음수 정수 대신 문자열 그대로 환경변수에 넣었을 때 텔레그램 API가 400 응답 — telegram_send 안에서 int 변환 시도 + 실패 시 `ConfigError`.

## pending_manual_qa_scenarios 누적

- "운영자가 직접 BotFather 토큰 발급 + 단톡방 생성·봇 초대·chat_id 획득 + Pages 활성화 + 6개 환경변수 등록 + dry_run=true 1회 실행 + 본인 단톡방·Pages URL 도착 확인 (step8 dry-run의 전제)"
- "Actions UI에서 cron 자동 실행 시각이 KST 07:30 ± 15분 안에 들어오는지 4주 모니터링 + Pages publish 평균 지연 분포 (step8 verification-record 에 평균·표준편차 기록)"
