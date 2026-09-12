"""Embedding service supporting Gemini API and local sentence-transformers fallback.

Default uses Gemini embedding model (gemini-embedding-001) with 1024 dimensions
matching pgvector column vector(1024). L2 normalized for cosine similarity.
"""

from __future__ import annotations

import logging
import math
import threading
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:  # pragma: no cover
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0:
        return vec
    return [x / norm for x in vec]


def _embed_gemini(texts: list[str]) -> list[list[float]]:
    import time
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_api_key)
    # Process in batches of 16 to respect API payload limits
    batch_size = 16
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=chunk if len(chunk) > 1 else chunk[0],
                    config=types.EmbedContentConfig(output_dimensionality=1024),
                )
                for emb in resp.embeddings:
                    all_embeddings.append(_normalize(list(emb.values)))
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning("Gemini rate limit hit, waiting 40s before retry (attempt %d/%d)...", attempt + 1, max_retries)
                        time.sleep(40)
                        continue
                raise

    return all_embeddings


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                device = settings.embedding_device if settings.embedding_device != "auto" else None
                logger.info("loading local sentence-transformers model %s", settings.embedding_model)
                _model = SentenceTransformer(settings.embedding_model, device=device)
    return _model


def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    """Embed a batch of texts. Returns L2-normalised vectors."""
    if not texts:
        return []

    # Prefer Gemini API when available for zero-dependency high quality embeddings
    if settings.google_api_key:
        try:
            return _embed_gemini(texts)
        except Exception as e:
            logger.warning("Gemini embedding failed (%s), trying local model", e)

    try:
        vectors = get_model().encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]
    except Exception as e:
        logger.error("All embedding backends failed: %s", e)
        raise


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]

