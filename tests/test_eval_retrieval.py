"""Unit tests for evals/eval_retrieval.py loading and filtering behavior."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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


class TestLoadQaItems:
    def test_loads_local_file_when_model_filter_not_requested(self, tmp_path):
        qa_path = tmp_path / "output" / "qa_final.json"
        qa_path.parent.mkdir(parents=True)
        qa_path.write_text(json.dumps({"qa_database": [{"question": "Q1"}]}), encoding="utf-8")

        with patch.object(mod, "PROJECT_ROOT", tmp_path), patch.object(mod, "_filter_model", None):
            items = mod._load_qa_items()

        assert len(items) == 1
        assert items[0]["question"] == "Q1"

    def test_returns_empty_when_local_file_missing(self, tmp_path):
        with patch.object(mod, "PROJECT_ROOT", tmp_path):
            assert mod._load_qa_items() == []

    def test_returns_empty_when_local_file_is_corrupt(self, tmp_path):
        qa_path = tmp_path / "output" / "qa_final.json"
        qa_path.parent.mkdir(parents=True)
        qa_path.write_text("{not json", encoding="utf-8")
        with patch.object(mod, "PROJECT_ROOT", tmp_path):
            assert mod._load_qa_items() == []

    def test_no_supabase_fallback_when_local_lacks_model(self, tmp_path):
        qa_path = tmp_path / "output" / "qa_final.json"
        qa_path.parent.mkdir(parents=True)
        qa_path.write_text(json.dumps({"qa_database": [{"question": "Q1"}]}), encoding="utf-8")

        with patch.object(mod, "PROJECT_ROOT", tmp_path), patch.object(mod, "_filter_model", "claude-code"):
            assert mod._load_qa_items() == []


class TestSearchViaApi:
    def test_uses_rag_client_without_mode(self):
        with patch.object(mod.rag_client, "search_results", return_value=[{"id": "a"}]) as search, \
                patch.object(mod, "_filter_model", None):
            assert mod._search_via_api("q") == [{"id": "a"}]
        assert search.call_args.args == ("q",)
        assert search.call_args.kwargs["top_k"] == 5
        assert search.call_args.kwargs["extra"] is None

    def test_passes_extraction_model_filter(self):
        with patch.object(mod.rag_client, "search_results", return_value=[{"id": "a"}]) as search, \
                patch.object(mod, "_filter_model", "claude-code"):
            mod._search_via_api("q", top_k=3)
        assert search.call_args.kwargs["extra"] == {"extraction_model": "claude-code"}
        assert search.call_args.kwargs["top_k"] == 3

    def test_empty_results_become_none_for_naive_fallback(self):
        with patch.object(mod.rag_client, "search_results", return_value=[]):
            assert mod._search_via_api("q") is None


class TestExecutor:
    def test_prefers_api_results(self):
        with patch.object(mod, "_search_via_api", return_value=[{"id": "a"}] * 7), \
                patch.object(mod, "_filter_model", None):
            out = mod.retrieval_executor({"query": "q"})
        assert out["source"] == "api"
        assert len(out["results"]) == 5

    def test_falls_back_to_naive_search(self):
        items = [{"question": "discover traffic", "answer": "", "keywords": []}]
        with patch.object(mod, "_search_via_api", return_value=None), \
                patch.object(mod, "_load_qa_items", return_value=items), \
                patch.object(mod, "_filter_model", None):
            out = mod.retrieval_executor({"query": "discover"})
        assert out["source"] == "naive"
        assert out["results"] == items


class TestThresholdSelection:
    def test_keyword_thresholds_when_llm_disabled(self):
        with patch.object(mod.rag_client, "llm_available", return_value=False):
            assert mod._threshold_section() == "retrieval_keyword"

    def test_hybrid_thresholds_when_llm_available(self):
        with patch.object(mod.rag_client, "llm_available", return_value=True):
            assert mod._threshold_section() == "retrieval"

    def test_keyword_section_exists_in_repo_thresholds(self):
        thresholds = json.loads((PROJECT_ROOT / "eval" / "eval_thresholds.json").read_text(encoding="utf-8"))
        assert set(thresholds["retrieval_keyword"]) == set(thresholds["retrieval"])


class TestTargetAvailability:
    def test_local_file_means_usable_without_network(self, tmp_path):
        (tmp_path / "output").mkdir()
        (tmp_path / "output" / "qa_final.json").write_text("{}", encoding="utf-8")
        with patch.object(mod, "PROJECT_ROOT", tmp_path), \
                patch.object(mod.rag_client, "preflight") as preflight:
            assert mod._target_unavailable_reason() is None
        preflight.assert_not_called()

    def test_reports_preflight_failure_reason(self, tmp_path):
        with patch.object(mod, "PROJECT_ROOT", tmp_path), \
                patch.object(mod.rag_client, "preflight", return_value=(False, "rag-api rejected credentials (HTTP 403)")):
            assert "403" in mod._target_unavailable_reason()

    def test_none_when_preflight_ok(self, tmp_path):
        with patch.object(mod, "PROJECT_ROOT", tmp_path), \
                patch.object(mod.rag_client, "preflight", return_value=(True, "ok")):
            assert mod._target_unavailable_reason() is None

    def test_run_eval_skips_with_warning_annotation(self, capsys):
        with patch.object(mod, "_target_unavailable_reason", return_value="rag-api unreachable (X)"), \
                patch.object(mod, "_run_threshold_gate") as gate, \
                patch.object(mod, "evaluate") as evaluate:
            mod.run_eval()
        gate.assert_not_called()
        evaluate.assert_not_called()
        assert "::warning::" in capsys.readouterr().out


class TestThresholdGate:
    _DATASET = [{
        "data": {"query": "q"},
        "target": {"expected_categories": ["A"], "expected_keywords": []},
    }]
    _HIT = {"results": [{"category": "A"}], "query": "q", "source": "api"}
    _MISS = {"results": [{"category": "B"}], "query": "q", "source": "api"}

    def _write(self, tmp_path, section, thresholds):
        path = tmp_path / "t.json"
        path.write_text(json.dumps({section: thresholds}), encoding="utf-8")
        return path

    def test_keyword_section_pass_populates_cache(self, tmp_path, capsys):
        path = self._write(tmp_path, "retrieval_keyword", {"hit_rate": 0.9})
        with patch.object(mod, "_threshold_path", path), patch.object(mod, "_dataset", self._DATASET), \
                patch.object(mod.rag_client, "llm_available", return_value=False), \
                patch.object(mod, "retrieval_executor", return_value=self._HIT):
            mod._run_threshold_gate()
        out = capsys.readouterr().out
        assert "retrieval_keyword thresholds" in out
        assert "PASS: hit_rate" in out
        assert mod._exec_cache["q"] == self._HIT

    def test_hybrid_section_used_when_llm_available(self, tmp_path, capsys):
        path = self._write(tmp_path, "retrieval", {"hit_rate": 0.9})
        with patch.object(mod, "_threshold_path", path), patch.object(mod, "_dataset", self._DATASET), \
                patch.object(mod.rag_client, "llm_available", return_value=True), \
                patch.object(mod, "retrieval_executor", return_value=self._HIT):
            mod._run_threshold_gate()
        assert "CI Eval Gate: retrieval thresholds" in capsys.readouterr().out

    def test_below_threshold_exits_nonzero(self, tmp_path):
        path = self._write(tmp_path, "retrieval_keyword", {"hit_rate": 0.9})
        with patch.object(mod, "_threshold_path", path), patch.object(mod, "_dataset", self._DATASET), \
                patch.object(mod.rag_client, "llm_available", return_value=False), \
                patch.object(mod, "retrieval_executor", return_value=self._MISS):
            with pytest.raises(SystemExit) as exc:
                mod._run_threshold_gate()
        assert exc.value.code == 1

    def test_missing_threshold_file_is_noop(self, tmp_path):
        with patch.object(mod, "_threshold_path", tmp_path / "absent.json"):
            mod._run_threshold_gate()
        assert mod._exec_cache == {}

    def test_run_eval_runs_gate_then_evaluate_when_target_usable(self):
        with patch.object(mod, "_target_unavailable_reason", return_value=None), \
                patch.object(mod, "_run_threshold_gate") as gate, \
                patch.object(mod, "evaluate") as evaluate:
            mod.run_eval()
        gate.assert_called_once()
        evaluate.assert_called_once()
