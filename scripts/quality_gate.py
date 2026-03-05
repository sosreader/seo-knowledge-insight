"""
quality_gate.py — ETL 後品質門檻檢查（MLOps Quality Gate）

讀取最新的 eval_run 結果（Supabase eval_runs 表或本機 output/evals/）
若任一指標低於門檻則 exit(1)，讓 GitHub Actions fail 並阻止部署。

用法：
  python scripts/quality_gate.py
  python scripts/quality_gate.py --source local        # 讀本機 JSON
  python scripts/quality_gate.py --source supabase     # 讀 Supabase eval_runs 表
  python scripts/quality_gate.py --dry-run             # 只輸出結果，不 exit(1)

品質門檻（依 v2.12 基準線）：
  qa_count_min        1000     — 最少 QA 數量
  hit_rate_min        0.90     — Hit Rate@5 >= 90%
  mrr_min             0.80     — MRR >= 0.80
  avg_confidence_min  0.75     — 平均信心分數 >= 0.75
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── Quality Gate Thresholds ──────────────────────────────────────────────────
THRESHOLDS: dict[str, float] = {
    "qa_count_min": 1000,
    "hit_rate_min": 0.90,
    "mrr_min": 0.80,
    "avg_confidence_min": 0.75,
}
# ────────────────────────────────────────────────────────────────────────────


def _load_from_local() -> dict[str, Any]:
    """
    Load latest eval results from local JSON files.
    Looks for output/evals/eval_results_*.json sorted by mtime.
    """
    evals_dir = ROOT_DIR / "output" / "evals"
    if not evals_dir.exists():
        logger.error("Evals directory not found: %s", evals_dir)
        return {}

    result_files = sorted(evals_dir.glob("eval_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not result_files:
        logger.warning("No eval result files found in %s", evals_dir)
        return {}

    latest = result_files[0]
    logger.info("Loading eval results from %s", latest)
    with latest.open(encoding="utf-8") as f:
        return json.load(f)


def _load_from_supabase() -> dict[str, Any]:
    """Load the latest eval_run from Supabase eval_runs table."""
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY for Supabase source")
        return {}

    resp = requests.get(
        f"{supabase_url}/rest/v1/eval_runs"
        "?select=metrics,qa_count,passed,group_name,run_at"
        "&order=run_at.desc&limit=10",
        headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
        timeout=15,
    )

    if resp.status_code != 200:
        logger.error("Failed to fetch eval_runs: %s %s", resp.status_code, resp.text[:200])
        return {}

    runs = resp.json()
    if not runs:
        logger.warning("No eval runs found in Supabase")
        return {}

    # Aggregate metrics from all recent runs
    merged: dict[str, Any] = {}
    for run in runs:
        merged.update(run.get("metrics") or {})
        if run.get("qa_count"):
            merged["qa_count"] = run["qa_count"]

    logger.info("Loaded %d eval runs from Supabase, merged metrics: %s", len(runs), list(merged.keys()))
    return merged


def _check_thresholds(metrics: dict[str, Any]) -> list[str]:
    """
    Check each threshold. Returns list of failure messages.
    Empty list means all passed.
    """
    failures: list[str] = []

    qa_count = metrics.get("qa_count") or metrics.get("total_qa_count") or 0
    if qa_count < THRESHOLDS["qa_count_min"]:
        failures.append(
            f"qa_count={qa_count} < threshold={int(THRESHOLDS['qa_count_min'])}"
        )

    hit_rate = metrics.get("hit_rate") or metrics.get("hit_rate@5") or 0.0
    if hit_rate < THRESHOLDS["hit_rate_min"]:
        failures.append(
            f"hit_rate={hit_rate:.2%} < threshold={THRESHOLDS['hit_rate_min']:.0%}"
        )

    mrr = metrics.get("mrr") or metrics.get("MRR") or 0.0
    if mrr < THRESHOLDS["mrr_min"]:
        failures.append(
            f"mrr={mrr:.3f} < threshold={THRESHOLDS['mrr_min']:.2f}"
        )

    avg_conf = metrics.get("avg_confidence") or metrics.get("average_confidence") or 0.0
    if avg_conf > 0 and avg_conf < THRESHOLDS["avg_confidence_min"]:
        failures.append(
            f"avg_confidence={avg_conf:.3f} < threshold={THRESHOLDS['avg_confidence_min']:.2f}"
        )

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality gate for ETL pipeline")
    parser.add_argument(
        "--source",
        choices=["local", "supabase"],
        default="local",
        help="Where to read eval metrics from",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results but do not exit(1) on failure",
    )
    args = parser.parse_args()

    logger.info("Quality gate — thresholds: %s", THRESHOLDS)

    if args.source == "supabase":
        metrics = _load_from_supabase()
    else:
        metrics = _load_from_local()

    if not metrics:
        msg = "No eval metrics found — cannot verify quality gate"
        if args.dry_run:
            logger.warning("%s (dry-run: not failing)", msg)
            return
        logger.error(msg)
        sys.exit(1)

    logger.info("Metrics found: %s", {k: v for k, v in metrics.items() if not isinstance(v, dict)})

    failures = _check_thresholds(metrics)

    if not failures:
        logger.info("Quality gate PASSED — all thresholds met")
        return

    for failure in failures:
        logger.error("QUALITY GATE FAILED: %s", failure)

    if args.dry_run:
        logger.warning("Dry-run mode: not exiting with error")
        return

    sys.exit(1)


if __name__ == "__main__":
    main()
