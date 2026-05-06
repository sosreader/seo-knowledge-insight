"""Tests for utils/maturity_llm_judge.py — LLM gate for L4 validation."""

from unittest.mock import MagicMock, patch

import pytest

from utils.maturity_llm_judge import llm_validate_l4


class TestLLMValidateL4:
    """L4 LLM gate behaviour with various API/cache states."""

    def test_no_api_key_returns_true(self, monkeypatch):
        """Without OPENAI_API_KEY, judge must NOT demote (returns True)."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        result = llm_validate_l4(
            question="什麼是 AI Overview？",
            answer="AI Overview 是 Google 的 AI 摘要功能。",
            keywords=["AI Overview"],
        )
        assert result is True

    def test_blank_api_key_returns_true(self, monkeypatch):
        """Whitespace-only OPENAI_API_KEY is treated as missing."""
        monkeypatch.setenv("OPENAI_API_KEY", "   ")
        result = llm_validate_l4(
            question="q",
            answer="a",
            keywords=[],
        )
        assert result is True

    def test_cache_hit_short_circuits_llm(self, monkeypatch):
        """Cache hit must skip the OpenAI call entirely."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        with patch(
            "utils.pipeline_cache.cache_get",
            return_value={"is_l4": False, "reason": "cached demote"},
        ), patch("utils.openai_helper._client") as mock_client, patch(
            "utils.pipeline_cache.cache_set"
        ) as mock_set:
            result = llm_validate_l4("q", "a", ["k"])
        assert result is False
        mock_client.assert_not_called()
        mock_set.assert_not_called()

    def test_llm_says_true_passes_through(self, monkeypatch):
        """LLM is_l4=true must return True and write the cache."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_resp = MagicMock()
        fake_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"is_l4": true, "reason": "完整實作架構"}'
                )
            )
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_resp
        with patch("utils.pipeline_cache.cache_get", return_value=None), patch(
            "utils.openai_helper._client", return_value=fake_client
        ), patch("utils.pipeline_cache.cache_set") as mock_set:
            result = llm_validate_l4("q", "a", ["k"])
        assert result is True
        mock_set.assert_called_once()

    def test_llm_says_false_signals_demote(self, monkeypatch):
        """LLM is_l4=false must return False so the caller demotes to L3."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_resp = MagicMock()
        fake_resp.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"is_l4": false, "reason": "純概念解釋"}'
                )
            )
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_resp
        with patch("utils.pipeline_cache.cache_get", return_value=None), patch(
            "utils.openai_helper._client", return_value=fake_client
        ), patch("utils.pipeline_cache.cache_set"):
            result = llm_validate_l4("q", "a", ["k"])
        assert result is False

    def test_llm_failure_keeps_l4(self, monkeypatch):
        """Network/parse failure must NOT demote — keep rule-layer L4."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError(
            "network timeout"
        )
        with patch("utils.pipeline_cache.cache_get", return_value=None), patch(
            "utils.openai_helper._client", return_value=fake_client
        ):
            result = llm_validate_l4("q", "a", ["k"])
        assert result is True

    def test_malformed_json_keeps_l4(self, monkeypatch):
        """Malformed JSON from LLM falls back to keeping L4."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        fake_resp = MagicMock()
        fake_resp.choices = [
            MagicMock(message=MagicMock(content="not-valid-json"))
        ]
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = fake_resp
        with patch("utils.pipeline_cache.cache_get", return_value=None), patch(
            "utils.openai_helper._client", return_value=fake_client
        ):
            result = llm_validate_l4("q", "a", ["k"])
        assert result is True
