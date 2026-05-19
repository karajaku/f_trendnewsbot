# Implementation Status

> 역할: f_trendnewsbot 의 시스템 단위 구현 현황을 한 표로 정리한다. phase 단위 진행이 끝난 시점의 status, 마지막 phase, verification-record 링크를 사람용으로 요약.
> 대상: 새 합류자가 "지금 무엇이 동작하고 있는가" 를 30초 안에 파악, 외부 보고 시 시스템 인벤토리, 분기별 회고 시 진행 추적.

작성일: 2026-05-19

---

## 활성 시스템

| 시스템 | feature group | 버전 | status | 마지막 phase | verification record | 운영 노트 |
|---|---|---|---|---|---|---|
| Daily Digest Bot | `daily_digest` | V1 | **applied — 운영 중** | [01-mvp-daily-digest](../phases/01-mvp-daily-digest/) (completed 2026-05-19) + [02-gemini-swap](../phases/02-gemini-swap/) (completed 2026-05-19) | [daily_digest_v1-manual-verification-record.md](history/daily_digest/daily_digest_v1-manual-verification-record.md) | 매일 KST 07:30 자동 cron. GitHub Actions ubuntu-latest. Gemini 2.5 Flash (ADR-005, 무료 tier). 텔레그램 단톡방 + GitHub Pages (gh-pages 브랜치). dry-run 6회차 통과 (run 26099906586, 2026-05-19 22:22 KST). 4주 모니터링 진행 중. |

## 보류 / 검토 중

(없음 — 2026-05-19)

## 종료된 시스템

(없음 — 2026-05-19)

---

## V1 → V2 진입 트리거

다음 중 하나 이상이면 V2 phase 계획 수립 (Stage 0 Discovery Research 부터):

- 직원 피드백 누적 (1개월 이상) 에서 카테고리 가중치·시간대 개인화 요구
- 텔레그램 외 채널 (슬랙·카카오워크·Teams) 추가 요청
- 일일 호출 규모 증가로 Gemini 무료 tier 한도 (15 RPM / 1500 RPD) 70% 초과 도달
- 외부 공유 요청 (사외 파트너·이사진 외부 통신) — Pages public 노출 정책 재검토 필요
- ADR-005 의 "6개월 후 재검토 트리거" 발동 (LLM provider 정책 변경·신규 사용자 차단·thinking-mode 변경)

V2 진입 시점에 본 문서의 V1 status 를 `superseded` 로 전환 + V2 행 추가.

---

## 참조

- 시스템 단위 architecture: [docs/canonical/ARCHITECTURE.md](canonical/ARCHITECTURE.md)
- phase 진행 라이프사이클: [docs/PHASE_MAP.md](PHASE_MAP.md)
- 장기 의사결정 누적: [docs/canonical/ADR.md](canonical/ADR.md)
- feature 단위 acceptance: [docs/features/daily_digest/daily_digest_v1-requirements.md](features/daily_digest/daily_digest_v1-requirements.md)
