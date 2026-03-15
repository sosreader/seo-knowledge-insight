"""
backfill_maturity_relevance.py — 追溯回填 Supabase qa_items 的 maturity_relevance

策略：
  1. Rule-based classifier 先處理高信心項目（L1/L4 關鍵字匹配）
  2. 低信心項目標記為 NULL（可後續由 LLM 補分類）
  3. 批次 PATCH 至 Supabase（100 rows/batch）

用法：
  python scripts/backfill_maturity_relevance.py --dry-run     # 預覽分布（不寫入）
  python scripts/backfill_maturity_relevance.py --execute      # 實際寫入
  python scripts/backfill_maturity_relevance.py --verify       # 驗證結果
  python scripts/backfill_maturity_relevance.py --limit 10     # 只處理前 10 筆（測試用）
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

# Add parent dir for utils import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.maturity_classifier import classify_maturity_level

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

BATCH_SIZE = 100
FETCH_PAGE_SIZE = 1000


def _get_supabase_config() -> tuple[str, str]:
    """Return (url, service_key) or exit if not set."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)
    return url, key


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _fetch_all_items(url: str, key: str, limit: int = 0) -> list[dict]:
    """Fetch all qa_items from Supabase (paginated)."""
    items: list[dict] = []
    offset = 0

    while True:
        select = (
            f"{url}/rest/v1/qa_items"
            f"?select=id,question,answer,keywords,maturity_relevance"
            f"&order=seq.asc&limit={FETCH_PAGE_SIZE}&offset={offset}"
        )
        resp = requests.get(select, headers=_headers(key), timeout=30)
        resp.raise_for_status()

        rows = resp.json()
        if not rows:
            break

        items.extend(rows)
        if len(rows) < FETCH_PAGE_SIZE:
            break
        offset += FETCH_PAGE_SIZE

    if limit > 0:
        items = items[:limit]

    return items


def _fetch_null_count(url: str, key: str) -> int:
    """Count items with NULL maturity_relevance."""
    resp = requests.get(
        f"{url}/rest/v1/qa_items?select=id&maturity_relevance=is.null",
        headers={**_headers(key), "Prefer": "count=exact"},
        timeout=30,
    )
    resp.raise_for_status()
    content_range = resp.headers.get("content-range", "*/0")
    return int(content_range.split("/")[1])


def _classify_items(items: list[dict]) -> list[dict]:
    """Run rule-based classifier on all items, return update payloads."""
    updates: list[dict] = []

    for item in items:
        # Skip already classified
        if item.get("maturity_relevance"):
            continue

        level = classify_maturity_level(
            keywords=item.get("keywords", []),
            question=item.get("question", ""),
            answer=item.get("answer", ""),
        )

        if level:
            updates.append({"id": item["id"], "maturity_relevance": level})

    return updates


def _patch_batch(url: str, key: str, updates: list[dict]) -> int:
    """PATCH items in batches. Returns count of successfully patched items."""
    patched = 0

    for i in range(0, len(updates), BATCH_SIZE):
        batch = updates[i : i + BATCH_SIZE]

        for item in batch:
            item_id = item["id"]
            resp = requests.patch(
                f"{url}/rest/v1/qa_items?id=eq.{quote(item_id)}",
                headers={**_headers(key), "Prefer": "return=minimal"},
                json={"maturity_relevance": item["maturity_relevance"]},
                timeout=15,
            )

            if resp.ok:
                patched += 1
            else:
                logger.warning("PATCH failed for %s: %s", item_id, resp.status_code)

        logger.info("Batch %d-%d: %d patched", i, i + len(batch), len(batch))
        time.sleep(0.5)  # Rate limiting

    return patched


def backfill(dry_run: bool = True, limit: int = 0) -> dict:
    """Main backfill entry point."""
    url, key = _get_supabase_config()

    logger.info("Fetching all qa_items...")
    items = _fetch_all_items(url, key, limit)
    logger.info("Fetched %d items", len(items))

    # Classify
    updates = _classify_items(items)

    # Distribution summary
    dist: dict[str, int] = {}
    for u in updates:
        level = u["maturity_relevance"]
        dist[level] = dist.get(level, 0) + 1

    already_classified = sum(
        1 for item in items if item.get("maturity_relevance")
    )
    unclassified = len(items) - already_classified - len(updates)

    logger.info("=== Classification Summary ===")
    logger.info("Total items:        %d", len(items))
    logger.info("Already classified: %d", already_classified)
    logger.info("Newly classified:   %d", len(updates))
    logger.info("Unclassified (low confidence): %d", unclassified)
    for level in ("L1", "L2", "L3", "L4"):
        logger.info("  %s: %d", level, dist.get(level, 0))

    if dry_run:
        logger.info("[DRY-RUN] No changes written to Supabase")
        return {
            "total": len(items),
            "classified": len(updates),
            "unclassified": unclassified,
            "distribution": dist,
            "dry_run": True,
        }

    # Execute
    patched = _patch_batch(url, key, updates)
    logger.info("Patched %d / %d items", patched, len(updates))

    return {
        "total": len(items),
        "classified": len(updates),
        "patched": patched,
        "distribution": dist,
        "dry_run": False,
    }


def verify() -> dict:
    """Verify backfill results — check NULL count."""
    url, key = _get_supabase_config()
    null_count = _fetch_null_count(url, key)
    logger.info("maturity_relevance NULL count: %d", null_count)
    return {"null_count": null_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill maturity_relevance")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--execute", action="store_true", help="Execute backfill")
    parser.add_argument("--verify", action="store_true", help="Verify NULL count")
    parser.add_argument("--limit", type=int, default=0, help="Limit items to process")
    args = parser.parse_args()

    if args.verify:
        result = verify()
        print(json.dumps(result, indent=2))
    elif args.execute:
        result = backfill(dry_run=False, limit=args.limit)
        print(json.dumps(result, indent=2))
    else:
        result = backfill(dry_run=True, limit=args.limit)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
