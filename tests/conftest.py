"""
Shared fixtures for FastAPI API tests.

Store is seeded with in-memory fake data — no disk I/O, no OpenAI calls by default.
"""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.store import QAItem, store


# ─────────────────────────── fake data ────────────────────────────────────────

FAKE_ITEMS: list[QAItem] = [
    QAItem(
        id=1,
        question="Discover 流量下降怎麼辦？",
        answer="可能是內容品質下降或演算法調整，建議審查最近更新的文章。",
        keywords=["Discover", "流量"],
        confidence=0.92,
        category="Discover與AMP",
        difficulty="進階",
        evergreen=True,
        source_title="SEO會議_2024-06-13",
        source_date="2024-06-13",
        is_merged=False,
    ),
    QAItem(
        id=2,
        question="canonical 設定錯誤會影響索引嗎？",
        answer="是的，canonical 指向錯誤頁面會導致正確頁面被忽略。",
        keywords=["canonical", "索引"],
        confidence=0.88,
        category="索引與檢索",
        difficulty="基礎",
        evergreen=True,
        source_title="SEO會議_2024-03-20",
        source_date="2024-03-20",
        is_merged=False,
    ),
    QAItem(
        id=3,
        question="AMP 驗證失敗如何排查？",
        answer="使用 Google AMP 測試工具，確認必要元素都存在。",
        keywords=["AMP", "驗證"],
        confidence=0.75,
        category="Discover與AMP",
        difficulty="進階",
        evergreen=False,
        source_title="SEO會議_2024-09-05",
        source_date="2024-09-05",
        is_merged=True,
    ),
]

# 每筆 item 對應一個零向量 embedding（維度 1536）
FAKE_EMBEDDINGS = np.zeros((len(FAKE_ITEMS), 1536), dtype=np.float32)


# ─────────────────────────── fixtures ─────────────────────────────────────────

@pytest.fixture
def client():
    """
    TestClient 搭配假 store。

    lifespan 會在 TestClient.__enter__ 時執行 store.load()（載入真實資料），
    因此在進入 context 後立即用 FAKE_ITEMS 覆蓋，確保測試資料隔離。
    """
    from app.main import app

    with TestClient(app) as c:
        # lifespan 已執行完畢，現在安全覆蓋
        store.items = list(FAKE_ITEMS)
        store.embeddings = FAKE_EMBEDDINGS.copy()
        yield c

    # 清空，讓下一個 fixture 從乾淨狀態開始
    store.items = []
    store.embeddings = np.empty((0, 1536), dtype=np.float32)
