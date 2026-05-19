# Step 1: 부트스트랩 — pyproject·폴더·lib helpers

> 추적: [phases/01-mvp-daily-digest/README.md](README.md) → [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md)

## 읽을 파일

- [CLAUDE.md](../../CLAUDE.md) (특히 anti-pattern A, CRITICAL #2·#7)
- [docs/canonical/DEV_PROCESS.md](../../docs/canonical/DEV_PROCESS.md) Stage 6
- [docs/canonical/ARCHITECTURE.md](../../docs/canonical/ARCHITECTURE.md) §폴더 구조·§모듈 ownership
- [docs/features/daily_digest/daily_digest_v1-requirements.md](../../docs/features/daily_digest/daily_digest_v1-requirements.md) §3, §6-1~§6-5, §8, AC-7
- [docs/features/daily_digest/daily_digest_v1-tech-research.md](../../docs/features/daily_digest/daily_digest_v1-tech-research.md) §3-6 의존성, §2-1 helper anchor

## 작업 범위

V1 운영을 가능케 하는 최소 부트스트랩만. 도메인 로직은 다음 step에서.

- `pyproject.toml` — Python ≥ 3.12, requirements §3-6 의존성 6개 + dev extras 4개.
- `.env.example` — requirements §8 환경변수 6개 (예시값, 시크릿 평문 없음).
- 폴더 구조 생성:
  - `src/__init__.py`, `src/lib/__init__.py` (빈 패키지 마커)
  - `src/lib/url_helper.py` — `canonicalize(url) -> str` 단일 함수 (AC-4.1)
  - `src/lib/time_helper.py` — `now_kst()`, `to_kst_string(dt)`, `format_subject_date(dt)`, `parse_to_kst(s)` (AC-1.2, AC-2.3, AC-2.5의 KST 표기 단일 진실)
  - `src/lib/logging_setup.py` — 시크릿 마스킹 (`mask_key(s)`) 포함, dict 직접 로그 금지 helper (AC-7.2)
- `tests/` 디렉토리 + 빈 fixture 폴더 + `pytest.ini`
- `.gitignore`는 이미 존재 — 추가 패턴 필요 시 보강만

## 영향받는 데이터 정의 목록

없음 (config 파일은 step2)

## Acceptance Criteria

- [ ] `pyproject.toml`에 requirements §3-6 의존성 정확히 등록 (버전 핀 포함, optional dev extras)
- [ ] `lib/url_helper.canonicalize(url)` 가 ① 호스트 lowercase ② `utm_*`/`fbclid`/`gclid` 제거 ③ trailing slash 제거 ④ fragment 제거 4단계를 모두 수행 (AC-4.1)
- [ ] `lib/url_helper` unit test 5건 이상 (정상 URL, utm 포함, fragment 포함, trailing slash, 대문자 host)
- [ ] `lib/time_helper.now_kst()`가 `Asia/Seoul` zoneinfo 사용, tz-aware datetime 반환
- [ ] `lib/time_helper.format_subject_date(dt)` 가 "5월 19일 (월) 오전 7:30 KST" 형식 한국어 출력 (AC-1.2)
- [ ] `lib/time_helper` unit test 4건 이상 (now_kst tz check, format 정확성, naive datetime 거부, UTC 입력 KST 변환)
- [ ] `lib/logging_setup.mask_key("sk-ant-abc123...")` 가 "sk-ant" + "..." 반환 (시크릿 노출 방지)
- [ ] `.env.example`에 §8 6개 변수 + `CLAUDE_MODEL_ID` 표기, 실제 시크릿 값 없음
- [ ] `pytest tests/` 통과

## 금지사항

- fetchers·filters·summarizer·dispatcher 모듈 생성 금지 (각 step의 책임)
- `config/*.yml` 신설 금지 (step2)
- 시크릿 평문 또는 placeholder 값을 `.env.example`에 넣되 "real-looking" 값은 금지 (`<your_key_here>` 형식)
- `time_helper`에 KST 외 시간대 helper 추가 금지 (V1 KST 전용)

## 수동 테스트 절차

1. `pip install -e ".[dev]"` 로컬 설치 → 의존성 6개 + dev 4개 모두 설치되는지 확인
2. `pytest tests/` 통과 확인
3. `python -c "from src.lib import url_helper, time_helper, logging_setup; print(time_helper.format_subject_date(time_helper.now_kst()))"` 실행 → "오늘 날짜 KST" 한국어 형식 출력 확인

## 수동 QA Owner

`에이전트 정적 분석` — pytest와 import smoke test로 검증 가능. 사용자 검토는 phase 끝 일괄.

## 주 담당 에이전트

`tnb-implementer` — Python helper 코드 + pyproject 설정. data 정의 변경 없음.

## 회귀 위험

- 향후 step에서 `lib/url_helper` 시그니처를 우회한 자체 정규화 코드가 dispatcher·filter에 들어가는 패턴(CLAUDE.md anti-pattern A) — qa-reviewer가 grep으로 차단.
- `time_helper` 우회 KST 표기가 다이제스트 본문 어딘가에 isoformat()으로 노출되는 패턴 — pending_manual_qa_scenarios에 "본문 시각 표기 일관성 시각 확인" 추가.

## pending_manual_qa_scenarios 누적

- "본문 시각 표기 일관성 — 헤더·항목 발행시각·운영자 alert 시각이 모두 `5월 19일 ... KST` 한국어 형식인지 phase 끝 dry-run에서 시각 확인"
