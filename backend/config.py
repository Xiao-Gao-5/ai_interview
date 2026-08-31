import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _project_path(raw: str | os.PathLike[str]) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


DATA_DIR = _project_path(os.getenv("DATA_DIR", "data"))
KNOWLEDGE_FILE = _project_path(os.getenv("KNOWLEDGE_FILE", "cs_knowledge.json"))
FAISS_INDEX = DATA_DIR / "faiss.index"
FAISS_META = DATA_DIR / "faiss_meta.npy"


def _split_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _json_env(name: str, default: dict[str, Any]) -> dict[str, Any]:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else default
    except json.JSONDecodeError:
        return default


@dataclass(frozen=True)
class ModelSettings:
    dashscope_api_keys: list[str]
    chat_model: str
    eval_model: str
    embedding_model: str
    asr_model: str
    available_chat_models: list[str]
    named_models: dict[str, Any]

    @property
    def has_dashscope_key(self) -> bool:
        return bool(self.dashscope_api_keys)


settings = ModelSettings(
    dashscope_api_keys=_split_env("DASHSCOPE_API_KEYS")
    or _split_env("DASHSCOPE_API_KEY"),
    chat_model=os.getenv("QWEN_MODEL", "qwen-plus"),
    eval_model=os.getenv("QWEN_EVAL_MODEL", os.getenv("QWEN_MODEL", "qwen-plus")),
    embedding_model=os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4"),
    asr_model=os.getenv("DASHSCOPE_ASR_MODEL", "paraformer-realtime-v2"),
    available_chat_models=_split_env("QWEN_MODELS", "qwen-plus,qwen-turbo"),
    named_models=_json_env("MODEL_CONFIG_JSON", {}),
)
