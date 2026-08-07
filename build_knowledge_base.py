from backend.rag_engine import SimpleRAG

if __name__ == "__main__":
    print("🔧 正在构建 RAG 知识库...")
    rag = SimpleRAG("cs_knowledge.json")
    print(f"✅ 知识库构建完成！共加载 {len(rag.knowledge)} 条知识条目")

    print("\n📋 知识库分类统计：")
    categories = {}
    for item in rag.knowledge:
        cat = item.get("category", "未分类")
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count} 条")

    print("\n🔍 测试检索：Java 垃圾回收")
    docs, scores = rag.retrieve("Java 垃圾回收", top_k=3)
    for d, s in zip(docs, scores):
        print(f"  [相似度 {s:.3f}] [{d['category']}] {d['question']}")

    print("\n🔍 测试检索：Redis 缓存")
    docs, scores = rag.retrieve("Redis 缓存穿透", top_k=3)
    for d, s in zip(docs, scores):
        print(f"  [相似度 {s:.3f}] [{d['category']}] {d['question']}")