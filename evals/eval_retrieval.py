"""
Laminar offline evaluation: Retrieval quality.

Tests whether the keyword-hybrid search engine returns results containing
the expected SEO keywords and categories for known real-world scenarios.

Dataset:  eval/golden_retrieval.json
Requires: LMNR_PROJECT_API_KEY
Search target: RAG_API_BASE (default online rag-api, keyword mode; see evals/rag_client.py)
Fallback data: output/qa_final.json (local naive search only)

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
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

from evals import rag_client  # noqa: E402

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
            "expected_intents": item.get("expected_intents", []),
            "booster_sensitive": item.get("booster_sensitive", False),
            "scenario": item["scenario"],
        },
    }
    for item in _golden_raw
]


# ── Executor ──────────────────────────────────────────────────────────────────

def _search_via_api(query: str, top_k: int = 5) -> list[dict] | None:
    """Call rag-api POST /search (no mode: keyword when LLM is off). None if unusable."""
    extra = {"extraction_model": _filter_model} if _filter_model else None
    results = rag_client.search_results(query, top_k=top_k, timeout=10, extra=extra)
    return results or None


def _local_items_support_model_filter(items: list[dict], model: str | None) -> bool:
    """Return True if local items can satisfy the requested model filter."""
    if not model:
        return True
    return any(item.get("extraction_model") for item in items)


def _load_qa_items() -> list[dict]:
    """Load QA items from the local output/qa_final.json (naive-search fallback only)."""
    qa_final_path = PROJECT_ROOT / "output" / "qa_final.json"

    if not qa_final_path.exists():
        logger.error("[eval_retrieval] No local qa_final.json for naive fallback")
        return []

    try:
        data = json.loads(qa_final_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("[eval_retrieval] Local file read failed: %s", e)
        return []

    items = data.get("qa_database", [])
    if items and _local_items_support_model_filter(items, _filter_model):
        logger.info("[eval_retrieval] Loaded %d QA items from local file", len(items))
        return items
    if items:
        logger.info(
            "[eval_retrieval] Local file lacks extraction_model for --model=%s", _filter_model
        )
    return []


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


def _result_categories(result: dict) -> set[str]:
    categories = result.get("categories")
    if isinstance(categories, list) and categories:
        return {str(cat) for cat in categories if cat}
    category = result.get("primary_category") or result.get("category", "")
    return {str(category)} if category else set()


def top1_category_match(output: dict, target: dict) -> float:
    """1 if the top-1 result's category is in expected_categories, else 0."""
    results: list[dict] = output.get("results", [])
    expected_cats: list[str] = target.get("expected_categories", [])

    if not expected_cats or not results:
        return 0.0

    return 1.0 if _result_categories(results[0]) & set(expected_cats) else 0.0


def top5_category_coverage(output: dict, target: dict) -> float:
    """Fraction of top-5 results whose category is in expected_categories."""
    results: list[dict] = output.get("results", [])
    expected_cats: list[str] = target.get("expected_categories", [])

    if not expected_cats or not results:
        return 0.0

    matches = sum(1 for r in results if _result_categories(r) & set(expected_cats))
    return matches / len(results)


def hit_rate(output: dict, target: dict) -> float:
    """1 if at least one top-K result's category is in expected_categories."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    return 1.0 if any(_result_categories(r) & expected_cats for r in results) else 0.0


def mrr(output: dict, target: dict) -> float:
    """Mean Reciprocal Rank: 1/rank of first category-matching result."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    for rank, r in enumerate(results, start=1):
        if _result_categories(r) & expected_cats:
            return 1.0 / rank
    return 0.0


def precision_at_k(output: dict, target: dict) -> float:
    """Precision@K: fraction of top-K results with matching category."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not results:
        return 0.0
    relevant = sum(1 for r in results if _result_categories(r) & expected_cats)
    return relevant / len(results)


def recall_at_k(output: dict, target: dict) -> float:
    """Recall@K: fraction of expected_categories covered by top-K results."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    retrieved_cats = {cat for result in results for cat in _result_categories(result)}
    return len(retrieved_cats & expected_cats) / len(expected_cats)


def dual_category_recall_at_k(output: dict, target: dict) -> float:
    """Recall@K for dual-label scenarios. Non-dual cases return 1.0 (neutral)."""
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if len(expected_cats) < 2:
        return 1.0
    return recall_at_k(output, target)


def multi_label_f1_at_k(output: dict, target: dict) -> float:
    """F1 over multi-label category precision/recall in top-K."""
    p = precision_at_k(output, target)
    r = recall_at_k(output, target)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def boosterless_precision_at_k(output: dict, target: dict) -> float:
    """Precision@K computed after excluding booster tier items."""
    results: list[dict] = output.get("results", [])
    expected_cats: set[str] = set(target.get("expected_categories", []))
    if not results:
        return 0.0

    non_booster = [
        result for result in results
        if str(result.get("serving_tier", "canonical")).lower() != "booster"
    ]
    if not non_booster:
        return 0.0
    relevant = sum(1 for result in non_booster if _result_categories(result) & expected_cats)
    return relevant / len(non_booster)


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
        cats = _result_categories(r)
        new_hits = (cats & expected_cats) - found_cats
        if new_hits:
            dcg += 1.0 / math.log2(rank + 1)
            found_cats.update(new_hits)

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
    "dual_category_recall_at_k": dual_category_recall_at_k,
    "multi_label_f1_at_k": multi_label_f1_at_k,
    "boosterless_precision_at_k": boosterless_precision_at_k,
    "ndcg_at_k": ndcg_at_k,
}

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _threshold_section() -> str:
    """'retrieval' (hybrid, LLM on) or 'retrieval_keyword' (rag-api answers llm_disabled)."""
    return "retrieval" if rag_client.llm_available() else "retrieval_keyword"


def _target_unavailable_reason() -> str | None:
    """Why the search target can't be used (None when usable or a local file exists)."""
    if (PROJECT_ROOT / "output" / "qa_final.json").exists():
        return None
    ok, reason = rag_client.preflight()
    return None if ok else reason


def _run_threshold_gate() -> None:
    """Run retrieval threshold gate and populate executor cache."""
    global _exec_cache

    if not _threshold_path.exists():
        _exec_cache = {}
        return

    section = _threshold_section()
    with open(_threshold_path, encoding="utf-8") as _tf:
        retrieval_thresholds: dict[str, float] = json.load(_tf).get(section, {})

    if not retrieval_thresholds:
        _exec_cache = {}
        return

    print(f"\n--- CI Eval Gate: {section} thresholds ---")

    pre_results = [(retrieval_executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {dp["data"]["query"]: out for dp, (out, _) in zip(_dataset, pre_results)}

    gate_failed = False
    for metric, min_val in retrieval_thresholds.items():
        evaluator = _EVALUATOR_MAP.get(metric)
        if not evaluator:
            continue
        scores = [evaluator(out, tgt) for out, tgt in pre_results]
        avg = sum(scores) / len(scores) if scores else 0.0
        if avg < min_val:
            print(f"  FAIL: {metric} = {avg:.4f} < {min_val}", file=sys.stderr)
            gate_failed = True
        else:
            print(f"  PASS: {metric} = {avg:.4f} >= {min_val}")

    if gate_failed:
        print("\nCI eval gate FAILED. Fix regressions before merging.", file=sys.stderr)
        sys.exit(1)
    print("All retrieval thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
    """Return pre-computed result if available, otherwise call API."""
    cached = _exec_cache.get(data["query"])
    return cached if cached is not None else retrieval_executor(data)


def run_eval() -> None:
    """Run threshold gate and Laminar evaluation."""
    unavailable = _target_unavailable_reason()
    if unavailable:
        # GitHub Actions annotation keeps the skip visible without failing the job.
        print(f"::warning::eval_retrieval SKIP: {unavailable} (base={rag_client.rag_api_base()})")
        print(f"[eval_retrieval] SKIP: {unavailable}", file=sys.stderr)
        return

    _run_threshold_gate()

    group_name = f"retrieval_quality_{_filter_model}" if _filter_model else "retrieval_quality"
    if _filter_model:
        print(f"\n[eval_retrieval] Filtering by extraction_model={_filter_model}")

    evaluate(
        data=_dataset,
        executor=_cached_executor if _threshold_path.exists() else retrieval_executor,
        evaluators=_EVALUATOR_MAP,
        group_name=group_name,
    )


if __name__ == "__main__":
    run_eval()
