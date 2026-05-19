# Design Review Questions

> 역할: 각 기능의 Concept 검토(Stage 2) 단계에서 발견된 PRD·ADR 충돌 / 미결 설계 질문을 누적 기록한다. 한 기능당 한 섹션.
> 대상: Stage 2 검토자, Stage 4 requirements 작성자, 사용자 일괄 검토자.

---

## daily_digest_v1 Concept 검토 — 2026-05-19

검토 입력: [daily_digest_v1-brief.md](features/daily_digest/daily_digest_v1-brief.md)
대조 문서: [PRD.md](canonical/PRD.md), [ADR.md](canonical/ADR.md)

### PRD 충돌 확인

| 검사 항목 | PRD 위치 | 브리프 정합성 | 결과 |
|---|---|---|---|
| 매일 1회 자동 발송, KST 07:30 | PRD §MVP 포함 | brief §3-1: 동일 (KST 07:30, 영업일) | ✅ 일치 |
| 3카테고리 (AI / 농산물 유통 / 팜보스 관심) | PRD §MVP 포함 | brief §3-2: 동일, 순서 고정 | ✅ 일치 |
| 카테고리당 5~10건 | PRD §성공 기준 | brief §3-2: 동일, 0건 시 "오늘 새 뉴스 없음" 명시 | ✅ 일치 + 보완 |
| 원문 링크 필수 | PRD §MVP, CLAUDE.md CRITICAL | brief §3-3: URL 전체 노출, 단축 금지 | ✅ 일치 + 강화 |
| dedup — URL 정규화 + 7일 이력 | PRD §MVP, ARCHITECTURE §데이터 흐름 | brief §3-4: 동일 | ✅ 일치 |
| 실패 격리 (소스 단위) | PRD §MVP, CLAUDE.md CRITICAL | brief §3-5: 동일, 헤더에 실패 소스 노출 | ✅ 일치 |
| Gmail SMTP | ADR-001 | brief §3-6: 동일 (recipients.yml로 명단 관리) | ✅ 일치 |
| 비-목표 (메신저·웹 대시보드 등) | PRD §비-목표 | brief §3-7: 7개 비-목표 모두 인용 | ✅ 일치 |
| 운영 비용 hard cap | PRD §성공 기준 ($20/월) | brief §3-5: API quota 초과 시 즉시 중단 + alert | ✅ 일치 |
| KST 절대 시각 표기 | CLAUDE.md CRITICAL | brief §3-1: "오늘/어제"는 헤더 1회만 허용 | ✅ 일치 + 보완 |

**충돌 없음.** brief는 PRD의 비-목표 7개를 모두 인용했고, ADR-001(Python 3.12 + GitHub Actions + Claude Haiku + Gmail SMTP)에 어긋나는 새 의존성을 도입하지 않았다.

### ADR 충돌 확인

- **ADR-001 (운영 환경)** — 동결 영역(언어/인프라/AI/채널) 변경 요구 없음. ✅
- **ADR-002 (발송 이력 저장 매체, draft)** — brief §3-4가 "최근 7일 이력"을 요구하지만 저장 매체는 미결. 이는 ADR-002 자체의 결정 대기 상태와 일치. Stage 3 Tech Research에서 후보 3종(artifact / repo push / Issue 누적)을 비교하고 Stage 4 requirements 작성 시점에 ADR-002를 accepted로 전환. ⚠️ Stage 3에서 해소 필요.

### 미결 설계 질문 (Stage 3 또는 Stage 4에서 해소)

brief §5의 6개 미결 항목 중 **Stage 3·4에서 기술적으로 해소해야 할 것**:

1. **발송 이력 저장 매체 결정** (ADR-002 accepted 전환 트리거) — Stage 3에서 후보 3종 비용·복잡도·실패 모드 비교 → Stage 4에서 결정 + data contract 명시.
2. **점수화·요약 호출 분리 가능성** — Stage 3에서 토큰 추정으로 월 $20 hard cap 안에 들어가는지 확인. 분리 비용이 cap을 깨면 V1은 단일 호출 + 짧은 요약 시작, V2 분리 항목으로 분류.
3. **소스 목록 V1 최종** — brief §3-2의 3카테고리에 들어갈 RSS·HTML·JSON API 소스를 Stage 3에서 12~18개 후보로 좁힘. PRD §타깃 사용자의 4 페르소나가 모두 가치를 보는지 확인.
4. **운영자 alert 채널** — brief §5-6. 별도 운영자 메일 vs 메타 헤더 노출 — Stage 4에서 결정.
5. **시각·날짜 helper의 단일 위치** — KST 표기 일관성을 위해 `src/lib/time_helper.py`에 단일 helper 두고 dispatcher/render/dedup 전부 공유(CLAUDE.md "표시-규칙 일치"). Stage 4 requirements에서 시그니처 확정.

### 사용자 검토 보류 항목 (Stage 4 이전 결정 불필요)

brief §5 중 사용자만 답할 수 있는 항목(기술 결정 없음):

- 주말·공휴일 발송 여부 (V1 기본값 "영업일만"으로 진행, 사용자 일괄 검토 시 변경 가능)
- 수신자 명단 확정 (V1 코드 작성과 무관, 운영 시점 결정)
- 회사 내부 선례 유무 (있으면 톤 참고, 없으면 그대로 진행)
- 이모지 사용 가부 (V1 기본값 "📰 헤더 1개 + 카테고리 번호" 정도, 사용자 일괄 검토 시 변경 가능)
- 외부 뉴스레터 중복 (V1 영향 없음, 모니터링 항목)

### Concept 검토 결과

- **PRD·ADR 충돌**: 0건
- **Stage 3 진입 가능**: 예 (Tech Research가 위 미결 항목 1·2·3·5를 해소함)
- **Stage 4 진입 차단 조건**: 미결 항목 1(저장 매체)이 Stage 3에서 해소되지 않으면 Stage 4 진입 보류 — ADR-002가 accepted 상태여야 requirements의 data contract를 동결할 수 있음. **(2026-05-19 ADR-002 accepted로 해소됨)**

---

## daily_digest_v1 사용자 일괄 검토 — 2026-05-19

Stage 4 design-review가 도출한 사용자 확인 항목 13개를 AskUserQuestion 4라운드로 진행. 답변 결과는 [design-review-daily_digest_v1-requirements.md §5](features/daily_digest/design-review-daily_digest_v1-requirements.md#L) 에 표로 정리됨. 핵심 변경:

| 변경 | Before | After |
|---|---|---|
| 발송 빈도 | 월~금 영업일만 | **매일** (토·일·공휴일 포함) |
| 정시성 SLA | 07:30 ± 5분 95% | **07:30 ± 15분 95%** (4주 모니터링 후 재조정 가능) |
| 모델 ID | 코드 하드코딩 가정 | **환경변수 `CLAUDE_MODEL_ID` 분리** |
| 수신자 공개 | 일괄 공개 가정 | **단계적**: 1주 운영자 → 1주 3이사 → 전 직원 |
| 발송자 주소 | Workspace 봇 계정 가정 | **운영자 본인 Gmail (`nterrr@gmail.com`)** 으로 V1 시작 |
| 메일 제목 | 미정 | `[팜보스 트렌드] M/D(요일) AI·농산물 유통 오늘의 뉴스 N건` |
| 톤·이모지 | 미정 | 헤더 `📰` + 카테고리 `①②③`, 항목 내부 이모지 없음 |
| 풋터 안내 | 미정 | "의견·소스 제안은 이 메일에 회신" 포함 |
| 외부 뉴스레터 중복 | 정책 미정 | 권고 안 함, 직원 자율 |
| 사내 선례 | 미확인 | 없음 — 이번이 처음 |

13개 항목 모두 해소. 사용자가 권장과 다르게 결정한 것은 **공휴일 발송**(권장: V2 보류 → 결정: 매일 발송) 1건.

---

## daily_digest_v1 V1 발송 채널 변경 — 2026-05-19 (사후 결정)

requirements `frozen` 직후 사용자가 "직원이 메일을 잘 확인 안할 거 같은데 카톡·텔레그램 알림으로 보내고 HTML 열게 하는 건 어때"를 제기. 4 질문 라운드로 결정.

| # | 질문 | 사용자 결정 | 반영 위치 |
|---|---|---|---|
| 1 | 회사 표준 메신저 | **텔레그램 그룹채팅방** | ADR-003 §맥락 |
| 2 | V1 채널 | **텔레그램 + GitHub Pages만, 이메일 폐기** | ADR-003 §결정, ADR-001 superseded |
| 3 | 메시지 형식 | **짧은 인덱스 + Pages URL** | requirements AC-2.3-A·2.3-B 분리 |
| 4 | Pages 공개 정책 | **public + noindex meta + robots.txt** | requirements AC-2.8 신규 |

영향 범위 (광범위):
- ADR-001 superseded → ADR-003 신규 accepted
- brief §1·§2 전부 / §3-3·§3-5·§3-6·§3-7 갱신
- tech-research §3-3 Gmail SMTP 섹션 → 텔레그램 + Pages 섹션 교체, §4 결론 #6 신규
- requirements 전면 — §1 의존, AC-1.6·AC-2.3·2.6·2.7·2.8·5.3·5.4·5.6·6 전면 갱신, §5 Resource flow, §6-3 폐기, §7 운영자 alert, §8 환경변수 교체
- PRD §MVP·§제외·§의존·Changelog
- phase 01 README §목표·§범위·§step 표·§가드레일·§단톡방 일정
- phase 01 index.json step2·step6·step7 summary
- step6.md 전면 재작성 (Pages publish + 텔레그램 + 운영자 alert chat)
- step7.md cron·workflow·Secrets·env.example·verification-record 갱신
- step8.md dry-run 시나리오·운영자 alert 시뮬레이션·Pages 검색엔진 점검 추가

---
