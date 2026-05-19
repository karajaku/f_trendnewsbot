# {{PROJECT_NAME}} Architecture

> 역할: 현재 시스템 구조·모듈 ownership·데이터 흐름의 단일 권위 정의. 코드 위치를 좁힐 때 출발점.
> 대상: 새 모듈 추가 시, 의존 관계 추적 시, 새 합류자 온보딩 시.

작성일: {{TODAY}}
상태: draft (구현 진행과 함께 갱신)

---

## 런타임

- 언어: {{LANGUAGE}}
- 런타임: {{RUNTIME}}
- 타깃: {{TARGET_PLATFORM}}

## 폴더 구조

```
{새 프로젝트의 실제 폴더 구조를 그려넣는다}
```

## 통합 진입 지점

> 시스템이 시작되는 단일 진입 파일/함수. CLAUDE.md의 "통합 지점 비대화 금지" CRITICAL 규칙이 가리키는 곳.

- 진입 파일: `{path/to/entry.ext}`
- 진입 함수/이벤트: `{function or event name}`

## 모듈 ownership

| 모듈 | 위치 | 책임 | 의존 |
|---|---|---|---|
| {모듈 1} | `path/to/module1` | {한 줄 요약} | — |
| {모듈 2} | `path/to/module2` | {한 줄 요약} | 모듈 1 |

## 데이터 흐름

> 데이터가 어디서 들어와 어디로 흐르는지. 화살표 다이어그램 또는 텍스트.

```
{source} → {transform} → {storage} → {output}
```

## 저장 계약

- 정적 데이터(저장 제외): {위치, 형식}
- 인스턴스 state(저장 포함): {위치, 형식, 마이그레이션 정책}

## 성능 기준선

> 측정 단위와 현재 baseline. quota/실행시간/응답시간 등.

- {지표 1}: {현재 값}
- {지표 2}: {현재 값}

---

> 이 문서는 코드 변경 시 함께 갱신한다. DEV_PROCESS Stage 7 Canonical Sync 트리거 조건 참조.
