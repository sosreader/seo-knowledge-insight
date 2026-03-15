"""
migrate_to_supabase.py — 一次性將 qa_final.json + qa_embeddings.npy 遷移至 Supabase pgvector

使用方式：
  python scripts/migrate_to_supabase.py
  python scripts/migrate_to_supabase.py --dry-run       # 只驗證，不寫入
  python scripts/migrate_to_supabase.py --batch-size 50 # 調整批次大小

需要環境變數（.env）：
  SUPABASE_URL          -- https://xxx.supabase.co
  SUPABASE_SERVICE_KEY  -- service_role key（能 bypass RLS）

輸入：
  output/qa_final.json       -- QA metadata
  output/qa_enriched.json    -- enriched QA（優先使用，有 synonyms/freshness）
  output/qa_embeddings.npy   -- Float32Array [N x 1536]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Load .env from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

BATCH_SIZE_DEFAULT = 100
OUTPUT_DIR = ROOT_DIR / "output"


def _load_qa_data() -> list[dict[str, Any]]:
    """Load QA items from enriched JSON (prefer) or final JSON."""
    enriched_path = OUTPUT_DIR / "qa_enriched.json"
    final_path = OUTPUT_DIR / "qa_final.json"

    path = enriched_path if enriched_path.exists() else final_path
    logger.info("Loading QA data from %s", path)

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("qa_database", [])
    logger.info("Loaded %d QA items", len(items))
    return items


def _load_embeddings() -> np.ndarray | None:
    """Load embeddings from .npy file. Returns shape [N, 1536] or None."""
    npy_path = OUTPUT_DIR / "qa_embeddings.npy"
    if not npy_path.exists():
        logger.warning("qa_embeddings.npy not found — embeddings will be NULL in Supabase")
        return None

    embeddings = np.load(str(npy_path)).astype(np.float32)
    logger.info("Loaded embeddings: shape %s", embeddings.shape)
    return embeddings


def _map_item(qa: dict[str, Any], embedding: list[float] | None) -> dict[str, Any]:
    """Map a raw QA item + embedding to a Supabase row dict."""
    enrichment = qa.get("_enrichment") or {}
    source_url_value = str(qa.get("source_url") or "").strip()
    enrichment_source_url = str(enrichment.get("source_url") or "").strip()
    notion_url = str(enrichment.get("notion_url") or "").strip()
    return {
        "id": qa.get("stable_id") or _compute_stable_id(
            qa.get("source_title", ""), qa.get("question", "")
        ),
        "seq": qa.get("id"),
        "question": qa["question"],
        "answer": qa["answer"],
        "keywords": qa.get("keywords") or [],
        "confidence": qa.get("confidence") or 0.0,
        "category": qa.get("category") or "",
        "difficulty": qa.get("difficulty") or "",
        "evergreen": bool(qa.get("evergreen", False)),
        "source_title": qa.get("source_title") or "",
        "source_date": qa.get("source_date") or "",
        "source_type": qa.get("source_type") or "meeting",
        "source_collection": qa.get("source_collection") or "seo-meetings",
        "source_url": source_url_value or enrichment_source_url or notion_url,
        "is_merged": bool(qa.get("is_merged", False)),
        "extraction_model": qa.get("extraction_model"),
        "maturity_relevance": qa.get("maturity_relevance") or enrichment.get("maturity_relevance"),
        "synonyms": enrichment.get("synonyms") or [],
        "freshness_score": enrichment.get("freshness_score") if enrichment.get("freshness_score") is not None else 1.0,
        "search_hit_count": enrichment.get("search_hit_count") or 0,
        "embedding": embedding,
    }


def _append_extended_fields(row: dict[str, Any], qa: dict[str, Any]) -> dict[str, Any]:
    """Optionally append retrieval-dimension fields for extended Supabase schemas."""
    return {
        **row,
        "primary_category": qa.get("primary_category") or qa.get("category") or "",
        "categories": qa.get("categories") or [qa.get("category") or ""],
        "intent_labels": qa.get("intent_labels") or [],
        "scenario_tags": qa.get("scenario_tags") or [],
        "serving_tier": qa.get("serving_tier") or "canonical",
        "retrieval_phrases": qa.get("retrieval_phrases") or [],
        "retrieval_surface_text": qa.get("retrieval_surface_text") or "",
        "content_granularity": qa.get("content_granularity") or "strategic",
        "evidence_scope": qa.get("evidence_scope") or [],
        "booster_target_queries": qa.get("booster_target_queries") or [],
        "hard_negative_terms": qa.get("hard_negative_terms") or [],
    }


def _compute_stable_id(source_title: str, question: str) -> str:
    """Compute stable_id matching Python utils/compute_stable_id() and TS computeStableId()."""
    import hashlib
    content = f"{source_title}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _upsert_batch(
    url: str,
    service_key: str,
    rows: list[dict[str, Any]],
) -> tuple[int, int]:
    """
    Upsert a batch of rows into Supabase qa_items via REST API.
    Returns (success_count, fail_count).
    """
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }

    resp = requests.post(
        f"{url}/rest/v1/qa_items",
        headers=headers,
        json=rows,
        timeout=60,
    )

    if resp.status_code in (200, 201):
        return len(rows), 0

    logger.error(
        "Upsert batch failed: status=%d body=%s",
        resp.status_code,
        resp.text[:500],
    )
    return 0, len(rows)


def migrate(
    supabase_url: str,
    service_key: str,
    batch_size: int = BATCH_SIZE_DEFAULT,
    dry_run: bool = False,
    include_extended_fields: bool = False,
) -> None:
    """Main migration logic."""
    items = _load_qa_data()
    embeddings = _load_embeddings()

    if embeddings is not None and len(embeddings) != len(items):
        raise ValueError(
            "Count mismatch: "
            f"{len(items)} items vs {len(embeddings)} embeddings. "
            "Regenerate embeddings before migrating to avoid partial NULL embeddings."
        )

    rows = []
    for i, qa in enumerate(items):
        emb = (
            embeddings[i].tolist()
            if embeddings is not None and i < len(embeddings)
            else None
        )
        row = _map_item(qa, emb)
        if include_extended_fields:
            row = _append_extended_fields(row, qa)
        rows.append(row)

    logger.info("Prepared %d rows for upsert", len(rows))

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d rows in batches of %d", len(rows), batch_size)
        sample = {k: v for k, v in rows[0].items() if k != "embedding"}
        logger.info("Sample row (without embedding): %s", json.dumps(sample, ensure_ascii=False))
        return

    total_success = 0
    total_fail = 0
    total_batches = (len(rows) + batch_size - 1) // batch_size

    for batch_idx in range(0, len(rows), batch_size):
        batch = rows[batch_idx : batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        logger.info("Upserting batch %d/%d (%d rows)...", batch_num, total_batches, len(batch))

        success, fail = _upsert_batch(supabase_url, service_key, batch)
        total_success += success
        total_fail += fail

        # Brief pause to avoid overwhelming Supabase
        if batch_num < total_batches:
            time.sleep(0.2)

    logger.info(
        "Migration complete: %d succeeded, %d failed (total %d)",
        total_success,
        total_fail,
        len(rows),
    )

    if total_fail > 0:
        logger.error("Some rows failed to upsert — check logs above")
        sys.exit(1)


def _verify_count(supabase_url: str, service_key: str) -> int:
    """Verify the count of rows in qa_items table."""
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Prefer": "count=exact",
    }
    resp = requests.get(
        f"{supabase_url}/rest/v1/qa_items?select=id",
        headers=headers,
        timeout=10,
    )
    if resp.status_code == 200:
        count = int(resp.headers.get("content-range", "*/0").split("/")[-1])
        return count
    return -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate qa_final.json + qa_embeddings.npy to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write to Supabase")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT, help="Rows per upsert batch")
    parser.add_argument("--verify", action="store_true", help="Only verify row count in Supabase")
    parser.add_argument(
        "--include-extended-fields",
        action="store_true",
        help="Include retrieval dimension fields (requires matching Supabase columns)",
    )
    args = parser.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if not supabase_url or not service_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment")
        logger.error("Set these in .env or export them before running this script")
        sys.exit(1)

    if args.verify:
        count = _verify_count(supabase_url, service_key)
        logger.info("qa_items count in Supabase: %d", count)
        return

    migrate(
        supabase_url=supabase_url,
        service_key=service_key,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        include_extended_fields=args.include_extended_fields,
    )

    if not args.dry_run:
        count = _verify_count(supabase_url, service_key)
        logger.info("Verification: %d rows in qa_items", count)


if __name__ == "__main__":
    main()
