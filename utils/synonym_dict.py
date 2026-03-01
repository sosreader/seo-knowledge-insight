"""
synonym_dict — SEO 術語同義詞詞典

提供：
  SYNONYMS:       dict[str, list[str]] — term → 同義詞清單
  expand_keywords: 將關鍵字清單展開（含同義詞），回傳 sorted, 去重 list

同義詞來源（優先序）：
  1. METRIC_QUERY_MAP 衍生（utils/metrics_parser.py — 核心指標術語）
  2. 補充詞典（_SUPPLEMENTAL_SYNONYMS）— 語意技術術語

使用時機：
  scripts/enrich_qa.py          （offline enrichment pipeline）
  utils/search_engine.py        （search-time synonym boost）
"""
from __future__ import annotations

import functools


# ── 補充詞典（不依賴 METRIC_QUERY_MAP 的技術術語）──────────────────
_SUPPLEMENTAL_SYNONYMS: dict[str, list[str]] = {
    "AMP": ["Accelerated Mobile Pages", "加速行動網頁", "AMP Article", "AMP non-Rich"],
    "canonical": ["正規化", "canonical URL", "標準網址", "重覆頁面", "Google選擇", "rel canonical"],
    "CTR": ["點擊率", "click-through rate", "Click Through Rate"],
    "Core Web Vitals": ["CWV", "網頁核心指標", "LCP", "INP", "CLS", "良好體驗"],
    "結構化資料": ["Structured Data", "Schema.org", "JSON-LD", "rich snippet", "Rich Result", "結構化標記"],
    "爬蟲": ["Crawler", "Googlebot", "Spider", "Crawl Budget", "抓取", "crawl"],
    "反向連結": ["Backlink", "外部連結", "inbound link", "referring domain", "backlinks"],
    "hreflang": ["多語系", "語言標記", "地區設定", "國際 SEO", "x-default"],
    "noindex": ["不索引", "排除索引", "robots meta", "disallow", "noindex tag"],
    "sitemap": ["網站地圖", "Sitemap.xml", "提交索引", "XML sitemap"],
    "SERP": ["搜尋結果頁", "Search Engine Results Page", "搜尋版位", "搜尋結果"],
    "E-E-A-T": ["專業度", "權威性", "可信度", "作者資訊", "EEAT", "E-A-T"],
    "Discover": ["Google Discover", "Google 探索", "探索推薦", "探索流量"],
    "曝光": ["曝光數", "Impression", "impressions", "曝光量"],
    "點擊": ["點擊數", "Click", "clicks", "點擊量"],
    "索引": ["Index", "索引狀態", "Coverage", "收錄", "index coverage"],
    "有效": ["有效頁面", "Submitted and indexed", "Coverage 有效"],
    "重新導向": ["Redirect", "301", "302", "轉址", "redirect chain"],
    "robots.txt": ["robots", "crawl disallow", "爬蟲封鎖", "Googlebot 封鎖"],
    "Google Search Console": ["GSC", "搜尋主控台", "Search Console", "站長工具"],
}


def _build_metric_query_synonyms() -> dict[str, list[str]]:
    """
    從 METRIC_QUERY_MAP 的 key + query tokens 衍生同義詞對。

    延遲 import 避免啟動時觸發副作用。
    若 metrics_parser 無法 import（測試隔離環境）則回傳空 dict。
    """
    try:
        from utils.metrics_parser import METRIC_QUERY_MAP  # type: ignore[import]
    except ImportError:
        return {}

    synonyms: dict[str, list[str]] = {}
    for metric_name, queries in METRIC_QUERY_MAP.items():
        related: set[str] = set()
        for q in queries:
            for token in q.split():
                # 長度 >= 2 且不等於指標名稱本身
                if len(token) >= 2 and token != metric_name:
                    related.add(token)
        if related:
            synonyms[metric_name] = sorted(related)
    return synonyms


def _build_synonyms() -> dict[str, list[str]]:
    """合併 METRIC_QUERY_MAP 衍生 + 補充詞典（補充詞典優先）。"""
    result = _build_metric_query_synonyms()
    # 補充詞典覆蓋：若 key 已存在則合併去重
    for term, syns in _SUPPLEMENTAL_SYNONYMS.items():
        existing = set(result.get(term, []))
        existing.update(syns)
        result[term] = sorted(existing)
    return result


@functools.lru_cache(maxsize=1)
def _get_synonyms() -> dict[str, list[str]]:
    """Build and cache synonym dict (thread-safe via lru_cache)."""
    return _build_synonyms()


def expand_keywords(keywords: list[str]) -> list[str]:
    """
    從同義詞詞典展開關鍵字清單。

    Args:
        keywords: 原始關鍵字清單

    Returns:
        包含原始詞 + 同義詞的 list（sorted 去重）
    """
    synonyms = _get_synonyms()
    expanded: set[str] = set(keywords)
    for kw in keywords:
        if kw in synonyms:
            expanded.update(synonyms[kw])
    return sorted(expanded)
