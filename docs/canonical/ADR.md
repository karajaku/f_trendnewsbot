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
상태: draft — V1 첫 phase 끝나기 전 결정

### 맥락

dedup의 신뢰원은 "최근 N일 발송 이력". GitHub Actions는 stateless라 다음 실행 시 이전 발송 결과를 어디서 읽을지 결정해야 한다.

### 결정

(아직 결정 안 함 — 첫 phase에서 다음 세 옵션 중 하나로 확정)

후보:
1. **GitHub Actions artifact + 매일 download/upload** — 90일 자동 보존, 인증 자동.
2. **repo 내 `history/sent.jsonl`을 봇이 push** — git history로 추적 가능, 그러나 봇이 commit 푸시 권한 필요.
3. **GitHub Issue 본문 누적** — 시각화 쉬움, 그러나 본문 크기 한도·동시성 관리 부담.

### 결과

(결정 후 기재)

### 대안

(결정 후 기재)
