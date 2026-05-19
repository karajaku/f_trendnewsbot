# f_trendnewsbot

팜보스 매일 아침 AI·농산물 유통 트렌드 뉴스 자동 큐레이션 봇

## 언어

모든 응답은 반드시 한국어로 작성한다. 사용자가 영어로 질문하더라도 한국어로 답변한다.

> 한국어 응답이 아닌 다른 언어를 기본으로 쓰는 프로젝트라면 위 두 줄을 도메인에 맞게 교체한다.

## 에이전트 위임

`.claude/agents/tnb-*.md` 프로파일을 Agent tool로 실행한다. 임시 역할을 만들지 않는다.

| 에이전트 | 용도 |
| --- | --- |
| `tnb-phase-orchestrator` | phase 선택·이어받기·ledger 정리 |
| `tnb-implementer` | 구현 (도메인 코드 변경) |
| `tnb-ui-specialist` | UI/표면 작업 (UI 없는 프로젝트면 제거 가능) |
| `tnb-data-steward` | 데이터·schema·설정 일관성 |
| `tnb-qa-reviewer` | QA 검토 (read-only) |
| `tnb-docs-keeper` | 문서 갱신 |
| `tnb-performance-investigator` | 성능·quota·실행시간 |
| `tnb-research-investigator` | Stage 0 Discovery Research / Stage 3 Tech Research |

drift 검증: `scripts/validate_agent_profiles.ps1`.

## 탐색 시작점

`docs/DOC_MAP.md` → 작업 유형별 read order: `docs/AGENT_READ_ORDER.md`

---

## 프로젝트

- 언어: Python 3.12
- 런타임: Python 3.12 + GitHub Actions
- 타깃: GitHub Actions cron + 이메일/메신저 전송
- 도메인: 뉴스 수집·요약·발송 자동화

## 핵심 아키텍처 규칙

- CRITICAL: 동작 중인 시스템의 전체 재작성보다 작은 helper·모듈·컴포넌트로 **점진 확장**을 우선한다.
- CRITICAL: **표시 로직과 실제 규칙이 같은 helper/data를 공유**한다. 발송 본문에 보이는 요약·링크·시간 표기는 내부 dedup·필터 로직과 동일한 정규화 helper를 사용한다.
- CRITICAL: 단일 진입 파일(`src/run_daily.py`)은 **통합 지점**이다. 새 fetcher·필터·dispatcher는 작은 모듈로 분리하고 진입 파일은 위임만 한다.
- CRITICAL: **외부 소스(RSS/API/스크래핑) 장애 격리**. 한 소스가 죽어도 발송 전체가 멈추면 안 된다. fetcher는 소스 단위 try/except + 부분 성공 보고, "실패 소스 N개" 메타 정보를 다이제스트에 포함한다.
- CRITICAL: **시크릿(API 키·SMTP 비밀번호·메신저 토큰)은 코드·로그·git 어디에도 평문 노출 금지**. GitHub Actions Secrets / `.env`(로컬, `.gitignore` 적용)만 사용한다. 로그에 dict를 통째로 찍지 않는다.
- CRITICAL: **LLM 요약 옆에 항상 원문 링크**를 함께 발송한다. 요약은 보조, 원문 링크가 일차 정보다. 직원이 hallucination을 즉시 검증할 수 있어야 한다.
- CRITICAL: **시간대는 KST(Asia/Seoul) 명시**. 다이제스트의 날짜·발송 시각·기사 publish 시각은 모두 KST 표기. cron 식은 UTC이므로 매번 KST 환산 주석을 단다.
- CRITICAL: **발송 이력 영속화 + dedup**. 어제 보낸 기사는 오늘 또 보내지 않는다. URL 정규화(쿼리스트링·utm 제거) + 제목 fuzzy match + 최근 N일 이력 저장(파일 또는 GitHub Actions artifact/Issue 본문 등 영속 매체).
- CRITICAL: **API quota·비용 hard cap**. Claude API 호출은 일일 토큰·호출 상한을 설정하고 초과 시 즉시 중단 + 알림. 폭주(예: 무한 루프) 차단.

## 개발 프로세스

전체 프로세스·DoD 체크리스트: `docs/canonical/DEV_PROCESS.md`

- 먼저 검색 도구(`rg`, Grep)로 실제 코드/데이터 위치를 찾는다.
- 코드 수정 전에 원인과 기존 흐름을 먼저 확인한다.
- 작고 집중된 변경을 선호한다. 명시 요청 없이 큰 리팩터링은 하지 않는다.
- 기존에 동작하는 기능은 보존한다.
- 에이전트를 쓰면 이름과 맡긴 범위를 먼저 알린다.
- 시스템 의미·데이터 계약·UI 표시 기준이 바뀌면 관련 `docs/` 문서를 함께 갱신한다.
- 새 `docs/` 문서: 제목 아래 `> 역할:` + `> 대상:` 헤더 → `docs/DOC_MAP.md` 등록.
- 큰 기능은 phase/step으로 나눠 `phases/`에 상태를 남긴다.

규모 판단: 핫픽스(1-2파일, 계약 변경 없음)는 직접 수정 + `phases/_hotfix-log/`에 경량 로그 한 건 추가. 소형 이상은 `docs/canonical/DEV_PROCESS.md` 규모 분류 확인 후 phase 생성.

**기획서 동기화 (Design doc sync)** — 구현 도중 brief.md / requirements.md / sub-brief / 통합 brief 등 **기획 문서에 박혀 있지 않은 신규 내용** (신규 UI element, 신규 입력, 신규 catalog/schema field, 신규 사용자 명령, 신규 규칙, 신규 분기 등) 이 추가되면:

1. **반드시 해당 기획 문서를 먼저 업데이트**한다. 구현만 하고 기획서를 비워두지 않는다.
2. 기획 문서의 frontmatter 에 `last_updated_at: "YYYY-MM-DD"` 필드 추가/갱신.
3. 기획 문서 마지막에 `## Changelog` 섹션 (없으면 신설) 에 한 줄 추가: `- YYYY-MM-DD: 변경 내용 한 줄 (사유 + 영향 범위)`.
4. 변경이 acceptance criteria 에 영향을 주면 AC 본문도 함께 갱신 (해당 AC 항목 끝에 `(YYYY-MM-DD 추가)` 표기).
5. 신규 표시 텍스트/UI 라벨이 추가됐다면 localization/문구 등록도 같은 PR 에서 처리 (도메인에 따라 catalog/i18n 파일).
6. 추가 내용이 별도 phase 로 분리될 만큼 크면 새 phase 를 만들고 (소형 1~3 step), 기존 기획서에는 "후속 phase 분리: `{phase-name}` 참조" 한 줄만 추가.

이 정책은 구현 PR 의 DoD 에 포함된다. 구현 중 발견된 신규 항목이 기획서에 반영되지 않은 채 merge 되는 것을 차단한다.

**Step 진입 자동화** — 한 step 완료 후 다음 step 진입에 사용자 확인을 묻지 않는다. 다음 "차단 조건" 중 하나에 해당할 때만 멈추고 사용자에게 확인을 요청한다:

- **회귀 발견**: 사용자 보고 또는 에이전트 검증 실패로 회귀가 드러난 경우. 즉시 핫픽스 + `phases/_hotfix-log/` 기록 후 다음 step 진입 여부를 사용자에게 확인.
- **단정 불가능한 design decision**: agent가 sub-brief/tech-research/requirements에 박힌 결정만으로 단정할 수 없는 분기 옵션이 새로 떠오른 경우 (예: 디자인 선호, UX 결정, 비용/균형 결정).
- **core 가정 흔들림**: save/저장 계약·core 동작 경로·통합 진입 파일 본문 직접 수정 강요·Anti-pattern 위반 위험이 결정 단계에서 드러난 경우.
- **`qa_blocking: true` step**: phase index.json에 명시된 step. 해당 step만 일시 정지.
- **phase 종료 직전**: 마지막 step 완료 후 phase 끝 일괄 QA 보고를 위해 멈춤.

위 조건에 해당하지 않으면 step → step 이동은 자동 진행. 각 step 완료 시 한 줄 결과 보고 후 곧바로 다음 step에 진입한다.

**QA cadence (수동 QA 빈도)** — step 단위 사용자 QA가 개발 속도를 저해한다는 피드백에 따라 **phase 단위 일괄 QA**가 기본값:

- **기본 — phase 단위 일괄 QA**: 에이전트가 매 step에서 정적으로 검증 가능한 모든 항목(산출물 정합성·validator 통과·schema 파싱·코드 inspection 회귀 확인·헤드리스 빌드 등)을 끝까지 수행한 뒤 step status를 곧바로 `completed`로 전환한다. **`implemented_pending_manual_qa` 단계는 기본 흐름에서 생략한다.** 사용자 수동 QA는 phase 끝에서 한 번에 일괄 수행.
- **에이전트가 정적 확인 불가한 항목** (실행 후 시각/동작 확인, 입력 응답, 애니메이션·UI 렌더, 시간 의존 시나리오 등)은 step 단위에서 status 차단하지 않고, 해당 phase의 index.json `pending_manual_qa_scenarios` 배열에 시나리오 한 줄씩 누적한다. phase 끝 일괄 보고 시 이 배열을 그대로 사용자에게 노출.
- **phase 끝 일괄 보고 항목** (모든 phase 공통):
  1. phase 동안 변경된 파일 diff 요약 (카테고리별)
  2. step별 산출물·acceptance criteria cross-check 표
  3. `pending_manual_qa_scenarios` — 사용자가 직접 런타임에서 확인해야 할 시나리오 목록
  4. phase 도중 발견·핫픽스 처리된 회귀 (`_hotfix-log/` 링크)
  5. 다음 phase 진입 입력 (helper 명세·신규 식별 키·save 버전 bump 시점 등)
- **예외 — step 단위 QA 강제**: 사용자가 특정 step에 대해 명시적으로 "이 step 후 일시 정지" 요청을 했거나, 변경이 save 계약·core 경로·통합 진입 파일 본문 중 하나를 건드려 phase 끝까지 미루면 회귀 복구가 어려운 경우, 해당 step은 기존 `implemented_pending_manual_qa` → 사용자 QA → `completed` 룰을 따른다. 이 예외는 phase index.json의 step 항목에 `qa_blocking: true` 플래그로 명시.
- **회귀 발견 시**: phase 도중 사용자 보고 또는 에이전트 검증 실패로 회귀가 드러나면 즉시 핫픽스 후 `phases/_hotfix-log/`에 누적 기록하고 phase 끝 일괄 보고에 포함한다.

`AskUserQuestion`을 호출하는 슬래시 커맨드는 호출 직전 `docs/canonical/ask-user-question-guide.md`를 읽고 그 원칙을 따른다.

## 컨텍스트 압축 시 보존 항목

대화가 압축될 때 다음 정보는 요약본에 반드시 유지한다:

- 현재 작업 중인 phase 이름과 `active_step`
- `in_progress` 또는 `implemented_pending_manual_qa` 상태의 step 목록
- 사용자가 명시한 수동 QA 결과(pass/fail/pending) 및 차단 사유
- 현재 세션에서 수정한 파일 경로 목록과 각 파일의 변경 의도 한 줄
- 미해결로 남긴 사용자 질문·결정 대기 항목

압축 후 첫 응답 전에 `phases/index.json`과 해당 phase의 `index.json`을 다시 읽어 위 정보를 코드 기준으로 재확인한다.

## 흔한 작업 패턴

- 새 뉴스 소스 추가: `config/sources.yml`에 항목 등록(이름·url·type·tags) → fetcher 어댑터 선택(RSS / HTML / JSON API) → dry-run으로 1회 출력 점검 → `docs/DOC_MAP.md`·PRD 소스 목록 갱신.
- 요약 프롬프트 조정: `prompts/summarize.md` 수정 → `tests/fixtures/`의 샘플 기사로 회귀 비교 → 길이·포맷·금칙어 변경 시 PRD 발송 형식 섹션도 함께 수정.
- 발송 채널 추가: `dispatchers/`에 채널 어댑터 신설(`send(digest, recipients)` 인터페이스 준수) → GitHub Actions Secrets 등록 → ARCHITECTURE 모듈 ownership 표 갱신.
- 카테고리·필터 변경: `config/filters.yml`의 키워드·블랙리스트 수정 → 1주일 dry-run으로 누락·과잉 확인 → 직원 피드백 반영 후 적용.
- 일일 cron 시간 변경: `.github/workflows/daily.yml`의 cron 식(UTC) + ARCHITECTURE의 KST 발송 시각 동시 수정. KST↔UTC 환산을 cron 라인 위에 주석으로 남긴다.

## Anti-pattern

핵심 아키텍처 규칙을 직접 위반하는 코드 형태다. PR/diff에 이런 패턴이 보이면 거부한다.

### A. 표시 로직과 규칙 분리

```python
# 금지 — 발송 본문이 dedup·필터와 다른 정규화 사용
sent_url = article.url.split("?")[0]            # dispatcher 안에서 자체 정규화
already_seen = article.url in history           # history는 원본 url로 검사

# 권장 — 같은 helper를 dedup과 발송이 공유
canonical = url_helper.canonicalize(article.url)
already_seen = canonical in history
sent_url = canonical
```

### B. 통합 지점에 새 규칙 직접 추가

```python
# 금지 — run_daily.py 본문에 새 소스 fetch·필터·요약 로직을 누적
def main():
    rss1 = feedparser.parse(...)
    rss2 = feedparser.parse(...)
    html = requests.get(...).text
    filtered = [a for a in rss1 if "AI" in a.title]
    # ... 수백 줄 ...

# 권장 — run_daily.py는 위임만, 소스/필터/요약은 모듈 분리
def main():
    articles = fetchers.run_all(config.sources)
    filtered = filters.apply(articles, config.filters)
    digest  = summarizer.build(filtered)
    dispatcher.send(digest)
```

### C. 단일 try/except가 전체 발송을 막음

```python
# 금지 — 한 소스 실패가 전체 다이제스트를 비움
try:
    for src in sources:
        results.extend(fetch(src))
except Exception:
    return  # 그날 발송 0건

# 권장 — 소스 단위 격리 + 부분 성공
results, failures = [], []
for src in sources:
    try: results.extend(fetch(src))
    except Exception as e: failures.append((src.name, str(e)))
digest.meta["failed_sources"] = failures   # 본문에 노출, 발송은 계속
```

### D. 시크릿 하드코딩·로그 노출

```python
# 금지
ANTHROPIC_KEY = "sk-ant-..."                       # 코드에 평문
log.info(f"calling api with {credentials}")        # dict 통째로 로그

# 권장
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]   # Secrets/env에서만
log.info("calling api", extra={"key_prefix": ANTHROPIC_KEY[:6]})
```

### E. 요약만 보내고 원문 링크 누락

```python
# 금지 — LLM hallucination을 직원이 검증할 방법 없음
digest.append(f"- {summary_text}")

# 권장 — 요약은 보조, 원문 링크는 항상 함께
digest.append(f"- {summary_text}\n  원문: {article.url}  ({article.source})")
```
