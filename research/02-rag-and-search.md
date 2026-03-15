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
[Retrieval] 把問題轉成 embedding → 在 1,323 筆 Q&A 中找最相關的 5 筆
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

### 本專案 Retrieval 評估基準線（v2.12→v2.24，2026-03-06）

| 指標                | 數值        | 說明                                 | 目標      |
| ------------------- | ----------- | ------------------------------------ | --------- |
| Hit Rate            | **100%** ✅ | top-5 中有正確結果（20 cases）        | ≥ 90%     |
| MRR                 | **0.88**    | 第一筆正確結果的排名倒數（越高越好） | ≥ 0.85 ✅ |
| Precision@K         | **76%**     | top-K 中有幾個是 relevant             | ≥ 80%     |
| Recall@K            | **77.5%**   | 正確結果有多少被 top-K 涵蓋           | ≥ 80%     |
| NDCG@K              | **0.72**    | 排名加權的累積相關度（v2.13 實作）    | ≥ 0.78    |
| F1 Score            | **0.74**    | Precision/Recall 調和平均             | ≥ 0.78    |

> v2.24 資料層改為 Supabase pgvector，搜尋品質維持不變（pgvector over-retrieve → TS re-rank）。

### Retrieval Data Dimensions 與 runtime rerank（2026-03-15）

v2.24 之後，retrieval 問題不再只是「找不找得到」，而是「top-k 純度不足、dual-label coverage 不足、booster 汙染 top-k」。

因此目前 runtime search 會把 QA item 視為多維度檢索單位，而不是只看單一 `category`：

- `primary_category` + `categories`：支援 single-label / dual-label coverage
- `intent_labels`：區分 diagnosis / implementation / measurement / reporting 等 query intent
- `scenario_tags`：區分 discover / google-news / author-page / ga4-attribution 等場景
- `serving_tier`：將 corpus 區分為 `canonical` / `supporting` / `booster`
- `retrieval_phrases` / `retrieval_surface_text`：提供更適合 runtime scoring 的 retrieval surface

### Retrieval metadata inference rules

`scripts/enrich_qa.py` 目前以規則式 backfill 為主，不是人工逐筆標註：

- `intent_labels`：掃描 normalized text 中的意圖關鍵詞，例如「異常 / 下滑 / 原因」映到 `diagnosis`，「如何 / 修正 / 設定」映到 `implementation`
- `scenario_tags`：掃描場景詞，例如 `discover`、`google news`、`/user`、`ga4 attribution`
- `categories`：保留原始 `category` 為 `primary_category`，再用 `CATEGORY_HINTS` 補第二、第三分類
- `backfill_confidence`：命中 3 個以上 category 記為 `high`、2 個記為 `medium`、其餘記為 `low`
- `serving_tier`：若 manual curation metadata 含 `booster` 則標為 `booster`；若 confidence 低則降為 `supporting`；其餘為 `canonical`

因此 retrieval metadata 是「高覆蓋率、可審計、可逐步人工校正」的中介層，不是假設它一開始就等於完美 taxonomy。

runtime ranking 公式可抽象化為：

```text
final_score
  = freshness_score × (
      semantic_weight × cosine_similarity
      + keyword_boost
      + synonym_bonus
      + metadata_feature_score
    )
```

其中 `metadata_feature_score` 由 phrase overlap、surface overlap、category / intent / scenario overlap、serving tier prior、hard negative penalty 組成。

排序完成後，系統不直接取 top-k，而是先 over-retrieve，再做 diversity rerank：

- duplicate question penalty
- category diversity bonus
- intent diversity bonus

這讓 top-1 仍追求最相關單筆，但 top-k 會刻意補第二面向，而不是塞滿近似答案。

### Retrieval Data Dimensions 離線成效（40 golden cases）

| 指標 | Baseline | Phase 4 |
|------|----------|---------|
| Precision@K | 0.58 | 0.85 |
| Boosterless Precision@K | — | 0.83 |
| Dual Category Recall@K | — | 1.00 |
| Multi-label F1@K | — | 0.97 |
| Canonical Top-1 Rate | — | 0.37 |
| MRR | 0.92 | 0.99 |

這 5 個新增 case 主要來自 Ahrefs 的 AI Search / AI Overviews 研究，因此這組數字代表的不只是一般 SEO query 的穩定度，也包含較高成熟度、較偏策略層問題的 retrieval 表現。

### 知識庫規模成長歷程

```
QA 數量
1323 ┤ ████████████████████████████████████ (2026-03-06 Supabase pgvector ← 現行)
 655 ┤ ████████████████████████   (2026-03-01 去重後 v2.0 最終版)
 670 ┤ █████████████████████████  (2026-03-01 防幻覺規則重跑)
 725 ┤ ██████████████████████████ (2026-02-28 初版萃取)
     └────────────────────────────────────────────────────
      2026-02-28       2026-03-01              2026-03-05
```

| 日期       | 事件               | QA 數量 | 說明                             |
| ---------- | ------------------ | ------- | -------------------------------- |
| 2026-02-28 | 初版萃取           | 725     | Step 2 首次全量萃取（87 場會議） |
| 2026-02-28 | 去重後             | 725     | Step 3 初版（v1.0）              |
| 2026-03-01 | 防幻覺規則重跑     | 670     | v2.0 重跑，新規則過濾低品質萃取  |
| 2026-03-01 | 去重後             | **655** | v2.0 最終版（+ 12 Google Cases） |
| 2026-03-05 | 多來源擴充            | 1,317     | v2.12：Notion 584 + Medium 505 + iThome 185 + Google Cases 43 |
| 2026-03-06 | Supabase pgvector（**現行**）| **1,323** | v2.24：6 筆缺 embedding 補齊 + pgvector 遷移 |

### KW Hit Rate 完整歷程

```
KW Hit Rate (%)
 85% ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ 目標線
 80% ┤                               ╭── 79.7%（enrichment）
 78% ┤         ▲── 78%（fuzzy match 修復）
 74% ┤                        ████  74%（v2.0 CJK+synonym）
 65% ┤                        ▼ 65%（v2.0 回歸，重新萃取導致）
 54% ┤ ████ 54%（初始基準，TypeB diagnosis）
     └────────────────────────────────────────────────────
      2026-02-27 基準    v2.0 重跑          enrichment 後
```

| 時間點                   | KW Hit Rate | 事件                                     |
| ------------------------ | ----------- | ---------------------------------------- |
| 2026-02-27 初始基準      | 54%         | TypeB 診斷前，exact string miss 導致低估 |
| 2026-02-27 修復後        | **78%**     | Fuzzy 子字串雙向匹配（TypeB 修復）       |
| 2026-03-01 v2.0 回歸     | 65%         | 知識庫重跑後舊 eval 邏輯不相容（-13pp）  |
| 2026-03-02 CJK+synonym   | **74%**     | CJK n-gram + synonym 展開（+9pp 回升）   |
| 2026-03-02 enrichment 後 | **79.67%**  | `make enrich` 同義詞全覆蓋（+5.67pp）    |
| **目標**                 | **≥ 85%**   | 透過擴充 `/api/v1/synonyms` 詞條達成     |

KW Hit Rate 完整修復過程見第 18 節 TypeA/TypeB 診斷與 CJK N-gram 章節。

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
- 目前 4 個來源（Notion / Medium / iThome / Google Cases）均自建 fetcher → 繼續自建擴充

---

## 18. Retrieval 指標說明與 Cross-encoder Reranking

### Retrieval 評估指標詳解

| 指標                                              | 計算方式                                 | 直覺理解                             | 本專案基準線          |
| ------------------------------------------------- | ---------------------------------------- | ------------------------------------ | --------------------- |
| **MRR**（Mean Reciprocal Rank）                   | 第一筆正確結果排名的倒數取平均           | 第 1 筆正確 = 1.0；第 2 筆正確 = 0.5 | **0.88** ✅           |
| **NDCG**（Normalized Discounted Cumulative Gain） | 考慮排名位置的累積相關度，越靠前越值錢   | 比 MRR 更細緻                        | **0.72**（v2.13 實作）|
| **Hit Rate**（Recall@K）                          | top-K 結果中有沒有包含正確答案           | Hit@5 = 前 5 筆有沒有                | **100%** ✅           |
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

### Reciprocal Rank Fusion（RRF）— 未來改進方向

目前本專案用線性加權混合 semantic score + keyword boost：

```python
final_score = semantic_weight * cosine_sim + keyword_boost
```

**Cormack et al.（2009, SIGIR）提出的 RRF 公式**，對 score scale 不敏感、更 robust：

```
RRF(d) = Σ 1/(k + rank_i(d))
```

其中 `k=60`（業界預設），`rank_i(d)` 是文件 d 在第 i 個排序器的排名。

**優勢**：不需要調整權重參數（`SEMANTIC_WEIGHT`, `KW_BOOST`），不同排序器的分數差異大時仍穩定。
**當前決策**：線性加權已驗證可行（KW Hit Rate 54% → 78%），RRF 列為 MEDIUM 優先改進路徑。

---

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

## 本專案 Pipeline Cache 設計（v1.6）

### 為什麼需要 Pipeline Cache？

RAG pipeline 有多個 LLM 呼叫點，每次重跑都重複付費：

- Step 2 萃取：`gpt-5.2` 解讀完整會議記錄（最貴，每份 ~2k tokens）
- Step 3 embedding：`text-embedding-3-small` × 700 筆
- Step 3 classify：`gpt-5-mini` × 700 筆（每 Q&A 一次 classify）
- Step 3 merge：`gpt-5.2` 對相似組做合併判斷
- Step 4 report：`gpt-5.2` 生成完整週報（每週一次）

**Cache 的前提：pipeline 是確定性的 — 相同輸入永遠產生相同輸出。**

### Content-Addressed Cache 原理

```
輸入 → SHA256 → 16 bytes hex → 作為 cache key
```

設計來自 Git（git object storage）和 IPFS：

- 不依賴時間、順序或檔名
- 同一份會議記錄無論何時跑，永遠命中同一個 cache entry
- 不同輸入即使只差一個字，也對應不同 key（無碰撞）

### 本專案 Cache 架構（utils/pipeline_cache.py）

```
output/.cache/
  extraction/
    4a/4a3f...json    ← SHA256 前兩碼作為子目錄（防單目錄爆炸）
    ...
  embedding/
    b2/b2c1...json    ← 每個文字 → embedding 向量 (list[float])
    ...
  classify/
    ...               ← question + "\n\n" + answer → {category, difficulty, evergreen}
  merge/
    ...               ← sorted Q&A pair JSON → merged Q&A
  report/
    ...               ← metrics_tsv + qa_version_id → report Markdown
```

### Cache 整合點與 cache key 設計

| Namespace  | Cache Key                       | Cached Value                                 | 位置                              |
| ---------- | ------------------------------- | -------------------------------------------- | --------------------------------- |
| extraction | 原始 Markdown content           | Q&A pairs list（不含 source）                | `02_extract_qa.py`                |
| embedding  | 單一文字 text                   | `list[float]` 向量                           | `openai_helper.get_embeddings`    |
| classify   | `question + "\n\n" + answer`    | `{category, difficulty, ...}`                | `openai_helper.classify_qa`       |
| merge      | sorted Q&A pairs JSON           | `{question, answer, keywords, source_dates}` | `openai_helper.merge_similar_qas` |
| report     | metrics_summary + QA version ID | `{"report_text": str}`                       | `04_generate_report.py`           |

### 重要設計決策

**extraction cache 不存 source_file/title/date**：這些是派生自 Markdown 路徑的 metadata，不是 LLM 輸出的一部分。命中 cache 後重新套用 enrichment，保持 cache 內容 source-agnostic 且可重用。

**merge cache 不存 merged_from**：`merged_from` 記錄哪些原始 Q&A 被合併，這是 runtime 的 structural info（index 關係），不是 LLM 決定的語意內容。LLM 輸出的是 `{question, answer, keywords}`，這才是可 cache 的。

**report cache key 包含 QA version ID**：報告依賴 Q&A 知識庫版本，相同指標但不同知識庫版本應生成不同報告。`get_latest_version(3)` 取得 Step 3 的版本 ID 作為 key 的一部分。

### Atomic Write 防止 Partial Write 污染

```python
# 先寫 .tmp，再 rename（POSIX 上是 atomic）
tmp.write_text(json.dumps(value))
tmp.replace(path)
```

若 process 中途 crash，`.tmp` 不會被誤讀為有效 cache entry。

### 版本 Registry（utils/pipeline_version.py）

每次 Step 3/4 完成後，呼叫 `record_artifact()` 記錄：

- content hash（16 char）→ 偵測內容變動
- 使用 / 節省的 tokens
- artifacts 路徑（不可變 JSON snapshot）

_`output/.versions/registry.json` 納入 git，step artifacts 本身 gitignored（可從 cache 重建）。_

---

## 20–25. Multi-Layer Context Architecture

> 此主題已拆出至獨立檔案，包含術語定義、同義詞擴展、時效性衰減、enrichment pipeline、Learning Store、指標基準線等完整內容。

**詳見：[10-multi-layer-context.md](./10-multi-layer-context.md)**

---

## 26. RAG 迭代改進框架（v2.12，2026-03-05）

> 參考：[Anthropic Cookbook - Contextual Embeddings Guide](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
> 四層改進方向：Synonym 擴充 → Contextual Embeddings → Re-ranking → Context Relevance 評估

### 四層架構對應本專案實作

| Level | 名稱                  | 核心概念                                           | 本專案實作                  | 預期效益           |
| ----- | --------------------- | -------------------------------------------------- | --------------------------- | ------------------ |
| 1     | Hybrid Search         | 語意 + 關鍵字 + 同義詞 + 時效                      | ✅ v1.x 已完成              | 基準線建立         |
| 2     | Contextual Embeddings | embed `context + question` 取代單純 `question`     | ✅ v2.11 腳本就緒（需生成） | Pass@10 +5pp       |
| 3     | Re-ranking            | over-retrieve → LLM 重排 → top-K                   | ✅ v2.11 整合               | Precision +3pp     |
| 4     | **Context Relevance** | **LLM judge 評估 retrieved contexts 的語意相關性** | **✅ v2.12 整合**           | **端到端品質驗證** |

### Phase 1：Synonym Dict 擴充

**目標**：KW Hit Rate 73% → 78%+（中間目標）→ ≥ 85%（最終目標）

三層 synonym 合併（優先序從低到高）：

```
METRIC_QUERY_MAP（指標術語）
< _SUPPLEMENTAL_SYNONYMS（補充術語，v2.11 新增 31 項共 214 詞條）
< custom JSON（/api/v1/synonyms 管理）
```

**v2.11 新增術語類別**：

- 技術面：技術SEO、頁面速度、行動裝置、重複內容、404、分頁
- 關鍵字面：長尾關鍵字、品牌字、非品牌字、排名
- 頁面元素：標題標籤、描述標籤、內部連結、錨點文字
- 使用者行為：跳出率、停留時間、流量、轉換率、搜尋意圖
- GSC 指標：Impressions、Position、Clicks

### Phase 2：Contextual Embeddings

**核心概念**（Anthropic Cookbook）：

> 不只 embed `question`，改為 embed `situating_context + question`

**Situating context 格式**：

```
此 Q&A 來自 {collection}，主題分類為 {category}。核心概念：{key_concepts}。
```

**實作設計**（`scripts/_generate_context.py`）：

- 模型：`claude-haiku-4-5-20251001`（成本低）
- 輸入：優先 `output/qa_enriched.json`，不存在則 fallback `output/qa_final.json`（**1317 items**）
- 輸出：`output/qa_context.json`（`{ "1": context_string, ..., "1317": context_string }`，key 為 str(id)）
- 增量式：預設跳過已存在，`--force` 重跑
- 成本估算：1317 × 200 tokens ≈ $0.10（有 prompt caching 時更低）
- **✅ 已完成**（2026-03-06，1317 筆全部生成）

**使用方式**：

```bash
python scripts/_generate_context.py --limit 10   # 先測試 10 筆
python scripts/_generate_context.py              # 全量生成
```

**config 整合**（`api/src/config.ts`）：

```typescript
ANTHROPIC_API_KEY: z.string().default(""),
CONTEXT_EMBEDDING_WEIGHT: z.coerce.number().min(0).max(1).default(0.6),
```

### Phase 3：Re-ranking（`api/src/services/reranker.ts`）

**策略**：Over-retrieve（K×3）→ Claude haiku 重排 → 回傳 top-K

**核心實作模式**：

```typescript
// 1. Over-retrieve
const retrieveK = config.ANTHROPIC_API_KEY
  ? config.CHAT_CONTEXT_K * 3
  : config.CHAT_CONTEXT_K;
const hits = store.hybridSearch(query, queryVec, retrieveK);

// 2. Rerank (dynamic import — SDK absent = no crash)
const { rerank } = await import("./reranker.js");
const finalHits = config.ANTHROPIC_API_KEY
  ? await rerank(query, hits, config.CHAT_CONTEXT_K)
  : hits.slice(0, config.CHAT_CONTEXT_K);
```

**Fallback 策略**（任一條件觸發即 skip reranker）：

- `ANTHROPIC_API_KEY` 未設定
- `@anthropic-ai/sdk` 未安裝（dynamic import catch）
- Claude API 呼叫失敗（try/catch）

**Prompt 設計（XML structured input + JSON output）**：

```
候選：<candidates><candidate stable_id="xxx"><question>...</question><initial_score>0.8</initial_score></candidate>...</candidates>
要求：輸出 JSON 陣列：[{"stable_id": "xxx", "rank": 1, "reason": "最相關"}]
```

**JSON 解析防禦**：

```typescript
const jsonMatch = text.match(/\[[\s\S]*\]/); // 處理 Claude 有時加 backtick 的情況
```

**設計決策**：
| 決策 | 選擇 | 理由 |
|------|------|------|
| Over-retrieve factor | 3× | 給 reranker 足夠候選、不過度增加 latency |
| Reranker model | claude-haiku-4-5 | 本地可用、成本低 |
| Dynamic import | `import().catch(() => null)` | SDK 可選依賴，不強制安裝 |
| Whitelist check | ranked id 必須在 candidates 中 | 防 LLM 幻覺 id |

**Eval 整合及評估結果（`POST /api/v1/eval/reranking`，v2.12）**：

```bash
# 評估 reranker 效果（使用 eval-semantic CLI）
cd api && npx tsx scripts/eval-semantic.ts            # 對比三種模式
cd api && npx tsx scripts/eval-semantic.ts --top-k 3 # 改變 top-K 參數
```

**三種模式評估**（20 golden cases，v2.12 實驗結果）：

| 模式 | Precision | Recall | F1 | Hit Rate | MRR | 說明 |
|------|-----------|--------|-----|----------|-----|------|
| **Keyword（baseline）** | 0.810 | 0.800 | 0.768 | 1.0 | 0.938 | Python keyword 手動實驗 baseline（非 TS eval-semantic.ts）|
| **Keyword + Claude Rerank** | **0.950** | **0.825** | **0.861** | 1.0 | **1.0** | Claude Code 直接語意選取 top-5 |
| **Delta** | **+0.140** | **+0.025** | **+0.093** | ±0.0 | **+0.062** | Precision +14pp，MRR 達到完美 |

> **Baseline 版本說明**：Precision 0.810 為 Python keyword 手動實驗結果；TypeScript `eval-semantic.ts` keyword mode 為 0.700（不同 BM25 實作）；`_eval_laminar.py` Python keyword 為 0.76。

**主要發現**：
- **Precision 大幅提升（+14%）**：Reranker 有效過濾噪音（keyword 命中但語意不相關的結果）
- **MRR 達到 1.0**：第一筆結果 100% 是期望分類，排序順序最優
- **Recall 小幅提升（+2.5%）**：受 over-retrieve pool 限制（某些期望分類不在 top-15 pool 中），無法進一步改善
- **Hit Rate 持平（1.0）**：所有 20 個查詢都至少命中一筆正確分類，keyword 搜尋本身無失敗

**Reranker 的語意判斷能力**：Claude haiku-4-5 作為 judge 輸入 query + candidates，輸出語意相關度排序。相比純 keyword 匹配，reranker 能捕捉：
- 語意等價但措詞不同的結果（如 "CTR" vs "點擊率"）
- Discover 專屬情境（keyword 命中「流量」但非 Discover 導向的結果被降權）
- 相關性梯度（部分相關 vs 完全相關，而非二元 relevant/irrelevant）

### Maturity-Aware Ranking（v3.4）

**策略**：Post-retrieve 乘法 boost，符合使用者成熟度的 QA 項目獲得 1.15× 分數加成。

**核心實作**（`api/src/utils/maturity.ts`）：

```typescript
// opt-in：只在 maturity_level param 存在時生效
const boostedHits = applyMaturityBoost(filteredHits, maturityLevel);
// maturityLevel = null → 原始排序不變（同一 reference，零開銷）
// maturityLevel = "L2" → item.maturity_relevance === "L2" 的 score × 1.15，重排
```

**設計決策**：
- **opt-in 而非 auto-detect**：Lambda 上無 meeting-prep 檔案，不適合自動偵測
- **post-retrieve 而非 pre-filter**：不排除其他等級的 QA，僅調整排序
- **乘法 boost 而非加法**：與 synonym_boost / freshness_decay 相容，高分項目被提升幅度更大
- **搜尋路徑**：`routes/search.ts` 呼叫 `applyMaturityBoost()` post-retrieve reranking
- **聊天路徑**：`rag-chat.ts` 呼叫 `buildMaturityContext()` 注入 system prompt（不做 reranking，而是調整回答深度）

**與現有 boost 的交互**：

| Boost 類型 | 實作位置 | 應用階段 |
|-----------|---------|---------|
| Keyword boost | `SearchEngine` / `SupabaseQAStore` | Retrieve 時 |
| Synonym boost | `SearchEngine._synonym_boost_vec` | Retrieve 時 |
| Freshness decay | `SearchEngine._freshness_vec` | Retrieve 時 |
| Claude rerank | `reranker.ts` | Post-retrieve |
| **Maturity boost** | `maturity.ts` | **Post-rerank**（最後一層） |

### Synonym Expansion 評估維度（v2.13）

**評估問題**：Synonym 擴充後，搜尋品質改善了多少？

本專案引入兩個 Layer 3 指標（`_eval_laminar.py --group retrieval-enhancement`）：

| 指標 | 定義 | 測量意義 |
|------|------|---------|
| `synonym_coverage` | `expected_keywords` 中有 synonym 對應的比例 | 詞典覆蓋密度——若 query 的 expected keywords 都沒有 synonym，擴充無效 |
| `kw_hit_rate_with_synonyms` | 同義詞展開後的 hit rate | 展開後搜尋是否實際改善命中（與 baseline hit_rate 對比）|

**Synonym Expansion 機制**：

```python
# 雙向展開：術語出現在 query → 加入所有同義詞
for term, syn_list in synonyms.items():
    if term.lower() in query_lower:
        expanded_terms.update(syn.lower() for syn in syn_list)
    for syn in syn_list:
        if syn.lower() in query_lower:
            expanded_terms.add(term.lower())  # 反向：同義詞 → 術語
            expanded_terms.update(s.lower() for s in syn_list)
```

**已知基準線**（v2.11，`qa_enriched.json`）：

| 指標 | 值 | 說明 |
|------|----|----|
| `synonym_coverage` | 100% | qa_enriched 有完整同義詞擴充；新 query 可能低於此值 |
| `kw_hit_rate_with_synonyms` | 79.67% | vs keyword hit_rate 74%（+5.67pp）|

### Phase 4：Context Relevance 評估（`api/src/services/context-relevance.ts`，v2.12）

**目標**：量化 retrieved contexts 對 query 的語意相關程度。補充 Hit Rate / MRR 的二元評估缺口。

**原理**：Claude haiku 作為 LLM judge，輸入 query + retrieved Q&A list，輸出 0–1 連續分數。
無需 ground truth，只需 query + contexts。

```typescript
// 呼叫方式
const result = await contextRelevance(
  query,
  hits.map((h) => h.item),
);
// result = { score: 0.82, reason: "...", per_context: [{ id, score }, ...] }
```

**與 Phase 1–3 的關係**：

| 優化 Phase                     | 動作             | 評估方式                                        |
| ------------------------------ | ---------------- | ----------------------------------------------- |
| Phase 1：Synonym 擴充          | 增加查詢覆蓋率   | KW Hit Rate（keyword overlap）                  |
| Phase 2：Contextual Embeddings | 強化語意向量     | 尚無獨立指標（混入 hybrid score）               |
| Phase 3：Re-ranking            | 改善排序順序     | `POST /eval/reranking`（rank order delta）      |
| **Phase 4：Context Relevance** | **評估整體品質** | **`POST /eval/context-relevance`（0–1 score）** |
| **Phase 5：Agentic RAG** | **LLM 自主多輪搜尋** | Agent mode `POST /chat`（tool_calls_count, agent_turns） |

Context Relevance 作為**端到端指標**，可驗證 Phase 1–3 的累積效果。
預期：`context_relevance_score > kw_hit_rate`（語意評估應高於純 keyword 判斷）。

**安全機制**：

- `escapeXml()` 防 XML prompt injection（`<>&"'`）
- `top_k` schema 上限 30（防 runaway API cost）
- ANTHROPIC_API_KEY 缺失時自動降級為 freshness_score heuristic

**API 端點**：

```bash
POST /api/v1/eval/context-relevance
{ "query": "Discover 流量下降", "top_k": 5 }
# 回傳: { score, reason, per_context[{ id, score }], query, total_contexts }
```

---

### Phase 5：Agentic RAG（`api/src/agent/`，v2.28）

Phase 1–4 的 RAG 是**單輪固定流程**：embedding → hybrid search → GPT completion。LLM 無法決定：
- 要不要搜尋、搜什麼關鍵字
- 搜到的結果夠不夠、要不要再搜一次
- 是否需要查詢特定 Q&A 的完整內容

**Agentic RAG = LLM 自主決定 tool calling，多輪收集資訊後回答**。

```
使用者問題
     ↓
LLM 分析 → 決定呼叫哪個 tool
     ↓
┌── Agent Loop（最多 5 輪）──────────────────────┐
│                                                 │
│  LLM 選擇 tool：                                │
│  ├─ search_knowledge_base（語意搜尋，含分類篩選）│
│  ├─ get_qa_detail（取得完整 Q&A 內容）          │
│  ├─ list_categories（了解知識庫覆蓋範圍）        │
│  └─ get_stats（知識庫統計）                      │
│                                                 │
│  LLM 評估 → 資訊充足？                          │
│  ├─ 是 → finish_reason="stop"，跳出 loop       │
│  └─ 否 → 再呼叫 tool（換關鍵字/換分類/查詳情）  │
│                                                 │
│  安全防護：                                      │
│  ├─ ALLOWED_TOOLS runtime whitelist             │
│  ├─ JSON.parse guard + Zod validation           │
│  ├─ Loop detection（連續相同 tool call 中斷）    │
│  └─ Timeout（預設 90s）                          │
│                                                 │
└─────────────────────────────────────────────────┘
     ↓
LLM 生成最終回答（含 sources 引用）
```

**與 Phase 1–4 的差異**：

| | Phase 1–4（Single-pass RAG） | Phase 5（Agentic RAG） |
|---|---|---|
| 搜尋次數 | 固定 1 次 | LLM 自主決定 1–N 次 |
| 關鍵字選擇 | 直接用使用者問題 | LLM 拆解、重組 |
| 結果評估 | 無（搜到就回答） | LLM 判斷是否充足 |
| Tool 種類 | 只有 search | 4 種 tools |
| 回應模式 | `mode: "full"` | `mode: "agent"` |

**Feature Flag**：`AGENT_ENABLED=auto|true|false`（auto = 有 OpenAI key 就啟用）。

**架構設計**：

- `agent/types.ts` — `AgentDeps` interface（Dependency Injection，解耦 qaStore）
- `agent/tool-definitions.ts` — 4 tool 的 Zod schema + OpenAI function calling format
- `agent/tool-executor.ts` — Tool dispatch + validation + 15s timeout per tool
- `agent/agent-loop.ts` — while-loop + 4 終止條件（stop / max_turns / timeout / loop_detection）
- `agent/agent-deps.ts` — qaStore → AgentDeps 橋接

---
