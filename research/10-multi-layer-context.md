# Multi-Layer Context 架構（Phase 1，2026-03-02）

> 屬於 [research/](./README.md)，從 [02-rag-and-search.md](./02-rag-and-search.md) 拆出。
> 對應實作計畫：`plans/completed/version-registry-multilayer.md`。

---

## 術語速查

| 術語 | 定義 |
|------|------|
| **enrichment** | 離線預計算程序：對每筆 Q&A 加入同義詞列表、時效性分數等 metadata |
| **qa_enriched.json** | `scripts/enrich_qa.py`（`make enrich`）產生的豐富化版知識庫，含 `_enrichment` 欄位 |
| **_enrichment** | Q&A JSON 物件中的 enrichment metadata 欄位（synonyms / freshness_score / search_hit_count） |
| **Learning Store** | `utils/learning_store.py`，JSONL append-only 失敗記憶庫（record_miss / record_feedback） |
| **Multi-Layer Context** | 三層知識庫架構：Knowledge（靜態）+ Context（離線計算）+ Learnings（動態） |
| **Staleness** | Q&A 超過 18 個月未更新，在 chat 回答中加入 ⚠️ 警示 |
| **Version Registry** | `utils/pipeline_version.py`，不可變 artifact 版本記錄（content_hash + 語意標籤） |

---

## 20. Multi-Layer Context Architecture

> 參考：OpenAI Data Agent（March 2026）啟發，實作見 `plans/completed/version-registry-multilayer.md`。

### 架構總覽（三層）

```
Knowledge Layer（靜態）：qa_final.json / qa_enriched.json
  ↕ offline enrichment（make enrich）
Context Layer（離線計算）：synonyms + freshness_score + search_hit_count
  ↕ real-time feedback
Learnings Layer（動態）：output/learnings.jsonl（record_miss + record_feedback）
```

### 為什麼需要三層？

| 層 | 解決的問題 | 業界對應 |
|----|-----------|---------|
| Knowledge | 靜態知識庫的覆蓋率與品質 | Elasticsearch index |
| Context | 搜尋時缺乏同義詞/時效加權 | Elasticsearch synonym filter + date boost |
| Learnings | 反覆失敗的搜尋無法改善 | Elastic Learn to Rank, Self-RAG |

---

## 21. 同義詞擴展（Synonym Expansion）

### 設計原則

1. **`METRIC_QUERY_MAP` 衍生優先**（`utils/metrics_parser.py`）：從現有 metric key 和 query values 自動萃取，確保覆蓋核心 SEO 指標
2. **`_SUPPLEMENTAL_SYNONYMS` 補充詞典**：手工維護 AMP/CTR/canonical/hreflang 等 SEO 技術術語
3. **`@functools.lru_cache(maxsize=1)` 執行緒安全**：字典只建一次，後續讀取免鎖

### `@functools.lru_cache` vs `global + None check`

```python
# BAD：全局可變狀態，多執行緒有 race condition
_SYNONYMS: dict | None = None
def _get_synonyms():
    global _SYNONYMS
    if _SYNONYMS is None:
        _SYNONYMS = _build()   # race: 兩個 thread 同時到這裡
    return _SYNONYMS

# GOOD：lru_cache 內建執行緒安全，且語意更清晰
@functools.lru_cache(maxsize=1)
def _get_synonyms() -> dict[str, list[str]]:
    return _build()             # 只呼叫一次，保證 singleton
```

**`maxsize=1`**：只快取一組結果（詞典固定不變），等同 singleton pattern。

### `expand_keywords()` 設計

```python
def expand_keywords(keywords: list[str]) -> list[str]:
    """
    輸入原始關鍵字列表，輸出包含同義詞的展開結果。
    - sorted + 去重（set 操作後排序）
    - 保留原始詞（確保原意不丟失）
    - 未知詞回傳原列表（不亂加不相關詞）
    """
    synonyms = _get_synonyms()
    expanded: set[str] = set(keywords)
    for kw in keywords:
        if kw in synonyms:
            expanded.update(synonyms[kw])
    return sorted(expanded)
```

### 本專案效益（2026-03-02 eval）

- avg_synonyms：**11.09 個/筆 Q&A**
- KW Hit Rate：70.4% → **79.67%**（+9.27pp）

### 學術依據

- **Xu & Croft（SIGIR 1996）**：Query Expansion 是資訊檢索標準技術
- **Ma et al. "Query2Doc"（EMNLP 2023）**：查詢豐富化顯著改善 dense retrieval
- **Elasticsearch synonym token filter**：企業搜尋業界標準作法

---

## 22. 時效性衰減（Temporal Freshness Decay）

### 公式

```
freshness_score = exp(-0.693 × age_days / half_life_days)
```

- **半衰期 540 天**（≈ 18 個月）：SEO 演算法年更頻率的業界估計
- **min_score = 0.5**：防止過舊資料完全被排除（保底 50%）
- **evergreen = True → 1.0**：常青內容（GA 設定、HTML 基礎）不衰減

### Python 實作

```python
def compute_freshness_score(
    source_date: str,
    is_evergreen: bool,
    half_life_days: float = 540.0,
    min_score: float = 0.5,
) -> float:
    if is_evergreen:
        return 1.0
    try:
        d = date.fromisoformat(source_date)
    except (ValueError, TypeError):
        return 1.0   # 無日期 → 保守回傳 1.0
    age_days = (date.today() - d).days
    if age_days <= 0:
        return 1.0
    decay = math.exp(-0.693 * age_days / half_life_days)
    return max(min_score, round(decay, 4))
```

### 設計決策：乘法而非減法

| 方式 | 公式 | 問題 |
|------|------|------|
| 減法 | `score - freshness_penalty` | 可能得到負分 |
| **乘法（採用）** | `base_score × freshness_score` | 永遠在 [min_score, 1.0]，不破壞排名結構 |

### 效益（2026-03-02）

- avg_freshness：**0.9076**（知識庫整體新鮮度良好，半數以上 Q&A 接近 1.0）
- freshness_rank_quality：**1.0**（舊文件未擠掉新文件，衰減機制生效）

### 學術依據

- **Dong et al. "Towards Recency Ranking in Web Search"（WWW 2010）**
- **Google Freshness Update（Nov 2011）**：時效性是官方排名因素
- SEO 情境：2023 年的 AMP 建議在 2026 年可能有害

---

## 23. Offline Enrichment Pipeline（enrich_qa.py）

### 設計原則

| 原則 | 做法 |
|------|------|
| 不消耗 LLM token | 純規則式（synonym dict + 數學公式） |
| 冪等 | 相同輸入永遠產生相同輸出 |
| 原子寫入 | `.tmp` → `rename`（POSIX atomic） |
| Fallback 安全 | store.load() 優先 qa_enriched.json，失敗回 qa_final.json |

### 輸出格式（`_enrichment` 欄位）

```json
{
  "id": 42,
  "question": "Discover 流量下降原因？",
  "_enrichment": {
    "synonyms": ["Discover", "Google Discover", "Discover 能見度", "探索流量"],
    "freshness_score": 0.8187,
    "search_hit_count": 0
  }
}
```

### SearchEngine 預計算（啟動時一次性）

```python
# app/core/store.py load() 後，SearchEngine.__init__() 預計算
self._synonym_boost_vec: np.ndarray = np.array([
    SYNONYM_BOOST if qa.get("_enrichment", {}).get("synonyms") else 0.0
    for qa in qa_pairs
], dtype=np.float32)   # shape: (n_qa,)

self._freshness_vec: np.ndarray = np.array([
    float(qa.get("_enrichment", {}).get("freshness_score", 1.0))
    for qa in qa_pairs
], dtype=np.float32)   # shape: (n_qa,)
```

**為什麼預計算？** 避免每次搜尋時 O(n) 重新遍歷 655 筆 Q&A，啟動時一次計算，搜尋時 O(1) broadcast。

### 執行指令

```bash
make enrich   # 執行 scripts/enrich_qa.py，輸出 output/qa_enriched.json
```

---

## 24. Learning Store + Staleness Feedback Loop

### 三個記錄函式

```python
class LearningStore:
    def record_miss(self, query: str, top_score: float, context: str) -> None:
        """搜尋未命中（top_score < 0.35）時自動記錄，來源：rag_chat()"""

    def record_feedback(self, query: str, qa_id: int,
                        feedback: Literal["helpful", "not_relevant"],
                        top_score: Optional[float] = None) -> None:
        """使用者回報結果不相關，來源：POST /api/v1/feedback"""

    def get_relevant_learnings(self, query: str) -> list[dict]:
        """keyword token 匹配，找到歷史失敗中相關的 learnings"""
```

### JSONL 選擇原因

| 選項 | 優點 | 缺點 |
|------|------|------|
| SQLite | 結構化查詢 | 增加依賴、需 schema migration |
| **JSONL（採用）** | append-only、zero-dependency、git-diff 可讀 | 全量載入記憶體（規模小時 OK） |

### Staleness 警示（18 個月閾值）

```python
def _is_stale(source_date: str) -> bool:
    """超過 18 個月（540 天）的非 evergreen Q&A 標記為可能過時"""
    try:
        d = date.fromisoformat(source_date)
        return (date.today() - d).days > 540
    except (ValueError, TypeError):
        return False
```

在 `rag_chat()` 的 context 組裝中，若 Q&A 過時則加注：

```
[注意：此建議超過 18 個月，請確認是否仍適用]
```

### Feedback API

```
POST /api/v1/feedback
Body: {
  "query": "Discover 流量下降",
  "qa_id": 42,
  "feedback": "not_relevant",   # or "helpful"
  "top_score": 0.68
}
```

Literal 型別驗證確保 feedback 值只接受合法字串，無效值回 422 Validation Error。

---

## 25. 更新後的 Retrieval 指標基準線（2026-03-02）

### KW Hit Rate 進化史

| 時間點 | KW Hit Rate | 關鍵改變 |
|--------|------------|---------|
| 2026-02-27（baseline） | 54% | 僅完整匹配 |
| 2026-02-27（Fuzzy 匹配後） | 78% | 雙向子字串匹配 |
| 2026-03-02（baseline，無 enrichment） | 70.4%* | golden set 從 307 → 20 筆重評 |
| 2026-03-02（make enrich 後） | **79.67%** | synonym expansion + freshness |

*20 筆 golden set（eval/golden_retrieval.json）評分方式與 307 筆不同，數值不可直接比較。

### 完整指標現況

| 指標 | 最新數值 | 目標 | 狀態 |
|------|---------|------|------|
| KW Hit Rate（synonym） | **79.67%** | ≥ 85% | 差 5.33pp |
| freshness_rank_quality | **1.0** | ≥ 0.9 | ✅ |
| synonym_coverage | **1.0** | — | ✅ |
| avg_synonyms / Q&A | 11.09 | — | — |
| avg_freshness | 0.9076 | — | — |

### 下一步（plans/active/phase2-learning-query.md）

- 擴充 synonym_dict 覆蓋率，目標 KW Hit Rate ≥ 85%（差 5.33pp）
- 2026-03-16 後執行 `make enrich`（積累 14 天含 top_score 的 access log）
- E2-3 `analyze-access`：識別 Top 20 失敗查詢（前置：usage_aggregator.py）

---
