#!/usr/bin/env python3
"""
enrich_qa.py — Offline Q&A Enrichment Pipeline

對 qa_final.json 的每筆 Q&A 計算：
  - synonyms:         關鍵字的同義詞展開（utils/synonym_dict）
  - freshness_score:  時效性分數（utils/freshness，指數衰減）
  - search_hit_count: 搜尋命中次數（從 access_logs 聚合）

輸出：output/qa_enriched.json
  - 與 qa_final.json 格式相同
  - 每筆 Q&A 新增 "_enrichment" 欄位

不消耗 LLM token（純規則式，幂等）。
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# 確保 project root 在 path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from utils.freshness import compute_freshness_score  # noqa: E402
from utils.notion_url_map import build_source_to_notion_url  # noqa: E402
from utils.synonym_dict import expand_keywords  # noqa: E402

OUTPUT_DIR = _ROOT / "output"
QA_FINAL_PATH = OUTPUT_DIR / "qa_final.json"
QA_ENRICHED_PATH = OUTPUT_DIR / "qa_enriched.json"
ACCESS_LOGS_DIR = OUTPUT_DIR / "access_logs"


def _aggregate_hit_counts() -> dict[str, int]:
    """
    從 access_logs/*.jsonl 聚合每筆 Q&A 的搜尋命中次數。

    只計算含 top_score 欄位的新格式記錄（MEDIUM-5 修復後才有）。
    若 access_logs 不存在，回傳空 dict。
    新舊記錄相容：int ID 自動轉 str。
    """
    hit_counts: dict[str, int] = {}
    if not ACCESS_LOGS_DIR.exists():
        return hit_counts

    for log_file in sorted(ACCESS_LOGS_DIR.glob("access_*.jsonl")):
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("event") not in ("search", "chat"):
                    continue
                if "top_score" not in record:
                    continue
                for qa_id in record.get("returned_ids", []):
                    key = str(qa_id)
                    hit_counts[key] = hit_counts.get(key, 0) + 1
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("access_log 讀取失敗：%s — %s", log_file, exc)

    return hit_counts


def _enrich_qa(
    qa: dict,
    hit_counts: dict[str, int],
    notion_url_map: dict[str, str],
) -> dict:
    """
    對單筆 Q&A 計算 enrichment 欄位。

    Args:
        qa:             原始 Q&A dict（qa_final.json 格式）
        hit_counts:     {qa_id: count} 聚合搜尋命中次數
        notion_url_map: {source_file: notion_url} 映射

    Returns:
        新的 dict（不修改原始 qa），加入 "_enrichment" 欄位
    """
    keywords = qa.get("keywords", [])
    source_date = qa.get("source_date", "")
    is_evergreen = bool(qa.get("evergreen", False))

    synonyms = expand_keywords(keywords)
    freshness_score = compute_freshness_score(source_date, is_evergreen)
    qa_id = qa.get("stable_id", str(qa.get("id", 0)))
    search_hit_count = hit_counts.get(qa_id, 0)

    # Notion URL：從 source_file 查映射
    source_file = qa.get("source_file", "")
    notion_url = notion_url_map.get(source_file, "")

    enrichment = {
        "synonyms": synonyms,
        "freshness_score": freshness_score,
        "search_hit_count": search_hit_count,
        "notion_url": notion_url,
    }
    return {**qa, "_enrichment": enrichment}


def run_enrichment(
    input_path: Path = QA_FINAL_PATH,
    output_path: Path = QA_ENRICHED_PATH,
) -> dict:
    """
    執行完整 enrichment pipeline。

    Args:
        input_path:  輸入 qa_final.json
        output_path: 輸出 qa_enriched.json

    Returns:
        {
            "total": int,
            "enriched": int,
            "avg_synonyms": float,
            "avg_freshness": float,
            "notion_url_count": int,
            "notion_url_pct": float,
        }
    """
    if not input_path.exists():
        raise FileNotFoundError(f"找不到輸入檔案：{input_path}")

    logger.info("讀取 %s", input_path)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    qa_list: list[dict] = raw.get("qa_database", [])

    if not qa_list:
        raise ValueError("qa_database 為空，請先執行 Step 3（dedupe-classify）")

    logger.info("聚合 access_logs 搜尋命中次數...")
    hit_counts = _aggregate_hit_counts()
    logger.info("有搜尋記錄的 Q&A：%d 筆", len(hit_counts))

    logger.info("建立 Notion URL 映射...")
    notion_url_map = build_source_to_notion_url()
    logger.info("Notion URL 映射：%d 筆", len(notion_url_map))

    logger.info("Enrichment 中（%d 筆 Q&A）...", len(qa_list))
    enriched_list = [_enrich_qa(qa, hit_counts, notion_url_map) for qa in qa_list]

    total_synonyms = sum(len(qa["_enrichment"]["synonyms"]) for qa in enriched_list)
    total_freshness = sum(qa["_enrichment"]["freshness_score"] for qa in enriched_list)
    total_with_url = sum(1 for qa in enriched_list if qa["_enrichment"].get("notion_url"))
    n = len(enriched_list)

    if notion_url_map and total_with_url == 0:
        logger.warning(
            "Notion URL 映射有 %d 筆但無 Q&A 命中，請確認 source_file 格式是否與映射 key 相符",
            len(notion_url_map),
        )

    output_data = {
        **{k: v for k, v in raw.items() if k != "qa_database"},
        "qa_database": enriched_list,
        "_enriched_at": datetime.now(timezone.utc).isoformat(),
    }

    # 原子寫入
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output_path)
    logger.info("已寫入 %s（%d 筆）", output_path, n)

    stats = {
        "total": n,
        "enriched": n,
        "avg_synonyms": round(total_synonyms / n, 2) if n else 0.0,
        "avg_freshness": round(total_freshness / n, 4) if n else 0.0,
        "notion_url_count": total_with_url,
        "notion_url_pct": round(total_with_url / n * 100, 1) if n else 0.0,
    }
    logger.info(
        "Enrichment 完成：avg_synonyms=%.2f, avg_freshness=%.4f, notion_url=%.1f%%",
        stats["avg_synonyms"],
        stats["avg_freshness"],
        stats["notion_url_pct"],
    )
    return stats


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import argparse

    parser = argparse.ArgumentParser(description="Offline Q&A enrichment（synonym + freshness + usage）")
    parser.add_argument("--input", default=str(QA_FINAL_PATH), help="輸入 JSON 路徑")
    parser.add_argument("--output", default=str(QA_ENRICHED_PATH), help="輸出 JSON 路徑")
    args = parser.parse_args()

    stats = run_enrichment(Path(args.input), Path(args.output))
    print(f"Total Q&A:       {stats['total']}")
    print(f"Avg synonyms:    {stats['avg_synonyms']:.2f}")
    print(f"Avg freshness:   {stats['avg_freshness']:.4f}")
    print(f"Notion URL:      {stats['notion_url_count']}/{stats['total']} ({stats['notion_url_pct']:.1f}%)")
