---
status: frozen
review_count: 1
created_at: "2026-05-19"
last_reviewed_at: "2026-05-19"
reviewer: "Claude (Stage 4 자가 교차 검토 + 수정 항목 3건 반영)"
feature: daily_digest_v1
based_on_brief: "docs/features/daily_digest/daily_digest_v1-brief.md"
based_on_tech_research: "docs/features/daily_digest/daily_digest_v1-tech-research.md"
applied_at: "2026-05-19"
applied_by: "phases/01-mvp-daily-digest/"
frozen_at: "2026-05-19"
frozen_by: "phases/01-mvp-daily-digest/"
---

# daily_digest V1 — Requirements

> 역할: V1 매일 다이제스트 봇의 acceptance criteria·data contract·의존 시스템·범위 외를 동결한다. Stage 5 phase 계획의 단일 입력 문서.
> 대상: Stage 5 phase 계획 작성자, Stage 6 구현자, Stage 7 QA reviewer.

---

## 1. 의존 시스템

| 시스템 | 영향 방향 | 비고 |
|---|---|---|
| Anthropic Claude API (Haiku 4.5) | 외부 의존 | summarizer가 호출. 일일 토큰·호출 hard cap 필수. |
| Gmail SMTP (smtp.gmail.com:465 SSL) | 외부 의존 | dispatcher가 발송. 앱 비밀번호 사용. |
| GitHub Actions Runner (ubuntu-latest) | 실행 인프라 | cron 트리거. 시크릿 주입 매체. |
| GitHub Actions Artifact storage | 영속 저장 (ADR-002) | history 모듈이 sent.jsonl을 업로드·다운로드. 90일 보존. |
| 외부 뉴스 소스 (RSS·HTML) | 외부 의존 | fetchers가 호출. 소스 단위 격리. 12~18개 소스. |
| Python 3.12 표준 라이브러리 (smtplib, email, zoneinfo, logging) | 내부 의존 | SMTP 발송·KST 변환·로깅. |
| 외부 패키지 (anthropic, feedparser, requests, beautifulsoup4, pyyaml, python-dateutil) | 내부 의존 | pyproject.toml 동결 버전. |

## 2. 범위 외 (명시적)

brief §3-7 비-목표 7개를 그대로 인용한다. 추가 V1 범위 외:

- 카테고리당 11건 이상 큐레이션 — 인지 부하 증가, 5분 읽기 목표 깨짐.
- "why it matters" / "당신에게 의미" 같은 LLM 코멘트 — Discovery 결론 #2 + Tech 결론 #2.
- 뉴스 본문 전체 인용·복사 — 저작권. 제목·한국어 요약 2문장·원문 링크 형식 고정.
- 사내 다른 시스템과 연동 (사내 ERP·재고·시세 시스템 등) — V2+.
- 한국어 외 발송 톤(영문 다이제스트) — 직원이 모두 한국어 사용.
- 사용자별 카테고리 가중치 — V2+.
- 발송 이력에서 직원 OPEN·CLICK 트래킹 — 사생활 침해 우려·V1 가치 부족.
- 외부 뉴스레터(TLDR AI·미라클레터 등) 구독 권고·중복 회피 — 직원 자율로 결정 (2026-05-19 사용자 결정). 본 V1은 외부 뉴스레터가 다루지 않는 회사 키워드(청도 산지·GS리테일 동향 등) 카테고리로 차별화.

## 3. 리서치 시사점 (Tech Research 결론 인용)

Stage 3 Tech Research 결론 5개를 그대로 인용한다(각 항목 끝에 출처 표기).

- 저장 매체는 GitHub Actions artifact로 시작. `history/sent.jsonl` 스키마는 §6 data contract에 명시. 6개월 후 migration 옵션은 ADR-002 §결과 참조 `(tech-research.md 결론 #1)`
- Claude API 호출은 V1 단일 호출(점수+요약 동시) 시작. V2에서 quality 모니터링 후 분리 검토 `(tech-research.md 결론 #2)`
- PRD 정시성 기준을 "KST 07:30 ± 15분 95%"로 완화 + cron을 KST 07:20(UTC 22:20)으로 당겨 10분 흡수. 4주 모니터링 후 실측 분포 반영 `(tech-research.md 결론 #3)`
- `lib/url_helper.canonicalize(url) -> str`, `lib/time_helper.to_kst_string(dt) -> str`, `lib/time_helper.now_kst() -> datetime`이 dedup·render·dispatcher·history 공유 단일 진실 `(tech-research.md 결론 #4)`
- `config/filters.yml`의 "팜보스 관심 키워드" 시드 12개 키워드 동결. dry-run 후 보강은 phase 외 운영 `(tech-research.md 결론 #5)`

## 4. Acceptance Criteria

### AC-1. 발송 시각·빈도

- **AC-1.1**: `.github/workflows/daily.yml`의 cron이 `30 22 * * *`로 설정됨(UTC, 매일). 라인 위 주석에 "= KST 익일 07:20 매일(토·일·공휴일 포함)" 명시. (cron은 발송 목표보다 10분 일찍 시작 — Tech 결론 #3) (2026-05-19 갱신)
- **AC-1.2**: 본문 헤더에 "5월 19일 (월) 오전 7:30 KST" 형식의 KST 절대 시각 표기. `lib/time_helper.format_subject_date(dt)` helper로 통일.
- **AC-1.3**: 발송 SLA "KST 07:30 ± 15분 95%" — `docs/canonical/PRD.md`의 성공 기준을 본 requirement 동결 시 갱신.
- **AC-1.4**: **매일 발송** — 토·일·공휴일 포함. (2026-05-19 사용자 결정 — 기존 "영업일만"에서 변경) workflow_dispatch 수동 트리거도 가능.
- **AC-1.5**: 한국 공휴일 자동 스킵은 V1·V2 모두 적용하지 않음 (2026-05-19 사용자 결정 — AI 트렌드는 주말·공휴일에도 발생). 특정 공휴일 발송을 차단하려면 운영자가 해당일 cron을 수동 disable.
- **AC-1.6**: 메일 제목 형식 `[팜보스 트렌드] M/D(요일) AI·농산물 유통 오늘의 뉴스 N건` (예: `[팜보스 트렌드] 5/19(월) AI·농산물 유통 오늘의 뉴스 8건`). N=0이면 "오늘 새 뉴스 없음"으로 본문은 발송, 제목 N건은 `0건`. (2026-05-19 사용자 결정)

### AC-2. 카테고리·항목

- **AC-2.1**: 본문에 카테고리 3개(`AI 트렌드` → `농산물·유통` → `팜보스 관심 키워드`) 순서 고정. 카테고리당 5~10건, 0건 시 "오늘 새 뉴스 없음" 명시.
- **AC-2.2**: 한 기사가 복수 카테고리 매칭 시 좁은 쪽 1곳에만 노출. 우선순위: `팜보스 관심 키워드` > `농산물·유통` > `AI 트렌드`. `filters/category.py`가 단일 매핑 결정.
- **AC-2.3**: 항목 form: `{번호}. {제목}\n   요약: {2문장 이내 한국어}\n   원문: {full URL}   ({출처명} · {KST 발행시각})`. plain-text와 HTML 본문 모두 동일 정보 노출.
- **AC-2.4**: 영어 원문은 한국어 번역 제목 + 괄호로 원제 병기 — `Anthropic, Claude Opus 4.7 출시 (Announcing Claude Opus 4.7)`.
- **AC-2.5**: 본문에 "why it matters" 같은 LLM 코멘트 라인 미포함(생성 금지).
- **AC-2.6**: 본문 풋터에 의견·소스 회신 안내 한 줄 — `의견·소스 추가 요청은 이 메일에 회신해 주세요. 운영: {운영자 표기}` (2026-05-19 사용자 결정). `Reply-To` 헤더는 `OPS_REPLY_TO` 환경변수.
- **AC-2.7**: 본문 헤더 이모지는 `📰` 1개만 (제목 prefix), 카테고리 헤더는 번호 `① AI 트렌드` `② 농산물·유통` `③ 팜보스 관심 키워드` 형식. 본문 항목 내부에는 이모지 사용하지 않음. (2026-05-19 사용자 결정)

### AC-3. 요약 품질·신뢰성

- **AC-3.1**: 요약 출력 길이 2문장 이내. system prompt에 명시 + 후처리에서 3문장 이상 잘라냄.
- **AC-3.2**: 숫자·고유명사·날짜는 원문 그대로 인용. system prompt에 "원문에 없는 수치·인과·날짜를 생성하지 말 것" 명시.
- **AC-3.3**: 모든 항목에 원문 URL 노출 (단축 URL 금지). URL 검증 helper가 발송 전 200~399 응답 확인 — 4xx/5xx면 항목 제외 + 메타에 누락 사실 노출.

### AC-4. dedup·이력

- **AC-4.1**: URL은 `lib/url_helper.canonicalize(url)` 통과 후 비교. canonicalize는 ① 호스트 lowercase ② 쿼리스트링에서 `utm_*`, `fbclid`, `gclid` 제거 ③ trailing slash 제거 ④ fragment 제거.
- **AC-4.2**: dedup 윈도우 = 발송 KST 기준 최근 7일. 7일 안에 발송된 canonical URL이 다시 등장하면 제외.
- **AC-4.3**: 제목 fuzzy match (Levenshtein 또는 `difflib.SequenceMatcher.ratio()` ≥ 0.85)로 보조 검사 — 다른 URL이지만 같은 기사인 경우 1건만 발송. dry-run 1주일 후 실측 false positive/negative 분포에 따라 0.80~0.90 범위에서 조정 가능. 조정은 `config/filters.yml`의 `global.fuzzy_title_threshold`만 변경. (2026-05-19 추가)
- **AC-4.4**: 발송 직후 `history/sent.jsonl` append + GitHub Actions artifact 업로드. 다음 실행 시 다운로드해서 입력.

### AC-5. 실패 격리·운영자 alert

- **AC-5.1**: 한 소스 fetch 실패가 전체 발송을 중단시키지 않음. `fetchers.run_all(sources) -> (list[Article], list[Failure])` 반환 형태 강제. 단일 try/except가 전체 loop를 감싸는 패턴 금지(CLAUDE.md anti-pattern C).
- **AC-5.2**: 본문 헤더에 "소스 N개 중 M개 정상 수집, X개 실패: {이름}" 표기. 실패가 없으면 "소스 N개 정상 수집" 표기.
- **AC-5.3**: Claude API quota·hard cap 초과 시 RuntimeError → `main()`이 잡아서 운영자(`OPS_ALERT_RECIPIENTS` 환경변수에서 명시) alert 메일 발송 후 종료. 직원 메일은 발송하지 않음.
- **AC-5.4**: SMTP 발송 실패 시 동일 운영자 alert. retry 1회만(같은 cron 안에서). 두 번째 실패 시 종료.
- **AC-5.5**: Hard cap: 일일 입력 토큰 ≤ 100,000, 일일 출력 토큰 ≤ 20,000, 일일 API 호출 횟수 ≤ 30. 어느 하나라도 초과 시 즉시 RuntimeError.

### AC-6. 수신자 관리

- **AC-6.1**: 수신자는 `config/recipients.yml` 로딩(별도 시크릿 관리). 형식 §6-3.
- **AC-6.2**: 수신자는 BCC로 발송 — `To: {GMAIL_FROM}` (봇 자신), `Bcc: {수신자 명단}`. `Reply-To: {OPS_REPLY_TO}` 환경변수.
- **AC-6.3**: `config/recipients.yml`에 `suppress: true` 표기된 항목은 발송 제외 (휴가·임시 정지용).
- **AC-6.4**: V1 발송 시작일 수신자 범위를 단계적으로 확장한다(2026-05-19 사용자 결정):
  - Day 0 ~ Day 6 (D+1주차): 운영자 1명만. `recipients.yml`에 운영자만 활성(다른 수신자는 `suppress: true`).
  - Day 7 ~ Day 13 (D+2주차): 김종만 총괄대표·정은주 이사·장석중 이사 3명 추가 활성.
  - Day 14 이후: 전 직원 활성.
  - 일정 변경은 운영자 재량(이사진 검토 결과에 따라 단축·연장 가능).
- **AC-6.5**: V1 발송자 주소 `GMAIL_FROM = nterrr@gmail.com` (운영자 본인 Gmail, 2026-05-19 결정). Workspace 전용 봇 계정(예: `trendbot@farmboss.kr`)은 V1.5 이후 검토 — ADR-001 §결과 보충 참조.

### AC-7. 운영체제 정합성

- **AC-7.1**: 모든 시크릿(API 키·SMTP 비밀번호·운영자 이메일 명단)은 GitHub Actions Secrets 또는 `.env`(로컬). `.gitignore`가 `.env`·`config/recipients.yml`·`secrets.*` 차단.
- **AC-7.2**: 로그에 시크릿 dict 통째 노출 금지. API 키는 prefix 6자리만 로그.
- **AC-7.3**: `run_daily.py`의 `main()` 본문에 도메인 규칙 누적 금지 — 5단계 호출(config→fetch→filter→summarize→dispatch→history.record)과 부분 실패 보고만 (CLAUDE.md anti-pattern B).
- **AC-7.4**: `lib/url_helper.canonicalize` 와 `lib/time_helper`는 dedup·render·dispatcher·history 모두 동일 호출. dispatcher 안에서 URL 잘라쓰기 같은 자체 정규화 금지 (CLAUDE.md anti-pattern A).

## 5. Resource flow loop

이 도메인은 게임·시뮬레이션이 아니라 자원 loop 표가 직접 적용되지 않는다. 대신 **다이제스트 1회 생성 사이클**의 input→process→output을 표로 정리한다.

| 자원 | input | process | output |
|---|---|---|---|
| Raw articles | RSS·HTML·JSON API 소스 12~18개 | fetchers/{rss,html,json_api}.py — 소스 단위 격리 try/except | `list[Article]` + `list[Failure]` |
| Filtered articles | Raw articles + history(`sent.jsonl`) + filters.yml | filters/{timewindow,keyword,category,dedup}.py — 시간윈도우(최근 36h) → 키워드/카테고리 매핑 → dedup | `dict[Category, list[Article]]` |
| Digest body | Filtered articles + summarize.md prompt | summarizer/client.py — Claude API 단일 호출(점수+요약), Prompt caching | `Digest` (카테고리별 항목·메타 포함) |
| Sent record | Digest의 모든 canonical URL | history/store.py — append to `sent.jsonl` + artifact 업로드 | 다음 실행의 dedup 입력 |
| Email | Digest (HTML + text) + recipients.yml | dispatchers/email_gmail.py — Gmail SMTP, BCC | 수신자 메일함 도착 |
| Operator alert (조건부) | 실패 이벤트 (quota·SMTP·dispatcher) | summarizer/dispatcher의 RuntimeError를 main()이 catch | 운영자 메일 (OPS_ALERT_RECIPIENTS) |

각 행에 미정 셀(`???`) 없음 — 본 requirements를 `applied` 또는 `frozen`으로 전환 가능.

## 6. Data Contract

### 6-1. `config/sources.yml` (정적 — 저장 제외, git tracked)

```yaml
# config/sources.yml
sources:
  - id: anthropic_blog              # 식별 키 — 영문 snake_case
    name: "Anthropic Blog"          # 본문 출처명에 노출되는 표시 이름
    url: "https://www.anthropic.com/news/rss.xml"
    type: rss                       # rss | html | json_api
    category: ai_trend              # ai_trend | agri_distribution | farmboss_keyword
    enabled: true
    tags: ["ai", "model_release"]
    time_window_hours: 36           # optional, default 36
  - id: nongmin_news
    name: "농민신문"
    url: "https://www.nongmin.com/rss/all.xml"
    type: rss
    category: agri_distribution
    enabled: true
    tags: ["agri"]
```

식별 키(`id`) 네이밍: `^[a-z][a-z0-9_]*$`. 변경 시 sent.jsonl의 history `source_id` 매칭이 깨지므로 한 번 정해진 id는 deprecated 처리 시에도 재사용 금지.

### 6-2. `config/filters.yml` (정적)

```yaml
# config/filters.yml
categories:
  ai_trend:
    label: "AI 트렌드"
    must_match_any: ["AI", "LLM", "Claude", "GPT", "Gemini", "Anthropic", "OpenAI", "Mistral"]
    exclude_any: ["부동산", "암호화폐 가격"]
    order: 1
  agri_distribution:
    label: "농산물·유통"
    must_match_any: ["농산물", "유통", "마트", "GS리테일", "쿠팡", "이마트", "산지", "출하", "공급망"]
    exclude_any: []
    order: 2
  farmboss_keyword:
    label: "팜보스 관심 키워드"
    must_match_any:
      - "정다운"
      - "팜보스"
      - "시경"
      - "닥터상달"
      - "GS리테일"
      - "청도"
      - "경산"
      - "밀양"
      - "복숭아"
      - "감"
      - "딸기"
      - "안동농협공판장"
    exclude_any: []
    order: 3
global:
  time_window_hours: 36
  fuzzy_title_threshold: 0.85
  dedup_days: 7
```

키워드 매칭은 case-insensitive substring. 영어 키워드는 한국어 본문에도 매칭(예: "AI"가 한국어 기사 본문에 포함될 때).

### 6-3. `config/recipients.yml` (시크릿 — `.gitignore` 차단)

```yaml
# config/recipients.yml — git에 커밋 금지
recipients:
  - name: "김종만"
    email: "jongman@example.com"
    role: "총괄대표"
    suppress: false
  - name: "정은주"
    email: "eunjoo@example.com"
    role: "팜보스 이사"
    suppress: false
  - name: "장석중"
    email: "seokjung@example.com"
    role: "정다운 이사"
    suppress: false
ops_alert:
  - name: "운영자"
    email: "ops@example.com"
ops_reply_to: "ops@example.com"
```

`config/recipients.example.yml`을 `.gitignore` 예외(`!config/recipients.example.yml`)로 커밋해 형식만 git에 둔다. 실제 명단은 운영 시점에 로컬 또는 GitHub Actions Secret(`RECIPIENTS_YML_BASE64`)으로 주입.

### 6-4. `history/sent.jsonl` (인스턴스 state — 저장 포함, artifact 영속)

각 줄 1 JSON 객체:

```json
{
  "sent_at_utc": "2026-05-19T22:30:14Z",
  "sent_at_kst": "2026-05-20T07:30:14+09:00",
  "version": 1,
  "items": [
    {
      "canonical_url": "https://www.anthropic.com/news/announcing-claude-opus-4-7",
      "title": "Announcing Claude Opus 4.7",
      "source_id": "anthropic_blog",
      "category": "ai_trend",
      "published_at_kst": "2026-05-19T06:12:00+09:00"
    }
  ],
  "meta": {
    "failed_sources": [{"id": "nongmin_news", "error": "HTTP 503"}],
    "claude_tokens_in": 6800,
    "claude_tokens_out": 2400
  }
}
```

**스키마 버전**: 최상위 `version: 1`. 변경 시 `history/store.py`에 v1→v2 마이그레이션 함수 추가(점진 확장). loader는 알려진 버전만 허용, 그 외는 무시(폭주 방지).

**보존**: artifact 90일 자동 보존. dedup 비교는 최근 7일분만 메모리에 로드(`global.dedup_days` 참조).

### 6-5. `prompts/summarize.md` (정적)

```markdown
당신은 팜보스 그룹(농산물 통합 유통 그룹) 임직원을 위한 매일 뉴스 다이제스트의
큐레이션·요약 어시스턴트입니다.

각 후보 기사에 대해 다음 두 가지를 출력하세요:
1. 중요도 점수 (1~10, 정수). 회사 사업 영역(산지유통·온라인커머스·프랜차이즈)
   또는 AI 산업 전반에 영향이 클수록 높음.
2. 한국어 요약 2 문장 이내. 원문에 명시되지 않은 수치·인과·날짜를 생성하지 마세요.
   숫자·고유명사·날짜는 원문 그대로 인용합니다.

출력 형식: JSON array. 각 원소는
  { "id": "...", "score": N, "summary": "..." }

금지: "why it matters" 같은 코멘트, 추측, 원문 외 정보, 영문 요약, 3문장 이상 요약.
```

JSON 출력 강제 + 후처리(`summarizer/render.py`)에서 schema validation. 위반 시 해당 항목 폐기.

## 7. 운영자 Alert 결정 (brief §5-6 해소)

**별도 메일** 사용 — 다이제스트 본문에 운영 메타를 노출하면 직원이 매일 보게 됨. 분리해서:

- 직원 다이제스트는 깨끗하게 "정상 수집 N건, 실패 X건" 한 줄만.
- 운영자 alert는 별도 메일 — 제목 `[팜보스 트렌드 알림] {datetime KST} {ERROR_KIND}`, 본문에 스택트레이스·실패 소스 상세·다음 cron 예정 시각.
- 수신자: `config/recipients.yml`의 `ops_alert` 섹션.

## 8. 시크릿·환경변수 명세

| 이름 | 매체 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | GitHub Actions Secret | Claude API 인증 |
| `GMAIL_USER` | GitHub Actions Secret | SMTP 로그인 ID |
| `GMAIL_APP_PASSWORD` | GitHub Actions Secret | SMTP 16자리 앱 비밀번호 |
| `GMAIL_FROM` | GitHub Actions Secret 또는 Variable | 발송자 표기 (`팜보스 트렌드봇 <ops@example.com>`) |
| `RECIPIENTS_YML_BASE64` | GitHub Actions Secret | `config/recipients.yml` 내용 base64 인코딩 |
| `OPS_REPLY_TO` | GitHub Actions Variable | `Reply-To` 헤더 |
| `CLAUDE_MODEL_ID` | GitHub Actions Variable | 사용 모델 ID. 기본값 `claude-haiku-4-5-20251001`. deprecated 시 코드 변경 없이 교체. (2026-05-19 추가) |

`.env.example`를 git에 커밋해 위 변수 목록을 명시. `.env`는 차단.

## 9. 완료 조건 (이 requirements를 frozen으로 전환할 조건)

- [ ] AC-1 ~ AC-7 모두 측정 가능 형태
- [ ] §6 data contract의 5개 파일 스키마 모두 명시
- [ ] §3 리서치 시사점이 tech-research.md 결론과 1:1 매칭
- [ ] §7 운영자 alert 결정 완료
- [ ] ADR-002 (저장 매체) accepted 상태로 전환
- [ ] Stage 5 phase 계획 입력으로 사용 가능

위 6항을 모두 만족하면 Stage 5에서 `/plan-phase` 결과에 의해 status `frozen` 전환.

---

## Changelog

- 2026-05-19: 초안 작성. Tech 결론 5개 인용, 운영자 alert 별도 메일로 결정, 7개 acceptance criteria 카테고리, 5개 data contract 스키마.
- 2026-05-19: design-review 자가 교차 검토 결과 3개 항목 반영 — AC-1.5 추가(한국 공휴일 V1 범위 외), AC-4.3 보강(fuzzy threshold 조정 가능성), §8에 `CLAUDE_MODEL_ID` 환경변수 추가.
- 2026-05-19: 사용자 일괄 검토 4라운드 결정 반영:
  - AC-1.1 cron `30 22 * * 0-4` → `30 22 * * *` (매일 발송, 토·일·공휴일 포함)
  - AC-1.4 "토·일·공휴일 미발송" → "매일 발송"으로 변경
  - AC-1.5 "한국 공휴일 V1 범위 외 (V2 검토)" → "V1·V2 모두 자동 스킵 미적용"으로 명확화
  - AC-1.6 메일 제목 형식 명시 추가 (`[팜보스 트렌드] M/D(요일) AI·농산물 유통 오늘의 뉴스 N건`)
  - AC-2.6 풋터 의견 회신 안내 추가
  - AC-2.7 헤더 이모지·카테고리 번호 톤 확정 (📰 + ①②③)
  - AC-6.4 수신자 단계적 공개 (운영자 1주 → 3이사 1주 → 전 직원)
  - AC-6.5 V1 발송자 주소 = 운영자 본인 Gmail
  - §2 범위 외에 외부 뉴스레터 권고 안 함 + V1 차별화 가치 명시
