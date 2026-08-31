from __future__ import annotations

import json

import faiss
import numpy as np

from .config import DATA_DIR, FAISS_INDEX, FAISS_META, KNOWLEDGE_FILE
from .embeddings import embed_texts
from .rag_engine import format_doc_for_embedding


def build_knowledge_base(batch_size: int = 10) -> int:
    if not KNOWLEDGE_FILE.exists():
        raise FileNotFoundError(f"Knowledge file not found: {KNOWLEDGE_FILE}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with KNOWLEDGE_FILE.open("r", encoding="utf-8") as file:
        docs = json.load(file)

    vectors: list[list[float]] = []
    for start in range(0, len(docs), batch_size):
        batch = docs[start : start + batch_size]
        texts = [format_doc_for_embedding(doc) for doc in batch]
        vectors.extend(embed_texts(texts))

    matrix = np.array(vectors, dtype="float32")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    faiss.write_index(index, str(FAISS_INDEX))
    np.save(str(FAISS_META), np.array(docs, dtype=object))
    return len(docs)


if __name__ == "__main__":
    total = build_knowledge_base()
    print(f"FAISS knowledge base built successfully. Documents: {total}")
