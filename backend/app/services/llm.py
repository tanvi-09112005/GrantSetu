"""Gemini client factory.

Nodes ask for a *tier* ("flash" or "pro"), never a model name. That keeps the
Addendum's rule -- no hardcoded model strings in node code -- enforceable by
reading the node files alone.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

Tier = Literal["flash", "pro"]

_MODEL_FOR_TIER: dict[str, str] = {
    "flash": settings.gemini_flash_model,
    "pro": settings.gemini_pro_model,
}

_cache: dict[tuple[str, float], BaseChatModel] = {}


def get_llm(tier: Tier = "flash", temperature: float = 0.2) -> BaseChatModel:
    """Return a chat model for the given tier.

    tier="flash" -> high-volume calls (reranking, claim extraction, verification).
    tier="pro"   -> the final drafting pass.
    """
    key = (tier, temperature)
    if key not in _cache:
        _cache[key] = ChatGoogleGenerativeAI(
            model=_MODEL_FOR_TIER[tier],
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
    return _cache[key]


def model_name(tier: Tier) -> str:
    """The concrete model string behind a tier -- for `model_used` audit columns."""
    return _MODEL_FOR_TIER[tier]


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json_response(text: str) -> Any:
    """Parse a JSON payload out of an LLM response.

    Gemini wraps JSON in a markdown fence often enough that every caller would
    otherwise reimplement this. Raises ValueError with the raw text attached so
    a failed parse is debuggable from the log line alone.
    """
    candidate = text.strip()
    fenced = _JSON_FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {text[:500]!r}") from exc
