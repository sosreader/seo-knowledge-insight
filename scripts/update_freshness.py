"""
update_freshness.py — 批次更新 Supabase qa_items 的 freshness_score（指數衰減）

公式：score = exp(-λ * age_days / half_life)
  - half_life = 540 天（18 個月）
  - evergreen=true 的筆一律維持 1.0
  - 差異 < 0.001 的筆跳過更新

用法：
  python scripts/update_freshness.py --dry-run              # 預覽（不寫入）
  python scripts/update_freshness.py --execute               # 實際寫入
  python scripts/update_freshness.py --verify                # 驗證非 evergreen 舊筆 < 1.0
  python scripts/update_freshness.py --since 2024-01-01      # 只處理指定日期之後的筆
  python scripts/update_freshness.py --limit 10 --dry-run    # 測試用
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
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
HALF_LIFE_DAYS = 540
LAMBDA = math.log(2) / HALF_LIFE_DAYS
MIN_DIFF = 0.001
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def compute_freshness_score(
    source_date: str,
    evergreen: bool,
    reference_date: datetime | None = None,
) -> float:
    """Compute freshness score using exponential decay.

    Args:
        source_date: ISO date string (YYYY-MM-DD)
        evergreen: If True, always returns 1.0
        reference_date: Override for testing (defaults to now UTC)

    Returns:
        Score between 0.0 and 1.0
    """
    if evergreen:
        return 1.0

    if not source_date or len(source_date) < 10:
        return 1.0  # unknown date → treat as fresh

    ref = reference_date or datetime.now(timezone.utc)
    try:
        parsed = datetime.strptime(source_date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return 1.0

    age_days = (ref - parsed).days
    if age_days <= 0:
        return 1.0

    score = math.exp(-LAMBDA * age_days)
    return round(max(score, 0.01), 4)  # floor at 0.01, round to 4 decimals


def _fetch_items(
    supabase_url: str,
    service_key: str,
    since: str | None = None,
    limit: int = 0,
) -> list[dict]:
    """Fetch qa_items for freshness update."""
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
            "?select=id,source_date,evergreen,freshness_score"
            "&order=seq.asc"
            f"&limit={page_limit}"
            f"&offset={offset}"
        )
        if since:
            if not _DATE_RE.fullmatch(since):
                raise ValueError(f"--since must be YYYY-MM-DD, got: {since!r}")
            url += f"&source_date=gte.{since}"

        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("Fetch failed: %s %s", resp.status_code, resp.text[:200])
            return []

        page_items = resp.json()
        items.extend(page_items)

        if len(page_items) < page_limit:
            break

        offset += len(page_items)

    logger.info("Fetched %d qa_items for freshness check", len(items))
    return items


def _patch_ids_with_score(
    supabase_url: str,
    service_key: str,
    row_ids: list[str],
    score: float,
) -> tuple[int, int]:
    """PATCH freshness_score for a group of ids sharing the same score."""
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
        json={"freshness_score": score},
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
    """PATCH a batch of freshness_score updates grouped by score."""
    grouped_ids: dict[float, list[str]] = {}
    for update in updates:
        grouped_ids.setdefault(update["score"], []).append(update["id"])

    total_success = 0
    total_fail = 0
    for score, row_ids in grouped_ids.items():
        success, fail = _patch_ids_with_score(supabase_url, service_key, row_ids, score)
        total_success += success
        total_fail += fail

    return total_success, total_fail


def _compute_updates(
    items: list[dict],
    ref: datetime,
) -> tuple[list[dict], int, int]:
    """Compute freshness updates, returning (updates, skipped, evergreen_count)."""
    updates: list[dict] = []
    skipped = 0
    evergreen_count = 0

    for item in items:
        new_score = compute_freshness_score(
            item.get("source_date", ""),
            item.get("evergreen", False),
            ref,
        )
        old_score = item.get("freshness_score", 1.0) or 1.0

        if item.get("evergreen", False):
            evergreen_count += 1
            if abs(old_score - 1.0) > MIN_DIFF:
                updates.append({"id": item["id"], "score": 1.0})
            else:
                skipped += 1
            continue

        if abs(new_score - old_score) > MIN_DIFF:
            updates.append({"id": item["id"], "score": new_score})
        else:
            skipped += 1

    return updates, skipped, evergreen_count


def _batch_patch_all(
    supabase_url: str,
    service_key: str,
    updates: list[dict],
) -> tuple[int, int]:
    """Execute batch PATCH for all updates. Returns (success, fail)."""
    total_success = 0
    total_fail = 0
    total_batches = (len(updates) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info("Patching batch %d/%d (%d rows)...", batch_num, total_batches, len(batch))
        success, fail = _patch_batch(supabase_url, service_key, batch)
        total_success += success
        total_fail += fail
        if batch_num < total_batches:
            time.sleep(0.3)

    return total_success, total_fail


def update_freshness(
    supabase_url: str,
    service_key: str,
    dry_run: bool = True,
    since: str | None = None,
    limit: int = 0,
) -> dict:
    """Main update logic. Returns stats dict."""
    items = _fetch_items(supabase_url, service_key, since, limit)
    if not items:
        return {"total": 0, "updated": 0, "skipped": 0}

    ref = datetime.now(timezone.utc)
    updates, skipped, evergreen_count = _compute_updates(items, ref)

    logger.info(
        "Analysis: %d total, %d evergreen, %d need update, %d skip (diff < %s)",
        len(items), evergreen_count, len(updates), skipped, MIN_DIFF,
    )

    if dry_run:
        logger.info("[DRY RUN] Would update %d rows", len(updates))
        for s in updates[:5]:
            orig = next((i for i in items if i["id"] == s["id"]), {})
            logger.info("  %s: %s → %.4f (date=%s)", s["id"], orig.get("freshness_score"), s["score"], orig.get("source_date"))
        return {"total": len(items), "updated": 0, "skipped": skipped, "need_update": len(updates), "dry_run": True}

    total_success, total_fail = _batch_patch_all(supabase_url, service_key, updates)
    logger.info("Freshness update complete: %d succeeded, %d failed", total_success, total_fail)
    return {"total": len(items), "updated": total_success, "failed": total_fail, "skipped": skipped}


def _verify(supabase_url: str, service_key: str) -> None:
    """Verify freshness scores are correct."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }
    # Check non-evergreen old items
    resp = requests.get(
        f"{supabase_url}/rest/v1/qa_items"
        "?select=id,source_date,freshness_score,evergreen"
        "&evergreen=eq.false"
        "&source_date=gte.1900-01-01"
        "&source_date=lt.2024-01-01"
        "&freshness_score=gte.1.0"
        "&limit=10",
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 200:
        items = resp.json()
        if items:
            logger.warning(
                "Found %d non-evergreen items before 2024-01-01 with freshness_score >= 1.0",
                len(items),
            )
            for item in items[:3]:
                logger.warning("  %s date=%s score=%s", item["id"], item["source_date"], item["freshness_score"])
        else:
            logger.info("PASS: All non-evergreen old items have freshness_score < 1.0")
    else:
        logger.error("Verify failed: %s", resp.status_code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Update freshness_score for Supabase qa_items")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write")
    parser.add_argument("--execute", action="store_true", help="Actually write to Supabase")
    parser.add_argument("--verify", action="store_true", help="Verify freshness scores")
    parser.add_argument("--since", type=str, default=None, help="Only process items since YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows (0=all)")
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
        sys.exit(1)

    if args.verify:
        _verify(supabase_url, service_key)
        return

    dry_run = not args.execute
    if dry_run and not args.dry_run:
        logger.info("Default mode is --dry-run. Use --execute to write.")

    update_freshness(
        supabase_url=supabase_url,
        service_key=service_key,
        dry_run=dry_run,
        since=args.since,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
