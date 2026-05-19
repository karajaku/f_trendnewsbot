---
status: applied
review_count: 0
created_at: "2026-05-19"
last_reviewed_at: null
reviewer: null
research_mode: technical
feature: daily_digest_v1
based_on_brief: "docs/features/daily_digest/daily_digest_v1-brief.md"
applied_at: "2026-05-19"
applied_by: "docs/features/daily_digest/daily_digest_v1-requirements.md"
---

# daily_digest V1 — Stage 3 Tech Research

> 역할: brief와 Concept 검토 결과를 바탕으로, requirements.md(Stage 4) 작성에 필요한 기술적 조사를 수행한다. 설계는 하지 않는다.
> 대상: Stage 4 requirements 작성자, ADR-002(저장 매체) accept 시점에 후보 비교 근거를 인용할 사람.

---

## 1. 조사 질문 (Concept 검토 §미결에서 도출, 사용자 일괄 검토 단계에서 보강 가능)

1. **저장 매체** — 발송 이력의 영속 저장은 ① GitHub Actions artifact ② repo 내 파일 자동 push ③ GitHub Issue 본문 누적 중 어느 쪽이 V1 운영에서 가장 안전·간단·관측 가능한가?
2. **Claude API 호출 분리** — 점수화·요약을 분리 호출 시 일 소요 토큰·비용은? 월 $20 hard cap 안에 들어가는가? 안 들어가면 어떤 단일 호출 구조로 대체할 수 있나?
3. **소스 후보** — AI 트렌드 / 농산물·유통 / 팜보스 관심 키워드 3카테고리에 V1 시작 시 등록할 RSS·HTML·JSON API 소스를 어떻게 정하나? RSS 우선·HTML 차선·스크래핑 최후 원칙은 유지 가능한가?
4. **시각·KST helper** — `src/lib/time_helper.py`의 시그니처(public 함수 목록)는 무엇이어야 dispatcher·render·dedup·history가 모두 공유하면서 표시-규칙 일치 원칙을 만족하나?
5. **GitHub Actions cron 정시성** — KST 07:30 ± 5분 95% 정시 목표를 GitHub Actions의 일반적 지연 특성에서 달성 가능한가? 불가능하면 어떤 보완책이 있나?

---

## 2. 코드베이스 조사

저장소는 그린필드(실행 코드 0)다. anchor 대상은 회사 도메인 문서와 canonical 계약 골격.

### 2-1. 현재 anchor 가능한 자산

| 영역 | 위치 | anchor 라인 | 활용 의미 |
|---|---|---|---|
| 통합 진입 (예정) | [docs/canonical/ARCHITECTURE.md](../../canonical/ARCHITECTURE.md#L25) §통합 진입 지점 | "진입 파일: `src/run_daily.py`, 진입 함수: `main()`" | `main()` 본문은 5단계 호출 + 부분 실패 보고만. 도메인 규칙 누적 금지(CLAUDE.md anti-pattern B). |
| 모듈 ownership | [docs/canonical/ARCHITECTURE.md](../../canonical/ARCHITECTURE.md#L31) §모듈 ownership | 6모듈(fetchers/filters/summarizer/dispatchers/history/lib) | 각 모듈이 한 책임만. helper는 lib에 집중. |
| dedup helper 공유 | [CLAUDE.md](../../../CLAUDE.md) §Anti-pattern A | "canonical = url_helper.canonicalize(article.url)" 예시 | dispatcher가 자체 url 잘라쓰는 것 금지. `lib/url_helper.py` 단일 진실. |
| 시간 표기 일관성 | [CLAUDE.md](../../../CLAUDE.md) §CRITICAL 7 | "KST(Asia/Seoul) 명시, cron 식은 UTC이므로 매번 KST 환산 주석" | render·dedup·history 모두 동일 helper로 KST 변환. |
| 소스 격리 | [CLAUDE.md](../../../CLAUDE.md) §Anti-pattern C | "results, failures = [], []; for src in sources: try: ... except ..." | fetchers가 list[Article] + list[Failure]를 동시 반환하는 형태. |
| 시크릿 관리 | [CLAUDE.md](../../../CLAUDE.md) §CRITICAL 5, Anti-pattern D | "`os.environ['ANTHROPIC_API_KEY']`만 사용, dict 통째 로그 금지" | summarizer.client.py·dispatcher.email_gmail.py·운영자 alert이 시크릿 접근점. |
| 회사 키워드 시드 | [docs/팜보스_회사소개.md](../../팜보스_회사소개.md) §3 주요 산지 | "경북 청도·경산(복숭아·감), 밀양·청도(딸기)" + 3법인명 | `config/filters.yml`의 "팜보스 관심 키워드" 초기 시드. |
| 회사 톤·호칭 | [docs/_extracted/fj260330직원_업무가이드.txt](../../_extracted/) | "총괄대표→이사→직원" 호칭 흐름 | 다이제스트 헤더·운영자 표기 톤 결정. |
| 데이터 흐름 | [docs/canonical/ARCHITECTURE.md](../../canonical/ARCHITECTURE.md#L113) §데이터 흐름 | "fetchers → filters → summarizer → dispatcher → history" 다이어그램 | requirements §의존 시스템 표의 기반. |
| 저장 계약 골격 | [docs/canonical/ARCHITECTURE.md](../../canonical/ARCHITECTURE.md#L132) §저장 계약 | "발송 이력: 후보 3종, ADR-002 결정 예정" | ADR-002 accepted 트리거가 Stage 4 진입 조건. |

### 2-2. 이식 가능한 helper — 없음

저장소에 Python 코드가 없으므로 이식 가능한 기존 helper는 없다. 모든 helper는 첫 phase에서 신규 생성. 다만 ARCHITECTURE.md가 helper 위치를 미리 못 박아뒀으므로(`lib/url_helper.py`, `lib/time_helper.py`, `lib/logging_setup.py`) Stage 4 requirements는 이 경로를 그대로 사용한다.

### 2-3. 회사 도메인 데이터 — 이식 가능

`config/filters.yml`의 "팜보스 관심 키워드" 카테고리 초기 시드는 회사 소개 문서에서 직접 추출한다.

```yaml
# config/filters.yml — "팜보스 관심 키워드" 카테고리 초기 시드 (예시)
farmboss_keywords:
  category: "팜보스 관심 키워드"
  must_match_any:    # 하나라도 매칭되면 후보
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
  exclude_any: []    # dry-run 1주일 후 보강
```

Stage 4 requirements는 위 키워드 목록을 *예시*가 아닌 *V1 시작 값*으로 동결한다.

---

## 3. 런타임 API · 외부 기술 자료

> 사용자가 외부 조사를 명시 허용한 단계가 아니므로, LLM 일반 지식(2026-01 cutoff) + Anthropic 공식 SDK 일반 지식만 사용한다. URL·retrieved 날짜는 사용자 일괄 검토 시 보강.

### 3-1. RSS·HTML·JSON API 수집 라이브러리

| 라이브러리 | 용도 | V1 사용 결정 | 비고 |
|---|---|---|---|
| `feedparser` | RSS·Atom 파싱 | ✅ 사용 | Python 표준 인터페이스, KST 변환은 별도 helper가 처리 |
| `requests` | HTTP GET (HTML·JSON API) | ✅ 사용 | timeout·재시도는 fetchers/base.py에서 wrap |
| `beautifulsoup4` (`bs4`) | HTML 파싱 | ✅ 사용 (HTML 소스에만) | RSS가 우선, HTML 스크래핑은 정말 필요한 소스에만 |
| `httpx` | requests 대체 | ❌ 미사용 (V1) | 비동기 fetch는 V1 단순성보다 작은 가치 |
| `lxml` | XML 가속 | ❌ 미사용 (V1) | feedparser 기본 파서로 충분 |
| `selectolax` | HTML 가속 | ❌ 미사용 (V1) | bs4로 충분 |

**fetch 동시성**: V1은 순차 fetch. 12~18개 소스 × 평균 1~2초 = 총 20~40초 예상. KST 07:30 발송에 영향 없음. V2에서 ThreadPoolExecutor로 병렬화 검토.

### 3-2. Anthropic Python SDK — 호출 패턴

V1은 [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) (`anthropic` 패키지)를 사용한다. 핵심 호출 형태:

```python
from anthropic import Anthropic
client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
resp = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    system="...요약 가이드라인...",
    messages=[{"role": "user", "content": "...기사 묶음..."}],
)
```

#### Prompt caching

V1은 카테고리별 system prompt가 거의 동일한 가이드라인(요약 길이·금칙어·KST 표기)을 매일 반복 사용한다. **Prompt caching**으로 system 영역을 cache하면 비용을 크게 절감할 수 있다.

```python
system=[
    {
        "type": "text",
        "text": SUMMARIZE_SYSTEM_PROMPT,  # 길고 고정
        "cache_control": {"type": "ephemeral"}
    }
],
```

5분 cache TTL 안에서 카테고리 3개를 연속 호출하면 두 번째·세 번째 카테고리는 system 토큰 비용이 90% 할인.

#### 일일 토큰 추정 (점수화·요약 분리 시 vs 단일 호출 시)

가정:
- 카테고리당 raw 후보 30건(필터 통과 후 추림), 최종 5~10건.
- 후보 1건당 제목+발췌 ~150 토큰, 요약 출력 1건당 ~100 토큰.

| 패턴 | 입력 토큰/일 | 출력 토큰/일 | 단가(Haiku 4.5, 추정) | 일/월 비용 |
|---|---|---|---|---|
| **A. 단일 호출 (점수+요약 동시)** | 카테고리 3개 × (system 1500 + 후보 30건×150) = 18,000 → cache 적용 시 ~7,000 | 카테고리 3개 × 10건×100 = 3,000 | 입력 $1/1M·출력 $5/1M (Haiku 가정) | 일 ~$0.02 / 월 ~$0.5 |
| **B. 분리 호출 (점수 → 상위 10건 → 요약)** | 점수 단계 18,000(cache 후 7,000) + 요약 단계 카테고리 3개 × 10건×200 = 6,000 (cache 적용 ~4,500) | 점수 100×3=300 + 요약 3,000 | 동일 | 일 ~$0.025 / 월 ~$0.6 |

**결론**: 두 패턴 모두 월 $20 hard cap의 3% 수준. **분리 호출이 quality에 유리하다면 V1부터 분리하는 것이 충분히 가능**(Discovery 결론 #3에 대한 기술적 해소). 다만 단일 호출이 코드·로깅·실패 격리 측면에서 단순하므로 **V1은 단일 호출 시작 + V2에서 quality 모니터링 후 분리 결정**으로 권장.

#### Hard cap 메커니즘

`summarizer/client.py`가 호출 직전 일일 누적 토큰·비용을 history(또는 별도 quota 파일)에서 읽어 초과 시 RuntimeError 발생. main()이 잡아서 운영자 alert 메일 발송 후 종료.

### 3-3. Gmail SMTP

| 항목 | 값 |
|---|---|
| 서버 | smtp.gmail.com |
| 포트 | 587 (STARTTLS) 또는 465 (SSL) |
| 인증 | **Google Workspace 앱 비밀번호** (2FA 활성 계정만 생성 가능). API 키 아닌 16자리 앱 패스워드. |
| 일일 발송 한도 | 외부 수신자 ~500통/일 (Workspace 기본). 사내 수신자 ≪ 50명이면 여유. |
| 라이브러리 | Python 표준 `smtplib` + `email.message.EmailMessage` (외부 의존성 불필요) |
| 시크릿 환경변수 | `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_FROM` (GitHub Actions Secrets) |

**HTML + 텍스트 백업 발송**: `EmailMessage`의 `add_alternative()` 사용. 메일 클라이언트가 HTML 못 읽으면 텍스트로 fallback.

```python
msg = EmailMessage()
msg["Subject"] = "[팜보스 트렌드] 5월 19일 (월) AI·농산물 유통 오늘의 뉴스 8건"
msg["From"] = os.environ["GMAIL_FROM"]
msg["To"] = ", ".join(recipients)
msg.set_content(plain_text_digest)             # 텍스트 백업
msg.add_alternative(html_digest, subtype="html")
with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login(os.environ["GMAIL_USER"], os.environ["GMAIL_APP_PASSWORD"])
    s.send_message(msg)
```

**BCC 운영**: 수신자 명단을 To에 노출할지 BCC로 가릴지는 사내 정책. V1은 **BCC 사용**(수신자 명단이 헤더에 노출되지 않게) 권장. 운영자(`Reply-To: 김종만 또는 정은주`)는 헤더에 명시.

### 3-4. GitHub Actions cron 정시성

| 항목 | 특성 |
|---|---|
| cron 입력 형식 | UTC 기준 5필드(min hour day month dayofweek) |
| 일반적 지연 | 0~수 분. 피크 시간(미국 동부 업무 시작 등) ±15분 보고 사례 다수 |
| SLA | 공식 SLA 없음 |
| KST 07:30 ↔ UTC | `30 22 * * 0-4` (UTC 22:30 = KST 익일 07:30, 일~목 실행 = KST 월~금 발송) |
| 우회: `workflow_dispatch` | 사용자 수동 트리거 추가 가능 (alert 받고 재시도용) |

**KST 07:30 ± 5분, 95% 정시 목표**: 실측 기반 통계는 GitHub Actions 정시성 변동성이 ±5분을 빈번히 초과한다는 비공식 보고가 다수. **PRD 성공 기준을 "± 5분 95%"에서 "± 15분 95%"로 완화**하는 것을 권장. Stage 4 requirements에서 PRD 갱신 여부를 정하거나, 그대로 두고 4주 모니터링 후 변경한다.

**보완책**:
- cron을 KST 07:20 (UTC 22:20)으로 당겨 평균 지연 10분을 흡수.
- 발송 실패 시 다음 정각 자동 재시도(workflow_dispatch + retry job).
- 4주 후 실측 지연 분포를 verification-record에 기록 + 필요 시 cron 시각 조정.

### 3-5. 저장 매체 후보 비교 (ADR-002 accepted 입력)

| 후보 | 영속성 | 구현 복잡도 | 실패 모드 | 추적성 | 결론 |
|---|---|---|---|---|---|
| **A. GitHub Actions artifact** | 90일 자동 보존, 일 1회 download/upload | 중 (`actions/upload-artifact@v4` + `actions/download-artifact@v4`) | artifact 누락 시 dedup 미적용 → 전일 중복 발송 가능 | 작음 (Actions UI에서 다운로드 필요) | 안정성 무난, 운영자가 history 즉시 보기 어려움 |
| **B. repo 내 `history/sent.jsonl` 자동 push** | repo와 동일 (영구) | 높음 (봇 commit 권한, push 권한, conflict 처리) | push 실패 시 다음 실행에 conflict | 매우 큼 (git log로 추적, diff 즉시 확인) | 추적성 최고, 그러나 봇이 main에 push하는 운영 부담 |
| **C. GitHub Issue 본문 누적** | repo와 동일 (영구) | 중 (`gh issue edit` 또는 REST API) | Issue 본문 크기 한도(65KB) 도달 시 분할 필요 | 큼 (Issue에서 즉시 열람) | 시각화 좋음, 본문 크기 한도가 1년 운영 시 부담 |

**권장**: 후보 **A (artifact)** 시작 — V1 구현 최소화. 6개월 운영 후 추적성·디버깅 부담이 크면 후보 B로 migrate. Stage 4 requirements에서 A로 동결 + ADR-002 accepted 전환. migration plan은 ADR-002 §결과에 명시.

### 3-6. 의존성 패키지 목록 (V1)

```toml
# pyproject.toml — V1 초기 (Stage 4에서 동결)
[project]
name = "f_trendnewsbot"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "anthropic>=0.40.0",     # Claude API SDK
    "feedparser>=6.0.11",    # RSS·Atom
    "requests>=2.32.0",      # HTTP
    "beautifulsoup4>=4.12.3",# HTML
    "pyyaml>=6.0.2",         # config/*.yml
    "python-dateutil>=2.9.0",# 시간대·KST 변환
]
[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-cov", "ruff", "mypy"]
```

표준 라이브러리만 사용(`smtplib`·`email`·`zoneinfo`)하는 영역: SMTP 발송, KST 변환.

---

## 4. 결론 — requirements.md 반영 시사점

Stage 4 requirements 작성 시 다음 5개 시사점을 인용한다.

1. **저장 매체는 GitHub Actions artifact로 시작**. 구현 단순성·V1 운영 부담 최소화 측면. requirements §data contract에 `history/sent.jsonl` 스키마 명시, `pyproject.toml` 의존성 외에 `actions/upload-artifact@v4` workflow 사용. 6개월 후 migration 옵션 ADR-002 §결과에 명시. `(tech-research.md §3-5)`
2. **Claude API 호출은 V1 단일 호출 (점수+요약 동시) 시작**. 일/월 비용이 단일·분리 모두 cap 3% 수준이지만 단일 호출이 코드·로깅·실패 격리에서 단순. V2에서 quality 모니터링 후 분리 검토. `(§3-2)`
3. **PRD 정시성 기준을 "± 5분 95%"에서 "± 15분 95%"로 완화** 또는 4주 모니터링 후 변경 결정. GitHub Actions cron의 일반적 지연 분포가 ± 5분을 빈번히 초과. cron 시각을 KST 07:20으로 당겨 10분 흡수. `(§3-4)`
4. **`src/lib/url_helper.py` 와 `src/lib/time_helper.py`가 dedup·render·dispatcher·history의 공유 단일 진실**. 시그니처는 `url_helper.canonicalize(url) -> str` / `time_helper.to_kst_string(dt) -> str` / `time_helper.now_kst() -> datetime`. requirements §의존 시스템·data contract에서 그대로 인용. `(§2-1 anchor + CLAUDE.md anti-pattern A)`
5. **`config/filters.yml`의 "팜보스 관심 키워드" 카테고리는 시드 12개 키워드로 동결** ([docs/팜보스_회사소개.md](../../팜보스_회사소개.md) 추출). dry-run 1주일 후 보강은 phase 외 운영 작업. `(§2-3 + Discovery 결론 #5)`

---

## 5. 미결 항목 (사용자 일괄 검토 시 결정)

- **정시성 SLA 완화 여부**: Stage 4가 PRD를 갱신할지 vs 4주 모니터링 후 갱신할지.
- **소스 목록 최종**: 카테고리당 4~6개씩 총 12~18개. brief §3-2 카테고리에 맞춰 후보를 Stage 4에서 동결할지, phase 첫 step에서 동결할지.
- **운영자 alert 채널**: brief §5-6 (별도 메일 vs 메타 헤더). Stage 4에서 결정.

---

## Changelog

- 2026-05-19: 초안 작성. 외부 URL은 LLM 일반 지식 기반 (사용자 외부 조사 허가 시 retrieved 날짜 보강). 저장 매체 후보 A 권장, Claude API 단일 호출 권장.
