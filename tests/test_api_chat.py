"""
API tests — Chat endpoint

Covers:
  POST /api/v1/chat

OpenAI embedding + completion 呼叫全部 mock，避免真實 API 費用。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


_MOCK_EMBEDDING = np.ones(1536, dtype=np.float32) / np.sqrt(1536)

_MOCK_ANSWER = "根據知識庫，Discover 流量下降通常與內容品質或演算法調整有關。"


def _make_completion_mock(content: str = _MOCK_ANSWER):
    """建構一個最小可用的 chat.completions.create 回傳物件。"""
    choice = SimpleNamespace(
        message=SimpleNamespace(content=content)
    )
    return SimpleNamespace(choices=[choice])


@pytest.fixture
def mock_openai():
    """同時 mock embedding 和 chat completion。"""
    with (
        patch("app.core.chat.get_embedding", new=AsyncMock(return_value=_MOCK_EMBEDDING)),
        patch(
            "app.core.chat._client.chat.completions.create",
            new=AsyncMock(return_value=_make_completion_mock()),
        ),
    ):
        yield


# ─────────────────────────── POST /api/v1/chat ────────────────────────────────

class TestChat:
    def test_returns_answer_and_sources(self, client, mock_openai):
        resp = client.post("/api/v1/chat", json={"message": "Discover 流量怎麼了？"})
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert "answer" in body
        assert "sources" in body
        assert isinstance(body["answer"], str)
        assert len(body["answer"]) > 0

    def test_sources_schema(self, client, mock_openai):
        resp = client.post("/api/v1/chat", json={"message": "canonical 設定問題"})
        assert resp.status_code == 200
        for src in resp.json()["data"]["sources"]:
            required = {"id", "question", "category", "source_title", "source_date", "score"}
            assert required.issubset(src.keys())
            assert 0.0 <= src["score"] <= 1.0

    def test_with_history(self, client, mock_openai):
        history = [
            {"role": "user", "content": "AMP 是什麼？"},
            {"role": "assistant", "content": "AMP 是加速行動頁面的技術。"},
        ]
        resp = client.post(
            "/api/v1/chat",
            json={"message": "那 AMP 驗證失敗怎麼辦？", "history": history},
        )
        assert resp.status_code == 200
        assert "answer" in resp.json()["data"]

    def test_empty_history_is_allowed(self, client, mock_openai):
        resp = client.post(
            "/api/v1/chat",
            json={"message": "SEO 基礎問題", "history": []},
        )
        assert resp.status_code == 200

    def test_empty_message_returns_422(self, client):
        resp = client.post("/api/v1/chat", json={"message": ""})
        assert resp.status_code == 422

    def test_message_too_long_returns_422(self, client):
        resp = client.post("/api/v1/chat", json={"message": "x" * 2001})
        assert resp.status_code == 422

    def test_invalid_history_role_returns_422(self, client):
        resp = client.post(
            "/api/v1/chat",
            json={
                "message": "問題",
                "history": [{"role": "system", "content": "..."}],  # system 不允許
            },
        )
        assert resp.status_code == 422

    def test_history_exceeds_max_returns_422(self, client):
        history = [
            {"role": "user", "content": f"訊息{i}"}
            for i in range(21)  # max_length=20
        ]
        resp = client.post(
            "/api/v1/chat",
            json={"message": "最後問題", "history": history},
        )
        assert resp.status_code == 422

    def test_missing_message_returns_422(self, client):
        resp = client.post("/api/v1/chat", json={})
        assert resp.status_code == 422

    def test_gpt_empty_response_returns_answer(self, client, mock_openai):
        """GPT 回傳空字串時，answer 應為空字串而非 crash。"""
        with patch(
            "app.core.chat._client.chat.completions.create",
            new=AsyncMock(return_value=_make_completion_mock(content="")),
        ):
            resp = client.post("/api/v1/chat", json={"message": "測試問題"})
        assert resp.status_code == 200
        assert resp.json()["data"]["answer"] == ""
