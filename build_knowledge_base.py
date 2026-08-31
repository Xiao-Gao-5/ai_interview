from backend.build_knowledge_base import build_knowledge_base


if __name__ == "__main__":
    total = build_knowledge_base()
    print(f"FAISS knowledge base built successfully. Documents: {total}")
