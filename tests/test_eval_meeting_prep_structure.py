"""Unit tests for evals/eval_meeting_prep_structure.py.

Guards against eval drift: the structure eval must PASS on the accepted
current-format meeting-prep reports and FAIL on deliberately broken samples
(Goodhart guard — a rubber-stamp eval that passes everything measures nothing).
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Patch lmnr before importing the module (avoid Laminar network side-effects).
sys.modules["lmnr"] = type(sys)("lmnr")
sys.modules["lmnr"].evaluate = lambda **kwargs: None  # type: ignore[attr-defined]

_ROOT = Path(__file__).resolve().parent.parent
_MOD_PATH = _ROOT / "evals" / "eval_meeting_prep_structure.py"
_FIXTURE_DIR = _ROOT / "eval" / "fixtures" / "meeting_prep"
_THRESHOLDS = json.loads(
    (_ROOT / "eval" / "eval_thresholds.json").read_text(encoding="utf-8")
)["meeting_prep_structure"]

# Accepted current-format reports referenced by golden_meeting_prep_structure.json
_ACCEPTED = [
    "meeting_prep_20260626_f2c16c7b.md",
    "meeting_prep_20260619_a6ee9934.md",
]

# expected_structure shared by the golden entries
_TARGET = {
    "question_by_type": {"A": [3, 5], "B": [4, 6], "C": [2, 3], "D": [2, 3]},
    "s3_anomaly_subsections_min": 3,
    "s5_layer_count": 5,
    "s7_element_count": 7,
    "s10_checklist_min": 5,
}


def _load_module():
    """Load the structure eval module, bypassing argparse and Laminar."""
    spec = importlib.util.spec_from_file_location("mps", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    with patch(
        "argparse.ArgumentParser.parse_known_args",
        return_value=(type("A", (), {"report": None, "limit": 0})(), []),
    ):
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_mod = _load_module()


def _scores_for(content: str) -> dict[str, float]:
    """Run every evaluator against report content (bypassing the file read)."""
    out = {
        "sections": _mod._parse_sections(content),
        "metadata": _mod._parse_meta(content),
        "citations": _mod._parse_citations(content),
        "questions": _mod._parse_questions(content),
        "raw_content": content,
    }
    return {name: fn(out, _TARGET) for name, fn in _mod._EVALUATOR_MAP.items()}


def _read(name: str) -> str:
    return (_FIXTURE_DIR / name).read_text(encoding="utf-8")


# ── Accepted baseline must PASS every threshold ───────────────────────────────

class TestAcceptedBaseline:
    @pytest.mark.parametrize("fixture", _ACCEPTED)
    def test_all_metrics_meet_threshold(self, fixture: str) -> None:
        scores = _scores_for(_read(fixture))
        for metric, min_val in _THRESHOLDS.items():
            assert scores[metric] >= min_val, (
                f"{fixture}: {metric}={scores[metric]:.3f} < {min_val}"
            )

    @pytest.mark.parametrize("fixture", _ACCEPTED)
    def test_question_type_distribution(self, fixture: str) -> None:
        q = _mod._parse_questions(_read(fixture))
        assert len(q["A"]) == 4 and len(q["B"]) == 5
        assert len(q["C"]) == 3 and len(q["D"]) == 2

    def test_meta_parses_nested_json(self) -> None:
        meta = _mod._parse_meta(_read(_ACCEPTED[0]))
        assert meta is not None
        assert 1 <= meta["eeat_avg"] <= 5
        # top-level maturity with half-levels, not nested under scores
        assert "scores" not in meta
        assert re.match(r"^L[1-4](?:\.\d)?$", meta["maturity"]["strategy"])


# ── Deliberately broken samples must FAIL (drift/Goodhart guard) ───────────────

class TestBrokenSamples:
    """Each mutation of an accepted report must drop the relevant metric
    below its threshold."""

    def _base(self) -> str:
        return _read(_ACCEPTED[0])

    def test_missing_section_fails_completeness(self) -> None:
        broken = self._base().replace(
            "## Section 5：五層審計缺口清單", "## (section removed)"
        )
        assert _scores_for(broken)["section_completeness"] < 1.0

    def test_scrambled_meta_fails_metadata(self) -> None:
        broken = re.sub(
            r'"strategy":\s*"L[0-9.]+"', '"strategy": "L9"', self._base()
        )
        assert _scores_for(broken)["metadata_valid"] < 1.0

    def test_missing_eeat_avg_fails_metadata(self) -> None:
        broken = re.sub(r'"eeat_avg":\s*[0-9.]+', '"eeat_avg": "n/a"', self._base())
        assert _scores_for(broken)["metadata_valid"] < 1.0

    def test_emptied_questions_fails_count(self) -> None:
        # Neutralise every bold question header (**A1 [ … → **XX1 [ … ).
        broken = re.sub(r"^\*\*([ABCD])\d", r"**X9", self._base(), flags=re.MULTILINE)
        scores = _scores_for(broken)
        assert scores["question_count_valid"] == 0.0
        assert scores["question_source_annotated"] == 0.0

    def test_s8_meta_mismatch_fails_consistency(self) -> None:
        # Change only the meta maturity so it no longer matches the S8 table.
        broken = re.sub(
            r'("maturity":\s*\{[^}]*?"metrics":\s*")L[0-9.]+', r"\1L1", self._base()
        )
        assert _scores_for(broken)["s8_meta_maturity_consistency"] < 1.0

    def test_stripped_s10_labels_fails_upgrade(self) -> None:
        broken = re.sub(
            r"\[[^\[\]]*L[1-4](?:\.\d)?\s*→\s*L[1-4](?:\.\d)?\]", "[]", self._base()
        )
        assert _scores_for(broken)["s10_maturity_upgrade_labeled"] < 0.8

    def test_broken_report_fails_gate(self) -> None:
        """A report that drops a section + questions must fail the gate as a
        whole (>=1 metric below threshold)."""
        broken = self._base().replace(
            "## Section 9：會議提問清單（核心輸出）", "## (removed)"
        )
        broken = re.sub(r"^\*\*([ABCD])\d", r"**X9", broken, flags=re.MULTILINE)
        scores = _scores_for(broken)
        failed = [m for m, v in scores.items() if v < _THRESHOLDS[m]]
        assert failed, "broken report unexpectedly passed all thresholds"
