"""
POST /api/v1/feedback — 使用者回饋

使用者回報搜尋結果是否有幫助，記錄到 utils/learning_store。
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.schemas import ApiResponse
from utils.learning_store import learning_store

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="原始查詢字串")
    qa_id: str = Field(..., pattern=r"^[0-9a-f]{16}$", description="被評分的 Q&A stable_id（16-char hex）")
    feedback: Literal["helpful", "not_relevant"] = Field(
        ..., description="回饋類型：helpful（有幫助）或 not_relevant（不相關）"
    )
    top_score: Optional[float] = Field(default=None, description="該 Q&A 的搜尋分數（可選）")


@router.post("", response_model=ApiResponse[dict])
async def feedback(req: FeedbackRequest) -> ApiResponse[dict]:
    """
    POST /api/v1/feedback — 接收使用者對搜尋結果的回饋。

    回饋記錄到 output/learnings.jsonl，供後續分析和改善搜尋品質。
    """
    learning_store.record_feedback(
        query=req.query,
        qa_id=req.qa_id,
        feedback=req.feedback,
        top_score=req.top_score,
    )

    return ApiResponse.ok({
        "recorded": True,
        "qa_id": req.qa_id,
        "feedback": req.feedback,
    })
