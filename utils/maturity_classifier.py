"""
maturity_classifier.py — Rule-based SEO maturity level classifier.

Classifies QA items into L1-L4 based on keywords, question complexity, and answer depth.
Shared between backfill script and pipeline auto-tagging.

Levels:
  L1 起步期 — basic awareness, manual processes
  L2 建置期 — structured processes, systematic tracking
  L3 優化期 — data-driven optimization, automated workflows
  L4 領先期 — predictive analytics, cross-channel integration
"""

from __future__ import annotations

import re
from typing import Optional

# --- Keyword patterns per level (ordered from most specific to least) ---

# L4_KEYWORDS — implementation-level / leading-edge terms only.
# 純 trend/topic 詞移到 TREND_TOPIC_TERMS，避免單一趨勢詞自動觸發 L4。
L4_KEYWORDS = frozenset([
    "預測", "predictive", "forecasting",
    "排名預測", "流量預測", "預測模型",
    "機器學習", "machine learning", "ml model",
    "跨通路", "跨通路整合", "cross-channel", "omnichannel",
    "歸因分析", "歸因模型", "attribution model", "multi-touch",
    "自動化測試", "seo 自動化測試", "automated testing framework", "regression testing",
    "competitive intelligence", "競爭情報", "競爭情報系統",
    "程式化 seo", "programmatic seo",
    "增量價值", "incremental value",
    "知識圖譜", "knowledge graph",
    "內容生成 pipeline", "content pipeline",
    "推薦系統", "recommendation engine",
    "citation growth", "引用成長",
    "scenario planning", "情境規劃",
    "authority building", "decision gates",
])

# TREND_TOPIC_TERMS — 趨勢主題詞（topic ≠ maturity）。
# 只給 +1 輔助分；單獨命中無法升 L4，必須與 advanced pattern / L4_STRATEGY_TERMS / 長答案並存。
TREND_TOPIC_TERMS = frozenset([
    "ai overview", "ai overviews", "aio",
    "ai search", "生成式搜尋",
    "geo", "generative engine optimization",
    "aeo", "answer engine optimization",
    "llm seo", "ai 可見度", "ai visibility",
    "ai 驅動", "ai-driven", "ai-powered",
    "品牌可見度", "brand visibility",
])

AI_SEARCH_TERMS = frozenset([
    "ai overview", "ai overviews", "aio",
    "ai search", "生成式搜尋",
    "geo", "generative engine optimization",
    "aeo", "answer engine optimization",
    "llm seo", "ai 可見度", "ai visibility",
])

# L4_STRATEGY_TERMS — 真正的策略級信號（去掉純 topic 詞 brand visibility）。
L4_STRATEGY_TERMS = frozenset([
    "citation growth", "引用成長",
    "scenario planning", "情境規劃",
    "authority building", "decision gates",
    "競爭情報", "competitive intelligence",
    "site:", "sub-queries", "subqueries",
    "流量預測", "預測模型",
])

L3_KEYWORDS = frozenset([
    "a/b test", "a/b 測試", "ab test",
    "數據分析", "data-driven", "data analysis",
    "自動化", "automation", "automated",
    "dashboard", "儀表板",
    "sop", "標準作業", "standard operating",
    "kpi 追蹤", "kpi tracking",
    "segmentation", "分群",
    "advanced schema", "進階 schema",
    "log analysis", "日誌分析",
    "crawl budget", "爬取預算",
    "api 整合", "api integration",
    "content hub", "內容中心",
    "entity seo", "實體 seo",
])

L2_KEYWORDS = frozenset([
    "流程", "process", "workflow",
    "追蹤", "tracking", "monitor",
    "指標", "metrics", "kpi",
    "google search console", "gsc",
    "google analytics", "ga4",
    "sitemap", "robots.txt",
    "canonical", "hreflang",
    "內部連結", "internal link",
    "meta tag", "meta 標籤",
    "schema markup", "結構化資料",
    "core web vitals", "cwv",
    "search intent", "搜尋意圖",
    "content calendar", "內容行事曆",
    "競爭分析", "competitor analysis",
])

L1_KEYWORDS = frozenset([
    "什麼是", "what is",
    "基礎", "basic", "beginner", "入門",
    "如何開始", "how to start", "getting started",
    "seo 是什麼", "seo 定義",
    "title tag", "標題標籤",
    "meta description",
    "關鍵字研究", "keyword research",
    "反向連結", "backlink",
    "on-page", "頁面優化",
    "google 索引", "google indexing",
    "seo 工具", "seo tool",
    "搜尋引擎", "search engine",
])

# Complexity indicators (answer depth)
ADVANCED_PATTERNS = [
    re.compile(r"(?:分析|分群|模型|框架|架構|演算法|pipeline)", re.IGNORECASE),
    re.compile(r"(?:integrate|integration|orchestrat|automat)", re.IGNORECASE),
    re.compile(r"(?:api|sdk|webhook|endpoint)", re.IGNORECASE),
]

BASIC_PATTERNS = [
    re.compile(r"(?:第一步|首先|建議先|可以先)", re.IGNORECASE),
    re.compile(r"(?:簡單來說|簡而言之|基本上)", re.IGNORECASE),
    re.compile(r"(?:what is|定義是)", re.IGNORECASE),
]

# 雙重證據 demote 門檻
_L4_DUAL_EVIDENCE_TRIGGER = 2


def classify_maturity_level(
    keywords: list[str],
    question: str,
    answer: str,
) -> Optional[str]:
    """Classify a QA item's maturity level based on content analysis.

    Returns "L1", "L2", "L3", "L4", or None if confidence is too low.

        Strategy (scoring):
            1. Match level-specific keywords in keywords/question/answer text (L4_KEYWORDS +2)
            2. TREND_TOPIC_TERMS only +1 each (topics, not maturity)
            3. Apply advanced/basic pattern bonuses from answer phrasing
            4. Apply AI-search strategy bonus when AI-search and L4 strategy signals coexist
            5. Dual-evidence demote: L4 must be backed by advanced pattern / L4 strategy term
               / long answer; otherwise reset L4 score to 0
            6. Return None if max score stays below the minimum confidence threshold
    """
    combined_text = f"{question} {answer}".lower()
    kw_text = " ".join(k.lower() for k in keywords)
    full_text = f"{kw_text} {combined_text}"

    # Score each level
    scores = {"L4": 0, "L3": 0, "L2": 0, "L1": 0}

    for term in L4_KEYWORDS:
        if term in full_text:
            scores["L4"] += 2

    # 趨勢詞：給 +1 輔助分（不足以單獨升 L4）
    for term in TREND_TOPIC_TERMS:
        if term in full_text:
            scores["L4"] += 1

    for term in L3_KEYWORDS:
        if term in full_text:
            scores["L3"] += 2

    for term in L2_KEYWORDS:
        if term in full_text:
            scores["L2"] += 1

    for term in L1_KEYWORDS:
        if term in full_text:
            scores["L1"] += 1

    # Complexity modifiers from answer patterns
    has_advanced = False
    for pattern in ADVANCED_PATTERNS:
        if pattern.search(answer):
            scores["L3"] += 1
            scores["L4"] += 1
            has_advanced = True

    has_ai_search_signal = any(term in full_text for term in AI_SEARCH_TERMS)
    has_l4_strategy_signal = any(term in full_text for term in L4_STRATEGY_TERMS)
    if has_ai_search_signal and has_l4_strategy_signal:
        scores["L4"] += 2

    for pattern in BASIC_PATTERNS:
        if pattern.search(answer):
            scores["L1"] += 2

    # Answer length as signal (very short = likely basic)
    if len(answer) < 100:
        scores["L1"] += 1
    elif len(answer) > 500:
        scores["L3"] += 1

    if "預測" not in full_text and ("預期" in full_text or "預設" in full_text):
        scores["L4"] = max(0, scores["L4"] - 2)

    # ── Dual-evidence rule (Task B) ────────────────────────────────────
    # 若 L4 達門檻但缺乏 advanced pattern / L4 strategy term / 長答案佐證，
    # 視為「只談趨勢」而非真正 L4，重置 L4 分數。
    if scores["L4"] >= _L4_DUAL_EVIDENCE_TRIGGER:
        has_long_answer = len(answer) > 500
        if not (has_advanced or has_l4_strategy_signal or has_long_answer):
            scores["L4"] = 0

    # Pick highest score level
    max_score = max(scores.values())
    if max_score < 2:
        return None  # Low confidence — needs LLM review

    # Tie-breaking: prefer higher maturity when scores are equal.
    for level in ("L4", "L3", "L2", "L1"):
        if scores[level] == max_score:
            return level

    return None
