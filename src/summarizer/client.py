"""Google Gemini 2.0 Flash SDK wrapper — 단일 호출(점수+요약+회사 영향+카테고리 핵심).

CRITICAL #4 (시크릿 평문 노출 금지) · CRITICAL #9 (quota hard cap) 의 코드 측 방어선.

설계 (ADR-004, 2026-05-19 — Anthropic Claude Haiku 4.5 → Gemini 2.0 Flash swap):
    - `prompts/summarize.md` 본문을 `system_instruction` 으로 전달. 회사 컨텍스트가 길지만
      Gemini 무료 tier 라 prompt caching 미사용 (V1.1 에서 Context Caching API 검토).
    - user contents 는 카테고리별 articles 를 JSON 으로 직렬화. canonical_url 을 `id` 로
      전달 — 응답 `items[].id` 와 1:1 매칭.
    - 응답은 단일 JSON object — Gemini JSON mode (`response_mime_type="application/json"`
      + `response_schema`) 로 schema 강제. markdown fence(```json ... ```) 감싸짐은 거의
      없지만 방어선으로 헬퍼 유지.
    - schema 위반 항목은 폐기 + `dropped_items` 누적 — 전체 응답 폐기는 금지(부분 성공).
    - 토큰 누적은 `QuotaTracker.check_and_record` 1회 호출 — cap 초과 시 raise.
    - rate limit / quota 초과 (`google.genai.errors.ClientError` 4xx 중 429) → 우리
      `QuotaExceededError` 로 매핑 → run_daily.py 의 exit 2 분기에 도달 (AC-5.3).

본 모듈은 dispatcher 로직(Pages publish · 텔레그램 send)을 호출하지 않는다 — step6.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from src.fetchers.base import Article
from src.lib.logging_setup import mask_key

from .quota import QuotaExceededError, QuotaTracker

logger = logging.getLogger(__name__)

# requirements §8 — env var 미지정 시 default.
# ADR-005 (2026-05-19): gemini-2.0-flash 가 신규 사용자에게 deprecated 됨에 따라
# gemini-2.5-flash 로 swap. provider/SDK/JSON mode 동일.
DEFAULT_MODEL: str = "gemini-2.5-flash"

# Gemini max_output_tokens — output cap 20k 이내 (AC-5.5).
# 2026-05-19 핫픽스 (gemini-2.5-flash thinking-mode truncate 회귀):
# 4096 → 8192. Gemini 2.5 라인은 thinking-mode 가 default 활성이며 thinking
# 토큰이 max_output_tokens 의 일부를 차지해 실제 JSON 응답이 잘렸다. 본 default
# 상향 + ThinkingConfig(thinking_budget=0) 비활성화 동시 적용.
DEFAULT_MAX_OUTPUT_TOKENS: int = 8192

# 카테고리 3종 — filters/pipeline.CATEGORIES 와 같은 단일 진실(렌더와 공유).
CATEGORIES: tuple[str, ...] = ("ai_trend", "agri_distribution", "farmboss_keyword")

# 응답이 markdown fence 로 감싸질 때 본문 추출 (Gemini JSON mode 가 대부분 막지만 방어선).
_FENCE_PATTERN = re.compile(
    r"```(?:json)?\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)

# Gemini JSON mode response_schema — items[].{id,score,summary,company_impact} +
# category_headlines.{ai_trend,agri_distribution,farmboss_keyword}.
_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "score": {"type": "INTEGER"},
                    "summary": {"type": "STRING"},
                    "company_impact": {"type": "STRING"},
                },
                "required": ["id", "score", "summary", "company_impact"],
            },
        },
        "category_headlines": {
            "type": "OBJECT",
            "properties": {
                "ai_trend": {"type": "STRING"},
                "agri_distribution": {"type": "STRING"},
                "farmboss_keyword": {"type": "STRING"},
            },
        },
    },
    "required": ["items", "category_headlines"],
}


@dataclass(frozen=True)
class ItemAnalysis:
    """LLM 이 반환한 기사 1건 분석 — `render.RenderedItem` 의 입력.

    Attributes:
        article_id: canonical_url (입력 Article 의 canonical_url 과 동일).
        score: 1~10 (회사 직접 영향 기준, prompt §6-5).
        summary: 한국어 2 문장 이내 요약.
        company_impact: 사업 영역 외면 빈 문자열 — 정상값. 폐기 사유 아님 (AC-2.5).
    """

    article_id: str
    score: int
    summary: str
    company_impact: str


@dataclass(frozen=True)
class SummarizeResult:
    """`SummarizerClient.summarize` 의 반환 — render 입력.

    Attributes:
        items: ItemAnalysis 리스트 (입력 Article 일부 폐기 가능 — schema 위반 시).
        category_headlines: 카테고리 3종 키 보장 (빈 문자열 허용).
        dropped_items: schema 위반으로 폐기된 항목 수 (메타에 노출).
        tokens_in: 누적된 입력 토큰 수.
        tokens_out: 누적된 출력 토큰 수.
    """

    items: list[ItemAnalysis]
    category_headlines: dict[str, str]
    dropped_items: int
    tokens_in: int
    tokens_out: int


def load_system_prompt(root: Path | None = None) -> str:
    """`prompts/summarize.md` 본문을 system 영역용으로 읽어 반환.

    Args:
        root: 리포 루트. 미지정 시 본 모듈 경로로 추정.

    Returns:
        파일 본문 (UTF-8, 마지막 newline 보존).
    """
    base = root or Path(__file__).resolve().parent.parent.parent
    path = base / "prompts" / "summarize.md"
    return path.read_text(encoding="utf-8")


def _strip_markdown_fence(text: str) -> str:
    """모델 응답이 ```json ... ``` 로 감싸졌으면 안쪽만 추출. 없으면 원문 반환.

    Gemini JSON mode 가 fence 없는 raw JSON 을 보장하지만, 방어선으로 유지.
    """
    if not isinstance(text, str):
        return text  # type: ignore[return-value]
    match = _FENCE_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _serialize_articles_for_user_message(
    by_category: dict[str, list[Article]],
) -> str:
    """카테고리별 articles 를 LLM user 메시지용 JSON 으로 직렬화.

    canonical_url 을 `id` 키로 전달 — 응답 `items[].id` 매칭의 단일 진실.
    """
    payload: dict[str, list[dict[str, str]]] = {}
    for cat in CATEGORIES:
        payload[cat] = []
        for art in by_category.get(cat, []):
            payload[cat].append(
                {
                    "id": art.canonical_url,
                    "title": art.title,
                    "source_name": art.source_name,
                    "published_at_kst": art.published_at_kst.isoformat(),
                    "snippet": art.snippet,
                }
            )
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _parse_response_json(raw_text: str) -> dict[str, Any]:
    """응답 텍스트를 JSON dict 로 파싱. fence strip 후 시도.

    Raises:
        RuntimeError — 전체 응답 JSON 파싱 실패 (빈 응답 포함). 진단을 위해 응답
            앞·뒤 snippet 과 raw_len 을 메시지에 포함 (2026-05-19 핫픽스).
    """
    if not raw_text or not raw_text.strip():
        raise RuntimeError("Gemini 응답이 비어있습니다.")
    cleaned = _strip_markdown_fence(raw_text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        snippet_head = cleaned[:200]
        snippet_tail = cleaned[-200:] if len(cleaned) > 400 else ""
        raise RuntimeError(
            f"Gemini 응답 JSON 파싱 실패: {e} (raw_len={len(cleaned)}, "
            f"head={snippet_head!r} tail={snippet_tail!r})"
        ) from e
    if not isinstance(parsed, dict):
        raise RuntimeError(
            f"Gemini 응답 최상위가 object 가 아닙니다 (got {type(parsed).__name__})."
        )
    return parsed


def _validate_and_filter_items(
    raw_items: Any,
    valid_ids: set[str],
) -> tuple[list[ItemAnalysis], int]:
    """raw `items[]` 를 schema 검증 — 위반 항목은 폐기 + dropped 카운트.

    검증:
        - dict 형태 + id/score/summary/company_impact 필드 존재.
        - score 는 1~10 정수 (bool 제외).
        - summary 는 비어있지 않은 문자열.
        - company_impact 는 문자열 (빈 문자열 정상).
        - id 가 valid_ids(canonical_url) 에 속해야 함.

    Returns:
        (valid_items, dropped_count).
    """
    validated: list[ItemAnalysis] = []
    dropped = 0

    if not isinstance(raw_items, list):
        logger.warning(
            "summarizer — items[] 가 list 가 아님 (got %s); 전체 폐기.",
            type(raw_items).__name__,
        )
        return validated, dropped

    seen_ids: set[str] = set()
    for idx, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            logger.warning("summarizer — items[%d] 가 dict 가 아님; 폐기.", idx)
            dropped += 1
            continue

        if not all(k in raw for k in ("id", "score", "summary", "company_impact")):
            missing = [k for k in ("id", "score", "summary", "company_impact") if k not in raw]
            logger.warning(
                "summarizer — items[%d] 필수 필드 누락: %s; 폐기.",
                idx, missing,
            )
            dropped += 1
            continue

        article_id = raw["id"]
        score = raw["score"]
        summary = raw["summary"]
        company_impact = raw["company_impact"]

        if not isinstance(article_id, str) or article_id not in valid_ids:
            logger.warning(
                "summarizer — items[%d].id=%r 가 입력 article id 와 매칭되지 않음; 폐기.",
                idx, article_id,
            )
            dropped += 1
            continue

        if article_id in seen_ids:
            logger.warning(
                "summarizer — items[%d].id=%r 가 중복; 폐기.",
                idx, article_id,
            )
            dropped += 1
            continue

        if not isinstance(score, int) or isinstance(score, bool):
            logger.warning(
                "summarizer — items[%d].score 가 int 가 아님 (got %r); 폐기.",
                idx, score,
            )
            dropped += 1
            continue
        if not (1 <= score <= 10):
            logger.warning(
                "summarizer — items[%d].score=%d 범위 밖 (1~10); 폐기.",
                idx, score,
            )
            dropped += 1
            continue

        if not isinstance(summary, str) or not summary.strip():
            logger.warning(
                "summarizer — items[%d].summary 가 비어있음; 폐기.",
                idx,
            )
            dropped += 1
            continue

        if not isinstance(company_impact, str):
            # 빈 문자열은 OK, None / 숫자 등은 폐기.
            logger.warning(
                "summarizer — items[%d].company_impact 가 문자열이 아님 (got %s); 폐기.",
                idx, type(company_impact).__name__,
            )
            dropped += 1
            continue

        seen_ids.add(article_id)
        validated.append(
            ItemAnalysis(
                article_id=article_id,
                score=score,
                summary=summary.strip(),
                company_impact=company_impact.strip(),
            )
        )

    return validated, dropped


def _validate_category_headlines(raw_headlines: Any) -> dict[str, str]:
    """raw `category_headlines` 를 3 카테고리 키 보장 형태로 정규화.

    누락된 카테고리 키는 빈 문자열로 보충 — 렌더가 빈 문자열일 때 표시 생략(AC-2.12).
    """
    out: dict[str, str] = {c: "" for c in CATEGORIES}
    if not isinstance(raw_headlines, dict):
        if raw_headlines is not None:
            logger.warning(
                "summarizer — category_headlines 가 dict 가 아님 (got %s); 빈 문자열로 대체.",
                type(raw_headlines).__name__,
            )
        return out
    for cat in CATEGORIES:
        v = raw_headlines.get(cat, "")
        if isinstance(v, str):
            out[cat] = v.strip()
        else:
            logger.warning(
                "summarizer — category_headlines[%s] 가 문자열이 아님 (got %s); 빈 문자열 사용.",
                cat, type(v).__name__,
            )
    return out


def _is_quota_or_rate_limit_error(exc: Exception) -> bool:
    """Gemini API 의 quota / rate limit 에러 판별.

    google.genai.errors.ClientError 의 code/status 4xx 중 429 (rate limit)
    또는 RESOURCE_EXHAUSTED 상태. message 본문에 "quota" / "rate limit" 키워드 fallback.
    """
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code == 429:
        return True
    status = getattr(exc, "status", None)
    if isinstance(status, str) and "RESOURCE_EXHAUSTED" in status.upper():
        return True
    message = str(exc).lower()
    if "quota" in message or "rate limit" in message or "resource_exhausted" in message:
        return True
    return False


class SummarizerClient:
    """Google Gemini wrapper — 단일 호출에 점수·요약·회사 영향·카테고리 핵심 동시 출력.

    Args:
        api_key: Gemini API key. mask_key 통해 prefix 만 로그.
        model: Gemini model ID. 기본 `DEFAULT_MODEL` (env `GEMINI_MODEL_ID` 로 override 는
            상위 호출자가 처리 — 본 클래스는 받은 값 사용).
        quota: 일일 cap 추적. 미지정 시 새 인스턴스 생성 (테스트·dry-run 용도).
        max_output_tokens: 응답 최대 토큰. 기본 4096.

    Notes:
        - Gemini JSON mode 로 `response_schema` 강제 — Anthropic 의 prompt caching
          (`cache_control: ephemeral`) 은 제거 (ADR-004). V1.1 에서 Context Caching API
          (`client.caches.create`) 검토.
        - 본 클래스는 dispatcher 를 호출하지 않는다 (step6 dispatcher 가 별도 모듈).
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        quota: QuotaTracker | None = None,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key 는 비어있지 않은 문자열이어야 합니다.")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model 은 비어있지 않은 문자열이어야 합니다.")
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens 는 양의 정수이어야 합니다.")

        # 시크릿 평문 로그 금지 — prefix 만 노출 (AC-7.2).
        logger.info(
            "SummarizerClient init — model=%s key_prefix=%s",
            model, mask_key(api_key),
        )
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.quota = quota if quota is not None else QuotaTracker()
        self.max_output_tokens = max_output_tokens

    def summarize(
        self,
        articles_by_category: dict[str, list[Article]],
        system_prompt: str,
    ) -> SummarizeResult:
        """단일 호출에 점수·요약·회사 영향·카테고리 핵심 동시 출력.

        Args:
            articles_by_category: filters.pipeline.apply 결과. 카테고리 3종 키.
            system_prompt: `prompts/summarize.md` 본문 (load_system_prompt 결과).

        Returns:
            SummarizeResult — items + category_headlines + dropped_items + 토큰 누적.

        Raises:
            QuotaExceededError: quota cap 초과 또는 Gemini API rate limit / quota 초과.
            RuntimeError: 응답 JSON 파싱 실패 또는 빈 응답.
        """
        if not isinstance(articles_by_category, dict):
            raise ValueError("articles_by_category 는 dict 이어야 합니다.")
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise ValueError("system_prompt 는 비어있지 않은 문자열이어야 합니다.")

        # 입력 article id 집합 — 응답 검증의 단일 진실.
        valid_ids: set[str] = set()
        for cat in CATEGORIES:
            for art in articles_by_category.get(cat, []):
                valid_ids.add(art.canonical_url)

        user_text = _serialize_articles_for_user_message(articles_by_category)

        logger.info(
            "Gemini API call — model=%s items=%d categories=%d",
            self.model, len(valid_ids), len(CATEGORIES),
        )

        # Gemini JSON mode + system_instruction. ADR-004: prompt caching 없음.
        # 2026-05-19 핫픽스: Gemini 2.5 라인의 thinking-mode 가 default 활성이라
        # max_output_tokens 의 일부 (수천 토큰) 가 thinking 에 소진 → 실제 JSON
        # 응답이 짧게 truncate 되는 회귀 발생. JSON 출력은 response_schema 가
        # 형식을 강제하므로 thinking 효과가 작고, 비활성이 응답 토큰 보장 측면에서 안전.
        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            max_output_tokens=self.max_output_tokens,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_text,
                config=config,
            )
        except (genai_errors.ClientError, genai_errors.ServerError) as e:
            if _is_quota_or_rate_limit_error(e):
                raise QuotaExceededError(
                    f"Gemini API quota / rate limit 초과: {e}"
                ) from e
            raise

        # 토큰 사용량 추출 — google-genai 의 usage_metadata.
        usage = getattr(response, "usage_metadata", None)
        tokens_in = int(getattr(usage, "prompt_token_count", 0) or 0)
        tokens_out = int(getattr(usage, "candidates_token_count", 0) or 0)

        # quota 체크 — cap 초과 시 raise (누적 미반영).
        self.quota.check_and_record(tokens_in, tokens_out)

        # 응답 본문 추출 — google-genai 의 response.text 우선, 없으면 candidates 순회.
        raw_text = getattr(response, "text", None) or ""
        if not raw_text:
            candidates = getattr(response, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                parts = getattr(content, "parts", None) or []
                for part in parts:
                    text = getattr(part, "text", None)
                    if isinstance(text, str):
                        raw_text += text
        if not raw_text.strip():
            raise RuntimeError("Gemini 응답 content 에 text 가 없습니다.")

        # 2026-05-19 핫픽스: truncate 회귀 진단을 위해 finish_reason 확인.
        # FinishReason.STOP 만 정상. MAX_TOKENS / SAFETY / RECITATION 등은 명시 raise.
        finish_reason = None
        resp_candidates = getattr(response, "candidates", None) or []
        if resp_candidates:
            finish_reason = getattr(resp_candidates[0], "finish_reason", None)
        finish_str = getattr(finish_reason, "value", None) or (
            str(finish_reason) if finish_reason is not None else ""
        )
        if finish_str and finish_str.upper() not in ("STOP",):
            snippet_head = raw_text[:200]
            snippet_tail = raw_text[-200:] if len(raw_text) > 400 else ""
            raise RuntimeError(
                f"Gemini 응답 종료 비정상 (finish_reason={finish_str}, "
                f"tokens_out={tokens_out}, raw_len={len(raw_text)}). "
                f"head={snippet_head!r} tail={snippet_tail!r}"
            )

        parsed = _parse_response_json(raw_text)

        items, dropped = _validate_and_filter_items(parsed.get("items"), valid_ids)
        category_headlines = _validate_category_headlines(parsed.get("category_headlines"))

        logger.info(
            "summarizer result — valid=%d dropped=%d tokens_in=%d tokens_out=%d",
            len(items), dropped, tokens_in, tokens_out,
        )

        return SummarizeResult(
            items=items,
            category_headlines=category_headlines,
            dropped_items=dropped,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
