# Step 2: config 로딩 — sources/filters/recipients 스키마와 로더

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) §6-1·§6-2·§6-3

## 읽을 파일

- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) §6-1 sources.yml, §6-2 filters.yml, §6-3 recipients.yml
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §2-3 회사 키워드 시드
- [docs/팜보스_회사소개.md](../../docs/팜보스_회사소개.md) §2-3 주요 산지·법인명 (filters.yml 시드 출처)
- [.gitignore](../../.gitignore) — `config/recipients.yml` 차단 확인
- step1 산출물: `src/lib/logging_setup.py` (시크릿 마스킹 helper)

## 작업 범위

- `config/sources.yml` — 초기 시드 12~18개 소스 등록 (카테고리당 4~6개). 사용자 일괄 검토에서 추가·제거 가능.
- `config/filters.yml` — requirements §6-2 그대로. `farmboss_keyword` 12개 시드는 동결.
- `config/recipients.example.yml` — git tracked 예시 파일 (실제 명단 없음, 운영자 1명 + 직원 placeholder)
- `config/recipients.yml` — `.gitignore`로 차단, 운영 시점 주입. 본 step에서는 생성 안 함.
- `src/config/__init__.py`, `src/config/loader.py` — 3 yml 로더 + dataclass 정의
  - `Source` (id, name, url, type, category, enabled, tags, time_window_hours)
  - `CategoryFilter` (label, must_match_any, exclude_any, order)
  - `GlobalFilters` (time_window_hours, fuzzy_title_threshold, dedup_days)
  - `Recipient` (name, email, role, suppress)
  - `OpsAlertRecipient` (name, email)
- 로더는 schema validation 실패 시 명확한 에러 메시지 + 파일·라인 표기

## 영향받는 데이터 정의 목록

- `config/sources.yml` — 신규 (정적, git tracked)
- `config/filters.yml` — 신규 (정적, git tracked)
- `config/recipients.example.yml` — 신규 (정적, git tracked, 예시만)
- `config/recipients.yml` — 신규 정의 (시크릿, git ignore, 운영 시점 생성)

## Acceptance Criteria

- [ ] `config/sources.yml`에 카테고리당 4~6개씩 총 12~18개 소스 등록 (id는 `^[a-z][a-z0-9_]*$`, 중복 없음)
- [ ] AI 트렌드 카테고리에 Anthropic Blog·OpenAI Blog·Google DeepMind Blog·TLDR AI·Hacker News 중 최소 4개
- [ ] 농산물·유통 카테고리에 농민신문·한국농어민신문·식품음료신문·aT 유통정보·GS리테일 IR 중 최소 4개
- [ ] 팜보스 관심 키워드 카테고리에 농민신문(농촌경제 섹션)·식품음료신문·청도군·경산시 등 산지 관련 4개
- [ ] `config/filters.yml`이 requirements §6-2와 완전 일치 (farmboss_keyword 12개 시드 포함)
- [ ] `config/recipients.example.yml`에 운영자 1명 + 직원 2명 placeholder (실제 도메인 없음, `@example.com`)
- [ ] `src/config/loader.py`가 3 yml을 dataclass로 파싱, schema 위반 시 `ConfigError(path, line, reason)` raise
- [ ] `Source.id` 중복 검출 (사람 실수 방지)
- [ ] unit test 8건 이상: 정상 로드 / id 중복 / 잘못된 type / 잘못된 category / suppress=true 제외 / yml 파일 없음 / 잘못된 yml 문법 / 필수 필드 누락

## 금지사항

- 실제 직원·운영자 이메일을 `recipients.example.yml`에 넣기 금지 (모두 `@example.com`)
- `recipients.yml`을 git에 add 금지 (`.gitignore` 의존)
- fetchers·filters 모듈 생성 금지 (다음 step)
- `Source.category`에 requirements §6-2 정의한 3개(`ai_trend`/`agri_distribution`/`farmboss_keyword`) 외 값 허용 금지
- `farmboss_keyword` must_match_any를 12개에서 임의 변경 금지 (Stage 3 동결 — phase 외 작업)

## 수동 테스트 절차

1. `python -c "from src.config.loader import load_all; r = load_all(); print(len(r.sources), len(r.filters.categories), r.global_filters)"` → 소스 12~18, 카테고리 3, GlobalFilters dataclass 출력
2. `config/sources.yml`에 일부러 id 중복 추가 → `pytest tests/test_config.py` → `ConfigError` 메시지에 라인·중복 id 노출 확인
3. `config/recipients.yml`을 git status 확인 → tracked 아님 (`.gitignore` 작동)

## 수동 QA Owner

`에이전트 정적 분석` — yml schema validation + pytest 가능. 직원 명단 보안은 사용자 phase 끝 검토.

## 주 담당 에이전트

`tnb-data-steward` — yml schema와 dataclass 정의, validator는 본 에이전트 책임.

## 회귀 위험

- `Source.id` 한 번 정해진 값을 변경하면 history sent.jsonl의 `source_id` 매칭이 끊김 (requirements §6-1) — qa-reviewer가 변경 시 경고.
- `recipients.yml`이 실수로 git에 들어가면 직원 이메일 유출. step7에서 git status 검증 절차 포함.

## pending_manual_qa_scenarios 누적

- "filters.yml의 `farmboss_keyword` 시드 12개가 회사 톤·실제 산지에 맞는지 사용자 일괄 검토 시 확인 (1주일 dry-run 후 보강 가능)"
- "sources.yml의 12~18개 소스 URL이 실제 fetcher dry-run에서 정상 응답하는지 step8에서 확인"
