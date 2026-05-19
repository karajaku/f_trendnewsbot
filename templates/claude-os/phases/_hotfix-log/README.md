# Hotfix Log

> 역할: phase를 생성하지 않는 핫픽스(1-2파일, 계약 변경 없음)의 경량 추적 로그.
> 대상: 핫픽스 완료 시 한 항목 추가. 회귀 추적·계약 변경 재분류 시 빠르게 훑는 용도.

## 사용 시점

`docs/canonical/DEV_PROCESS.md` "핫픽스 경로" 기준에 해당하는 변경(1-2파일, 단일 버그, 시스템 계약 변경 없음)을 끝낸 직후. phase 생성은 여전히 하지 않는다. 이 로그는 git log 위에 얹는 경량 인덱스다.

## 기록 규칙

- 파일 이름: `YYYY-MM-DD-{short-slug}.md`
- 하루에 여러 건이면 각각 별도 파일.
- 핫픽스 도중 시스템 계약 변경이 드러나면 **이 로그는 만들지 말고** 소형 이상 phase로 재분류한다(`docs/canonical/DEV_PROCESS.md` 규모 분류 참조).
- 이 폴더는 `phases/index.json`에 등록하지 않는다. phase가 아니다.

## 템플릿

신규 항목은 `_template.md`를 복사해서 만든다.

## 정리 정책

분기마다 6개월 이상 지난 항목은 `docs/history/hotfix-log/{year}/`로 이동해서 보관한다. 활성 폴더가 비대해지지 않게 한다.
