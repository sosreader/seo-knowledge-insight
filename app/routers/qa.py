"""
GET /api/v1/qa       — 分頁列表（支援篩選）
GET /api/v1/qa/{id}  — 取單筆
GET /api/v1/qa/categories — 所有分類
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.store import QAItem, store

router = APIRouter(prefix="/api/v1/qa", tags=["qa"])


# ──────────── schema ────────────

class QAResponse(BaseModel):
    id: int
    question: str
    answer: str
    keywords: list[str]
    confidence: float
    category: str
    difficulty: str
    evergreen: bool
    source_title: str
    source_date: str
    is_merged: bool


class QAListResponse(BaseModel):
    items: list[QAResponse]
    total: int
    offset: int
    limit: int


class CategoriesResponse(BaseModel):
    categories: list[str]


def _to_schema(item: QAItem) -> QAResponse:
    return QAResponse(
        id=item.id,
        question=item.question,
        answer=item.answer,
        keywords=item.keywords,
        confidence=item.confidence,
        category=item.category,
        difficulty=item.difficulty,
        evergreen=item.evergreen,
        source_title=item.source_title,
        source_date=item.source_date,
        is_merged=item.is_merged,
    )


# ──────────── routes ────────────

@router.get("/categories", response_model=CategoriesResponse)
def get_categories() -> CategoriesResponse:
    return CategoriesResponse(categories=store.categories())


@router.get("/{item_id}", response_model=QAResponse)
def get_qa_item(item_id: int) -> QAResponse:
    for item in store.items:
        if item.id == item_id:
            return _to_schema(item)
    raise HTTPException(status_code=404, detail=f"QA id={item_id} not found")


@router.get("", response_model=QAListResponse)
def list_qa(
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=100),
    difficulty: Optional[str] = Query(default=None, pattern="^(基礎|進階)$"),
    evergreen: Optional[bool] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> QAListResponse:
    items, total = store.list_qa(
        category=category,
        keyword=keyword,
        difficulty=difficulty,
        evergreen=evergreen,
        limit=limit,
        offset=offset,
    )
    return QAListResponse(
        items=[_to_schema(i) for i in items],
        total=total,
        offset=offset,
        limit=limit,
    )
