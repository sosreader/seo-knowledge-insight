"""
Laminar offline evaluation: Deduplication quality.

Tests whether the search engine correctly handles near-duplicate QA pairs.
For "should_merge" pairs, both should map to similar search results.
For "should_not_merge" pairs, they should return distinct results.

Dataset:  eval/golden_dedup.json (40 pairs: 20 merge + 20 no-merge)
Requires: LMNR_PROJECT_API_KEY, running TS API (cd api && pnpm dev)

Run:
    python evals/eval_dedup.py
    lmnr eval evals/eval_dedup.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── Config ────────────────────────────────────────────────────────────────────

_API_BASE = os.environ.get("EVAL_API_BASE", "http://localhost:8002")
_API_KEY = os.environ.get("SEO_API_KEY", "")

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_dedup.json"
if not _golden_path.exists():
    print(f"[eval_dedup] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_dataset = [
    {
        "data": {
            "question_a": item["qa_a"]["question"],
            "question_b": item["qa_b"]["question"],
            "keywords_a": item["qa_a"].get("keywords", []),
            "keywords_b": item["qa_b"].get("keywords", []),
        },
        "target": {
            "should_merge": item["should_merge"],
            "pair_id": item["id"],
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────

def _search(query: str) -> list[dict]:
    """Call search API and return top-5 results."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY

    try:
        resp = requests.post(
            f"{_API_BASE}/api/v1/search",
            json={"query": query, "top_k": 5},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {}).get("results", [])
    except Exception as e:
        logger.warning("[eval_dedup] API call failed: %s", e)
    return []


def dedup_executor(data: dict) -> dict:
    """Search for both questions and compare their result overlap."""
    results_a = _search(data["question_a"])
    results_b = _search(data["question_b"])

    # Extract IDs for overlap calculation
    ids_a = {r.get("id", r.get("question", "")[:50]) for r in results_a}
    ids_b = {r.get("id", r.get("question", "")[:50]) for r in results_b}

    # Category overlap
    cats_a = {r.get("category", "") for r in results_a}
    cats_b = {r.get("category", "") for r in results_b}

    overlap = len(ids_a & ids_b)
    union = len(ids_a | ids_b) if ids_a or ids_b else 1
    cat_overlap = len(cats_a & cats_b)

    return {
        "result_overlap": overlap / max(len(ids_a), len(ids_b), 1),
        "jaccard": overlap / union,
        "cat_overlap": cat_overlap,
        "results_a_count": len(results_a),
        "results_b_count": len(results_b),
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

def overlap_consistency(output: dict, target: dict) -> float:
    """
    For merge pairs: high overlap is good (score = jaccard).
    For no-merge pairs: low overlap is good (score = 1 - jaccard).
    """
    jaccard = output.get("jaccard", 0.0)
    if target.get("should_merge"):
        return jaccard
    return 1.0 - jaccard


def category_consistency(output: dict, target: dict) -> float:
    """
    For merge pairs: both should return same categories (1 if cat_overlap > 0).
    For no-merge pairs: different categories preferred (1 if cat_overlap == 0).
    """
    cat_overlap = output.get("cat_overlap", 0)
    if target.get("should_merge"):
        return 1.0 if cat_overlap > 0 else 0.0
    return 1.0 if cat_overlap == 0 else 0.5  # partial credit for no-merge with overlap


def both_have_results(output: dict, *_: object) -> float:
    """1 if both queries returned at least 1 result."""
    a = output.get("results_a_count", 0) > 0
    b = output.get("results_b_count", 0) > 0
    return 1.0 if a and b else 0.0


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=dedup_executor,
    evaluators={
        "overlap_consistency": overlap_consistency,
        "category_consistency": category_consistency,
        "both_have_results": both_have_results,
    },
    group_name="dedup_quality",
)
