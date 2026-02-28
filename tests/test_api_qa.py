"""
API tests — QA endpoints

Covers:
  GET  /health
  GET  /api/v1/qa
  GET  /api/v1/qa/categories
  GET  /api/v1/qa/{id}
"""
from __future__ import annotations

import pytest


# ─────────────────────────── /health ──────────────────────────────────────────

class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_returns_qa_count(self, client):
        resp = client.get("/health")
        assert resp.json()["qa_count"] == 3  # FAKE_ITEMS 共 3 筆


# ─────────────────────────── GET /api/v1/qa ───────────────────────────────────

class TestListQA:
    def test_default_returns_all(self, client):
        resp = client.get("/api/v1/qa")
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_response_schema(self, client):
        item = client.get("/api/v1/qa").json()["data"]["items"][0]
        required_fields = {
            "id", "question", "answer", "keywords",
            "confidence", "category", "difficulty",
            "evergreen", "source_title", "source_date", "is_merged",
        }
        assert required_fields.issubset(item.keys())

    def test_filter_by_category(self, client):
        resp = client.get("/api/v1/qa", params={"category": "Discover與AMP"})
        body = resp.json()["data"]
        assert body["total"] == 2
        assert all(i["category"] == "Discover與AMP" for i in body["items"])

    def test_filter_by_difficulty(self, client):
        resp = client.get("/api/v1/qa", params={"difficulty": "基礎"})
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["difficulty"] == "基礎"

    def test_filter_by_evergreen(self, client):
        resp = client.get("/api/v1/qa", params={"evergreen": "true"})
        body = resp.json()["data"]
        assert body["total"] == 2
        assert all(i["evergreen"] for i in body["items"])

    def test_filter_by_keyword(self, client):
        resp = client.get("/api/v1/qa", params={"keyword": "canonical"})
        body = resp.json()["data"]
        assert body["total"] == 1
        assert "canonical" in body["items"][0]["question"].lower()

    def test_pagination_limit(self, client):
        resp = client.get("/api/v1/qa", params={"limit": 2, "offset": 0})
        body = resp.json()["data"]
        assert len(body["items"]) == 2
        assert body["total"] == 3   # total 不受 limit 影響
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_pagination_offset(self, client):
        resp = client.get("/api/v1/qa", params={"limit": 2, "offset": 2})
        body = resp.json()["data"]
        assert len(body["items"]) == 1  # 總共 3 筆，offset=2 → 只剩 1 筆

    def test_invalid_difficulty_returns_422(self, client):
        resp = client.get("/api/v1/qa", params={"difficulty": "超難"})
        assert resp.status_code == 422

    def test_limit_exceeds_max_returns_422(self, client):
        resp = client.get("/api/v1/qa", params={"limit": 999})
        assert resp.status_code == 422


# ─────────────────────────── GET /api/v1/qa/categories ───────────────────────

class TestCategories:
    def test_returns_category_list(self, client):
        resp = client.get("/api/v1/qa/categories")
        assert resp.status_code == 200
        cats = resp.json()["data"]["categories"]
        assert isinstance(cats, list)
        assert "Discover與AMP" in cats
        assert "索引與檢索" in cats

    def test_sorted_by_count_descending(self, client):
        cats = client.get("/api/v1/qa/categories").json()["data"]["categories"]
        # Discover與AMP 有 2 筆，索引與檢索 有 1 筆 → Discover 應排前
        assert cats[0] == "Discover與AMP"


# ─────────────────────────── GET /api/v1/qa/{id} ─────────────────────────────

class TestGetQAItem:
    def test_existing_id_returns_item(self, client):
        resp = client.get("/api/v1/qa/1")
        assert resp.status_code == 200
        item = resp.json()["data"]
        assert item["id"] == 1
        assert "Discover" in item["question"]

    def test_response_includes_all_fields(self, client):
        item = client.get("/api/v1/qa/2").json()["data"]
        assert item["category"] == "索引與檢索"
        assert item["difficulty"] == "基礎"
        assert item["evergreen"] is True

    def test_nonexistent_id_returns_404(self, client):
        resp = client.get("/api/v1/qa/9999")
        assert resp.status_code == 404

    def test_invalid_id_type_returns_422(self, client):
        resp = client.get("/api/v1/qa/abc")
        assert resp.status_code == 422
