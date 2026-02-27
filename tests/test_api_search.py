"""
API tests — Search endpoint

Covers:
  POST /api/v1/search

OpenAI embedding 呼叫用 patch mock，避免真實 API 費用。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import numpy as np
import pytest


# mock embedding：回傳一個非零向量，讓 cosine similarity 有值
_MOCK_EMBEDDING = np.ones(1536, dtype=np.float32) / np.sqrt(1536)


@pytest.fixture
def mock_embedding():
    with patch("app.core.chat.get_embedding", new=AsyncMock(return_value=_MOCK_EMBEDDING)):
        yield


# ─────────────────────────── POST /api/v1/search ──────────────────────────────

class TestSearch:
    def test_returns_results(self, client, mock_embedding):
        resp = client.post("/api/v1/search", json={"query": "Discover 流量"})
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert "total" in body
        assert body["total"] == len(body["results"])

    def test_result_schema(self, client, mock_embedding):
        resp = client.post("/api/v1/search", json={"query": "canonical"})
        assert resp.status_code == 200
        if resp.json()["total"] > 0:
            item = resp.json()["results"][0]
            required = {
                "id", "question", "answer", "keywords",
                "category", "difficulty", "evergreen",
                "source_title", "source_date", "score",
            }
            assert required.issubset(item.keys())

    def test_score_between_0_and_1(self, client, mock_embedding):
        resp = client.post("/api/v1/search", json={"query": "AMP"})
        for result in resp.json()["results"]:
            assert 0.0 <= result["score"] <= 1.0

    def test_top_k_limit(self, client, mock_embedding):
        resp = client.post("/api/v1/search", json={"query": "SEO", "top_k": 2})
        assert resp.status_code == 200
        assert len(resp.json()["results"]) <= 2

    def test_category_filter(self, client, mock_embedding):
        resp = client.post(
            "/api/v1/search",
            json={"query": "AMP", "top_k": 5, "category": "Discover與AMP"},
        )
        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert r["category"] == "Discover與AMP"

    def test_empty_query_returns_422(self, client):
        resp = client.post("/api/v1/search", json={"query": ""})
        assert resp.status_code == 422

    def test_query_too_long_returns_422(self, client):
        resp = client.post("/api/v1/search", json={"query": "x" * 501})
        assert resp.status_code == 422

    def test_top_k_zero_returns_422(self, client):
        resp = client.post("/api/v1/search", json={"query": "SEO", "top_k": 0})
        assert resp.status_code == 422

    def test_top_k_exceeds_max_returns_422(self, client):
        resp = client.post("/api/v1/search", json={"query": "SEO", "top_k": 99})
        assert resp.status_code == 422

    def test_missing_query_returns_422(self, client):
        resp = client.post("/api/v1/search", json={"top_k": 3})
        assert resp.status_code == 422
