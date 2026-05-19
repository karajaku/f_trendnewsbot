"""필터 파이프라인 — timewindow · keyword · category · dedup.

run_daily.py 통합 진입은 `pipeline.apply` 만 호출하고 본 패키지의 다른 모듈은
파이프라인 내부에서만 사용한다 (anti-pattern B — 통합 지점 본문 누적 회피).

CRITICAL #2 (helper 공유):
- URL 정규화는 dedup 단계에서 `lib.url_helper.canonicalize` 한 곳에서만 호출.
  Article 생성 단계에서 이미 canonical 통과를 강제 (`src.fetchers.base.Article.__post_init__`).
  filters 안에서 자체 URL 자르기는 0줄.
- 발송 본문(summarizer/render)·발송 이력(history)·dedup 이 같은 canonical_url 을 공유한다.
"""

from __future__ import annotations

from .base import Filter
from .pipeline import apply as apply_pipeline

__all__ = ["Filter", "apply_pipeline"]
