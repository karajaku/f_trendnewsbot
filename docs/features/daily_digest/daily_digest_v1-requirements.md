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
| **텔레그램 Bot API** (`api.telegram.org`) | 외부 의존 (ADR-003) | dispatcher가 단톡방에 짧은 인덱스 + Pages URL 발송. BotFather 토큰. |
| **GitHub Pages** (`{owner}.github.io/{repo}`) | 외부 의존 (ADR-003) | dispatcher가 HTML을 `docs/digest/YYYY-MM-DD.html`로 commit·push. public + noindex. |
| GitHub Actions Runner (ubuntu-latest) | 실행 인프라 | cron 트리거. 시크릿 주입 매체. `GITHUB_TOKEN` 으로 Pages publish 권한 자동 부여. |
| GitHub Actions Artifact storage | 영속 저장 (ADR-002) | history 모듈이 sent.jsonl을 업로드·다운로드. 90일 보존. |
| 외부 뉴스 소스 (RSS·HTML) | 외부 의존 | fetchers가 호출. 소스 단위 격리. 12~18개 소스. |
| Python 3.12 표준 라이브러리 (zoneinfo, subprocess, logging) | 내부 의존 | KST 변환·git commit·로깅. SMTP/email 의존성은 V1에서 제거 (ADR-003). |
| 외부 패키지 (anthropic, feedparser, requests, beautifulsoup4, pyyaml, python-dateutil) | 내부 의존 | pyproject.toml 동결 버전. `requests`가 텔레그램 API 호출 겸용. |
| tzdata (Windows 한정, `sys_platform == 'win32'`) | 내부 의존 | Python `zoneinfo` 가 IANA tzdata 를 요구하나 Windows 는 시스템 db 없음 — PyPI 패키지로 보충. (step1 검증 중 발견, `phases/_hotfix-log/2026-05-19-windows-tzdata.md`) |

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
- **AC-1.6**: 텔레그램 메시지 헤더 한 줄 형식 `📰 [팜보스 트렌드] M/D(요일) 오늘의 뉴스 N건` (예: `📰 [팜보스 트렌드] 5/19(월) 오늘의 뉴스 8건`). N=0이면 본문은 발송, 제목 N건은 `0건`. Pages HTML `<title>` 태그도 동일 형식. (2026-05-19 사용자 결정, ADR-003 채널 변경으로 "메일 제목" → "메시지 헤더"로 일반화)

### AC-2. 카테고리·항목

- **AC-2.1**: 카테고리 3개(`AI 트렌드` → `농산물·유통` → `팜보스 관심 키워드`) 순서 고정. 카테고리당 5~10건, 0건 시 "오늘 새 뉴스 없음" 명시. 표면 A(텔레그램)·표면 B(Pages) 모두 동일 순서.
- **AC-2.2**: 한 기사가 복수 카테고리 매칭 시 좁은 쪽 1곳에만 노출. 우선순위: `팜보스 관심 키워드` > `농산물·유통` > `AI 트렌드`. `filters/category.py`가 단일 매핑 결정.
- **AC-2.3-A** (표면 A — 텔레그램 메시지): 카테고리당 헤드라인 한 줄씩, "외 N건" 표기. 메시지 form:
  ```
  📰 [팜보스 트렌드] M/D(요일) 오늘의 뉴스 N건
  (소스 X개 중 Y개 정상, Z개 실패: ...)

  ① AI 트렌드 (3건)
    • {제목 1} 외 2건
  ② 농산물·유통 (3건)
    • {제목 1} 외 2건
  ③ 팜보스 관심 키워드 (2건)
    • {제목 1} 외 1건

  전체 본문: {Pages URL}
  의견·소스 제안은 단톡방 답글로.
  ```
  메시지 총 길이 ≤ 4,096자 (텔레그램 한도). 발송 시 `disable_web_page_preview=true` 설정 — Pages URL 미리보기 카드 차단.
- **AC-2.3-B** (표면 B — Pages HTML): 항목 form `{번호}. {제목}\n   요약: {2문장 이내 한국어}\n   원문: <a href="{full URL}">{full URL}</a>   ({출처명} · {KST 발행시각})`. 표면 A의 헤드라인 목록과 표면 B의 항목 목록은 순서·건수·우선순위 1:1 일치 (`render`에서 같은 데이터 구조에서 두 형식 동시 생성).
- **AC-2.4**: 영어 원문은 한국어 번역 제목 + 괄호로 원제 병기 — `Anthropic, Claude Opus 4.7 출시 (Announcing Claude Opus 4.7)`. 표면 A·B 모두 동일.
- **AC-2.5** (2026-05-19 갱신 — 기존 "LLM 코멘트 금지" 폐기): 표면 A·B 각 항목에 `💡 회사 영향:` 한 줄 명시 허용. LLM이 회사 사업 영역(정다운 산지유통·팜보스 온라인커머스·시경 프랜차이즈)과 직결되는 영향만 작성. 사업 영역 외 일반 산업 동향이면 빈 메시지(예: `회사 직접 영향 없음`)로 통일 — **억지 추론 금지**. 안전장치: 원문 링크 동봉(AC-3.3) + 풋터 hallucination 경고(AC-2.9).
- **AC-2.6**: 표면 A 풋터 한 줄 `의견·소스 제안은 단톡방 답글로` + 표면 B HTML 풋터 `의견·소스 추가 요청은 단톡방에서. 운영: {운영자 표기}` (2026-05-19 사용자 결정, ADR-003 채널 변경으로 "이 메일에 회신" → "단톡방 답글"로 변경).
- **AC-2.7** (2026-05-19 갱신 — 애플 감성 디자인 v3 채택):
  - 표면 A 텔레그램: 헤더 이모지 `📰` 1개 + 카테고리 번호 `①②③` + 우선순위 `⭐⭐⭐` (텍스트). 본문 항목 내부에 이모지 사용하지 않음.
  - 표면 B Pages HTML: **애플 사이트 감성 미니멀** 톤 — 큰 hero 타이포(`오늘 챙길 뉴스 N건.` 48~56px Bold), 폰트 스택 `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "Noto Sans KR", "Apple SD Gothic Neo", sans-serif`, `letter-spacing: -0.022em`, 카드 제거하고 1px 보더 + 큰 여백, TL;DR 박스는 `background: #f5f5f7; border-radius: 18px; padding: 40px 32px`, 우선순위는 점 3개 indicator(`••●` / `••○` / `•○○`), 링크는 Apple Blue `#06c` + arrow(`원문 읽기 →`), hero 강조 텍스트만 `linear-gradient(135deg, #0a84ff 0%, #5e5ce6 100%)` background-clip. 카테고리 eyebrow에 색 약간씩 (AI `#0a84ff` / 농산물 `#30a46c` / 팜보스 `#d04545`), 카테고리 제목·본문은 모두 `#1d1d1f`로 절제.
  - 모바일 반응형: 600px 이하에서 hero 56→40px, 카테고리 36→28px, TL;DR padding 40→28px 자동 축소.
  - 샘플 레퍼런스: [samples/2026-05-19-digest-preview-v3.html](../../../samples/2026-05-19-digest-preview-v3.html)
- **AC-2.8** (ADR-003 신규, 2026-05-19 boundary 갱신): 표면 B(Pages HTML)는 `<meta name="robots" content="noindex,nofollow">` 헤더 필수. **`gh-pages` branch root** 의 `robots.txt` 에 `User-agent: * / Disallow: /` 배치. 검색엔진 크롤링 차단. master branch 의 `docs/canonical/`·`docs/features/`·`docs/_extracted/` 같은 회사 사내 문서는 Pages 에 절대 노출되지 않음 (Pages source = `gh-pages` branch root).
- **AC-2.9** (2026-05-19 신규): 표면 B HTML 풋터에 안전 경고 한 줄 — `"회사 영향" 라인은 봇의 분석으로, 원문에 없는 추론이 포함될 수 있습니다. 의사결정 전 반드시 원문 링크를 함께 확인해 주세요.` 직원이 LLM 분석을 맹신하지 않게.
- **AC-2.10** (2026-05-19 신규): 각 항목에 **회사 영향 우선순위** 표시:
  - `⭐⭐⭐` — 회사 직접 영향 (정다운/팜보스/시경 운영에 즉시 액션 필요)
  - `⭐⭐` — 회사 간접 영향 (참고용 데이터, 협상·전략 입력)
  - `⭐` — 산업 동향 일반 (직접 영향 없음)
  Prompt가 회사 사업 컨텍스트(§6-5)를 받아 점수 결정. 표면 A·B 모두 우선순위 표시.
- **AC-2.11** (2026-05-19 신규): 표면 A·B 상단에 **TL;DR 박스** — `⭐⭐⭐` 항목 자동 추출, 최대 3건 노출:
  - 1건 이상 있으면 헤더 `⚡ 오늘 꼭 챙길 N건` + 각 항목 1줄(제목 + 회사 영향 요약)
  - 0건이면 헤더 `⚡ 오늘은 산업 동향 위주` + 1줄 안내(`회사 직결 뉴스 없음, 산업 동향 N건 정리`)
  - 표면 A는 TL;DR을 메시지 상단 2~3줄로, 표면 B는 카드형 박스로.
- **AC-2.12** (2026-05-19 신규): 각 카테고리 헤더 아래 **"이 카테고리 핵심"** 한 줄 — 해당 카테고리의 항목들을 1줄로 요약. 항목 1건이면 그 1건 요약, 0건이면 표시 안 함. Prompt가 카테고리 단위로 생성.

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
- **AC-5.2**: 메시지·Pages 헤더 양쪽에 "소스 N개 중 M개 정상 수집, X개 실패: {이름}" 표기. 실패가 없으면 "소스 N개 정상 수집" 표기.
- **AC-5.3**: Claude API quota·hard cap 초과 시 RuntimeError → `main()`이 잡아서 운영자 텔레그램 chat(`OPS_ALERT_CHAT_ID`)에 alert 메시지 발송 후 종료. 직원 단톡방·Pages는 게시하지 않음.
- **AC-5.4** (ADR-003 갱신): 텔레그램 Bot API 발송 실패 또는 Pages publish (git push) 실패 시 동일 운영자 alert. retry 1회만(같은 cron 안에서). 두 번째 실패 시 종료. 운영자 alert 자체가 실패하면 stderr 로그만 + 비정상 exit code (alert 무한루프 방지).
- **AC-5.5**: Hard cap: 일일 입력 토큰 ≤ 100,000, 일일 출력 토큰 ≤ 20,000, 일일 API 호출 횟수 ≤ 30. 어느 하나라도 초과 시 즉시 RuntimeError.
- **AC-5.6** (ADR-003 신규): dispatcher는 ① Pages publish 성공 (HTTP 200 응답 확인) → ② 텔레그램 메시지 발송 순서 강제. Pages 미배포 상태로 텔레그램 URL 발송 금지 — 직원이 클릭 시 404 회피. push 후 60초 대기 + URL HEAD 200 확인까지 wait, 그래도 404면 운영자 alert 후 텔레그램 메시지 발송 안 함.

### AC-6. 수신자 관리 (ADR-003 갱신 — 텔레그램 단톡방 기반)

- **AC-6.1** (ADR-003 갱신): 직원 수신자는 `TELEGRAM_CHAT_ID` 환경변수가 가리키는 사내 다이제스트 전용 단톡방 1개. `config/recipients.yml` 파일은 V1에서 제거됨 (이메일 수신자 관리 불필요).
- **AC-6.2** (ADR-003 갱신): 단톡방 멤버 = 직원 수신자. 멤버 추가·제거는 단톡방 입퇴장으로 즉시 반영. 코드 변경·배포 불필요.
- **AC-6.3** (ADR-003 갱신): 일시 정지(휴가·이탈) 직원은 단톡방 음소거 또는 알림 끄기로 본인 재량 처리. 봇은 단톡방 전체에 발송하므로 개별 suppress 개념 없음.
- **AC-6.4** (ADR-003 갱신, 2026-05-19 사용자 결정): V1 단톡방 멤버를 단계적으로 확장:
  - Day 0 ~ Day 6 (D+1주차): 운영자 본인만 단톡방 멤버. 운영자가 다이제스트 톤·hallucination·소스 누락을 1주 검토.
  - Day 7 ~ Day 13 (D+2주차): 김종만 총괄대표·정은주 이사·장석중 이사 3명 단톡방 초대. 이사진 1주 검토.
  - Day 14 이후: 전 직원 단톡방 초대.
  - 일정 변경은 운영자 재량.
- **AC-6.5** (ADR-003 갱신): V1 발송 채널 = 텔레그램 Bot API. Gmail SMTP·이메일 발송은 V1에서 제거. 봇 이름은 BotFather에서 결정 (예: `@farmboss_trend_bot`), 토큰은 `TELEGRAM_BOT_TOKEN` 시크릿. 운영자 alert은 별도 chat `OPS_ALERT_CHAT_ID`.
- **AC-6.6** (ADR-003 신규, 2026-05-19 boundary 갱신): Pages HTML은 매일 **`gh-pages` branch** 의 `digest/YYYY-MM-DD.html` 로 commit·push (master branch 와 분리, 사내 문서 보호). dispatcher 는 `git worktree` 또는 임시 디렉토리에서 `gh-pages` checkout → 파일 작성 → commit → push 처리. 같은 날짜 재실행 시 동일 파일 덮어쓰기 + commit message에 "(rerun)" 표기. push 권한은 `GITHUB_TOKEN` 기본값 사용. **운영자 초기 셋업 1회**: 빈 orphan `gh-pages` branch push 후 Settings → Pages 에서 Source 를 `gh-pages` branch root 로 설정 — `docs/ops/secrets_setup.md` 가이드 참조.

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
| Digest body | Filtered articles + summarize.md prompt + 회사 컨텍스트 (3법인 사업 영역·산지) | summarizer/client.py — Claude API 단일 호출(점수+요약+회사 영향+카테고리 핵심), Prompt caching, schema validation | `Digest` (항목별 score·summary·company_impact + 카테고리 headline + HTML body + 텔레그램 인덱스 + TL;DR 자동 추출 메타) |
| Sent record | Digest의 모든 canonical URL | history/store.py — append to `sent.jsonl` + artifact 업로드 | 다음 실행의 dedup 입력 |
| Pages HTML | Digest.html | dispatchers/pages_publish.py — `docs/digest/YYYY-MM-DD.html` commit·push, push 후 URL HTTP 200 확인 | Pages URL 활성 |
| Telegram message | Digest.telegram_text + 활성 Pages URL | dispatchers/telegram_send.py — Bot API sendMessage | 사내 단톡방 알림 도착 |
| Operator alert (조건부) | 실패 이벤트 (quota·텔레그램·Pages publish) | summarizer/dispatcher의 RuntimeError를 main()이 catch | 운영자 텔레그램 chat (OPS_ALERT_CHAT_ID) |

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

### 6-3. 수신자 관리 (ADR-003 갱신 — `config/recipients.yml` 폐기)

V1 직원 수신자는 텔레그램 단톡방 멤버십으로 관리. `config/recipients.yml` 파일은 V1에서 생성하지 않는다. 멤버 추가·제거는 단톡방 운영자가 텔레그램 UI에서 직접 처리.

수신자 관련 정보는 모두 §8 환경변수로 이동:
- `TELEGRAM_CHAT_ID` — 직원 다이제스트 단톡방 ID (예: `-1001234567890`, 음수)
- `OPS_ALERT_CHAT_ID` — 운영자 alert 전용 chat ID
- `TELEGRAM_BOT_TOKEN` — 봇 인증 토큰

이메일 수신자 관리(BCC·suppress·Reply-To 등)는 V1 범위 외. V2에서 이메일 dispatcher 재도입 시 별도 yml 부활.

`.gitignore`에 `config/recipients.yml` 차단 항목은 유지 (V2 재도입 시 실수 방지).

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

### 6-5. `prompts/summarize.md` (정적, 2026-05-19 갱신)

```markdown
당신은 팜보스 그룹(농산물 통합 유통 그룹) 임직원을 위한 매일 뉴스 다이제스트의
큐레이션·요약·분석 어시스턴트입니다.

## 회사 컨텍스트 (회사 영향 판단 기준)

팜보스 그룹은 3법인 구조:
- 정다운 영농조합법인 (j): 산지 유통, GS리테일 1차 밴드 납품, 청도·경산·밀양 산지
- 팜보스 농업회사법인 (f): 온라인 커머스 B2C, 사방넷 기반, 콘텐츠 마케팅
- 주식회사 시경 (s): 닥터상달 과일 프랜차이즈, 안동농협공판장 중도매

주요 작목: 복숭아(청도·경산), 감(청도·경산), 딸기(밀양·청도).
협력사: 금송농업회사법인(GS 물류), 이븐농산물류(온라인 출고).

## 출력 사항

각 후보 기사에 대해:

1. **score** (정수 1~10) — 회사 직접 영향이 클수록 높음:
   - 8~10: 3법인 중 하나 이상의 운영(납품·수매·출하·마케팅)에 즉시 액션 필요한 영향
   - 5~7: 협상 카드·전략 입력으로 참고 가치 있는 간접 영향
   - 1~4: 산업 동향 일반, 회사 직접 영향 없음

2. **summary** (한국어 2 문장 이내) — 원문에 명시되지 않은 수치·인과·날짜 생성 금지.
   숫자·고유명사·날짜는 원문 그대로 인용.

3. **company_impact** (문자열) — 회사 사업 영역과 직결되는 영향만 한 문장으로.
   - 직결 영향이 있으면: 어느 법인·어떤 운영에·어떤 액션이 필요한지 1문장
     (예: `정다운 1차 밴드 납품 조건 재검토 가능. 장석중 이사 영업 미팅 점검 필요.`)
   - 직결 영향이 없으면: 빈 문자열 `""` (산업 동향 일반 항목)
   - **억지 추론 금지**: 회사 영역과 무관하면 반드시 빈 문자열로.

## 카테고리 단위 추가 출력

전체 후보를 카테고리(ai_trend / agri_distribution / farmboss_keyword)별로 묶은 뒤
각 카테고리마다 다음을 추가:

4. **category_headline** (문자열) — 해당 카테고리 항목들을 1줄로 요약.
   1건만 있으면 그 1건의 핵심을, 0건이면 빈 문자열.

## 출력 형식

```json
{
  "items": [
    {"id": "...", "score": 9, "summary": "...", "company_impact": "..."},
    {"id": "...", "score": 3, "summary": "...", "company_impact": ""}
  ],
  "category_headlines": {
    "ai_trend": "오늘은 LLM 3사 업데이트가 동시에 — Anthropic·OpenAI·Google.",
    "agri_distribution": "...",
    "farmboss_keyword": "..."
  }
}
```

## 금지

- 원문에 없는 수치·인과·날짜 생성
- 3문장 이상 요약 또는 3문장 이상 company_impact
- 영문 요약·영문 company_impact
- "why it matters", "한 가지 더", "당신에게 의미" 같은 광고형 코멘트 (company_impact 자리에 명확한 행동 한 줄만)
- score를 회사 영향 외 기준으로 매기기 (개인 흥미·기술적 신기성 등)
```

JSON 출력 강제 + 후처리(`summarizer/render.py`)에서 schema validation. 위반 시 해당 항목 폐기. `company_impact` 빈 문자열은 정상값, 폐기 사유 아님.

## 7. 운영자 Alert 결정 (brief §5-6 해소, ADR-003 갱신)

**운영자 전용 텔레그램 chat** 사용 — 직원 단톡방·Pages는 깨끗하게 유지:

- 직원 단톡방 메시지: "소스 N개 중 M개 정상, X개 실패: {이름}" 한 줄만 메타 헤더.
- 운영자 alert: `OPS_ALERT_CHAT_ID` chat에 별도 텍스트 메시지 발송 — 본문 `[팜보스 트렌드 알림] {datetime KST} {ERROR_KIND}\n{스택트레이스}\n다음 cron: {KST}`.
- 발송 실패가 alert 자체에서도 발생하면 stderr 로그 + 비정상 exit code만 (재시도 없음 — 무한루프 방지).
- chat 선택: ① 운영자 본인과 봇의 1:1 chat 또는 ② 운영자 전용 다른 단톡방(2~3명). V1은 ①로 시작.

## 8. 시크릿·환경변수 명세 (ADR-003 갱신)

| 이름 | 매체 | 용도 |
|---|---|---|
| `ANTHROPIC_API_KEY` | GitHub Actions Secret | Claude API 인증 |
| `TELEGRAM_BOT_TOKEN` | GitHub Actions Secret | 텔레그램 Bot API 인증 (BotFather 발급, 형태 `123456:ABC-DEF...`) |
| `TELEGRAM_CHAT_ID` | GitHub Actions Variable 또는 Secret | 직원 다이제스트 단톡방 ID (음수 정수, 예: `-1001234567890`) |
| `OPS_ALERT_CHAT_ID` | GitHub Actions Variable 또는 Secret | 운영자 alert 전용 chat ID |
| `PAGES_BASE_URL` | GitHub Actions Variable | Pages base URL 표기 (예: `https://owner.github.io/f_trendnewsbot`). 텔레그램 메시지·로깅에서 사용 |
| `CLAUDE_MODEL_ID` | GitHub Actions Variable | 사용 모델 ID. 기본값 `claude-haiku-4-5-20251001`. deprecated 시 코드 변경 없이 교체. |
| `GITHUB_TOKEN` | GitHub Actions 자동 주입 | Pages publish 시 git push 권한. 별도 등록 불필요. |

V1에서 제거된 환경변수 (ADR-003): `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `GMAIL_FROM`, `RECIPIENTS_YML_BASE64`, `OPS_REPLY_TO`.

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
- 2026-05-19: V1 발송 채널 변경 (ADR-003 accepted) — Gmail SMTP → 텔레그램 Bot API + GitHub Pages 전면 전환:
  - §1 의존 시스템: Gmail SMTP 항목 제거, 텔레그램 Bot API + Pages 추가
  - AC-1.6: "메일 제목" → "메시지 헤더 + Pages `<title>`"
  - AC-2.3 → AC-2.3-A(텔레그램 메시지) / AC-2.3-B(Pages HTML) 분리. 텔레그램은 헤드라인 인덱스, Pages는 전체 본문.
  - AC-2.6 풋터: "이 메일에 회신" → "단톡방 답글"
  - AC-2.8 신규: Pages noindex meta + robots.txt
  - AC-5.3·5.4 운영자 alert 채널: Gmail → 텔레그램 chat
  - AC-5.6 신규: Pages publish 성공 확인 후 텔레그램 발송 (순서 강제)
  - AC-6 전면 — `recipients.yml` 폐기, 단톡방 멤버십으로 수신자 관리. AC-6.6 신규(Pages publish 규칙).
  - §5 Resource flow: Email row → Pages HTML row + Telegram message row 분할
  - §6-3: `recipients.yml` 스키마 → 텔레그램 환경변수 안내로 교체
  - §7 운영자 alert: 별도 메일 → 운영자 텔레그램 chat
  - §8 환경변수: GMAIL_*·RECIPIENTS_YML_BASE64·OPS_REPLY_TO 제거, TELEGRAM_BOT_TOKEN·TELEGRAM_CHAT_ID·OPS_ALERT_CHAT_ID·PAGES_BASE_URL 추가
- 2026-05-19: UX·분석 강화 결정 반영 (샘플 v2 톤 사용자 OK):
  - AC-2.5 폐기 ("LLM 코멘트 금지") → 회사 영향 한 줄 명시 허용 (사업 영역 외면 빈 문자열, 억지 추론 금지)
  - AC-2.7 표면 B 카테고리별 색상 분리 추가 (AI 파랑·농산물 초록·팜보스 빨강)
  - AC-2.9 신규: HTML 풋터에 hallucination 안전 경고
  - AC-2.10 신규: 항목별 회사 영향 우선순위 ⭐⭐⭐/⭐⭐/⭐
  - AC-2.11 신규: TL;DR 박스 (⭐⭐⭐ 자동 추출, 0건이면 산업 동향 안내)
  - AC-2.12 신규: 카테고리 헤더 아래 "이 카테고리 핵심" 한 줄
  - §5 Digest row에 score·company_impact·category_headline·TL;DR 메타 명시
  - §6-5 prompt 전면 갱신 — 회사 컨텍스트(3법인 사업·산지·협력사) 포함, 출력 형식 JSON 확장(items + category_headlines), 점수 0~10 기준이 회사 영향으로 명확화, company_impact 빈 문자열 허용·억지 추론 금지 강제
- 2026-05-19: 표면 B Pages HTML 디자인을 **애플 사이트 감성 미니멀**로 확정 — AC-2.7 보강 (SF Pro / Noto Sans KR 폰트 스택, 56px hero·hero 그라데이션 강조, 카드 제거·1px 보더, TL;DR `#f5f5f7` background·`border-radius: 18px`, 우선순위 점 indicator `••●`, 링크 Apple Blue `#06c` + arrow, 카테고리별 미세한 eyebrow 색). 샘플 레퍼런스 `samples/2026-05-19-digest-preview-v3.html`로 동결.
- 2026-05-19: Pages 배포 boundary 변경 (ADR-003 §결정·§대안 F 갱신) — master `/docs` root 채택 시 회사 사내 문서(`docs/canonical/`·`docs/features/`·`docs/_extracted/`) 가 외부 공개되는 위험 발견. **`gh-pages` 전용 branch root** 로 변경. AC-2.8·6.6 본문 갱신. step6 dispatcher 의 `pages_publish.py` 핫픽스 + step7 secrets_setup.md 에 운영자 초기 셋업 1회 가이드 추가 필요.
