"""
Unit tests for evals/eval_crawled_not_indexed.py evaluator functions.

Tests only the pure evaluator functions (no network calls).
The executor function itself is tested via integration test (skipped by default).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Import the module under test ───────────────────────────────────────────────

# Patch lmnr.evaluate to a no-op so importing the module does not trigger a run
with patch.dict("sys.modules", {"lmnr": MagicMock()}):
    import importlib
    import evals.eval_crawled_not_indexed as mod
    importlib.reload(mod)


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_output(
    severity: str = "critical",
    worsening: list[dict] | None = None,
    improving: list[dict] | None = None,
    markdown: str = "",
) -> dict:
    """Build a minimal API response dict."""
    return {
        "insight": {
            "overall_severity": severity,
            "worsening_paths": worsening or [],
            "improving_paths": improving or [],
            "stable_paths": [],
            "summary_text": "",
        },
        "markdown": markdown,
    }


# ── severity_accuracy ─────────────────────────────────────────────────────────


class TestSeverityAccuracy:
    def test_exact_match_critical(self):
        output = _make_output(severity="critical")
        target = {"expected_severity": "critical"}
        assert mod.severity_accuracy(output, target) == 1.0

    def test_exact_match_warning(self):
        output = _make_output(severity="warning")
        target = {"expected_severity": "warning"}
        assert mod.severity_accuracy(output, target) == 1.0

    def test_exact_match_stable(self):
        output = _make_output(severity="stable")
        target = {"expected_severity": "stable"}
        assert mod.severity_accuracy(output, target) == 1.0

    def test_exact_match_improving(self):
        output = _make_output(severity="improving")
        target = {"expected_severity": "improving"}
        assert mod.severity_accuracy(output, target) == 1.0

    def test_mismatch_returns_zero(self):
        output = _make_output(severity="warning")
        target = {"expected_severity": "critical"}
        assert mod.severity_accuracy(output, target) == 0.0

    def test_missing_insight_key(self):
        """Gracefully handle malformed output."""
        output = {}
        target = {"expected_severity": "stable"}
        assert mod.severity_accuracy(output, target) == 0.0

    def test_empty_actual_severity(self):
        output = _make_output(severity="")
        target = {"expected_severity": "critical"}
        assert mod.severity_accuracy(output, target) == 0.0


# ── worsening_path_recall ─────────────────────────────────────────────────────


class TestWorseningPathRecall:
    def test_all_found(self):
        output = _make_output(
            worsening=[{"segment": "/article/"}, {"segment": "/salon/"}]
        )
        target = {"expected_worsening_paths": ["/article/", "/salon/"]}
        assert mod.worsening_path_recall(output, target) == 1.0

    def test_partial_found(self):
        output = _make_output(
            worsening=[{"segment": "/article/"}]
        )
        target = {"expected_worsening_paths": ["/article/", "/salon/"]}
        assert mod.worsening_path_recall(output, target) == pytest.approx(0.5)

    def test_none_found(self):
        output = _make_output(worsening=[])
        target = {"expected_worsening_paths": ["/article/"]}
        assert mod.worsening_path_recall(output, target) == 0.0

    def test_no_expected_worsening_returns_one(self):
        """No expected worsening paths → recall is 1 (no requirement to satisfy)."""
        output = _make_output(worsening=[])
        target = {"expected_worsening_paths": []}
        assert mod.worsening_path_recall(output, target) == 1.0

    def test_missing_target_key_defaults_to_one(self):
        output = _make_output(worsening=[])
        target = {}
        assert mod.worsening_path_recall(output, target) == 1.0

    def test_extra_actual_paths_do_not_reduce_score(self):
        """Extra detected paths that are not in expected should not penalise recall."""
        output = _make_output(
            worsening=[
                {"segment": "/article/"},
                {"segment": "/salon/"},
                {"segment": "/unexpected/"},
            ]
        )
        target = {"expected_worsening_paths": ["/article/", "/salon/"]}
        assert mod.worsening_path_recall(output, target) == 1.0

    def test_missing_insight_key(self):
        output = {}
        target = {"expected_worsening_paths": ["/article/"]}
        assert mod.worsening_path_recall(output, target) == 0.0


# ── improving_path_recall ─────────────────────────────────────────────────────


class TestImprovingPathRecall:
    def test_all_found(self):
        output = _make_output(
            improving=[{"segment": "/en/"}, {"segment": "/tag/"}]
        )
        target = {"expected_improving_paths": ["/en/", "/tag/"]}
        assert mod.improving_path_recall(output, target) == 1.0

    def test_partial_found(self):
        output = _make_output(improving=[{"segment": "/en/"}])
        target = {"expected_improving_paths": ["/en/", "/tag/"]}
        assert mod.improving_path_recall(output, target) == pytest.approx(0.5)

    def test_none_found(self):
        output = _make_output(improving=[])
        target = {"expected_improving_paths": ["/en/"]}
        assert mod.improving_path_recall(output, target) == 0.0

    def test_no_expected_improving_returns_one(self):
        output = _make_output(improving=[])
        target = {"expected_improving_paths": []}
        assert mod.improving_path_recall(output, target) == 1.0

    def test_missing_target_key_defaults_to_one(self):
        output = _make_output(improving=[])
        target = {}
        assert mod.improving_path_recall(output, target) == 1.0

    def test_missing_insight_key(self):
        output = {}
        target = {"expected_improving_paths": ["/en/"]}
        assert mod.improving_path_recall(output, target) == 0.0


# ── path_coverage ─────────────────────────────────────────────────────────────


class TestPathCoverage:
    def test_all_paths_in_markdown(self):
        markdown = "## Analysis\n/article/ 有問題\n/tag/ 需關注\n/user/ 穩定"
        output = _make_output(
            markdown=markdown,
            worsening=[{"segment": "/article/"}],
        )
        target = {
            "expected_worsening_paths": ["/article/"],
            "expected_improving_paths": [],
            "input_tsv": "全網域\t5%\t0\t100\t50\t\t100\n/article/\t30%\t0\t200\t10\t\t200\n/tag/\t-5%\t0\t50\t3\t\t50\n/user/\t1%\t0\t10\t1\t\t10\n總合\t15%\t0\t260\t14\t\t",
        }
        score = mod.path_coverage(output, target)
        assert score == pytest.approx(1.0)

    def test_partial_paths_in_markdown(self):
        markdown = "## Analysis\n/article/ 有問題"
        output = _make_output(markdown=markdown)
        target = {
            "expected_worsening_paths": ["/article/"],
            "expected_improving_paths": [],
            "input_tsv": "全網域\t5%\t0\t100\t50\t\t100\n/article/\t30%\t0\t200\t10\t\t200\n/tag/\t-5%\t0\t50\t3\t\t50\n總合\t15%\t0\t250\t13\t\t",
        }
        score = mod.path_coverage(output, target)
        # Only /article/ mentioned out of /article/, /tag/
        assert 0.0 < score < 1.0

    def test_empty_markdown_returns_zero(self):
        output = _make_output(markdown="")
        target = {
            "expected_worsening_paths": [],
            "expected_improving_paths": [],
            "input_tsv": "/article/\t30%\t0\t200\t10\t\t200\n/tag/\t-5%\t0\t50\t3\t\t50\n總合\t15%\t0\t250\t13\t\t",
        }
        score = mod.path_coverage(output, target)
        assert score == 0.0

    def test_no_paths_in_tsv_returns_one(self):
        """When TSV has no parseable path rows, coverage is 1 (nothing to miss)."""
        output = _make_output(markdown="some content")
        target = {
            "expected_worsening_paths": [],
            "expected_improving_paths": [],
            "input_tsv": "總合\t0%\t0\t100\t50\t\t",
        }
        score = mod.path_coverage(output, target)
        assert score == 1.0


# ── overall ───────────────────────────────────────────────────────────────────


class TestOverall:
    def test_perfect_score(self):
        output = _make_output(
            severity="critical",
            worsening=[{"segment": "/article/"}, {"segment": "/salon/"}],
            improving=[{"segment": "/en/"}],
            markdown="/article/ 惡化\n/salon/ 惡化\n/en/ 改善\n/tag/ 穩定",
        )
        target = {
            "expected_severity": "critical",
            "expected_worsening_paths": ["/article/", "/salon/"],
            "expected_improving_paths": ["/en/"],
            "input_tsv": (
                "全網域\t10%\t0\t900000\t350000\t\t820000\n"
                "/article/\t55%\t0\t374000\t12000\t\t100000\n"
                "/salon/\t134%\t0\t94000\t11000\t\t95000\n"
                "/en/\t-32%\t0\t22000\t950\t\t950\n"
                "/tag/\t3%\t0\t34000\t10000\t\t27000\n"
                "總合\t62%\t-1\t442000\t42000\t\t"
            ),
        }
        score = mod.overall(output, target)
        # All sub-metrics should be 1.0 → overall near 1.0
        assert score == pytest.approx(1.0, abs=0.01)

    def test_zero_score_on_all_wrong(self):
        output = _make_output(
            severity="stable",
            worsening=[],
            improving=[],
            markdown="",
        )
        target = {
            "expected_severity": "critical",
            "expected_worsening_paths": ["/article/"],
            "expected_improving_paths": ["/en/"],
            "input_tsv": (
                "/article/\t55%\t0\t374000\t12000\t\t100000\n"
                "/en/\t-32%\t0\t22000\t950\t\t950\n"
                "總合\t62%\t-1\t442000\t42000\t\t"
            ),
        }
        score = mod.overall(output, target)
        # severity wrong (0), recalls both 0, coverage 0 → overall = 0
        assert score == pytest.approx(0.0, abs=0.05)

    def test_returns_value_between_zero_and_one(self):
        output = _make_output(
            severity="warning",
            worsening=[{"segment": "/article/"}],
            improving=[],
            markdown="/article/ 上升",
        )
        target = {
            "expected_severity": "critical",
            "expected_worsening_paths": ["/article/", "/salon/"],
            "expected_improving_paths": [],
            "input_tsv": (
                "/article/\t55%\t0\t374000\t12000\t\t100000\n"
                "/salon/\t134%\t0\t94000\t11000\t\t95000\n"
                "總合\t62%\t-1\t442000\t42000\t\t"
            ),
        }
        score = mod.overall(output, target)
        assert 0.0 <= score <= 1.0


# ── Dataset structure ─────────────────────────────────────────────────────────


class TestDatasetStructure:
    def test_golden_dataset_loads(self):
        assert len(mod._dataset) > 0

    def test_dataset_items_have_required_keys(self):
        for item in mod._dataset:
            assert "data" in item
            assert "target" in item
            assert "raw_tsv" in item["data"]
            assert "expected_severity" in item["target"]
            assert "expected_worsening_paths" in item["target"]
            assert "expected_improving_paths" in item["target"]

    def test_dataset_raw_tsv_non_empty(self):
        for item in mod._dataset:
            assert len(item["data"]["raw_tsv"].strip()) > 0

    def test_dataset_severity_valid_values(self):
        valid = {"critical", "warning", "stable", "improving"}
        for item in mod._dataset:
            assert item["target"]["expected_severity"] in valid


# ── extract_path_segments helper ─────────────────────────────────────────────


class TestExtractPathSegments:
    def test_extracts_slash_paths(self):
        tsv = (
            "全網域\t5%\t0\t100\t50\t\t100\n"
            "/article/\t30%\t0\t200\t10\t\t200\n"
            "/tag/\t-5%\t0\t50\t3\t\t50\n"
            "總合\t15%\t0\t250\t13\t\t"
        )
        segments = mod._extract_path_segments(tsv)
        assert "/article/" in segments
        assert "/tag/" in segments
        # 全網域 and 總合 are not slash-prefixed path rows
        assert "全網域" not in segments
        assert "總合" not in segments

    def test_empty_tsv_returns_empty_list(self):
        assert mod._extract_path_segments("") == []

    def test_only_summary_rows_returns_empty(self):
        tsv = "總合\t15%\t0\t250\t13\t\t\n總合/全網域\t44%\t0\t43%\t10%\t\t"
        assert mod._extract_path_segments(tsv) == []
