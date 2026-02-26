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
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    import config
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import config

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
   - 3 分：有回答但缺少原因、案例或數據
   - 5 分：包含具體建議、原因、案例與行動方向

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


def load_golden_set(path: str) -> list[dict]:
    """載入 golden set（人工標注的正確答案）"""
    golden_path = Path(path)
    if golden_path.exists():
        return json.loads(golden_path.read_text(encoding="utf-8"))
    return []


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


def evaluate_retrieval(
    golden_cases: list[dict],
    qa_pairs: list[dict],
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
    case_results: list[dict] = []

    for case in golden_cases:
        query = case["query"]
        expected_kws = [kw.lower() for kw in case.get("expected_keywords", [])]
        expected_cats = case.get("expected_categories", [])

        # Embed query
        q_emb = np.array(get_embeddings([query]))
        q_norm = q_emb / (np.linalg.norm(q_emb, axis=1, keepdims=True) + 1e-8)
        scores = (q_norm @ qa_norm.T).flatten()

        # Keyword boost
        for ji, qa in enumerate(qa_pairs):
            keywords = qa.get("keywords", [])
            hits = sum(1 for kw in keywords if kw.lower() in query.lower())
            if hits > 0:
                scores[ji] += 0.08 * min(hits, 3)

        top_indices = np.argsort(scores)[::-1][:top_k]
        retrieved = [qa_pairs[int(idx)] for idx in top_indices]
        retrieved_scores = [float(scores[int(idx)]) for idx in top_indices]

        # Keyword Hit Rate: 檢查 retrieved Q&A 的 keywords 是否覆蓋 expected_keywords
        all_retrieved_kws = set()
        for qa in retrieved:
            all_retrieved_kws.update(kw.lower() for kw in qa.get("keywords", []))
        kw_hits = sum(1 for kw in expected_kws if kw in all_retrieved_kws)
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


def _llm_judge_retrieval_relevance(query: str, qa: dict) -> bool:
    """用 LLM 判斷 retrieved Q&A 是否與 query 真的相關"""
    client = _client()

    user_msg = (
        f"搜尋查詢：{query}\n\n"
        f"檢索到的 Q&A：\n"
        f"Q: {qa['question']}\n"
        f"A: {qa['answer'][:500]}\n\n"
        f"這個 Q&A 是否與搜尋查詢相關？請回答 relevant 或 not_relevant。"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
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
    except Exception:
        return False


# ──────────────────────────────────────────────────────
# LLM-as-Judge：Q&A 品質評估
# ──────────────────────────────────────────────────────

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
        f"--- 萃取的 Q&A ---\n"
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
        f"系統標記的分類：\n"
        f"- category: {qa.get('category', 'N/A')}\n"
        f"- difficulty: {qa.get('difficulty', 'N/A')}\n"
        f"- evergreen: {qa.get('evergreen', 'N/A')}\n"
    )

    response = client.chat.completions.create(
        model="gpt-5-mini",
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
        f"- 評估樣本數：{sample_size}",
        f"- 帶原始來源驗證：{'是' if with_source else '否'}",
        f"- 評估日期：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
# 主程式
# ──────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> None:
    if not config.OPENAI_API_KEY:
        print("❌ 請設定 OPENAI_API_KEY（在 .env）")
        sys.exit(1)

    print("=" * 60)
    print("📊 步驟 5：Q&A 品質評估（Evaluation）")
    print(f"   Judge 模型: {config.OPENAI_MODEL}")
    print(f"   抽樣數量: {args.sample}")
    print(f"   帶原始來源: {'是' if args.with_source else '否'}")
    print("=" * 60)

    # 載入資料
    qa_pairs = load_qa_data()
    if not qa_pairs:
        print("❌ 找不到 Q&A 資料，請先執行步驟 2-3")
        sys.exit(1)

    print(f"\n📥 載入 {len(qa_pairs)} 個 Q&A")

    # 抽樣
    sample_size = min(args.sample, len(qa_pairs))
    if args.seed is not None:
        random.seed(args.seed)
    sampled = random.sample(qa_pairs, sample_size)
    print(f"   抽樣 {sample_size} 個（seed: {args.seed}）")

    # ── Q&A 品質評估 ──
    eval_results: list[dict] = []
    if not args.classify_only:
        print(f"\n🔍 評估 Q&A 品質（{sample_size} 筆）...")
        for i, qa in enumerate(sampled, 1):
            source_text = ""
            if args.with_source and qa.get("source_file"):
                source_text = load_source_markdown(qa["source_file"])

            print(f"  [{i}/{sample_size}] {qa['question'][:50]}...")

            try:
                result = evaluate_qa_quality(qa, source_text)
                result["_qa_id"] = qa.get("id", i)
                result["_question"] = qa["question"]
                result["_confidence"] = qa.get("confidence", None)
                eval_results.append(result)
            except Exception as e:
                print(f"    ⚠️  評估失敗: {e}")
                eval_results.append({"error": str(e), "_qa_id": qa.get("id", i)})

            time.sleep(0.5)

    # ── 分類品質評估 ──
    classify_results: list[dict] = []
    classify_stats = None
    if not args.skip_classify_eval:
        classified = [qa for qa in sampled if qa.get("category")]
        if classified:
            eval_count = min(len(classified), args.sample)
            print(f"\n🏷️  評估分類品質（{eval_count} 筆）...")
            for i, qa in enumerate(classified[:eval_count], 1):
                print(f"  [{i}/{eval_count}] {qa.get('category', '?')} ← {qa['question'][:40]}...")
                try:
                    result = evaluate_classification(qa)
                    if "category_judgment" not in result:
                        print(f"    ⚠️  空回應（推理模型 content=None），跳過 QA {qa.get('id', i)}")
                        continue
                    result["_qa_id"] = qa.get("id", i)
                    result["_original_category"] = qa.get("category", "")
                    classify_results.append(result)
                except Exception as e:
                    print(f"    ⚠️  評估失敗: {e}")

                time.sleep(0.3)

            classify_stats = compute_classify_statistics(classify_results)

    # ── Retrieval 品質評估 ──
    retrieval_stats = None
    if args.eval_retrieval:
        golden_ret = load_golden_retrieval(args.retrieval_golden)
        if golden_ret:
            print(f"\n🔎 評估 Retrieval 品質（{len(golden_ret)} 個場景）...")
            retrieval_stats = evaluate_retrieval(golden_ret, qa_pairs)
        else:
            print("   ⚠️  找不到 retrieval golden set，跳過")

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

    # 印出摘要
    print("\n" + "=" * 60)
    print("📊 評估結果摘要")
    print("=" * 60)

    if stats:
        for dim in ["relevance", "accuracy", "completeness", "granularity"]:
            if dim in stats:
                print(f"   {dim:15s}: {stats[dim]['mean']:.2f} / 5.0")

    if classify_stats:
        ca = classify_stats["category_accuracy"]
        print(f"\n   分類正確率: {ca['accuracy_rate']:.0%}")
        print(f"   Difficulty 合理率: {classify_stats['difficulty_accuracy']:.0%}")
        print(f"   Evergreen 合理率: {classify_stats['evergreen_accuracy']:.0%}")

    if retrieval_stats and "error" not in retrieval_stats:
        print(f"\n   Retrieval 品質：")
        print(f"   KW 命中率: {retrieval_stats['avg_keyword_hit_rate']:.0%}")
        print(f"   分類命中率: {retrieval_stats['avg_category_hit_rate']:.0%}")
        print(f"   MRR: {retrieval_stats['avg_mrr']:.2f}")
        print(f"   Top-1 Precision: {retrieval_stats['llm_top1_precision']:.0%}")

    if low_quality:
        print(f"\n   ⚠️  低品質 Q&A: {len(low_quality)} 筆（平均分 < 3.0）")

    print(f"\n   📄 詳細報告: {json_path}")
    print(f"   📄 Markdown: {md_path}")
    print(f"   💾 歷史紀錄: {history_path}")
    print(f"   💾 快照: {snapshot_dir / f'eval_{snap_ts}.json'}")
    print("=" * 60)

    # Console 輸出 Markdown 報告
    print("\n" + md_report)


def compare_eval_reports(path1: str, path2: str) -> None:
    """比較兩個評估報告，輸出 diff 表格"""
    r1 = json.loads(Path(path1).read_text(encoding="utf-8"))
    r2 = json.loads(Path(path2).read_text(encoding="utf-8"))
    p1, p2 = Path(path1).name, Path(path2).name

    print(f"\n{'='*60}")
    print(f"📊 評估結果比較")
    print(f"   A: {p1}")
    print(f"   B: {p2}")
    print(f"{'='*60}\n")

    q1 = r1.get("quality_stats", {})
    q2 = r2.get("quality_stats", {})

    dims = ["relevance", "accuracy", "completeness", "granularity"]
    print(f"  {'指標':<20} {'A':>7} {'B':>7} {'Δ':>8}")
    print("  " + "-" * 46)
    for dim in dims:
        v1 = q1.get(dim, {}).get("mean")
        v2 = q2.get(dim, {}).get("mean")
        if v1 is not None and v2 is not None:
            delta = v2 - v1
            arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "→")
            print(f"  {dim:<20} {v1:>7.2f} {v2:>7.2f} {delta:>+7.2f} {arrow}")

    ret1 = r1.get("retrieval_stats") or {}
    ret2 = r2.get("retrieval_stats") or {}
    if ret1 and ret2 and "error" not in ret1 and "error" not in ret2:
        print()
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
                print(f"  {label:<20} {v1:>7.2%} {v2:>7.2%} {delta:>+7.2%} {arrow}")

    cc1 = (r1.get("classify_stats") or {}).get("category_accuracy", {})
    cc2 = (r2.get("classify_stats") or {}).get("category_accuracy", {})
    if cc1 and cc2:
        print()
        v1, v2 = cc1.get("accuracy_rate", 0), cc2.get("accuracy_rate", 0)
        delta = v2 - v1
        arrow = "↑" if delta > 0.02 else ("↓" if delta < -0.02 else "→")
        print(f"  {'分類正確率':<20} {v1:>7.0%} {v2:>7.0%} {delta:>+7.0%} {arrow}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Q&A 品質評估")
    parser.add_argument("--sample", type=int, default=30, help="抽樣數量（預設 30）")
    parser.add_argument("--seed", type=int, default=42, help="隨機種子（預設 42，設 -1 為不固定）")
    parser.add_argument("--with-source", action="store_true", help="帶入原始 Markdown 驗證 Accuracy/Faithfulness")
    parser.add_argument("--classify-only", action="store_true", help="只評估分類品質")
    parser.add_argument("--skip-classify-eval", action="store_true", help="跳過分類評估")
    parser.add_argument("--eval-retrieval", action="store_true", help="評估 Retrieval 品質")
    parser.add_argument("--retrieval-golden", type=str, default="", help="Retrieval golden set 路徑")
    parser.add_argument("--golden", type=str, default="", help="Golden set JSON 路徑")
    parser.add_argument(
        "--compare", nargs=2, metavar=("REPORT_A", "REPORT_B"),
        help="比較兩個 eval_report.json，例如 --compare eval_reports/eval_A.json eval_reports/eval_B.json",
    )
    args = parser.parse_args()

    if args.compare:
        compare_eval_reports(args.compare[0], args.compare[1])
        sys.exit(0)

    if args.seed == -1:
        args.seed = None

    main(args)
