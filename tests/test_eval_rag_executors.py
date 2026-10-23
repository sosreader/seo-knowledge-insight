"""Executors of evals that talk to rag-api: URL/header assembly, 501 llm_disabled, fallbacks."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evals import rag_client  # noqa: E402

with patch.dict("sys.modules", {"lmnr": MagicMock()}), \
        patch.object(rag_client, "llm_available", return_value=True):
    import evals.eval_chat as chat
    import evals.eval_chat_maturity as chat_maturity
    import evals.eval_dedup as dedup
    import evals.eval_meeting_prep_grounding as grounding
    import evals.eval_qa_classification as qa_class

CF_ENV = {
    "RAG_API_BASE": "https://warehouse-api.vocus.cc/internal/rag",
    "CF_ACCESS_CLIENT_ID": "id",
    "CF_ACCESS_CLIENT_SECRET": "sec",
}


@pytest.fixture(autouse=True)
def _rag_env(monkeypatch):
    for key in ("RAG_API_BASE", "CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "SEO_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for key, value in CF_ENV.items():
        monkeypatch.setenv(key, value)


def _resp(status: int, body: object = None) -> MagicMock:
    resp = MagicMock(status_code=status, text="")
    resp.json.return_value = body
    return resp


LLM_OFF = {"data": None, "error": "llm_disabled"}


class TestChatExecutor:
    def test_posts_to_rag_chat_with_cf_headers(self):
        body = {"data": {"answer": "a" * 60, "sources": [{"category": "c"}], "mode": "rag"}}
        with patch.object(rag_client.requests, "post", return_value=_resp(200, body)) as post:
            out = chat.chat_executor({"question": "q"})
        assert post.call_args.args[0] == "https://warehouse-api.vocus.cc/internal/rag/chat"
        assert post.call_args.kwargs["headers"]["CF-Access-Client-Id"] == "id"
        assert post.call_args.kwargs["json"] == {"message": "q", "history": []}
        assert out["source_count"] == 1
        assert out["mode"] == "rag"

    def test_llm_disabled_maps_to_marker_mode(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(501, LLM_OFF)):
            out = chat.chat_executor({"question": "q"})
        assert out == {"answer": "", "sources": [], "source_count": 0, "mode": "llm_disabled"}

    def test_other_status_is_error_mode(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(500, {})):
            assert chat.chat_executor({"question": "q"})["mode"] == "error"

    def test_connection_error_is_error_mode(self):
        with patch.object(rag_client.requests, "post", side_effect=requests.ConnectionError()):
            assert chat.chat_executor({"question": "q"})["mode"] == "error"

    def test_unexpected_error_is_error_mode(self):
        with patch.object(rag_client.requests, "post", side_effect=RuntimeError("x")):
            assert chat.chat_executor({"question": "q"})["mode"] == "error"


class TestChatMaturityExecutor:
    def test_posts_maturity_level(self):
        body = {"data": {"answer": "hello", "mode": "rag"}}
        with patch.object(rag_client.requests, "post", return_value=_resp(200, body)) as post:
            out = chat_maturity.chat_executor({"query": "q", "maturity_level": "L2"})
        assert post.call_args.args[0].endswith("/internal/rag/chat")
        assert post.call_args.kwargs["json"] == {"message": "q", "maturity_level": "L2"}
        assert out == {"answer": "hello", "mode": "rag"}

    def test_llm_disabled(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(501, LLM_OFF)):
            out = chat_maturity.chat_executor({"query": "q", "maturity_level": "L1"})
        assert out == {"answer": "", "mode": "llm_disabled"}

    def test_http_error(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(502, {})):
            out = chat_maturity.chat_executor({"query": "q", "maturity_level": "L1"})
        assert out["mode"] == "error"
        assert "502" in out["error"]

    def test_exception(self):
        with patch.object(rag_client.requests, "post", side_effect=RuntimeError("x")):
            assert chat_maturity.chat_executor({"query": "q", "maturity_level": "L1"})["mode"] == "error"


class TestSearchBackedExecutors:
    def test_dedup_uses_rag_search_without_mode(self):
        body = {"data": {"results": [{"id": "1", "category": "c"}, {"id": "2", "category": "d"}]}}
        with patch.object(rag_client.requests, "post", return_value=_resp(200, body)) as post:
            out = dedup.dedup_executor({"question_a": "a", "question_b": "b"})
        assert post.call_args.args[0] == "https://warehouse-api.vocus.cc/internal/rag/search"
        assert "mode" not in post.call_args.kwargs["json"]
        assert out["jaccard"] == 1.0
        assert out["results_a_count"] == 2

    def test_dedup_when_api_unusable_returns_zero_counts(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(403, {})):
            out = dedup.dedup_executor({"question_a": "a", "question_b": "b"})
        assert out["results_a_count"] == 0
        assert out["results_b_count"] == 0

    def test_qa_classification_returns_top_result_fields(self):
        results = [{"category": "c", "difficulty": "d", "evergreen": True, "question": "q"}, {"category": "x"}]
        body = {"data": {"results": results}}
        with patch.object(rag_client.requests, "post", return_value=_resp(200, body)) as post:
            out = qa_class.qa_search_executor({"question": "q"})
        assert post.call_args.kwargs["json"] == {"query": "q", "top_k": 3}
        assert out == {"category": "c", "difficulty": "d", "evergreen": True, "question": "q", "result_count": 2}

    def test_qa_classification_empty_on_failure(self):
        with patch.object(rag_client.requests, "post", return_value=_resp(500, {})):
            out = qa_class.qa_search_executor({"question": "q"})
        assert out["category"] == ""
        assert out["result_count"] == 0


class TestLlmEvalsSkipOn501:
    @pytest.mark.parametrize("name", ["eval_chat", "eval_chat_maturity"])
    def test_module_import_exits_zero_when_llm_disabled(self, name, capsys):
        # patch.dict restores sys.modules on exit, so the fresh import leaves no trace.
        with patch.dict("sys.modules", {"lmnr": MagicMock()}), \
                patch.object(rag_client.requests, "post", return_value=_resp(501, LLM_OFF)):
            sys.modules.pop(f"evals.{name}", None)
            with pytest.raises(SystemExit) as exc:
                importlib.import_module(f"evals.{name}")
        assert exc.value.code == 0
        assert "SKIP" in capsys.readouterr().err

    @pytest.mark.parametrize("name", ["eval_chat", "eval_chat_maturity"])
    def test_module_import_runs_evaluate_when_llm_enabled(self, name):
        lmnr_mock = MagicMock()
        with patch.dict("sys.modules", {"lmnr": lmnr_mock}), \
                patch.object(rag_client.requests, "post", return_value=_resp(200, {})):
            sys.modules.pop(f"evals.{name}", None)
            importlib.import_module(f"evals.{name}")
        lmnr_mock.evaluate.assert_called_once()


class TestGroundingKbLookup:
    def setup_method(self):
        grounding._remote_kb_cache.clear()

    def test_local_index_wins_without_network(self):
        with patch.object(rag_client, "fetch_qa_item") as fetch:
            assert grounding._resolve_kb_item("a", {"a": {"category": "c"}}) == {"category": "c"}
        fetch.assert_not_called()

    def test_remote_lookup_is_cached(self):
        with patch.object(rag_client, "fetch_qa_item", return_value={"category": "c"}) as fetch:
            assert grounding._resolve_kb_item("b", {}) == {"category": "c"}
            assert grounding._resolve_kb_item("b", {}) == {"category": "c"}
        assert fetch.call_count == 1

    def test_missing_remote_item_is_cached_as_none(self):
        with patch.object(rag_client, "fetch_qa_item", return_value=None) as fetch:
            assert grounding._resolve_kb_item("c", {}) is None
            assert grounding._resolve_kb_item("c", {}) is None
        assert fetch.call_count == 1

    def test_empty_id_is_not_looked_up(self):
        with patch.object(rag_client, "fetch_qa_item") as fetch:
            assert grounding._resolve_kb_item("", {}) is None
        fetch.assert_not_called()

    def test_load_qa_items_reads_local_file_only(self, tmp_path):
        qa = tmp_path / "output" / "qa_final.json"
        qa.parent.mkdir(parents=True)
        qa.write_text('{"qa_database": [{"stable_id": "s", "category": "c"}]}', encoding="utf-8")
        with patch.object(grounding, "PROJECT_ROOT", tmp_path), patch.object(grounding, "_kb_cache", None):
            assert grounding._load_qa_items() == [{"stable_id": "s", "category": "c"}]

    def test_load_qa_items_empty_without_local_file(self, tmp_path):
        with patch.object(grounding, "PROJECT_ROOT", tmp_path), patch.object(grounding, "_kb_cache", None):
            assert grounding._load_qa_items() == []

    def test_load_qa_items_tolerates_corrupt_file(self, tmp_path):
        qa = tmp_path / "output" / "qa_final.json"
        qa.parent.mkdir(parents=True)
        qa.write_text("{nope", encoding="utf-8")
        with patch.object(grounding, "PROJECT_ROOT", tmp_path), patch.object(grounding, "_kb_cache", None):
            assert grounding._load_qa_items() == []

    def test_gate_skips_with_warning_when_no_kb_and_rag_unusable(self, capsys, tmp_path):
        thresholds = tmp_path / "t.json"
        thresholds.write_text('{"meeting_prep_grounding": {"citation_id_resolution": 0.9}}', encoding="utf-8")
        with patch.object(grounding, "_threshold_path", thresholds), \
                patch.object(grounding, "_load_qa_items", return_value=[]), \
                patch.object(rag_client, "preflight", return_value=(False, "rag-api rejected credentials (HTTP 403)")), \
                patch.object(grounding, "executor") as executor:
            grounding._run_threshold_gate()
        executor.assert_not_called()
        assert "::warning::" in capsys.readouterr().out
