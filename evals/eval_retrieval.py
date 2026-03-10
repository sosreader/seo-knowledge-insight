"""
Laminar offline evaluation: Retrieval quality.

Tests whether the keyword-hybrid search engine returns results containing
the expected SEO keywords and categories for known real-world scenarios.

Dataset:  eval/golden_retrieval.json
Requires: LMNR_PROJECT_API_KEY
Data source: output/qa_final.json (local) or Supabase qa_items (CI fallback)

Run:
    python evals/eval_retrieval.py
    python evals/eval_retrieval.py --model claude-code   # Filter by extraction_model
    python evals/eval_retrieval.py --limit 5             # Limit golden cases
    lmnr eval evals/eval_retrieval.py
"""
from __future__ import annotations

import argparse
import json
import logging
import math
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

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Retrieval quality eval")
_parser.add_argument("--model", type=str, default=None, help="Filter by extraction_model (e.g. claude-code)")
_parser.add_argument("--limit", type=int, default=0, help="Limit golden cases (0=all)")
_args, _unknown = _parser.parse_known_args()
_filter_model: str | None = _args.model
_limit_cases: int = _args.limit

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_retrieval.json"
if not _golden_path.exists():
    print(f"[eval_retrieval] Golden dataset not found: {_golden_path}", file=sys.stderr)
    print("[eval_retrieval] Run the pipeline first (Steps 1–3) to generate output.", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _limit_cases > 0:
    _golden_raw = _golden_raw[:_limit_cases]
    print(f"[eval_retrieval] Limiting to {_limit_cases} golden cases")

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

_API_BASE = os.environ.get("EVAL_API_BASE", "http://localhost:8002")
_API_KEY = os.environ.get("SEO_API_KEY", "")


def _search_via_api(query: str, top_k: int = 5) -> list[dict] | None:
    """Try calling the actual search API. Returns None if server unavailable."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY

    try:
        resp = requests.post(
            f"{_API_BASE}/api/v1/search",
            json={"query": query, "top_k": top_k},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            body = resp.json()
            results = body.get("data", {}).get("results", [])
            if results:
                return results
        logger.warning("[eval_retrieval] API returned %s", resp.status_code)
    except requests.ConnectionError:
        logger.info("[eval_retrieval] API not reachable, falling back to naive search")
    except Exception as e:
        logger.warning("[eval_retrieval] API call failed: %s", e)
    return None


def _load_qa_items() -> list[dict]:
    """Load QA items from local file first, fallback to Supabase REST API."""
    qa_final_path = PROJECT_ROOT / "output" / "qa_final.json"

    # 1. Try local file
    if qa_final_path.exists():
        try:
            data = json.loads(qa_final_path.read_text(encoding="utf-8"))
            items = data.get("qa_database", [])
            if items:
                logger.info("[eval_retrieval] Loaded %d QA items from local file", len(items))
                return items
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[eval_retrieval] Local file read failed: %s", e)

    # 2. Fallback to Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        logger.error("[eval_retrieval] No local qa_final.json and no SUPABASE_URL/SUPABASE_ANON_KEY set")
        return []

    logger.info("[eval_retrieval] Local file not found, loading from Supabase...")
    resp = requests.get(
        f"{supabase_url}/rest/v1/qa_items"
        "?select=id,question,answer,keywords,category,confidence,difficulty,evergreen,"
        "source_title,source_type,source_collection,source_url",
        headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
        timeout=30,
    )

    if resp.status_code != 200:
        logger.error("[eval_retrieval] Supabase fetch failed: %s %s", resp.status_code, resp.text[:200])
        return []

    items = resp.json()
    logger.info("[eval_retrieval] Loaded %d QA items from Supabase", len(items))
    return items


def _naive_search(query: str, qa_items: list[dict]) -> list[dict]:
    """Fallback: naive token-based search when API is unavailable."""
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
    return [qa for _, qa in scored[:5]]


def _filter_by_model(results: list[dict], model: str | None) -> list[dict]:
    """Filter results by extraction_model if specified."""
    if not model:
        return results
    return [r for r in results if r.get("extraction_model") == model]


def retrieval_executor(data: dict) -> dict:
    """Search via actual API first, fallback to naive keyword search."""
    query: str = data["query"]

    # 1. Try the real search API (keyword + synonym + hybrid)
    api_results = _search_via_api(query)
    if api_results is not None:
        filtered = _filter_by_model(api_results, _filter_model)
        return {"results": filtered[:5], "query": query, "source": "api"}

    # 2. Fallback to naive search
    qa_items = _load_qa_items()
    if _filter_model:
        qa_items = [qa for qa in qa_items if qa.get("extraction_model") == _filter_model]
    results = _naive_search(query, qa_items)
    return {"results": results, "query": query, "source": "naive"}


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


def hit_rate(output: dict, target: dict) -> float:
    """1 if at least one top-K result's category is in expected_categories."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    return 1.0 if any(r.get("category", "") in expected_cats for r in results) else 0.0


def mrr(output: dict, target: dict) -> float:
    """Mean Reciprocal Rank: 1/rank of first category-matching result."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    for rank, r in enumerate(results, start=1):
        if r.get("category", "") in expected_cats:
            return 1.0 / rank
    return 0.0


def precision_at_k(output: dict, target: dict) -> float:
    """Precision@K: fraction of top-K results with matching category."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not results:
        return 0.0
    relevant = sum(1 for r in results if r.get("category", "") in expected_cats)
    return relevant / len(results)


def recall_at_k(output: dict, target: dict) -> float:
    """Recall@K: fraction of expected_categories covered by top-K results."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    retrieved_cats = {r.get("category", "") for r in results}
    return len(retrieved_cats & expected_cats) / len(expected_cats)


def ndcg_at_k(output: dict, target: dict) -> float:
    """NDCG@K: normalized discounted cumulative gain (Jarvelin & Kekalainen, 2002)."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    if not results:
        return 0.0

    found_cats: set[str] = set()
    dcg = 0.0
    for rank, r in enumerate(results, start=1):
        cat = r.get("category", "")
        if cat in expected_cats and cat not in found_cats:
            dcg += 1.0 / math.log2(rank + 1)
            found_cats.add(cat)

    n_perfect = min(len(expected_cats), len(results))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_perfect))
    return dcg / idcg if idcg > 0 else 0.0


# ── Threshold gate (CI eval gate) ─────────────────────────────────────────────

_EVALUATOR_MAP = {
    "keyword_hit_rate": keyword_hit_rate,
    "top1_category_match": top1_category_match,
    "top5_category_coverage": top5_category_coverage,
    "hit_rate": hit_rate,
    "mrr": mrr,
    "precision_at_k": precision_at_k,
    "recall_at_k": recall_at_k,
    "ndcg_at_k": ndcg_at_k,
}

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
if _threshold_path.exists():
    with open(_threshold_path, encoding="utf-8") as _tf:
        _retrieval_thresholds: dict[str, float] = json.load(_tf).get("retrieval", {})

    if _retrieval_thresholds:
        print("\n--- CI Eval Gate: retrieval thresholds ---")

        # Pre-compute executor results (reused by evaluate() below via cache)
        _pre_results = [(retrieval_executor(dp["data"]), dp["target"]) for dp in _dataset]
        _exec_cache: dict[str, dict] = {dp["data"]["query"]: out for dp, (out, _) in zip(_dataset, _pre_results)}

        _gate_failed = False
        for _metric, _min_val in _retrieval_thresholds.items():
            _fn = _EVALUATOR_MAP.get(_metric)
            if not _fn:
                continue
            _scores = [_fn(out, tgt) for out, tgt in _pre_results]
            _avg = sum(_scores) / len(_scores) if _scores else 0.0
            if _avg < _min_val:
                print(f"  FAIL: {_metric} = {_avg:.4f} < {_min_val}", file=sys.stderr)
                _gate_failed = True
            else:
                print(f"  PASS: {_metric} = {_avg:.4f} >= {_min_val}")

        if _gate_failed:
            print("\nCI eval gate FAILED. Fix regressions before merging.", file=sys.stderr)
            sys.exit(1)
        print("All retrieval thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
    """Return pre-computed result if available, otherwise call API."""
    cached = _exec_cache.get(data["query"]) if "_exec_cache" in globals() else None
    return cached if cached is not None else retrieval_executor(data)


# ── Run ───────────────────────────────────────────────────────────────────────

_group_name = f"retrieval_quality_{_filter_model}" if _filter_model else "retrieval_quality"
if _filter_model:
    print(f"\n[eval_retrieval] Filtering by extraction_model={_filter_model}")

evaluate(
    data=_dataset,
    executor=_cached_executor if _threshold_path.exists() else retrieval_executor,
    evaluators=_EVALUATOR_MAP,
    group_name=_group_name,
)
