# Windows 환경 tzdata 의존성 추가

날짜: 2026-05-19
규모: 핫픽스 (1파일, 계약 변경 없음)

## 증상

phase 01 step1 검증 중 `pytest tests/` 가 Windows 환경에서 다음 에러로 collection 실패:

```
zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key Asia/Seoul'
```

`tests/test_time_helper.py`·`tests/test_logging_setup.py` 2개 파일이 import 단계에서 raise.

## 원인

Python `zoneinfo` 표준 라이브러리는 시스템 IANA tzdata 를 의존한다. Linux·macOS 는 시스템에 기본 db 가 있어 동작하지만, Windows 는 시스템 db 가 없어 PyPI `tzdata` 패키지를 별도로 설치해야 한다.

step1.md AC §3-6 의존성 목록 작성 시 사용자 환경이 Windows 라는 점을 충분히 고려하지 못해 누락. tech-research §3-1 에서도 `feedparser`·`requests`·`bs4` 만 명시했고 zoneinfo 보강용 패키지는 빠짐.

## 변경

- `pyproject.toml:23` — platform conditional dependency 추가:
  ```toml
  "tzdata>=2024.2; sys_platform == 'win32'",
  ```
  Linux/macOS 는 시스템 db 사용, Windows 만 PyPI 패키지를 끌어쓴다. 다른 OS 에는 무영향.

## 수동 확인

- [x] `pip install -e ".[dev]"` 재실행으로 `tzdata-2026.2` 설치 확인
- [x] `pytest tests/ -v` 14건 모두 PASS (실측 0.07s)
- [x] `PYTHONIOENCODING=utf-8 python -c "..."` smoke test 출력 `5월 19일 (화) 오후 2:12 KST` 정상
- [x] `git diff --check` 통과 — 공백 오류 없음

## 회귀 위험

없음. `tzdata` 는 IANA TZ DB 공식 미러를 그대로 제공하는 표준 패키지로, Python `zoneinfo` 모듈이 자동으로 인식. macOS·Linux 환경에서 평가하면 pip 가 install spec 의 `sys_platform == 'win32'` marker 를 보고 설치 자체를 건너뜀.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음
- [x] 공개 함수 시그니처 변경 없음
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음

위 4개 모두 OK. 핫픽스 분류 유지. 단 의존성 명세는 변경이라 `daily_digest_v1-requirements.md` §1 의존 시스템 표·`daily_digest_v1-tech-research.md` §3-6 의존성 목록에 한 줄씩 동기화 — 별도 commit 또는 본 phase step8 canonical sync 시 함께 처리.

## 관련 phase·step

phase 01 step1 (부트스트랩) 의 dry-run 검증 중 발견. step1 산출물 자체는 시그니처·테스트·AC 모두 통과. 본 핫픽스 적용 후 step1 status 는 `completed` 유지.
