# RAG 與混合搜尋

> 屬於 [research/](./README.md)。涵蓋 RAG 架構、Hybrid Search、框架比較、Retrieval 指標。

---

## 8. RAG：讓 AI 查資料再回答

### 核心問題

AI 不知道你的私人資料（會議紀錄、客戶資料）。
直接問 AI → AI 只能靠通用知識回答，可能不準確。

### RAG 解決方案

**R**etrieval **A**ugmented **G**eneration = 先搜尋，再生成

```
[問題] 「上次開會說 Discover 流量下降，怎麼解決？」
   ↓
[Retrieval] 把問題轉成 embedding → 在 703 筆 Q&A 中找最相關的 5 筆
   ↓
[Augmented] 把這 5 筆 Q&A 塞進 prompt：
   「根據以下 SEO 知識：
   Q: Discover 流量下降原因？ A: 可能是內容品質、AMP...
   Q: AMP 焦點新聞如何維持？ A: ...
   [3 筆省略]
   請根據以上知識，分析本週 Discover 下降 20% 的情況」
   ↓
[Generation] AI 有了具體上下文，回答更準確、有依據
```

### 比喻：開卷考試

- ❌ 無 RAG = 閉卷考試（AI 只能靠記憶）
- ✅ 有 RAG = 開卷考試（AI 可以查你的筆記本）

### 本專案 Step 4 流程

```python
# 1. 讀取本週 Google Sheets 指標
metrics = load_google_sheets_tsv("metrics.tsv")

# 2. 偵測異常（月趨勢超出閾值）
anomalies = detect_anomalies(metrics)
# → ["有效頁面數 -5%", "AMP Article -114%", "CTR -8%"]

# 3. 對每個異常，做語意搜尋
for anomaly in anomalies:
    query_vector = embed(anomaly)   # 轉成 embedding
    top5_qa = semantic_search(query_vector, qa_embeddings, top_k=5)

    # 4. 組裝 prompt（RAG 的核心）
    prompt = f"""
    本週異常：{anomaly}

    相關知識：
    {format_qa_list(top5_qa)}

    請分析原因並給出具體建議。
    """

    # 5. 生成週報段落
    report_section = gpt52(prompt)
```

---

## 9. Hybrid Search：語意 + 關鍵字混合搜尋

### 純語意搜尋的弱點

語意搜尋有時會漏掉「精確術語」：

```
查詢：「WAF 封鎖 Googlebot」
語意搜尋可能找到：「伺服器設定問題」（語意相近但沒有 WAF）
    → 但 WAF 是關鍵詞，漏掉就答非所問
```

### Hybrid Search = 語意分數 + 關鍵字加分

```python
# Step 1：計算語意相似度分數
scores = cosine_similarity(query_vector, all_qa_vectors)

# Step 2：關鍵字加分（Q&A 的 keywords 出現在查詢中）
for i, qa in enumerate(qa_pairs):
    hits = sum(1 for kw in qa["keywords"] if kw.lower() in query.lower())
    if hits > 0:
        scores[i] += 0.08 * min(hits, 3)   # 最多加 0.24 分

# Step 3：取分數最高的前 5 筆
top_indices = np.argsort(scores)[::-1][:5]
retrieved = [qa_pairs[i] for i in top_indices]
```

### 本專案 Retrieval 評估基準線

| 指標                | 數值       | 說明                                 |
| ------------------- | ---------- | ------------------------------------ |
| KW Hit Rate         | **78%** ✅ | 查詢的關鍵字有多少被 top-5 覆蓋      |
| Category Hit Rate   | 70%        | top-5 中有沒有正確分類的 Q&A         |
| MRR                 | 0.75       | 第一筆正確結果的排名倒數（越高越好） |
| LLM Top-1 Precision | 100%       | top-1 結果是否真的和查詢相關         |

KW Hit Rate 54% → **78%** 已解決，做法見第 18 節 TypeA/TypeB 診斷。

### 當前 Hybrid Search 實作（雙向 keyword boost）

```python
# Step 1：語意分數
scores = cosine_similarity(query_vector, all_qa_vectors)

# Step 2：雙向 keyword boost（四種命中方式）
query_lower = query.lower()
query_tokens = {t for t in query_lower.split() if len(t) >= 2}

for i, qa in enumerate(qa_pairs):
    total_hits = 0.0
    for kw in qa["keywords"]:
        kw_lower = kw.lower()
        kw_tokens = {t for t in kw_lower.split() if len(t) >= 2}
        if kw_lower in query_lower:                              # 正向完整
            total_hits += 1
        elif any(t in kw_lower for t in query_tokens):          # query token in kw
            total_hits += 1
        elif any(t in query_lower for t in kw_tokens):          # kw token in query
            total_hits += 1
        elif len(kw_lower) >= 2 and kw_lower[:2] in query_lower: # 中文 bigram 弱命中
            total_hits += 0.5
    if total_hits > 0:
        scores[i] += 0.10 * min(total_hits, 3)

# Step 3：取分數最高的前 5 筆
top_indices = np.argsort(scores)[::-1][:5]
retrieved = [qa_pairs[i] for i in top_indices]
```

---

---

## 17. RAG 框架比較與整合策略

### 主流框架比較

| 框架                      | 定位         | 優點                               | 缺點               |
| ------------------------- | ------------ | ---------------------------------- | ------------------ |
| **自建 pipeline**（現用） | 輕量自定義   | 低依賴、高彈性                     | 需要自己維護       |
| LangChain                 | 工作流編排   | 生態豐富、鏈式組合                 | 複雜、版本頻繁變動 |
| LlamaIndex                | 文件檢索優化 | Retrieval 提升 35%、支援多種資料源 | 較重               |
| txtai                     | 輕量無依賴   | 嵌入式、極簡                       | 功能受限           |

### 現階段決策：不引入外部框架

**原因**：現有 pipeline 已驗證、穩定，引入框架的收益不值得增加的複雜度。

**未來整合時機**：

- 若需要支援 PDF、資料庫、圖片等多來源 → 考慮 LlamaIndex
- 若需要複雜的多步驟 AI 工作流 → 考慮 LangChain
- 目前只有 Notion Markdown 作為資料源 → 繼續自建

---

## 18. Retrieval 指標說明與 Cross-encoder Reranking

### Retrieval 評估指標詳解

| 指標                                              | 計算方式                                 | 直覺理解                             | 本專案基準線          |
| ------------------------------------------------- | ---------------------------------------- | ------------------------------------ | --------------------- |
| **MRR**（Mean Reciprocal Rank）                   | 第一筆正確結果排名的倒數取平均           | 第 1 筆正確 = 1.0；第 2 筆正確 = 0.5 | 0.79 ✅               |
| **NDCG**（Normalized Discounted Cumulative Gain） | 考慮排名位置的累積相關度，越靠前越值錢   | 比 MRR 更細緻                        | 未實作                |
| **Hit Rate**（Recall@K）                          | top-K 結果中有沒有包含正確答案           | Hit@5 = 前 5 筆有沒有                | KW 54% / Category 75% |
| **LLM Top-1 Precision**                           | top-1 結果是否與查詢真實相關（LLM 判斷） | 最重要的第一筆準不準                 | 100% ✅               |

### KW Hit Rate 54% → 78%：TypeA/TypeB 診斷（2026-02-27 解決）

**診斷第一原則：指標低 ≠ 排序差**

KW Hit Rate 低時，需先分清兩種失敗類型，再決定要改什麼：

| 類型  | 定義                                                    | 修法             |
| ----- | ------------------------------------------------------- | ---------------- |
| TypeA | 正確文件在資料庫中根本不存在                            | 補資料、重跑萃取 |
| TypeB | 正確文件已排在前面，但評估指標過嚴（exact string miss） | 修評估指標       |

**本專案實際診斷結果（`--debug-retrieval`）**：13/13 失敗全是 TypeB。
正確 Q&A 已在第 1 名，但 `"CTR"` 不等於 `"點擊率"`、`"探索流量"` 不等於 `"流量"`。

**解法：Fuzzy 子字串雙向匹配**

```python
# BEFORE（exact match，54%）：
kw_hits = sum(1 for kw in expected_kws if kw in all_retrieved_kws)

# AFTER（bidirectional substring，78%）：
def _kw_fuzzy_hit(exp_kw, retrieved_kws):
    kw = exp_kw.lower()
    # "流量" in "探索流量" ✅  |  len("ga") >= 2, "ga" in "google analytics" ✅
    return any(kw in rkw or (len(rkw) >= 2 and rkw in kw) for rkw in retrieved_kws)
```

**注意**：這修的是「評估指標」，不是排序演算法本身。

### LLM Reranking 實驗（`--eval-reranking`，待驗證）

若 TypeA 比例高（資料庫覆蓋不夠），可考慮 LLM reranking 補強排序：

```bash
# 實驗性旗標，不影響正式 pipeline
python scripts/05_evaluate.py --eval-retrieval --eval-reranking
```

使用 gpt-5-nano 對 bi-encoder top-20 做重排序，約 20 cases × 650 tokens，成本極低。

---

## 19. SearchEngine 模組化（utils/search_engine.py）

> v1.5 新增：`utils/search_engine.py` — 將 Hybrid Search 邏輯從 `04_generate_report.py` 和 `app/core/store.py` 統一抽出。

### 模組架構

```
utils/search_engine.py
  ├── compute_keyword_boost()   ← 模組級函式（可直接 import，不需實例化）
  └── SearchEngine              ← 封裝完整搜尋流程
        ├── __init__(qa_pairs, qa_embeddings, semantic_weight)
        ├── search(query, query_embedding, top_k, category, min_score)
        ├── search_multi(queries, query_embeddings, top_k_per_query, total_max)
        └── _keyword_boost_matrix(queries)  → delegates to compute_keyword_boost
```

### 模組級函式：`compute_keyword_boost()`

**設計原則**：先把核心演算法暴露為模組級函式，再讓 class method 委派。這樣 script 可以直接 import 函式而不需要實例化整個類別。

```python
from utils.search_engine import compute_keyword_boost

# 四向雙邊關鍵字匹配（返回 shape=(n_queries, n_qa) 的 boost 矩陣）
boost_matrix = compute_keyword_boost(queries, qa_pairs)
# queries: list[str]
# qa_pairs: list[dict]  — 每個 dict 有 "keywords" 欄位
# 返回: np.ndarray shape=(n_queries, n_qa)，float32
```

四種命中方式（優先序）：

1. `kw_lower in query_lower` — 關鍵字完整出現在 query（正向）
2. `any(t in kw_lower for t in query_tokens)` — query 的 token 出現在 kw
3. `any(t in query_lower for t in kw_tokens)` — kw 的 token 出現在 query
4. `kw_lower[:2] in query_lower` — 中文 bigram 弱命中（給 `KW_BOOST_PARTIAL` 分）

### `SEMANTIC_WEIGHT` vs `KW_BOOST` 的設計區別

| 參數                  | 位置        | 用途                                                      |
| --------------------- | ----------- | --------------------------------------------------------- |
| `SEMANTIC_WEIGHT=0.7` | `config.py` | 語意分數的權重係數（最終分 = 語意×0.7 + kw_boost）        |
| `KEYWORD_WEIGHT=0.3`  | `config.py` | 未來保留：可用於混合排序加權                              |
| `KW_BOOST=0.10`       | `config.py` | 每次關鍵字命中加的固定分數（上限 `KW_BOOST_MAX_HITS` 次） |

> `KW_BOOST` 是加法（加到語意分上），`SEMANTIC_WEIGHT` 是乘法（縮放語意分）。
> 兩者獨立控制，不重複計算。

### `search_multi()`：週報多 query 搜尋

```python
# 04_generate_report.py 用此方式聚合多個 query 的結果
engine = SearchEngine(qa_dicts, qa_embeddings)
results = engine.search_multi(
    queries=["Core Web Vitals 如何影響排名", "GA4 事件追蹤設定"],
    query_embeddings=[emb1, emb2],
    top_k_per_query=3,
    total_max=15,
)
# 返回去重後的 QA 清單（同一 QA 不重複，按最高分排序）
```

### app/core/store.py 整合

```python
from utils.search_engine import SearchEngine

@dataclass
class QAStore:
    _engine: Optional[SearchEngine] = field(default=None, repr=False)

    def load(self, ...):
        # ... 載入 items 後 ...
        qa_dicts = [{"question": i.question, "answer": i.answer,
                     "keywords": i.keywords, "category": i.category,
                     "id": i.id} for i in self.items]
        self._engine = SearchEngine(qa_dicts, embeddings_raw)

    def hybrid_search(self, query, query_embedding, top_k=5, ...):
        """委派給 SearchEngine，返回值映射回 QAItem（by id）。"""
```

### 使用 SearchEngine 的地方

| 模組                            | 使用方式                                                            |
| ------------------------------- | ------------------------------------------------------------------- |
| `app/core/store.py`             | `QAStore.hybrid_search()` → delegates to `SearchEngine.search()`    |
| `scripts/04_generate_report.py` | `_compute_keyword_boost()` → delegates to `compute_keyword_boost()` |
| `scripts/05_evaluate.py`        | `--eval-retrieval` 模式建立暫時 `SearchEngine` 實例做 MRR 評估      |

---
