# Step 6: dispatchers — Pages publish + 텔레그램 Bot API + 운영자 alert (ADR-003)

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.3·2.8·3.3·5.3·5.4·5.6·6.1·6.2·6.6 + §7

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) anti-pattern A (표시 helper 공유), CRITICAL #5 (시크릿 마스킹)
- [docs/canonical/ADR.md](../../docs/canonical/ADR.md) ADR-003 V1 채널 결정
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.3-A·2.3-B·2.8·5.3·5.4·5.6·6·7
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §3-3 텔레그램 + Pages
- step1 산출물: `lib/url_helper.canonicalize`, `lib/time_helper.format_subject_date`, `lib/logging_setup.mask_key`
- step5 산출물: `Digest.html`, `Digest.telegram_text` (render에서 동시 생성)

## 작업 범위

### Base 인터페이스

- `src/dispatchers/__init__.py`, `src/dispatchers/base.py`
  - `Dispatcher` 인터페이스 — `send(digest: Digest) -> SendResult`
  - `SendResult(success, kind, error_kind, error_message, retried)`. `kind` = `pages` | `telegram` | `ops_alert`

### Pages publish

- `src/dispatchers/pages_publish.py` (2026-05-19 gh-pages branch boundary 채택)
  - `publish(digest: Digest, date_kst: date) -> str`
    - `git worktree add {tmp} gh-pages` 로 임시 디렉토리에 `gh-pages` branch checkout (master 영향 0)
    - `{tmp}/digest/YYYY-MM-DD.html` 작성 (`digest.html` 그대로 — HTML head에 `<meta name="robots" content="noindex,nofollow">` 포함, AC-2.8)
    - `{tmp}/robots.txt` 가 없으면 같이 생성 (`User-agent: * / Disallow: /`)
    - `git -C {tmp} add digest/YYYY-MM-DD.html robots.txt`
    - `git -C {tmp} commit -m "digest: YYYY-MM-DD"` (재실행 시 `(rerun)` suffix)
    - `git -C {tmp} push origin gh-pages` — `GITHUB_TOKEN` 으로 인증
    - `git worktree remove {tmp} --force` 로 임시 디렉토리 정리 (finally 블록)
    - push 후 `{PAGES_BASE_URL}/digest/YYYY-MM-DD.html`을 30~60초 polling (HEAD 200 응답) — AC-5.6
    - 게시 확인 시 URL 반환, 실패 시 `PagesPublishError(stage=...)`
  - 테스트 hook: `git_runner` (subprocess.run 호환), `http_checker` (requests.head 호환), `tmp_factory` (tempfile.mkdtemp 호환 — worktree 디렉토리 격리용). 모두 키워드 전용 인자.
  - `git` author/committer는 `f_trendnewsbot` 봇 이름·이메일 (commit 출처 명확)
  - **운영자 초기 셋업 1회 (step7 secrets_setup.md)**: 빈 orphan `gh-pages` branch push (`git checkout --orphan gh-pages → git rm -rf . → echo "# Digest archive" > README.md → git add README.md → git commit -m "Initialize gh-pages" → git push origin gh-pages → git checkout master`) + Settings → Pages 에서 Source: `gh-pages` branch root.

### Telegram send

- `src/dispatchers/telegram_send.py`
  - `send(digest: Digest, pages_url: str, chat_id: str, token: str) -> SendResult`
  - `requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=...)` 호출
  - `json` 본문: `chat_id`, `text` = `digest.telegram_text + "\n\n전체 본문: " + pages_url`, `parse_mode="HTML"`, `disable_web_page_preview=True` (AC-2.3-A)
  - timeout 10초, retry 1회 (AC-5.4)
  - 인증 실패(401) / chat_id 무효(400) → `TelegramSendError`

### Operator alert

- `src/dispatchers/ops_alert.py`
  - `send_ops_alert(reason: str, error: Exception | None, chat_id: str, token: str)` — `OPS_ALERT_CHAT_ID` 로 텔레그램 메시지 발송
  - 본문: `[팜보스 트렌드 알림] {KST datetime} {ERROR_KIND}\n{trim된 스택트레이스}\n다음 cron: {next KST}` (§7)
  - alert 자체 발송 실패 시: stderr 로그만 + 종료 (재시도 없음 — 무한루프 방지, AC-5.4 마지막 줄)

### dispatcher 호출 순서 (run_daily.py가 책임, AC-5.6)

```
1. pages_url = pages_publish(digest, date_kst)         # 게시 확인까지 wait
2. telegram_send(digest, pages_url, ...)               # 직원 단톡방
   - 직원 단톡방 발송 성공 시 history.record() 호출
3. (실패 분기) → ops_alert(...) + sys.exit(비정상)
```

직원 단톡방 발송이 Pages publish 성공에 종속. 순서 어김 시 직원이 404 URL 클릭하는 사고 발생.

## 영향받는 데이터 정의 목록

- `docs/digest/YYYY-MM-DD.html` — 신규 (정적, git tracked, Pages 자동 배포 대상)
- `docs/digest/robots.txt` — 신규 (1회 생성 후 변경 없음)
- 환경변수 의존: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPS_ALERT_CHAT_ID`, `PAGES_BASE_URL`, `GITHUB_TOKEN` (자동 주입)

## Acceptance Criteria

- [ ] `pages_publish.publish()` 가 ① 파일 작성 ② commit ③ push ④ HTTP 200 확인 순서로 실행, 어느 단계 실패도 명확한 예외 (`PagesPublishError(stage=...)`)
- [ ] HTML head에 `<meta name="robots" content="noindex,nofollow">` 존재 (AC-2.8) — render 결과 string 그대로 사용, dispatcher가 후처리하지 않음
- [ ] `docs/digest/robots.txt` 가 `User-agent: * / Disallow: /` 내용으로 1회 생성됨
- [ ] commit message 형식 `digest: YYYY-MM-DD` 또는 `digest: YYYY-MM-DD (rerun)`
- [ ] push는 `GITHUB_TOKEN` 자동 권한 사용 — PAT 별도 등록 불필요
- [ ] `telegram_send.send()` 가 `chat_id`·`text`·`parse_mode="HTML"`·`disable_web_page_preview=True` 4 필드 포함 (AC-2.3-A)
- [ ] 텔레그램 메시지 본문 길이 ≤ 4,096자 (텔레그램 한도) — render 단계에서 검증, dispatcher에서 재검증
- [ ] 텔레그램 발송 실패 시 1회 retry, 두 번째 실패 시 `TelegramSendError` raise (AC-5.4)
- [ ] `ops_alert.send_ops_alert()` 가 별도 chat(`OPS_ALERT_CHAT_ID`)에 발송, 직원 단톡방 발송 없음 (§7)
- [ ] alert 자체 실패 시 stderr 로그 + 종료, 재시도 0회 (AC-5.4 무한루프 방지)
- [ ] 모든 시각 표기는 `lib/time_helper` 통과 (AC-7.4)
- [ ] 시크릿(`TELEGRAM_BOT_TOKEN`) 평문 로그 금지 — `mask_key` 통과 (AC-7.2)
- [ ] 시크릿 환경변수 누락 시 `ConfigError(missing_env=...)` raise — 발송 시도 안 함
- [ ] unit test 12건 이상:
  - pages_publish: 정상 / git push 실패 / Pages 60초 후에도 404 / robots.txt 신규 생성
  - telegram_send: BCC/Bcc 헤더 개념 없음 확인 / chat_id 무효 400 / 토큰 무효 401 / 정상 retry / 한도 4096자 초과 거부 / disable_web_page_preview True / parse_mode HTML
  - ops_alert: 별도 chat / alert 자체 실패 시 stderr only

## 금지사항

- 직원 단톡방 메시지 본문에 스택트레이스·운영 메타·실패 상세 추가 금지 (§7 — alert는 분리)
- API 토큰·chat_id 평문 로그 금지 (`mask_key` 통과)
- summarizer·main 모듈 수정 금지 (각자 책임)
- 임의 재시도 횟수 2회 이상 금지 (AC-5.4는 1회 retry)
- Pages publish 없이 텔레그램 메시지 발송 금지 (AC-5.6 순서 강제) — main()의 호출 순서로 강제
- Pages HTML 직접 생성 금지 — `Digest.html` (render 결과) 그대로 사용. dispatcher가 HTML 후처리하면 anti-pattern A (표시-규칙 helper 우회).
- Gmail SMTP·이메일 dispatcher 신설 금지 (V1 제거, ADR-003)
- `config/recipients.yml` 사용 금지 (V1 제거, ADR-003)

## 수동 테스트 절차

1. mock: Pages publish 성공 + 텔레그램 mock → SendResult.success=True, history.record() 호출됨
2. mock: Pages git push 실패 → `PagesPublishError(stage='push')` → main()이 ops_alert 호출, 텔레그램 직원 단톡방 발송 안 함
3. mock: Pages publish 성공이지만 60초 후 URL 여전히 404 → `PagesPublishError(stage='verify')` → ops_alert
4. mock: 텔레그램 chat_id 무효 (HTTP 400) → 1회 retry 후 `TelegramSendError` → ops_alert
5. mock: ops_alert도 401 토큰 실패 → stderr 로그만, exit code 비정상 (재시도 0회)
6. fixture: 텔레그램 메시지 본문이 4097자 → render에서 split하거나 거부 (테스트로 명시)
7. (선택, 운영자 본인 환경) BotFather에서 발급한 토큰으로 1:1 chat에 sendMessage 1회 → 운영자 본인 텔레그램에 메시지 도착 (step7 통합 후 권장)
8. `pytest tests/test_dispatchers.py` 통과

## 수동 QA Owner

`에이전트 정적 분석` — mock + pytest로 검증. 실제 텔레그램·Pages 발송은 step8 dry-run.

## 주 담당 에이전트

`tnb-implementer` — Pages git 작업·텔레그램 API·운영자 alert 도메인.

## 회귀 위험

- Pages publish가 race condition으로 push 실패 → main()이 ops_alert로 잡지만 직원 단톡방 발송 없음 → 4주 모니터링 시 push 충돌 사고 빈도 verification-record 기록.
- 텔레그램 token이 환경변수에 strip 안 된 채로 들어가면 401 인증 실패 → 로딩 시 `.strip()`.
- ops_alert가 무한루프(alert 보내다 실패 → alert 보내다 실패) 위험. AC-5.4 마지막 줄로 1회 재시도 금지.
- Pages HTML head의 noindex meta가 누락되면 검색엔진 노출 — render 단계에서 head template에 hard-code + step8 verification에서 grep 확인.

## pending_manual_qa_scenarios 누적

- "실제 텔레그램 봇 토큰·운영자 1:1 chat·운영자 단톡방 ID로 step8 dry-run에서 메시지 도착·Pages URL 활성·noindex meta·robots.txt 4종 시각 확인"
- "Pages publish 1회 race condition 시뮬레이션 (force push 직후 dispatcher 실행) — push 실패 시 ops_alert만, 직원 단톡방 정상 미발송 확인"
- "운영자 alert 발송 자체 실패 시뮬레이션 (잘못된 OPS_ALERT_CHAT_ID) — stderr 로그 + 비정상 exit code, 재시도 없음 확인"
