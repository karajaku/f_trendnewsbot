# 소스·키워드 운영 보강 — ai_trend 빅테크 누락 보완 + 카테고리 키워드 폭 확장

날짜: 2026-05-20
규모: 핫픽스급 운영 보강 (2 config 파일, 계약 변경 없음, 코드 변경 없음)

## 동기

운영자 보고 (2026-05-20):

> "오늘 구글 제미나이 3.5 공개 뉴스가 있던데 이런 뉴스는 어떻게 찾아야 우리 레터에 들어올까"

`ai_trend` 카테고리의 구글 진영 소스가 `google_deepmind_blog` 하나뿐이라, Gemini·Veo 등 **제품 발표의 1차 진원지인 The Keyword (blog.google) 가 시드에 누락**. 더불어 `must_match_any` 키워드에 Llama·DeepSeek·Grok·Veo·Sora·Copilot 같은 메이저 모델/제품명이 다수 누락되어 있어, 진원지 RSS 가 들어오더라도 본문 키워드 매칭에서 떨어질 위험이 있음. `agri_distribution`·`farmboss_keyword` 도 같은 검토에서 보강 필요성 확인.

requirements.md §6-2 의 "시드 12개 키워드 동결. dry-run 후 보강은 phase 외 운영" 정책에 따라 phase 생성 없이 운영 보강으로 처리.

## 변경

### 1. `config/sources.yml` — ai_trend 4개 신규 enable

| id | name | URL | 비고 |
|---|---|---|---|
| `google_blog_ai` | Google AI Blog (The Keyword) | `https://blog.google/technology/ai/rss/` | Gemini 등 제품 발표 1차 진원지 |
| `google_cloud_ai` | Google Cloud AI Blog | `https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/` | Vertex AI 등 엔터프라이즈 발표. 정식 path `cloud.google.com` 은 SPA 라 RSS 미제공 — withgoogle.com 미러 채택 |
| `google_research` | Google Research Blog | `https://research.google/blog/rss/` | DeepMind 보완 채널 |
| `the_verge_ai` | The Verge AI | `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | Atom feed (feedparser 호환). 빅테크 출시 24h 내 보도 안전망 |

운영 현황: 14개 → 18개 entry, enabled 7개 → 11개.

### 2. `config/filters.yml` — 카테고리 키워드 확장

**ai_trend.must_match_any** (8개 → 21개):
- 추가 (+13): `Llama` `DeepSeek` `Grok` `Sora` `Veo` `Copilot` `Perplexity` `NVIDIA` `Codex` `Midjourney` `DALL-E` `인공지능` `생성형 AI`

**agri_distribution.must_match_any** (9개 → 19개):
- 추가 (+10): `도매시장` `콜드체인` `물류` `신선식품` `농협` `컬리` `홈플러스` `롯데마트` `농림축산식품부` `작황`

**farmboss_keyword.must_match_any** (12개 → 24개):
- 제거 (-1): `감` — substring noise 매우 큼 (감동·감기·민감·예감 등 무관 한자어 매칭)
- 분해 교체 (+4): `단감` `홍시` `곶감` `청도반시`
- 추가 산지 (+3): `안동` `영천` `상주`
- 추가 작물 (+5): `사과` `자두` `포도` `양파` `마늘`
- 추가 매장 (+2): `GS25` `GS THE FRESH`

코드(`src/`) 변경 없음. `id` · `category` enum · `type` enum · 스키마 모두 보존.

## URL 응답 사전 검증 (2026-05-20)

`Invoke-WebRequest -UseBasicParsing -TimeoutSec 15 -UserAgent 'Mozilla/5.0 f_trendnewsbot/1.0'` 으로 4개 후보 URL 직접 확인:

| 후보 URL | 결과 | 채택 여부 |
|---|---|---|
| `https://blog.google/technology/ai/rss/` | HTTP 200, RSS XML 30KB | ✅ 채택 |
| `https://cloud.google.com/blog/products/ai-machine-learning/rss` | HTTP 200, HTML SPA (RSS 아님) | ❌ 폐기 |
| `https://cloud.google.com/blog/products/ai-machine-learning.rss` | HTTP 200, HTML SPA | ❌ 폐기 |
| `https://cloud.google.com/blog/rss/` | HTTP 200, HTML SPA | ❌ 폐기 |
| `https://cloudblog.withgoogle.com/products/ai-machine-learning/rss/` | HTTP 200, RSS XML 500KB | ✅ 채택 (미러) |
| `https://research.google/blog/rss/` | HTTP 200, RSS XML 78KB | ✅ 채택 |
| `https://www.theverge.com/ai-artificial-intelligence/rss/index.xml` | HTTP 404 | ❌ 폐기 |
| `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | HTTP 200, Atom XML 28KB | ✅ 채택 |
| `https://www.theverge.com/ai/rss/index.xml` | HTTP 404 | ❌ 폐기 |

## 추가 검토 후 채택하지 않은 키워드

substring 매칭의 noise 위험 때문에 후보에서 제외:

- `Meta` (회사) — metadata · metaphor · metabolism 매칭
- `Phi` (Microsoft 모델) — Philippines · Philadelphia 매칭
- `RAG` — RAGe · dRAG · FRAGment 매칭
- `MCP` — 일부 일반어 noise + 검색량 작음
- `Cursor` (AI 코딩 에디터) — 마우스/DB 커서 일반어 매칭
- `Whisper` (OpenAI 음성) — "속삭임" 일반어 매칭
- `오아시스` (마켓컬리 경쟁사) — 지명·일반어 매칭
- `aT` (한국농수산식품유통공사) — eat · heart 등 영어 substring 매칭
- `신선` — 단독은 일반어 매칭 ("신선한", "참신선언") — `신선식품` 으로 한정

## 수동 확인

- [ ] `python -m pytest -q` — 회귀 0건 (entry 14 → 18 변동, 테스트 범위 `12 <= len(sources) <= 18` 끝값에 닿음 → 범위 확장 검토 필요할 수 있음)
- [ ] `python -m ruff check src/` — config 변경이라 영향 없지만 안전망
- [ ] `python -c "from src.config.loader import load_sources, load_filters; print(len(load_sources().sources), len(load_filters().categories))"` — 스키마 파싱 확인
- [ ] 다음 발송 본문 메타 헤더의 "소스 N개 중 M개 정상 수집" 에서 신규 4개 ai_trend 소스가 정상 응답으로 표시되는지 확인
- [ ] ai_trend 카테고리에 Gemini/Veo/Llama 등 키워드 매칭 기사가 실제로 잡히는지 발송 결과로 확인 (1~2주 모니터링)
- [ ] `farmboss_keyword` 24개로 확장된 후 다른 카테고리 기사가 과도하게 흡수되는지 확인 (좁은-카테고리 우선 재배정 정책상 가능성 존재)

## 회귀 위험

- **카테고리 풀 변화**: ai_trend enabled 4 → 8 (RSS 4개 추가). 토큰 사용량 증가 가능 — Gemini API quota hard cap 모니터링 필요. summarizer 가 입력 cap 정책을 두는지 별도 확인 필요할 수 있음.
- **farmboss_keyword 흡수 폭 증가**: 키워드 12 → 24 로 두 배. `src/filters/category.py` 의 좁은-카테고리 우선 재배정이 ai_trend·agri_distribution 기사를 farmboss 로 더 자주 빨아들일 수 있음. 1주일 발송 후 카테고리별 기사 분포 검토.
- **substring noise 잔여 위험**: `Sora` (3자), `Veo` (3자), `GS25` (영문+숫자) 는 안전한 편이지만 한국어 본문에서 의외 매칭 가능성 존재 — 발송 본문 점검 시 무관 매칭 발견하면 제거 또는 단어 경계 매칭(`filters/keyword.py` 개선)을 V2 로 검토.
- **dedup 호환성**: 기존 source_id · canonical url 정규화 helper 무변경. `history/sent.jsonl` 영향 없음.
- **테스트 fixture 상한**: `12 <= len(sources) <= 18` 같은 범위 검증이 있다면 18 entry 가 끝값에 닿음. pytest 결과로 확인.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음 (entry 추가만, 스키마 무변경)
- [x] 공개 함수 시그니처 변경 없음 (코드 무변경)
- [x] save/저장 구조 변경 없음 (`history/sent.jsonl` 스키마·source_id 호환)
- [x] 모듈 경계 변경 없음
- [x] requirements.md §6-1 / §6-2 시드 동결 정책의 "dry-run 후 보강은 phase 외 운영" 조항에 부합 — phase 생성 불필요

## 후속

1. **1~2주 발송 모니터링** — ai_trend 카테고리에 빅테크 출시 기사가 실제 잡히는지, farmboss_keyword 흡수 폭이 과도하지 않은지.
2. **단어 경계 매칭** (`filters/keyword.py` 개선) — substring noise 가 발송 본문에서 발견되면 V2 phase 로 분리 검토 (`\b{kw}\b` regex 등).
3. **요약 토큰 비용 모니터링** — ai_trend 소스 4 → 8 증가로 후보 기사 수가 2배 가까이 늘면 Gemini API 일일 비용 hard cap 재검토.
4. **추가 한국어 AI 매체 보강 가능성** — AI타임스 등 한국어 매체가 V2 보강 후보. 현 시드만으로 한국어 AI 보도 충분히 잡히는지 1주일 후 평가.
