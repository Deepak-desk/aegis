"""
AEGIS — RAG Chain
End-to-end Academic Mode pipeline: retrieve → rerank → scope-check → LLM → answer.
"""

from rag.vector_store import load_collection, retrieve_chunks
from rag.retriever import (
    compute_confidence,
    is_out_of_scope,
    rerank,
    build_context,
    build_sources,
    RETRIEVE_K,
)
from models.ollama_llm import query_llm

# ── Prompt Templates ──
SYSTEM_PROMPT = (
    "You are AEGIS, a helpful college assistant chatbot for "
    "Sree Saraswathi Thyagaraja College (STC), Pollachi. "
    "You answer student queries based ONLY on the provided handbook context.\n\n"
    "Rules:\n"
    "1. Answer ONLY from the given context. Do NOT make up information.\n"
    "2. If the answer is not in the context, say: "
    '"This information is not available in the handbook. '
    'Please contact the college office for more details."\n'
    "3. Be concise, friendly, and helpful.\n"
    "4. Use simple language that college students can understand.\n"
    "5. Do NOT repeat the source citations — the system adds them automatically."
)

QUERY_TEMPLATE = """Context from STC Handbook:
---
{context}
---

Student's Question: {question}

Answer:"""

OUT_OF_SCOPE_RESPONSE = (
    "⚠️ This question is outside the scope of the STC Handbook.\n"
    "I can only answer questions related to STC college rules, attendance, fees, "
    "scholarships, library, hostel, programmes, and other handbook topics.\n\n"
    "💡 **Tip:** Switch to **General Mode** to ask general knowledge questions!"
)


def ask(question: str, collection=None) -> dict:
    """Full Academic RAG pipeline.

    Returns dict with: answer, sources, confidence, out_of_scope, chunks
    """
    if collection is None:
        collection = load_collection()

    # 1. Retrieve (fetch 5)
    raw_chunks = retrieve_chunks(collection, question, top_k=RETRIEVE_K)

    # 2. Rerank (keep best 3)
    chunks = rerank(raw_chunks)

    # 3. Confidence
    confidence = compute_confidence(chunks)

    # 4. Scope guard
    if is_out_of_scope(raw_chunks):
        return {
            "answer": OUT_OF_SCOPE_RESPONSE,
            "sources": "",
            "confidence": confidence,
            "out_of_scope": True,
            "chunks": chunks,
        }

    # 5. Build prompt & generate
    context = build_context(chunks)
    prompt = QUERY_TEMPLATE.format(context=context, question=question)
    answer = query_llm(prompt, system=SYSTEM_PROMPT)

    # 6. Sources
    sources = build_sources(chunks)

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "out_of_scope": False,
        "chunks": chunks,
    }
