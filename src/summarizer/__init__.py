"""summarizer 패키지 — Anthropic Claude 단일 호출 + render(HTML+텔레그램) 단일 진실.

CRITICAL #6 (요약 옆 원문 링크) · CRITICAL #9 (API quota hard cap) 의 코드 측 방어선.

서브모듈:
- `quota`: 일일 토큰·호출 cap 추적 (`QuotaTracker`, `QuotaExceededError`).
- `client`: Anthropic SDK wrapper + Prompt caching system 영역 + JSON schema validation.
- `render`: 애플 감성 v3 HTML + 텔레그램 인덱스 동시 생성.
"""
