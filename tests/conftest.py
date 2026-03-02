"""
Shared fixtures for FastAPI API tests.

Store is seeded with in-memory fake data — no disk I/O, no OpenAI calls by default.
"""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.store import QAItem, store

# 測試用 API Key — conftest 啟動前先注入 env，讓 config.API_KEY 讀到此值
_TEST_API_KEY = "test-secret-key"
API_KEY_HEADER = {"X-API-Key": _TEST_API_KEY}


# ─────────────────────────── fake data ────────────────────────────────────────

FAKE_ITEMS: list[QAItem] = [
    QAItem(
        id=1,
        stable_id="a1b2c3d4e5f60001",
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
        stable_id="a1b2c3d4e5f60002",
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
        stable_id="a1b2c3d4e5f60003",
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
def client(monkeypatch):
    """
    TestClient 搭配假 store，並注入測試用 API key。

    lifespan 會在 TestClient.__enter__ 時執行 store.load()（載入真實資料），
    因此在進入 context 後立即用 FAKE_ITEMS 覆蓋，確保測試資料隔離。
    """
    monkeypatch.setenv("SEO_API_KEY", _TEST_API_KEY)
    monkeypatch.delenv("LMNR_PROJECT_API_KEY", raising=False)
    # 同步更新已載入的 config 模組
    import app.config as app_config
    monkeypatch.setattr(app_config, "API_KEY", _TEST_API_KEY)

    from app.main import app

    with TestClient(app) as c:
        # lifespan 已執行完畢，現在安全覆蓋
        store.items = list(FAKE_ITEMS)
        store.embeddings = FAKE_EMBEDDINGS.copy()
        # _id_index 必須與 items 同步，否則 get_item_by_id() 會查到舊資料
        store._id_index = {item.id: item for item in store.items}
        # 預設帶入 API key header，讓所有 API 測試不需逐一補 header
        c.headers.update(API_KEY_HEADER)
        yield c

    # 清空，讓下一個 fixture 從乾淨狀態開始
    store.items = []
    store.embeddings = np.empty((0, 1536), dtype=np.float32)
    store._id_index = {}
