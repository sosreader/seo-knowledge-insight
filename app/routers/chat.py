"""
POST /api/v1/chat — RAG 問答
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator

from app.core.chat import rag_chat
from app.core.limiter import limiter
from app.core.schemas import ApiResponse
from utils import audit_logger

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class HistoryMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[HistoryMessage] = Field(default_factory=list)

    @field_validator("history")
    @classmethod
    def history_max_length(cls, v: list) -> list:
        if len(v) > 20:
            raise ValueError("history cannot exceed 20 messages")
        return v


class SourceItem(BaseModel):
    id: str
    question: str
    category: str
    source_title: str
    source_date: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@router.post("", response_model=ApiResponse[ChatResponse])
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request) -> ApiResponse[ChatResponse]:
    history = [{"role": m.role, "content": m.content} for m in req.history]
    result = await rag_chat(req.message, history=history or None)

    # 稽核日誌：記錄問答與使用的來源 QA IDs
    client_ip = request.client.host if request.client else None
    source_ids = [s["id"] for s in result["sources"]]
    source_titles = list({s["source_title"] for s in result["sources"]})
    audit_logger.log_chat(
        message=req.message,
        returned_ids=source_ids,
        source_titles=source_titles,
        client_ip=client_ip,
    )

    return ApiResponse.ok(
        ChatResponse(
            answer=result["answer"],
            sources=[SourceItem(**s) for s in result["sources"]],
        )
    )
