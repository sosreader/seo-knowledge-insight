"""Unit tests for evals/eval_meeting_prep_novelty.py helper functions."""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

# Import helpers directly — avoid module-level side effects (argparse, Laminar)
import importlib
import sys

# Patch lmnr before importing the module
sys.modules["lmnr"] = type(sys)("lmnr")
sys.modules["lmnr"].evaluate = lambda **kwargs: None  # type: ignore[attr-defined]

_MOD_PATH = Path(__file__).resolve().parent.parent / "evals" / "eval_meeting_prep_novelty.py"


def _load_module():
    """Load the novelty eval module, bypassing argparse and Laminar."""
    spec = importlib.util.spec_from_file_location("novelty", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Patch argparse to avoid CLI side-effects
    with patch("argparse.ArgumentParser.parse_known_args", return_value=(type("A", (), {"report": None, "limit": 0})(), [])):
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()


# ── find_prior_report ────────────────────────────────────────────────────────

class TestFindPriorReport:
    def test_finds_most_recent_prior(self, tmp_path: Path) -> None:
        (tmp_path / "meeting_prep_20260220_aaaaaaaa.md").write_text("old")
        (tmp_path / "meeting_prep_20260227_bbbbbbbb.md").write_text("mid")
        target = tmp_path / "meeting_prep_20260306_cccccccc.md"
        target.write_text("new")

        result = _mod.find_prior_report(target)
        assert result is not None
        assert "20260227" in result.name

    def test_returns_none_for_first_report(self, tmp_path: Path) -> None:
        target = tmp_path / "meeting_prep_20260220_aaaaaaaa.md"
        target.write_text("first")

        result = _mod.find_prior_report(target)
        assert result is None

    def test_ignores_non_matching_filenames(self, tmp_path: Path) -> None:
        (tmp_path / "meeting_prep_20260220_v33.md").write_text("bad suffix")
        target = tmp_path / "meeting_prep_20260306_cccccccc.md"
        target.write_text("new")

        # Mock PROJECT_ROOT so fallback to output/ doesn't find real files
        with patch.object(_mod, "PROJECT_ROOT", tmp_path):
            result = _mod.find_prior_report(target)
        assert result is None


# ── s2_novelty ───────────────────────────────────────────────────────────────

class TestS2Novelty:
    def test_all_new_urls(self) -> None:
        output = {
            "no_prior": False,
            "curr_s2_tags": {"NEW": 0, "ONGOING": 0, "CF": 0, "RESOLVED": 0, "CARRY": 0},
            "curr_s2_urls": ["https://a.com/1", "https://a.com/2"],
            "prev_s2_urls": ["https://b.com/1", "https://b.com/2"],
        }
        score = _mod.s2_novelty(output, {})
        assert score == 1.0

    def test_all_same_urls(self) -> None:
        output = {
            "no_prior": False,
            "curr_s2_tags": {"NEW": 0, "ONGOING": 0, "CF": 0, "RESOLVED": 0, "CARRY": 0},
            "curr_s2_urls": ["https://a.com/1"],
            "prev_s2_urls": ["https://a.com/1"],
        }
        score = _mod.s2_novelty(output, {})
        assert score == 0.0

    def test_partial_overlap(self) -> None:
        output = {
            "no_prior": False,
            "curr_s2_tags": {"NEW": 0, "ONGOING": 0, "CF": 0, "RESOLVED": 0, "CARRY": 0},
            "curr_s2_urls": ["https://a.com/1", "https://a.com/new"],
            "prev_s2_urls": ["https://a.com/1", "https://a.com/old"],
        }
        score = _mod.s2_novelty(output, {})
        # Jaccard: intersection=1, union=3, distance=1-1/3=0.667
        assert 0.6 < score < 0.7

    def test_sitrep_tags_preferred(self) -> None:
        output = {
            "no_prior": False,
            "curr_s2_tags": {"NEW": 3, "ONGOING": 1, "CF": 0, "RESOLVED": 1, "CARRY": 0},
            "curr_s2_urls": [],
            "prev_s2_urls": [],
        }
        score = _mod.s2_novelty(output, {})
        assert score == 3 / 5  # 3 NEW out of 5 total

    def test_no_prior_returns_one(self) -> None:
        output = {"no_prior": True}
        assert _mod.s2_novelty(output, {}) == 1.0


# ── s4_novelty ───────────────────────────────────────────────────────────────

class TestS4Novelty:
    def test_topic_extraction(self) -> None:
        text = textwrap.dedent("""\
            | 主題 | KB | 顧問 | 指標 | 業界 | 判斷 |
            |------|-----|------|------|------|------|
            | **[NEW]** Discover 演算法 | ... | ... | ... | ... | 一致 |
            | **[CF]** AI 流量趨勢 | ... | ... | ... | ... | 一致 |
        """)
        topics = _mod._extract_s4_topics(text)
        assert len(topics) == 2
        assert "Discover 演算法" in topics
        assert "AI 流量趨勢" in topics

    def test_all_different_topics(self) -> None:
        output = {
            "no_prior": False,
            "curr_s4_topics": ["TopicA", "TopicB"],
            "prev_s4_topics": ["TopicC", "TopicD"],
        }
        assert _mod.s4_novelty(output, {}) == 1.0

    def test_all_same_topics(self) -> None:
        output = {
            "no_prior": False,
            "curr_s4_topics": ["TopicA"],
            "prev_s4_topics": ["TopicA"],
        }
        assert _mod.s4_novelty(output, {}) == 0.0


# ── score_drift_novelty ──────────────────────────────────────────────────────

class TestScoreDrift:
    def test_identical_scores_zero(self) -> None:
        meta = {
            "scores": {
                "eeat": {"experience": 3, "expertise": 3, "authoritativeness": 2, "trustworthiness": 3},
                "maturity": {"strategy": "L2", "process": "L2", "keywords": "L3", "metrics": "L2"},
            }
        }
        output = {"no_prior": False, "curr_meta": meta, "prev_meta": meta}
        assert _mod.score_drift_novelty(output, {}) == 0.0

    def test_some_change_positive(self) -> None:
        curr = {
            "scores": {
                "eeat": {"experience": 3, "expertise": 3, "authoritativeness": 3, "trustworthiness": 3},
                "maturity": {"strategy": "L2", "process": "L3", "keywords": "L3", "metrics": "L2"},
            }
        }
        prev = {
            "scores": {
                "eeat": {"experience": 3, "expertise": 3, "authoritativeness": 2, "trustworthiness": 3},
                "maturity": {"strategy": "L2", "process": "L2", "keywords": "L3", "metrics": "L2"},
            }
        }
        output = {"no_prior": False, "curr_meta": curr, "prev_meta": prev}
        # delta: auth 1 + process 1 = 2, normalised = 2/4 = 0.5
        assert _mod.score_drift_novelty(output, {}) == 0.5


# ── s7_citation_novelty ──────────────────────────────────────────────────────

class TestS7CitationNovelty:
    def test_all_new_citations(self) -> None:
        output = {
            "no_prior": False,
            "curr_s7_ids": ["id1", "id2", "id3"],
            "prev_s7_ids": ["id4", "id5"],
        }
        assert _mod.s7_citation_novelty(output, {}) == 1.0

    def test_all_repeated_citations(self) -> None:
        output = {
            "no_prior": False,
            "curr_s7_ids": ["id1", "id2"],
            "prev_s7_ids": ["id1", "id2", "id3"],
        }
        assert _mod.s7_citation_novelty(output, {}) == 0.0


# ── toggle_structure ─────────────────────────────────────────────────────────

class TestToggleStructure:
    def test_no_toggles_zero(self) -> None:
        output = {"no_prior": False, "curr_toggles": 0}
        assert _mod.toggle_structure(output, {}) == 0.0

    def test_three_toggles_perfect(self) -> None:
        output = {"no_prior": False, "curr_toggles": 3}
        assert _mod.toggle_structure(output, {}) == 1.0

    def test_first_report_no_toggle_needed(self) -> None:
        output = {"no_prior": True, "curr_toggles": 0}
        assert _mod.toggle_structure(output, {}) == 1.0


# ── Jaccard helper ───────────────────────────────────────────────────────────

class TestJaccard:
    def test_empty_sets(self) -> None:
        assert _mod._jaccard_distance(set(), set()) == 1.0

    def test_identical_sets(self) -> None:
        assert _mod._jaccard_distance({"a", "b"}, {"a", "b"}) == 0.0

    def test_disjoint_sets(self) -> None:
        assert _mod._jaccard_distance({"a"}, {"b"}) == 1.0
