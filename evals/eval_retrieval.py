"""
Laminar offline evaluation: Retrieval quality.

Tests whether the keyword-hybrid search engine returns results containing
the expected SEO keywords and categories for known real-world scenarios.

Dataset:  eval/golden_retrieval.json
Requires: LMNR_PROJECT_API_KEY, output/qa_final.json

Run:
    python evals/eval_retrieval.py
    lmnr eval evals/eval_retrieval.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lmnr import evaluate  # type: ignore[import]

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_retrieval.json"
if not _golden_path.exists():
    print(f"[eval_retrieval] Golden dataset not found: {_golden_path}", file=sys.stderr)
    print("[eval_retrieval] Run the pipeline first (Steps 1–3) to generate output.", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_dataset = [
    {
        "data": {"query": item["query"]},
        "target": {
            "expected_keywords": item["expected_keywords"],
            "expected_categories": item.get("expected_categories", []),
            "scenario": item["scenario"],
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────

def retrieval_executor(data: dict) -> dict:
    """Keyword-based search over qa_final.json (no embedding / no OpenAI)."""
    from scripts.qa_tools import _load_qa_final  # type: ignore[import]

    query: str = data["query"]
    qa_items = _load_qa_final()

    query_tokens = set(query.lower().split())
    scored: list[tuple[float, dict]] = []

    for qa in qa_items:
        pool = (
            qa.get("question", "") + " "
            + qa.get("answer", "") + " "
            + " ".join(qa.get("keywords", []))
        ).lower()
        hits = sum(1 for tok in query_tokens if tok in pool)
        if hits > 0:
            scored.append((hits, qa))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [qa for _, qa in scored[:5]]

    return {"results": results, "query": query}


# ── Evaluators ────────────────────────────────────────────────────────────────

def keyword_hit_rate(output: dict, target: dict) -> float:
    """Fraction of expected keywords found anywhere in the top-5 results.

    Uses substring matching so "探索流量" matches "流量", matching the
    fuzzy approach used in 05_evaluate.py.
    """
    results: list[dict] = output.get("results", [])
    expected_kws: list[str] = target.get("expected_keywords", [])

    if not expected_kws:
        return 1.0
    if not results:
        return 0.0

    pool = " ".join(
        qa.get("question", "") + " "
        + qa.get("answer", "") + " "
        + " ".join(qa.get("keywords", []))
        for qa in results
    ).lower()

    hits = sum(1 for kw in expected_kws if kw.lower() in pool)
    return hits / len(expected_kws)


def top1_category_match(output: dict, target: dict) -> float:
    """1 if the top-1 result's category is in expected_categories, else 0."""
    results: list[dict] = output.get("results", [])
    expected_cats: list[str] = target.get("expected_categories", [])

    if not expected_cats or not results:
        return 0.0

    return 1.0 if results[0].get("category", "") in expected_cats else 0.0


def top5_category_coverage(output: dict, target: dict) -> float:
    """Fraction of top-5 results whose category is in expected_categories."""
    results: list[dict] = output.get("results", [])
    expected_cats: list[str] = target.get("expected_categories", [])

    if not expected_cats or not results:
        return 0.0

    matches = sum(1 for r in results if r.get("category", "") in expected_cats)
    return matches / len(results)


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=retrieval_executor,
    evaluators={
        "keyword_hit_rate": keyword_hit_rate,
        "top1_category_match": top1_category_match,
        "top5_category_coverage": top5_category_coverage,
    },
    group_name="retrieval_quality",
)
