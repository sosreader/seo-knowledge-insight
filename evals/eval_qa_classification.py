"""
Laminar offline evaluation: QA classification quality.

Tests whether the QA knowledge base correctly classifies items by category,
difficulty, and evergreen status, using golden_qa.json as ground truth.

Dataset:  eval/golden_qa.json (48 scenarios)
Requires: LMNR_PROJECT_API_KEY, running TS API (cd api && pnpm dev)

Run:
    python evals/eval_qa_classification.py
    lmnr eval evals/eval_qa_classification.py
"""
from __future__ import annotations

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

from evals import rag_client  # noqa: E402

# ── Config ────────────────────────────────────────────────────────────────────

# Target: RAG_API_BASE + CF Access / SEO_API_KEY auth, see evals/rag_client.py

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_qa.json"
if not _golden_path.exists():
    print(f"[eval_qa_class] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_dataset = [
    {
        "data": {"question": item["question"]},
        "target": {
            "expected_category": item["expected_category"],
            "expected_difficulty": item.get("expected_difficulty", ""),
            "expected_evergreen": item.get("expected_evergreen"),
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────

def qa_search_executor(data: dict) -> dict:
    """Search for the question via API and return the best matching QA item."""
    question: str = data["question"]

    results = rag_client.search_results(question, top_k=3, timeout=10)
    if results:
        top = results[0]
        return {
            "category": top.get("category", ""),
            "difficulty": top.get("difficulty", ""),
            "evergreen": top.get("evergreen"),
            "question": top.get("question", ""),
            "result_count": len(results),
        }

    return {"category": "", "difficulty": "", "evergreen": None, "question": "", "result_count": 0}


# ── Evaluators ────────────────────────────────────────────────────────────────

def category_match(output: dict, target: dict) -> float:
    """1 if the top-1 result's category matches expected_category."""
    return 1.0 if output.get("category") == target.get("expected_category") else 0.0


def difficulty_match(output: dict, target: dict) -> float:
    """1 if the top-1 result's difficulty matches expected_difficulty."""
    expected = target.get("expected_difficulty", "")
    if not expected:
        return 1.0  # no expectation
    return 1.0 if output.get("difficulty") == expected else 0.0


def evergreen_match(output: dict, target: dict) -> float:
    """1 if the top-1 result's evergreen matches expected_evergreen."""
    expected = target.get("expected_evergreen")
    if expected is None:
        return 1.0  # no expectation
    return 1.0 if output.get("evergreen") == expected else 0.0


def has_result(output: dict, *_: object) -> float:
    """1 if the search returned at least 1 result."""
    return 1.0 if output.get("result_count", 0) > 0 else 0.0


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=qa_search_executor,
    evaluators={
        "category_match": category_match,
        "difficulty_match": difficulty_match,
        "evergreen_match": evergreen_match,
        "has_result": has_result,
    },
    group_name="qa_classification_quality",
)
