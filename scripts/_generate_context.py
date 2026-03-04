"""
_generate_context.py — 離線 Contextual Embedding 生成

為每個 QA item 生成 situating context，提升 embedding 語意匹配精度。
使用 Claude claude-haiku-4-5（本地可用）+ prompt caching 降低成本。

輸出: output/qa_context.json  {"stable_id": "context string", ...}

使用：
    python scripts/_generate_context.py --limit 10   # 測試 10 筆
    python scripts/_generate_context.py              # 全量生成
    python scripts/_generate_context.py --force      # 強制重新生成
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

QA_ENRICHED_PATH = ROOT / "output" / "qa_enriched.json"
QA_FINAL_PATH = ROOT / "output" / "qa_final.json"
CONTEXT_OUTPUT_PATH = ROOT / "output" / "qa_context.json"

CONTEXT_PROMPT_TEMPLATE = """你是一位 SEO 知識整理員。根據以下 Q&A 的 metadata，生成 2-3 句精簡的定位說明（繁體中文），幫助語意搜尋系統理解這個 Q&A 的核心知識領域。

格式要求：
- 說明涵蓋：來源集合、主題分類、核心概念
- 2-3 句話，每句不超過 30 字
- 不要複述完整問題，而是用概念性語言描述

Metadata:
- 來源集合 (collection): {source_collection}
- 主題分類 (category): {category}
- 問題: {question}
- 關鍵字: {keywords}

生成定位說明（只輸出說明本身，不要額外解釋）："""


def _load_qas() -> list[dict]:
    path = QA_ENRICHED_PATH if QA_ENRICHED_PATH.exists() else QA_FINAL_PATH
    if not path.exists():
        logger.error("找不到 QA 資料：%s", path)
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["qa_database"]


def _get_anthropic_client():
    try:
        import anthropic  # type: ignore[import]
        return anthropic.Anthropic()
    except ImportError:
        logger.error("anthropic SDK 未安裝：pip install anthropic")
        sys.exit(1)
    except Exception as e:
        logger.error("Anthropic client 初始化失敗：%s", e)
        sys.exit(1)


def _generate_context_for_qa(client, qa: dict) -> Optional[str]:
    """為單一 QA item 生成 situating context。失敗回傳 None。"""
    stable_id = qa.get("stable_id", str(qa.get("id", "")))
    question = qa.get("question", "")[:200]
    category = qa.get("category", "未分類")
    source_collection = qa.get("source_collection", "seo-meetings")
    keywords = ", ".join(qa.get("keywords", [])[:5])

    prompt = CONTEXT_PROMPT_TEMPLATE.format(
        source_collection=source_collection,
        category=category,
        question=question,
        keywords=keywords or "無",
    )

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        content = resp.content[0].text if resp.content else ""
        if not content.strip():
            logger.warning("stable_id=%s 生成空白 context，跳過", stable_id)
            return None
        return content.strip()
    except Exception as e:
        logger.error("stable_id=%s 生成失敗：%s", stable_id, e)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="離線生成 QA contextual descriptions")
    parser.add_argument("--limit", type=int, default=0, help="限制處理筆數（0 = 全量）")
    parser.add_argument("--force", action="store_true", help="強制重新生成已存在的 context")
    parser.add_argument("--delay", type=float, default=0.1, help="每筆之間的延遲秒數（避免 rate limit）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    qas = _load_qas()
    if args.limit > 0:
        qas = qas[: args.limit]
    logger.info("載入 %d 筆 QA", len(qas))

    # 載入現有 context（若存在）
    existing: dict[str, str] = {}
    if CONTEXT_OUTPUT_PATH.exists() and not args.force:
        try:
            existing = json.loads(CONTEXT_OUTPUT_PATH.read_text(encoding="utf-8"))
            logger.info("載入現有 context：%d 筆", len(existing))
        except json.JSONDecodeError:
            logger.warning("現有 qa_context.json 格式錯誤，重新生成")

    client = _get_anthropic_client()

    results: dict[str, str] = {**existing}
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, qa in enumerate(qas):
        stable_id = qa.get("stable_id", str(qa.get("id", "")))
        if not stable_id:
            logger.warning("QA #%d 無 stable_id，跳過", i)
            continue

        if stable_id in results and not args.force:
            skip_count += 1
            continue

        context = _generate_context_for_qa(client, qa)
        if context:
            results = {**results, stable_id: context}
            success_count += 1
        else:
            fail_count += 1

        if (i + 1) % 50 == 0:
            logger.info("進度：%d/%d（成功 %d，跳過 %d，失敗 %d）", i + 1, len(qas), success_count, skip_count, fail_count)
            # 中間儲存
            CONTEXT_OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

        if args.delay > 0:
            time.sleep(args.delay)

    # 最終儲存
    CONTEXT_OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "完成：成功 %d，跳過 %d，失敗 %d → 總計 %d 筆，輸出：%s",
        success_count, skip_count, fail_count, len(results), CONTEXT_OUTPUT_PATH
    )


if __name__ == "__main__":
    main()
