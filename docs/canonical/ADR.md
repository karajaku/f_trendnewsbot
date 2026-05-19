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
상태: superseded — 발송 채널은 ADR-003 (Gmail SMTP → 텔레그램 Bot API + GitHub Pages), AI 요약 모델은 ADR-004 (Anthropic Claude Haiku 4.5 → Google Gemini 2.0 Flash) 에 의해 변경. 언어·인프라 결정은 여전히 유효.

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

---

## ADR-003: V1 발송 채널 — 텔레그램 Bot API + GitHub Pages (이메일 폐기)

날짜: 2026-05-19
상태: accepted (ADR-001의 발송 채널 결정을 supersede)

### 맥락

ADR-001에서 V1 발송 채널을 Gmail SMTP로 잡았다. 사용자 일괄 검토 후속 대화(2026-05-19)에서 "직원이 매일 메일함을 열어 다이제스트를 정독한다"는 가정의 불확실성이 제기됐다. 팜보스 그룹의 실제 사내 표준 메신저는 **텔레그램 그룹채팅방**으로 확인됐다.

채널 변경의 트레이드오프를 4축으로 정리했다.

| 축 | 이메일 | 텔레그램 |
|---|---|---|
| 즉시 도달·낮은 마찰 | 보통 (메일함 열기 필요) | **높음** (단톡방 push 알림) |
| 보관·검색·과거 조회 | **높음** (메일 검색 강력) | 낮음 (메시지 흘러감) |
| 대량·긴 본문 | **높음** (HTML 본문 그대로) | 보통 (4096자/메시지 한도, 채팅창 점령) |
| 셋업 부담 | 보통 (Gmail 앱 비밀번호) | 낮음 (BotFather 토큰 1개) |

이메일의 "보관·검색"은 GitHub Pages로 대체 가능하다. Pages는 매일 URL 1개씩 누적되고, public + noindex로 검색엔진 노출 없이 직원만 접근. 검색은 GitHub repo 내 검색이나 직원이 URL 패턴 추측으로 가능.

### 결정

**V1 발송 채널을 텔레그램 Bot API + GitHub Pages 조합으로 변경**한다. Gmail SMTP·이메일 발송은 V1에서 제거.

운영 흐름:
1. summarizer가 다이제스트 본문 생성 (HTML + 짧은 인덱스 text 두 형식)
2. dispatcher가 매일 cron마다:
   - HTML을 **`gh-pages` branch** 의 `digest/YYYY-MM-DD.html` 로 commit·push → GitHub Pages 자동 배포. master branch 의 docs/ 는 Pages 에 노출되지 않음.
   - 짧은 인덱스 + Pages URL을 텔레그램 Bot API로 단톡방에 발송
3. 직원이 단톡방 알림 → 헤드라인 훑기 → 관심 항목만 Pages URL 클릭 → 브라우저에서 본문

운영자 alert:
- 별도 텔레그램 chat(`OPS_ALERT_CHAT_ID`)에 짧은 텍스트로 발송. 직원 단톡방은 깨끗하게 유지.

Pages 공개 정책 (2026-05-19 갱신 — 사내 문서 노출 위험 발견 후 boundary 분리):
- public repo 의 Pages 를 **`gh-pages` branch root** 로 설정. master 의 `docs/canonical/`·`docs/features/`·`docs/_extracted/` 등 회사 사내 문서는 Pages 에 노출되지 않는다.
- `gh-pages` branch 안에는 다이제스트 HTML 파일과 `robots.txt`·`index.html`(선택) 만. 다른 파일 commit 금지.
- HTML 헤더에 `<meta name="robots" content="noindex,nofollow">` + `gh-pages` root 의 `robots.txt` 에 `User-agent: * / Disallow: /` 로 검색엔진 크롤링 차단.
- 회사 내부 데이터(시세·매출·인사)는 어차피 다이제스트 본문에 없음 — 본문은 외부 뉴스 큐레이션. 외부 노출돼도 위험 작음.
- **운영자 초기 셋업 (1회)**: 빈 `gh-pages` orphan branch 생성·push (`git checkout --orphan gh-pages` → `git rm -rf .` → 빈 README 또는 robots.txt commit → `git push origin gh-pages` → `git checkout master`). 그 후 Repo Settings → Pages 에서 Source: Deploy from branch · Branch: `gh-pages` · Folder: `/ (root)` 설정. 자세한 가이드는 `docs/ops/secrets_setup.md` (step7).

### 결과

**얻는 것**
- 즉시 도달·낮은 마찰: 단톡방 push 알림이 메일 열기보다 직원이 빠르게 인지.
- 셋업 단순: 텔레그램 BotFather에서 토큰 발급 1회, 단톡방에 봇 초대 1회. Gmail 앱 비밀번호·BCC·SMTP 인증 부담 제거.
- 수신자 관리 단순: `recipients.yml` 폐기. 직원 추가·제거는 단톡방 입퇴장으로 처리.
- 보관·검색: GitHub Pages가 매일 URL 1개씩 누적. 과거 조회는 URL 패턴(`/digest/YYYY-MM-DD.html`)으로 직접 접근.
- 추적성: HTML 파일이 git history로 영구 보존.

**감수하는 것**
- 메일 검색만큼 강력한 과거 조회 없음. Pages는 URL 알아야 접근.
- 단톡방 점유: 단톡방을 다이제스트 전용으로 두지 않으면 다른 대화에 묻힘 → V1은 **다이제스트 전용 단톡방** 권장.
- 직원이 텔레그램 안 깔았으면 설치 마찰 — 회사 차원 일괄 안내 필요.
- Pages 호스팅이 깨지면(force push 실수) 과거 다이제스트 다 사라짐 — git history로 복구 가능.
- 검색엔진 noindex는 "착한 크롤러"에만 작동. 악의적 크롤러는 차단 못 함. 다만 다이제스트 본문에 회사 기밀 없음.

**전환 일정**
- AC-6.4 (단계적 공개) 동일 적용: 운영자 1주 → 3이사 1주 → 전 직원. 단톡방 멤버 초대 일정으로 해석.
- ADR-001의 발송자 주소 결정(`nterrr@gmail.com`)은 더 이상 적용되지 않음 — 메일 발송 자체가 사라짐.

**6개월 후 재검토 트리거**
다음 중 하나 이상이면 이메일 dispatcher 재도입 또는 다른 메신저(슬랙·카카오워크) 추가 검토:
- 텔레그램이 회사 표준에서 밀려나는 경우
- 이사진이 "메일도 받고 싶다" 명시 요청
- Pages 운영 부담 호소

### 대안

- **A. 이메일 + 텔레그램 + Pages 셋 다 (이중 발송)** — 마이너리티 수신·검색 모두 보존. dispatcher 2개, 수신자 관리 복잡도 증가, phase 일정 1주 증가. V1 단순성과 충돌. Reject — 가치 대비 복잡도.
- **B. 텔레그램 메시지에 본문 전체 포함, Pages 없음** — Pages 호스팅 부담 0이지만 채팅창 점령, 아카이브 가치 0. Reject — 아카이브 가치를 포기하기 아쉬움.
- **C. 카카오톡 단톡방** — 일반 카카오톡은 봇 API가 폐쇄적이라 매일 자동 발송 불가. 알림톡은 사업자 등록·템플릿 등록 필요(자유 본문 불가). 카카오워크는 회사 도입 필요. Reject — 현재 사용 가능 범위 밖.
- **D. 슬랙·Teams·카카오워크** — 회사가 도입한 사내 메신저가 없는 상태라 추가 도입 마찰. Reject — V2에서 도입 시 재검토.
- **E. private repo Pages (GitHub Pro $4/월)** — 완전 비공개. 직원이 GitHub 계정 로그인 + 권한 부여 필요. 운영 마찰 증가. Reject — 본문이 외부 뉴스 큐레이션이라 public + noindex로 충분.
- **F. Pages root `/docs` (master branch 의 docs 폴더)** — 가장 단순하지만 master 의 `docs/canonical/`·`docs/features/`·`docs/_extracted/` 같은 회사 사내 문서가 모두 외부 공개됨 (PRD·requirements·운영 매뉴얼 등). 2026-05-19 사용자 검토 중 발견된 위험. Reject — 채택 옵션은 `gh-pages` branch (boundary 분리).

---

## ADR-004: V1 LLM provider — Anthropic Claude Haiku 4.5 → Google Gemini 2.0 Flash

날짜: 2026-05-19
상태: superseded — 모델 ID `gemini-2.0-flash` 는 ADR-005 (2026-05-19) 에 의해 `gemini-2.5-flash` 로 변경. provider (Google Gemini) 결정 자체는 유효.

### 맥락

phase 01 step7 dry-run (2026-05-19 16:59 KST) 에서 GitHub Actions workflow 가 정상 트리거되고 secrets 6개가 로딩됐으나 Anthropic API 호출에서 `BadRequestError 400 — Your credit balance is too low` 발생. ops_alert 분기는 정상 동작해 운영자 단톡방에 예외 메시지 도착.

대응 옵션:
1. Anthropic 계정 크레딧 충전 (단발성, $5 충전 시 1~3개월 운영) — 코드 변경 0.
2. 무료 tier LLM provider 로 swap — 영구 운영 비용 0.
3. LLM 없는 extractive 요약으로 후퇴 — 사용자 요구사항(분석·점수·회사 영향) 손실.

운영자가 무료 영구화를 우선해 옵션 2 선택 (2026-05-19). 현재 사용 가능한 무료 tier LLM 중 한국어 품질·rate limit·SDK 안정성을 4축으로 비교:

| 모델 | 한국어 품질 | Rate limit | SDK 안정성 | 비고 |
|---|---|---|---|---|
| **Google Gemini 2.0 Flash** | 매우 좋음 | 15 RPM / 1500 RPD | google-genai 안정 | JSON mode native, 무료 영구 |
| Groq (Llama 3.3 / Qwen) | 보통~좋음 | 30 RPM (무료) | OpenAI 호환 | 한국어 농산물 용어 정확도 한 단계 낮음 |
| Cerebras / Together free tier | 보통 | 변동적 | 변동적 | 정책 불안정 |
| 로컬 Ollama | 모델별 상이 | 무제한 | 안정 | GitHub Actions runner GPU·메모리 부족 → 자체 서버 필요. 제외 |

V1 일일 호출 규모: 카테고리 3개 × 1~2 chunk + 재시도 여유 ≈ 4~6회/일. Gemini 무료 tier (1500 RPD) 의 0.4% 미만 사용 → 안정적 운영 가능.

### 결정

**V1 LLM provider 를 Google Gemini 2.0 Flash 로 변경**한다. 모델 ID `gemini-2.0-flash`, SDK `google-genai>=0.3.0`.

운영 흐름:
1. `src/summarizer/client.py` 내부를 Anthropic SDK → google-genai SDK 로 swap. `SummarizerClient.summarize() → SummarizeResult` 인터페이스는 유지 (caller 무영향).
2. JSON 출력은 Gemini native JSON mode (`response_mime_type="application/json"` + `response_schema=...`) 로 강제. `prompts/summarize.md` 본문은 그대로 재사용 (schema 동일).
3. Anthropic prompt caching (`cache_control: ephemeral`) 은 제거. Gemini Context Caching API (`client.caches.create`) 는 V1.1+ 에서 검토 — 무료 tier 비용 0이라 V1 단순성 우선.
4. quota 초과 (429 / `google.genai.errors.ClientError` / `ResourceExhausted`) → 우리 `QuotaExceededError` 로 매핑 → run_daily.py 의 exit 2 분기에 도달 (AC-5.3).
5. 환경변수 rename: `ANTHROPIC_API_KEY` → `GEMINI_API_KEY`, `CLAUDE_MODEL_ID` → `GEMINI_MODEL_ID`. GitHub Secrets·workflow yml·secrets_setup·PRD·requirements §8 동시 갱신.

전환 phase: `phases/02-gemini-swap/` 4 step (ADR+deps / client.py 재작성 / env rename / pytest+dry-run).

### 결과

**얻는 것**
- 운영 비용 0원 (무료 tier 영구). 크레딧 잔량 감시 부담 제거.
- Gemini 2.0 Flash 는 Claude Haiku 4.5 대비 한국어 일반 요약 품질 동등 수준 (2025-2026 공개 벤치마크 기준). 농산물·유통 도메인 용어는 prompt 의 회사 컨텍스트로 보강 가능 (system_instruction 그대로).
- JSON mode 가 schema 강제라 응답 형식 위반 빈도 낮아질 가능성 (Anthropic 은 markdown fence 가끔 발생 → `_strip_markdown_fence` 헬퍼로 대응 중).
- SDK 무료, 발급 즉시 (Google 계정만 필요).

**감수하는 것**
- Gemini 무료 tier 정책 변경 위험 (Google 이 무료 한도를 축소·종료할 수 있음). 모니터링 트리거: 일일 호출 실패율 > 5% 또는 Google 공식 공지. trigger 시 ADR-005 로 재검토.
- prompt caching 없음 → 매 호출 system_instruction 전송. 무료 tier 라 비용 부담 0, 토큰 latency 만 약간 증가 (수십 ms). V1 SLA (±15분 정시성) 에는 영향 없음.
- Gemini 의 농산물·유통 도메인 한국어 정확도가 Claude 대비 한 단계 약할 가능성. 1주 dry-run 후 직원 피드백 수집 → 필요 시 prompt 튜닝 또는 V1.1 에서 Sonnet/Opus 옵션 재추가.
- Anthropic 계정·SDK 의존 제거 → V2에서 Anthropic 재도입 시 dispatcher 인터페이스 재추상화 필요. 단, `SummarizerClient` 인터페이스가 SDK-agnostic 이라 부담 작음.

**6개월 후 재검토 트리거**
다음 중 하나 이상이면 LLM provider 재검토:
- Gemini 무료 tier 정책 변경 (한도 축소·종료·유료 전환)
- Gemini 응답 품질이 직원 피드백에서 명시적으로 문제 제기됨
- Google API 의 한국 IP·관할 정책 변경

migrate plan: `src/summarizer/client.py` 의 내부만 swap. caller (`run_daily.py`·`render.py`) 와 `SummarizeResult` dataclass 는 SDK-agnostic 이라 무영향.

### 대안

- **A. Anthropic $5 충전 + V1.1 에서 Gemini swap** — 가장 안정적·코드 변경 0. Reject — 사용자가 무료 영구화 우선. 운영 비용 발생 자체를 회피.
- **B. Groq (Llama 3.3 / Qwen)** — 무료 영구·매우 빠름. Reject — 한국어 농산물 도메인 용어 정확도가 Gemini 대비 한 단계 낮음. V1 의 단톡방 직원 첫 경험에서 hallucination 가능성을 줄이는 게 우선.
- **C. OpenAI GPT-4o-mini** — 한국어 우수. Reject — 무료 tier 없음 (신규 가입 $5 trial 도 2024년 종료). 운영 비용 발생.
- **D. 로컬 Ollama / vLLM** — 완전 무료. Reject — GitHub Actions runner 에 GPU·메모리 부족. 자체 서버 운영 필요 → V1 단순성과 충돌.
- **E. LLM 없는 extractive 요약 (RSS description 첫 N문장)** — 무료·SDK 의존 0. Reject — 사용자 요구사항 (점수·summary·company_impact·category_headlines 분석 출력) 후퇴.
- **F. Gemini 2.0 Flash + prompt caching (Context Caching API)** — 토큰 비용 추가 절감 가능. Defer — 무료 tier 비용 0이라 V1.1 이후에 검토. 캐시 만료·invalidation 코드 추가가 V1 단순성과 충돌.
- **G. Gemini 2.5 Pro / Ultra (유료 tier 모델)** — 품질 더 높음. Reject — V1 일일 비용 발생. Flash 로 시작 → 직원 피드백에서 품질 부족 호소 시 V1.1 에서 카테고리 단위 Pro 옵션 검토 (ADR-001 의 Haiku→Sonnet 옵션 패턴과 동일).

---

## ADR-005: Gemini 모델 ID — `gemini-2.0-flash` → `gemini-2.5-flash` (deprecation 대응)

날짜: 2026-05-19
상태: accepted (ADR-004 의 모델 ID 결정을 supersede; provider 결정은 그대로 유효)

### 맥락

phase 02 step4 dry-run (2026-05-19 19:36 KST) 에서 신규 GCP project + 신규 `GEMINI_API_KEY` 로 호출 시 다음 응답:

```
ClientError 404 NOT_FOUND
"This model models/gemini-2.0-flash is no longer available to new users.
 Please update your code to use a newer model for the latest features and improvements."
```

직전 시도 (같은 모델, 결제 미연결 기존 project) 에서는 `limit: 0` 형태의 quota error 였다 — 신규 가입 시점부터 `gemini-2.0-flash` 사용권이 부여되지 않음. Google 이 2.0-flash 의 신규 사용자 가입 창구를 닫고 후속 모델 (2.5 라인) 로 유도하는 상태로 추정.

ADR-004 의 "6개월 후 재검토 트리거" 첫 번째 항목 (`Gemini 무료 tier 정책 변경 — 한도 축소·종료·유료 전환`) 발동. provider (Google Gemini) 자체는 유지 — SDK·JSON mode·prompt 자산 그대로 재사용 가능.

후보 (2026-05 기준):

| 모델 | 무료 tier | 한국어 품질 | 비고 |
|---|---|---|---|
| **gemini-2.5-flash** | 지원 (15 RPM / 1500 RPD 추정) | 우수 (2.0-flash 대비 향상) | Gemini 2.5 라인의 표준 flash, JSON mode/`response_schema` 호환 |
| gemini-2.5-flash-lite | 지원, 더 높은 한도 | 양호 (2.5-flash 대비 약간 낮음) | 더 저렴·빠름, 무료 tier 친화 |
| gemini-2.5-pro | 유료 only (또는 매우 작은 무료 한도) | 최상위 | V1 비용 0 원칙 위반 |
| gemini-1.5-flash | 지원 (Legacy) | 양호 (구버전) | 2.0-flash 와 비슷한 deprecation 위험 |

### 결정

**모델 ID 를 `gemini-2.5-flash` 로 변경**한다. SDK (`google-genai>=0.3.0`), 호출 시그니처, JSON mode, `response_schema`, `prompts/summarize.md` 모두 그대로 재사용.

운영 흐름:
1. `src/summarizer/client.py` `DEFAULT_MODEL` 상수 갱신: `gemini-2.0-flash` → `gemini-2.5-flash`.
2. `docs/features/daily_digest/daily_digest_v1-requirements.md` §8, `docs/ops/secrets_setup.md`, `.env.example`, `tests/test_summarizer.py` 의 모델 ID 표기 일괄 갱신. (ADR-004 본문·phase ledger·hotfix log 는 audit trail 로 보존.)
3. GitHub Actions Variables 의 `GEMINI_MODEL_ID` 값이 명시되어 있다면 운영자가 `gemini-2.5-flash` 로 갱신 또는 삭제 (코드 default fallback 으로 충분). secrets_setup.md 안내 갱신.
4. ADR-004 status → `superseded` (provider 결정은 유효, 모델 ID 만 변경).

### 결과

**얻는 것**
- 신규 GCP project 에서도 즉시 사용 가능 (deprecation 해소).
- 2.5-flash 는 2.0-flash 대비 한국어·instruction following 품질 향상 (2025-06 Gemini 2.5 라인 출시 시 공개 벤치마크 기준).
- caller·prompt·SDK 인터페이스 무변경 → 호출부 영향 0.

**감수하는 것**
- Gemini 2.5-flash 도 정책 변경 위험 동일. 동일 모니터링 트리거 유지 (ADR-004 의 6개월 재검토 트리거 항목 그대로 승계).
- 토큰 latency·비용 (무료 tier 한도) 의 정확한 수치는 Google 공지에 의존. 1주 dry-run 후 직원 피드백 + Actions 로그의 호출 시간 분포로 재확인.
- 2.5-flash 의 prompt caching API (Context Caching) 가 2.0-flash 와 호환되는지 V1.1+ 검토 시 재확인 필요.

**6개월 후 재검토 트리거 (ADR-004 승계)**
- Gemini 2.5-flash 무료 tier 정책 변경 (한도 축소·종료·유료 전환)
- 신규 사용자 가입 차단 (이번 ADR-005 의 발동 패턴)
- Gemini 응답 품질이 직원 피드백에서 명시적으로 문제 제기됨
- Google API 의 한국 IP·관할 정책 변경

trigger 시 ADR-006 으로 재검토 (Gemini 3 라인 / Groq / paid tier 비교).

migrate plan: `DEFAULT_MODEL` 상수 1줄 변경 + 문서 5개 파일 일괄 swap. caller (`run_daily.py`·`render.py`) 와 `SummarizeResult` dataclass 는 무영향.

### 대안

- **A. `gemini-2.5-flash-lite`** — 더 저렴·빠름·한도 더 큼. Defer — V1 첫 운영에서는 표준 flash 가 한국어 품질에서 더 안전. 직원 피드백에서 V1.1 로 전환 검토 가능.
- **B. `gemini-2.5-pro`** — 품질 최상위. Reject — V1 비용 0 원칙 위반 (paid tier).
- **C. `gemini-1.5-flash` (legacy)** — 즉시 호환. Reject — 같은 deprecation 위험 (Google 이 1.5 라인도 점진 종료 중인 정황). 후행 ADR 한 번 더 발생.
- **D. provider 재-swap (Groq Llama 3.3 / OpenRouter)** — 완전히 다른 무료 tier. Reject — ADR-004 의 한국어 도메인 품질 비교 결과 (Gemini 우위) 가 여전히 유효. 모델 ID 1줄 변경 vs SDK·prompt 재작성의 비용 비교에서 1줄 변경이 압도적.
- **E. Anthropic paid tier 재전환** — Claude Haiku 4.5 가 한국어 우수. Reject — 운영 비용 발생. ADR-004 의 무료 영구화 원칙과 충돌.
