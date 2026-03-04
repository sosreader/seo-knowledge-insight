#!/usr/bin/env python3
"""
push_golden_to_laminar.py — 將 eval/ 目錄的 golden sets 推送到 Laminar Datasets

每個 golden set 對應一個 Laminar Dataset：
  golden_retrieval.json  → golden-retrieval  (20 筆 retrieval cases)
  golden_qa.json         → golden-qa         (48 筆 QA evaluation cases)
  golden_extraction.json → golden-extraction (5 筆 extraction cases)
  golden_dedup.json      → golden-dedup
  golden_report.json     → golden-report
  golden_seo_analysis.json → golden-seo-analysis

Usage:
    .venv/bin/python scripts/push_golden_to_laminar.py
    .venv/bin/python scripts/push_golden_to_laminar.py --dataset golden-retrieval
    .venv/bin/python scripts/push_golden_to_laminar.py --dry-run
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

import os  # noqa: E402

import httpx  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

LMNR_BASE_URL = os.getenv("LMNR_BASE_URL", "https://api.lmnr.ai")
LMNR_API_KEY = os.getenv("LMNR_PROJECT_API_KEY", "")

EVAL_DIR = PROJECT_ROOT / "eval"

GOLDEN_DATASETS = {
    "golden-retrieval": "golden_retrieval.json",
    "golden-qa": "golden_qa.json",
    "golden-extraction": "golden_extraction.json",
    "golden-dedup": "golden_dedup.json",
    "golden-report": "golden_report.json",
    "golden-seo-analysis": "golden_seo_analysis.json",
}


def _to_datapoints(name: str, items: list) -> list[dict]:
    """Convert golden set items to Laminar datapoint format.

    Laminar datapoint format: {"data": {...}, "target": {...}, "metadata": {...}}
    We put the full item in `data` and extract common target fields if present.
    """
    datapoints = []
    for item in items:
        item = dict(item)

        # Extract target fields by dataset type
        target: dict = {}
        if name == "golden-retrieval":
            target = {
                "expected_keywords": item.pop("expected_keywords", []),
                "expected_categories": item.pop("expected_categories", []),
            }
        elif name == "golden-qa":
            target = {
                "expected_category": item.pop("expected_category", None),
                "expected_difficulty": item.pop("expected_difficulty", None),
                "expected_evergreen": item.pop("expected_evergreen", None),
            }

        datapoints.append({
            "data": item,
            "target": target,
            "metadata": {"source": "eval-golden-set", "dataset": name},
        })
    return datapoints


def push_dataset(name: str, filepath: Path, dry_run: bool = False) -> int:
    """Push a golden set JSON file to Laminar as a Dataset. Returns count pushed."""
    if not filepath.exists():
        logger.warning("File not found: %s — skipping", filepath)
        return 0

    raw = json.loads(filepath.read_text(encoding="utf-8"))
    items = raw if isinstance(raw, list) else [raw]
    datapoints = _to_datapoints(name, items)

    logger.info(
        "Dataset: %-28s  file: %-30s  items: %d",
        name, filepath.name, len(datapoints),
    )

    if dry_run:
        logger.info("  [dry-run] would push %d datapoints", len(datapoints))
        return len(datapoints)

    headers = {
        "Authorization": f"Bearer {LMNR_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "datasetName": name,
        "datapoints": datapoints,
        "createDataset": True,
    }

    resp = httpx.post(
        f"{LMNR_BASE_URL}/v1/datasets/datapoints",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if resp.status_code in (200, 201):
        logger.info("  pushed %d datapoints  (HTTP %d)", len(datapoints), resp.status_code)
        return len(datapoints)
    else:
        logger.error("  FAILED  HTTP %d: %s", resp.status_code, resp.text[:200])
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Push eval/ golden sets to Laminar Datasets"
    )
    parser.add_argument(
        "--dataset", metavar="NAME",
        help="Only push this dataset (e.g. golden-retrieval). Omit for all.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be pushed")
    args = parser.parse_args()

    if not LMNR_API_KEY:
        logger.error("LMNR_PROJECT_API_KEY not set in .env — aborting")
        sys.exit(1)

    targets = (
        {args.dataset: GOLDEN_DATASETS[args.dataset]}
        if args.dataset and args.dataset in GOLDEN_DATASETS
        else GOLDEN_DATASETS
    )

    total = 0
    for ds_name, filename in targets.items():
        total += push_dataset(ds_name, EVAL_DIR / filename, dry_run=args.dry_run)

    logger.info("Done. Total datapoints pushed: %d", total)


if __name__ == "__main__":
    main()
