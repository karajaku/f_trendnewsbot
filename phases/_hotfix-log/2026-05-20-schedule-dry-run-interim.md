# cron schedule 실행을 임시로 dry-run 고정 — 운영자 채널만 발송

날짜: 2026-05-20
규모: 핫픽스 (1파일 — `.github/workflows/daily.yml`, 임시 운영 조치)

## 증상

이 워크플로의 **첫 `schedule`(cron) 실행**(run `26156817670`)이 `2026-05-20T10:30:31Z` UTC = **KST 19:30(저녁 7:30)**에 발동했다. 게시된 HTML hero 표기도 `KST 19:30`. "매일 아침" 다이제스트가 저녁에 나갔다.

## 원인

`daily.yml` 의 cron `'20 22 * * *'`(22:20 UTC = KST 익일 07:20)은 **값 자체가 정확**하다. git 이력상 생성 이래 다른 값이었던 적이 없다. 그러나 GitHub Actions 의 `schedule` 트리거는 **정시 보장이 없다** — 저활동 저장소·부하 시 크게 지연·이탈하는 것이 문서화된 약점이며, 오늘이 첫 schedule 실행이라 정착 과정의 일회성일 가능성이 있다.

타이밍이 안정됐는지 1~2회 더 관찰해야 하는데, 그 동안 잘못된 시각의 다이제스트가 **직원 단톡방(`TELEGRAM_CHAT_ID`)** 으로 나가면 안 된다.

## 변경

- `.github/workflows/daily.yml` "Run daily digest" 스텝 — 실행 인자 조건을
  `inputs.dry_run` → `github.event_name == 'schedule' || inputs.dry_run` 로 확장.
  `schedule` 이벤트면 항상 `--dry-run` 부착 → `run_daily.py` 가 `OPS_ALERT_CHAT_ID`(운영자
  채널)로만 발송. `workflow_dispatch` 는 기존대로 `dry_run` 입력을 따른다.

## 효과 / 영향

- cron 발송은 안정화 확인 전까지 **운영자 채널 전용**. 운영자는 매일 cron 발동 시각·내용을 직접 모니터링할 수 있다 (hero eyebrow 의 `KST HH:MM` 로 실제 발동 시각 확인).
- **직원 단톡방은 이 기간 동안 cron 다이제스트를 받지 않는다** — 의도된 임시 조치. 필요 시 `workflow_dispatch`(dry_run=false) 수동 발송으로 직원 발송 가능.
- Pages publish·history 기록은 dry-run 여부와 무관하게 그대로 동작.

## 되돌림 조건 (REVERT CONDITION)

cron 발동 시각이 **KST 07:20 ±15분**으로 1~2회 안정 확인되면, "Run daily digest" 스텝의 `github.event_name == 'schedule' ||` 분기를 제거해 `schedule` → 직원 발송으로 복귀한다. 그 상태가 requirements AC-1.4(매일 발송)·AC-2.3-A(직원 단톡방 메시지)의 정상 동작이다. 본 핫픽스는 그때까지의 한시 가드.

## 수동 확인

- [ ] 머지 후 다음 cron 실행 → 다이제스트가 운영자 채널에만 도착(직원 단톡방 미수신) 확인
- [ ] `workflow_dispatch` dry_run=false 1회 → 직원 발송 경로가 여전히 살아있는지 확인
- [ ] `git diff --check` 통과

## 회귀 위험

- `workflow_dispatch` 분기 무영향 — `dry_run=false` 면 종전대로 직원 발송, `true` 면 운영자.
- GitHub expression `(A || B) && '--dry-run' || ''` — schedule/dispatch-true → `--dry-run`, dispatch-false → 빈 문자열. 세 경우 모두 검증함.
- 안정화 후 되돌림을 잊으면 직원 발송이 무기한 누락 — 되돌림 조건을 본 로그에 명시해 가드.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음 (코드 무변경, 워크플로 YAML 만)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음

> 직원 발송 경로의 한시적 우회다. AC-1.4(빈도)는 유지(매일 실행), 변경되는 것은 수신 대상뿐이며 되돌림 조건이 명시돼 있어 핫픽스로 처리. 안정화 후 복귀가 정상 상태.
