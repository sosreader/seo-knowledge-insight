"""
QAStore — 啟動時載入 qa_final.json + qa_embeddings.npy 進記憶體
提供 search（語意）和 list（篩選）兩種查詢介面
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from app import config

logger = logging.getLogger(__name__)


@dataclass
class QAItem:
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


@dataclass
class QAStore:
    items: list[QAItem] = field(default_factory=list)
    # shape: (N, embedding_dim)，每列已 L2 歸一化（方便用點積算 cosine）
    embeddings: np.ndarray = field(default_factory=lambda: np.empty((0, 1536)))

    def load(
        self,
        json_path: Path = config.QA_JSON_PATH,
        npy_path: Path = config.QA_EMBEDDINGS_PATH,
    ) -> None:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        raw_items = data["qa_database"]

        self.items = [
            QAItem(
                id=qa["id"],
                question=qa["question"],
                answer=qa["answer"],
                keywords=qa.get("keywords", []),
                confidence=qa.get("confidence", 0.0),
                category=qa.get("category", ""),
                difficulty=qa.get("difficulty", ""),
                evergreen=qa.get("evergreen", False),
                source_title=qa.get("source_title", ""),
                source_date=qa.get("source_date", ""),
                is_merged=qa.get("is_merged", False),
            )
            for qa in raw_items
        ]

        embeddings_raw = np.load(npy_path).astype(np.float32)
        # L2 歸一化，讓點積等於 cosine similarity
        norms = np.linalg.norm(embeddings_raw, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self.embeddings = embeddings_raw / norms

        logger.info("QAStore loaded: %d items, embeddings shape %s", len(self.items), self.embeddings.shape)

    def search(
        self,
        query_embedding: list[float] | np.ndarray,
        top_k: int = 5,
        category: Optional[str] = None,
    ) -> list[tuple[QAItem, float]]:
        """
        語意搜尋，回傳 [(item, score), ...] 依相似度降序
        """
        q = np.array(query_embedding, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        scores: np.ndarray = self.embeddings @ q  # (N,)

        if category:
            mask = np.array([item.category == category for item in self.items])
            scores = np.where(mask, scores, -1.0)

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(self.items[i], float(scores[i])) for i in top_indices if scores[i] > 0]

    def list_qa(
        self,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
        difficulty: Optional[str] = None,
        evergreen: Optional[bool] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[QAItem], int]:
        """
        篩選列表。回傳 (items, total_count)
        """
        results = self.items

        if category:
            results = [i for i in results if i.category == category]
        if keyword:
            kw_lower = keyword.lower()
            results = [
                i for i in results
                if kw_lower in i.question.lower()
                or kw_lower in i.answer.lower()
                or any(kw_lower in k.lower() for k in i.keywords)
            ]
        if difficulty:
            results = [i for i in results if i.difficulty == difficulty]
        if evergreen is not None:
            results = [i for i in results if i.evergreen == evergreen]

        total = len(results)
        return results[offset : offset + limit], total

    def categories(self) -> list[str]:
        seen: dict[str, int] = {}
        for item in self.items:
            seen[item.category] = seen.get(item.category, 0) + 1
        return sorted(seen, key=lambda c: -seen[c])


# module-level singleton，啟動時呼叫 .load()
store = QAStore()
