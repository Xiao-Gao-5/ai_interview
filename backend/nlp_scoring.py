from __future__ import annotations

import json
import re

import numpy as np

from .config import settings
from .embeddings import EmbeddingError, embed_texts
from .llm import call_qwen


class SemanticScorer:
    def similarity(self, answer: str, reference: str) -> float:
        if not answer.strip() or not reference.strip():
            return 0.0
        try:
            v1, v2 = embed_texts([answer, reference])
        except EmbeddingError:
            return 0.0

        a = np.array(v1, dtype="float32")
        b = np.array(v2, dtype="float32")
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.dot(a, b) / denom) if denom else 0.0

    def evaluate_answer(self, question: str, answer: str, reference: str) -> dict:
        semantic = self.similarity(answer, reference)
        baseline = max(1.0, min(10.0, semantic * 10))

        prompt = f"""你是严格但客观的技术面试评分器。请只输出 JSON。

问题：
{question}

候选人回答：
{answer}

参考资料：
{reference}

语义相似度基线：{semantic:.4f}

请按 1-10 分评价：
- accuracy：技术准确性
- completeness：回答完整性
- logic：表达逻辑
- depth：技术深度

输出格式：
{{"accuracy": 8, "completeness": 7, "logic": 8, "depth": 6, "comment": "简短评价", "key_tech": ["技术点"]}}
"""
        result = call_qwen(prompt, model=settings.eval_model, temperature=0.2)
        if result:
            try:
                match = re.search(r"\{.*\}", result, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    return self._normalize(data, baseline, semantic)
            except json.JSONDecodeError:
                pass

        return self._normalize(
            {
                "accuracy": baseline,
                "completeness": baseline,
                "logic": max(1.0, min(10.0, baseline + 0.5)),
                "depth": max(1.0, min(10.0, baseline - 0.5)),
                "comment": "已根据语义相似度给出基础评价，建议结合参考答案补充关键细节。",
                "key_tech": [],
            },
            baseline,
            semantic,
        )

    def _normalize(self, data: dict, baseline: float, semantic: float) -> dict:
        normalized = {}
        for key in ["accuracy", "completeness", "logic", "depth"]:
            value = data.get(key, baseline)
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = baseline
            normalized[key] = round(max(1.0, min(10.0, value)), 2)

        normalized["comment"] = str(data.get("comment") or "回答有一定相关性，但仍需补充细节。")
        key_tech = data.get("key_tech", [])
        normalized["key_tech"] = key_tech if isinstance(key_tech, list) else []
        normalized["semantic_score"] = round(semantic, 4)
        return normalized
