"""
QAStore — 啟動時載入 qa_final.json + qa_embeddings.npy 進記憶體
提供 search（語意）、hybrid_search（語意+關鍵字）和 list（篩選）三種查詢介面
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from app import config
from utils.search_engine import SearchEngine

logger = logging.getLogger(__name__)


@dataclass
class QAItem:
    id: int
    stable_id: str
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
    # Hybrid search engine（load() 後初始化）
    _engine: Optional[SearchEngine] = field(default=None, repr=False)
    # O(1) id 查詢索引（load() 後建立）
    _id_index: dict = field(default_factory=dict, repr=False)

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
                stable_id=qa.get("stable_id", ""),
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

        # 建立 id → QAItem 索引，讓 get_item_by_id() 達到 O(1) 查詢
        self._id_index = {item.id: item for item in self.items}

        logger.info("QAStore loaded: %d items, embeddings shape %s", len(self.items), self.embeddings.shape)

        # 初始化 hybrid search engine（shared embeddings，不重算）
        # 若 embeddings 數量與 items 不符（如資料重算中途中斷），降級為語意搜尋
        if len(self.items) == embeddings_raw.shape[0]:
            qa_dicts = [
                {
                    "question": item.question,
                    "answer": item.answer,
                    "keywords": item.keywords,
                    "category": item.category,
                    "id": item.id,
                }
                for item in self.items
            ]
            self._engine = SearchEngine(qa_dicts, embeddings_raw)
        else:
            logger.warning(
                "SearchEngine 未初始化：items (%d) 與 embeddings (%d) 數量不符，"
                "hybrid_search 將降級為語意搜尋。請重新執行 Step 3 使兩者一致。",
                len(self.items),
                embeddings_raw.shape[0],
            )
            self._engine = None

    def get_item_by_id(self, qa_id: int) -> Optional[QAItem]:
        """O(1) id 查詢，load() 後可用；若不存在回傳 None。"""
        return self._id_index.get(qa_id)

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

    def hybrid_search(
        self,
        query: str,
        query_embedding: list[float] | np.ndarray,
        top_k: int = 5,
        category: Optional[str] = None,
        min_score: float = 0.20,
    ) -> list[tuple[QAItem, float]]:
        """
        Hybrid 搜尋（語意 + 關鍵字 boost），回傳 [(item, score), ...] 依分數降序。
        semantic_weight 由 config.SEMANTIC_WEIGHT 控制（預設 0.7）。
        """
        if self._engine is None:
            logger.warning("hybrid_search 呼叫時 SearchEngine 尚未初始化，fallback 到 search()")
            return self.search(query_embedding, top_k=top_k, category=category)

        raw_results = self._engine.search(
            query=query,
            query_embedding=query_embedding,
            top_k=top_k,
            category=category,
            min_score=min_score,
        )

        # 將 qa_dict 映射回 QAItem（用 id 對應）
        id_to_item = {item.id: item for item in self.items}
        output: list[tuple[QAItem, float]] = []
        for qa_dict, score in raw_results:
            item = id_to_item.get(qa_dict["id"])
            if item is not None:
                output.append((item, score))
        return output

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
