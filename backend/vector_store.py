import chromadb
from sentence_transformers import SentenceTransformer
import os

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./chroma_db"))
collection = client.get_or_create_collection("codebase_context")

def query_context(query_text: str, n_results=5) -> list[dict]:
    """
    Input  : free-form text (affected area + user description)
    Output : top N relevant modules/files with owner emails
    """
    embedding = model.encode([query_text]).tolist()

    results = collection.query(
        query_embeddings=embedding,
        n_results=n_results,
        include=["metadatas", "documents", "distances"]
    )

    retrieved = []
    for i in range(len(results["ids"][0])):
        similarity = round(1 - results["distances"][0][i], 2)
        if similarity < 0.4:      # skip low-relevance chunks
            continue
        retrieved.append({
            "text":        results["documents"][0][i],
            "module":      results["metadatas"][0][i]["module_name"],
            "type":        results["metadatas"][0][i]["type"],
            "similarity":  similarity
        })

    return retrieved


def format_context_for_prompt(chunks: list[dict]) -> str:
    """Formats retrieved chunks into a clean string for LLM injection."""
    if not chunks:
        return "No specific module context found."

    lines = []
    for c in chunks:
        lines.append(
            f"- [{c['type'].upper()}] {c['text']} "
            f"(relevance: {c['similarity']}, owner: {c['owner_email']})"
        )
    return "\n".join(lines)