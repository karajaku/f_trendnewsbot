# Step 5: summarizer — Anthropic SDK + Prompt caching + hard cap + render(HTML+text)

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.3·2.4·2.5·3·5.3·5.5 + §6-5

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) CRITICAL #6 (요약 옆 원문 링크), CRITICAL #9 (quota hard cap)
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) AC-2.3~2.5, AC-3, AC-5.3, AC-5.5, §6-5 prompts
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §3-2 Anthropic SDK·Prompt caching·토큰 추정
- step1 산출물: `lib/time_helper.to_kst_string`
- step3·4 산출물: `Article`, filter 통과 후 `dict[CategoryId, list[Article]]`

## 작업 범위

### Summarizer client

- `src/summarizer/__init__.py`, `src/summarizer/client.py`
  - `Anthropic` 클라이언트 wrapper
  - 모델 ID는 `os.environ.get("CLAUDE_MODEL_ID", "claude-haiku-4-5-20251001")` (requirements §8)
  - Prompt caching `system` 영역에 적용 (tech-research §3-2)
  - 단일 호출 (점수+요약 동시) — requirements §3 결론 #2
  - JSON output schema validation (`id`, `score`, `summary`)
  - 결과 매핑 실패한 항목은 폐기 + 메타에 누락 표기 (design-review R-1)

### Hard cap quota

- `src/summarizer/quota.py`
  - 일일 누적 token·call 추적 (in-memory + 호출 직전 체크)
  - 입력 ≤ 100,000, 출력 ≤ 20,000, 호출 ≤ 30 (AC-5.5)
  - 초과 시 `QuotaExceededError` raise

### Prompts

- `prompts/summarize.md` — requirements §6-5 그대로
- prompt 안에 "원문에 없는 수치·인과·날짜를 생성하지 말 것" 명시
- "why it matters" 금지 문구 명시

### Render

- `src/summarizer/render.py`
  - `build_digest(by_category, failures, sent_at_kst, source_count) -> Digest`
  - `Digest.html`, `Digest.text` (HTML + plain text 동일 정보, AC-2.3)
  - HTML은 인라인 스타일 (Gmail 호환), 외부 리소스 없음
  - 한국어 헤더 "5월 19일 (월) 오전 7:30 KST" (AC-1.2, `lib/time_helper.format_subject_date`)
  - 카테고리 0건 시 "오늘 새 뉴스 없음" 라인 (AC-2.1)
  - 실패 소스 헤더 한 줄 (AC-5.2)
  - 영어 원문 제목은 한국어 번역 + 괄호 원제 (AC-2.4)
  - **"why it matters" 류 라인 절대 생성 금지** (AC-2.5)

## 영향받는 데이터 정의 목록

- `prompts/summarize.md` — 신규 (정적, git tracked, requirements §6-5 그대로)
- `src/summarizer/templates/digest.html.j2` (또는 동등 Python f-string template) — 애플 감성 v3 HTML template, 인라인 스타일 동결. requirements AC-2.7 + 샘플 `samples/2026-05-19-digest-preview-v3.html` 기준
- 신규 환경변수 의존: `ANTHROPIC_API_KEY` (시크릿), `CLAUDE_MODEL_ID` (variable)

## Acceptance Criteria

- [ ] `client.summarize(by_category_articles) -> SummarizeResult` 가 Prompt caching `system` 영역 사용 (tech §3-2), 단일 호출에 `items[].score` + `items[].summary` + `items[].company_impact` + `category_headlines{}` 동시 출력 (AC-2.10·2.11·2.12, prompt §6-5)
- [ ] system prompt에 회사 컨텍스트(3법인 사업·청도·경산·밀양 산지·금송·이븐 협력사) 포함 — 사용자가 변경 시 prompt 파일만 수정, 코드 무관
- [ ] JSON output schema 위반 항목은 폐기 + 메타에 `dropped_items` 카운트 누적. `company_impact` 빈 문자열은 정상값 (폐기 사유 아님)
- [ ] `quota.check_and_record(tokens_in, tokens_out)` 가 cap 초과 시 `QuotaExceededError` raise (AC-5.5)
- [ ] hard cap: input 100k / output 20k / calls 30. 코드에 상수 + override env var 없음 (운영자 수동 조정만)
- [ ] `render.build_digest`의 출력 `Digest.html` 에 모든 `Article.canonical_url` 포함 (단축 URL 0건, AC-2.3-B)
- [ ] `Digest.html` 은 애플 감성 v3 template 사용 (AC-2.7): hero·TL;DR 박스·카테고리 헤더·항목 카드·풋터 6 컴포넌트, 외부 CSS·이미지 의존 0 (인라인 스타일만)
- [ ] `Digest.telegram_text` 와 `Digest.html` 항목 수·순서·우선순위 점수 1:1 일치 (render 단일 데이터 구조에서 두 형식 생성, AC-2.3-A/B)
- [ ] **TL;DR 자동 추출** (AC-2.11): `items[].score >= 8` (⭐⭐⭐) 항목을 최대 3건 자동 추출. 0건이면 "오늘은 산업 동향 위주" fallback
- [ ] **우선순위 매핑** (AC-2.10): score 8~10 → `⭐⭐⭐` / `••●`, score 5~7 → `⭐⭐` / `••○`, score 1~4 → `⭐` / `•○○`. render에서 자동 변환
- [ ] **카테고리 핵심** (AC-2.12): 각 카테고리 헤더 아래 `category_headlines[cat_id]` 출력. 빈 문자열이면 표시 안 함
- [ ] **회사 영향 박스** (AC-2.5): 각 항목에 `💡 회사 영향: {company_impact}` 박스 (`#f5f5f7` background, 18px radius). 빈 문자열이면 `회사 직접 영향 없음` 라인으로 fallback 표시
- [ ] HTML head에 `<meta name="robots" content="noindex,nofollow">` (AC-2.8)
- [ ] HTML 풋터에 hallucination 경고 한 줄 (AC-2.9)
- [ ] 카테고리 0건 시 본문에 "오늘 새 뉴스 없음" 1회 노출, 카테고리 자체는 표기 유지 (AC-2.1)
- [ ] 실패 소스 있으면 hero 메타 + 텔레그램 헤더 한 줄에 "소스 N개 중 M개 정상 수집, X개 실패: {이름}" (AC-5.2)
- [ ] 본문 어디에도 "why it matters", "당신에게 의미", "왜 중요한가" 류 광고형 코멘트 라인 없음 (grep 통과, prompt §6-5 금지)
- [ ] 시각 표기 모두 `lib/time_helper.format_subject_date` 또는 `to_kst_string` 통과 (AC-7.4)
- [ ] unit test 15건 이상: schema 위반 폐기 / quota cap / Prompt caching system 적용 / 카테고리 0건 / 실패 소스 노출 / HTML·telegram 정보 일치 / 영어 제목 번역 / URL 보존 / 광고형 코멘트 차단 / 한국어 헤더 형식 / TL;DR 1~3건 추출 / TL;DR 0건 fallback / 우선순위 점수→indicator 매핑 / category_headlines 빈 문자열 처리 / company_impact 빈 문자열 fallback

## 금지사항

- 점수·요약을 분리 호출 (V1은 단일 호출 — V2 검토, design-review R 별도 항목)
- prompt에 "why it matters"·"당신에게 의미"·"한 가지 더" 같은 광고형 코멘트 출력 유도 금지 (§6-5)
- `company_impact` 자리에 회사 사업 영역 외 일반 시사점 작성 금지 — 빈 문자열로 통일 (AC-2.5 억지 추론 금지)
- HTML template을 코드로 동적 조립 금지 — `digest.html.j2` (또는 동등) template 1개로 동결, 데이터만 주입
- 디자인 톤 변경 금지 (AC-2.7 애플 감성 동결, 변경 시 brief·requirements 갱신 필수)
- 외부 CSS·이미지·폰트 파일 의존 금지 — Pages가 정적이라 인라인 스타일 + 시스템 폰트만
- `httpx` 직접 사용 금지 (Anthropic SDK가 알아서)
- API 키 평문 로그 금지 — `mask_key` helper 통과 (AC-7.2)
- dispatcher 모듈 생성 금지 (step6)
- 시간 표기 helper 우회한 isoformat 노출 금지 (AC-7.4)

## 수동 테스트 절차

1. fixture 기사 묶음(카테고리별 8건) → `summarize` 호출 mock → JSON 응답 mock 처리 → `Summary` list 검증
2. fixture JSON 응답 1건이 schema 위반(필드 누락) → 해당 항목 폐기 + `meta.dropped_items` +1
3. fixture에 quota 한계 직전 토큰 적용 → 다음 호출에서 `QuotaExceededError`
4. fixture digest 생성 → `digest.html` 에 `</p><a href="https://..."` 등 모든 URL 포함 확인 (grep)
5. `digest.text`에 "why it matters" / "왜 중요" 부재 grep 확인 (테스트 코드)
6. `pytest tests/test_summarizer.py` 통과

## 수동 QA Owner

`에이전트 정적 분석` — Claude API mock + grep + pytest로 검증. 실제 API 호출은 step8 dry-run.

## 주 담당 에이전트

`tnb-implementer` — SDK 호출·prompt·render 도메인 로직.

## 회귀 위험

- Prompt caching 적용 실수로 토큰 비용 폭증 → hard cap이 잡지만 운영자 alert 발생. quota.py로 방어.
- model ID 환경변수 누락 시 default 사용 — 의도된 동작이지만 로그에 "using default model: ..." 출력 권장.
- JSON 응답 model이 가끔 markdown fence(```json ... ```)로 감싸서 반환 — 파서가 fence 처리하지 못하면 전체 카테고리 폐기. 파서에 fence strip 코드 필수.

## pending_manual_qa_scenarios 누적

- "실제 Anthropic API 호출 시 system prompt cache hit 비율 확인 (step8 dry-run에서 로그 검사, 70%+ 기대)"
- "다이제스트 본문(HTML+text) 시각·문체·광고형 코멘트(`why it matters` 등) 부재를 사용자가 실제 메일에서 phase 끝 일괄 검토에서 시각 확인"
- "회사 영향 라인 hallucination 비율 — 첫 1주일 dry-run에서 실제 회사 영향과 비교, 잘못된 추론 비율 verification-record 기록 (4주 후 분리 호출 전환 판단 입력)"
- "TL;DR 자동 추출 정확도 — `score >= 8` 항목이 실제 회사 직결 영향과 일치하는지 1주일 dry-run에서 운영자 검토"
- "애플 감성 v3 디자인이 모바일(600px 이하)에서 깨지지 않는지 운영자가 단톡방 메시지 → Pages URL → 모바일 브라우저로 확인"
