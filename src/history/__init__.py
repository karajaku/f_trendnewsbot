"""history 패키지 — 발송 이력 영속화 + dedup 입력 단일 진실 (CRITICAL #8).

공개 표면:

- `SentItem`, `SentRecord` — `history/sent.jsonl` 한 줄 1 record 의 dataclass (requirements §6-4).
- `History` — load 결과 (dedup 입력 형태).
- `HistoryBackend` — Protocol (load/record).
- `LocalFileBackend` — 로컬 파일 backend (`history/sent.jsonl`).

V1 운영은 step7 의 GitHub Actions workflow 가 `actions/download-artifact` /
`actions/upload-artifact` 로 같은 `sent.jsonl` 파일을 옮긴다. 본 step 은 인터페이스 +
로컬 file backend 까지 (artifact download/upload 코드는 step7).
"""

from __future__ import annotations

from .schema import SentItem, SentRecord
from .store import History, HistoryBackend, LocalFileBackend

__all__ = [
    "SentItem",
    "SentRecord",
    "History",
    "HistoryBackend",
    "LocalFileBackend",
]
