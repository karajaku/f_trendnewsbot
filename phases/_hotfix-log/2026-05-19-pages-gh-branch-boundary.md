# Pages 배포 boundary 변경 — master `/docs` → `gh-pages` branch root

날짜: 2026-05-19
규모: 핫픽스 (1 코드 파일 + tests + 5 문서 동기화, 시스템 계약 보강이지만 사용자 합의 후 ADR-003 §결정 갱신으로 정리)

## 증상

step6 구현 후 GitHub Desktop publish 가이드 단계에서 발견 — ADR-003 §3-3-b 의 "Pages source = master `/docs` 폴더" 설정을 그대로 적용하면 master 의 회사 사내 문서가 외부 공개됨:

- `docs/팜보스_회사소개.md` → 회사 정체성·법인 구조·매출 외부 공개
- `docs/canonical/PRD.md` → MVP 사업 전략 외부 공개
- `docs/features/daily_digest/*.md` → brief·requirements·design-review 모두 외부 공개
- `docs/_extracted/` → 직원 업무 가이드·조직 운영 규칙 외부 공개

본문이 외부 뉴스 큐레이션이라 "Pages 본문 자체는 안전" 가정했지만, **`/docs` root 설정 부작용**으로 다이제스트 HTML 외 다른 `docs/*` 파일이 모두 같은 base URL 하위에 노출됨.

## 원인

ADR-003 §결정 작성 시 boundary 분리 검토 부족. dispatcher 가 `repo_root/docs/digest/` 에 commit 하는 흐름을 사용자가 검토 없이 따라가다가, Pages 활성화 시점에 폴더 단위 설정의 결과를 인지.

## 변경

- `src/dispatchers/pages_publish.py:전체` — master `docs/digest/` 대신 `git worktree` 로 임시 디렉토리에 `gh-pages` branch checkout → `digest/YYYY-MM-DD.html` 작성 → commit → `push origin gh-pages` → finally cleanup. 4단계 라벨(write/commit/push/verify) 유지.
- `tests/test_dispatchers.py:Pages 테스트 4건 갱신 + 1건 신규` — worktree-based 흐름 mock + `git worktree add gh-pages` 실패(=운영자 초기 셋업 미진행) 케이스 추가.
- `docs/canonical/ADR.md:ADR-003` — §결정 본문 갱신 (gh-pages branch 채택 + 운영자 초기 셋업 1회 가이드), §대안 F 신규 추가 (`/docs` root 옵션 reject 사유 기록).
- `docs/features/daily_digest/daily_digest_v1-brief.md:§2-2` — 표면 B 안내 한 줄 추가, Changelog 갱신.
- `docs/features/daily_digest/daily_digest_v1-requirements.md:AC-2.8·AC-6.6` — gh-pages branch 명시, Changelog 갱신.
- `docs/features/daily_digest/daily_digest_v1-tech-research.md:§3-3-b` — 활성화 row + 게시 흐름 코드 블록 갱신, Changelog 갱신.
- `phases/01-mvp-daily-digest/step6.md:§Pages publish` — worktree 흐름 명시, 테스트 hook 한 줄(`git_runner`/`http_checker`/`tmp_factory`) 추가, 운영자 초기 셋업 안내 한 줄 추가.
- `phases/01-mvp-daily-digest/step7.md:§GitHub Pages 활성화` — orphan branch 셋업 6단계 + Source `gh-pages` root 로 갱신.

## 수동 확인

- [x] `pytest tests/` 99 PASS (Pages 5 + Telegram 7 + OpsAlert 3 + 다른 모듈 84). 회귀 0.
- [x] `git_runner` mock 으로 worktree add → ls-files → add → commit → push origin gh-pages → worktree remove 순서 검증.
- [x] 운영자 초기 셋업 미진행 (gh-pages branch 없음) → `PagesPublishError(stage="write")` + "운영자 초기 셋업 (orphan branch push) 필요할 수 있음" 메시지 케이스 신규 테스트 추가.
- [x] master branch 의 `docs/digest/` 미생성 — test 에서 명시적 단언.

## 회귀 위험

- **medium**: `run_daily.py` (step7 미구현) 통합 진입점이 publish 결과 외에 push branch 정보를 가정하는 경우. `pages_publish.publish` 는 `final_url` 만 반환 — 외부 의존 없음.
- **low (운영)**: 운영자 초기 셋업 (`git checkout --orphan gh-pages → ... → git push origin gh-pages`) 안 된 환경에서는 모든 발송이 write 단계 실패. step7 secrets_setup.md 가이드로 사전 셋업 강제.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일에 최상위 필드 변경 없음 (sent.jsonl·sources.yml·filters.yml 무변경)
- [x] 공개 함수 시그니처 변경 없음 — `publish()` 매개변수 4개 그대로, `tmp_factory` 키워드 hook 만 신규 (테스트 격리용, 기본값 `tempfile.mkdtemp`)
- [x] save/저장 구조 변경 없음
- [x] 모듈 경계 변경 없음 — Pages publish 가 master 의 다른 폴더를 건드리지 않게 된 것 (boundary 강화).

4개 모두 OK — 핫픽스 분류 유지. 단 ADR §결정 본문 + 5 기획서 동기화는 정상적 design doc sync 흐름.

## 관련 phase·step

phase 01 step6 (dispatchers) 의 구현 후속. step6 status 는 `completed` 유지 — 본 변경은 같은 step 의 핫픽스. step7 (secrets_setup·workflow) 에서 운영자 초기 셋업 가이드가 가이드 본문으로 흡수.
