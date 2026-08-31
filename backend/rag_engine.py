from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from .config import FAISS_INDEX, FAISS_META, KNOWLEDGE_FILE
from .embeddings import EmbeddingError, embed_text

logger = logging.getLogger(__name__)


def format_doc_for_embedding(doc: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"分类：{doc.get('category', '')}",
            f"问题：{doc.get('question', '')}",
            f"答案：{doc.get('answer', '')}",
        ]
    )


class VectorRAG:
    def __init__(
        self,
        index_path: Path = FAISS_INDEX,
        meta_path: Path = FAISS_META,
        knowledge_path: Path = KNOWLEDGE_FILE,
    ):
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.knowledge_path = Path(knowledge_path)
        self.index = None
        self.metadata: list[dict[str, Any]] = []
        self.load()

    @property
    def ready(self) -> bool:
        return self.index is not None and bool(self.metadata)

    def load(self) -> None:
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            loaded = np.load(str(self.meta_path), allow_pickle=True)
            self.metadata = [dict(item) for item in loaded.tolist()]
            return

        logger.warning(
            "FAISS index not found. Run `python -m backend.build_knowledge_base`."
        )
        self.index = None
        self.metadata = self._load_knowledge_fallback()

    def _load_knowledge_fallback(self) -> list[dict[str, Any]]:
        if not self.knowledge_path.exists():
            return []
        with self.knowledge_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []

    def retrieve(self, query: str, top_k: int = 3) -> tuple[list[dict[str, Any]], list[float]]:
        if not query.strip() or not self.metadata:
            return [], []

        if not self.ready:
            return self.metadata[:top_k], [0.0] * min(top_k, len(self.metadata))

        try:
            vector = np.array([embed_text(query)], dtype="float32")
        except EmbeddingError as exc:
            logger.warning("Embedding failed during retrieval: %s", exc)
            return self.metadata[:top_k], [0.0] * min(top_k, len(self.metadata))

        faiss.normalize_L2(vector)
        scores, ids = self.index.search(vector, top_k)

        docs: list[dict[str, Any]] = []
        clean_scores: list[float] = []
        for idx, score in zip(ids[0], scores[0]):
            if idx == -1:
                continue
            docs.append(self.metadata[int(idx)])
            clean_scores.append(float(score))
        return docs, clean_scores


SimpleRAG = VectorRAG
