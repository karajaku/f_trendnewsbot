# f_trendnewsbot Architecture

> 역할: 현재 시스템 구조·모듈 ownership·데이터 흐름의 단일 권위 정의. 코드 위치를 좁힐 때 출발점.
> 대상: 새 모듈 추가 시, 의존 관계 추적 시, 새 합류자 온보딩 시.

작성일: 2026-05-19
상태: draft — 구현 시작 전 설계 골격. 실제 코드 합류 시 모듈 ownership 표 갱신.

---

## 런타임

- 언어: Python 3.12
- 런타임: Python 3.12 + GitHub Actions
- 타깃: GitHub Actions cron + 텔레그램 Bot API + GitHub Pages (ADR-003, 2026-05-19 — ADR-001의 Gmail SMTP supersede)
- 시간대: KST (Asia/Seoul). cron 식만 UTC.

## 폴더 구조 (예정)

```
f_trendnewsbot/
├── CLAUDE.md                          # 작업 규칙·CRITICAL·anti-pattern
├── README.md                          # (이식 직후 템플릿 README — 추후 도메인 README로 교체)
├── pyproject.toml                     # 의존성·툴체인 설정
├── .github/
│   └── workflows/
│       └── daily.yml                  # cron: 매일 KST 07:30 (= UTC 22:30 전일)
├── src/
│   ├── run_daily.py                   # 통합 진입 지점. 위임만.
│   ├── fetchers/
│   │   ├── base.py                    # Fetcher 인터페이스
│   │   ├── rss.py                     # feedparser 기반
│   │   ├── html.py                    # requests + BeautifulSoup 기반
│   │   └── json_api.py                # 일반 JSON API 어댑터
│   ├── filters/
│   │   ├── dedup.py                   # URL 정규화 + 제목 fuzzy match
│   │   ├── keyword.py                 # config/filters.yml 기반 포함/제외
│   │   └── timewindow.py              # 최근 24~36시간 기사만
│   ├── summarizer/
│   │   ├── client.py                  # Anthropic SDK wrapper, prompt caching
│   │   ├── scoring.py                 # 중요도 점수 (카테고리별)
│   │   └── render.py                  # 다이제스트 본문 빌더 (HTML + text)
│   ├── dispatchers/
│   │   ├── base.py                    # Dispatcher 인터페이스: send(digest, recipients)
│   │   └── email_gmail.py             # Gmail SMTP
│   ├── history/
│   │   └── store.py                   # 발송 이력 영속화 (artifact 또는 repo file)
│   └── lib/
│       ├── url_helper.py              # canonicalize() — dedup·발송 공유
│       ├── time_helper.py             # KST 변환·표기
│       └── logging_setup.py
├── config/
│   ├── sources.yml                    # 소스 목록 (이름·url·type·tags·category)
│   ├── filters.yml                    # 키워드·블랙리스트·카테고리 매핑
│   └── recipients.yml                 # 수신자 이메일 (이름·email·suppress flag)
├── prompts/
│   ├── summarize.md                   # 카테고리별 요약 프롬프트
│   └── score.md                       # 중요도 점수 프롬프트
├── tests/
│   ├── fixtures/                      # 샘플 RSS·HTML·API 응답
│   ├── test_dedup.py
│   ├── test_filters.py
│   └── test_render.py
├── docs/                              # (canonical OS + 회사 문서 — 별도 섹션)
├── phases/                            # 구현 phase 추적
└── scripts/                           # 검증 스크립트
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
| Fetcher | `src/fetchers/` | 소스별 raw article 가져오기. 소스 단위 try/except로 격리. | `lib/url_helper`, `lib/time_helper` |
| Filter | `src/filters/` | 시간 윈도우·키워드·dedup으로 후보 축소 | `history.store`, `lib/url_helper` |
| Summarizer | `src/summarizer/` | Claude API 호출, 카테고리별 점수·요약·다이제스트 렌더 | Anthropic SDK, `prompts/` |
| Dispatcher | `src/dispatchers/` | 채널별 발송. V1은 Gmail SMTP만. 인터페이스 `send(digest, recipients)`. | `summarizer.render` 결과 |
| History | `src/history/` | 발송 이력 영속화·조회 (dedup의 신뢰원) | 저장 매체 (file/artifact/Issue) |
| Lib | `src/lib/` | URL·시간·로그 helper. 표시·규칙 공유의 single source. | 표준 라이브러리 |
| Config | `config/` | 소스·필터·수신자 정의 (코드 변경 없이 운영 변경 가능) | — |

## 데이터 흐름

```
[RSS·HTML·API 소스]
        │ fetchers (소스 단위 격리)
        ▼
   raw_articles[]  ─→ fetch_failures[]
        │ filters: timewindow → keyword → dedup
        ▼
   kept_articles[]
        │ summarizer (Claude API: 점수 + 한 줄 요약)
        ▼
   digest{ AI: [...], 농산물유통: [...], 팜보스관심: [...], meta: { failures, generated_at_kst } }
        │ dispatcher.send (Gmail SMTP)
        ▼
   [수신자 메일함]
        │ history.record(sent_urls, sent_at)
        ▼
   [발송 이력 (다음날 dedup 입력)]
```

## 저장 계약

- **정적 데이터(저장 제외)**: 코드·`config/*.yml`·`prompts/*.md`. git이 source of truth.
- **인스턴스 state(영속화 필요)**:
  - **발송 이력** (`history/store.py` 책임): URL canonical + 제목 + 발송일. 최근 30일 보존, 7일까지 dedup 비교.
    - 저장 매체 후보(ADR-002에서 결정 예정): ① GitHub Actions artifact + 매일 download/upload, ② repo 내 `history/sent.jsonl`을 봇이 PR 없이 직접 push, ③ GitHub Issue 본문에 누적.
  - **운영 로그**: GitHub Actions 런 로그(자동 보존 90일). 별도 영속 안 함.
- **마이그레이션 정책**: 이력 스키마 변경 시 `history/store.py`에 버전 필드 + 로더가 구버전 호환 fallback 유지(점진 확장 원칙).

## 성능 기준선 (예상값 — V1 가동 후 갱신)

- 전체 실행 시간: < 3분 (소스 fetch 병렬화 + Claude API 일괄 호출 기준)
- Claude API 호출: 일 1회 cron당 총 토큰 < 50k (입력) + < 10k (출력)
- 월 비용: < $20 (Haiku 4.5 기준)
- GitHub Actions 분: 일 ~3분 × 22 영업일 = 월 ~66분 (무료 한도 2000분 대비 충분)

## 회사 도메인 문서

OS와 별개로, 팜보스 회사 자체 문서가 같은 저장소에 공존한다. 봇 코드가 회사 문맥을 이해할 때 참조한다.

- `docs/팜보스_회사소개.md` — 3법인 구조·핵심 인물·주요 산지(필터 키워드 결정에 직결)
- `docs/_extracted/` — 직원 업무 가이드 텍스트 사본
- `docs/f-공통직원업무매뉴얼/` — 원본 .docx 모음

---

## Changelog

- 2026-05-19: 초안 작성. V1 폴더 구조·모듈 ownership·데이터 흐름 정의. 발송 이력 저장 매체는 ADR-002에서 결정 예정.
- 2026-05-19: V1 발송 채널 변경 (ADR-003 accepted) — §런타임 항목에 텔레그램 Bot API + GitHub Pages 명시. 폴더 구조·모듈 ownership·데이터 흐름의 dispatcher 부분은 phase 01 구현·step8 canonical sync에서 코드 기반으로 일괄 갱신.
