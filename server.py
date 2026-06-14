"""
AEGIS — FastAPI Backend
REST API for the React frontend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag.vector_store import load_collection
from router.query_router import academic_handler, general_handler
from database import (
    save_chat,
    get_recent_history,
    get_device_history,
    get_recent_sessions,
    get_session_messages,
    get_total_chats,
    get_unique_devices,
    init_db,
)

# ── Initialise ──────────────────────────────────────────────────────────────

init_db()

app = FastAPI(title="AEGIS API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pre-load vector store once at startup
_collection = None


@app.on_event("startup")
def startup():
    global _collection
    _collection = load_collection()
    print("✅ AEGIS API ready — vector store loaded")


# ── Request / Response Models ───────────────────────────────────────────────


class ChatRequest(BaseModel):
    question: str
    mode: str = "academic"  # "academic" | "general"
    tools: list[str] = []   # for general mode: "Wikipedia", "Web Search (Tavily)", "arXiv"
    device_id: str = "web"
    session_id: str | None = None  # If None, creates new session


class ChatResponse(BaseModel):
    answer: str
    mode: str
    tool_used: str = ""
    session_id: str = ""  # Return session_id so frontend can track it


class HistoryItem(BaseModel):
    id: str
    device_id: str
    question: str
    answer: str
    mode: str
    timestamp: str
    session_id: str = ""


class SessionItem(BaseModel):
    session_id: str
    device_id: str
    title: str
    mode: str
    created_at: str
    updated_at: str


class StatsResponse(BaseModel):
    total_chats: int
    unique_devices: int


# ── Endpoints ───────────────────────────────────────────────────────────────


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Main chat endpoint — routes to Academic or General handler."""
    if req.mode == "academic":
        result = academic_handler(req.question)
    else:
        result = general_handler(req.question, req.tools)

    answer = result.get("answer", "Sorry, I couldn't process that.")
    tool_used = result.get("tool_used", "")
    confidence = result.get("confidence", 0.0)
    mode_label = "Academic" if req.mode == "academic" else "General"

    # Save to Supabase (will create new session if session_id is None)
    session_id = save_chat(
        req.device_id, 
        req.question, 
        answer, 
        mode_label, 
        confidence,
        req.session_id
    )

    return ChatResponse(
        answer=answer, 
        mode=mode_label, 
        tool_used=tool_used,
        session_id=session_id or ""
    )


@app.get("/api/sessions", response_model=list[SessionItem])
def sessions(device_id: str | None = None, limit: int = 30):
    """Get chat sessions — optionally filtered by device."""
    rows = get_recent_sessions(device_id, limit)
    return rows


@app.get("/api/sessions/{session_id}/messages", response_model=list[HistoryItem])
def session_messages(session_id: str):
    """Get all messages from a specific session."""
    rows = get_session_messages(session_id)
    return rows


@app.get("/api/history", response_model=list[HistoryItem])
def history(device_id: str | None = None, limit: int = 30):
    """Get chat history — optionally filtered by device."""
    if device_id:
        rows = get_device_history(device_id, limit)
    else:
        rows = get_recent_history(limit)
    return rows


@app.get("/api/stats", response_model=StatsResponse)
def stats():
    """Get usage stats."""
    return StatsResponse(
        total_chats=get_total_chats(),
        unique_devices=get_unique_devices(),
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "model": "gemma4:e4b"}
