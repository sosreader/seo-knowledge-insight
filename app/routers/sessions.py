"""
Chat Sessions API — CRUD + RAG message handler

Endpoints:
  GET    /api/v1/sessions              - List sessions (paginated)
  POST   /api/v1/sessions              - Create new session
  GET    /api/v1/sessions/{id}         - Get session with messages
  POST   /api/v1/sessions/{id}/messages - Send message (triggers RAG chat)
  DELETE /api/v1/sessions/{id}         - Delete session
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.chat import rag_chat
from app.core.limiter import limiter
from app.core.schemas import ApiResponse
from app.core.session_store import Session, SessionMessage, session_store

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


# ── Request / Response schemas ───────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=100)


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class SessionMessageOut(BaseModel):
    role: str
    content: str
    sources: list[dict]
    created_at: str


class SessionSummaryOut(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class SessionDetailOut(SessionSummaryOut):
    messages: list[SessionMessageOut]


class SessionListOut(BaseModel):
    items: list[SessionSummaryOut]
    total: int


class SendMessageOut(BaseModel):
    answer: str
    sources: list[dict]
    session: SessionDetailOut


# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_summary(s: Session) -> SessionSummaryOut:
    return SessionSummaryOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_detail(s: Session) -> SessionDetailOut:
    return SessionDetailOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
        messages=[
            SessionMessageOut(
                role=m.role,
                content=m.content,
                sources=m.sources,
                created_at=m.created_at,
            )
            for m in s.messages
        ],
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=ApiResponse[SessionListOut])
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ApiResponse[SessionListOut]:
    sessions, total = session_store.list_sessions(limit=limit, offset=offset)
    return ApiResponse.ok(
        SessionListOut(
            items=[_to_summary(s) for s in sessions],
            total=total,
        )
    )


@router.post("", response_model=ApiResponse[SessionDetailOut])
async def create_session(
    req: Optional[CreateSessionRequest] = None,
) -> ApiResponse[SessionDetailOut]:
    title = req.title if req and req.title else ""
    session = session_store.create_session(title=title)
    return ApiResponse.ok(_to_detail(session))


@router.get("/{session_id}", response_model=ApiResponse[SessionDetailOut])
async def get_session(session_id: str) -> ApiResponse[SessionDetailOut]:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return ApiResponse.ok(_to_detail(session))


@router.post(
    "/{session_id}/messages",
    response_model=ApiResponse[SendMessageOut],
)
@limiter.limit("20/minute")
async def send_message(
    session_id: str,
    req: SendMessageRequest,
    request: Request,
) -> ApiResponse[SendMessageOut]:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Save user message
    user_msg = SessionMessage(role="user", content=req.message)
    session = session_store.add_message(session_id, user_msg)
    if session is None:
        raise HTTPException(
            status_code=409,
            detail="Failed to add message (session full or concurrent conflict)",
        )

    # 2. Build history from existing messages (exclude the just-added user msg)
    history = [{"role": m.role, "content": m.content} for m in session.messages[:-1]]

    # 3. Call RAG chat
    result = await rag_chat(req.message, history=history or None)

    # 4. Save assistant message
    assistant_msg = SessionMessage(
        role="assistant",
        content=result["answer"],
        sources=result["sources"],
    )
    session = session_store.add_message(session_id, assistant_msg)
    if session is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to save assistant response",
        )

    return ApiResponse.ok(
        SendMessageOut(
            answer=result["answer"],
            sources=result["sources"],
            session=_to_detail(session),
        )
    )


@router.delete("/{session_id}", response_model=ApiResponse[dict])
async def delete_session(session_id: str) -> ApiResponse[dict]:
    deleted = session_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return ApiResponse.ok({"deleted": True, "session_id": session_id})
