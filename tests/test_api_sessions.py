"""Tests for /api/v1/sessions endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.core.session_store import FileSessionStore


@pytest.fixture
def sessions_dir(tmp_path):
    """Provide a temp dir and patch session_store to use it."""
    temp_store = FileSessionStore(base_dir=tmp_path)
    with patch("app.routers.sessions.session_store", temp_store):
        yield tmp_path, temp_store


class TestListSessions:
    def test_empty_list(self, client, sessions_dir):
        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_sessions(self, client, sessions_dir):
        _, store = sessions_dir
        store.create_session(title="Session A")
        store.create_session(title="Session B")

        resp = client.get("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_pagination(self, client, sessions_dir):
        _, store = sessions_dir
        for i in range(5):
            store.create_session(title=f"Session {i}")

        resp = client.get("/api/v1/sessions?limit=2&offset=0")
        data = resp.json()["data"]
        assert len(data["items"]) == 2
        assert data["total"] == 5

        resp2 = client.get("/api/v1/sessions?limit=2&offset=4")
        data2 = resp2.json()["data"]
        assert len(data2["items"]) == 1


class TestCreateSession:
    def test_create_with_title(self, client, sessions_dir):
        resp = client.post("/api/v1/sessions", json={"title": "My Chat"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "My Chat"
        assert "id" in data
        assert data["messages"] == []

    def test_create_without_body(self, client, sessions_dir):
        resp = client.post("/api/v1/sessions")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["title"] == "New Chat"

    def test_title_sanitized_to_50_chars(self, client, sessions_dir):
        long_title = "B" * 80  # within schema max_length=100
        resp = client.post("/api/v1/sessions", json={"title": long_title})
        assert resp.status_code == 200
        # _sanitize_title truncates to 50 chars
        assert len(resp.json()["data"]["title"]) <= 50

    def test_title_over_schema_limit_rejected(self, client, sessions_dir):
        resp = client.post("/api/v1/sessions", json={"title": "A" * 200})
        assert resp.status_code == 422


class TestGetSession:
    def test_existing_session(self, client, sessions_dir):
        _, store = sessions_dir
        session = store.create_session(title="Test")

        resp = client.get(f"/api/v1/sessions/{session.id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == session.id
        assert data["title"] == "Test"

    def test_nonexistent_session(self, client, sessions_dir):
        resp = client.get("/api/v1/sessions/00000000-0000-4000-8000-000000000000")
        assert resp.status_code == 404

    def test_invalid_uuid_format(self, client, sessions_dir):
        resp = client.get("/api/v1/sessions/not-a-uuid")
        assert resp.status_code == 404


class TestDeleteSession:
    def test_delete_existing(self, client, sessions_dir):
        _, store = sessions_dir
        session = store.create_session(title="To Delete")

        resp = client.delete(f"/api/v1/sessions/{session.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

        # Verify it's gone
        resp2 = client.get(f"/api/v1/sessions/{session.id}")
        assert resp2.status_code == 404

    def test_delete_nonexistent(self, client, sessions_dir):
        resp = client.delete("/api/v1/sessions/00000000-0000-4000-8000-000000000000")
        assert resp.status_code == 404


class TestSendMessage:
    def test_send_message_triggers_rag(self, client, sessions_dir):
        _, store = sessions_dir
        session = store.create_session(title="Chat")

        mock_result = {
            "answer": "SEO is important.",
            "sources": [{"id": "abc", "score": 0.9}],
        }
        with patch("app.routers.sessions.rag_chat", new_callable=AsyncMock) as mock_rag:
            mock_rag.return_value = mock_result
            resp = client.post(
                f"/api/v1/sessions/{session.id}/messages",
                json={"message": "What is SEO?"},
            )

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["answer"] == "SEO is important."
        assert len(data["sources"]) == 1
        # Session should have 2 messages (user + assistant)
        assert len(data["session"]["messages"]) == 2
        assert data["session"]["messages"][0]["role"] == "user"
        assert data["session"]["messages"][1]["role"] == "assistant"

    def test_send_to_nonexistent_session(self, client, sessions_dir):
        resp = client.post(
            "/api/v1/sessions/00000000-0000-4000-8000-000000000000/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 404

    def test_empty_message_rejected(self, client, sessions_dir):
        _, store = sessions_dir
        session = store.create_session(title="Chat")

        resp = client.post(
            f"/api/v1/sessions/{session.id}/messages",
            json={"message": ""},
        )
        assert resp.status_code == 422


class TestSessionStore:
    """Unit tests for FileSessionStore (not API level)."""

    def test_max_messages_limit(self, tmp_path):
        store = FileSessionStore(base_dir=tmp_path)
        session = store.create_session(title="Full")

        from app.core.session_store import MAX_MESSAGES_PER_SESSION, SessionMessage

        for i in range(MAX_MESSAGES_PER_SESSION):
            msg = SessionMessage(role="user", content=f"Message {i}")
            result = store.add_message(session.id, msg)
            assert result is not None

        # Next message should be rejected
        overflow = SessionMessage(role="user", content="Overflow")
        result = store.add_message(session.id, overflow)
        assert result is None

    def test_path_traversal_blocked(self, tmp_path):
        store = FileSessionStore(base_dir=tmp_path)
        # Invalid UUID should raise ValueError internally, return None
        assert store.get_session("../../etc/passwd") is None
        assert store.delete_session("../../../evil") is False

    def test_title_xss_sanitized(self, tmp_path):
        store = FileSessionStore(base_dir=tmp_path)
        session = store.create_session(title='<script>alert("xss")</script>')
        assert "<script>" not in session.title
        assert "&lt;script&gt;" in session.title
