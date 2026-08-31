from __future__ import annotations

import itertools
import logging
from typing import Iterable

import dashscope
from dashscope import Generation

from .config import settings

logger = logging.getLogger(__name__)

_key_cycle: Iterable[str] | None = (
    itertools.cycle(settings.dashscope_api_keys)
    if settings.dashscope_api_keys
    else None
)


class LLMError(RuntimeError):
    pass


def _next_api_key() -> str | None:
    if _key_cycle is None:
        return None
    return next(_key_cycle)


def call_qwen(
    prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1200,
) -> str | None:
    """Call Qwen through DashScope. Returns None when cloud config is missing."""
    api_key = _next_api_key()
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY or DASHSCOPE_API_KEYS is not configured.")
        return None

    dashscope.api_key = api_key
    try:
        response = Generation.call(
            model=model or settings.chat_model,
            prompt=prompt,
            result_format="text",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.warning("Qwen request failed: %s", exc)
        return None

    status_code = getattr(response, "status_code", 200)
    if status_code != 200:
        message = getattr(response, "message", None) or str(response)
        logger.error("Qwen request failed: %s", message)
        return None

    output = getattr(response, "output", None)
    if isinstance(output, str):
        return output.strip()
    if isinstance(output, dict):
        text = output.get("text")
        return text.strip() if isinstance(text, str) else None
    return None


def list_models() -> dict:
    return {
        "chat_model": settings.chat_model,
        "eval_model": settings.eval_model,
        "embedding_model": settings.embedding_model,
        "asr_model": settings.asr_model,
        "available_chat_models": settings.available_chat_models,
        "named_models": settings.named_models,
        "api_key_count": len(settings.dashscope_api_keys),
    }
