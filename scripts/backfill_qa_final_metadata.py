"""
backfill_qa_final_metadata.py — 回填 output/qa_final.json 缺漏的 metadata 欄位

針對 maturity_relevance 與 extraction_model 兩個欄位，採取 Supabase 優先 +
本地 fallback 策略：

  1. 拉取 Supabase qa_items 全表（id↔stable_id, maturity_relevance, extraction_model）
  2. 對每筆 qa_final 中缺漏（None or missing）的欄位：
     - Supabase 有值 → 採用 Supabase 值（authoritative，可能來自既有人工分類或 OpenAI 模式跑過的結果）
     - Supabase 也無值 → fallback：
       * maturity_relevance: classify_maturity_level()（低信心 return None → 自動 skip，等 LLM 補）
       * extraction_model: "legacy-unknown"（lineage marker；非 heuristic 萃取，僅標 metadata 缺失）
  3. 將補齊後的 qa_database 寫回 output/qa_final.json

用法：
  python scripts/backfill_qa_final_metadata.py --verify    # 只檢視缺漏比例（不寫入）
  python scripts/backfill_qa_final_metadata.py --dry-run   # 預覽會改哪些欄位（不寫入）
  python scripts/backfill_qa_final_metadata.py --execute   # 實際寫回 qa_final.json

Exit codes:
  0 — 成功（含 verify / dry-run）
  1 — Supabase 連線失敗 / 必要欄位缺失 / 寫入失敗
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from utils.maturity_classifier import classify_maturity_level

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(ROOT_DIR / ".env")

QA_FINAL_PATH = ROOT_DIR / "output" / "qa_final.json"
FETCH_PAGE_SIZE = 1000
LEGACY_EXTRACTION_MODEL = "legacy-unknown"
TARGET_FIELDS = ("maturity_relevance", "extraction_model")


def _load_qa_final() -> dict:
    if not QA_FINAL_PATH.exists():
        logger.error("qa_final.json not found at %s", QA_FINAL_PATH)
        sys.exit(1)
    return json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))


def _save_qa_final(payload: dict) -> None:
    QA_FINAL_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _supabase_lookup() -> dict[str, dict]:
    """
    從 Supabase 拉取所有 qa_items metadata，回傳 {stable_id: {maturity_relevance, extraction_model}}。
    無 Supabase 設定時回傳空 dict（純本地 fallback 模式）。
    """
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        logger.warning("Supabase env not set — falling back to local heuristic only")
        return {}

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    lookup: dict[str, dict] = {}
    offset = 0

    while True:
        endpoint = (
            f"{url}/rest/v1/qa_items"
            f"?select=id,maturity_relevance,extraction_model"
            f"&order=id.asc&limit={FETCH_PAGE_SIZE}&offset={offset}"
        )
        try:
            resp = requests.get(endpoint, headers=headers, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Supabase fetch failed at offset=%d: %s", offset, exc)
            sys.exit(1)

        rows = resp.json()
        if not rows:
            break
        for row in rows:
            sid = row.get("id")
            if sid:
                lookup[sid] = {
                    "maturity_relevance": row.get("maturity_relevance"),
                    "extraction_model": row.get("extraction_model"),
                }
        if len(rows) < FETCH_PAGE_SIZE:
            break
        offset += FETCH_PAGE_SIZE

    logger.info("Supabase lookup loaded: %d entries", len(lookup))
    return lookup


def _resolve_value(
    field: str,
    qa: dict,
    supabase_value: str | None,
) -> tuple[str | None, str]:
    """
    回傳 (resolved_value, source) — source 是 "supabase" / "heuristic" / "skip"。
    - 既有非空值不覆蓋（回傳 source="skip"）
    - Supabase 有值優先
    - 否則本地 heuristic
    """
    existing = qa.get(field)
    if existing:
        return existing, "skip"

    if supabase_value:
        return supabase_value, "supabase"

    if field == "maturity_relevance":
        level = classify_maturity_level(
            keywords=qa.get("keywords", []),
            question=qa.get("question", ""),
            answer=qa.get("answer", ""),
        )
        return level, "heuristic" if level else "skip"

    if field == "extraction_model":
        # 缺漏代表「萃取模型未知」（non-canonical lineage），不是 heuristic 萃取。
        # 用 legacy-unknown 表達 metadata 缺失，避免污染 claude-code-heuristic 群體統計。
        return LEGACY_EXTRACTION_MODEL, "legacy-marker"

    return None, "skip"


def _audit(qas: list[dict]) -> dict[str, int]:
    audit = {}
    for field in TARGET_FIELDS:
        audit[field] = sum(1 for q in qas if not q.get(field))
    return audit


def _summarize_changes(changes: list[dict]) -> None:
    by_field_source: Counter = Counter()
    for change in changes:
        by_field_source[(change["field"], change["source"])] += 1
    logger.info("=== 變更摘要 ===")
    for (field, source), count in sorted(by_field_source.items()):
        logger.info("  %-20s ← %-10s : %d", field, source, count)


def run(mode: str) -> int:
    payload = _load_qa_final()
    qas: list[dict] = payload.get("qa_database", [])
    logger.info("Loaded qa_final.json: %d entries", len(qas))

    audit_before = _audit(qas)
    logger.info("=== Missing 統計（執行前）===")
    for field, count in audit_before.items():
        pct = 100 * count / max(len(qas), 1)
        logger.info("  %-20s missing=%d (%.1f%%)", field, count, pct)

    if mode == "verify":
        return 0

    lookup = _supabase_lookup() if mode in ("dry-run", "execute") else {}

    changes: list[dict] = []
    for qa in qas:
        sid = qa.get("stable_id")
        sb = lookup.get(sid, {}) if sid else {}
        for field in TARGET_FIELDS:
            new_val, source = _resolve_value(field, qa, sb.get(field))
            if source == "skip":
                continue
            changes.append(
                {
                    "stable_id": sid,
                    "field": field,
                    "old": qa.get(field),
                    "new": new_val,
                    "source": source,
                }
            )
            if mode == "execute":
                qa[field] = new_val

    _summarize_changes(changes)

    if mode == "dry-run":
        logger.info("Dry-run: %d 個欄位變更（未寫入檔案）", len(changes))
        return 0

    if mode == "execute":
        if not changes:
            logger.info("沒有變更需要寫入")
            return 0
        _save_qa_final(payload)
        logger.info("已寫回 %s（%d 個欄位變更）", QA_FINAL_PATH, len(changes))
        audit_after = _audit(qas)
        logger.info("=== Missing 統計（執行後）===")
        for field, count in audit_after.items():
            pct = 100 * count / max(len(qas), 1)
            logger.info("  %-20s missing=%d (%.1f%%)", field, count, pct)
        return 0

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill qa_final.json metadata")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", action="store_true", help="只列出 Missing 統計（不查 Supabase 不寫入）")
    group.add_argument("--dry-run", action="store_true", help="預覽會改哪些欄位（不寫入）")
    group.add_argument("--execute", action="store_true", help="實際寫回 qa_final.json")
    args = parser.parse_args()

    if args.verify:
        sys.exit(run("verify"))
    if args.dry_run:
        sys.exit(run("dry-run"))
    if args.execute:
        sys.exit(run("execute"))


if __name__ == "__main__":
    main()
