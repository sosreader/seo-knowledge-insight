#!/usr/bin/env python3
"""
步驟 3：去重、合併、分類

功能：
- 讀取 output/qa_all_raw.json
- 用 embedding 找出相似 Q&A
- 用 LLM 合併重複的
- 對每個 Q&A 加分類標籤
- 輸出最終資料庫 output/qa_final.json

用法：
    python scripts/03_dedupe_classify.py
    python scripts/03_dedupe_classify.py --skip-dedup     # 跳過去重
    python scripts/03_dedupe_classify.py --skip-classify   # 跳過分類
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from tqdm import tqdm

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.openai_helper import get_embeddings, merge_similar_qas, classify_qa
from scripts.dedupe_helpers import _cosine_similarity_matrix


def find_duplicate_groups(
    qa_pairs: list[dict],
    threshold: float,
) -> tuple[list[list[int]], list[int]]:
    """
    用 embedding 找出相似的 Q&A 群組。
    
    回傳：
    - groups: [[idx1, idx2, ...], ...] 需要合併的群組
    - unique: [idx, ...] 沒有重複的獨立 Q&A
    """
    print("  📐 計算 embeddings ...")
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    embeddings = get_embeddings(texts)

    print("  🔍 計算相似度矩陣（向量化）...")
    sim_matrix = _cosine_similarity_matrix(embeddings)
    n = len(qa_pairs)
    merged = set()  # 已被分到某個群組的 index
    groups: list[list[int]] = []

    for i in tqdm(range(n), desc="  分組中"):
        if i in merged:
            continue
        # 用 numpy 一次比對 i 與所有 j>i 的相似度
        sims = sim_matrix[i, i + 1:]
        candidates = np.where(sims >= threshold)[0] + (i + 1)
        # 過濾已分組的
        new_members = [int(j) for j in candidates if j not in merged]
        if new_members:
            group = [i] + new_members
            groups.append(group)
            merged.add(i)
            merged.update(new_members)

    unique = [i for i in range(n) if i not in merged]

    return groups, unique


def deduplicate_qas(qa_pairs: list[dict]) -> list[dict]:
    """去重並合併相似 Q&A"""
    threshold = config.SIMILARITY_THRESHOLD
    print(f"\n📊 去重分析（相似度閾值: {threshold}）")
    print(f"   原始 Q&A 數量: {len(qa_pairs)}")

    groups, unique_indices = find_duplicate_groups(qa_pairs, threshold)
    print(f"   找到 {len(groups)} 組重複")
    print(f"   獨立 Q&A: {len(unique_indices)} 個")

    result: list[dict] = []

    # 獨立的直接保留
    for idx in unique_indices:
        qa = qa_pairs[idx].copy()
        qa["is_merged"] = False
        result.append(qa)

    # 重複的合併
    if groups:
        print(f"\n🔄 合併重複 Q&A ...")
        for group_i, group in enumerate(tqdm(groups, desc="  合併中")):
            group_qas = [qa_pairs[idx] for idx in group]

            # 顯示合併的內容
            questions_preview = [q["question"][:40] for q in group_qas]
            tqdm.write(
                f"  群組 {group_i+1}: {len(group_qas)} 筆 → "
                f"{questions_preview[0]}..."
            )

            try:
                merged = merge_similar_qas(group_qas)
                merged["is_merged"] = True
                merged["merge_count"] = len(group_qas)
                result.append(merged)
            except Exception as e:
                tqdm.write(f"  ⚠️  合併失敗: {e}，保留第一筆")
                qa = group_qas[0].copy()
                qa["is_merged"] = False
                qa["merge_note"] = f"合併失敗，共 {len(group_qas)} 筆相似"
                result.append(qa)

            time.sleep(0.5)

    print(f"\n   去重後 Q&A 數量: {len(result)}")
    return result


def classify_all_qas(qa_pairs: list[dict]) -> list[dict]:
    """對每個 Q&A 加分類標籤"""
    print(f"\n🏷️  分類標籤（共 {len(qa_pairs)} 個 Q&A）")

    for qa in tqdm(qa_pairs, desc="  分類中"):
        try:
            labels = classify_qa(qa["question"], qa["answer"])
            qa["category"] = labels.get("category", "其他")
            qa["difficulty"] = labels.get("difficulty", "基礎")
            qa["evergreen"] = labels.get("evergreen", True)
        except Exception as e:
            tqdm.write(f"  ⚠️  分類失敗: {e}")
            qa["category"] = "其他"
            qa["difficulty"] = "基礎"
            qa["evergreen"] = True

        time.sleep(0.3)  # rate limit

    # 統計
    categories = {}
    for qa in qa_pairs:
        cat = qa.get("category", "其他")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n   分類統計：")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {count}")

    return qa_pairs


def main(args: argparse.Namespace) -> None:
    if not config.OPENAI_API_KEY:
        print("❌ 請設定 OPENAI_API_KEY（在 .env）")
        sys.exit(1)

    print("=" * 60)
    print("🔧 步驟 3：去重、合併、分類")
    print("=" * 60)

    # 讀取原始 Q&A
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"
    if not raw_path.exists():
        print(f"❌ 找不到 {raw_path}，請先執行步驟 2")
        sys.exit(1)

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    qa_pairs = raw_data.get("qa_pairs", [])
    print(f"\n📥 讀取 {len(qa_pairs)} 個原始 Q&A")

    # 去重
    if not args.skip_dedup:
        qa_pairs = deduplicate_qas(qa_pairs)
    else:
        print("\n⏭️  跳過去重")

    # 分類
    if not args.skip_classify:
        qa_pairs = classify_all_qas(qa_pairs)
    else:
        print("\n⏭️  跳過分類")

    # 加上唯一 ID
    for i, qa in enumerate(qa_pairs, 1):
        qa["id"] = i

    # 輸出最終結果
    final_output = {
        "version": "1.0",
        "total_count": len(qa_pairs),
        "original_count": raw_data.get("total_qa_count", 0),
        "meetings_processed": raw_data.get("meetings_processed", 0),
        "qa_database": qa_pairs,
    }

    final_path = config.OUTPUT_DIR / "qa_final.json"
    final_path.write_text(
        json.dumps(final_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 同時輸出一份人類可讀的 Markdown
    _export_readable_md(qa_pairs)

    print("\n" + "=" * 60)
    print(f"✅ 步驟 3 完成！")
    print(f"   最終 Q&A 數量: {len(qa_pairs)}")
    print(f"   JSON: {final_path}")
    print(f"   Markdown: {config.OUTPUT_DIR / 'qa_final.md'}")
    print("=" * 60)


def _export_readable_md(qa_pairs: list[dict]) -> None:
    """輸出人類可讀的 Markdown 版本"""
    lines = [
        "# SEO 問答資料庫",
        "",
        f"共 {len(qa_pairs)} 個問答",
        "",
        "---",
        "",
    ]

    # 按分類分組
    by_category: dict[str, list[dict]] = {}
    for qa in qa_pairs:
        cat = qa.get("category", "其他")
        by_category.setdefault(cat, []).append(qa)

    for cat, qas in sorted(by_category.items()):
        lines.append(f"## {cat} ({len(qas)})")
        lines.append("")

        for qa in qas:
            difficulty = qa.get("difficulty", "")
            evergreen = "🌿" if qa.get("evergreen") else "⏰"
            source = qa.get("source_title", qa.get("source_date", ""))

            lines.append(f"### Q: {qa['question']}")
            lines.append("")
            lines.append(f"**難度**: {difficulty} | **時效**: {evergreen}")
            if source:
                lines.append(f"**來源**: {source}")
            lines.append("")
            lines.append(qa.get("answer", ""))
            lines.append("")
            if qa.get("keywords"):
                lines.append(f"*關鍵字: {', '.join(qa['keywords'])}*")
            lines.append("")
            lines.append("---")
            lines.append("")

    md_path = config.OUTPUT_DIR / "qa_final.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="去重、合併、分類")
    parser.add_argument("--skip-dedup", action="store_true", help="跳過去重")
    parser.add_argument("--skip-classify", action="store_true", help="跳過分類")
    args = parser.parse_args()
    main(args)
