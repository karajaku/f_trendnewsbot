# Step 8: dry-run + verification-record + canonical sync

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-1.3 + Phase DoD

**qa_blocking: true** — phase 전체의 사용자 일괄 QA 게이트. PRD·ARCHITECTURE 갱신 포함. 본 step 완료 = phase 완료.

## 읽을 파일

- [docs/canonical/DEV_PROCESS.md](../../docs/canonical/DEV_PROCESS.md) Stage 7 (QA cadence·verification-record 기준), Stage 8 (Phase DoD), Stage 9 (Canonical Sync)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) 전부 — AC cross-check 입력
- [docs/canonical/PRD.md](../../docs/canonical/PRD.md) §성공 기준 — 정시성 갱신 대상
- [docs/canonical/ARCHITECTURE.md](../../docs/canonical/ARCHITECTURE.md) — 모듈 ownership 실측 갱신 대상
- step1~7 산출물 전부 + `phases/01-mvp-daily-digest/index.json` (`pending_manual_qa_scenarios` 누적분)

## 작업 범위

### 1. Dry-run 1회 (운영자 환경, ADR-003 갱신)

- Actions tab → `daily.yml` → Run workflow → `dry_run=true` → 운영자 단톡방만 수신
- 발송 후 다음 확인:
  - 운영자 단톡방에 짧은 인덱스 메시지 도착 (헤더 + 카테고리 헤드라인 3개 + Pages URL)
  - Pages URL 클릭 → 브라우저에서 HTML 본문 정상 표시
  - HTML head에 `<meta name="robots" content="noindex,nofollow">` 존재 (브라우저 view-source 확인)
  - `docs/digest/robots.txt`가 `User-agent: * / Disallow: /` 인지 확인
  - 본문 시각 표기(`5월 19일 ... KST`) 일관성
  - 카테고리 3개 헤더·항목 5~10건
  - Pages HTML 모든 항목에 원문 URL 노출 (텔레그램 메시지에는 Pages URL만)
  - "why it matters" 류 라인 부재
  - 실패 소스 있으면 메시지·HTML 헤더 한 줄 노출
  - `history/sent.jsonl` artifact 업로드 성공
  - git log에 `digest: YYYY-MM-DD` commit 1건

### 2. Verification record 작성

- `docs/history/daily_digest/daily_digest_v1-manual-verification-record.md` 신규
  - 실행 일시·환경·수신자(운영자 단톡방 멤버 = 운영자 본인)
  - AC-1 ~ AC-7 각각의 실측 결과 (✅/❌/N/A + 한 줄 코멘트)
  - `pending_manual_qa_scenarios` 누적분 일괄 결과
  - 발견된 회귀·핫픽스 (있으면 `phases/_hotfix-log/` 링크)
  - 4주 모니터링 항목 명시 (cron 정시성 분포·Pages publish 평균 지연·fuzzy threshold 실측·텔레그램 메시지 도착률)
  - **단톡방 단계적 멤버 초대 일정** (AC-6.4): Day 0 운영자 1명 → Day 7 3이사 합류 → Day 14 전 직원. 각 단계 초대일·이슈·이사진 피드백을 verification-record에 누적 기록.
  - **운영자 alert 첫 시뮬레이션** (AC-5.3·AC-5.4·AC-5.6):
    - quota 초과 강제 → 운영자 chat에 alert 1통, 직원 단톡방·Pages 미게시 확인
    - Pages publish 실패 시뮬레이션 (`GITHUB_TOKEN` 일시 권한 박탈) → 운영자 chat에만 alert, 직원 단톡방 미게시
    - 텔레그램 chat_id 무효 → 운영자 chat에 alert
  - **외부 뉴스레터 권고 안 함 정책 확인** (requirements §2): 본 V1이 외부 뉴스레터가 다루지 않는 회사 키워드 카테고리로 차별화되는지 1주차 수신자(운영자) 체감 메모
  - **Pages 검색엔진 노출 점검**: dry-run 후 1주일 뒤 구글 `site:` 검색으로 다이제스트 페이지가 인덱싱되지 않는지 1회 확인 (AC-2.8)

### 3. Canonical Sync (Stage 9)

신규 시스템 추가 — Stage 9 트리거 조건 충족.

- `docs/canonical/PRD.md` §성공 기준:
  - "KST 07:30 ± 5분 95%" → "KST 07:30 ± 15분 95% (4주 모니터링 후 실측 분포 반영하여 재검토)" (Tech 결론 #3, design-review 관점 A 조치)
- `docs/canonical/ARCHITECTURE.md`:
  - §폴더 구조: 예정 다이어그램을 실제 구현 경로로 교체
  - §모듈 ownership: 실제 코드 경로·테스트 위치 반영
  - §성능 기준선: dry-run 실측 토큰·실행 시간 반영
- `docs/implementation_status.md` 신규: 시스템 목록에 `daily_digest_v1` 행 추가 + status·last_phase·verification 링크
- `docs/PHASE_MAP.md` 신규: phase 01 행 추가 (`README.md` 작성 또는 _template 기반)

### 4. Phase DoD 게이트

- `phases/01-mvp-daily-digest/index.json` 의 모든 step status = `completed` 확인
- phase index.json `status: completed`, `completed_at: "2026-MM-DD"`
- `phases/index.json` 의 phase 엔트리 동기화
- `daily_digest_v1-brief.md` frontmatter → `status: frozen`, `frozen_at`
- `daily_digest_v1-requirements.md` frontmatter → `status: frozen`, `frozen_at`
- `daily_digest_v1-design-review.md` frontmatter → `status: applied`, `applied_at` (사용자 일괄 검토 OK 후)

## 영향받는 데이터 정의 목록

- 정적 데이터 변경 없음 (sources.yml·filters.yml은 step2 동결)
- 메타: PRD·ARCHITECTURE·implementation_status·PHASE_MAP 동기화

## Acceptance Criteria

- [ ] dry-run 1회 성공 — 운영자 본인 메일함에 도착, 위 시각 정합 6개 확인
- [ ] `daily_digest_v1-manual-verification-record.md` 생성 — AC-1~AC-7 cross-check 표 + `pending_manual_qa_scenarios` 일괄 결과
- [ ] `PRD.md` 정시성 기준 갱신 + Changelog 한 줄
- [ ] `ARCHITECTURE.md` 폴더 구조·모듈 ownership·성능 기준선 갱신
- [ ] `implementation_status.md` 신규 + `daily_digest_v1` 행
- [ ] `PHASE_MAP.md` 신규 + phase 01 행
- [ ] `phases/01-mvp-daily-digest/index.json` status=completed, completed_at 기록
- [ ] `phases/index.json` 동기화
- [ ] `brief.md`·`requirements.md` frontmatter → frozen, design-review → applied
- [ ] `validate_agent_profiles.ps1` + `validate_doc_status.ps1` 모두 OK 종료
- [ ] 회귀·핫픽스 발생 시 `phases/_hotfix-log/` 링크가 verification-record에 포함

## 금지사항

- 직원 메일에 dry-run 발송 금지 — `dry_run=true` 의 정의가 운영자만 수신
- PRD·ARCHITECTURE 갱신을 step1~7에서 산발적으로 진행 금지 — 본 step에서 일괄
- verification-record 없이 phase status=completed 전환 금지 (Stage 7 "중요 기능" 기준 — 새 시스템 추가)
- 4주 모니터링 결과 없이 정시성 기준을 다시 ± 5분으로 되돌리기 금지

## 수동 테스트 절차

1. step7의 dry-run 1회 (운영자 메일함 도착·시각·카테고리·URL 모두 확인)
2. `pending_manual_qa_scenarios` 배열의 각 시나리오를 사용자가 직접 재현 + 결과를 verification-record에 기록
3. canonical 문서 4종 갱신 → diff 검토
4. `validate_*.ps1` 두 개 모두 실행 → 모두 `OK` 출력
5. phase·feature doc frontmatter 상태 일관성 확인 (`grep -r "status:"`)

## 수동 QA Owner

**`사용자` (qa_blocking)** — phase 끝 일괄 QA. 다음을 사용자가 직접 확인:

- dry-run 메일 본문 시각·카테고리·요약·URL·"why it matters" 부재
- `pending_manual_qa_scenarios` 누적분 (step1~7 동안 누적된 약 12개 시나리오)
- design-review §5 사용자 확인 7항목 (정시성 SLA·공휴일·model env·fuzzy·이모지·운영자 alert·미결 6개)
- PRD 갱신 내용 동의
- ARCHITECTURE 갱신 내용 동의

사용자 OK 후 design-review.md `applied` 전환·phase `completed` 전환.

## 주 담당 에이전트

`tnb-qa-reviewer` (정적 검토·verification-record 작성) + `tnb-docs-keeper` (canonical 4종 갱신).

## 회귀 위험

- canonical 갱신 후 frontmatter 상태가 어긋나면 `validate_doc_status.ps1` 실패. step 안에서 모든 frontmatter 일관성을 마지막에 점검.
- 4주 모니터링은 phase 종료 후 별도 작업. verification-record에 모니터링 시작일·평가 시점·재검토 트리거를 명시.
- 사용자 일괄 검토에서 design-review 수정 항목이 추가로 나오면 핫픽스로 처리 + `_hotfix-log/` 기록.

## pending_manual_qa_scenarios 누적

본 step에서 새로 누적할 시나리오 없음 — step1~7의 누적분을 본 step에서 일괄 처리·해소.
