"""
從 03_dedupe_classify.py 抽出的純邏輯函式，方便測試和重用。
"""
from __future__ import annotations

import numpy as np


def _cosine_similarity_matrix(embeddings: list[list[float]]) -> np.ndarray:
    """用 numpy 向量化計算全量 cosine similarity 矩陣"""
    mat = np.array(embeddings)  # (n, dim)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    # 避免零向量除以零
    norms = np.where(norms == 0, 1.0, norms)
    normalized = mat / norms
    return normalized @ normalized.T  # (n, n)
