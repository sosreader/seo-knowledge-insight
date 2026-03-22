#!/usr/bin/env python3
"""
Meeting-Prep autoresearch eval — rule-based composite score.

Runs L1 structure + L2 grounding + L2.5 coherence + L4 web layers,
computes a single composite number for keep/discard decisions.

No LLM calls. Deterministic. ~2s per report.

Usage:
    python autoresearch/meeting-prep/eval_local.py \
        --report output/meeting_prep_20260322_558a5833.md \
        --alert-names "Discover,外部連結,週平均回應時間"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import evaluators from existing eval scripts
from evals.eval_meeting_prep_structure import executor as structure_executor, _EVALUATOR_MAP as STRUCTURE_MAP
from evals.eval_meeting_prep_grounding import executor as grounding_executor, _EVALUATOR_MAP as GROUNDING_MAP
from evals.eval_meeting_prep_coherence import executor as coherence_executor, _EVALUATOR_MAP as COHERENCE_MAP
from evals.eval_meeting_prep_web import executor as web_executor, _EVALUATOR_MAP as WEB_MAP


def _avg(scores: dict[str, float | None]) -> float:
    vals = [v for v in scores.values() if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def compute_rule_based_composite(
    l1: dict[str, float],
    l2_grounding: dict[str, float],
    l2_coherence: dict[str, float],
    l4: dict[str, float],
) -> float:
    """Weighted composite for autoresearch (no L3 LLM judge).

    Weights tuned for autoresearch discrimination:
    - L1 structure (0.10) — mostly saturated, low weight
    - L2 grounding (0.20) — citation quality
    - L2.5 coherence (0.45) — highest discrimination, highest weight
    - L4 web (0.25) — freshness + density
    """
    return (
        _avg(l1) * 0.10
        + _avg(l2_grounding) * 0.20
        + _avg(l2_coherence) * 0.45
        + _avg(l4) * 0.25
    )


def evaluate_meeting_prep(report_path: str) -> dict[str, float]:
    """Run all 4 rule-based layers and return individual + composite scores."""
    data = {"report_path": report_path}

    # Borrow expected values from golden dataset
    golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    # Use first non-calibration case for target values
    target_case = next(c for c in golden if not c.get("calibration_only", False))
    target = {
        **target_case.get("expected_structure", {}),
        **target_case.get("expected_grounding", {}),
        **target_case.get("expected_web", {}),
        **target_case.get("expected_coherence", {}),
    }

    # L1: Structure
    l1_out = structure_executor(data)
    l1_scores = {}
    for name, fn in STRUCTURE_MAP.items():
        try:
            l1_scores[name] = fn(l1_out, target)
        except Exception:
            l1_scores[name] = 0.0

    # L2: Grounding
    l2g_out = grounding_executor(data)
    l2g_scores = {}
    for name, fn in GROUNDING_MAP.items():
        try:
            l2g_scores[name] = fn(l2g_out, target)
        except Exception:
            l2g_scores[name] = 0.0

    # L2.5: Coherence
    l2c_out = coherence_executor(data)
    l2c_scores = {}
    for name, fn in COHERENCE_MAP.items():
        try:
            l2c_scores[name] = fn(l2c_out, target)
        except Exception:
            l2c_scores[name] = 0.0

    # L4: Web
    l4_out = web_executor(data)
    l4_scores = {}
    for name, fn in WEB_MAP.items():
        try:
            score = fn(l4_out, target)
            if score is not None:
                l4_scores[name] = score
        except Exception:
            l4_scores[name] = 0.0

    composite = compute_rule_based_composite(l1_scores, l2g_scores, l2c_scores, l4_scores)

    all_scores = {
        **{f"l1_{k}": v for k, v in l1_scores.items()},
        **{f"l2g_{k}": v for k, v in l2g_scores.items()},
        **{f"l2c_{k}": v for k, v in l2c_scores.items()},
        **{f"l4_{k}": v for k, v in l4_scores.items()},
    }
    all_scores["composite"] = composite

    return all_scores


def main():
    parser = argparse.ArgumentParser(description="Meeting-prep rule-based composite eval")
    parser.add_argument("--report", required=True, help="Path to meeting prep .md file")
    parser.add_argument("--alert-names", default="", help="Comma-separated ALERT_DOWN names (unused, kept for API compat)")
    args = parser.parse_args()

    scores = evaluate_meeting_prep(args.report)

    # Print all scores
    for k, v in sorted(scores.items()):
        if k != "composite":
            print(f"  {k}: {v:.4f}")

    print(f"\nMEETING_PREP_COMPOSITE={scores['composite']:.6f}")


if __name__ == "__main__":
    main()
