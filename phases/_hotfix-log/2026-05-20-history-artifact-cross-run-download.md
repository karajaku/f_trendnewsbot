# 발송 이력 아티팩트가 run 간 이어지지 않음 — download-artifact@v4 cross-run 미설정

날짜: 2026-05-20
규모: 핫픽스 (1파일 — `.github/workflows/daily.yml`, 계약 변경 없음)

## 증상

phase 03 dry-run 테스트(run `26145620879`) 로그 annotation:

> `Unable to download artifact(s): Artifact not found for name: digest-history`

매 run 의 "Download previous history artifact" 스텝이 실패하고 있었다. `continue-on-error: true` 라 job 은 통과하지만, 결과적으로 매 run 이 **빈 발송 이력**으로 시작한다.

## 원인

`.github/workflows/daily.yml` 의 다운로드 스텝이 `actions/download-artifact@v4` 를 `run-id` 없이 사용했다. **v4 부터 download-artifact 는 `run-id` 미지정 시 "현재 run" 의 아티팩트만 조회**한다(v3 와 달라진 점). 워크플로의 의도는 *직전 run* 의 `digest-history` 를 받아 오는 것인데, v4 의미상 그것은 불가능하다.

`digest-history` 아티팩트는 매 run 정상 업로드된다(저장소에 13개 존재, 미만료). 그러나 다운로드는 항상 "현재 run 에 없음"으로 실패 → `continue-on-error` 가 조용히 삼킴 → `history/sent.jsonl` 부재 → `history.store.LocalFileBackend.load` 가 빈 History 반환.

`history/sent.jsonl` 은 `.gitignore` 대상(`.gitignore:46-47`)이라 artifact 가 유일한 영속 매체다. 따라서 cross-day dedup(CLAUDE.md CRITICAL #8 — 어제 보낸 기사 오늘 재발송 금지)이 **phase 01 이래로 실제 동작하지 않았다**. phase 03·02 와 무관한 잠복 버그.

## 변경

- `.github/workflows/daily.yml` `permissions` — `actions: read` 추가. 이전 run 조회·cross-run 아티팩트 다운로드에 필요(워크플로가 `permissions` 를 명시하면 나열된 권한만 부여됨).
- `Find last successful run id` 스텝 신설 — `gh run list --workflow daily.yml --status success --limit 1` 로 직전 성공 run id 를 step output(`lastrun.id`)으로 노출. API 실패 시 `|| echo ""` 로 빈 id.
- `Download previous history artifact` 스텝 — `run-id: ${{ steps.lastrun.outputs.id }}` + `github-token` 추가(v4 의 cross-run 다운로드 필수 입력), `if: steps.lastrun.outputs.id != ''` 가드로 첫 실행 fresh-start 유지.

## 수동 확인

- [ ] 머지 후 `workflow_dispatch` 1회 → "Download previous history artifact" 스텝이 ✓ 이고 "Artifact not found" annotation 이 사라졌는지 로그 확인
- [ ] 연속 2회 dry-run → 두 번째 다이제스트에서 첫 번째 발송 항목이 dedup 되어 빠지는지 (cross-run 이력 적용 확인)
- [ ] `git diff --check` 통과

## 회귀 위험

- **첫 실행(직전 성공 run 없음)**: `if` 가드로 다운로드 스텝 skip → 기존 fresh-start 동작 그대로.
- **`gh run list` API 실패**: `|| echo ""` 로 빈 id → 다운로드 skip → fresh-start. job 실패 없음.
- **dry-run 의 digest-history 도 success run 으로 선택됨**: `run_daily.py` 는 dry-run 도 `backend.record()` 로 이력을 남기므로 의도된 동작 — dry-run 발송분도 정상적으로 dedup 대상.
- **직전 성공 run 의 아티팩트 만료(retention 90일)**: dedup 창 7일 이내라 정상 운영에선 무관. 만료 시 download `continue-on-error` 로 fresh-start fallback.
- 본 수정은 dedup AC·CRITICAL #8 을 "실제로 충족"시키는 것 — AC 문구 변경 없음, 기획서 동기화 불요.

## 계약 변경 재분류 체크

- [x] 데이터 정의 파일 최상위 필드 변경 없음 (`history/sent.jsonl` 스키마 무변경)
- [x] 공개 함수 시그니처 변경 없음 (코드 무변경, 워크플로 YAML 만)
- [x] save/저장 구조 변경 없음 — 저장 매체(artifact)·스키마 동일, 깨진 다운로드 경로만 수정
- [x] 모듈 경계 변경 없음
