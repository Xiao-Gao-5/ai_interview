import json
import os
from collections import Counter


class SimpleRAG:
    """无 sklearn 的轻量级 RAG 检索引擎"""

    def __init__(self, knowledge_path="cs_knowledge.json"):
        self.knowledge_path = knowledge_path
        self.knowledge = []
        self.load_knowledge()

    def load_knowledge(self):
        if not os.path.exists(self.knowledge_path):
            raise FileNotFoundError(f"知识库文件不存在: {self.knowledge_path}")

        with open(self.knowledge_path, "r", encoding="utf-8") as f:
            self.knowledge = json.load(f)

    def _tokenize(self, text: str):
        return text.lower().split()

    def retrieve(self, query: str, top_k=3):
        if not self.knowledge:
            return [], []

        query_tokens = self._tokenize(query)
        results = []
        scores = []

        for item in self.knowledge:
            text = (
                item.get("question", "")
                + " "
                + item.get("answer", "")
                + " "
                + " ".join(item.get("keywords", []))
            ).lower()

            text_tokens = self._tokenize(text)

            # ✅ 关键词命中数
            common = Counter(query_tokens) & Counter(text_tokens)
            hit_count = sum(common.values())

            # ✅ 归一化得分（防止长文本作弊）
            score = hit_count / max(len(query_tokens), 1)

            if score > 0.05:
                results.append(item)
                scores.append(round(score, 4))

        # 排序 + Top-K
        sorted_items = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
        results, scores = zip(*sorted_items[:top_k]) if sorted_items else ([], [])

        return list(results), list(scores)