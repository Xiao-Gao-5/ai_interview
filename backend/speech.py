from __future__ import annotations

import logging
from pathlib import Path

import dashscope

from .config import settings

logger = logging.getLogger(__name__)


class ASRError(RuntimeError):
    pass


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"wav", "mp3", "m4a", "aac", "pcm", "flac", "opus"}:
        return suffix
    return "wav"


def speech_to_text(
    audio_path: str,
    sample_rate: int = 16000,
    audio_format: str | None = None,
) -> str:
    """Transcribe local audio through DashScope ASR.

    The implementation uses DashScope's streaming recognition SDK and can be
    reused by a future WebSocket endpoint for realtime interview audio.
    """
    if not settings.dashscope_api_keys:
        raise ASRError("DASHSCOPE_API_KEY or DASHSCOPE_API_KEYS is not configured.")

    path = Path(audio_path)
    if not path.exists():
        raise ASRError(f"Audio file not found: {audio_path}")

    dashscope.api_key = settings.dashscope_api_keys[0]
    fmt = audio_format or _detect_format(path)

    try:
        from dashscope.audio.asr import Recognition, RecognitionCallback
    except Exception as exc:
        raise ASRError("Installed dashscope package does not provide ASR support.") from exc

    class Callback(RecognitionCallback):
        def __init__(self):
            self.text_parts: list[str] = []

        def on_event(self, result):
            sentence = getattr(result, "sentence", None)
            if isinstance(sentence, dict):
                text = sentence.get("text", "")
                if text:
                    self.text_parts.append(text)

        def on_error(self, message):
            logger.error("DashScope ASR error: %s", message)

    callback = Callback()
    try:
        recognition = Recognition(
            model=settings.asr_model,
            format=fmt,
            sample_rate=sample_rate,
            callback=callback,
        )
        recognition.call(str(path))
    except Exception as exc:
        logger.exception("DashScope ASR request failed.")
        raise ASRError(str(exc)) from exc

    return "".join(callback.text_parts).strip()
