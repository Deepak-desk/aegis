"""
AEGIS — Retriever
Handles retrieval, relevance scoring, reranking, and scope-guard logic.
"""

from rag.vector_store import load_collection, retrieve_chunks

# ── Thresholds ──
OUT_OF_SCOPE_THRESHOLD = 0.75
LOW_CONFIDENCE_THRESHOLD = 0.60
RETRIEVE_K = 5   # fetch 5 chunks
RERANK_K = 3     # keep best 3 after reranking


def compute_confidence(chunks: list[dict]) -> float:
    """Compute confidence % from retrieval distances."""
    if not chunks:
        return 0.0
    distances = [c["distance"] for c in chunks]
    avg_distance = sum(distances) / len(distances)
    raw = (1 - avg_distance) * 100
    return round(max(0, min(100, raw * 1.15)), 1)


def is_out_of_scope(chunks: list[dict]) -> bool:
    """True if best chunk distance exceeds threshold → query unrelated."""
    if not chunks:
        return True
    return chunks[0]["distance"] > OUT_OF_SCOPE_THRESHOLD


def rerank(chunks: list[dict], top_n: int = RERANK_K) -> list[dict]:
    """Simple reranker: keep the top_n closest chunks.

    Currently uses distance-based ordering (ChromaDB already returns sorted).
    This can later be upgraded to a cross-encoder reranker.
    """
    sorted_chunks = sorted(chunks, key=lambda c: c["distance"])
    return sorted_chunks[:top_n]


def build_context(chunks: list[dict]) -> str:
    """Build the context string for the LLM prompt."""
    parts = []
    for chunk in chunks:
        meta = chunk["metadata"]
        parts.append(
            f"[Source: {meta['topic']} | Page: {meta['source_page']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n".join(parts)


def build_sources(chunks: list[dict]) -> str:
    """Build formatted source citations."""
    seen = []
    sources = []
    for chunk in chunks:
        meta = chunk["metadata"]
        entry = f"Page {meta['source_page']} — {meta['topic']}"
        if entry not in seen:
            seen.append(entry)
            sources.append(f"  📄 {entry}")
    return "\n".join(sources)
