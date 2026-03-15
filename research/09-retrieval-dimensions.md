# Retrieval Dimensions 設計紀錄

> 補充 [06-project-architecture.md](./06-project-architecture.md) 中 retrieval metadata 與 Supabase schema fallback 的細節。重點不是再講一次 hybrid search，而是說清楚「除了 embedding similarity 之外，系統還用哪些欄位把結果排得更像真實 SEO 問題」。

---

## 1. 問題定義

只靠 `question`、`answer`、`keywords` 與 cosine similarity，對這個 SEO 知識庫有兩個限制：

1. 很多 query 其實帶有情境，例如 Discover、GA4 attribution、author page、FAQ rich result。
2. 同一個主題底下，還存在 intent、內容粒度、證據範圍、服務層級等差異，單靠向量很難穩定分開。

因此 v3.4 前後新增了一組 retrieval metadata 欄位，讓 re-rank 可以讀到「題目適不適合這個 query」，而不是只讀到「文字像不像」。

---

## 2. Schema：`010_retrieval_metadata_columns.sql`

`supabase/migrations/010_retrieval_metadata_columns.sql` 為 `qa_items` 增加以下欄位：

- `primary_category`
- `categories`
- `intent_labels`
- `scenario_tags`
- `serving_tier`
- `retrieval_phrases`
- `retrieval_surface_text`
- `content_granularity`
- `evidence_scope`
- `booster_target_queries`
- `hard_negative_terms`

同時建立對應 index：

- `primary_category` btree
- `categories` gin
- `intent_labels` gin
- `scenario_tags` gin
- `serving_tier` btree

另外補了一個 `increment_search_hit_count(qa_ids TEXT[])` function，讓命中次數可以在 DB 端累加。

這組欄位的目的，不是把所有 ranking 邏輯塞進 SQL，而是讓 TypeScript API 能在 over-retrieve 之後做更細的 metadata-aware re-rank。

### Migration status（2026-03-15）

截至 2026-03-15，`010_retrieval_metadata_columns.sql` 已經準備完成，但架構文件記錄的 production 現況仍是假設「遠端 schema 可能尚未套用」。也就是說，文件中的 fallback 描述不是歷史殘留，而是目前仍需保留的 runtime 保護。

若要確認實際執行中是否還在 fallback，可直接觀察 API 啟動 log 是否出現：

- `SupabaseQAStore: qa_items is missing extended retrieval columns; falling back to base schema`

只要這行還會出現，就代表 metadata-aware ranking 仍未在 production 完整生效。

---

## 3. Runtime mapping：`api/src/store/supabase-qa-store.ts`

`MatchRow` / `QARow` 會把 extended retrieval columns 一起載入，然後在 `rowToQAItem()` 轉成 runtime 使用的 `QAItem`：

- `primary_category` 預設回退到舊 `category`
- `categories` 預設回退成 `[category]`
- `serving_tier` 預設 `canonical`
- `retrieval_phrases` 預設回退到 `keywords`
- `retrieval_surface_text` 預設用 `question + answer + keywords` 組成
- 缺少的 array 欄位統一回退為空陣列

這層 mapping 很重要，因為它保證：

1. 新舊 schema 都能進到同一個 `QAItem` 介面
2. metadata 缺值時仍有可解釋的 fallback，而不是 `undefined` 到處外漏

---

## 4. Startup schema fallback：extended schema 不是硬依賴

`SupabaseQAStore.load()` 的策略是：

1. 先用 `EXTENDED_SELECT_COLUMNS` 載完整 retrieval metadata
2. 如果第一頁就遇到 `column qa_items.<name> does not exist`
3. 觸發 `isMissingColumnError()`
4. 印出 warning，改成 `BASE_SELECT_COLUMNS` 重試

因此 production 即使還沒套 migration，也不會因為多抓了新欄位而整個 API 啟不來。代價是：

- 基本搜尋仍可用
- 但 metadata-aware ranking 的大部分能力會退化

這是一個刻意的架構取捨：先保 availability，再追 feature parity。

---

## 5. Ranking signal composition：`metadataScore()`

`metadataScore(query, item)` 是 retrieval dimensions 的核心。它把 query 與 item 都投影到幾個可解釋維度，再計算額外分數。

目前主要訊號：

1. `phraseBoost`
   - 對 `retrieval_phrases` 做 phrase-level matching
   - 分數再乘 `2.0`，表示這是最直接的人寫提示

2. `surfaceBoost`
   - query token 與 `retrieval_surface_text` token 的重疊數
   - 每個 token 命中加 `0.03`

3. `categoryBoost`
   - query 先經 `QUERY_CATEGORY_HINTS` 推斷類別，再與 `item.categories` 對齊
   - 每個命中加 `0.08`

4. `intentBoost`
   - query 經 `QUERY_INTENT_HINTS` 推斷是 diagnosis / implementation / measurement / reporting 等
   - 與 `item.intent_labels` 對齊，每個命中加 `0.06`

5. `scenarioBoost`
   - query 經 `QUERY_SCENARIO_HINTS` 推斷特殊場景，如 Discover、FAQ rich result、GA4 attribution
   - 與 `item.scenario_tags` 對齊，每個命中加 `0.05`

6. `exactTermBoost`
   - 直接檢查 query term 是否命中 `retrieval_surface_text`
   - 每個命中加 `0.04`
   - 用來把 `VideoObject`、`WAF`、`ChatGPT` 這類高辨識詞拉回前排，避免只被 broad category signal 稀釋

7. `tierScore`
   - `canonical`：`+0.08`
   - `supporting`：`+0.02`
   - `booster`：若 query 命中 `booster_target_queries` 則 `+0.05`，否則 `-0.08`

8. `hardNegativePenalty`
   - query 命中 `hard_negative_terms` 時 `-0.05`
   - 用來避免某些 booster 被誤套到相近但不該命中的 query

這裡的重點不是某個單一欄位，而是多個弱訊號的組合。它讓 SEO query 的 ranking 更接近「懂領域的人會怎麼挑答案」。

### Re-rank 不是只加分，還會做 query-aware diversity

`api/src/store/search-engine.ts` 與 `api/src/store/supabase-qa-store.ts` 都不是單純把 base score 排序後直接截斷，而是再跑一輪 query-aware rerank：

- 若 candidate 覆蓋了尚未被選中的 query category，額外加分
- 若 candidate 帶來新的 query term 覆蓋，也會加分
- 若 question signature 與已選結果過於接近，會扣分

這代表 retrieval dimensions 的價值分成兩層：

1. `metadataScore()` 決定單筆資料對 query 有多合適
2. `rerankCandidates()` / `rerankResults()` 決定 top-k 整體是否有代表性，而不是被近重複答案佔滿

---

## 6. Hybrid search 與 keyword-only 都會吃這套 metadata

兩條查詢路徑都會使用 retrieval dimensions：

1. `hybridSearch()`
   - Supabase RPC `match_qa_items` 先做 pgvector over-retrieve
   - 再把 `row.similarity * 0.7 + kwBoost + synonymBonus + metadataScore()` 組成 base score
   - 最後乘上 `freshness_score`

2. `keywordSearch()`
   - 不呼叫 Supabase RPC，直接用記憶體中的 item
   - 仍會把 `kwBoost + synonymBonus + textMatch + metadataScore()` 乘上 `freshness_score`

所以 retrieval dimensions 不只服務 full semantic mode，也服務 local/context-only/fallback 場景。

---

## 7. Query-to-label inference 是刻意簡化的 heuristic layer

這套設計沒有把 query classification 再丟給一個 LLM，而是用三組 hints 做快速推斷：

- `QUERY_INTENT_HINTS`
- `QUERY_SCENARIO_HINTS`
- `QUERY_CATEGORY_HINTS`

這三組 hints 定義在 `api/src/store/search-engine.ts`（v3.5 從 `supabase-qa-store.ts` 抽出統一 export，`supabase-qa-store.ts` 改為 import 共用），是 runtime ranking 可直接修改的 heuristic 字典。若要擴充新場景，正確做法不是只改 query hints，而是讓 offline enrichment 也同步產生對應的 `intent_labels` / `scenario_tags` / `categories`，否則 query 端新增提示詞，item 端仍缺 metadata，效果會很有限。

原因很務實：

1. ranking 需要低延遲
2. API 在 local mode 與 production fallback 也要可用
3. hints 雖然粗，但可測、可預期、可直接修 keyword list

這也是 retrieval dimensions 的一個核心哲學：把昂貴與不穩定的判斷前移到 offline enrichment，runtime 只做小成本 signal composition。

---

## 8. 與 enrichment artifact 的關係

這些欄位不是在 API 當場生成，而是預期由 enrichment / curated QA 後處理先寫好，再送進 serving artifact 與 Supabase。

也就是說：

- `qa_final.json` / `qa_enriched.json` 是 metadata 的來源 artifact
- Supabase `qa_items` 是 production serving state
- `SupabaseQAStore` 只是讀取、fallback、re-rank，不負責創造 metadata

這樣的責任分界，讓 ranking 行為可以在離線資料處理與線上 serving 間保持一致。

---

## 9.5 Phase 2：從 internal metadata 變成 queryable capability

2026-03-15 的 phase 2 變更，代表 retrieval metadata 不再只存在 ranking 內部，而是正式進到 API contract：

- `GET /api/v1/qa` 新增 `primary_category`、`intent_label`、`scenario_tag`、`serving_tier`、`evidence_scope` filters
- `POST /api/v1/search` 也新增同一組 metadata filters，採 route-layer post-filter，不改底層 search engine signature
- API response 現在會直接回傳 `all_categories`、`intent_labels`、`scenario_tags`、`serving_tier`、`evidence_scope`

這個選擇的關鍵是風險控制：

1. ranking heuristics 繼續留在 store layer，避免 phase 2 把搜尋核心一起重寫
2. queryability 先在 route layer productize，讓前端、eval、admin tooling 可以直接消費 metadata
3. 若未來要下推到 DB filter，可先用同一組 API contract 驗證需求，再決定要不要改 store / SQL

---

## 10. 目前限制

這套 retrieval dimensions 仍有幾個明確限制：

- 若 production 尚未套 migration，extended columns 只存在本地 artifact，不存在 DB
- `QUERY_*_HINTS` 仍是手工字典，會有 coverage 上限
- 分數權重目前是 heuristics，不是經過大量 learning-to-rank 校正
- metadata 豐富度取決於 enrichment 寫得多完整，空欄位越多，效果越接近傳統 hybrid search

因此它現在的價值主要是「可解釋、可落地、可逐步 rollout」，而不是一次做成 fully learned ranker。

---

## 11. 結論

Retrieval dimensions 的本質，是把原本隱含在人類 SEO 顧問腦中的判斷標準，拆成幾個可儲存、可回退、可加權的欄位與規則：

- 類別是不是對
- 意圖是不是對
- 場景是不是對
- 這筆資料是 canonical、supporting 還是 booster
- 有沒有明確不該命中的 query

一旦這些訊號能進入 artifact 與 schema，搜尋品質就不再只靠 embedding 模型本身，而能開始做真正領域化的 ranking。

---

## 9. Migration 011：Snapshot Maturity Column

`supabase/migrations/011_snapshot_maturity_column.sql` 為 `metrics_snapshots` 增加：

- `maturity JSONB`：儲存成熟度維度資訊（`Record<string, string>`）

用途：`POST /api/v1/pipeline/metrics/save` 現可接受 `maturity` 欄位，儲存至快照。Report generator 從 snapshot 讀取成熟度維度，實現「存快照帶入 maturity → 生成報告時不需額外傳參」的工作流。

這是 010 retrieval metadata columns 的延伸：010 針對 `qa_items`（搜尋排序用），011 針對 `metrics_snapshots`（報告生成用）。兩者都遵循相同的 runtime fallback 策略 — column 不存在時不會導致 API 啟動失敗。
