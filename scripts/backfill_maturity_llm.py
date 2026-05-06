"""
backfill_maturity_llm.py — Claude Code 作為 classifier，補齊 qa_final.json 的
maturity_relevance（L1/L2/L3/L4）缺漏。

工作流程（兩階段）：

  Phase A — prepare-batches:
    1. 讀 output/qa_final.json，找出 maturity_relevance 為 None 的 QA
    2. 切成 N 個 batch JSON 檔，每檔含 stable_id + question + answer + keywords
    3. 輸出到 output/maturity_batches/batch_NN.json
    4. 同時輸出一份 prompt 範本到 output/maturity_batches/SUBAGENT_PROMPT.md

  Phase B（人為操作 - 由 orchestrator 並行 dispatch sub-agents 執行 classification）：
    每個 sub-agent 讀 batch_NN.json，依規則分類，寫 result_NN.json

  Phase C — merge:
    1. 讀所有 result_NN.json
    2. 套用到 qa_final.json（補 maturity_relevance）
    3. 驗證 missing 統計

用法：
  python scripts/backfill_maturity_llm.py prepare-batches --count 8
  # （orchestrator 並行跑 8 個 sub-agent）
  python scripts/backfill_maturity_llm.py merge --execute
  python scripts/backfill_maturity_llm.py merge --dry-run
  python scripts/backfill_maturity_llm.py status
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
QA_FINAL_PATH = ROOT_DIR / "output" / "qa_final.json"
BATCH_DIR = ROOT_DIR / "output" / "maturity_batches"
VALID_LEVELS = {"L1", "L2", "L3", "L4"}


SUBAGENT_PROMPT_TEMPLATE = """\
# Sub-Agent 任務：SEO 成熟度分類

你是 SEO 成熟度分類員。對給定 batch 中每個 Q&A，判定 maturity_relevance（L1/L2/L3/L4）。

## 輸入

讀取檔案：`{batch_path}`

格式：
```json
{{
  "batch_id": "batch_NN",
  "items": [
    {{
      "stable_id": "<hex>",
      "question": "...",
      "answer": "...",
      "keywords": ["..."]
    }}
  ]
}}
```

## 分類標準

- **L1（起步期）**：基礎概念解釋、「什麼是 X」類問題、入門工具介紹、單一指標定義
- **L2（建置期）**：流程建置、指標追蹤、GSC/GA4 設定、canonical/hreflang 設定、基本 SOP
- **L3（優化期）**：A/B 測試、數據分析驅動決策、自動化工具、跨指標關聯分析、優化 SOP
- **L4（領先期）**：預測模型、跨通路整合、AI 驅動策略、競爭情報系統、實驗框架

判斷原則：
1. 看 question 主軸（**做什麼層級的事**），不是看技術術語有多深
2. 「什麼是 / 為什麼會 / 基本介紹」→ L1
3. 「如何設定 / 如何追蹤 / 怎麼做（基本流程）」→ L2
4. 「如何優化 / 如何測試 / 如何分析數據驅動決策」→ L3
5. 「預測 / 自動化策略 / AI 整合 / 跨通路系統設計」→ L4

模糊案例優先選 L2（最常見的中段建置內容）。

## 輸出

寫到：`{result_path}`

格式（**只寫這個 JSON**）：
```json
{{
  "batch_id": "batch_NN",
  "classifications": [
    {{ "stable_id": "<hex>", "maturity_relevance": "L2" }}
  ]
}}
```

要求：
- `classifications` 陣列長度必須等於 `items` 長度（每筆都要有對應分類）
- `maturity_relevance` 只能是 "L1" / "L2" / "L3" / "L4"
- 不要附加任何解釋文字、log 或 markdown，只寫純 JSON
- 不要 fail open——若某筆完全無法判斷，標 "L2"（最保守的中段選擇）

完成後回報「batch_NN 完成 — N 筆分類，分布 {{L1: x, L2: y, L3: z, L4: w}}」。
"""


def _load_qa_final() -> dict:
    if not QA_FINAL_PATH.exists():
        logger.error("qa_final.json not found")
        sys.exit(1)
    return json.loads(QA_FINAL_PATH.read_text(encoding="utf-8"))


def _save_qa_final(payload: dict) -> None:
    QA_FINAL_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def cmd_prepare_batches(count: int) -> int:
    payload = _load_qa_final()
    qas = payload.get("qa_database", [])
    missing = [
        q for q in qas
        if not q.get("maturity_relevance") and q.get("stable_id")
    ]
    logger.info("Total QAs: %d, missing maturity_relevance: %d", len(qas), len(missing))

    if not missing:
        logger.info("無缺漏，跳過")
        return 0

    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    chunk = (len(missing) + count - 1) // count
    for i in range(count):
        items = missing[i * chunk : (i + 1) * chunk]
        if not items:
            continue
        batch_id = f"batch_{i+1:02d}"
        out_path = BATCH_DIR / f"{batch_id}.json"
        out_path.write_text(
            json.dumps(
                {
                    "batch_id": batch_id,
                    "items": [
                        {
                            "stable_id": q["stable_id"],
                            "question": q.get("question", ""),
                            "answer": q.get("answer", ""),
                            "keywords": q.get("keywords", []),
                        }
                        for q in items
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("  %s: %d 筆 → %s", batch_id, len(items), out_path.relative_to(ROOT_DIR))

    prompt_path = BATCH_DIR / "SUBAGENT_PROMPT.md"
    prompt_path.write_text(
        SUBAGENT_PROMPT_TEMPLATE.format(
            batch_path="output/maturity_batches/batch_NN.json",
            result_path="output/maturity_batches/result_NN.json",
        ),
        encoding="utf-8",
    )
    logger.info("Prompt template written: %s", prompt_path.relative_to(ROOT_DIR))
    return 0


def cmd_status() -> int:
    if not BATCH_DIR.exists():
        logger.warning("BATCH_DIR not found: %s", BATCH_DIR)
        return 0
    batches = sorted(BATCH_DIR.glob("batch_*.json"))
    results = sorted(BATCH_DIR.glob("result_*.json"))
    logger.info("batches: %d", len(batches))
    logger.info("results: %d", len(results))
    for b in batches:
        rid = b.name.replace("batch_", "result_")
        rpath = BATCH_DIR / rid
        mark = "✅" if rpath.exists() else "❌"
        logger.info("  %s %s", mark, b.name)
    return 0


def cmd_merge(dry_run: bool) -> int:
    if not BATCH_DIR.exists():
        logger.error("BATCH_DIR not found")
        return 1

    results = sorted(BATCH_DIR.glob("result_*.json"))
    if not results:
        logger.error("no result_*.json found in %s", BATCH_DIR)
        return 1

    classifications: dict[str, str] = {}
    for r in results:
        try:
            data = json.loads(r.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.error("invalid JSON in %s: %s", r.name, exc)
            return 1
        for entry in data.get("classifications", []):
            sid = entry.get("stable_id")
            level = entry.get("maturity_relevance")
            if not sid or level not in VALID_LEVELS:
                logger.warning("skip invalid entry in %s: %s", r.name, entry)
                continue
            classifications[sid] = level

    logger.info("Loaded %d valid classifications from %d result files", len(classifications), len(results))

    payload = _load_qa_final()
    qas = payload.get("qa_database", [])

    applied = 0
    skipped_existing = 0
    no_match = 0
    dist: dict[str, int] = {}
    for qa in qas:
        sid = qa.get("stable_id")
        if not sid or sid not in classifications:
            continue
        if qa.get("maturity_relevance"):
            skipped_existing += 1
            continue
        new_val = classifications[sid]
        if dry_run:
            applied += 1
        else:
            qa["maturity_relevance"] = new_val
            applied += 1
        dist[new_val] = dist.get(new_val, 0) + 1

    seen_qa_sids = {q.get("stable_id") for q in qas}
    no_match = sum(1 for sid in classifications if sid not in seen_qa_sids)

    logger.info("=== 套用摘要 ===")
    logger.info("套用: %d", applied)
    logger.info("已有值跳過: %d", skipped_existing)
    logger.info("classification 找不到對應 QA: %d", no_match)
    for level in ("L1", "L2", "L3", "L4"):
        logger.info("  %s: %d", level, dist.get(level, 0))

    if dry_run:
        logger.info("Dry-run: 不寫入 qa_final.json")
        return 0

    _save_qa_final(payload)
    logger.info("已寫回 qa_final.json")

    remaining = sum(1 for q in qas if not q.get("maturity_relevance"))
    logger.info("剩餘 missing maturity_relevance: %d", remaining)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill qa_final.json maturity_relevance via Claude Code sub-agents")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare-batches", help="切批次")
    p_prep.add_argument("--count", type=int, default=8, help="batch 數量（建議 6-10）")

    sub.add_parser("status", help="顯示 batch 與 result 進度")

    p_merge = sub.add_parser("merge", help="套用 result_*.json 到 qa_final.json")
    g = p_merge.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")

    args = parser.parse_args()
    if args.cmd == "prepare-batches":
        sys.exit(cmd_prepare_batches(args.count))
    if args.cmd == "status":
        sys.exit(cmd_status())
    if args.cmd == "merge":
        sys.exit(cmd_merge(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
