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
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from tqdm import tqdm

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.openai_helper import get_embeddings, merge_similar_qas, classify_qa
from utils.pipeline_deps import preflight_check, StepDependency
from utils.observability import init_laminar, flush_laminar, observe
from utils.pipeline_version import record_artifact
from scripts.dedupe_helpers import _cosine_similarity_matrix


def compute_stable_id(source_file: str, question: str) -> str:
    """基於內容的確定性 ID，跨次執行不變。"""
    content = f"{source_file}::{question[:120]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def compute_stable_id_from_sources(source_ids: list[str]) -> str:
    """合併後 Q&A 的 stable_id：由所有來源 stable_id 排序後取 hash。"""
    content = "::".join(sorted(source_ids))
    return hashlib.sha256(content.encode()).hexdigest()[:16]


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


@observe(name="deduplicate_qas")
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
        print("\n🔄 合併重複 Q&A ...")
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
                # stable_id 由所有來源 stable_id 排序後取 hash
                source_ids = [qa.get("stable_id", "") for qa in group_qas]
                merged["stable_id"] = compute_stable_id_from_sources(source_ids)
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


@observe(name="classify_all_qas")
def classify_all_qas(qa_pairs: list[dict]) -> list[dict]:
    """對每個 Q&A 加分類標籤（回傳新 list，不直接修改傳入的 list）"""
    print(f"\n🏷️  分類標籤（共 {len(qa_pairs)} 個 Q&A）")

    result: list[dict] = []
    for qa in tqdm(qa_pairs, desc="  分類中"):
        try:
            labels = classify_qa(qa["question"], qa["answer"])
            new_qa = {
                **qa,
                "category": labels.get("category", "其他"),
                "difficulty": labels.get("difficulty", "基礎"),
                "evergreen": labels.get("evergreen", True),
            }
        except Exception as e:
            tqdm.write(f"  ⚠️  分類失敗: {e}")
            new_qa = {
                **qa,
                "category": "其他",
                "difficulty": "基礎",
                "evergreen": True,
            }

        result.append(new_qa)
        time.sleep(0.3)  # rate limit

    # 統計
    categories: dict[str, int] = {}
    for qa in result:
        cat = qa.get("category", "其他")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n   分類統計：")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   - {cat}: {count}")

    return result


def _rebuild_embeddings_from_final() -> None:
    """從現有 qa_final.json 重建 qa_embeddings.npy（優先走 cache，避免重打 API）。

    設計用途：
    - qa_final.json 已存在（Step 3 曾完整跑過）但 qa_embeddings.npy 與之不匹配時
    - 不重跑 dedup / classify，只補齊 embedding 陣列
    """
    final_path = config.OUTPUT_DIR / "qa_final.json"
    if not final_path.exists():
        print("❌ qa_final.json 不存在，請先執行完整 Step 3")
        return

    final_data = json.loads(final_path.read_text(encoding="utf-8"))
    qa_pairs = final_data.get("qa_database", [])
    if not qa_pairs:
        print("❌ qa_final.json 中沒有 qa_database，格式異常")
        return

    # 先統計 cache 命中率（不呼叫 API）
    from utils.pipeline_cache import cache_get
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    hits = sum(1 for t in texts if cache_get("embedding", t) is not None)
    misses = len(texts) - hits
    print(f"\n💾 重建 embeddings（{len(texts)} 筆，cache hit {hits}，miss {misses}）")
    if misses:
        print(f"   ⚠️  {misses} 筆 cache miss，將呼叫 embedding API 補齊")

    _persist_embeddings(qa_pairs)
    print("\n✅ Embeddings 重建完成！")
    print(f"   qa_embeddings.npy: {len(texts)} rows")


def main(args: argparse.Namespace) -> None:
    # ── Rebuild-only 模式（不需要 OPENAI_API_KEY，只走 embedding cache）──
    if getattr(args, "rebuild_embeddings", False):
        init_laminar()
        _rebuild_embeddings_from_final()
        flush_laminar()
        return

    init_laminar()

    # ── Pre-flight 依賴檢查 ──
    preflight_check(
        deps=[
            StepDependency(
                path=config.OUTPUT_DIR / "qa_all_raw.json",
                required=True,
                max_age_days=7,
                hint="請先執行 python scripts/02_extract_qa.py",
            ),
        ],
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 3: 去重 + 分類",
        check_only=getattr(args, "check", False),
    )
    if getattr(args, "check", False):
        return

    print("=" * 60)
    print("🔧 步驟 3：去重、合併、分類")
    print("=" * 60)

    # 讀取原始 Q&A
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    qa_pairs = raw_data.get("qa_pairs", [])
    print(f"\n📥 讀取 {len(qa_pairs)} 個原始 Q&A")

    if args.limit and args.limit < len(qa_pairs):
        qa_pairs = qa_pairs[: args.limit]
        print(f"⚠️  測試模式：僅處理前 {args.limit} 個 Q&A")

    # 預計算 stable_id（跨次執行不變，基於 source_file + question 內容）
    for qa in qa_pairs:
        if not qa.get("stable_id"):
            qa["stable_id"] = compute_stable_id(
                qa.get("source_file", ""),
                qa["question"],
            )

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

    # 加上流水號 id（顯示用）和確認 stable_id（跨系統引用用）
    final_qa_pairs = [
        {
            **qa,
            "id": i,
            "stable_id": qa.get("stable_id") or compute_stable_id(
                qa.get("source_file", ""),
                qa["question"],
            ),
        }
        for i, qa in enumerate(qa_pairs, 1)
    ]

    # 輸出最終結果
    final_output = {
        "version": "1.0",
        "total_count": len(final_qa_pairs),
        "original_count": raw_data.get("total_qa_count", 0),
        "meetings_processed": raw_data.get("meetings_processed", 0),
        "qa_database": final_qa_pairs,
    }

    final_path = config.OUTPUT_DIR / "qa_final.json"
    final_path.write_text(
        json.dumps(final_output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── Layer 2: Version Registry ──────────────────────────────
    version_entry = record_artifact(
        step=3,
        data=final_output,
        metadata={"qa_count": len(final_qa_pairs)},
    )
    print(f"\n🔖 版本記録: {version_entry['version_id']}")

    # QA DB 快照：複製到 output/snapshots/ 供版本比較
    snapshot_dir = config.OUTPUT_DIR / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    snap_ts = datetime.now().strftime("%Y%m%d")
    snap_path = snapshot_dir / f"qa_final_{snap_ts}.json"
    shutil.copy2(final_path, snap_path)

    # 持久化 embedding 向量（Step 4 語意搜尋可直接載入，免重算）
    _persist_embeddings(final_qa_pairs)

    # 同時輸出一份人類可讀的 Markdown
    _export_readable_md(final_qa_pairs)

    # ── Laminar Dataset 快照：記錄本次知識庫版本 ──
    _push_laminar_kb_snapshot(final_qa_pairs)

    print("\n" + "=" * 60)
    print("✅ 步驟 3 完成！")
    print(f"   最終 Q&A 數量: {len(final_qa_pairs)}")
    print(f"   JSON: {final_path}")
    print(f"   快照: {snap_path}")
    print(f"   Embeddings: {config.OUTPUT_DIR / 'qa_embeddings.npy'}")
    print(f"   Embedding Index: {config.OUTPUT_DIR / 'qa_embeddings_index.json'}")
    print(f"   Markdown: {config.OUTPUT_DIR / 'qa_final.md'}")
    print("=" * 60)

    flush_laminar()


def _push_laminar_kb_snapshot(qa_pairs: list[dict]) -> None:
    """Push a sample of the current QA knowledge base to Laminar as an evaluation
    dataset snapshot.

    Registers up to 50 QA pairs under the ``qa_knowledge_base`` group so each
    run of Step 3 produces a versioned entry visible in the Laminar Evaluations
    and Datasets pages.  Non-fatal: silently skips when LMNR_PROJECT_API_KEY is
    not set or the lmnr package is unavailable.
    """
    api_key = os.getenv("LMNR_PROJECT_API_KEY", "")
    if not api_key:
        return
    try:
        from lmnr import evaluate  # type: ignore[import]

        sample = qa_pairs[:50]
        data = [
            {
                "data": {
                    "question": qa["question"],
                    "answer": qa.get("answer", ""),
                    "category": qa.get("category", ""),
                    "keywords": qa.get("keywords", []),
                },
                "target": {"expected_category": qa.get("category", "")},
            }
            for qa in sample
        ]

        def _passthrough(data: dict) -> dict:  # noqa: WPS430
            return data

        evaluate(
            data=data,
            executor=_passthrough,
            evaluators={
                "category_present": lambda output, target: float(
                    bool(output.get("category"))
                )
            },
            group_name="qa_knowledge_base",
            name=f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}",
            project_api_key=api_key,
        )
        print(f"   Laminar 知識庫快照已推送（{len(sample)} 筆樣本 → group: qa_knowledge_base）")
    except Exception as exc:
        logger.warning(
            "Laminar KB snapshot push failed (non-fatal): %s", exc
        )


def _persist_embeddings(qa_pairs: list[dict]) -> None:
    """計算並持久化 Q&A embedding，供 Step 4 語意搜尋直接載入。
    同時產生 qa_embeddings_index.json（{stable_id: row_index}），
    使增量更新不再依賴位置耦合。
    """
    print("\n💾 持久化 embedding 向量 ...")
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    embeddings = get_embeddings(texts)
    emb_array = np.array(embeddings)
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    np.save(emb_path, emb_array)
    print(f"   已儲存 {emb_array.shape} 至 {emb_path}")

    # 產生 stable_id → row_index 映射，供增量更新使用
    index = {
        qa["stable_id"]: i
        for i, qa in enumerate(qa_pairs)
        if qa.get("stable_id")
    }
    index_path = config.OUTPUT_DIR / "qa_embeddings_index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"   已儲存 embedding index（{len(index)} 筆）至 {index_path}")


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
    parser.add_argument("--limit", type=int, default=0, help="測試模式：僅處理前 N 個 Q&A（0 = 全部）")
    parser.add_argument("--check", action="store_true", help="只執行依賴檢查，不實際執行")
    parser.add_argument(
        "--rebuild-embeddings",
        action="store_true",
        help="從現有 qa_final.json 重建 qa_embeddings.npy（優先走 cache，不重跑 dedup/classify）",
    )
    args = parser.parse_args()
    main(args)
