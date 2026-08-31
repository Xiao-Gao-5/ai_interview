from __future__ import annotations

import itertools
import logging
from typing import Iterable

import dashscope
from dashscope import TextEmbedding

from .config import settings

logger = logging.getLogger(__name__)

_embedding_key_cycle: Iterable[str] | None = (
    itertools.cycle(settings.dashscope_api_keys)
    if settings.dashscope_api_keys
    else None
)


class EmbeddingError(RuntimeError):
    pass


def _next_api_key() -> str | None:
    if _embedding_key_cycle is None:
        return None
    return next(_embedding_key_cycle)


def embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = _next_api_key()
    if not api_key:
        raise EmbeddingError("DashScope API key is not configured.")

    dashscope.api_key = api_key
    try:
        response = TextEmbedding.call(
            model=settings.embedding_model,
            input=texts,
            api_key=api_key,
        )
    except Exception as exc:
        logger.warning("DashScope embedding request failed: %s", exc)
        raise EmbeddingError(str(exc)) from exc

    status_code = getattr(response, "status_code", 200)
    if status_code != 200:
        message = getattr(response, "message", None) or str(response)
        raise EmbeddingError(message)

    output = getattr(response, "output", None)
    if isinstance(output, dict):
        embeddings = output.get("embeddings", [])
    else:
        embeddings = output["embeddings"]

    ordered = sorted(embeddings, key=lambda item: item.get("text_index", 0))
    return [item["embedding"] for item in ordered]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
