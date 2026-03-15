"""
backfill_extraction_model.py — 追溯回填 Supabase qa_items 的 extraction_model

策略：
  1. 掃描 output/qa_per_meeting/*.json 反查 stable_id → extraction_model
  2. 查無對應 extraction_model 的一律標記 "claude-code"（歷史資料主要由 /extract-qa 生成）
  3. 批次 PATCH 至 Supabase（100 rows/batch）

用法：
  python scripts/backfill_extraction_model.py --dry-run     # 預覽（不寫入）
  python scripts/backfill_extraction_model.py --execute      # 實際寫入
  python scripts/backfill_extraction_model.py --verify       # 驗證 NULL 筆數
  python scripts/backfill_extraction_model.py --limit 5      # 只處理前 5 筆（測試用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

BATCH_SIZE = 100
FETCH_PAGE_SIZE = 1000
DEFAULT_MODEL = "claude-code"


def _compute_stable_id(source_file: str, question: str) -> str:
    """Match Python's compute_stable_id() in 03_dedupe_classify.py."""
    content = f"{source_file}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _scan_per_meeting_files() -> dict[str, str]:
    """Scan qa_per_meeting JSONs to build stable_id → extraction_model map.

    Since current per-meeting files don't contain extraction_model,
    all will map to DEFAULT_MODEL. This function is designed to support
    future per-file model tags.
    """
    qa_dir = ROOT_DIR / "output" / "qa_per_meeting"
    model_map: dict[str, str] = {}

    if not qa_dir.exists():
        logger.warning("qa_per_meeting dir not found: %s", qa_dir)
        return model_map

    for json_file in sorted(qa_dir.glob("*_qa.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Skip %s: %s", json_file.name, e)
            continue

        pairs = data.get("qa_pairs", [])
        file_model = data.get("extraction_model", None)

        for qa in pairs:
            qa_model = qa.get("extraction_model") or file_model
            source_file = qa.get("source_file", "")
            question = qa.get("question", "")
            if not question:
                continue

            sid = _compute_stable_id(source_file, question)
            if qa_model:
                model_map[sid] = qa_model
    return model_map


def _fetch_null_model_ids(
    supabase_url: str,
    service_key: str,
    limit: int = 0,
) -> list[dict]:
    """Fetch qa_items where extraction_model IS NULL."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    items: list[dict] = []
    offset = 0

    while True:
        remaining = limit - len(items) if limit > 0 else FETCH_PAGE_SIZE
        page_limit = min(FETCH_PAGE_SIZE, remaining) if limit > 0 else FETCH_PAGE_SIZE
        if page_limit <= 0:
            break

        url = (
            f"{supabase_url}/rest/v1/qa_items"
            "?select=id"
            "&extraction_model=is.null"
            "&order=seq.asc"
            f"&limit={page_limit}"
            f"&offset={offset}"
        )
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("Fetch failed: %s %s", resp.status_code, resp.text[:200])
            return []

        page_items = resp.json()
        items.extend(page_items)

        if len(page_items) < page_limit:
            break

        offset += len(page_items)

    logger.info("Found %d qa_items with extraction_model IS NULL", len(items))
    return items


def _patch_ids_with_model(
    supabase_url: str,
    service_key: str,
    row_ids: list[str],
    model: str,
) -> tuple[int, int]:
    """PATCH extraction_model for a group of ids sharing the same model."""
    if not row_ids:
        return 0, 0

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    id_filter = ",".join(quote(row_id, safe="") for row_id in row_ids)
    resp = requests.patch(
        f"{supabase_url}/rest/v1/qa_items?id=in.({id_filter})",
        headers=headers,
        json={"extraction_model": model},
        timeout=60,
    )
    if resp.status_code in (200, 204):
        return len(row_ids), 0
    logger.error("Patch failed: %s %s", resp.status_code, resp.text[:300])
    return 0, len(row_ids)


def _patch_batch(
    supabase_url: str,
    service_key: str,
    updates: list[dict],
) -> tuple[int, int]:
    """PATCH a batch of rows — grouped by target model for partial updates."""
    grouped_ids: dict[str, list[str]] = {}
    for update in updates:
        grouped_ids.setdefault(update["model"], []).append(update["id"])

    total_success = 0
    total_fail = 0
    for model, row_ids in grouped_ids.items():
        success, fail = _patch_ids_with_model(supabase_url, service_key, row_ids, model)
        total_success += success
        total_fail += fail

    return total_success, total_fail


def _verify_null_count(supabase_url: str, service_key: str) -> int:
    """Count qa_items where extraction_model IS NULL."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "count=exact",
    }
    resp = requests.get(
        f"{supabase_url}/rest/v1/qa_items?select=id&extraction_model=is.null",
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 200:
        count = int(resp.headers.get("content-range", "*/0").split("/")[-1])
        return count
    return -1


def backfill(
    supabase_url: str,
    service_key: str,
    dry_run: bool = True,
    limit: int = 0,
) -> dict:
    """Main backfill logic. Returns stats dict."""
    # Step 1: scan local per-meeting files for any explicit model tags
    model_map = _scan_per_meeting_files()
    logger.info("Per-meeting scan: %d entries with explicit model", len(model_map))

    # Step 2: fetch null-model rows from Supabase
    null_items = _fetch_null_model_ids(supabase_url, service_key, limit)
    if not null_items:
        logger.info("No rows to backfill")
        return {"total": 0, "updated": 0, "skipped": 0}

    # Step 3: resolve model for each row
    updates = []
    model_stats: dict[str, int] = {}
    for item in null_items:
        model = model_map.get(item["id"], DEFAULT_MODEL)
        updates.append({"id": item["id"], "model": model})
        model_stats[model] = model_stats.get(model, 0) + 1

    logger.info("Model assignment distribution: %s", model_stats)

    if dry_run:
        logger.info("[DRY RUN] Would update %d rows", len(updates))
        logger.info("Sample (first 3): %s", updates[:3])
        return {"total": len(updates), "updated": 0, "skipped": 0, "dry_run": True}

    # Step 4: batch PATCH
    total_success = 0
    total_fail = 0
    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(updates) + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Patching batch %d/%d (%d rows)...", batch_num, total_batches, len(batch))
        success, fail = _patch_batch(supabase_url, service_key, batch)
        total_success += success
        total_fail += fail
        if batch_num < total_batches:
            time.sleep(0.3)

    logger.info("Backfill complete: %d succeeded, %d failed", total_success, total_fail)
    return {"total": len(updates), "updated": total_success, "failed": total_fail}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill extraction_model for Supabase qa_items",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write")
    parser.add_argument("--execute", action="store_true", help="Actually write to Supabase")
    parser.add_argument("--verify", action="store_true", help="Only verify NULL count")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows to process (0=all)")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")
        sys.exit(1)

    if args.verify:
        count = _verify_null_count(supabase_url, service_key)
        logger.info("extraction_model IS NULL count: %d", count)
        return

    dry_run = not args.execute
    if dry_run and not args.dry_run:
        logger.info("Default mode is --dry-run. Use --execute to write.")

    backfill(
        supabase_url=supabase_url,
        service_key=service_key,
        dry_run=dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
