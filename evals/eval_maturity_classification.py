"""
Laminar offline evaluation: Maturity classification accuracy.

Tests whether the rule-based maturity classifier (utils/maturity_classifier.py)
correctly classifies QA items into L1-L4 levels.

Dataset:  eval/golden_maturity_classification.json (30 scenarios)
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_maturity_classification.py
    python evals/eval_maturity_classification.py --limit 5
    lmnr eval evals/eval_maturity_classification.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

from utils.maturity_classifier import classify_maturity_level  # noqa: E402

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Maturity classification eval")
_parser.add_argument("--limit", type=int, default=0, help="Limit golden cases (0=all)")
_args, _unknown = _parser.parse_known_args()

# ── Golden dataset ────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_maturity_classification.json"
if not _golden_path.exists():
    print(
        f"[eval_maturity] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]

_dataset = [
    {
        "data": {
            "question": item["question"],
            "answer": item["answer"],
            "keywords": item["keywords"],
        },
        "target": {
            "expected_maturity": item["expected_maturity"],
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────


def classify_executor(data: dict) -> dict:
    """Run rule-based classifier on the QA item."""
    result = classify_maturity_level(
        keywords=data["keywords"],
        question=data["question"],
        answer=data["answer"],
    )
    return {"predicted_maturity": result or "NONE"}


# ── Evaluators ────────────────────────────────────────────────────────────────


def accuracy(output: dict, target: dict) -> float:
    """Exact match: predicted == expected."""
    return 1.0 if output["predicted_maturity"] == target["expected_maturity"] else 0.0


def adjacent_accuracy(output: dict, target: dict) -> float:
    """Within-one-level tolerance (L1 vs L2 = 1.0, L1 vs L3 = 0.0)."""
    level_order = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "NONE": 0}
    predicted = level_order.get(output["predicted_maturity"], -1)
    expected = level_order.get(target["expected_maturity"], -1)
    if predicted < 0 or expected < 0:
        return 0.0
    return 1.0 if abs(predicted - expected) <= 1 else 0.0


def not_none(output: dict, target: dict) -> float:
    """Classifier returned a result (not NONE)."""
    return 0.0 if output["predicted_maturity"] == "NONE" else 1.0


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=classify_executor,
    evaluators={
        "accuracy": accuracy,
        "adjacent_accuracy": adjacent_accuracy,
        "classification_rate": not_none,
    },
    group_id="maturity_classification",
)
