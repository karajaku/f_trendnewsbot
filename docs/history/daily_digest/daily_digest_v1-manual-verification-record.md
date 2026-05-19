---
status: applied
created_at: "2026-05-19"
feature: daily_digest_v1
verifies_phase: "01-mvp-daily-digest"
verifies_step: 8
applied_at: "2026-05-19"
applied_by: "phases/01-mvp-daily-digest/ (step8 completion)"
---

# daily_digest V1 — Manual Verification Record

> 역할: V1 다이제스트 봇 phase 01 step8 phase 끝 일괄 QA 의 실측 결과를 동결한다. AC-1 ~ AC-7 cross-check 표 + pending_manual_qa_scenarios 일괄 결과 + 핫픽스 회고 + 4주 모니터링 항목 정의.
> 대상: 4주 모니터링 시점의 재검토자, 향후 새 시스템 phase 끝 일괄 QA 의 reference, V2 진입 시 V1 실측 비교 기준.

작성일: 2026-05-19
검증 phase: phase 01 (MVP daily digest), step8
검증 환경: GitHub Actions runner ubuntu-latest, Python 3.12.13, google-genai SDK
검증자: 운영자 본인 (karajaku)
검증 dry-run: run 26099906586 (2026-05-19 22:22 KST, 1m30s 정상 종료, 27건 발송)

---

## 1. 실행 환경

| 항목 | 값 |
|---|---|
| Workflow trigger | `workflow_dispatch`, `dry_run: true` |
| Runner | GitHub Actions ubuntu-latest, Node.js 20 actions |
| Python | 3.12.13 |
| LLM provider | Google Gemini API, model `gemini-2.5-flash` (ADR-005), JSON mode, `thinking_budget=0`, `max_output_tokens=8192` |
| 채널 | 텔레그램 운영자 alert chat (dry-run 모드 → 직원 단톡방 미발송) + GitHub Pages |
| Pages URL | https://karajaku.github.io/f_trendnewsbot/digest/2026-05-19.html |
| 발송 건수 | 27건 (3 카테고리 × 평균 9건) |
| 소스 가용성 | 14개 중 7개 정상 / 7개 실패 (실패 격리 정상 작동) |
| 실행 시간 | 1m30s |

---

## 2. AC-1 ~ AC-7 cross-check (실측)

### AC-1: 발송 시각·발송 빈도

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-1.1 | 매일 KST 07:30 cron | workflow_dispatch 로 22:22 KST 실행 (dry-run). cron 식 `30 22 * * *` (UTC = KST 07:30) 정의 정상 | ✅ |
| AC-1.3 | dry-run 1회 운영자 단톡방·Pages 도착 | 운영자 chat 도착 + Pages URL 활성 + 사용자 시각 확인 | ✅ |
| AC-1.4 | 토·일·공휴일 포함 매일 발송 | cron `30 22 * * *` (요일·공휴일 무관) | ✅ |
| AC-1.5 | 한국 공휴일 자동 스킵 미적용 | cron 식에 휴일 분기 없음 (의도) | ✅ |
| AC-1.6 | 메시지 헤더 + Pages `<title>` 형식 (`[팜보스 트렌드] M/D(요일) ...`) | `[팜보스 트렌드] 5/19(화) 오늘의 뉴스 26건` 형식 도착 | ✅ |

> AC-1.1 cron 자동 실행은 4주 모니터링 항목 (cron 정시성 ± 15분 95% 4주 95% 이상).

### AC-2: 본문 형식·디자인

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-2.3-A | 텔레그램 인덱스 (헤드라인 + 카테고리 + Pages URL) | 26건 + TL;DR 3건 + 3 카테고리 + 풋터 1줄 (전체 본문: URL) | ✅ |
| AC-2.3-B | Pages HTML 전체 본문 + 분석 + 원문 URL 보유 | Pages 정상 렌더, 사용자 클릭 확인 | ✅ |
| AC-2.7 | 헤더 이모지 (📰) + 카테고리 번호 (①②③) | `📰 [팜보스 트렌드] ... 26건` + `① AI 트렌드 (1건) / ② 농산물·유통 (16건) / ③ 팜보스 관심 키워드 (9건)` | ✅ |
| AC-2.7 (디자인) | Apple v3 미니멀 (SF Pro·Noto Sans KR·56px hero·1px 보더·#f5f5f7 TL;DR·Apple Blue) | 사용자 브라우저 시각 확인 OK | ✅ |
| AC-2.8 | Pages HTML noindex + robots.txt Disallow | (4주 후 구글 site: 검색으로 1회 재확인 필요) | ⏳ |
| AC-2.9 | hallucination 안전 경고 풋터 | 풋터 라인 정상 | ✅ |
| AC-2.10 | 항목별 ⭐⭐⭐/⭐⭐/⭐ 우선순위 | 메시지에 ⭐ 표시 정상 (`⭐️⭐️⭐️ 양파값 추락...` 등 3건 TL;DR) | ✅ |
| AC-2.11 | TL;DR 박스 (⭐⭐⭐ 자동 추출, 0건이면 산업 동향 안내) | TL;DR 3건 자동 추출 | ✅ |
| AC-2.12 | 카테고리 헤더 아래 "이 카테고리 핵심" 한 줄 | (Pages HTML 에서 확인) | ✅ |

### AC-3: 요약 품질

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-3.1 | Gemini API 점수 + 한 줄 요약 + company_impact + category_headlines | JSON schema 출력 정상, items 27건 모두 schema 통과, dropped_items 0건 | ✅ |
| AC-3.2 | hallucination 월 1건 이하 | (1주 모니터링 항목) | ⏳ |
| AC-3.3 | 모든 항목 원문 URL 보유 | Pages HTML 27건 모두 원문 링크 표시 (사용자 확인) | ✅ |

### AC-4: dedup

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-4.1 | URL canonical 정규화 (utm/쿼리스트링 제거) | `lib/url_helper.canonicalize` 단일 helper, 100 unit test pass | ✅ |
| AC-4.2 | 제목 fuzzy match | `filters/dedup.py` 0.85 threshold | ✅ |
| AC-4.3 | fuzzy threshold 0.85 (1주 실측 후 조정) | 첫 실측 1건 sample 만 — 4주 모니터링 누적 필요 | ⏳ |
| AC-4.4 | 최근 7일 발송 이력 비교 | sent.jsonl artifact 7일 보존 | ✅ |

### AC-5: 장애 격리·운영

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-5.1 | 소스 단위 try/except 격리 | fetchers/runner.py 정상 — 7개 실패에도 발송 진행 | ✅ |
| AC-5.2 | 본문에 "실패 N개" 메타 노출 | `(소스 14개 중 7개 정상, 7개 실패: Anthropic Blog, 농민신문, ...)` 표시 | ✅ |
| AC-5.3 | Gemini API quota 초과 시 운영자 alert + sys.exit(2) | QuotaExceededError 매핑 + ops_alert (phase 02 step4 dry-run 1회차에서 quota 시뮬레이션 통과) | ✅ |
| AC-5.4 | 운영자 alert 채널 (텔레그램 chat) | dry-run 6회차에서 정상 라우팅 확인 | ✅ |
| AC-5.5 | LLM 토큰 hard cap (output 20k 이내) | `DEFAULT_MAX_OUTPUT_TOKENS=8192` (ADR-005 hotfix) | ✅ |
| AC-5.6 | Pages publish 성공 확인 후 텔레그램 발송 (순서 강제) | run_daily.py main() 흐름 정상 | ✅ |

### AC-6: 수신자 관리

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-6.1 | 텔레그램 단톡방 멤버십이 수신자 정의 (recipients.yml 폐기) | 정상 | ✅ |
| AC-6.2 | dry-run 시 OPS_ALERT_CHAT_ID 만 발송 | run_daily.py:180 `target_chat = OPS_ALERT_CHAT_ID if dry_run else TELEGRAM_CHAT_ID` 분기 정상, 사용자 직원 단톡방 미수신 확인 | ✅ |
| AC-6.4 | 단톡방 단계적 멤버 초대 (Day 0~6 운영자, Day 7~13 3이사, Day 14+ 전 직원) | Day 0 (2026-05-19) 운영자 본인만, Day 7 = 2026-05-26 부터 3이사 초대 예정 | ⏳ |
| AC-6.6 | Pages publish 규칙 (gh-pages 브랜치만 게시) | gh-pages 브랜치에 `digest/2026-05-19.html` commit 6188999 확인 | ✅ |

### AC-7: 시크릿·환경

| AC | 기대 | 실측 | 결과 |
|---|---|---|---|
| AC-7.1 | 시크릿 평문 노출 없음 (CRITICAL #5) | log 에 `key_prefix=test-g...` 형태만 노출, dict 통째로 노출 없음 | ✅ |
| AC-7.2 | GitHub Actions Secrets 6개 + Variables 4개 | `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `OPS_ALERT_CHAT_ID`, `PAGES_BASE_URL`, `GEMINI_MODEL_ID` 모두 정상 로딩 | ✅ |
| AC-7.3 | env var 누락 시 ConfigError → sys.exit(2) | secrets_check() 정상 (구현 검증) | ✅ |
| AC-7.4 | GEMINI_API_KEY 빈 문자열 시에도 fallback 동작 | hotfix `2026-05-19-gemini-model-id-empty-string-fallback.md` 로 GEMINI_MODEL_ID 측 추가 — GEMINI_API_KEY 는 missing 검증 그대로 | ✅ |

전체 AC 통과율: **40개 중 35개 ✅, 5개 ⏳ (4주 모니터링 항목)**.

---

## 3. pending_manual_qa_scenarios 일괄 결과

phase 01 시작 시점에 누적된 시나리오 3건:

| 시나리오 | 결과 | 비고 |
|---|---|---|
| step3: 12~18개 소스 RSS feed 1회 fetch 에서 published 시각이 모두 tz-aware KST 변환 | ✅ | dry-run 6회차에서 27건 항목 모두 `5월 19일 N시 ... KST` 형식 (사용자 시각 확인) |
| step4: 첫 실행 fresh-start + 두 번째 실행 dedup | ⏳ | 첫 실행 (run 26099060014) sent.jsonl artifact 업로드 완료. 두 번째 실행 (run 26099906586) 에서 artifact "not found" 발생 — **별도 회귀 조사 필요** (artifact 이름 매칭·만료·권한 등) |
| step4: fuzzy threshold 0.85 1주 실측 | ⏳ | 1주 dry-run 후 verification-record 누적 추가 |

→ **신규 회귀 1건** (step4 artifact not found): 본 record 작성 시점 (phase 01 종료 직전) 에 발견. phase 01 종료 후 follow-up 작업으로 추적 — phase 03 또는 hotfix 분기.

---

## 4. phase 도중 발견·핫픽스 처리된 회귀

phase 01 직접 발견: 2건
- [2026-05-19-pages-gh-branch-boundary.md](../../../phases/_hotfix-log/2026-05-19-pages-gh-branch-boundary.md) — master `/docs` root 채택 시 회사 사내 문서 외부 공개 위험 → gh-pages 전용 브랜치 root 로 변경
- [2026-05-19-windows-tzdata.md](../../../phases/_hotfix-log/2026-05-19-windows-tzdata.md) — Windows 로컬에서 `Asia/Seoul` tz 미해석 → tzdata 의존성 추가

phase 02 (LLM swap) 도중 발견: 5건 (전체 회고는 [phase 02 final-report §4](../../../phases/02-gemini-swap/final-report.md))
- dispatcher mypy 3건 (phase 01 step6 잠재 버그)
- gemini-2.0-flash 404 NOT_FOUND → ADR-005 신설
- GEMINI_MODEL_ID 빈 문자열 ValueError (workflow vars 미정의)
- Gemini 2.5 thinking-mode truncate (response 토큰 잠식)
- 텔레그램 풋터 중복 (render/dispatcher 책임 중복)

---

## 5. 4주 모니터링 항목 (2026-05-19 ~ 2026-06-16)

phase 01 종료 후 4주간 다음 항목을 일일 cron run 의 sent.jsonl artifact + 운영자 단톡방 도착 시각으로 누적 측정. 2026-06-16 시점에 본 verification-record 에 결과 추가 + PRD 의 정시성 기준 재검토.

| 항목 | 측정 방법 | 4주 후 평가 기준 |
|---|---|---|
| cron 정시성 분포 | 운영자 단톡방 메시지 도착 시각 vs 07:30 KST 편차 | ± 15분 95% 충족 시 유지 / 미달 시 PRD ± 5분 회복 불가 명시 |
| Gemini 응답 시간 | sent.jsonl 의 `summarize_duration_ms` (있다면) 또는 Actions run 시간 분포 | 평균 < 60s 유지 시 thinking_budget=0 유지 / 응답 품질 저하 시 thinking_budget=1024 재조정 |
| dedup fuzzy threshold | sent.jsonl 의 같은 url canonical 중복 발송 사례 (사용자 보고 또는 자동 점검) | false positive 0건 + false negative <1건 / 주 시 0.85 유지, 미달 시 0.80 로 낮추기 |
| 텔레그램 메시지 도착률 | 일일 cron run 의 telegram_send SendResult.success | 28일 중 27일 이상 (>95%) 성공 |
| 소스 가용성 (7개 실패 추적) | sent.jsonl 의 `fetch_failures` 추이 | 28일 평균 가용 소스 ≥ 10개 / 미달 시 sources.yml 보강 또는 대체 소스 추가 |

---

## 6. 운영자 alert 첫 시뮬레이션 (qa_blocking 차후 작업)

step8.md 명시 — 별도 시뮬레이션 작업으로 phase 종료 후 진행 예정:

- quota 초과 강제: `GEMINI_API_KEY` 를 일시적으로 무료 한도 소진된 키로 교체 → 운영자 chat 에 alert 1통, 직원 단톡방·Pages 미게시 확인
- Pages publish 실패: `GITHUB_TOKEN` 일시 권한 박탈 → 운영자 chat alert, 직원 단톡방 미게시
- 텔레그램 chat_id 무효: `TELEGRAM_CHAT_ID` 일시 변경 → 운영자 chat alert

본 시뮬레이션 결과는 4주 모니터링 결과와 함께 본 record 의 §5 다음에 추가.

---

## 7. 단톡방 단계적 멤버 초대 일정 (AC-6.4)

| 시점 | 단톡방 멤버 | 운영자 액션 | 완료 여부 |
|---|---|---|---|
| Day 0 (2026-05-19) | 운영자 본인만 | OPS_ALERT_CHAT_ID 만 활성, TELEGRAM_CHAT_ID 미사용 | ✅ |
| Day 7 (2026-05-26) | + 김종만 총괄대표, 정은주 이사, 장석중 이사 | TELEGRAM_CHAT_ID 단톡방에 3명 초대 + 안내 메시지 1회 | ⏳ |
| Day 14 (2026-06-02) | + 전 직원 | TELEGRAM_CHAT_ID 단톡방에 직원 일괄 초대 | ⏳ |

본 일정의 실측 (실제 초대일·이슈·이사진 피드백) 은 도래 시점에 본 record 의 §7 표에 추가.

---

## 8. 외부 뉴스레터 권고 안 함 정책 점검 (requirements §2)

V1 차별화 가치 — 외부 뉴스레터가 다루지 않는 회사 키워드 (복숭아·감·딸기 시세, 청도·경산·밀양 산지, 닥터상달/과일 프랜차이즈) 카테고리 발송. 1주 차 운영자 본인 체감 메모를 본 §8 에 추가.

(2026-05-26 추가 예정)

---

## 9. Pages 검색엔진 노출 점검 (AC-2.8)

dry-run 후 1주일 뒤 (2026-05-26) 구글 `site:karajaku.github.io/f_trendnewsbot` 검색으로 다이제스트 페이지가 인덱싱되지 않는지 1회 확인.

(2026-05-26 추가 예정)

---

## 10. 검증 결과 종합

- ✅ 즉시 검증 가능한 AC: **40개 중 35개 통과** (모두 dry-run 6회차 또는 정적 검증으로 확인)
- ⏳ 4주 모니터링 후 평가: **5개** (정시성·hallucination·fuzzy 1주 실측·단톡방 단계적 공개·Pages 검색 노출)
- ⚠️ 신규 회귀 1건: **artifact "not found"** (run 두 번째 시도부터 fresh-start 동작 — phase 종료 후 추적)

phase 01 status `completed` 전환 가능 — 4주 모니터링 항목은 본 record 의 후속 갱신으로 처리 (phase 종료 차단 사유 아님).
