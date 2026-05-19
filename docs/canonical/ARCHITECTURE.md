# f_trendnewsbot Architecture

> 역할: 현재 시스템 구조·모듈 ownership·데이터 흐름의 단일 권위 정의. 코드 위치를 좁힐 때 출발점.
> 대상: 새 모듈 추가 시, 의존 관계 추적 시, 새 합류자 온보딩 시.

작성일: 2026-05-19
상태: applied — phase 01 step1~7 + phase 02 step1~4 구현 완료 후 실측 반영 (step8 canonical sync, 2026-05-19).

---

## 런타임

- 언어: Python 3.12
- 런타임: Python 3.12 + GitHub Actions
- 타깃: GitHub Actions cron + 텔레그램 Bot API + GitHub Pages (ADR-003, 2026-05-19 — ADR-001의 Gmail SMTP supersede)
- 시간대: KST (Asia/Seoul). cron 식만 UTC.

## 폴더 구조 (실측 — 2026-05-19 phase 01 step8)

```
f_trendnewsbot/
├── CLAUDE.md                          # 작업 규칙·CRITICAL·anti-pattern
├── README.md
├── pyproject.toml                     # google-genai>=0.3.0, ruff, mypy, pytest (ADR-005)
├── .env.example                       # GEMINI_API_KEY, TELEGRAM_BOT_TOKEN 등 안내
├── .gitignore                         # .claude/settings.local.json, secrets, history/
├── .github/workflows/daily.yml        # cron: 매일 KST 07:30 (= UTC 22:30 전일) + workflow_dispatch
├── src/
│   ├── run_daily.py                   # 통합 진입 지점 (5단계 호출 위임만, ~200 lines)
│   ├── config/                        # sources.yml / filters.yml 로더 (recipients.yml 폐기, ADR-003)
│   ├── fetchers/                      # base + rss + html + json_api (소스 단위 try/except 격리)
│   ├── filters/                       # timewindow + keyword + category + dedup + pipeline
│   ├── history/                       # store.py — GitHub Actions artifact 다운/업로드
│   ├── summarizer/
│   │   ├── client.py                  # google-genai SDK + JSON mode + ThinkingConfig(0) (ADR-005)
│   │   ├── quota.py                   # QuotaExceededError 라벨 + 일일 hard cap
│   │   └── render.py                  # Apple v3 HTML + 텔레그램 인덱스 텍스트 빌드
│   ├── dispatchers/
│   │   ├── base.py                    # Dispatcher Protocol + SendResult + 예외 (ADR-003)
│   │   ├── pages_publish.py           # gh-pages 브랜치 commit·push (사내 docs 노출 차단)
│   │   ├── telegram_send.py           # Bot API sendMessage + final URL 풋터 단일 책임
│   │   └── ops_alert.py               # 운영자 alert chat
│   └── lib/
│       ├── url_helper.py              # canonicalize() — dedup·발송 공유 정규화
│       ├── time_helper.py             # KST 변환·표기
│       └── logging_setup.py
├── config/
│   ├── sources.yml                    # 소스 목록 (14개, 이름·url·type·tags·category)
│   └── filters.yml                    # 키워드·블랙리스트·카테고리 매핑
├── prompts/summarize.md               # 카테고리별 요약 프롬프트 (회사 컨텍스트 포함)
├── samples/                           # 디자인 mockup·발송 본문 sample (개발 참조용)
├── templates/                         # Apple v3 HTML template 자산
├── tests/                             # 100 unit tests (config·fetchers·filters·history·summarizer·dispatchers·time·url·logging)
├── scripts/
│   ├── render_sample_v4.py            # render.build_digest 시각 점검
│   ├── validate_agent_profiles.ps1    # .claude/agents/tnb-* drift 검증
│   └── validate_doc_status.ps1        # docs 상태·phase frozen 검증
├── docs/                              # canonical + features + ops + history + 회사 도메인 문서
└── phases/
    ├── index.json                     # phase 라우팅 source of truth
    ├── 01-mvp-daily-digest/           # step1~8 + README + final-report
    ├── 02-gemini-swap/                # step1~4 + final-report (5건 hotfix 회고 포함)
    └── _hotfix-log/                   # phase 외 1~2 파일 핫픽스 로그
```

## 통합 진입 지점

- 진입 파일: `src/run_daily.py`
- 진입 함수: `main()` — fetcher → filter → summarizer → dispatcher 순서로 위임만. 본문에 도메인 규칙을 누적하지 않는다(CRITICAL: 통합 지점 비대화).

진입 함수의 책임은 다음 5단계 호출과 부분 실패 보고로 한정한다.

```
1. config 로드 + 시크릿 검증
2. fetchers.run_all(sources)          → articles, fetch_failures
3. filters.apply(articles, filters)   → kept_articles
4. summarizer.build(kept, prompts)    → digest (카테고리별 + 메타)
5. dispatcher.send(digest, recipients) → send_result
6. history.record(sent_urls)
```

## 모듈 ownership

| 모듈 | 위치 | 책임 | 의존 |
|---|---|---|---|
| Fetcher | `src/fetchers/` (base + rss + html + json_api + runner) | 소스별 raw article 가져오기. 소스 단위 try/except 격리 + fetch_failures 보고. | `lib/url_helper`, `lib/time_helper` |
| Filter | `src/filters/` (timewindow + keyword + category + dedup + pipeline) | 시간 윈도우·키워드·카테고리·dedup으로 후보 축소 | `history.store`, `lib/url_helper` |
| Summarizer | `src/summarizer/` (client + quota + render) | Gemini API 호출 (ADR-005, gemini-2.5-flash, thinking_budget=0). 카테고리별 점수·요약·company_impact·category_headlines·TL;DR 분석. Apple v3 HTML + 텔레그램 인덱스 렌더. | google-genai SDK, `prompts/summarize.md` |
| Dispatcher | `src/dispatchers/` (base + pages_publish + telegram_send + ops_alert) | 채널별 발송. V1: gh-pages 브랜치 publish + 텔레그램 Bot API sendMessage + 운영자 alert chat (ADR-003). final URL 풋터 단일 책임. | `summarizer.render` 결과 |
| History | `src/history/store.py` | 발송 이력 영속화·조회 (sent.jsonl, GitHub Actions artifact, ADR-002) | artifact API |
| Lib | `src/lib/` (url_helper + time_helper + logging_setup) | URL canonicalize·KST 변환·로그 setup 의 single source (CRITICAL: 표시·규칙 공유) | 표준 라이브러리 |
| Config | `config/` (sources.yml + filters.yml) | 소스·필터 정의 (코드 변경 없이 운영 변경 가능). recipients.yml 폐기 (ADR-003 — 텔레그램 단톡방 멤버십이 수신자) | — |
| Run entry | `src/run_daily.py` | 5단계 호출 위임 + 환경변수 검증 + ConfigError·QuotaExceededError 분기 + ops_alert 라우팅. 본문 ~200 lines (anti-pattern B 회피) | 위 모든 모듈 |

## 데이터 흐름

```
[RSS·HTML·API 소스 14개]
        │ fetchers.run_all (소스 단위 try/except 격리)
        ▼
   raw_articles[]  ─→ fetch_failures[(name, reason)]
        │ filters.pipeline.apply: timewindow → keyword → category → dedup
        ▼
   kept_articles  (카테고리별 dict)
        │ summarizer.client.summarize  (Gemini 2.5 Flash, JSON mode, ADR-005)
        ▼
   SummarizeResult { items + category_headlines + tokens_in/out }
        │ summarizer.render.build_digest (Apple v3 HTML + 텔레그램 인덱스)
        ▼
   RenderedDigest { html + telegram_text + subject + meta }
        │ dispatchers.pages_publish.publish (gh-pages 브랜치 commit·push, AC-5.6)
        ▼
   final pages_url = https://{owner}.github.io/f_trendnewsbot/digest/{date}.html
        │ dispatchers.telegram_send.send (Bot API + 풋터 "전체 본문: {final_url}" 단일 책임)
        ▼
   [텔레그램 단톡방 - 운영자 또는 직원]
        │ history.store.record (sent.jsonl artifact 업로드)
        ▼
   [발송 이력 (다음날 dedup 입력)]
```

장애 경로: `QuotaExceededError` / `PagesPublishError` / `TelegramSendError` / `ConfigError` 모두 `dispatchers.ops_alert.send` 로 라우팅 → 운영자 alert chat 만 발송 + sys.exit(2).

## 저장 계약

- **정적 데이터(저장 제외)**: 코드·`config/*.yml`·`prompts/*.md`. git이 source of truth.
- **인스턴스 state(영속화 필요)**:
  - **발송 이력** (`history/store.py` 책임): URL canonical + 제목 + 발송일. 최근 30일 보존, 7일까지 dedup 비교.
    - 저장 매체 후보(ADR-002에서 결정 예정): ① GitHub Actions artifact + 매일 download/upload, ② repo 내 `history/sent.jsonl`을 봇이 PR 없이 직접 push, ③ GitHub Issue 본문에 누적.
  - **운영 로그**: GitHub Actions 런 로그(자동 보존 90일). 별도 영속 안 함.
- **마이그레이션 정책**: 이력 스키마 변경 시 `history/store.py`에 버전 필드 + 로더가 구버전 호환 fallback 유지(점진 확장 원칙).

## 성능 기준선 (실측 — phase 01 step8 dry-run 6회차, run 26099906586, 2026-05-19 22:22 KST)

- 전체 실행 시간: **1m30s** (소스 14개 fetch + Gemini 호출 + Pages publish + 텔레그램 발송 + artifact upload 포함). 예상치 < 3분 대비 50% 여유.
- 발송 건수: **27건** (3 카테고리 × 평균 9건). 카테고리당 5~10건 목표 부합.
- 소스 가용성: 14개 중 7개 정상 / 7개 실패 (Anthropic Blog, 농민신문, aT KAMIS, GS리테일 IR, 농민신문 농촌경제, 청도군 보도, 안동농협공판장). 실패 격리 정상 작동 — 발송 전체 지장 없음. 1주 모니터링 후 소스 보강 필요.
- Gemini API: 1회 cron 당 1회 호출. `max_output_tokens=8192`, `thinking_budget=0` (ADR-005 후속 hotfix). 토큰 사용 상세는 sent.jsonl artifact 의 tokens_in/out 필드.
- 월 비용: $0 (Gemini 2.5 Flash 무료 tier, ADR-005). 무료 한도 15 RPM / 1500 RPD 의 1% 미만 사용.
- GitHub Actions 분: 일 ~1.5분 × 30일 = 월 ~45분 (무료 한도 2000분 대비 2.25% 사용).
- Pages publish: gh-pages 브랜치 fast-forward commit, master `/docs` root 노출 회피 (Hotfix `2026-05-19-pages-gh-branch-boundary.md`).

4주 모니터링 항목: cron 정시성 분포, Gemini 응답 시간 변동, dedup fuzzy threshold 실측, 소스 7개 실패 원인 (RSS 변경 / 차단 / 일시 장애 구분).

## 회사 도메인 문서

OS와 별개로, 팜보스 회사 자체 문서가 같은 저장소에 공존한다. 봇 코드가 회사 문맥을 이해할 때 참조한다.

- `docs/팜보스_회사소개.md` — 3법인 구조·핵심 인물·주요 산지(필터 키워드 결정에 직결)
- `docs/_extracted/` — 직원 업무 가이드 텍스트 사본
- `docs/f-공통직원업무매뉴얼/` — 원본 .docx 모음

---

## Changelog

- 2026-05-19: 초안 작성. V1 폴더 구조·모듈 ownership·데이터 흐름 정의. 발송 이력 저장 매체는 ADR-002에서 결정 예정.
- 2026-05-19: V1 발송 채널 변경 (ADR-003 accepted) — §런타임 항목에 텔레그램 Bot API + GitHub Pages 명시. 폴더 구조·모듈 ownership·데이터 흐름의 dispatcher 부분은 phase 01 구현·step8 canonical sync에서 코드 기반으로 일괄 갱신.
- 2026-05-19: UX 강화 — summarizer 모듈이 회사 컨텍스트 system prompt + 점수·요약·회사 영향·카테고리 핵심을 단일 호출로 출력하는 schema로 갱신 (requirements §6-5). render 모듈은 애플 감성 v3 HTML template 1종 동결 (디자인 자산 `src/summarizer/templates/digest.html.j2` 예정). 코드 기반 모듈 ownership 표 갱신은 phase 01 구현 후 step8에서.
- 2026-05-19: phase 01 step8 canonical sync 적용 — 폴더 구조·모듈 ownership·데이터 흐름·성능 기준선 모두 실측 반영. status `draft` → `applied`. LLM provider 표기 ADR-004 (gemini-2.0-flash) → ADR-005 (gemini-2.5-flash + thinking_budget=0). gh-pages 브랜치 publish + 텔레그램 풋터 단일 책임 + 5단계 호출 위임 패턴 모두 코드 기준으로 명시.
