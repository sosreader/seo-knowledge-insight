"""
API Security tests — Phase A (Auth) + Phase C (Exception Handler)

Covers:
  - 無 header → 401
  - 錯誤 key → 401
  - 正確 key → 200
  - 未捕獲例外不洩漏 traceback
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.store import store
from tests.conftest import FAKE_EMBEDDINGS, FAKE_ITEMS, _TEST_API_KEY


def _setup_fake_store() -> None:
    """3 個 fixture 共用的 store 初始化邏輯。"""
    store.items = list(FAKE_ITEMS)
    store.embeddings = FAKE_EMBEDDINGS.copy()
    store._id_index = {item.id: item for item in store.items}

_VALID_KEY = _TEST_API_KEY
_INVALID_KEY = "wrong-key"


@pytest.fixture
def auth_client(monkeypatch):
    """預設帶正確 API Key 的 client。"""
    monkeypatch.setenv("SEO_API_KEY", _VALID_KEY)
    import app.config as app_config
    monkeypatch.setattr(app_config, "API_KEY", _VALID_KEY)

    from app.main import app

    with TestClient(app) as c:
        _setup_fake_store()
        c.headers.update({"X-API-Key": _VALID_KEY})
        yield c


@pytest.fixture
def no_auth_client(monkeypatch):
    """不帶 API Key 的 client，SEO_API_KEY 已設定（啟用認證）。"""
    monkeypatch.setenv("SEO_API_KEY", _VALID_KEY)
    import app.config as app_config
    monkeypatch.setattr(app_config, "API_KEY", _VALID_KEY)

    from app.main import app

    with TestClient(app) as c:
        _setup_fake_store()
        yield c


# ─────────────────────────── Phase A：Auth ────────────────────────────────────

class TestApiKeyAuth:
    def test_no_key_returns_401(self, no_auth_client):
        resp = no_auth_client.get("/api/v1/qa")
        assert resp.status_code == 401

    def test_wrong_key_returns_401(self, no_auth_client):
        resp = no_auth_client.get("/api/v1/qa", headers={"X-API-Key": _INVALID_KEY})
        assert resp.status_code == 401

    def test_correct_key_returns_200(self, auth_client):
        resp = auth_client.get("/api/v1/qa")
        assert resp.status_code == 200

    def test_401_body_does_not_leak_traceback(self, no_auth_client):
        resp = no_auth_client.get("/api/v1/qa")
        body = resp.json()
        # 確認沒有 traceback 資訊洩漏
        assert "traceback" not in str(body).lower()
        assert "exception" not in str(body).lower()

    def test_health_does_not_require_auth(self, no_auth_client):
        """健康檢查 endpoint 不需要認證。"""
        resp = no_auth_client.get("/health")
        assert resp.status_code == 200

    def test_search_requires_auth(self, no_auth_client):
        resp = no_auth_client.post("/api/v1/search", json={"query": "SEO"})
        assert resp.status_code == 401

    def test_chat_requires_auth(self, no_auth_client):
        resp = no_auth_client.post("/api/v1/chat", json={"message": "SEO 問題"})
        assert resp.status_code == 401

    def test_qa_single_requires_auth(self, no_auth_client):
        resp = no_auth_client.get("/api/v1/qa/1")
        assert resp.status_code == 401

    def test_qa_categories_requires_auth(self, no_auth_client):
        resp = no_auth_client.get("/api/v1/qa/categories")
        assert resp.status_code == 401


# ─────────────────────────── Phase C：Exception Handler ─────────────────────

class TestExceptionHandler:
    def test_unhandled_exception_returns_500_without_traceback(self, monkeypatch):
        """模擬 store 拋出非預期例外，確認不洩漏 traceback。"""
        monkeypatch.setenv("SEO_API_KEY", _VALID_KEY)
        import app.config as app_config
        monkeypatch.setattr(app_config, "API_KEY", _VALID_KEY)

        from app.main import app

        # raise_server_exceptions=False 讓我們能接到 500 response 而非 Python exception
        with TestClient(app, raise_server_exceptions=False) as c:
            _setup_fake_store()
            c.headers.update({"X-API-Key": _VALID_KEY})

            with patch("app.core.store.store.list_qa", side_effect=RuntimeError("boom")):
                resp = c.get("/api/v1/qa")

        assert resp.status_code == 500
        body = resp.json()
        assert body["data"] is None
        assert body["error"] == "Internal server error"
        assert "boom" not in str(body)
        assert "RuntimeError" not in str(body)
        assert "Traceback" not in str(body)


# ─────────────────────────── Phase D：Response Envelope ──────────────────────

class TestResponseEnvelope:
    def test_successful_response_has_data_key(self, auth_client):
        resp = auth_client.get("/api/v1/qa")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "error" in body
        assert "meta" in body
        assert body["error"] is None

    def test_meta_has_request_id_and_version(self, auth_client):
        resp = auth_client.get("/api/v1/qa")
        meta = resp.json()["meta"]
        assert "request_id" in meta
        assert "version" in meta
        # request_id 應是 UUID 格式
        uuid.UUID(meta["request_id"])  # 若格式錯誤會拋例外


# ─────────────────────────── Phase C：Feedback Endpoint ──────────────────────

class TestFeedbackEndpoint:
    def test_helpful_feedback_returns_200(self, auth_client, tmp_path, monkeypatch):
        """POST /api/v1/feedback 回應 200 且包含 ApiResponse 結構。"""
        import utils.learning_store as ls_mod
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", tmp_path / "learnings.jsonl")
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"query": "canonical 問題", "qa_id": 2, "feedback": "helpful"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["error"] is None

    def test_not_relevant_feedback_recorded(self, auth_client, tmp_path, monkeypatch):
        """not_relevant feedback 應寫入 learning store。"""
        import utils.learning_store as ls_mod
        log_path = tmp_path / "learnings.jsonl"
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", log_path)
        auth_client.post(
            "/api/v1/feedback",
            json={"query": "不相關的測試查詢", "qa_id": 1, "feedback": "not_relevant"},
        )
        assert log_path.exists()
        import json
        records = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
        assert len(records) >= 1
        assert records[0]["feedback"] == "not_relevant"

    def test_missing_query_returns_422(self, auth_client):
        """缺少必填欄位 query 應回 422。"""
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"qa_id": 1, "feedback": "helpful"},
        )
        assert resp.status_code == 422

    def test_invalid_feedback_type_returns_422(self, auth_client):
        """feedback 欄位只接受 helpful / not_relevant。"""
        resp = auth_client.post(
            "/api/v1/feedback",
            json={"query": "q", "qa_id": 1, "feedback": "invalid_type"},
        )
        assert resp.status_code == 422


# ─────────────────────────── Phase C：LearningStore ──────────────────────────

class TestLearningStore:
    def test_record_miss_writes_jsonl(self, tmp_path, monkeypatch):
        """record_miss() 應寫入 JSONL 記錄。"""
        import utils.learning_store as ls_mod
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", tmp_path / "learnings.jsonl")
        from utils.learning_store import LearningStore
        ls = LearningStore()
        ls.record_miss("canonical 設定問題", top_score=0.15, context="search")
        records = ls._load_all()
        assert len(records) == 1
        assert records[0]["query"] == "canonical 設定問題"

    def test_get_relevant_learnings_returns_list(self, tmp_path, monkeypatch):
        """get_relevant_learnings() 對有匹配的查詢應回傳非空 list。"""
        import utils.learning_store as ls_mod
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", tmp_path / "learnings.jsonl")
        from utils.learning_store import LearningStore
        ls = LearningStore()
        ls.record_miss("canonical SEO 設定", top_score=0.10, context="search")
        results = ls.get_relevant_learnings("canonical 問題")
        assert isinstance(results, list)

    def test_record_miss_idempotent_context(self, tmp_path, monkeypatch):
        """多次 record_miss() 應累積記錄（JSONL append）。"""
        import utils.learning_store as ls_mod
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", tmp_path / "learnings.jsonl")
        from utils.learning_store import LearningStore
        ls = LearningStore()
        ls.record_miss("query1", top_score=0.1, context="search")
        ls.record_miss("query2", top_score=0.2, context="chat")
        assert len(ls._load_all()) == 2

    def test_load_all_empty_when_no_file(self, tmp_path, monkeypatch):
        """若 JSONL 不存在，_load_all() 應回傳空 list。"""
        import utils.learning_store as ls_mod
        monkeypatch.setattr(ls_mod, "_LEARNINGS_PATH", tmp_path / "learnings.jsonl")
        from utils.learning_store import LearningStore
        ls = LearningStore()
        assert ls._load_all() == []
