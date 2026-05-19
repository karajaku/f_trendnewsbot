# Step 6: dispatchers — Gmail SMTP + BCC + 운영자 alert 분리 메일

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-3.3·5.4·6.2 + §7

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) anti-pattern A (표시 helper 공유) — dispatcher가 자체 URL 자르기 금지
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-3.3, AC-5.4, AC-6.2, §7 운영자 alert, §8 SMTP 환경변수
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §3-3 Gmail SMTP
- step2 산출물: `Recipient`, `OpsAlertRecipient` dataclass + `recipients.example.yml`
- step5 산출물: `Digest` (html + text)

## 작업 범위

### Base 인터페이스

- `src/dispatchers/__init__.py`, `src/dispatchers/base.py`
  - `Dispatcher` 인터페이스 — `send(digest: Digest, recipients: list[Recipient]) -> SendResult`
  - `SendResult(success, error_kind, error_message, retried)`

### Email Gmail

- `src/dispatchers/email_gmail.py`
  - `EmailMessage` 빌더: Subject(헤더 자동 생성), From, To = `GMAIL_FROM`, Bcc = recipients, Reply-To = `OPS_REPLY_TO`
  - `set_content(digest.text)` + `add_alternative(digest.html, subtype="html")` (AC-2.3 정보 동일)
  - `smtplib.SMTP_SSL("smtp.gmail.com", 465)` + `login(GMAIL_USER, GMAIL_APP_PASSWORD)` + `send_message`
  - `suppress=true` 수신자 제외 (AC-6.3)
  - **AC-3.3 URL 검증**: 발송 직전 모든 URL HEAD/GET 응답 코드 확인. 4xx/5xx 항목 제외 + Digest 메타에 누락 표기. (대량 검증은 timeout 부담이라 본 step에서는 ✅ URL 보존 + 발송 후 retry 1회만)
  - SMTP 발송 실패 시 1회 retry, 두 번째 실패 시 `SendError` raise (AC-5.4)

### Operator alert

- `src/dispatchers/ops_alert.py`
  - `send_ops_alert(reason: str, error: Exception | None, recipients: list[OpsAlertRecipient])`
  - 별도 메일 (§7 결정) — 제목 `[팜보스 트렌드 알림] {KST} {ERROR_KIND}`
  - 본문: 스택트레이스 + 실패 컨텍스트 + 다음 cron 예정 시각
  - 직원 다이제스트와 동시 발송 없음 — main()이 분기

## 영향받는 데이터 정의 목록

- 환경변수 `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_FROM`, `OPS_REPLY_TO`, `RECIPIENTS_YML_BASE64` 의존 (시크릿)

## Acceptance Criteria

- [ ] `EmailMessage` 의 `To` 는 단일값(`GMAIL_FROM`), `Bcc` 가 수신자 명단 (AC-6.2 — 직원 명단이 메일 헤더에 노출되지 않음)
- [ ] `Reply-To` 가 `OPS_REPLY_TO` 환경변수 값
- [ ] `suppress: true` 수신자는 Bcc에서 제외 (AC-6.3)
- [ ] `set_content` 와 `add_alternative` 둘 다 호출 — text/HTML 양쪽 본문 (AC-2.3)
- [ ] SMTP 발송 실패 시 정확히 1회 retry, 두 번째 실패 시 `SendError` (AC-5.4)
- [ ] `ops_alert.send_ops_alert` 가 직원 다이제스트와 별개 메일 — 직원 메일 본문에 운영 메타 추가 금지 (§7)
- [ ] 운영자 alert 제목에 KST 시각과 ERROR_KIND 포함
- [ ] 모든 시각 표기는 `lib/time_helper` 통과 (AC-7.4)
- [ ] 시크릿 환경변수 누락 시 명확한 `ConfigError(missing_env=...)` raise — 직원 메일 발송 시도 안 함
- [ ] unit test 8건 이상: BCC 헤더 확인 / Reply-To 헤더 / suppress 제외 / text+HTML 동시 / SMTP 정상 / SMTP 실패 1회 retry / SMTP 실패 2회 후 raise / ops_alert 별도 메일

## 금지사항

- 직원 다이제스트 본문에 스택트레이스·운영 메타 추가 금지 (§7 결정)
- API 키·SMTP 비밀번호 평문 로그 금지 (`mask_key` 통과)
- `To` 헤더에 직원 이메일 노출 금지 (BCC 강제)
- summarizer·main 모듈 수정 금지 (각자 책임)
- 임의 재시도 횟수 2회 이상 금지 (AC-5.4는 1회 retry)
- 대량 URL HEAD 검증 도입 금지 (시간 부담, V1 보류) — Article fetch 시점에 status가 200이었다는 가정으로 진행

## 수동 테스트 절차

1. mock SMTP server → suppress=true 1명 + 정상 3명 → Bcc에 3명만 (suppress 제외)
2. mock SMTP가 첫 번째 호출에서 SMTPException → 두 번째는 정상 → SendResult.success=True, retried=1
3. mock SMTP가 두 번째도 실패 → `SendError` raise → main()이 잡아 ops_alert 호출 (다음 step에서 통합)
4. mock recipients.yml에 ops_alert 1명 → `send_ops_alert("quota_exceeded", err, ...)` → 별도 메일 1통 발송
5. `pytest tests/test_dispatchers.py` 통과
6. (선택, 운영자 본인 계정만) 실제 Gmail SMTP 1회 dry-run → 운영자 본인 메일함에 도착 확인 — step7 통합 후 권장

## 수동 QA Owner

`에이전트 정적 분석` — mock SMTP로 검증. 실제 발송은 step8 dry-run.

## 주 담당 에이전트

`tnb-implementer` — SMTP·EmailMessage 도메인.

## 회귀 위험

- BCC가 To로 잘못 들어가면 직원 명단이 메일 헤더에 노출 — qa-reviewer가 `EmailMessage["To"]` assignment grep로 차단.
- Gmail 앱 비밀번호 16자리에 공백 포함 여부에 따라 인증 실패 — 로딩 시 `.strip()` + replace(" ", "").
- SMTP_SSL 포트 465 / SMTP STARTTLS 포트 587 혼동 → 시크릿 환경변수에 port 명시 안 함, V1은 465 고정.
- 운영자 alert이 무한루프(alert 보내다 실패 → alert 보내다 실패) 위험. ops_alert 안에서 alert 실패 시 stderr만 출력 + 종료 (재시도 없음).

## pending_manual_qa_scenarios 누적

- "실제 Gmail SMTP 인증·발송 — 운영자 본인 계정으로 step8 dry-run에서 메일 도착 + Bcc 정상 + 시각 표기 확인"
- "운영자 alert가 실제 quota 초과·SMTP 장애 시뮬레이션에서 직원 메일 미발송 + ops 별도 메일 1통만 가는지 step8 시뮬레이션"
