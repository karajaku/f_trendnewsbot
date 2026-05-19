---
status: frozen
review_count: 2
created_at: "2026-05-19"
last_reviewed_at: "2026-05-19"
reviewer: "Claude (self cross-review) + 사용자 일괄 검토 4라운드 (2026-05-19)"
feature: daily_digest_v1
reviewed_doc: "docs/features/daily_digest/daily_digest_v1-requirements.md"
applied_at: "2026-05-19"
applied_by: "docs/features/daily_digest/daily_digest_v1-requirements.md (Changelog 2026-05-19 사용자 결정 반영)"
frozen_at: "2026-05-19"
frozen_by: "phases/01-mvp-daily-digest/ (step1~7 완료, step8 진입)"
---

# daily_digest V1 — Design Review

> 역할: V1 requirements가 PRD·ADR·CLAUDE.md·brief·tech-research와 정합한지, 빠진 조건·모호한 acceptance criteria·구현 위험을 사전에 짚는다. /design-review의 다중 에이전트 교차 리뷰를 대체하는 자가 교차 검토(사용자 마지막 일괄 검토 시 추가 리뷰 받음).
> 대상: 사용자 일괄 검토자, Stage 5 phase 계획 작성자.

검토 입력: [daily_digest_v1-requirements.md](daily_digest_v1-requirements.md)
대조 문서: [PRD.md](../../canonical/PRD.md) / [ARCHITECTURE.md](../../canonical/ARCHITECTURE.md) / [ADR.md](../../canonical/ADR.md) / [CLAUDE.md](../../../CLAUDE.md) / [daily_digest_v1-brief.md](daily_digest_v1-brief.md) / [daily_digest_v1-tech-research.md](daily_digest_v1-tech-research.md)
sibling 쌍: [design-review-daily_digest_v1-brief.md](design-review-daily_digest_v1-brief.md) (Stage 2 Concept 검토)

---

## 1. 교차 검토 — 5개 관점

### 관점 A: 도메인 일관성 (PRD ↔ requirements)

| 검사 | 결과 | 비고 |
|---|---|---|
| MVP 포함 항목 9건 모두 AC로 변환됨 | ✅ | AC-1 (cron·KST), AC-2 (3카테고리), AC-3 (요약), AC-4 (dedup), AC-5 (실패 격리·quota), AC-6 (수신자), AC-7 (운영체제 정합) — PRD §MVP 9건과 1:1 매칭 |
| 성공 기준 6건 모두 측정 가능 | ⚠️ | PRD §성공 기준 "KST 07:30 ± 5분 95%"를 requirements AC-1.3가 "± 15분 95%"로 완화 — PRD 본문 갱신 필요(Stage 4 산출물 §추가 작업) |
| 비-목표 7건 명시 보존 | ✅ | requirements §2가 brief §3-7 7개를 그대로 인용 + 4개 추가(인지부하·코멘트 금지·본문 복사·트래킹) |

**조치**: PRD §성공 기준의 "07:30 ± 5분" → "07:30 ± 15분 (4주 모니터링 후 조정)"로 본 requirements `frozen` 전환 시점에 갱신. 이 책임은 Stage 5 phase 계획의 마지막 step 또는 Stage 9 Canonical Sync.

### 관점 B: 운영체제 정합 (CLAUDE.md ↔ requirements)

| CRITICAL 규칙 | requirements 대응 | 결과 |
|---|---|---|
| #1 점진 확장 | §3 시사점·§9 phase 입력으로 6모듈 분리 | ✅ |
| #2 표시-규칙 일치 | AC-7.4 + §3 Tech 결론 #4 (url_helper·time_helper 공유) | ✅ |
| #3 단일 진입 비대화 | AC-7.3 (`main()` 5단계 호출만) | ✅ |
| #4 외부 소스 장애 격리 | AC-5.1, AC-5.2 + §2-1 fetcher 형태 강제 | ✅ |
| #5 시크릿 평문 노출 금지 | AC-7.1, AC-7.2 + §8 환경변수 명세 | ✅ |
| #6 요약 옆 원문 링크 | AC-2.3 (form), AC-3.3 (URL 검증) | ✅ |
| #7 시간대 KST 명시 | AC-1.1 (cron 주석), AC-1.2 (form), AC-1.3 (SLA) | ✅ |
| #8 발송 이력 dedup | AC-4 전부, §6-4 sent.jsonl 스키마 | ✅ |
| #9 API quota hard cap | AC-5.3, AC-5.5 (구체 수치 명시) | ✅ |

Anti-pattern 5개도 모두 AC 또는 §6 data contract로 차단. 누락 없음.

### 관점 C: 추적성 (brief ↔ tech-research ↔ requirements)

| 추적선 | 결과 |
|---|---|
| Discovery 결론 5개 → brief §4 인용 5개 | ✅ |
| brief §3 규칙 → requirements AC 변환 | ✅ (brief §3-1~§3-7 → AC-1~AC-6 + §2) |
| Tech 결론 5개 → requirements §3 인용 5개 | ✅ |
| Concept 검토 미결 항목 5개 → 해소 위치 | ✅ — 1(ADR-002 accepted), 2(AC-3·§3), 3(§6-1 sources.yml — Stage 5에서 동결), 4(§7 운영자 alert 결정), 5(AC-7.4 + §3 결론 #4) |

추적 체인 끊김 없음.

### 관점 D: 구현 위험·모호함

**위험 R-1 — Claude API JSON 파싱 실패**
- AC-3.1이 "2문장 이내"를 후처리에서 자른다고 명시하지만, `prompts/summarize.md`가 JSON 출력을 강제할 때 model이 `summary` 필드를 누락하거나 schema에 어긋날 가능성.
- 대응: `summarizer/render.py`의 schema validation 실패 시 해당 항목을 폐기 + 메타에 누락 표기. requirements §6-5 마지막 줄에 명시되어 있음. ✅

**위험 R-2 — sent.jsonl 첫 실행**
- §6-4: artifact 없으면 빈 history로 부팅. 첫 실행 시 dedup 적용 안 됨 → 첫날 발송 후 artifact 생성됨.
- 대응: phase 계획에서 첫 step의 수동 QA 시나리오에 "artifact 없는 상태로 dry-run 1회"를 추가하도록 Stage 5에 전달.

**위험 R-3 — Gmail SMTP 일일 한도**
- Tech §3-3: Workspace 기본 외부 수신자 ~500통/일. 수신자 10명 × 1회 = 10통/일이라 여유.
- BCC로 묶어 1통으로 전송하는 운영을 AC-6.2에 명시. ✅

**위험 R-4 — 영업일 판단**
- AC-1.4 "토·일·공휴일 미발송", cron `0-4`(일~목 UTC) = 한국 월~금 KST. 하지만 한국 공휴일(설·추석·삼일절 등)은 cron으로 처리 불가.
- 대응: 본 V1은 공휴일 발송 허용(공휴일이 적고, 직원이 알아서 무시 가능). requirements §2 범위 외에 "한국 공휴일 자동 스킵"을 명시 추가하는 게 명확. → **수정 항목 1**.

**위험 R-5 — Claude Haiku 4.5 모델 ID 가용성**
- Tech §3-2: `claude-haiku-4-5-20251001` 사용 가정. 모델 ID가 향후 deprecated 되면 호출 실패.
- 대응: 환경변수 `CLAUDE_MODEL_ID`로 분리해서 코드 변경 없이 교체 가능하도록 AC 추가 권장. → **수정 항목 2**.

### 관점 E: 사용자 검토 대기 항목 vs 자동 결정 적정성

requirements에서 agent가 단독 결정한 항목 vs 사용자에게 보류한 항목:

| 항목 | 결정 위치 | 적정성 |
|---|---|---|
| 운영자 alert = 별도 메일 | §7 (agent 결정) | ✅ 합리적 — 직원 본문 깨끗함 |
| dedup 윈도우 7일 | AC-4.2 (brief §3-4 인용) | ✅ |
| fuzzy threshold 0.85 | AC-4.3 (agent 결정) | ⚠️ 검증 부족 — dry-run 후 조정 가능, requirements §1 위험 R로 추가 권장 |
| hard cap 수치(100k 토큰 등) | AC-5.5 (agent 결정) | ✅ Tech 추정의 10배 여유 — 합리적 |
| Claude model = Haiku 4.5 | ADR-001 (이미 accepted) | ✅ |
| 정시성 ± 15분 완화 | AC-1.3 (Tech §3-4 인용) | ⚠️ PRD 갱신 필요 (관점 A 조치 항목) |
| 한국 공휴일 미스킵 | 명시 없음 | ⚠️ 위험 R-4 — 수정 항목 1 |
| sources.yml V1 최종 12~18개 | 미정 (Stage 5로 위임) | ✅ phase 첫 step에서 동결 |
| 이모지 사용 | 헤더 1개 (📰) 묵시적 가정 | ⚠️ 사용자 일괄 검토에서 회사 톤 확인 필요 |

---

## 2. 발견된 결함·수정 항목 (Stage 5 진입 전 처리)

### 수정 항목 1 — 한국 공휴일 처리 명시

requirements §2 범위 외 또는 §4 AC-1에 다음 추가:

> **AC-1.5**: 한국 공휴일 자동 스킵은 V1 범위 외. cron이 토·일(`0-4` 요일 필터)만 차단하며, 평일 공휴일은 발송된다. 운영자가 워크플로 disable로 수동 차단 가능. V2에서 공휴일 캘린더 API 연동 검토.

### 수정 항목 2 — Claude model ID 환경변수화

§8 시크릿·환경변수 명세 표에 다음 추가:

> `CLAUDE_MODEL_ID` | GitHub Actions Variable | 사용 모델 ID. 기본값 `claude-haiku-4-5-20251001`. deprecated 시 코드 변경 없이 교체. |

### 수정 항목 3 — fuzzy threshold 조정 가능성 명시

AC-4.3에 추가:

> dry-run 1주일 후 실측 false positive/negative 분포에 따라 0.80~0.90 범위에서 조정 가능. 조정은 `config/filters.yml`의 `global.fuzzy_title_threshold`만 변경.

세 수정 항목은 자가 검토에서 도출됐으므로 사용자 일괄 검토 시 confirm 받고 requirements에 반영(Changelog 갱신).

---

## 3. 종합 평가

| 평가 영역 | 결과 |
|---|---|
| PRD 정합성 | ✅ (1건 갱신 필요: 정시성 ± 15분) |
| ADR 정합성 | ✅ (ADR-002 본 검토와 함께 accepted 전환) |
| CLAUDE.md 9개 CRITICAL 커버리지 | ✅ 9/9 |
| brief·tech-research·requirements 추적 체인 | ✅ 끊김 없음 |
| Acceptance Criteria 측정 가능성 | ✅ (수정 항목 1~3 반영 시 100%) |
| Data Contract 완성도 | ✅ 5개 파일 스키마 모두 명시 |
| 구현 위험 | 5건 식별, 3건 수정 항목으로 도출 |
| Stage 5 진입 준비 | ⚠️ 수정 항목 3건 반영 후 진입 |

---

## 4. Stage 5 진입 권고

수정 항목 1·2·3 반영 후 다음 입력으로 Stage 5(`/plan-phase` 또는 `tnb-phase-orchestrator`) 진입:

- `related_docs`:
  - `docs/features/daily_digest/daily_digest_v1-brief.md` (frozen 예정)
  - `docs/features/daily_digest/daily_digest_v1-discovery-research.md` (applied, frozen 안 함)
  - `docs/features/daily_digest/daily_digest_v1-tech-research.md` (applied, frozen 안 함)
  - `docs/features/daily_digest/daily_digest_v1-requirements.md` (frozen 예정)
  - `docs/features/daily_digest/daily_digest_v1-design-review.md` (reviewed → applied)
- 규모: 대형
- 권장 step 분해 (Stage 5에서 확정):
  1. 부트스트랩 (`pyproject.toml`, 폴더 구조, `lib/`, logging, KST helper)
  2. config 로딩 (`sources.yml`, `filters.yml`, `recipients.yml`)
  3. fetchers (`rss`, `html`, `json_api`) + 소스 격리
  4. filters (`timewindow`, `keyword`, `category`, `dedup`) + history backend
  5. summarizer (Claude SDK + prompt caching + hard cap + score·summary 단일 호출)
  6. dispatchers (Gmail SMTP + BCC + 운영자 alert)
  7. run_daily.py 통합 + GitHub Actions workflow + Secrets 등록 가이드
  8. dry-run 1회 + verification-record + PRD 갱신 (정시성 ± 15분)

---

## 5. 사용자 일괄 검토 결과 (2026-05-19)

| # | 질문 | 사용자 결정 | 반영 위치 |
|---|---|---|---|
| 1 | 정시성 SLA "± 15분 95%"로 PRD 갱신 | ✅ 동의 (권장) | PRD §성공 기준 + requirements AC-1.3 |
| 2 | 한국 공휴일 V1·V2 미스킵 | ✅ 동의 — 매일 발송으로 변경 | requirements AC-1.4, AC-1.5 갱신, cron `0-4` → `*` |
| 3 | `CLAUDE_MODEL_ID` 환경변수화 | ✅ 동의 (권장) | requirements §8 |
| 4 | fuzzy 0.85 시작 + dry-run 조정 | ✅ 동의 (권장) | requirements AC-4.3 |
| 5 | 이모지 톤 (📰 + ①②③) | ✅ 동의 (권장) | requirements AC-2.7 (신규) |
| 6 | 운영자 alert 별도 메일 | ✅ 동의 (권장) | requirements §7 + AC-5.3·5.4 |
| 7 | 소스 12~18개 phase 첫 step에서 에이전트 초안 | ✅ 동의 (권장) | step2.md (이미 명시) |
| 8 | 수신자 단계적 공개 (운영자 → 3이사 → 전직원) | ✅ 동의 (권장) | requirements AC-6.4 (신규), phase README |
| 9 | 사내 선례 유무 | 없음 — 이번이 처음 | Discovery §3 가정 확정 |
| 10 | 외부 뉴스레터 중복 | 권고 안 함, 직원 자율 | requirements §2 범위 외 |
| 11 | V1 발송자 주소 | `nterrr@gmail.com` (운영자 본인) | requirements AC-6.5 (신규), ADR-001 §결과 보충 |
| 12 | 메일 제목 형식 | `[팜보스 트렌드] M/D(요일) AI·농산물 유통 오늘의 뉴스 N건` | requirements AC-1.6 (신규) |
| 13 | 발송 시각 KST 07:30 | ✅ 그대로 (권장) | PRD·brief·requirements 그대로 |
| 14 | 본문 풋터 의견 회신 안내 | ✅ 포함 (권장) | requirements AC-2.6 (신규) |

13개 항목 모두 권장 또는 사용자 명시 답으로 해소. 수정 항목 자체적 도출 3건(R-1·R-2·R-3)은 이미 requirements Changelog 두 번째 줄에 반영 완료.

---

## Changelog

- 2026-05-19: 초안 작성. 자가 교차 검토(관점 A~E) 완료. 수정 항목 3건 도출(공휴일·모델 ID·fuzzy threshold). 사용자 일괄 검토 시 추가 리뷰 받을 예정.
- 2026-05-19: 사용자 일괄 검토 4라운드(13 질문) 완료. §5를 결과 표로 교체. 모든 항목 권장 또는 명시 답으로 해소. requirements·PRD·ADR·phase README/step7/step8에 일괄 반영. status `reviewed` → `applied` 전환.
- 2026-05-19: V1 발송 채널 변경 (ADR-003 accepted) — Gmail SMTP·이메일 발송 폐기, 텔레그램 Bot API + GitHub Pages 조합. 본 design-review의 결론(관점 A·B·C·D·E)은 채널과 직접 관련된 항목(BCC·SMTP 일일 한도 등)을 제외하면 그대로 유효. 관련 위험 R-3(Gmail 일일 한도)는 채널 변경으로 자동 해소. 새 위험 R-6(Pages publish race condition)·R-7(텔레그램 chat_id 음수 정수 처리)은 step6·step7에 반영됨. [design_review_questions.md §채널 변경](../../design_review_questions.md) 참조.
- 2026-05-19: UX 강화 + 애플 감성 디자인 (사용자 2차례 톤 조정 요청 반영) — 본 design-review의 관점 D 위험 R-1(JSON 파싱 실패)·R-5(model ID)는 그대로 유효. 새 위험 R-8(LLM의 회사 영향 hallucination)을 추가 식별. 안전장치는 ① prompt에서 회사 사업 영역 외면 빈 문자열 강제 ② HTML 풋터 hallucination 경고 ③ 4주 운영 후 실측 hallucination 비율 기반 분리 호출 전환 검토. 관점 C(추적성) 보강 — AC-2.5 폐기·AC-2.7 보강·AC-2.9~2.12 신규를 [design_review_questions.md §UX·디자인](../../design_review_questions.md) 표로 연결. [샘플 동결: samples/2026-05-19-digest-preview-v3.html].
