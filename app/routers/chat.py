"""
POST /api/v1/chat — RAG 問答
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.chat import rag_chat

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=20)


class SourceItem(BaseModel):
    id: int
    question: str
    category: str
    source_title: str
    source_date: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    history = [{"role": m.role, "content": m.content} for m in req.history]
    result = await rag_chat(req.message, history=history or None)

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceItem(**s) for s in result["sources"]],
    )
