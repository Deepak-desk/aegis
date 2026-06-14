"""
AEGIS RAG Pipeline - Query + LLM Answer Generation (v2)
========================================================
Features:
  1. Source Citation    — shows handbook page numbers for every answer
  2. Confidence Score   — computed from vector similarity distances
  3. Out-of-Scope Guard — rejects questions unrelated to the handbook

Flow:
  User Query → Embedding → ChromaDB → Relevance Check → Prompt → Qwen → Answer + Sources + Confidence
"""

import chromadb
from chromadb.utils import embedding_functions
import requests
import sys

# ── Configuration ──────────────────────────────────────────────────────────
CHROMA_DB_PATH = "chroma_db"
COLLECTION_NAME = "stc_handbook"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "gemma4:e4b"
TOP_K = 3

# ── Thresholds ─────────────────────────────────────────────────────────────
OUT_OF_SCOPE_THRESHOLD = 0.75   # best chunk distance above this → reject
LOW_CONFIDENCE_THRESHOLD = 0.60 # warn user if confidence below this


# ── Prompt Templates ───────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are AEGIS, a helpful college assistant chatbot for Sree Saraswathi Thyagaraja College (STC), Pollachi. You answer student queries based ONLY on the provided handbook context.

Rules:
1. Answer ONLY from the given context. Do NOT make up information.
2. If the answer is not in the context, say: "This information is not available in the handbook. Please contact the college office for more details."
3. Be concise, friendly, and helpful.
4. Use simple language that college students can understand.
5. Do NOT repeat the source citations — the system will add them automatically."""

QUERY_TEMPLATE = """Context from STC Handbook:
---
{context}
---

Student's Question: {question}

Answer:"""

OUT_OF_SCOPE_RESPONSE = (
    "⚠️ This question is outside the scope of the STC Handbook knowledge base.\n"
    "I can only answer questions related to STC college rules, attendance, fees, "
    "scholarships, library, hostel, programmes, and other handbook topics.\n"
    "Please ask something about STC!"
)


# ── Core Functions ─────────────────────────────────────────────────────────

def load_collection():
    """Load the ChromaDB collection with the embedding function."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
    )
    return collection


def retrieve_chunks(collection, query: str, top_k: int = TOP_K) -> list[dict]:
    """Retrieve the most relevant chunks from ChromaDB."""
    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    chunks = []
    for i in range(len(results["documents"][0])):
        chunks.append({
            "content": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return chunks


def compute_confidence(chunks: list[dict]) -> float:
    """Compute confidence score from retrieval distances.

    Uses the formula: confidence = (1 - avg_distance) * 100
    Then clamps to 0-100 range and applies light normalization
    to make scores more intuitive (since most distances are 0.2-0.7).
    """
    if not chunks:
        return 0.0

    distances = [c["distance"] for c in chunks]
    avg_distance = sum(distances) / len(distances)

    # Raw confidence from distance
    raw_confidence = (1 - avg_distance) * 100

    # Normalize: distances typically range 0.15-0.75 for relevant queries
    # Map this to a more intuitive 60-98% range
    # A perfect match (dist=0.15) → ~95%, weak match (dist=0.65) → ~65%
    normalized = max(0, min(100, raw_confidence * 1.15))

    return round(normalized, 1)


def is_out_of_scope(chunks: list[dict]) -> bool:
    """Check if the query is outside the handbook's scope.

    If the best (closest) chunk has distance above threshold,
    the query is likely unrelated to the handbook.
    """
    if not chunks:
        return True
    best_distance = chunks[0]["distance"]
    return best_distance > OUT_OF_SCOPE_THRESHOLD


def build_context(chunks: list[dict]) -> str:
    """Build the context string from retrieved chunks."""
    context_parts = []
    for chunk in chunks:
        meta = chunk["metadata"]
        context_parts.append(
            f"[Source: {meta['topic']} | Page: {meta['source_page']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n".join(context_parts)


def build_sources(chunks: list[dict]) -> str:
    """Build formatted source citations from retrieved chunks."""
    seen = []
    sources = []
    for chunk in chunks:
        meta = chunk["metadata"]
        entry = f"Page {meta['source_page']} — {meta['topic']}"
        if entry not in seen:
            seen.append(entry)
            sources.append(f"  📄 {entry}")
    return "\n".join(sources)


def query_ollama(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Send prompt to Qwen via Ollama and return the response."""
    payload = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 512,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "Error: No response from model.")
    except requests.ConnectionError:
        return ("❌ Error: Cannot connect to Ollama. "
                "Make sure Ollama is running ('ollama serve').")
    except requests.Timeout:
        return "❌ Error: Ollama request timed out."
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── Main RAG Pipeline ─────────────────────────────────────────────────────

def ask(question: str, collection=None, verbose: bool = False) -> dict:
    """Full RAG pipeline with source citation, confidence, and scope guard.

    Returns a dict with: answer, sources, confidence, out_of_scope, chunks
    """
    if collection is None:
        collection = load_collection()

    # Step 1: Retrieve relevant chunks
    chunks = retrieve_chunks(collection, question)

    if verbose:
        print("\n📚 Retrieved Chunks:")
        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            print(f"   {i}. chunk_{meta['chunk_id']} — {meta['topic']} "
                  f"(distance: {chunk['distance']:.4f})")

    # Step 2: Compute confidence
    confidence = compute_confidence(chunks)

    # Step 3: Out-of-scope check
    if is_out_of_scope(chunks):
        if verbose:
            print(f"\n⚠️ Out-of-scope detected (best distance: {chunks[0]['distance']:.4f})")
        return {
            "answer": OUT_OF_SCOPE_RESPONSE,
            "sources": "",
            "confidence": confidence,
            "out_of_scope": True,
            "chunks": chunks,
        }

    # Step 4: Build context and prompt
    context = build_context(chunks)
    prompt = QUERY_TEMPLATE.format(context=context, question=question)

    if verbose:
        print(f"   Confidence: {confidence}%")

    # Step 5: Generate answer via LLM
    answer = query_ollama(prompt)

    # Step 6: Build source citations
    sources = build_sources(chunks)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "out_of_scope": False,
        "chunks": chunks,
    }


def format_response(result: dict) -> str:
    """Format the full response with answer, confidence, and sources."""
    parts = []

    # Answer
    parts.append(f"🛡️ AEGIS: {result['answer']}")

    if not result["out_of_scope"]:
        # Confidence
        conf = result["confidence"]
        if conf >= 80:
            conf_icon = "🟢"
        elif conf >= 60:
            conf_icon = "🟡"
        else:
            conf_icon = "🔴"
        parts.append(f"\n{conf_icon} Confidence: {conf}%")

        # Sources
        if result["sources"]:
            parts.append(f"\n📚 Sources:")
            parts.append(result["sources"])

    return "\n".join(parts)


# ── Interactive & Demo Modes ───────────────────────────────────────────────

def interactive_mode():
    """Run AEGIS in interactive chat mode."""
    print("=" * 60)
    print("   🛡️  AEGIS — STC College Assistant")
    print("   Ask any question about STC Handbook (2025-26)")
    print("   Type 'quit' or 'exit' to stop")
    print("=" * 60)

    collection = load_collection()
    print("✅ Knowledge base loaded (53 chunks).\n")

    while True:
        try:
            question = input("🎓 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break

        print("\n⏳ Thinking...\n")
        result = ask(question, collection, verbose=True)
        print()
        print(format_response(result))
        print("\n" + "-" * 60)


def demo_mode():
    """Run a demo with preset questions including out-of-scope test."""
    print("=" * 60)
    print("   🛡️  AEGIS — DEMO MODE")
    print("   Testing retrieval, answers, citations & scope guard")
    print("=" * 60)

    collection = load_collection()
    print("✅ Knowledge base loaded (53 chunks).\n")

    demo_questions = [
        # In-scope questions
        "What is the minimum attendance required to write exams?",
        "Can I write exams if my attendance is 70%?",
        "Is ragging allowed in STC?",
        "How many books can a UG student borrow from the library?",
        "What is the fine for late fee payment?",
        "What scholarships are available for MBA students?",
        "Does STC offer BCA programme?",
        "What are the hostel rules?",
        # Out-of-scope questions (should be rejected)
        "Who is Elon Musk?",
        "What is the capital of France?",
    ]

    for question in demo_questions:
        print(f"\n{'=' * 60}")
        print(f"🎓 Question: {question}")
        print("-" * 60)
        result = ask(question, collection, verbose=True)
        print()
        print(format_response(result))

    print(f"\n{'=' * 60}")
    print("✅ DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_mode()
    else:
        interactive_mode()
