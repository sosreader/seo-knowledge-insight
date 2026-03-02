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
    "TTFB": ["伺服器回應時間", "回應時間", "Time to First Byte", "首位元組時間"],
    "WAF": ["Web Application Firewall", "網頁應用程式防火牆", "防火牆規則"],
    "工作階段": ["Session", "sessions", "工作階段數", "Organic Search工作階段"],
    "Organic Search": ["自然搜尋", "有機搜尋", "搜尋流量", "Organic"],
    # Coverage <-> 索引覆蓋率 為刻意的雙向映射，expand_query_tokens 只做單層展開，不會無限遞迴
    "Coverage": ["索引覆蓋率", "有效頁面", "收錄率", "索引率"],
    "內容供給": ["當週文章", "文章數量", "文章頻率", "供給量"],
    "索引覆蓋率": ["Coverage", "有效 (Coverage)", "已索引頁面"],
    "版位": ["SERP 版位", "搜尋版位", "搜尋位置", "版位變化"],
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


# ── CJK n-gram + query expansion ─────────────────────


def _is_cjk_char(char: str) -> bool:
    """判斷單一字元是否為 CJK 統一表意文字。"""
    cp = ord(char)
    return (
        0x4E00 <= cp <= 0x9FFF        # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF     # CJK Unified Ideographs Extension A
        or 0xF900 <= cp <= 0xFAFF     # CJK Compatibility Ideographs
    )


def _has_cjk(token: str) -> bool:
    """token 是否含有至少一個 CJK 字元。"""
    return any(_is_cjk_char(c) for c in token)


def _expand_cjk_ngrams(token: str, max_n: int = 4) -> set[str]:
    """
    將含 CJK 字元的長 token 展開為 bigram ~ max_n-gram。

    只對 CJK 連續字元子串做 n-gram（跳過 ASCII 段落）。
    例：「內部連結架構優化」→ {內部, 連結, 架構, 優化, 內部連結, 連結架構, ...}

    限制：被 ASCII 分隔的單一 CJK 字元不產出 n-gram（buf 長度 < 2 時跳過）。
    例：「A索B引C」中「索」「引」各自獨立，不會組成「索引」bigram。
    """
    # 先抽出純 CJK 連續片段
    cjk_runs: list[str] = []
    buf: list[str] = []
    for ch in token:
        if _is_cjk_char(ch):
            buf.append(ch)
        else:
            if len(buf) > 1:
                cjk_runs.append("".join(buf))
            buf = []
    if len(buf) > 1:
        cjk_runs.append("".join(buf))

    ngrams: set[str] = set()
    for run in cjk_runs:
        for n in range(2, min(max_n + 1, len(run) + 1)):
            for i in range(len(run) - n + 1):
                ngrams.add(run[i:i + n])
    return ngrams


@functools.lru_cache(maxsize=1)
def _get_supplemental_synonyms_lower() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    建立 lowercase 正向索引 + 反向索引（cached）。

    Returns:
        (forward, inverted)
        forward:  key_lower -> [syn_lower, ...]
        inverted: syn_lower -> [key_lower, ...]
    """
    forward: dict[str, list[str]] = {}
    inverted: dict[str, list[str]] = {}
    for key, syns in _SUPPLEMENTAL_SYNONYMS.items():
        kl = key.lower()
        syn_lowers = [s.lower() for s in syns]
        forward[kl] = syn_lowers
        for sl in syn_lowers:
            inverted.setdefault(sl, []).append(kl)
    return forward, inverted


def expand_query_tokens(query: str) -> set[str]:
    """
    將搜尋 query 展開為 token set（三層展開）。

    Layer 1: whitespace split + CJK n-gram（解決中文分詞）
    Layer 2: Forward synonym（CTR -> 點擊率）
    Layer 3: Inverted synonym（n-gram 是某同義詞值 → 加入主鍵）

    僅使用 _SUPPLEMENTAL_SYNONYMS，不使用 METRIC_QUERY_MAP
    （後者含 "原因"/"如何" 等噪音 token，實測會造成 regression）。
    """
    raw_tokens = set(query.lower().split())
    expanded: set[str] = set(raw_tokens)

    # Layer 1: CJK n-gram
    cjk_ngrams: set[str] = set()
    for token in raw_tokens:
        if len(token) > 2 and _has_cjk(token):
            cjk_ngrams.update(_expand_cjk_ngrams(token))
    expanded.update(cjk_ngrams)

    forward, inverted = _get_supplemental_synonyms_lower()

    # Layer 2: Forward synonym — token 是 key → 加入 synonyms
    for token in raw_tokens | cjk_ngrams:
        if token in forward:
            expanded.update(forward[token])

    # Layer 3: Inverted synonym — token 是某 key 的 synonym → 加入 key
    for token in raw_tokens | cjk_ngrams:
        if token in inverted:
            expanded.update(inverted[token])

    return expanded
