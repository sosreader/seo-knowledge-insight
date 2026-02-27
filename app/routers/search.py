"""
POST /api/v1/search — 語意搜尋 SEO 知識庫
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app import config
from app.core.chat import get_embedding
from app.core.store import store
from utils import audit_logger

router = APIRouter(prefix="/api/v1/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜尋關鍵字或問題")
    top_k: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = Field(default=None, description="限定分類篩選")


class SearchResult(BaseModel):
    id: int
    question: str
    answer: str
    keywords: list[str]
    category: str
    difficulty: str
    evergreen: bool
    source_title: str
    source_date: str
    score: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int


@router.post("", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    embedding = await get_embedding(req.query)
    hits = store.search(embedding, top_k=req.top_k, category=req.category)

    results = [
        SearchResult(
            id=item.id,
            question=item.question,
            answer=item.answer,
            keywords=item.keywords,
            category=item.category,
            difficulty=item.difficulty,
            evergreen=item.evergreen,
            source_title=item.source_title,
            source_date=item.source_date,
            score=round(score, 4),
        )
        for item, score in hits
    ]

    # 稽核日誌：記錄查詢與返回的 QA IDs
    client_ip = request.client.host if request.client else None
    audit_logger.log_search(
        query=req.query,
        top_k=req.top_k,
        category=req.category,
        returned_ids=[r.id for r in results],
        source_titles=list({r.source_title for r in results}),
        client_ip=client_ip,
    )

    return SearchResponse(results=results, total=len(results))
