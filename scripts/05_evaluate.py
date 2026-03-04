#!/usr/bin/env python3
"""
步驟 5：Q&A 品質評估（Evaluation）

功能：
- 從 qa_final.json 或 qa_all_raw.json 隨機抽樣 Q&A
- 用 LLM-as-Judge 對每筆 Q&A 做四維度評分
- 驗證分類準確度（與 golden set 對比）
- 驗證 confidence 校準度
- 產出評估報告 output/eval_report.json + eval_report.md

評估維度（1–5 分）：
  1. Relevance（相關性）：Q&A 是否涵蓋真正有價值的 SEO 知識
  2. Accuracy（準確性）：A 是否忠實反映原始會議內容
  3. Completeness（完整性）：A 是否有足夠上下文讓讀者理解
  4. Granularity（粒度）：Q 的範圍是否恰當

用法：
    python scripts/05_evaluate.py                      # 預設抽樣 30 筆
    python scripts/05_evaluate.py --sample 50          # 抽樣 50 筆
    python scripts/05_evaluate.py --with-source        # 帶入原始 Markdown 做 Accuracy 驗證
    python scripts/05_evaluate.py --classify-only      # 只評估分類品質
    python scripts/05_evaluate.py --golden eval/golden_qa.json  # 對照 golden set
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import numpy as np

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

from utils.pipeline_deps import preflight_check, StepDependency
from utils.observability import init_laminar, flush_laminar, observe

from openai import OpenAI

# ──────────────────────────────────────────────────────
# 評估 Prompt
# ──────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """\
你是一位 Q&A 品質評審員，專精 SEO 領域。

你的任務是評估從 SEO 顧問會議紀錄中萃取的 Q&A 品質。請依以下四個維度評分（1–5 分）：

1. **Relevance（相關性）**：Q&A 是否涵蓋真正有價值的 SEO 知識
   - 1 分：萃取了行政內容、閒聊或無意義的對話
   - 3 分：相關但過於表面或偏離核心議題
   - 5 分：精準捕捉到會議的關鍵 SEO 知識點

2. **Accuracy（準確性）**：A 的內容是否合理且無明顯虛構
   - 1 分：明顯失真或虛構了不可能存在的資訊
   - 3 分：大致正確但有模糊或不精確之處
   - 5 分：論述合理，無明顯問題

3. **Completeness（完整性）**：A 是否包含足夠的上下文讓讀者理解
   - 1 分：答案片段化，缺少關鍵脈絡
   - 3 分：有 What/Why 但 How 完全缺失（無任何可執行步驟）
   - 4 分：How 含 `[補充]` 標記的通用 SEO 標準步驟（清楚標記非會議原文）
   - 5 分：What/Why/How 齊全，且 How 有具體到此次情境的步驟

   **重要**：`[補充]` 標記 = 通用 SEO 標準做法（非此次會議特定內容）。
   這是誠實歸因的正確做法，**不應視為幻覺**。

4. **Granularity（粒度）**：Q 的範圍是否恰當（不太粗也不太細）
   - 1 分：多個不相關主題塞在一個 Q 裡
   - 3 分：粒度偏大或偏小，但尚可
   - 5 分：一個 Q 聚焦一個主題，可獨立理解

額外檢查：
- **Confidence 校準**：confidence 分數是否與內容確定度一致（合理 / 偏高 / 偏低）
- **Self-contained**：Q 是否不需要看過原會議就能理解（是 / 否）
- **Actionable**：A 是否提供了可執行的建議（是 / 部分 / 否）

用繁體中文回答。
"""

JUDGE_WITH_SOURCE_PROMPT = """\
你是一位 Q&A 品質評審員，專精 SEO 領域。

你的任務是根據「原始會議紀錄」來評估萃取的 Q&A 品質。
請特別注意 Accuracy（準確性）— A 的內容是否忠實反映原始會議紀錄，有無添加或曲解。

評分維度（1–5 分）同上。但多了一個額外維度：
- **Faithfulness（忠實度）**：A 中的每句陳述是否都能追溯到原始會議文本（1–5 分）
  - 1 分：大量虛構或添加了原文沒有的內容
  - 3 分：大致忠實但有小幅推論或補充
  - 5 分：完全忠實，每個論點都能在原文找到對應

用繁體中文回答。
"""

CLASSIFY_EVAL_PROMPT = """\
你是 SEO 分類專家。以下是一個 Q&A 以及它被系統標記的分類。
請判斷這個分類是否正確。

分類選項：
- 索引與檢索、連結策略、搜尋表現分析、內容策略、Discover與AMP
- 技術SEO、GA與數據追蹤、平台策略、演算法與趨勢、其他

請回答：
1. 系統標記的分類是否正確？（correct / incorrect / borderline）
2. 如果不正確，正確的分類應該是什麼？
3. difficulty（基礎/進階）是否合理？
4. evergreen（常青/時效性）是否合理？

用繁體中文回答。
"""


def _client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)


# ──────────────────────────────────────────────────────
# 載入資料
# ──────────────────────────────────────────────────────

def load_qa_data() -> list[dict]:
    """載入 Q&A 資料，優先 qa_final.json"""
    final = config.OUTPUT_DIR / "qa_final.json"
    raw = config.OUTPUT_DIR / "qa_all_raw.json"

    if final.exists():
        data = json.loads(final.read_text(encoding="utf-8"))
        qas = data.get("qa_database", [])
        if qas:
            return qas

    if raw.exists():
        data = json.loads(raw.read_text(encoding="utf-8"))
        return data.get("qa_pairs", [])

    return []


def load_source_markdown(source_file: str) -> str:
    """載入原始會議 Markdown"""
    md_path = config.RAW_MD_DIR / source_file
    if md_path.exists():
        return md_path.read_text(encoding="utf-8")
    return ""


def load_golden_retrieval(path: str = "") -> list[dict]:
    """載入 retrieval golden set"""
    if not path:
        path = str(config.ROOT_DIR / "eval" / "golden_retrieval.json")
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return []


# ──────────────────────────────────────────────────────
# Retrieval 品質評估
# ──────────────────────────────────────────────────────

def _load_persisted_embeddings(qa_count: int) -> np.ndarray | None:
    """載入 Step 3 持久化的 embedding"""
    emb_path = config.OUTPUT_DIR / "qa_embeddings.npy"
    if not emb_path.exists():
        return None
    emb = np.load(emb_path)
    if emb.shape[0] != qa_count:
        return None
    return emb


@observe(name="evaluate_retrieval")
def evaluate_retrieval(
    golden_cases: list[dict],
    qa_pairs: list[dict],
    debug: bool = False,
    use_reranking: bool = False,
) -> dict:
    """
    評估 Retrieval 品質。

    對每個 golden case：
    1. 用 query 做 embedding 語意搜尋（+ keyword boost）
    2. 檢查 retrieved Q&A 是否包含 expected_keywords
    3. 檢查 retrieved Q&A 的 category 是否在 expected_categories
    4. 用 LLM 判斷 retrieved Q&A 是否真的相關

    回傳指標：Keyword Hit Rate, Category Hit Rate, LLM Relevance, MRR
    """
    from utils.openai_helper import get_embeddings

    if not qa_pairs or not golden_cases:
        return {"error": "缺少 Q&A 或 golden cases"}

    # 載入或計算 Q&A embeddings
    persisted = _load_persisted_embeddings(len(qa_pairs))
    if persisted is not None:
        qa_embs = persisted
    else:
        texts = [f"{qa['question']} {qa['answer']}" for qa in qa_pairs]
        qa_embs = np.array(get_embeddings(texts))

    qa_norm = qa_embs / (np.linalg.norm(qa_embs, axis=1, keepdims=True) + 1e-8)

    top_k = 5
    debug_top_k = 20  # 診斷時搜尋更廣
    case_results: list[dict] = []

    for case in golden_cases:
        query = case["query"]
        expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
        expected_cats = case.get("expected_categories", [])

        # Embed query
        q_emb = np.array(get_embeddings([query]))
        q_norm = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-8)
        scores = (q_norm @ qa_norm.T).flatten()

        # Keyword boost (bidirectional)
        boost = getattr(config, "KW_BOOST", 0.10)
        max_hits = getattr(config, "KW_BOOST_MAX_HITS", 3)
        partial = getattr(config, "KW_BOOST_PARTIAL", 0.05)
        query_lower = query.lower()
        query_tokens = {t for t in query_lower.split() if len(t) >= 2}
        for ji, qa in enumerate(qa_pairs):
            total_hits = 0.0
            for kw in qa.get("keywords", []):
                kw_lower = kw.lower()
                kw_tokens = {t for t in kw_lower.split() if len(t) >= 2}
                if kw_lower in query_lower:
                    total_hits += 1
                elif any(t in kw_lower for t in query_tokens):
                    total_hits += 1
                elif any(t in query_lower for t in kw_tokens):
                    total_hits += 1
                elif len(kw_lower) >= 2 and kw_lower[:2] in query_lower:
                    total_hits += (partial / boost) if boost else 0
            if total_hits > 0:
                scores[ji] += boost * min(total_hits, max_hits)

        # 搜尋 top-20 for debug / reranking，最終取 top-5
        wide_k = debug_top_k if (debug or use_reranking) else top_k
        wide_indices = np.argsort(scores)[::-1][:wide_k]
        wide_retrieved = [qa_pairs[int(idx)] for idx in wide_indices]

        # LLM Reranking（實驗性）
        if use_reranking and len(wide_retrieved) > top_k:
            wide_retrieved = _llm_rerank_retrieval(query, wide_retrieved, top_k=top_k)

        retrieved = wide_retrieved[:top_k]
        retrieved_scores = [float(scores[int(idx)]) for idx in np.argsort(scores)[::-1][:top_k]]

        # ── Debug：失敗診斷 ──
        if debug:
            all_retrieved_kws_wide: set[str] = set()
            for qa in wide_retrieved:
                all_retrieved_kws_wide.update(kw.lower() for kw in qa.get("keywords", []))
            kw_hits_wide = sum(1 for kw in expected_kws if kw in all_retrieved_kws_wide)

            if kw_hits_wide < len(expected_kws):
                missing_kws = [kw for kw in expected_kws if kw not in all_retrieved_kws_wide]
                # 在完整資料庫中找出含有 expected_kws 的 Q&A 最高排在哪
                full_sorted = np.argsort(scores)[::-1]
                best_correct_rank = None
                best_correct_score = None
                best_correct_q = None
                for rank, idx in enumerate(full_sorted, 1):
                    qa_kws = {kw.lower() for kw in qa_pairs[int(idx)].get("keywords", [])}
                    if qa_kws & set(expected_kws):
                        best_correct_rank = rank
                        best_correct_score = float(scores[int(idx)])
                        best_correct_q = qa_pairs[int(idx)]["question"][:70]
                        break

                logger.debug(f"\n[DEBUG] {query}")
                if best_correct_rank is not None and best_correct_rank <= 20:
                    logger.warning(f"  ⚠️  失敗類型: TypeB（正確答案存在但排在第 {best_correct_rank} 名）")
                    logger.info(f"  排名第 {best_correct_rank}（score={best_correct_score:.4f}）: {best_correct_q}")
                else:
                    logger.error("  ❌ 失敗類型: TypeA（資料庫無覆蓋此 keywords）")
                logger.info(f"  未命中 keywords: {missing_kws}")

        # Keyword Hit Rate: 檢查 retrieved Q&A 的 keywords 是否覆蓋 expected_keywords
        # 使用子字串雙向匹配（"流量" 可命中 "探索流量"；"影片" 可命中 "影片縮圖"）
        all_retrieved_kws: set[str] = set()
        for qa in retrieved:
            all_retrieved_kws.update(kw.lower() for kw in qa.get("keywords", []))

        def _kw_fuzzy_hit(exp_kw: str, retrieved_kws: set) -> bool:
            kw = exp_kw.lower()
            # rkw in kw 方向需要最低長度 2，避免單字誤命中所有含該字的 expected_keyword
            return any(
                kw in rkw or (len(rkw) >= 2 and rkw in kw)
                for rkw in retrieved_kws
            )

        kw_hits: int = sum(1 for kw in expected_kws if _kw_fuzzy_hit(kw, all_retrieved_kws))
        kw_hit_rate = kw_hits / len(expected_kws) if expected_kws else 0

        # Category Hit Rate: 是否有至少一筆 Q&A 的 category 在 expected_categories
        retrieved_cats = {qa.get("category", "") for qa in retrieved}
        cat_hits = len(retrieved_cats & set(expected_cats))
        cat_hit_rate = cat_hits / len(expected_cats) if expected_cats else 0

        # LLM Relevance: 讓 LLM 判斷 top-1 是否真的與 query 相關
        llm_relevant = _llm_judge_retrieval_relevance(query, retrieved[0]) if retrieved else False

        # MRR: 找第一個 LLM 認為相關的位置（簡化版：用 category 判斷）
        first_relevant_rank = 0
        for rank, qa in enumerate(retrieved, 1):
            if qa.get("category", "") in expected_cats:
                first_relevant_rank = rank
                break
        mrr = 1 / first_relevant_rank if first_relevant_rank > 0 else 0

        case_results.append({
            "scenario": case.get("scenario", ""),
            "query": query,
            "top_k_questions": [qa["question"][:60] for qa in retrieved],
            "top_k_scores": retrieved_scores,
            "keyword_hit_rate": round(kw_hit_rate, 2),
            "category_hit_rate": round(cat_hit_rate, 2),
            "llm_top1_relevant": llm_relevant,
            "mrr": round(mrr, 2),
        })

        time.sleep(0.3)

    # 彙整統計
    if not case_results:
        return {"error": "所有 golden case 評估均失敗，無法計算統計", "case_details": []}

    avg_kw_hit = sum(c["keyword_hit_rate"] for c in case_results) / len(case_results)
    avg_cat_hit = sum(c["category_hit_rate"] for c in case_results) / len(case_results)
    avg_mrr = sum(c["mrr"] for c in case_results) / len(case_results)
    llm_precision = sum(1 for c in case_results if c["llm_top1_relevant"]) / len(case_results)

    return {
        "total_cases": len(case_results),
        "avg_keyword_hit_rate": round(avg_kw_hit, 2),
        "avg_category_hit_rate": round(avg_cat_hit, 2),
        "avg_mrr": round(avg_mrr, 2),
        "llm_top1_precision": round(llm_precision, 2),
        "case_details": case_results,
    }


def _llm_rerank_retrieval(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
    """bi-encoder top-20 → gpt-5-nano batch rerank → top-k（實驗性）"""
    if len(candidates) <= top_k:
        return candidates

    client = _client()
    items = []
    for i, qa in enumerate(candidates):
        ans = (qa.get("answer") or "")[:150].replace("\n", " ")
        kws = ", ".join(qa.get("keywords", [])[:4])
        items.append(f"[{i}] Q: {qa['question'][:80]}\n    KW: {kws}\n    A: {ans}")

    try:
        resp = client.chat.completions.create(
            model=config.EVAL_RERANK_MODEL,
            messages=[{"role": "user", "content":
                f"查詢：{query}\n\n候選：\n\n" + "\n\n".join(items) +
                f"\n\n回傳與查詢最相關的 {top_k} 個 index（0-based），相關性遞減。"
            }],
            response_format={"type": "json_schema", "json_schema": {
                "name": "rerank_result", "strict": True,
                "schema": {"type": "object",
                    "properties": {"ranked_indices": {"type": "array", "items": {"type": "integer"}}},
                    "required": ["ranked_indices"], "additionalProperties": False,
                },
            }},
            max_completion_tokens=256,
        )
        content = resp.choices[0].message.content
        if not content:
            logger.warning("⚠️ _llm_rerank_retrieval：LLM 回傳空內容，使用原始排序")
            return candidates[:top_k]
        ranked = json.loads(content).get("ranked_indices", [])
        valid = [i for i in ranked if isinstance(i, int) and 0 <= i < len(candidates)]
        # fallback：補全至 top_k
        seen = set(valid)
        for i in range(len(candidates)):
            if i not in seen:
                valid.append(i)
        return [candidates[i] for i in valid[:top_k]]
    except Exception as e:
        logger.warning(f"⚠️ _llm_rerank_retrieval 失敗（{e}），使用原始排序")
        return candidates[:top_k]


@observe(name="_llm_judge_retrieval_relevance")
def _llm_judge_retrieval_relevance(query: str, qa: dict) -> bool:
    """用 LLM 判斷 retrieved Q&A 是否與 query 真的相關"""
    client = _client()

    user_msg = (
        f"搜尋查詢：{query}\n\n"
        "檢索到的 Q&A：\n"
        f"Q: {qa['question']}\n"
        f"A: {qa['answer'][:500]}\n\n"
        "這個 Q&A 是否與搜尋查詢相關？請回答 relevant 或 not_relevant。"
    )

    try:
        response = client.chat.completions.create(
            model=config.EVAL_JUDGE_MODEL,
            messages=[
                {"role": "system", "content": "你是 SEO 資訊檢索品質評審員。判斷檢索到的 Q&A 是否與搜尋查詢相關。只回答 JSON。"},
                {"role": "user", "content": user_msg},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "retrieval_relevance",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "judgment": {
                                "type": "string",
                                "enum": ["relevant", "not_relevant"],
                            },
                            "reason": {"type": "string"},
                        },
                        "required": ["judgment", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            max_completion_tokens=1024,
        )
        content = response.choices[0].message.content
        if not content:
            return False
        result = json.loads(content)
        judgment = result.get("judgment")
        if judgment is None:
            return False
        return judgment == "relevant"
    except Exception as e:
        logger.warning("_llm_judge_retrieval_relevance 失敗（結果計為 False）：%s", e)
        return False


# ──────────────────────────────────────────────────────
# LLM-as-Judge：Q&A 品質評估
# ──────────────────────────────────────────────────────

@observe(name="evaluate_qa_quality")
def evaluate_qa_quality(
    qa: dict,
    source_text: str = "",
) -> dict:
    """
    用 LLM 評估單筆 Q&A 的品質。
    如果提供 source_text，額外評估 Faithfulness。
    """
    client = _client()

    system_prompt = JUDGE_WITH_SOURCE_PROMPT if source_text else JUDGE_SYSTEM_PROMPT

    user_msg = ""
    if source_text:
        # 截取相關段落（取前 3000 字避免太長）
        user_msg += f"--- 原始會議紀錄（節錄）---\n{source_text[:3000]}\n\n"

    user_msg += (
        "--- 萃取的 Q&A ---\n"
        f"Q: {qa['question']}\n"
        f"A: {qa['answer']}\n"
        f"Keywords: {', '.join(qa.get('keywords', []))}\n"
        f"Confidence: {qa.get('confidence', 'N/A')}\n"
    )

    if qa.get("category"):
        user_msg += f"Category: {qa['category']}\n"

    schema_props: dict[str, Any] = {
        "relevance": {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["score", "reason"],
            "additionalProperties": False,
        },
        "accuracy": {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["score", "reason"],
            "additionalProperties": False,
        },
        "completeness": {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["score", "reason"],
            "additionalProperties": False,
        },
        "granularity": {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["score", "reason"],
            "additionalProperties": False,
        },
        "confidence_calibration": {
            "type": "string",
            "enum": ["合理", "偏高", "偏低"],
        },
        "self_contained": {
            "type": "boolean",
        },
        "actionable": {
            "type": "string",
            "enum": ["是", "部分", "否"],
        },
        "overall_comment": {"type": "string"},
    }
    required = [
        "relevance", "accuracy", "completeness", "granularity",
        "confidence_calibration", "self_contained", "actionable",
        "overall_comment",
    ]

    if source_text:
        schema_props["faithfulness"] = {
            "type": "object",
            "properties": {
                "score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["score", "reason"],
            "additionalProperties": False,
        }
        required.append("faithfulness")

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "evaluate_qa",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": schema_props,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=4096,  # gpt-5 推理模型：reasoning + JSON output 共享 token 預算
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "JSON 解析失敗"}


# ──────────────────────────────────────────────────────
# 分類品質評估
# ──────────────────────────────────────────────────────

def evaluate_classification(qa: dict) -> dict:
    """用 LLM 評估單筆 Q&A 的分類是否正確"""
    client = _client()

    user_msg = (
        f"Q: {qa['question']}\n"
        f"A: {qa['answer']}\n\n"
        "系統標記的分類：\n"
        f"- category: {qa.get('category', 'N/A')}\n"
        f"- difficulty: {qa.get('difficulty', 'N/A')}\n"
        f"- evergreen: {qa.get('evergreen', 'N/A')}\n"
    )

    response = client.chat.completions.create(
        model=config.EVAL_JUDGE_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFY_EVAL_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "classify_eval",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "category_judgment": {
                            "type": "string",
                            "enum": ["correct", "incorrect", "borderline"],
                        },
                        "suggested_category": {"type": "string"},
                        "difficulty_reasonable": {"type": "boolean"},
                        "evergreen_reasonable": {"type": "boolean"},
                        "reason": {"type": "string"},
                    },
                    "required": [
                        "category_judgment", "suggested_category",
                        "difficulty_reasonable", "evergreen_reasonable",
                        "reason",
                    ],
                    "additionalProperties": False,
                },
            },
        },
        max_completion_tokens=2048,
    )

    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "JSON 解析失敗"}


# ──────────────────────────────────────────────────────
# 統計彙整
# ──────────────────────────────────────────────────────

def compute_statistics(eval_results: list[dict]) -> dict:
    """彙整評估結果的統計"""
    dimensions = ["relevance", "accuracy", "completeness", "granularity"]
    stats: dict[str, Any] = {}

    for dim in dimensions:
        scores = [
            r[dim]["score"]
            for r in eval_results
            if dim in r and isinstance(r[dim], dict) and "score" in r[dim]
        ]
        if scores:
            stats[dim] = {
                "mean": round(sum(scores) / len(scores), 2),
                "min": min(scores),
                "max": max(scores),
                "count": len(scores),
                "distribution": {i: scores.count(i) for i in range(1, 6)},
            }

    # Faithfulness（只在 with-source 模式有）
    faith_scores = [
        r["faithfulness"]["score"]
        for r in eval_results
        if "faithfulness" in r and isinstance(r["faithfulness"], dict)
    ]
    if faith_scores:
        stats["faithfulness"] = {
            "mean": round(sum(faith_scores) / len(faith_scores), 2),
            "min": min(faith_scores),
            "max": max(faith_scores),
            "count": len(faith_scores),
        }

    # Confidence 校準
    calibrations = [r.get("confidence_calibration", "") for r in eval_results]
    stats["confidence_calibration"] = {
        "合理": calibrations.count("合理"),
        "偏高": calibrations.count("偏高"),
        "偏低": calibrations.count("偏低"),
    }

    # Self-contained
    self_contained = [r.get("self_contained") for r in eval_results if r.get("self_contained") is not None]
    stats["self_contained_rate"] = (
        round(sum(1 for s in self_contained if s) / len(self_contained), 2)
        if self_contained else 0
    )

    # Actionable
    actionable = [r.get("actionable", "") for r in eval_results]
    stats["actionable"] = {
        "是": actionable.count("是"),
        "部分": actionable.count("部分"),
        "否": actionable.count("否"),
    }

    return stats


def compute_classify_statistics(classify_results: list[dict]) -> dict:
    """彙整分類評估的統計"""
    judgments = [r.get("category_judgment", "") for r in classify_results]
    diff_ok = sum(1 for r in classify_results if r.get("difficulty_reasonable"))
    ever_ok = sum(1 for r in classify_results if r.get("evergreen_reasonable"))
    total = len(classify_results)

    return {
        "category_accuracy": {
            "correct": judgments.count("correct"),
            "incorrect": judgments.count("incorrect"),
            "borderline": judgments.count("borderline"),
            "accuracy_rate": round(
                (judgments.count("correct") + judgments.count("borderline") * 0.5)
                / total, 2
            ) if total else 0,
        },
        "difficulty_accuracy": round(diff_ok / total, 2) if total else 0,
        "evergreen_accuracy": round(ever_ok / total, 2) if total else 0,
        "total_evaluated": total,
    }


# ──────────────────────────────────────────────────────
# 報告產生
# ──────────────────────────────────────────────────────

def generate_eval_report_md(
    stats: dict,
    classify_stats: dict | None,
    sample_size: int,
    with_source: bool,
    low_quality_items: list[dict],
    retrieval_stats: dict | None = None,
) -> str:
    """產生人類可讀的 Markdown 評估報告"""
    lines = [
        "# Q&A 品質評估報告\n",
        "**[Meta] 評估方式：LLM-as-Judge（gpt-5-mini）| 檢索引擎：Embedding + 關鍵字強化**\n",
        f"- 評估樣本數：{sample_size}",
        f"- 帶原始來源驗證：{'是' if with_source else '否'}",
        f"- 評估日期：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 總體評分：{sum(stats.get(d, {}).get('mean', 0) for d in ['relevance', 'accuracy', 'completeness', 'granularity']) / 4:.2f}/5",
        "",
    ]

    # 四維度分數
    lines.append("## 品質評分摘要\n")
    lines.append("| 維度 | 平均分 | 最低 | 最高 | 評估數 |")
    lines.append("|------|--------|------|------|--------|")
    for dim in ["relevance", "accuracy", "completeness", "granularity", "faithfulness"]:
        if dim in stats:
            s = stats[dim]
            lines.append(f"| {dim} | {s['mean']} | {s['min']} | {s['max']} | {s['count']} |")

    lines.append("")

    # 分數分佈
    for dim in ["relevance", "accuracy", "completeness", "granularity"]:
        if dim in stats and "distribution" in stats[dim]:
            dist = stats[dim]["distribution"]
            lines.append(f"### {dim} 分佈")
            lines.append(f"1⭐: {dist.get(1,0)} | 2⭐: {dist.get(2,0)} | 3⭐: {dist.get(3,0)} | 4⭐: {dist.get(4,0)} | 5⭐: {dist.get(5,0)}")
            lines.append("")

    # Confidence 校準
    cal = stats.get("confidence_calibration", {})
    lines.append("## Confidence 校準\n")
    lines.append(f"- 合理：{cal.get('合理', 0)}")
    lines.append(f"- 偏高：{cal.get('偏高', 0)}")
    lines.append(f"- 偏低：{cal.get('偏低', 0)}")
    lines.append("")

    # Self-contained & Actionable
    lines.append("## 其他品質指標\n")
    lines.append(f"- Self-contained（可獨立理解）比率：{stats.get('self_contained_rate', 0):.0%}")
    act = stats.get("actionable", {})
    lines.append(f"- Actionable（可執行建議）：是 {act.get('是', 0)} / 部分 {act.get('部分', 0)} / 否 {act.get('否', 0)}")
    lines.append("")

    # 分類品質
    if classify_stats:
        lines.append("## 分類品質\n")
        ca = classify_stats["category_accuracy"]
        lines.append(f"- Category 正確率：{ca['accuracy_rate']:.0%}（correct: {ca['correct']} / incorrect: {ca['incorrect']} / borderline: {ca['borderline']}）")
        lines.append(f"- Difficulty 合理率：{classify_stats['difficulty_accuracy']:.0%}")
        lines.append(f"- Evergreen 合理率：{classify_stats['evergreen_accuracy']:.0%}")
        lines.append("")

    # 低品質項目
    if low_quality_items:
        lines.append("## 需要關注的低品質 Q&A\n")
        for item in low_quality_items[:10]:
            q = item["question"][:60]
            avg = item["avg_score"]
            lines.append(f"- **[ID {item.get('id', '?')}]** (avg: {avg:.1f}) {q}...")
            lines.append(f"  - {item.get('comment', '')}")
        lines.append("")

    # Retrieval 品質
    if retrieval_stats and "error" not in retrieval_stats:
        lines.append("## Retrieval 品質（語意搜尋）\n")
        lines.append(f"- 測試場景數：{retrieval_stats['total_cases']}")
        lines.append(f"- 平均關鍵字命中率：{retrieval_stats['avg_keyword_hit_rate']:.0%}")
        lines.append(f"- 平均分類命中率：{retrieval_stats['avg_category_hit_rate']:.0%}")
        lines.append(f"- 平均 MRR：{retrieval_stats['avg_mrr']:.2f}")
        lines.append(f"- LLM Top-1 Precision：{retrieval_stats['llm_top1_precision']:.0%}")
        lines.append("")

        # 各場景詳情
        lines.append("### 各場景詳情\n")
        lines.append("| 場景 | KW命中 | 分類命中 | MRR | Top-1相關 |")
        lines.append("|------|--------|----------|-----|-----------|")
        for c in retrieval_stats.get("case_details", []):
            llm_icon = "✅" if c["llm_top1_relevant"] else "❌"
            lines.append(
                f"| {c['scenario']} | {c['keyword_hit_rate']:.0%} | "
                f"{c['category_hit_rate']:.0%} | {c['mrr']:.2f} | {llm_icon} |"
            )
        lines.append("")

    # 建議
    lines.append("## 改善建議\n")

    all_dims = ["relevance", "accuracy", "completeness", "granularity"]
    weak_dims = [d for d in all_dims if d in stats and stats[d]["mean"] < 3.5]
    if weak_dims:
        lines.append(f"⚠️ 以下維度平均分低於 3.5，建議優先改善 prompt：**{', '.join(weak_dims)}**\n")

    if cal.get("偏高", 0) > cal.get("合理", 0):
        lines.append("⚠️ Confidence 普遍偏高，建議在 prompt 中加入更嚴格的評分標準\n")

    if stats.get("self_contained_rate", 1) < 0.8:
        lines.append("⚠️ 自包含率低於 80%，部分 Q 需要看原文才能理解，建議改善萃取 prompt 要求 Q 必須自包含\n")

    if retrieval_stats and retrieval_stats.get("avg_mrr", 1) < 0.5:
        lines.append("⚠️ Retrieval MRR 低於 0.5，語意搜尋品質需要改善（考慮 reranking 或調整 embedding 策略）\n")

    if retrieval_stats and retrieval_stats.get("llm_top1_precision", 1) < 0.7:
        lines.append("⚠️ Top-1 Precision 低於 70%，排序品質不佳，建議加入 cross-encoder reranking\n")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────
# Laminar metadata 記錄
# ──────────────────────────────────────────────────────

def _record_laminar_eval_metadata(stats: dict, sample_size: int, retrieval_stats: dict | None = None) -> None:
    """記錄評估 metadata 到 Laminar"""
    try:
        from lmnr import current_span
        span = current_span()
        if span:
            metadata = {
                "step": "evaluate",
                "sample_size": sample_size,
                "judge_model": getattr(config, "EVAL_JUDGE_MODEL", "gpt-5-mini"),
            }
            
            # 四維度評分
            for dim in ["relevance", "accuracy", "completeness", "granularity"]:
                if dim in stats:
                    metadata[f"{dim}_mean"] = stats[dim].get("mean", 0)
                    metadata[f"{dim}_count"] = stats[dim].get("count", 0)
            
            # Confidence 校準
            if "confidence_calibration" in stats:
                cal = stats["confidence_calibration"]
                metadata["calibration_appropriate"] = cal.get("合理", 0)
                metadata["calibration_overconfident"] = cal.get("偏高", 0)
                metadata["calibration_underconfident"] = cal.get("偏低", 0)
            
            # Retrieval 指標
            if retrieval_stats and "error" not in retrieval_stats:
                metadata["retrieval_test_cases"] = retrieval_stats.get("total_cases", 0)
                metadata["keyword_hit_rate"] = retrieval_stats.get("avg_keyword_hit_rate", 0)
                metadata["category_hit_rate"] = retrieval_stats.get("avg_category_hit_rate", 0)
                metadata["mean_reciprocal_rank"] = retrieval_stats.get("avg_mrr", 0)
                metadata["llm_precision"] = retrieval_stats.get("llm_top1_precision", 0)
            
            span.set_metadata(metadata)
    except Exception:
        pass  # Laminar not available or span not in context


# ──────────────────────────────────────────────────────
# 萃取品質評估（Phase 2）
# ──────────────────────────────────────────────────────

def evaluate_extraction(
    golden_cases: list[dict],
    per_meeting_dir: Path | None = None,
) -> dict:
    """
    驗證每場會議萃取的 Q&A 是否符合 golden_extraction.json 的期望。

    評估維度：
      - count_accuracy: Q&A 數量是否在 [min_qa_count, max_qa_count] 範圍
      - keyword_coverage_rate: must_extract_keywords 在萃取結果中的覆蓋率
      - hallucination_rate: should_not_extract 關鍵詞不應出現在萃取結果中
    """
    if per_meeting_dir is None:
        per_meeting_dir = config.QA_PER_MEETING_DIR

    case_details: list[dict] = []

    for case in golden_cases:
        qa_file = per_meeting_dir / case["per_meeting_qa_file"]
        if not qa_file.exists():
            case_details.append({
                "source_file": case["source_file"],
                "status": "file_not_found",
                "qa_file": str(qa_file),
            })
            continue

        try:
            data = json.loads(qa_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            case_details.append({
                "source_file": case["source_file"],
                "status": f"read_error: {e}",
            })
            continue

        qa_list: list[dict] = data if isinstance(data, list) else data.get("qa_pairs", [])
        actual_count = len(qa_list)
        min_count = case.get("min_qa_count", 0)
        max_count = case.get("max_qa_count", 9999)
        count_ok = min_count <= actual_count <= max_count

        # 把所有 Q&A 文字合併方便搜尋
        all_text = " ".join(
            f"{qa.get('question', '')} {qa.get('answer', '')}"
            for qa in qa_list
        ).lower()

        must_kws = case.get("must_extract_keywords", [])
        kw_hits = sum(1 for kw in must_kws if kw.lower() in all_text)
        kw_coverage = kw_hits / len(must_kws) if must_kws else 1.0

        should_not_kws = case.get("should_not_extract", [])
        hallu_hits = sum(1 for kw in should_not_kws if kw.lower() in all_text)
        hallu_rate = hallu_hits / len(should_not_kws) if should_not_kws else 0.0

        case_details.append({
            "source_file": case["source_file"],
            "description": case.get("description", ""),
            "actual_count": actual_count,
            "count_ok": count_ok,
            "count_range": [min_count, max_count],
            "keyword_coverage": round(kw_coverage, 2),
            "must_keywords_hit": kw_hits,
            "must_keywords_total": len(must_kws),
            "hallucination_rate": round(hallu_rate, 2),
            "should_not_extract_violated": hallu_hits,
        })

    if not case_details:
        return {"error": "沒有可評估的 extraction golden case"}

    valid = [c for c in case_details if "status" not in c]
    if not valid:
        return {"error": "所有 golden case 都找不到對應檔案", "case_details": case_details}

    count_accuracy = sum(1 for c in valid if c.get("count_ok", False)) / len(valid)
    avg_kw_coverage = sum(c.get("keyword_coverage", 0) for c in valid) / len(valid)
    avg_hallu_rate = sum(c.get("hallucination_rate", 0) for c in valid) / len(valid)

    return {
        "total_cases": len(golden_cases),
        "evaluated": len(valid),
        "count_accuracy": round(count_accuracy, 2),
        "avg_keyword_coverage_rate": round(avg_kw_coverage, 2),
        "avg_hallucination_rate": round(avg_hallu_rate, 2),
        "case_details": case_details,
    }


# ──────────────────────────────────────────────────────
# 去重品質評估（Phase 2）
# ──────────────────────────────────────────────────────

def _compute_pair_similarities(golden_pairs: list[dict]) -> np.ndarray:
    """
    對 golden_dedup.json 中每對 (qa_a, qa_b) 計算 cosine similarity。
    回傳 shape=(N,) 的 similarity 陣列，對應各 pair 的分數。
    """
    from utils.openai_helper import get_embeddings

    texts_a = [p["qa_a"]["question"] for p in golden_pairs]
    texts_b = [p["qa_b"]["question"] for p in golden_pairs]
    all_embs = np.array(get_embeddings(texts_a + texts_b), dtype=np.float32)

    n = len(golden_pairs)
    embs_a = all_embs[:n]
    embs_b = all_embs[n:]

    norm_a = embs_a / (np.linalg.norm(embs_a, axis=1, keepdims=True) + 1e-8)
    norm_b = embs_b / (np.linalg.norm(embs_b, axis=1, keepdims=True) + 1e-8)

    return (norm_a * norm_b).sum(axis=1)  # element-wise dot product -> cosine


def _dedup_metrics_at_threshold(
    similarities: np.ndarray,
    labels: list[bool],
    threshold: float,
) -> dict:
    """給定 pre-computed similarities 和 threshold，計算 precision/recall/F1。"""
    tp = fp = fn = tn = 0
    for sim, should_merge in zip(similarities, labels):
        predicted_merge = sim >= threshold
        if predicted_merge and should_merge:
            tp += 1
        elif predicted_merge and not should_merge:
            fp += 1
        elif not predicted_merge and should_merge:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "threshold": round(threshold, 2),
        "precision": round(precision, 2),
        "recall": round(recall, 2),
        "f1": round(f1, 2),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


@observe(name="evaluate_dedup")
def evaluate_dedup(
    golden_pairs: list[dict],
    threshold: float | None = None,
    precomputed_similarities: np.ndarray | None = None,
) -> dict:
    """
    評估去重準確度：對 golden_dedup.json 的每對 Q&A 計算 embedding cosine similarity，
    與標籤對比計算 precision/recall/F1。

    Parameters
    ----------
    threshold:
        閾值（None → 使用 config.SIMILARITY_THRESHOLD）
    precomputed_similarities:
        若已有預計算相似度，直接傳入避免重複呼叫 embedding API
    """
    if not golden_pairs:
        return {"error": "缺少 golden pair 資料"}

    threshold = threshold if threshold is not None else float(config.SIMILARITY_THRESHOLD)
    labels = [bool(p.get("should_merge", False)) for p in golden_pairs]

    if precomputed_similarities is not None:
        sims = precomputed_similarities
    else:
        logger.info(f"   計算 {len(golden_pairs)} 對 Q&A 的 embedding similarity...")
        sims = _compute_pair_similarities(golden_pairs)

    metrics = _dedup_metrics_at_threshold(sims, labels, threshold)
    metrics["total_pairs"] = len(golden_pairs)
    metrics["positive_pairs"] = sum(labels)
    metrics["negative_pairs"] = len(labels) - sum(labels)
    metrics["current_threshold"] = float(config.SIMILARITY_THRESHOLD)

    return metrics


@observe(name="evaluate_dedup_threshold_sweep")
def evaluate_dedup_threshold_sweep(golden_pairs: list[dict]) -> dict:
    """
    掃描閾值 0.80–0.95（步長 0.01），找出 F1 最佳的閾值。
    回傳 sweep 結果和建議的最佳閾值。
    """
    if not golden_pairs:
        return {"error": "缺少 golden pair 資料"}

    logger.info(f"   計算 {len(golden_pairs)} 對 Q&A 的 embedding similarity（一次性）...")
    sims = _compute_pair_similarities(golden_pairs)
    labels = [bool(p.get("should_merge", False)) for p in golden_pairs]

    sweep = []
    for t_int in range(80, 96):  # 0.80 ~ 0.95
        t = t_int / 100.0
        metrics = _dedup_metrics_at_threshold(sims, labels, t)
        sweep.append(metrics)

    best = max(sweep, key=lambda m: m["f1"])
    current_metrics = _dedup_metrics_at_threshold(sims, labels, float(config.SIMILARITY_THRESHOLD))

    return {
        "current_threshold": float(config.SIMILARITY_THRESHOLD),
        "current_f1": current_metrics["f1"],
        "optimal_threshold": best["threshold"],
        "optimal_f1": best["f1"],
        "recommendation": (
            f"建議將 SIMILARITY_THRESHOLD 從 {config.SIMILARITY_THRESHOLD} 改為 {best['threshold']}"
            if best["threshold"] != float(config.SIMILARITY_THRESHOLD)
            else f"目前閾值 {config.SIMILARITY_THRESHOLD} 已是最佳"
        ),
        "sweep": sweep,
    }


# ──────────────────────────────────────────────────────
# 週報品質評估（Phase 2）
# ──────────────────────────────────────────────────────

def _load_report_content(report_path: Path) -> str:
    """載入報告 Markdown 內容，不存在回傳空字串。"""
    if not report_path.exists():
        return ""
    return report_path.read_text(encoding="utf-8")


@observe(name="evaluate_report_quality")
def evaluate_report_quality(
    golden_cases: list[dict],
    reports_dir: Path | None = None,
) -> dict:
    """
    評估週報品質：
      1. required_topics 覆蓋率（快速字串匹配）
      2. LLM-as-Judge 評估 grounding（有引用具體 Q&A 知識）、
         actionability（有可執行建議）和 relevance（不偏題）
    """
    client = _client()
    if reports_dir is None:
        reports_dir = config.OUTPUT_DIR

    case_details: list[dict] = []

    for case in golden_cases:
        # 嘗試找到最新報告（用 glob 匹配 report_*.md）
        report_files = sorted(reports_dir.glob("report_*.md"))
        if not report_files:
            # fallback：用 case["id"] 嘗試精確匹配
            candidate = reports_dir / f"{case['id']}.md"
            report_files = [candidate] if candidate.exists() else []

        if not report_files:
            case_details.append({
                "id": case["id"],
                "status": "no_report_found",
                "description": case.get("description", ""),
            })
            continue

        # 取最新報告
        report_path = report_files[-1]
        content = _load_report_content(report_path)
        if not content:
            case_details.append({
                "id": case["id"],
                "status": "empty_report",
                "report_path": str(report_path),
            })
            continue

        # 快速 topic 覆蓋率檢查
        content_lower = content.lower()
        required_topics = case.get("required_topics", [])
        topic_hits = sum(1 for t in required_topics if t.lower() in content_lower)
        topic_coverage = topic_hits / len(required_topics) if required_topics else 1.0

        # source_qa_keywords 關鍵字接地性
        source_kws = case.get("source_qa_keywords", [])
        kw_hits = sum(1 for kw in source_kws if kw.lower() in content_lower)
        kw_grounding = kw_hits / len(source_kws) if source_kws else 1.0

        # LLM 評估報告品質
        llm_scores: dict = {}
        try:
            user_msg = (
                f"報告用途：{case.get('description', '')}\n\n"
                f"報告內容（節錄前 3000 字）：\n{content[:3000]}\n\n"
                "請評估這份 SEO 週報的品質，回傳 JSON。"
            )
            resp = client.chat.completions.create(
                model=config.EVAL_JUDGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是 SEO 報告品質評審員。評估報告的三個維度（1-5分）："
                            "grounding（有引用具體 SEO 知識而非泛泛而談）、"
                            "actionability（有具體可執行的建議）、"
                            "relevance（內容與 SEO 主題相關，未偏題）。"
                            "只回答 JSON。"
                        ),
                    },
                    {"role": "user", "content": user_msg},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "report_quality",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "grounding": {"type": "integer"},
                                "actionability": {"type": "integer"},
                                "relevance": {"type": "integer"},
                                "comment": {"type": "string"},
                            },
                            "required": ["grounding", "actionability", "relevance", "comment"],
                            "additionalProperties": False,
                        },
                    },
                },
                max_completion_tokens=512,
            )
            content_str = resp.choices[0].message.content
            if content_str:
                llm_scores = json.loads(content_str)
        except Exception as e:
            llm_scores = {"error": str(e)}

        case_details.append({
            "id": case["id"],
            "description": case.get("description", ""),
            "report_path": str(report_path),
            "topic_coverage": round(topic_coverage, 2),
            "kw_grounding": round(kw_grounding, 2),
            "llm_grounding": llm_scores.get("grounding"),
            "llm_actionability": llm_scores.get("actionability"),
            "llm_relevance": llm_scores.get("relevance"),
            "llm_comment": llm_scores.get("comment", ""),
        })

        time.sleep(0.3)

    valid = [c for c in case_details if "status" not in c and "llm_grounding" in c]
    if not valid:
        return {
            "error": "無有效報告可評估（請先執行 Step 4 生成報告）",
            "case_details": case_details,
        }

    avg_topic_cov = sum(c["topic_coverage"] for c in valid) / len(valid)
    avg_kw_ground = sum(c["kw_grounding"] for c in valid) / len(valid)
    llm_grounds = [c["llm_grounding"] for c in valid if isinstance(c.get("llm_grounding"), int)]
    llm_actions = [c["llm_actionability"] for c in valid if isinstance(c.get("llm_actionability"), int)]
    llm_rels = [c["llm_relevance"] for c in valid if isinstance(c.get("llm_relevance"), int)]

    return {
        "total_cases": len(golden_cases),
        "evaluated": len(valid),
        "avg_topic_coverage": round(avg_topic_cov, 2),
        "avg_kw_grounding": round(avg_kw_ground, 2),
        "avg_llm_grounding": round(sum(llm_grounds) / len(llm_grounds), 2) if llm_grounds else None,
        "avg_llm_actionability": round(sum(llm_actions) / len(llm_actions), 2) if llm_actions else None,
        "avg_llm_relevance": round(sum(llm_rels) / len(llm_rels), 2) if llm_rels else None,
        "case_details": case_details,
    }


# ──────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────

def _save_versioned_eval(
    args: argparse.Namespace,
    stats: dict | None,
    classify_stats: dict | None,
    retrieval_stats: dict | None,
    sample_size: int,
) -> None:
    """
    版本化 eval 結果儲存到 output/evals/{date}_{provider}_{extraction_engine}.json
    並可選擇性地與基準線比較 / 更新基準線。
    """
    evals_dir = config.OUTPUT_DIR / "evals"
    evals_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = config.OUTPUT_DIR / "eval_baseline.json"

    provider = getattr(args, "provider", "openai")
    extraction_engine = getattr(args, "extraction_engine", "openai")
    model = getattr(args, "model", "") or config.OPENAI_MODEL
    today = datetime.now().strftime("%Y%m%d")
    run_id = f"{today}_{provider}_{extraction_engine}"

    dims = ["relevance", "accuracy", "completeness", "granularity"]
    generation_scores: dict[str, float] = {}
    if stats:
        for dim in dims:
            if dim in stats:
                generation_scores[dim] = round(stats[dim]["mean"], 4)

    retrieval_scores: dict[str, float] = {}
    if retrieval_stats and "error" not in retrieval_stats:
        retrieval_scores = {
            "kw_hit_rate":       round(retrieval_stats.get("avg_keyword_hit_rate", 0), 4),
            "mrr":               round(retrieval_stats.get("avg_mrr", 0), 4),
            "llm_top1_precision": round(retrieval_stats.get("llm_top1_precision", 0), 4),
        }

    classification_scores: dict[str, float] = {}
    if classify_stats:
        ca = classify_stats.get("category_accuracy", {})
        classification_scores = {
            "category_accuracy":  round(ca.get("accuracy_rate", 0), 4),
            "difficulty_accuracy": round(classify_stats.get("difficulty_accuracy", 0), 4),
            "evergreen_accuracy":  round(classify_stats.get("evergreen_accuracy", 0), 4),
        }

    versioned: dict = {
        "version": run_id,
        "date": today,
        "sample_size": sample_size,
        "provider": provider,
        "extraction_engine": extraction_engine,
        "model": model,
        "generation": generation_scores,
        "retrieval": retrieval_scores,
        "classification": classification_scores,
    }

    versioned_path = evals_dir / f"{run_id}.json"
    versioned_path.write_text(json.dumps(versioned, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"   版本化 eval 儲存至: {versioned_path}")

    # ── 基準線比較 ──────────────────────────────────────────
    if not baseline_path.exists():
        return

    try:
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    bs = baseline.get("generation", baseline.get("scores", {}))
    if not bs or not generation_scores:
        return

    new_avg = sum(generation_scores.get(d, 0) for d in dims) / len(dims)
    base_avg = sum(bs.get(d, 0) for d in dims) / len(dims)
    delta = new_avg - base_avg
    arrow = "↑" if delta > 0.02 else ("↓" if delta < -0.02 else "→")
    logger.info(f"\n   基準線比較（avg）：新分數 {new_avg:.2f} vs 基準 {base_avg:.2f}  Δ{delta:+.2f} {arrow}")
    for dim in dims:
        nv = generation_scores.get(dim, 0)
        bv = bs.get(dim, 0)
        logger.info(f"     {dim:<15s}: {nv:.2f} vs {bv:.2f}  Δ{nv-bv:+.2f}")

    if getattr(args, "update_baseline", False):
        threshold = 0.05
        if delta >= threshold:
            versioned["note"] = "自動更新基準線"
            baseline_path.write_text(json.dumps(versioned, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"\n   基準線已更新（Δ{delta:+.2f} >= {threshold}）")
        else:
            logger.info(f"\n   基準線未更新（Δ{delta:+.2f} < {threshold}），保留原有基準線")


def main(args: argparse.Namespace) -> None:
    init_laminar()

    # ── Preflight dependency check ───────────────────────────
    deps = [
        StepDependency(
            path=config.OUTPUT_DIR / "qa_final.json",
            required=False,
            max_age_days=7,
            hint="建議先執行 Step 3（或用 qa_all_raw.json fallback）",
        ),
    ]
    preflight_check(
        deps=deps,
        env_keys=["OPENAI_API_KEY"],
        step_name="Step 5: 品質評估",
        check_only=getattr(args, "check", False),
    )
    if getattr(args, "check", False):
        return

    logger.info("=" * 60)
    logger.info("📊 步驟 5：Q&A 品質評估（Evaluation）")
    logger.info(f"   Judge 模型: {config.OPENAI_MODEL}")
    logger.info(f"   抽樣數量: {args.sample}")
    logger.info(f"   帶原始來源: {'是' if args.with_source else '否'}")
    logger.info("=" * 60)

    # 載入資料
    qa_pairs = load_qa_data()
    if not qa_pairs:
        logger.error("❌ 找不到 Q&A 資料，請先執行步驟 2-3")
        sys.exit(1)

    logger.info(f"\n📥 載入 {len(qa_pairs)} 個 Q&A")

    # 抽樣
    sample_size = min(args.sample, len(qa_pairs))
    if args.seed is not None:
        random.seed(args.seed)
    sampled = random.sample(qa_pairs, sample_size)
    logger.info(f"   抽樣 {sample_size} 個（seed: {args.seed}）")

    # ── Q&A 品質評估 ──
    eval_results: list[dict] = []
    if not args.classify_only:
        logger.info(f"\n🔍 評估 Q&A 品質（{sample_size} 筆）...")
        for i, qa in enumerate(sampled, 1):
            source_text = ""
            if args.with_source and qa.get("source_file"):
                source_text = load_source_markdown(qa["source_file"])

            logger.info(f"  [{i}/{sample_size}] {qa['question'][:50]}...")

            try:
                result = evaluate_qa_quality(qa, source_text)
                result["_qa_id"] = qa.get("stable_id", str(qa.get("id", i)))
                result["_question"] = qa["question"]
                result["_confidence"] = qa.get("confidence", None)
                eval_results.append(result)
            except Exception as e:
                logger.warning(f"    ⚠️  評估失敗: {e}")
                eval_results.append({"error": str(e), "_qa_id": qa.get("stable_id", str(qa.get("id", i)))})

            time.sleep(0.5)

    # ── 分類品質評估 ──
    classify_results: list[dict] = []
    classify_stats = None
    if not args.skip_classify_eval:
        classified = [qa for qa in sampled if qa.get("category")]
        if classified:
            eval_count = min(len(classified), args.sample)
            logger.info(f"\n🏷️  評估分類品質（{eval_count} 筆）...")
            for i, qa in enumerate(classified[:eval_count], 1):
                logger.info(f"  [{i}/{eval_count}] {qa.get('category', '?')} ← {qa['question'][:40]}...")
                try:
                    result = evaluate_classification(qa)
                    if "category_judgment" not in result:
                        logger.warning(f"    ⚠️  空回應（推理模型 content=None），跳過 QA {qa.get('id', i)}")
                        continue
                    result["_qa_id"] = qa.get("stable_id", str(qa.get("id", i)))
                    result["_original_category"] = qa.get("category", "")
                    classify_results.append(result)
                except Exception as e:
                    logger.warning(f"    ⚠️  評估失敗: {e}")

                time.sleep(0.3)

            classify_stats = compute_classify_statistics(classify_results)

    # ── Retrieval 品質評估 ──
    retrieval_stats = None
    if args.eval_retrieval:
        golden_ret = load_golden_retrieval(args.retrieval_golden)
        if golden_ret:
            logger.info(f"\n🔎 評估 Retrieval 品質（{len(golden_ret)} 個場景）...")
            retrieval_stats = evaluate_retrieval(
                golden_ret, qa_pairs,
                debug=getattr(args, "debug_retrieval", False),
                use_reranking=getattr(args, "eval_reranking", False),
            )
        else:
            logger.warning("   ⚠️  找不到 retrieval golden set，跳過")

    # ── 萃取品質評估 ──
    extraction_stats = None
    if getattr(args, "eval_extraction", False):
        golden_ext_path = getattr(args, "extraction_golden", "") or "eval/golden_extraction.json"
        ext_path = Path(golden_ext_path)
        if not ext_path.is_absolute():
            ext_path = config.ROOT_DIR / ext_path
        if ext_path.exists():
            golden_ext = json.loads(ext_path.read_text(encoding="utf-8"))
            logger.info(f"\n📝 評估萃取品質（{len(golden_ext)} 個場景）...")
            extraction_stats = evaluate_extraction(golden_ext)
        else:
            logger.warning(f"   ⚠️  找不到 extraction golden set（{ext_path}），跳過")

    # ── 去重品質評估 ──
    dedup_stats = None
    dedup_sweep_stats = None
    if getattr(args, "eval_dedup", False) or getattr(args, "dedup_threshold_sweep", False):
        golden_dedup_path = getattr(args, "dedup_golden", "") or "eval/golden_dedup.json"
        dedup_path = Path(golden_dedup_path)
        if not dedup_path.is_absolute():
            dedup_path = config.ROOT_DIR / dedup_path
        if dedup_path.exists():
            golden_dedup = json.loads(dedup_path.read_text(encoding="utf-8"))
            if getattr(args, "dedup_threshold_sweep", False):
                logger.info(f"\n🔬 掃描去重閾值（{len(golden_dedup)} 對 × 16 個閾值）...")
                dedup_sweep_stats = evaluate_dedup_threshold_sweep(golden_dedup)
                logger.info(f"   {dedup_sweep_stats.get('recommendation', '')}")
                # 順便在目前閾值下計算精確指標
                dedup_stats = evaluate_dedup(golden_dedup)
            elif getattr(args, "eval_dedup", False):
                logger.info(f"\n⚖️  評估去重品質（{len(golden_dedup)} 對，閾值={config.SIMILARITY_THRESHOLD}）...")
                dedup_stats = evaluate_dedup(golden_dedup)
        else:
            logger.warning(f"   ⚠️  找不到 dedup golden set（{dedup_path}），跳過")

    # ── 週報品質評估 ──
    report_eval_stats = None
    if getattr(args, "eval_report", False):
        golden_rep_path = getattr(args, "report_golden", "") or "eval/golden_report.json"
        rep_path = Path(golden_rep_path)
        if not rep_path.is_absolute():
            rep_path = config.ROOT_DIR / rep_path
        if rep_path.exists():
            golden_rep = json.loads(rep_path.read_text(encoding="utf-8"))
            logger.info(f"\n📰 評估週報品質（{len(golden_rep)} 個場景）...")
            report_eval_stats = evaluate_report_quality(golden_rep)
        else:
            logger.warning(f"   ⚠️  找不到 report golden set（{rep_path}），跳過")

    # ── 統計彙整 ──
    valid_evals = [r for r in eval_results if "error" not in r]
    stats = compute_statistics(valid_evals) if valid_evals else {}

    # 找出低品質項目（平均分 < 3.0）
    low_quality: list[dict] = []
    for r in valid_evals:
        scores = [
            r[d]["score"]
            for d in ["relevance", "accuracy", "completeness", "granularity"]
            if d in r and isinstance(r[d], dict) and "score" in r[d]
        ]
        if scores:
            avg = sum(scores) / len(scores)
            if avg < 3.0:
                low_quality.append({
                    "id": r.get("_qa_id"),
                    "question": r.get("_question", ""),
                    "avg_score": avg,
                    "comment": r.get("overall_comment", ""),
                })

    # ── 輸出報告 ──
    report = {
        "sample_size": sample_size,
        "with_source": args.with_source,
        "quality_stats": stats,
        "classify_stats": classify_stats,
        "retrieval_stats": retrieval_stats,
        "extraction_stats": extraction_stats,
        "dedup_stats": dedup_stats,
        "dedup_sweep_stats": dedup_sweep_stats,
        "report_eval_stats": report_eval_stats,
        "low_quality_items": low_quality,
        "eval_details": eval_results,
        "classify_details": classify_results,
    }

    # JSON
    json_path = config.OUTPUT_DIR / "eval_report.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 歷史紀錄：追加到 eval_history.jsonl（不含詳細 eval_details，節省大小）
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    history_entry = {
        "timestamp": ts,
        "sample_size": report["sample_size"],
        "quality_stats": report["quality_stats"],
        "classify_stats": report["classify_stats"],
        "retrieval_stats": report["retrieval_stats"],
        "extraction_stats": report["extraction_stats"],
        "dedup_stats": report["dedup_stats"],
        "dedup_sweep_stats": {
            k: v for k, v in (report["dedup_sweep_stats"] or {}).items()
            if k != "sweep"  # 不存 sweep 陣列，節省大小
        } if report["dedup_sweep_stats"] else None,
        "report_eval_stats": report["report_eval_stats"],
    }
    history_path = config.OUTPUT_DIR / "eval_history.jsonl"
    with open(history_path, "a", encoding="utf-8") as _hf:
        _hf.write(json.dumps(history_entry, ensure_ascii=False) + "\n")

    # 快照：複製完整報告到 eval_reports/ 子目錄
    snapshot_dir = config.OUTPUT_DIR / "eval_reports"
    snapshot_dir.mkdir(exist_ok=True)
    snap_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(json_path, snapshot_dir / f"eval_{snap_ts}.json")

    # Markdown
    md_report = generate_eval_report_md(
        stats, classify_stats, sample_size, args.with_source, low_quality,
        retrieval_stats=retrieval_stats,
    )
    md_path = config.OUTPUT_DIR / "eval_report.md"
    md_path.write_text(md_report, encoding="utf-8")

    # 記錄 Laminar 元數據
    _record_laminar_eval_metadata(stats, sample_size, retrieval_stats=retrieval_stats)

    # 印出摘要
    logger.info("\n" + "=" * 60)
    logger.info("📊 評估結果摘要")
    logger.info("=" * 60)

    if stats:
        for dim in ["relevance", "accuracy", "completeness", "granularity"]:
            if dim in stats:
                logger.info(f"   {dim:15s}: {stats[dim]['mean']:.2f} / 5.0")

    if classify_stats:
        ca = classify_stats["category_accuracy"]
        logger.info(f"\n   分類正確率: {ca['accuracy_rate']:.0%}")
        logger.info(f"   Difficulty 合理率: {classify_stats['difficulty_accuracy']:.0%}")
        logger.info(f"   Evergreen 合理率: {classify_stats['evergreen_accuracy']:.0%}")

    if retrieval_stats and "error" not in retrieval_stats:
        logger.info("\n   Retrieval 品質：")
        logger.info(f"   KW 命中率: {retrieval_stats['avg_keyword_hit_rate']:.0%}")
        logger.info(f"   分類命中率: {retrieval_stats['avg_category_hit_rate']:.0%}")
        logger.info(f"   MRR: {retrieval_stats['avg_mrr']:.2f}")
        logger.info(f"   Top-1 Precision: {retrieval_stats['llm_top1_precision']:.0%}")

    if extraction_stats and "error" not in extraction_stats:
        logger.info("\n   萃取品質：")
        logger.info(f"   Count Accuracy: {extraction_stats['count_accuracy']:.0%}")
        logger.info(f"   Keyword Coverage: {extraction_stats['avg_keyword_coverage_rate']:.0%}")
        logger.info(f"   Hallucination Rate: {extraction_stats['avg_hallucination_rate']:.0%}")

    if dedup_stats and "error" not in dedup_stats:
        logger.info(f"\n   去重品質（threshold={dedup_stats['threshold']:.2f}）：")
        logger.info(f"   Precision: {dedup_stats['precision']:.0%}")
        logger.info(f"   Recall:    {dedup_stats['recall']:.0%}")
        logger.info(f"   F1:        {dedup_stats['f1']:.0%}")

    if dedup_sweep_stats and "error" not in dedup_sweep_stats:
        logger.info(f"\n   閾值掃描：{dedup_sweep_stats.get('recommendation', '')}")

    if report_eval_stats and "error" not in report_eval_stats:
        logger.info("\n   週報品質：")
        if report_eval_stats.get("avg_llm_grounding") is not None:
            logger.info(f"   Grounding:     {report_eval_stats['avg_llm_grounding']:.1f}/5")
        if report_eval_stats.get("avg_llm_actionability") is not None:
            logger.info(f"   Actionability: {report_eval_stats['avg_llm_actionability']:.1f}/5")
        if report_eval_stats.get("avg_llm_relevance") is not None:
            logger.info(f"   Relevance:     {report_eval_stats['avg_llm_relevance']:.1f}/5")

    if low_quality:
        logger.warning(f"\n   ⚠️  低品質 Q&A: {len(low_quality)} 筆（平均分 < 3.0）")

    logger.info(f"\n   📄 詳細報告: {json_path}")
    logger.info(f"   📄 Markdown: {md_path}")
    logger.info(f"   💾 歷史紀錄: {history_path}")
    logger.info(f"   💾 快照: {snapshot_dir / f'eval_{snap_ts}.json'}")
    logger.info("=" * 60)

    # ── 版本化 eval 輸出（output/evals/） ──────────────────
    _save_versioned_eval(args, stats, classify_stats, retrieval_stats, sample_size)

    # Console 輸出 Markdown 報告
    logger.info("\n" + md_report)

    flush_laminar()


def compare_eval_reports(path1: str, path2: str) -> None:
    """比較兩個評估報告，輸出 diff 表格"""
    r1 = json.loads(Path(path1).read_text(encoding="utf-8"))
    r2 = json.loads(Path(path2).read_text(encoding="utf-8"))
    p1, p2 = Path(path1).name, Path(path2).name

    logger.info(f"\n{'='*60}")
    logger.info("📊 評估結果比較")
    logger.info(f"   A: {p1}")
    logger.info(f"   B: {p2}")
    logger.info(f"{'='*60}\n")

    q1 = r1.get("quality_stats", {})
    q2 = r2.get("quality_stats", {})

    dims = ["relevance", "accuracy", "completeness", "granularity"]
    logger.info(f"  {'指標':<20} {'A':>7} {'B':>7} {'Δ':>8}")
    logger.info("  " + "-" * 46)
    for dim in dims:
        v1 = q1.get(dim, {}).get("mean")
        v2 = q2.get(dim, {}).get("mean")
        if v1 is not None and v2 is not None:
            delta = v2 - v1
            arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "→")
            logger.info(f"  {dim:<20} {v1:>7.2f} {v2:>7.2f} {delta:>+7.2f} {arrow}")

    ret1 = r1.get("retrieval_stats") or {}
    ret2 = r2.get("retrieval_stats") or {}
    if ret1 and ret2 and "error" not in ret1 and "error" not in ret2:
        logger.info()
        for key, label in [
            ("avg_mrr", "MRR"),
            ("llm_top1_precision", "Top-1 Precision"),
            ("avg_keyword_hit_rate", "KW Hit Rate"),
            ("avg_category_hit_rate", "Category Hit Rate"),
        ]:
            v1 = ret1.get(key)
            v2 = ret2.get(key)
            if v1 is not None and v2 is not None:
                delta = v2 - v1
                arrow = "↑" if delta > 0.02 else ("↓" if delta < -0.02 else "→")
                logger.info(f"  {label:<20} {v1:>7.2%} {v2:>7.2%} {delta:>+7.2%} {arrow}")

    cc1 = (r1.get("classify_stats") or {}).get("category_accuracy", {})
    cc2 = (r2.get("classify_stats") or {}).get("category_accuracy", {})
    if cc1 and cc2:
        logger.info()
        v1, v2 = cc1.get("accuracy_rate", 0), cc2.get("accuracy_rate", 0)
        delta = v2 - v1
        arrow = "↑" if delta > 0.02 else ("↓" if delta < -0.02 else "→")
        logger.info(f"  {'分類正確率':<20} {v1:>7.0%} {v2:>7.0%} {delta:>+7.0%} {arrow}")

    logger.info(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Q&A 品質評估")
    parser.add_argument("--sample", type=int, default=30, help="抽樣數量（預設 30）")
    parser.add_argument("--seed", type=int, default=42, help="隨機種子（預設 42，設 -1 為不固定）")
    parser.add_argument("--with-source", action="store_true", help="帶入原始 Markdown 驗證 Accuracy/Faithfulness")
    parser.add_argument("--classify-only", action="store_true", help="只評估分類品質")
    parser.add_argument("--skip-classify-eval", action="store_true", help="跳過分類評估")
    parser.add_argument("--eval-retrieval", action="store_true", help="評估 Retrieval 品質")
    parser.add_argument("--debug-retrieval", action="store_true", help="輸出 Retrieval 失敗診斷（TypeA/TypeB）")
    parser.add_argument("--eval-reranking", action="store_true", help="實驗性 LLM Reranking（gpt-5-nano bi-encoder top-20 rerank）")
    parser.add_argument("--retrieval-golden", type=str, default="", help="Retrieval golden set 路徑")
    parser.add_argument("--golden", type=str, default="", help="Golden set JSON 路徑")
    parser.add_argument(
        "--check",
        action="store_true",
        help="只檢查依賴是否就緒，不實際執行",
    )
    parser.add_argument(
        "--compare", nargs=2, metavar=("REPORT_A", "REPORT_B"),
        help="比較兩個 eval_report.json，例如 --compare eval_reports/eval_A.json eval_reports/eval_B.json",
    )
    # ── Phase 2 新增 eval flags ───────────────────────────
    parser.add_argument("--eval-extraction", action="store_true", help="評估萃取品質（需 eval/golden_extraction.json）")
    parser.add_argument("--extraction-golden", type=str, default="", help="Extraction golden set 路徑（預設 eval/golden_extraction.json）")
    parser.add_argument("--eval-dedup", action="store_true", help="評估去重準確度（需 eval/golden_dedup.json）")
    parser.add_argument("--dedup-golden", type=str, default="", help="Dedup golden set 路徑（預設 eval/golden_dedup.json）")
    parser.add_argument("--dedup-threshold-sweep", action="store_true", help="掃描去重閾值 0.80–0.95，找出 F1 最佳閾值")
    parser.add_argument("--eval-report", action="store_true", help="評估週報品質（需 eval/golden_report.json + output/report_*.md）")
    parser.add_argument("--report-golden", type=str, default="", help="Report golden set 路徑（預設 eval/golden_report.json）")
    # ── 跨 provider 追蹤 flags ────────────────────────────
    parser.add_argument("--provider", default="openai",
                        help="Judge provider（預設 openai）")
    parser.add_argument("--extraction-engine", dest="extraction_engine", default="openai",
                        help="Q&A 萃取引擎（openai / claude-code，預設 openai）")
    parser.add_argument("--model", default="",
                        help="Judge model（空白時沿用 config.OPENAI_MODEL）")
    parser.add_argument("--update-baseline", action="store_true",
                        help="若新分數超過基準線閾值（+0.05），更新 output/eval_baseline.json")
    args = parser.parse_args()

    if args.compare:
        compare_eval_reports(args.compare[0], args.compare[1])
        sys.exit(0)

    if args.seed == -1:
        args.seed = None

    main(args)
