"""Gemini client factory with resilient multi-model fallback.

Nodes ask for a *tier* ("flash" or "pro"), never a model name. That keeps the
Addendum's rule -- no hardcoded model strings in node code -- enforceable by
reading the node files alone.

Includes automatic model fallback to handle Google AI Studio free tier 429 /
RESOURCE_EXHAUSTED rate limits seamlessly.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

logger = logging.getLogger(__name__)

Tier = Literal["flash", "pro"]

_MODEL_FOR_TIER: dict[str, str] = {
    "flash": settings.gemini_flash_model,
    "pro": settings.gemini_pro_model,
}

import time

_cache: dict[tuple[str, float, str], BaseChatModel] = {}
# Track (api_key, model) pairs that hit 429 rate limits, with an expiry timestamp
_exhausted_candidates: dict[tuple[str, str], float] = {}


def _get_api_keys() -> list[str]:
    """Get list of configured Gemini API keys (supports comma-separated keys for pooling)."""
    raw = settings.google_api_key or ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return keys if keys else [""]


def get_llm(tier: Tier = "flash", temperature: float = 0.2) -> BaseChatModel:
    """Return a chat model for the given tier.

    tier="flash" -> high-volume calls (reranking, claim extraction, verification).
    tier="pro"   -> the final drafting pass.
    """
    keys = _get_api_keys()
    primary_key = keys[0] if keys else ""
    key = (tier, temperature, primary_key)
    if key not in _cache:
        _cache[key] = ChatGoogleGenerativeAI(
            model=_MODEL_FOR_TIER[tier],
            google_api_key=primary_key,
            temperature=temperature,
        )
    return _cache[key]


def invoke_with_fallback(
    prompt: str,
    tier: Tier = "flash",
    temperature: float = 0.2,
) -> str:
    """Invoke Gemini with automatic fallback across Gemini 3.x models and multiple API keys."""
    primary_model = _MODEL_FOR_TIER.get(tier, "gemini-3.5-flash")
    # Strictly modern Gemini 3.x models — prioritize stable models over overloaded preview models
    candidate_models = [
        primary_model,
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
    ]

    seen = set()
    models_to_try = []
    for m in candidate_models:
        if m not in seen:
            seen.add(m)
            models_to_try.append(m)

    # If provider is explicitly set to groq, try Groq first
    from app.services.groq_client import invoke_groq, is_groq_configured

    if settings.llm_provider == "groq":
        try:
            return invoke_groq(prompt, temperature=temperature)
        except Exception as e:
            logger.warning("Primary Groq invocation failed: %s. Trying Gemini fallback...", e)

    # Try Gemini 3.x candidate models across available API keys
    api_keys = _get_api_keys()
    now = time.time()
    last_error = None

    for key_idx, api_key in enumerate(api_keys):
        if not api_key:
            continue
        for model in models_to_try:
            # Skip if this model/key combination was marked exhausted within cooldown
            cooldown_until = _exhausted_candidates.get((api_key, model), 0)
            if cooldown_until > now:
                logger.debug(
                    "Skipping '%s' (key #%d) due to active cooldown (%ds remaining)",
                    model,
                    key_idx + 1,
                    int(cooldown_until - now),
                )
                continue

            try:
                llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=api_key,
                    temperature=temperature,
                    max_retries=1,
                    timeout=10.0,
                )
                resp = llm.invoke(prompt)
                content = resp.content
                if isinstance(content, list):
                    content = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in content
                    )
                return str(content)
            except Exception as e:
                err_str = str(e).lower()
                # If rate-limited / quota exhausted (429), place on cooldown for 2 hours
                if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                    _exhausted_candidates[(api_key, model)] = now + 7200
                    logger.warning(
                        "Model '%s' with key #%d hit quota limit (429). Put on 2-hr cooldown. Trying next candidate...",
                        model,
                        key_idx + 1,
                    )
                # If experiencing high demand / service unavailable (503), place on 5-minute cooldown
                elif "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
                    _exhausted_candidates[(api_key, model)] = now + 300
                    logger.warning(
                        "Model '%s' with key #%d experiencing high demand (503). Put on 5-min cooldown. Trying next candidate...",
                        model,
                        key_idx + 1,
                    )
                else:
                    logger.warning(
                        "Model '%s' with key #%d failed (%s), trying next candidate...",
                        model,
                        key_idx + 1,
                        e,
                    )
                last_error = e
                continue

    # In 'auto' mode, if Gemini fails and Groq is configured, fail over to Groq
    if settings.llm_provider == "auto" and is_groq_configured():
        logger.info("All Gemini 3.x candidates exhausted. Attempting Groq (Llama 3.3 70B) failover...")
        try:
            return invoke_groq(prompt, temperature=temperature)
        except Exception as groq_err:
            logger.warning("Groq failover also failed: %s", groq_err)
            last_error = groq_err

    if last_error:
        raise last_error
    raise RuntimeError("All candidate LLM models and providers failed")


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
