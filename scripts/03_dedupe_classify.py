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
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

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


from utils.stable_id import compute_stable_id
from utils.maturity_classifier import classify_maturity_level


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
    logger.info("  計算 embeddings ...")
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    embeddings = get_embeddings(texts)

    logger.info("  計算相似度矩陣（向量化）...")
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


def _group_by_collection(qa_pairs: list[dict]) -> dict[str, list[dict]]:
    """按 source_collection 分組（向下相容：無欄位預設 seo-meetings）。"""
    from collections import defaultdict
    by_collection: dict[str, list[dict]] = defaultdict(list)
    for qa in qa_pairs:
        collection = qa.get("source_collection") or "seo-meetings"
        by_collection[collection].append(qa)
    return dict(by_collection)


def _infer_source_type(qa: dict, collection: str) -> str:
    source_type = qa.get("source_type")
    if source_type:
        return str(source_type)
    if collection == "seo-meetings":
        return "meeting"
    return "article"


def _infer_maturity_relevance(qa: dict) -> str | None:
    existing = qa.get("maturity_relevance")
    if existing:
        return str(existing)
    level = classify_maturity_level(
        qa.get("keywords", []),
        qa.get("question", ""),
        qa.get("answer", ""),
    )
    # L4 LLM gate: only when LLM available and rule layer voted L4.
    # Without OPENAI_API_KEY the rule layer's dual-evidence check is the only gate
    # (preserves the OpenAI-less pipeline path; PR #38).
    if level == "L4" and os.getenv("OPENAI_API_KEY", "").strip():
        from utils.maturity_llm_judge import llm_validate_l4
        if not llm_validate_l4(
            qa.get("question", ""),
            qa.get("answer", ""),
            qa.get("keywords", []),
        ):
            return "L3"  # Demoted by LLM gate — was a trendy-topic false positive
    return level


def _normalize_extraction_model(value: object) -> str | None:
    if value is None:
        return None
    model = str(value).strip()
    return model or None


def _collect_source_models(qa_group: list[dict]) -> list[str]:
    seen: set[str] = set()
    models: list[str] = []
    for qa in qa_group:
        model = _normalize_extraction_model(qa.get("extraction_model"))
        if not model or model in seen:
            continue
        seen.add(model)
        models.append(model)
    return models


def _resolve_group_extraction_model(source_models: list[str]) -> str | None:
    if not source_models:
        return None
    if len(source_models) == 1:
        return source_models[0]
    return "mixed"


def _build_extraction_provenance(
    qa_group: list[dict],
    merge_model: str | None,
    merge_strategy: str,
) -> dict:
    source_models = _collect_source_models(qa_group)
    source_ids = [
        str(source_id)
        for source_id in (qa.get("stable_id") for qa in qa_group)
        if source_id
    ]
    status = "unknown"
    if source_models:
        status = "single-source" if len(source_models) == 1 else "mixed-source"
    return {
        "source_models": source_models,
        "source_stable_ids": source_ids,
        "source_count": len(qa_group),
        "merge_model": merge_model,
        "merge_strategy": merge_strategy,
        "provenance_status": status,
    }


@observe(name="deduplicate_qas")
def deduplicate_qas(qa_pairs: list[dict]) -> list[dict]:
    """Collection-scoped 去重：各 collection 內部獨立 dedup，跨 collection 不 dedup。"""
    threshold = config.SIMILARITY_THRESHOLD
    use_remote_llm = bool(os.getenv("OPENAI_API_KEY", "").strip())
    logger.info("去重分析（相似度閾值: %s）", threshold)
    logger.info("原始 Q&A 數量: %d", len(qa_pairs))

    by_collection = _group_by_collection(qa_pairs)
    logger.info("Collections: %s", list(by_collection.keys()))

    all_result: list[dict] = []

    for collection, items in by_collection.items():
        logger.info("── %s（%d 筆）──", collection, len(items))
        groups, unique_indices = find_duplicate_groups(items, threshold)
        logger.info("找到 %d 組重複，獨立 %d 個", len(groups), len(unique_indices))

        result: list[dict] = []

        # 獨立的直接保留（immutable — dict unpacking）
        for idx in unique_indices:
            item = items[idx]
            source_model = _normalize_extraction_model(item.get("extraction_model"))
            provenance = item.get("extraction_provenance") or _build_extraction_provenance(
                [item],
                merge_model=None,
                merge_strategy="none",
            )
            result.append({
                **item,
                "is_merged": False,
                "extraction_model": source_model,
                "extraction_provenance": provenance,
            })

        # 重複的合併
        if groups:
            logger.info("合併重複 Q&A ...")
            for group_i, group in enumerate(tqdm(groups, desc=f"  [{collection}] 合併中")):
                group_qas = [items[idx] for idx in group]

                # 顯示合併的內容
                questions_preview = [q["question"][:40] for q in group_qas]
                tqdm.write(
                    f"  群組 {group_i+1}: {len(group_qas)} 筆 → "
                    f"{questions_preview[0]}..."
                )

                try:
                    merged_raw, used_remote_merge = merge_similar_qas(
                        group_qas,
                        return_used_remote=True,
                    )
                    source_ids = [qa.get("stable_id", "") for qa in group_qas]
                    source_models = _collect_source_models(group_qas)
                    result.append({
                        **merged_raw,
                        "is_merged": True,
                        "merge_count": len(group_qas),
                        "source_type": _infer_source_type(group_qas[0], collection),
                        "source_collection": collection,
                        "source_url": group_qas[0].get("source_url", ""),
                        "stable_id": compute_stable_id_from_sources(source_ids),
                        "extraction_model": _resolve_group_extraction_model(source_models),
                        "extraction_provenance": _build_extraction_provenance(
                            group_qas,
                            merge_model=config.OPENAI_MODEL,
                            merge_strategy="llm",
                        ),
                    })
                except Exception as e:
                    logger.warning("merge_similar_qas failed for group %d: %s", group_i + 1, e, exc_info=True)
                    tqdm.write(f"  合併失敗（保留第一筆）：{e}")
                    result.append({
                        **group_qas[0],
                        "is_merged": False,
                        "merge_note": f"合併失敗，共 {len(group_qas)} 筆相似",
                    })
                    used_remote_merge = False

                if used_remote_merge:
                    time.sleep(0.5)

        logger.info("去重後: %d 筆", len(result))
        all_result.extend(result)

    logger.info("去重後 Q&A 總數: %d", len(all_result))
    return all_result


@observe(name="classify_all_qas")
def classify_all_qas(qa_pairs: list[dict]) -> list[dict]:
    """對每個 Q&A 加分類標籤（回傳新 list，不直接修改傳入的 list）"""
    logger.info("分類標籤（共 %d 個 Q&A）", len(qa_pairs))

    result: list[dict] = []
    for qa in tqdm(qa_pairs, desc="  分類中"):
        try:
            labels, used_remote_classification = classify_qa(
                qa["question"],
                qa["answer"],
                return_used_remote=True,
            )

            new_qa = {
                **qa,
                "source_collection": qa.get("source_collection") or "seo-meetings",
                "source_type": _infer_source_type(qa, qa.get("source_collection") or "seo-meetings"),
                "category": labels.get("category", "其他"),
                "difficulty": labels.get("difficulty", "基礎"),
                "evergreen": labels.get("evergreen", True),
                "maturity_relevance": _infer_maturity_relevance(qa),
            }
        except Exception as e:
            logger.warning("分類失敗: %s", e)
            used_remote_classification = False
            new_qa = {
                **qa,
                "source_collection": qa.get("source_collection") or "seo-meetings",
                "source_type": _infer_source_type(qa, qa.get("source_collection") or "seo-meetings"),
                "category": "其他",
                "difficulty": "基礎",
                "evergreen": True,
                "maturity_relevance": _infer_maturity_relevance(qa),
            }

        result.append(new_qa)
        if used_remote_classification:
            time.sleep(0.3)  # rate limit

    # 統計
    categories: dict[str, int] = {}
    for qa in result:
        cat = qa.get("category", "其他")
        categories[cat] = categories.get(cat, 0) + 1

    logger.info("分類統計：")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        logger.info("  - %s: %d", cat, count)

    return result


def _rebuild_embeddings_from_final() -> None:
    """從現有 qa_final.json 重建 qa_embeddings.npy（優先走 cache，避免重打 API）。

    設計用途：
    - qa_final.json 已存在（Step 3 曾完整跑過）但 qa_embeddings.npy 與之不匹配時
    - 不重跑 dedup / classify，只補齊 embedding 陣列
    """
    final_path = config.OUTPUT_DIR / "qa_final.json"
    if not final_path.exists():
        logger.error("qa_final.json 不存在，請先執行完整 Step 3")
        return

    final_data = json.loads(final_path.read_text(encoding="utf-8"))
    qa_pairs = final_data.get("qa_database", [])
    if not qa_pairs:
        logger.error("qa_final.json 中沒有 qa_database，格式異常")
        return

    # 先統計 cache 命中率（不呼叫 API）
    from utils.pipeline_cache import cache_get
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    hits = sum(1 for t in texts if cache_get("embedding", t) is not None)
    misses = len(texts) - hits
    logger.info("重建 embeddings（%d 筆，cache hit %d，miss %d）", len(texts), hits, misses)
    if misses:
        logger.warning("%d 筆 cache miss，將呼叫 embedding API 補齊", misses)

    _persist_embeddings(qa_pairs)
    logger.info("Embeddings 重建完成")
    logger.info("qa_embeddings.npy: %d rows", len(texts))


def _reclassify_l4_only(execute: bool) -> None:
    """重新分類 qa_final.json 中所有 L4 項目（套用新的雙重證據規則 + LLM gate）。

    用途：L4 retighten sprint（plans/active/maturity-l4-retighten.md）。
    對既有 qa_final.json 中標記 L4 的 Q&A 重跑 _infer_maturity_relevance。
    """
    final_path = config.OUTPUT_DIR / "qa_final.json"
    if not final_path.exists():
        logger.error("qa_final.json 不存在；請先執行完整 Step 3")
        return

    final_data = json.loads(final_path.read_text(encoding="utf-8"))
    qa_pairs = final_data.get("qa_database", [])
    if not qa_pairs:
        logger.error("qa_final.json 中沒有 qa_database，格式異常")
        return

    l4_items = [qa for qa in qa_pairs if qa.get("maturity_relevance") == "L4"]
    logger.info("找到 %d 筆 L4 待重新分類（總共 %d 筆）", len(l4_items), len(qa_pairs))

    transitions = {"L4->L4": 0, "L4->L3": 0, "L4->L2": 0, "L4->L1": 0, "L4->None": 0}
    for qa in l4_items:
        # 強制重跑 — 清掉現有 maturity 欄位讓 _infer_maturity_relevance 走規則路徑
        original = qa.pop("maturity_relevance", None)
        new_level = _infer_maturity_relevance(qa)
        key = f"L4->{new_level or 'None'}"
        transitions[key] = transitions.get(key, 0) + 1
        # 對「原本是 L4 但新規則信心不足回 None」的項目：保守降到 L3
        # 這些是雙重證據規則 demote 後 max_score < 2 的項目——既然舊系統能標 L4，
        # 至少還有部分 L4 跡象，但缺乏實作佐證；降到 L3 比保留 L4 或設 None 更合理
        write_level = new_level if new_level is not None else "L3"
        if execute:
            qa["maturity_relevance"] = write_level
        else:
            # dry-run：恢復原值
            qa["maturity_relevance"] = original

    logger.info("L4 重新分類結果：%s", transitions)
    if not execute:
        logger.info("Dry-run 模式：未寫入檔案。加 --execute 才會寫回。")
        return

    final_path.write_text(
        json.dumps(final_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("已寫回 %s", final_path)


def main(args: argparse.Namespace) -> None:
    # ── Rebuild-only 模式（不需要 OPENAI_API_KEY，只走 embedding cache）──
    if getattr(args, "rebuild_embeddings", False):
        init_laminar()
        _rebuild_embeddings_from_final()
        flush_laminar()
        return

    # ── L4 重新分類模式（套用新雙重證據規則 + LLM gate）──
    if getattr(args, "reclassify_l4_only", False):
        init_laminar()
        _reclassify_l4_only(execute=getattr(args, "execute", False))
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
        env_keys=["OPENAI_API_KEY"] if os.getenv("OPENAI_API_KEY", "").strip() else [],
        step_name="Step 3: 去重 + 分類",
        check_only=getattr(args, "check", False),
    )
    if getattr(args, "check", False):
        return

    logger.info("步驟 3：去重、合併、分類")

    # 讀取原始 Q&A
    raw_path = config.OUTPUT_DIR / "qa_all_raw.json"

    raw_data = json.loads(raw_path.read_text(encoding="utf-8"))
    qa_pairs = raw_data.get("qa_pairs", [])
    logger.info("讀取 %d 個原始 Q&A", len(qa_pairs))

    if args.limit and args.limit < len(qa_pairs):
        qa_pairs = qa_pairs[: args.limit]
        logger.warning("測試模式：僅處理前 %d 個 Q&A", args.limit)

    # 預計算 stable_id（immutable — 建立新 list）
    qa_pairs = [
        {**qa, "stable_id": qa.get("stable_id") or compute_stable_id(
            qa.get("source_file", ""), qa["question"],
        )}
        for qa in qa_pairs
    ]

    # 去重
    if not args.skip_dedup:
        qa_pairs = deduplicate_qas(qa_pairs)
    else:
        logger.info("跳過去重")

    # 分類
    if not args.skip_classify:
        qa_pairs = classify_all_qas(qa_pairs)
    else:
        logger.info("跳過分類")

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
        metadata={
            "qa_count": len(final_qa_pairs),
            "embedding_model": config.OPENAI_EMBEDDING_MODEL,
            "classify_model": config.CLASSIFY_MODEL,
        },
    )
    logger.info("版本記録: %s", version_entry['version_id'])

    # QA DB 快照：複製到 output/snapshots/ 供版本比較
    snapshot_dir = config.OUTPUT_DIR / "snapshots"
    snapshot_dir.mkdir(exist_ok=True)
    snap_ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    snap_path = snapshot_dir / f"qa_final_{snap_ts}.json"
    shutil.copy2(final_path, snap_path)

    # 持久化 embedding 向量（Step 4 語意搜尋可直接載入，免重算）
    _persist_embeddings(final_qa_pairs)

    # 同時輸出一份人類可讀的 Markdown
    _export_readable_md(final_qa_pairs)

    # ── Laminar Dataset 快照：記錄本次知識庫版本 ──
    _push_laminar_kb_snapshot(final_qa_pairs)

    logger.info("步驟 3 完成")
    logger.info("最終 Q&A 數量: %d", len(final_qa_pairs))
    logger.info("JSON: %s", final_path)
    logger.info("快照: %s", snap_path)
    logger.info("Embeddings: %s", config.OUTPUT_DIR / "qa_embeddings.npy")
    logger.info("Embedding Index: %s", config.OUTPUT_DIR / "qa_embeddings_index.json")
    logger.info("Markdown: %s", config.OUTPUT_DIR / "qa_final.md")

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
        logger.info("Laminar 知識庫快照已推送（%d 筆樣本，group: qa_knowledge_base）", len(sample))
    except Exception as exc:
        logger.warning(
            "Laminar KB snapshot push failed (non-fatal): %s", exc
        )


def _persist_embeddings(qa_pairs: list[dict]) -> None:
    """計算並持久化 Q&A embedding，供 Step 4 語意搜尋直接載入。
    同時產生 qa_embeddings_index.json（{stable_id|id: row_index}），
    使增量更新不再依賴位置耦合。key 優先使用 stable_id，fallback 到 id（v2.0 格式）。
    """
    logger.info("持久化 embedding 向量 ...")
    texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
    embeddings = get_embeddings(texts)
    emb_array = np.array(embeddings)
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    np.save(emb_path, emb_array)
    logger.info("已儲存 %s 至 %s", emb_array.shape, emb_path)

    # 產生 id → row_index 映射，供增量更新使用
    # 優先使用 stable_id，fallback 到 id（v2.0 格式）
    index = {}
    for i, qa in enumerate(qa_pairs):
        key = qa.get("stable_id") or qa.get("id")
        if key is not None:
            str_key = str(key)
            if str_key in index:
                logger.warning(
                    "embedding index key collision: %s (row %d overwrites row %d)",
                    str_key, i, index[str_key],
                )
            index[str_key] = i
    index_path = config.OUTPUT_DIR / "qa_embeddings_index.json"
    index_path.write_text(
        json.dumps(index, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("已儲存 embedding index（%d 筆）至 %s", len(index), index_path)


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
    parser.add_argument(
        "--reclassify-l4-only",
        action="store_true",
        help="只對 qa_final.json 中現有 L4 項目套用新分類規則（含 LLM gate）",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="搭配 --reclassify-l4-only：實際寫入；未指定則為 dry-run",
    )
    args = parser.parse_args()
    main(args)
