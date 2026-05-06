"""
push_qa_metadata_to_supabase.py — 把本地 qa_final.json 中變動過的 metadata 欄位
（maturity_relevance + extraction_model）精準 PATCH 至 Supabase qa_items。

與 migrate_to_supabase.py 不同：
  - migrate 推全部 3,422 rows + 1536-dim embedding（重）
  - 本腳本只 PATCH 兩個 metadata 欄位，且只對「local 與 Supabase 不一致且 local 有值」的 row 動作

工作流程：
  1. 讀本地 qa_final.json，建 {stable_id: {maturity, model}} dict
  2. 拉 Supabase 對應行的當前值（select=id,maturity_relevance,extraction_model）
  3. 計算差集：local 有值 ∧ supabase 不同 → 該欄需 PATCH
  4. 對每行送 PATCH /qa_items?id=eq.{stable_id}（只送變動欄位）

用法：
  python scripts/push_qa_metadata_to_supabase.py --verify     # 只列差集（不寫入）
  python scripts/push_qa_metadata_to_supabase.py --dry-run    # 預覽
  python scripts/push_qa_metadata_to_supabase.py --execute    # 實際 PATCH
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

QA_FINAL_PATH = ROOT_DIR / "output" / "qa_final.json"
FETCH_PAGE_SIZE = 1000
PATCH_RATE_LIMIT_SEC = 0.05  # 每筆 50ms，3000 筆約 2.5 min


def _get_supabase() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        logger.error("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
        sys.exit(1)
    return url, key


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _load_local() -> dict[str, dict]:
    """{stable_id: {maturity_relevance, extraction_model}}"""
    payload = json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for q in payload.get("qa_database", []):
        sid = q.get("stable_id")
        if not sid:
            continue
        out[sid] = {
            "maturity_relevance": q.get("maturity_relevance"),
            "extraction_model": q.get("extraction_model"),
        }
    return out


def _fetch_supabase(url: str, key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    offset = 0
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    while True:
        endpoint = (
            f"{url}/rest/v1/qa_items"
            f"?select=id,maturity_relevance,extraction_model"
            f"&order=id.asc&limit={FETCH_PAGE_SIZE}&offset={offset}"
        )
        resp = requests.get(endpoint, headers=headers, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for row in rows:
            sid = row.get("id")
            if sid:
                out[sid] = {
                    "maturity_relevance": row.get("maturity_relevance"),
                    "extraction_model": row.get("extraction_model"),
                }
        if len(rows) < FETCH_PAGE_SIZE:
            break
        offset += FETCH_PAGE_SIZE
    return out


def _compute_diff(
    local: dict[str, dict],
    remote: dict[str, dict],
) -> list[dict]:
    """回傳需要 PATCH 的列表，每筆: {stable_id, payload, reasons}"""
    diff: list[dict] = []
    for sid, lvals in local.items():
        rvals = remote.get(sid)
        if rvals is None:
            continue
        payload: dict = {}
        reasons: list[str] = []
        for field in ("maturity_relevance", "extraction_model"):
            lv = lvals.get(field)
            rv = rvals.get(field)
            if lv and lv != rv:
                payload[field] = lv
                reasons.append(f"{field}:{rv or '<NULL>'}→{lv}")
        if payload:
            diff.append({"stable_id": sid, "payload": payload, "reasons": reasons})
    return diff


def _summarize(diff: list[dict]) -> None:
    by_field: Counter = Counter()
    by_target: Counter = Counter()
    for d in diff:
        for field, val in d["payload"].items():
            by_field[field] += 1
            by_target[(field, val)] += 1
    logger.info("=== 差集摘要 ===")
    logger.info("總 PATCH 行數: %d", len(diff))
    for field, count in by_field.most_common():
        logger.info("  %-22s : %d 行需 PATCH", field, count)
    logger.info("=== 目標值分布 ===")
    for (field, val), count in sorted(by_target.items()):
        logger.info("  %-22s ← %-22s : %d", field, val, count)


def _patch_one(url: str, key: str, sid: str, payload: dict) -> bool:
    headers = {**_headers(key), "Prefer": "return=minimal"}
    endpoint = f"{url}/rest/v1/qa_items?id=eq.{sid}"
    try:
        resp = requests.patch(endpoint, headers=headers, json=payload, timeout=15)
        return resp.ok
    except requests.RequestException as exc:
        logger.warning("PATCH %s failed: %s", sid, exc)
        return False


def run(mode: str) -> int:
    url, key = _get_supabase()

    logger.info("讀本地 qa_final.json...")
    local = _load_local()
    logger.info("  本地 %d 個 stable_id", len(local))

    logger.info("拉 Supabase qa_items...")
    remote = _fetch_supabase(url, key)
    logger.info("  Supabase %d 個 id（不限本地交集）", len(remote))

    diff = _compute_diff(local, remote)
    _summarize(diff)

    if mode in ("verify", "dry-run"):
        return 0

    logger.info("=== 開始 PATCH ===")
    success = 0
    fail = 0
    for i, d in enumerate(diff):
        if _patch_one(url, key, d["stable_id"], d["payload"]):
            success += 1
        else:
            fail += 1
        if (i + 1) % 100 == 0:
            logger.info("  進度: %d/%d (success=%d fail=%d)", i + 1, len(diff), success, fail)
        time.sleep(PATCH_RATE_LIMIT_SEC)

    logger.info("=== 完成 ===")
    logger.info("成功: %d", success)
    logger.info("失敗: %d", fail)
    return 0 if fail == 0 else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Push qa_final.json metadata to Supabase")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--verify", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.verify:
        sys.exit(run("verify"))
    if args.dry_run:
        sys.exit(run("dry-run"))
    if args.execute:
        sys.exit(run("execute"))


if __name__ == "__main__":
    main()
