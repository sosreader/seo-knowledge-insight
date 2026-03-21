"""
Local retrieval evaluation — no Laminar dependency.

Runs golden_retrieval.json cases against the search API and computes
a composite score from 8 weighted metrics. Designed for autoresearch
loop: stdout last line is machine-readable COMPOSITE_SCORE=X.XXXX.

Usage:
    .venv/bin/python autoresearch/eval_local.py
    .venv/bin/python autoresearch/eval_local.py --api-base http://localhost:8002
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── CLI ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Local retrieval eval (no Laminar)")
parser.add_argument(
    "--api-base", default="http://localhost:8002", help="API base URL"
)
parser.add_argument("--api-key", default="", help="X-API-Key header value")
parser.add_argument(
    "--golden",
    default=str(PROJECT_ROOT / "eval" / "golden_retrieval.json"),
    help="Path to golden dataset",
)
parser.add_argument("--top-k", type=int, default=5, help="Top-K results")
args = parser.parse_args()

# ── Dataset ──────────────────────────────────────────────────────────────────

golden_path = Path(args.golden)
if not golden_path.exists():
    print(f"Golden dataset not found: {golden_path}", file=sys.stderr)
    sys.exit(1)

with open(golden_path, encoding="utf-8") as f:
    golden_cases: list[dict] = json.load(f)

print(f"[eval_local] {len(golden_cases)} golden cases loaded", file=sys.stderr)


# ── Search executor ──────────────────────────────────────────────────────────

def search_api(query: str, top_k: int = 5) -> list[dict]:
    """Call search API with retry on 429. Returns results list."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    for attempt in range(4):
        resp = requests.post(
            f"{args.api_base}/api/v1/search",
            json={"query": query, "top_k": top_k},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 429:
            wait = 2 ** attempt
            print(f"    429 rate limited, retry in {wait}s...", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", {}).get("results", [])

    resp.raise_for_status()
    return []


# ── Evaluator functions (from evals/eval_retrieval.py) ───────────────────────

def _result_categories(result: dict) -> set[str]:
    categories = result.get("categories")
    if isinstance(categories, list) and categories:
        return {str(c) for c in categories if c}
    cat = result.get("primary_category") or result.get("category", "")
    return {str(cat)} if cat else set()


def keyword_hit_rate(results: list[dict], target: dict) -> float:
    expected_kws: list[str] = target.get("expected_keywords", [])
    if not expected_kws:
        return 1.0
    if not results:
        return 0.0
    pool = " ".join(
        r.get("question", "") + " " + r.get("answer", "") + " "
        + " ".join(r.get("keywords", []))
        for r in results
    ).lower()
    hits = sum(1 for kw in expected_kws if kw.lower() in pool)
    return hits / len(expected_kws)


def hit_rate(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    return 1.0 if any(
        _result_categories(r) & expected_cats for r in results
    ) else 0.0


def mrr(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    for rank, r in enumerate(results, start=1):
        if _result_categories(r) & expected_cats:
            return 1.0 / rank
    return 0.0


def precision_at_k(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not results:
        return 0.0
    relevant = sum(1 for r in results if _result_categories(r) & expected_cats)
    return relevant / len(results)


def recall_at_k(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    retrieved = {c for r in results for c in _result_categories(r)}
    return len(retrieved & expected_cats) / len(expected_cats)


def dual_category_recall_at_k(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if len(expected_cats) < 2:
        return 1.0
    return recall_at_k(results, target)


def multi_label_f1_at_k(results: list[dict], target: dict) -> float:
    p = precision_at_k(results, target)
    r = recall_at_k(results, target)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def boosterless_precision_at_k(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not results:
        return 0.0
    non_booster = [
        r for r in results
        if str(r.get("serving_tier", "canonical")).lower() != "booster"
    ]
    if not non_booster:
        return 0.0
    relevant = sum(
        1 for r in non_booster if _result_categories(r) & expected_cats
    )
    return relevant / len(non_booster)


def ndcg_at_k(results: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    if not results:
        return 0.0
    found: set[str] = set()
    dcg = 0.0
    for rank, r in enumerate(results, start=1):
        cats = _result_categories(r)
        new_hits = (cats & expected_cats) - found
        if new_hits:
            dcg += 1.0 / math.log2(rank + 1)
            found.update(new_hits)
    n_perfect = min(len(expected_cats), len(results))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(n_perfect))
    return dcg / idcg if idcg > 0 else 0.0


# ── Composite score weights ─────────────────────────────────────────────────

WEIGHTS = {
    "hit_rate": 0.20,
    "mrr": 0.20,
    "precision_at_k": 0.15,
    "ndcg_at_k": 0.15,
    "keyword_hit_rate": 0.15,
    "multi_label_f1_at_k": 0.10,
    "dual_category_recall_at_k": 0.03,
    "boosterless_precision_at_k": 0.02,
}

EVALUATORS = {
    "hit_rate": hit_rate,
    "mrr": mrr,
    "precision_at_k": precision_at_k,
    "ndcg_at_k": ndcg_at_k,
    "keyword_hit_rate": keyword_hit_rate,
    "multi_label_f1_at_k": multi_label_f1_at_k,
    "dual_category_recall_at_k": dual_category_recall_at_k,
    "boosterless_precision_at_k": boosterless_precision_at_k,
}


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Verify server reachable
    try:
        resp = requests.get(f"{args.api_base}/health", timeout=5)
        if resp.status_code != 200:
            print(
                f"[eval_local] Server returned {resp.status_code}", file=sys.stderr
            )
            sys.exit(1)
    except requests.ConnectionError:
        print(
            f"[eval_local] Server not reachable at {args.api_base}", file=sys.stderr
        )
        sys.exit(1)

    # Run all cases
    all_scores: dict[str, list[float]] = {k: [] for k in EVALUATORS}
    failures = 0

    for i, case in enumerate(golden_cases):
        query = case["query"]
        try:
            results = search_api(query, args.top_k)
        except Exception as e:
            print(
                f"  [{i+1}/{len(golden_cases)}] FAIL {case['scenario']}: {e}",
                file=sys.stderr,
            )
            failures += 1
            for k in EVALUATORS:
                all_scores[k].append(0.0)
            continue

        for metric_name, evaluator_fn in EVALUATORS.items():
            score = evaluator_fn(results, case)
            all_scores[metric_name].append(score)

        print(
            f"  [{i+1}/{len(golden_cases)}] {case['scenario']}: "
            f"mrr={all_scores['mrr'][-1]:.3f} "
            f"prec={all_scores['precision_at_k'][-1]:.3f}",
            file=sys.stderr,
        )

    if failures == len(golden_cases):
        print("[eval_local] All cases failed", file=sys.stderr)
        sys.exit(1)

    # Compute averages
    averages: dict[str, float] = {}
    for metric_name, scores in all_scores.items():
        averages[metric_name] = sum(scores) / len(scores) if scores else 0.0

    # Compute composite
    composite = sum(
        averages[k] * w for k, w in WEIGHTS.items()
    )

    # Output to stderr: detailed metrics
    print("\n--- Retrieval Eval Results ---", file=sys.stderr)
    for metric_name, avg in sorted(averages.items()):
        weight = WEIGHTS.get(metric_name, 0)
        print(
            f"  {metric_name:35s} = {avg:.4f}  (weight: {weight:.2f})",
            file=sys.stderr,
        )
    print(f"\n  COMPOSITE = {composite:.6f}", file=sys.stderr)
    if failures > 0:
        print(f"  ({failures} failures out of {len(golden_cases)})", file=sys.stderr)

    # Machine-readable output (stdout last line)
    # Also output individual metrics for runner.sh TSV
    metrics_line = "\t".join(
        f"{averages.get(k, 0):.6f}"
        for k in [
            "hit_rate", "mrr", "precision_at_k", "ndcg_at_k",
            "keyword_hit_rate", "multi_label_f1_at_k",
            "dual_category_recall_at_k", "boosterless_precision_at_k",
        ]
    )
    print(f"METRICS={metrics_line}")
    print(f"COMPOSITE_SCORE={composite:.6f}")


if __name__ == "__main__":
    main()
