"""
AEGIS — Vector Store Interface
Manages the ChromaDB collection: load, query, and retrieve.
Uses singleton caching so the embedding model loads only once.
"""

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "stc_handbook"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Singleton cache ──
_collection = None


def load_collection():
    """Load the ChromaDB collection (cached after first call)."""
    global _collection
    if _collection is not None:
        return _collection

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    _collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    return _collection


def retrieve_chunks(collection, query: str, top_k: int = 5) -> list[dict]:
    """Retrieve the most relevant chunks from ChromaDB.

    Fetches `top_k` chunks and returns them sorted by distance (best first).
    Default top_k is 5 to allow for reranking downstream.
    """
    results = collection.query(query_texts=[query], n_results=top_k)

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append(
            {
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )
    return chunks
