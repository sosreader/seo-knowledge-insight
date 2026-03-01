"""
SearchEngine — 統一 Hybrid Search 模組

封裝語意搜尋（embedding cosine similarity）+ 關鍵字雙向匹配 boost，
供 scripts/04_generate_report.py 和 app/core/store.py 共用。

演算法：
  final_score = semantic_weight * cosine_sim + keyword_boost
  keyword_boost = 0.10 per hit (up to KW_BOOST_MAX_HITS)
      - 完整匹配: kw 出現在 query 中（+1.0 hit）
      - token 正向: query token 出現在 kw 中（+1.0 hit）
      - token 反向: kw token 出現在 query 中（+1.0 hit）
      - bigram 弱命中: kw 前兩字出現在 query（+partial/boost hit）
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

# 確保可從 scripts/ 或 app/ 任意位置 import
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    import config
except ModuleNotFoundError:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("config", _root / "config.py")
    config = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
    _spec.loader.exec_module(config)  # type: ignore[union-attr]


def compute_keyword_boost(
    queries: list[str],
    qa_pairs: list[dict[str, Any]],
    boost: float | None = None,
    max_hits: int | None = None,
    partial: float | None = None,
) -> np.ndarray:
    """
    Module-level helper：計算 shape=(n_queries, n_qa) 的關鍵字 boost 矩陣。

    四種命中方式（優先序）：
      1. kw 完整出現在 query 中
      2. query token 出現在 kw 中
      3. kw token 出現在 query 中
      4. 中文 bigram（kw 前 2 字）弱命中（給 partial 分）

    Parameters
    ----------
    queries:   查詢字串列表
    qa_pairs:  Q&A 清單，每筆需有 "keywords" 欄位
    boost:     每次命中的加分量（預設 config.KW_BOOST = 0.10）
    max_hits:  每筆 Q&A 最多累計的命中數（預設 config.KW_BOOST_MAX_HITS = 3）
    partial:   bigram 弱命中的加分量（預設 config.KW_BOOST_PARTIAL = 0.05）
    """
    boost_val: float = boost if boost is not None else float(getattr(config, "KW_BOOST", 0.10))
    max_hits_val: int = max_hits if max_hits is not None else int(getattr(config, "KW_BOOST_MAX_HITS", 3))
    partial_val: float = partial if partial is not None else float(getattr(config, "KW_BOOST_PARTIAL", 0.05))

    n_q = len(queries)
    n_qa = len(qa_pairs)
    matrix = np.zeros((n_q, n_qa), dtype=np.float32)

    for qi, query in enumerate(queries):
        query_lower = query.lower()
        query_tokens = {t for t in query_lower.split() if len(t) >= 2}
        for ji, qa in enumerate(qa_pairs):
            total_hits = 0.0
            for kw in qa.get("keywords", []):
                kw_lower = kw.lower()
                kw_tokens = {t for t in kw_lower.split() if len(t) >= 2}
                if kw_lower in query_lower:
                    total_hits += 1
                elif any(t in kw_lower for t in query_tokens):
                    total_hits += 1
                elif any(t in query_lower for t in kw_tokens):
                    total_hits += 1
                elif len(kw_lower) >= 2 and kw_lower[:2] in query_lower:
                    total_hits += (partial_val / boost_val) if boost_val else 0
            if total_hits > 0:
                matrix[qi, ji] = boost_val * min(total_hits, max_hits_val)

    return matrix


class SearchEngine:
    """
    Hybrid Search 引擎：語意相似度 + 關鍵字 boost + 同義詞加成 + 時效性調整。

    Usage:
        engine = SearchEngine(qa_pairs, qa_embeddings)
        results = engine.search("如何改善 LCP？", top_k=5)
    """

    def __init__(
        self,
        qa_pairs: list[dict[str, Any]],
        qa_embeddings: np.ndarray,
        semantic_weight: float | None = None,
    ) -> None:
        """
        Parameters
        ----------
        qa_pairs:
            Q&A 資料，每筆需有 "question", "answer", "keywords" 欄位；
            若含 "_enrichment" 欄位則啟用同義詞加成和時效性調整
        qa_embeddings:
            shape (N, embedding_dim)，對應 qa_pairs 的 embedding 向量
            可以是 raw 或已歸一化版本，本建構子會自動歸一化
        semantic_weight:
            控制語意相似度分數的權重（預設讀取 config.SEMANTIC_WEIGHT）
        """
        if len(qa_pairs) != qa_embeddings.shape[0]:
            raise ValueError(
                f"qa_pairs ({len(qa_pairs)}) 與 qa_embeddings ({qa_embeddings.shape[0]}) 數量不符"
            )

        self._qa_pairs = qa_pairs
        self._semantic_weight: float = (
            semantic_weight
            if semantic_weight is not None
            else float(getattr(config, "SEMANTIC_WEIGHT", 0.7))
        )

        embs = qa_embeddings.astype(np.float32)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self._qa_norm: np.ndarray = embs / norms

        # 預計算 enrichment 向量（從 _enrichment 欄位，防守性 .get()）
        n = len(qa_pairs)
        synonym_boost_val = float(getattr(config, "SYNONYM_BOOST", 0.05))
        self._synonym_boost_vec: np.ndarray = np.array(
            [
                synonym_boost_val if qa.get("_enrichment", {}).get("synonyms") else 0.0
                for qa in qa_pairs
            ],
            dtype=np.float32,
        )
        self._freshness_vec: np.ndarray = np.array(
            [
                float(qa.get("_enrichment", {}).get("freshness_score", 1.0))
                for qa in qa_pairs
            ],
            dtype=np.float32,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        query_embedding: list[float] | np.ndarray,
        top_k: int = 5,
        category: str | None = None,
        min_score: float = 0.20,
    ) -> list[tuple[dict[str, Any], float]]:
        """
        單查詢 Hybrid Search。

        Returns
        -------
        list of (qa_dict, final_score) sorted by score desc
        """
        scores = self._hybrid_scores(query, np.asarray(query_embedding, dtype=np.float32))

        if category:
            mask = np.array([qa.get("category", "") == category for qa in self._qa_pairs])
            scores = np.where(mask, scores, -1.0)

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            (self._qa_pairs[int(i)], float(scores[i]))
            for i in top_indices
            if scores[i] >= min_score
        ]

    def search_multi(
        self,
        queries: list[str],
        query_embeddings: np.ndarray,
        top_k_per_query: int = 3,
        total_max: int = 15,
        min_score: float = 0.28,
    ) -> list[dict[str, Any]]:
        """
        多查詢 Hybrid Search（用於週報生成）。

        Returns
        -------
        list of qa_dict（附 _score, _queries 欄位），依最高分排序，最多 total_max 筆
        """
        if not queries or len(self._qa_pairs) == 0:
            return []

        q_embs = np.asarray(query_embeddings, dtype=np.float32)
        q_norms = np.linalg.norm(q_embs, axis=1, keepdims=True)
        q_norms = np.where(q_norms == 0, 1.0, q_norms)
        q_norm = q_embs / q_norms

        # 語意相似度矩陣 (n_queries, n_qa)
        sim_matrix = q_norm @ self._qa_norm.T

        # 關鍵字 boost 矩陣
        boost_matrix = self._keyword_boost_matrix(queries)

        # 同義詞 bonus 矩陣 (n_queries, n_qa)
        synonym_bonus_matrix = np.array(
            [self._compute_synonym_bonus(q) for q in queries],
            dtype=np.float32,
        )

        # 基礎分數矩陣（語意 + 關鍵字 + 同義詞）
        base_matrix = sim_matrix * self._semantic_weight + boost_matrix + synonym_bonus_matrix

        # 時效性調整（廣播乘以 freshness_vec，shape (n_qa,)）
        score_matrix = base_matrix * self._freshness_vec[np.newaxis, :]

        collected: dict[int, dict[str, Any]] = {}
        for qi, query in enumerate(queries):
            scores = score_matrix[qi]
            top_indices = np.argsort(scores)[::-1][:top_k_per_query]
            for idx in top_indices:
                score = float(scores[idx])
                if score < min_score:
                    continue
                if idx not in collected:
                    collected[idx] = {
                        **self._qa_pairs[int(idx)],
                        "_score": score,
                        "_queries": [query],
                    }
                else:
                    if score > collected[idx]["_score"]:
                        collected[idx]["_score"] = score
                    collected[idx]["_queries"].append(query)

        results = sorted(collected.values(), key=lambda x: -x["_score"])
        return results[:total_max]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _hybrid_scores(self, query: str, query_emb: np.ndarray) -> np.ndarray:
        """計算單一查詢的 hybrid 分數向量 (N,)，含同義詞加成與時效性調整。"""
        norm = np.linalg.norm(query_emb)
        q_norm = query_emb / norm if norm > 0 else query_emb

        semantic_scores: np.ndarray = (self._qa_norm @ q_norm) * self._semantic_weight
        boost_row = self._keyword_boost_matrix([query])[0]  # (N,)

        # 同義詞命中 boost（當查詢詞出現在同義詞清單中時）
        synonym_bonus = self._compute_synonym_bonus(query)

        # 基礎分數 = 語意 + 關鍵字 boost + 同義詞 bonus
        base = semantic_scores + boost_row + synonym_bonus

        # 時效性調整（乘以 freshness_score，evergreen = 1.0 不衰減）
        return base * self._freshness_vec

    def _compute_synonym_bonus(self, query: str) -> np.ndarray:
        """
        計算同義詞命中 bonus 向量 (N,)。

        若查詢字串的任一 token 出現在 Q&A 的同義詞清單中，
        則加上 SYNONYM_BOOST 分數。
        """
        query_lower = query.lower()
        synonym_boost_val = float(getattr(config, "SYNONYM_BOOST", 0.05))
        bonus = np.zeros(len(self._qa_pairs), dtype=np.float32)

        for i, qa in enumerate(self._qa_pairs):
            enrichment = qa.get("_enrichment", {})
            synonyms = enrichment.get("synonyms", [])
            if not synonyms:
                continue
            for syn in synonyms:
                if syn.lower() in query_lower or query_lower in syn.lower():
                    bonus[i] = synonym_boost_val
                    break

        return bonus

    def _keyword_boost_matrix(self, queries: list[str]) -> np.ndarray:
        """Delegate to module-level compute_keyword_boost."""
        return compute_keyword_boost(queries, self._qa_pairs)
