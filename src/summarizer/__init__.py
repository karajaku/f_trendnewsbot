"""summarizer 패키지 — Google Gemini 2.0 Flash 단일 호출 + render(HTML+텔레그램) 단일 진실.

CRITICAL #6 (요약 옆 원문 링크) · CRITICAL #9 (API quota hard cap) 의 코드 측 방어선.
ADR-004 (2026-05-19): Anthropic Claude Haiku 4.5 → Gemini 2.0 Flash swap. SDK 는 google-genai.

서브모듈:
- `quota`: 일일 토큰·호출 cap 추적 (`QuotaTracker`, `QuotaExceededError`).
- `client`: google-genai SDK wrapper + JSON mode (response_schema) + ResourceExhausted 매핑.
- `render`: 애플 감성 v3 HTML + 텔레그램 인덱스 동시 생성.
"""
