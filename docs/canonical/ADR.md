# f_trendnewsbot Architecture Decision Records

> 역할: 장기 의사결정의 누적 기록. "왜 이렇게 결정했는가"의 단일 권위.
> 대상: 결정 배경 확인 시, 같은 트레이드오프 재논의 회피, 새 합류자 온보딩 시.

작성일: 2026-05-19

---

## 기록 형식

각 ADR은 다음 형식을 따른다.

```markdown
## ADR-NNN: {결정 제목}

날짜: YYYY-MM-DD
상태: accepted | superseded | deprecated

### 맥락
{어떤 상황·문제 때문에 결정이 필요했는가}

### 결정
{어떻게 결정했는가}

### 결과
{이 결정으로 인한 트레이드오프, 영향}

### 대안
{고려했지만 채택하지 않은 옵션과 거절 이유}
```

번호는 1부터 순차 증가. 폐기되어도 번호는 재사용하지 않는다.

---

## ADR-001: 운영 환경 — Python 3.12 + GitHub Actions cron + Gmail SMTP + Claude API

날짜: 2026-05-19
상태: accepted

### 맥락

팜보스 임직원이 매일 아침 출근 직후 AI·농산물 유통 트렌드를 5분 안에 파악하도록 하는 자동 뉴스 다이제스트 봇을 만든다(PRD 참조). MVP는 매일 1회 발송, 3개 카테고리, 카테고리당 5~10건 큐레이션. 운영 환경을 결정해야 한다. 결정 축은 4개:

1. 언어/런타임
2. 실행 인프라(스케줄러·서버)
3. AI 요약 모델
4. V1 발송 채널

### 결정

- **언어/런타임: Python 3.12**
- **실행 인프라: GitHub Actions cron** (`.github/workflows/daily.yml`, KST 07:30 = UTC 22:30 전일)
- **AI 요약 모델: Anthropic Claude Haiku 4.5** (1차), 품질 부족 시 카테고리 단위로 Sonnet 4.6 옵션
- **V1 발송 채널: Gmail SMTP** 이메일만. 메신저(슬랙·카카오워크 등)는 V2.

### 결과

**얻는 것**
- Python: RSS(`feedparser`)·HTML 파싱(`beautifulsoup4`)·SMTP(`email`/`smtplib`)·Anthropic SDK 모두 표준이고 예제 풍부. 사내 학습 곡선 낮음.
- GitHub Actions: 별도 서버·VPS 불필요. 무료 한도(월 2000분) 대비 예상 사용량(월 ~66분)이 매우 여유. Secrets 관리·로그 보관(90일) 내장.
- Claude API Haiku 4.5: 한국어 요약 품질 충분, 토큰 단가 저렴(월 $20 이하 예상). 사용량 폭주 시 사용자 환경의 hard cap으로 차단.
- Gmail SMTP: 팜보스가 이미 Google Workspace 환경. 별도 ESP(SendGrid 등) 결제·인증 절차 없음. 수신자 추가가 `recipients.yml`에 한 줄 추가로 끝남.

**감수하는 것**
- GitHub Actions cron은 정시 ±몇 분 지연이 정상(공식 SLA 아님). PRD의 "07:30 ± 5분, 95% 정시"는 4주 모니터링 후 미달 시 ADR-supersede.
- Gmail SMTP는 일일 발송 한도(앱 비밀번호 기준 ~500통/일)가 있지만 사내 수신자 ≪ 100명이라 V1에서 문제 없음. 외부 공개로 확장 시 재검토.
- 영속 저장소가 없어 발송 이력 저장은 별도 결정 필요 → ADR-002에서 다룸.
- **V1 발송자 주소** (2026-05-19 사용자 결정): `GMAIL_FROM = nterrr@gmail.com` (운영자 본인 Gmail 계정)으로 V1 시작. Workspace 전용 봇 계정(예: `trendbot@farmboss.kr`) 신규 개설은 V1.5 이후로 보류. 사유: ① 신규 계정 생성·앱 비밀번호 발급 절차 단축, ② V1 수신자가 단계적 공개(운영자 → 3이사 → 전 직원, requirements AC-6.4)라 초기에는 사적 계정으로 충분, ③ Workspace 관리자 일정 의존 없이 즉시 시작 가능. 트레이드오프: 사적 계정으로 받는 메일은 공식감이 약하므로 전 직원 공개 단계 전까지 봇 계정 이관 검토 필요.

### 대안

- **AWS Lambda + EventBridge**: 안정적·SLA 명확. 그러나 AWS 계정·IAM·VPC 설정 비용, Secrets는 별도(SSM/Secrets Manager) 필요. V1 규모에 과한 운영 부담.
- **사내 Windows PC + Task Scheduler**: PC 켜져 있어야 하고 재부팅·VPN·네트워크 단절 위험. 백업/모니터링 부담을 직원이 짐.
- **Cloud Run / Cloud Functions Scheduler**: GCP 자체는 좋지만 Google Workspace와 별개 결제·프로젝트 분리. V1에는 과한 셋업.
- **n8n / Make.com 노코드**: 빠르지만 카테고리별 요약 프롬프트·dedup·필터 같은 도메인 로직을 코드로 명시·테스트하기 어려움. 변경 추적도 git에 비해 약함.
- **OpenAI GPT-4o-mini**: 가능. 사용자 환경이 이미 Claude 중심이고 한국어 톤 자연스러움에서 차이가 크게 없어 Anthropic으로 통일.
- **Slack 발송 우선**: 팜보스가 슬랙 표준이라면 1순위였겠지만, 전 직원 채널 표준화 여부 미확인 + 이메일은 누구나 받음. V2에서 슬랙 어댑터 추가가 인터페이스만 잘 맞추면 가벼움.

---

## ADR-002: 발송 이력 저장 매체 (영속화)

날짜: 2026-05-19
상태: accepted

### 맥락

dedup의 신뢰원은 "최근 N일 발송 이력". GitHub Actions는 stateless라 다음 실행 시 이전 발송 결과를 어디서 읽을지 결정해야 한다. Stage 3 Tech Research(`docs/features/daily_digest/daily_digest_v1-tech-research.md` §3-5)에서 후보 3종을 영속성·구현 복잡도·실패 모드·추적성 4축으로 비교했다.

### 결정

**A. GitHub Actions artifact + 매일 download/upload**를 V1에서 사용한다.

- 워크플로 시작 시 `actions/download-artifact@v4`로 직전 `sent.jsonl` 다운로드.
- 종료 직전 `actions/upload-artifact@v4`로 갱신본 업로드.
- artifact 이름: `digest-history` (고정). 90일 자동 보존.

스키마(`sent.jsonl`)는 requirements §6-4에 동결. 최상위 `version: 1` 필드로 향후 마이그레이션 대응.

### 결과

**얻는 것**
- 구현 복잡도 최소(다운로드·업로드 2 step). 봇이 main에 push할 commit 권한 불필요.
- 시크릿 관리 단순(`GITHUB_TOKEN` 기본 제공).
- 인증·권한 실패 모드 단순.

**감수하는 것**
- 추적성이 약함: 운영자가 history를 보려면 Actions UI에서 artifact를 다운로드해야 함. 즉시 열람 어려움.
- artifact 누락(스토리지 장애·90일 경과·실수 삭제) 시 dedup 미적용 → 전일 중복 발송 가능. 첫 실행 시 artifact 없으면 빈 history로 부팅.
- 90일 후 자동 삭제: 7일 dedup 윈도우에는 영향 없으나 장기 운영 통계는 별도 저장 필요.

**6개월 후 재검토 트리거**
다음 중 하나 이상이면 후보 B(repo push) 또는 C(Issue 누적)로 migrate 결정:
- 운영자가 디버깅 시 artifact 다운로드 부담 호소
- artifact 누락 사고 발생
- 6개월 누적 history를 분석·시각화하려는 요구

migrate plan: `history/store.py`의 backend를 인터페이스(`HistoryBackend`)로 추상화하고 구현체만 교체. 스키마는 동일(`sent.jsonl` 한 줄 1 JSON) 유지.

### 대안

- **B. repo 내 `history/sent.jsonl` 자동 push** — 추적성 최고지만 봇이 main에 push하는 운영 부담(권한, conflict, force-push 위험). V1 단순성과 충돌. Reject (현재).
- **C. GitHub Issue 본문 누적** — 시각화는 좋으나 본문 크기 한도(65KB)가 1년 운영 시 분할 부담. API 호출 횟수 증가. Reject (현재).
- **D. 외부 KV store (Redis Cloud, Upstash 등)** — 추가 외부 의존성·계정·시크릿. V1 단순성과 충돌. Reject.
