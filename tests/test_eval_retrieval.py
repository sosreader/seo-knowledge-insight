"""Unit tests for evals/eval_retrieval.py loading and filtering behavior."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

with patch.dict("sys.modules", {"lmnr": MagicMock()}):
    import evals.eval_retrieval as mod
    importlib.reload(mod)


class TestLocalModelSupport:
    def test_supports_no_model_filter(self):
        assert mod._local_items_support_model_filter([{"question": "Q"}], None) is True

    def test_rejects_model_filter_when_local_items_lack_model(self):
        assert mod._local_items_support_model_filter([{"question": "Q"}], "claude-code") is False

    def test_accepts_model_filter_when_any_item_has_model(self):
        items = [{"question": "Q1"}, {"question": "Q2", "extraction_model": "claude-code"}]
        assert mod._local_items_support_model_filter(items, "claude-code") is True


class TestSupabaseLoad:
    def test_fetch_supabase_qa_items_paginates(self):
        first = Mock(status_code=200)
        first.json.return_value = [{"id": f"id-{i}", "extraction_model": "claude-code"} for i in range(1000)]
        second = Mock(status_code=200)
        second.json.return_value = [{"id": f"id-{1000 + i}", "extraction_model": "claude-code"} for i in range(329)]
        with patch.object(mod.requests, "get", side_effect=[first, second]) as mock_get:
            items = mod._fetch_supabase_qa_items("https://example.supabase.co", "anon")

            assert len(items) == 1329
            assert mock_get.call_count == 2
            assert "offset=1000" in mock_get.call_args_list[1].args[0]
            assert "extraction_model" in mock_get.call_args_list[0].args[0]


class TestLoadQaItems:
    def test_loads_local_file_when_model_filter_not_requested(self, tmp_path):
        qa_path = tmp_path / "output" / "qa_final.json"
        qa_path.parent.mkdir(parents=True)
        qa_path.write_text(json.dumps({"qa_database": [{"question": "Q1"}]}), encoding="utf-8")

        with patch.object(mod, "PROJECT_ROOT", tmp_path), patch.object(mod, "_filter_model", None):
            items = mod._load_qa_items()

        assert len(items) == 1
        assert items[0]["question"] == "Q1"

    @patch.object(mod, "_fetch_supabase_qa_items")
    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_ANON_KEY": "anon"}, clear=False)
    def test_falls_back_to_supabase_when_model_filter_requested_but_local_has_no_model(self, mock_fetch, tmp_path):
        qa_path = tmp_path / "output" / "qa_final.json"
        qa_path.parent.mkdir(parents=True)
        qa_path.write_text(json.dumps({"qa_database": [{"question": "Q1"}]}), encoding="utf-8")
        mock_fetch.return_value = [{"question": "Q2", "extraction_model": "claude-code"}]

        with patch.object(mod, "PROJECT_ROOT", tmp_path), patch.object(mod, "_filter_model", "claude-code"):
            items = mod._load_qa_items()

        assert len(items) == 1
        assert items[0]["extraction_model"] == "claude-code"
        mock_fetch.assert_called_once_with("https://example.supabase.co", "anon")