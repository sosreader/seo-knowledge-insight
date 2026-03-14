# Retrieval 評分與 QA 資料維度提升計畫

**狀態：已完成**
**建立日期：** 2026-03-15
**完成日期：** 2026-03-15
**前置脈絡：** `plans/completed/version-registry-multilayer.md`、`plans/active/phase2-learning-query.md`

## 完成摘要

- 已完成 retrieval metadata backfill：`primary_category`、`categories`、`intent_labels`、`scenario_tags`、`serving_tier`、`retrieval_phrases`、`retrieval_surface_text`
- 已完成 Python 離線 retrieval scoring / rerank 升級，並輸出 `slice_metrics`、`failure_buckets`、`boosterless` / `dual-label` 指標
- 已完成 TypeScript runtime search path 對齊：file-based 與 Supabase store 均使用 metadata-aware rerank
- 已完成 `extraction_model` over-retrieve before filter、migration fail-fast、source_url fallback consistency
- 已完成 README / API / research 文件同步與 PR 更新

## 驗證結果

- Baseline `precision_at_k=0.58` → Phase 4 `precision_at_k=0.85`
- `boosterless_precision_at_k=0.83`
- `dual_category_recall_at_k=1.00`
- `multi_label_f1_at_k=0.97`
- `mrr=0.99`
- `pytest tests/test_qa_tools_eval.py tests/test_retrieval_enrichment_migration.py -q` → `43 passed`
- `pnpm test`（api/）→ `58 files / 613 tests passed`

---

## 背景

目前本地 retrieval 已具備不錯的召回能力，但整體排序純度仍不足。

- 現況指標約為：`avg_keyword_hit_rate=0.78`、`avg_category_hit_rate=0.89`、`avg_mrr=0.92`、`avg_precision_at_k=0.58`、`avg_f1_score=0.64`
- 現有門檻見 `eval/eval_thresholds.json`：`keyword_hit_rate=0.70`、`mrr=0.90`、`precision_at_k=0.75`
- 實際痛點已不是「找不到答案」，而是「top-1 常正確，但 top-k 混入過多部分相關或近重複結果」
- `eval/golden_retrieval.json` 已有大量雙分類情境，但現有 QA item 主要仍用單一 `category` 表達，導致資料結構天然吃虧
- `manual curated retrieval boosters` 已證明能補 query surface，但若繼續靠 booster 擴張，會把 corpus 缺口、ranking 缺口與 eval 口徑混在一起

這份計畫的核心目標，是把改善順序明確定義為：

`資料維度擴充 → coverage-aware retrieval/scoring → eval 口徑升級 → booster 治理`

而不是再追加更多定向 booster。

---

## 問題定義

### P1. Top-k purity 不足

- `MRR` 已高，表示第一筆常常可用
- `precision_at_k` 明顯偏低，表示結果集污染嚴重
- `f1_score` 被 `precision_at_k` 與雙分類 case 的 coverage 一起拖累

### P2. 資料模型無法原生表達多分類與多意圖

- 現有欄位偏單一 `category`
- 同一筆 QA 即使同時包含 diagnosis、implementation、measurement，也無法被檢索層正確利用
- dual-category case 只能靠額外 booster 補第二面向

### P3. Booster 與 canonical corpus 等權

- booster 現在能有效修弱案例
- 但若不區分 `canonical` 與 `booster`，會污染其他 query 的 top-k
- 長期會讓 eval 分數變好，但根因未解

### P4. Eval 觀測口徑不足

- 現有總平均會掩蓋 slice 差異
- 缺少 `dual-label`、`boosterless`、`hard-negative` 等切片
- 無法判斷改善是來自 corpus、ranking，還是 booster 硬拉

---

## 目標

- 提升 top-k purity，讓 `precision_at_k` 成為主要改善指標
- 讓 QA corpus 可原生表達 `primary + secondary category` 與多意圖面向
- 讓 retrieval scoring 能辨識 coverage、去除近重複、並治理 booster 權重
- 讓 eval 能拆解 single-label、dual-label、boosterless、hard-negative 場景
- 讓新增 metadata 能支援未來 Supabase、API、reporting 與 meeting-prep 的進一步分析

---

## 非目標

- 不重寫現有 9 大分類 taxonomy
- 不直接導入需要大量線上點擊資料的 Learn-to-Rank 訓練流程
- 不在本輪全面移除 booster，而是把 booster 退回輔助角色
- 不優先做大型 UI 擴張；前端僅需要支援新指標與切片顯示
- 不把 retrieval 問題完全轉嫁給更大模型或更重的 embedding 成本

---

## 現況資料欄位

根據 `scripts/migrate_to_supabase.py`，目前主要欄位包含：

- `question`
- `answer`
- `keywords`
- `confidence`
- `category`
- `difficulty`
- `evergreen`
- `source_title`
- `source_date`
- `source_type`
- `source_collection`
- `source_url`
- `is_merged`
- `extraction_model`
- `synonyms`
- `freshness_score`
- `search_hit_count`
- `embedding`

這些欄位足夠支撐 baseline search，但不足以支撐多分類 coverage 與 finer-grained rerank。

---

## 擬擴充資料模型

採 backward-compatible 策略：保留現有 `category` 作為相容欄位，同時擴充新欄位。

### 必要欄位

- `primary_category`
  - 與現有 `category` 對齊
  - 作為舊 API / filter 的相容入口
- `categories`
  - 多值分類陣列
  - 第一個元素必須等於 `primary_category`
- `intent_labels`
  - 例如：`diagnosis`、`root-cause`、`implementation`、`measurement`、`reporting`、`platform-decision`
- `scenario_tags`
  - 例如：`discover`、`google-news`、`faq-rich-result`、`ga4-attribution`、`author-page`、`image-seo`
- `serving_tier`
  - `canonical`、`supporting`、`booster`

### 建議欄位

- `retrieval_phrases`
  - 常見 query phrasing 的短語集合
- `retrieval_surface_text`
  - 專供 embedding / keyword hybrid 使用的乾淨檢索文本
- `content_granularity`
  - `tactical`、`diagnostic`、`strategic`
- `evidence_scope`
  - `technical`、`content`、`analytics`、`platform`
- `booster_target_queries`
  - 僅 booster 使用，明確記錄服務哪些 query pattern
- `hard_negative_terms`
  - 容易混淆的 query / term，用於 rerank penalty 與 eval

### 設計原則

- `categories` 與 `intent_labels` 為本輪必要欄位
- 其他欄位可分批上線，但 schema 要一次預留
- 允許 partial coverage，但必須有 coverage 指標與 backfill 信心分布

---

## Retrieval / Scoring 改進方向

### 1. Candidate generation 與 rerank 分層

- Candidate generation 先追 recall
- Rerank 再處理 purity、coverage、duplicate penalty、booster penalty
- 避免在第一層就過度剪枝，犧牲 second-intent coverage

### 2. 新增 rerank 特徵

- `category overlap score`
- `intent overlap score`
- `scenario match score`
- `duplicate penalty`
- `booster prior penalty`
- `canonical prior bonus`
- `source diversity penalty`
- `granularity fit`
- `log-scaled search_hit_count`

### 3. Top-k coverage-aware 組裝

- top-1 仍以最相關單筆為目標
- top-5 則必須考慮結果集多樣性與第二面向覆蓋
- 若 top-3 已有兩筆極近似答案，應優先補第二 category / 第二 intent，而非繼續塞重複內容

### 4. 真正接入 contextual retrieval surface

- 將 multi-layer context 方向落地到 retrieval
- `qa_context.json` 或等價 contextual description 應進入 ranking / embedding surface
- 改善字面相似不足但語義高度相關的 query

---

## Eval / Golden 擴充方向

### Golden Retrieval v2 建議欄位

- `expected_primary_category`
- `expected_categories`
- `expected_intents`
- `expected_scenarios`
- `min_relevant_items`
- `disallowed_categories`
- `booster_sensitive`
- `canonical_required`
- `hard_negative_queries`
- `source_preference`

### 新增評估切片

- `single-label slice`
- `dual-label slice`
- `boosterless slice`
- `hard-negative slice`
- `topic slice`：Discover / analytics / indexing / platform
- `source-type slice`：meeting / article / curated-manual

### 新增或正式化指標

- `dual_category_recall_at_k`
- `multi_label_f1_at_k`
- `ndcg_at_k`
- `boosterless_precision_at_k`
- `canonical_top1_rate`
- `duplicate_rate_at_k`
- `intent_coverage_at_k`

---

## 分階段執行方案

### Phase 0：基線切片與失敗模式盤點

**目標：** 把 `precision_at_k` 的損失來源拆成可行動的 failure buckets。

**工作項目：**
- 對現有 retrieval eval 輸出建立 failure taxonomy
- 區分：single-label miss、dual-label second-intent miss、duplicate noise、booster leakage、platform-strategy miss、analytics-vs-technical confusion
- 盤點 corpus 中哪些 QA 實際具備多意圖內容，但目前只被標成單一 category
- 盤點 `canonical / supporting / booster` 比例與 top-k 影響

**Deliverables：**
- failure report
- slice dashboard 規格
- schema 決策草案

**驗收：**
- 能量化 `precision_at_k` 的主要損失來源，而不只看到單一總平均

---

### Phase 1：資料模型擴充與 backfill

**目標：** 讓 corpus 原生支援多分類、多意圖與 serving tier。

**工作項目：**
- 新增 `primary_category`、`categories`、`intent_labels`、`scenario_tags`、`retrieval_phrases`、`retrieval_surface_text`、`serving_tier`
- 設計 backfill 規則：優先從既有 `category`、`keywords`、`source_type`、booster metadata、query wording 規則化生成
- 低信心項目進人工校正池
- 將欄位接入 `scripts/enrich_qa.py` 與 `scripts/migrate_to_supabase.py`
- 製作 coverage report 與 confidence distribution

**Deliverables：**
- schema 變更清單
- migration / backfill plan
- qa_enriched v2 artifact spec
- metadata coverage report

**驗收：**
- 至少 80% corpus 具備 `categories` 與 `intent_labels`
- 100% booster 具備 `serving_tier` 與 target scenario metadata

---

### Phase 2：Retrieval candidate 與 rerank 升級

**目標：** 降低 top-k 噪音並補足第二面向 coverage。

**工作項目：**
- 在 retrieval store 導入 coverage-aware rerank
- 對 semantic / keyword / synonym / category / intent / booster prior / duplicate penalty 建立可配置權重
- 讓 embedding surface 改用 `retrieval_surface_text` 或等價輸入
- 加入 duplicate suppression 與 category diversity top-k 組裝
- booster 預設降權，只在 scenario 強匹配時回升

**Deliverables：**
- 新版 score formula
- 權重配置
- top-k 組裝策略
- A/B 離線 eval 報告

**驗收：**
- 不犧牲 top-1 的前提下，`precision_at_k` 與 dual-category coverage 可重現提升

---

### Phase 3：Golden / Eval 擴充與 gate 重設

**目標：** 讓評估口徑與實際痛點對齊。

**工作項目：**
- 擴充 `golden_retrieval.json` metadata
- 新增 dual-label、boosterless、hard-negative evaluator
- 報表改為總平均 + slice 並列輸出
- 重設 threshold 為過渡 gate 與穩定 gate 兩階段

**Deliverables：**
- golden retrieval v2
- eval report v2
- threshold proposal
- failure sample set

**驗收：**
- 每次 eval 都能辨識改善是來自 corpus、ranking，還是 booster

---

### Phase 4：Booster 治理與 rollout

**目標：** 將 booster 從主改善手段降回輔助機制。

**工作項目：**
- 建立 booster 新增準則與淘汰準則
- 定義 canonical 吸收流程
- 將 booster 效益與副作用納入週期性報表
- 先以 read-only / eval mode 驗證，再灰度切換 scoring 權重

**Deliverables：**
- booster governance policy
- rollout checklist
- rollback plan
- 監測報表模板

**驗收：**
- 排除 booster 後，`boosterless slice` 仍維持改善

---

## 指標與門檻建議

### 基礎排序層

- `keyword_hit_rate`
- `mrr`
- `hit_rate`

### Purity / Coverage 層

- `precision_at_k`
- `dual_category_recall_at_k`
- `multi_label_f1_at_k`
- `ndcg_at_k`
- `duplicate_rate_at_k`

### Booster 治理層

- `boosterless_precision_at_k`
- `canonical_top1_rate`
- `booster_top1_share`

### 資料完整度層

- `categories coverage`
- `intent_labels coverage`
- `scenario_tags coverage`
- `serving_tier coverage`
- `backfill confidence distribution`

### 建議 gate

**短期過渡 gate：**

- `keyword_hit_rate >= 0.75`
- `mrr >= 0.90`
- `precision_at_k >= 0.65`
- `dual_category_recall_at_k >= 0.75`
- `multi_label_f1_at_k >= 0.68`

**最終穩定 gate：**

- `keyword_hit_rate >= 0.75`
- `mrr >= 0.90`
- `precision_at_k >= 0.72`
- `dual_category_recall_at_k >= 0.82`
- `multi_label_f1_at_k >= 0.75`
- `boosterless_precision_at_k >= 0.65`
- `ndcg_at_k >= 0.80`

關鍵不是立刻把 `precision_at_k` 拉到 0.75，而是先建立對準真實問題的觀測口徑，再逐步收斂。

---

## 風險與依賴

### 風險

- 多標籤 backfill 品質不穩，會把 retrieval 噪音轉移到 metadata
- schema 擴充會牽動 API / migration / search store / eval 多個模組
- booster 降權後，短期弱案例分數可能先下滑
- retrieval surface 改變後，`MRR` 可能短期回退
- 新 threshold 與舊 baseline 不可直接橫比

### 緩解策略

- 先建立高信心規則 + 人工校正池
- 採 backward-compatible schema，保留 `category -> primary_category` 相容層
- 先並行跑 `with-booster` 與 `boosterless` 報表
- 強制保留 top-1 regression check
- 標註 `corpus version`、`golden version`、`booster policy version`

### 依賴

- Supabase schema migration
- enrichment pipeline 可穩定輸出新欄位
- retrieval eval 可按 `serving_tier`、`source_type`、`single/dual-label` 切片
- 需要決定哪些欄位允許純規則 backfill，哪些欄位需要人工審校

---

## 建議執行順序

1. 先做 Phase 0 failure slicing，明確量化 precision 損失來源
2. 再做 Phase 1 schema 與 backfill，先把資料表徵修正到位
3. 接著做 Phase 2 rerank 與 top-k 組裝
4. 再做 Phase 3 golden / threshold 升級
5. 最後做 Phase 4 booster 治理與 rollout

---

## 預期成果

完成後，系統應從「第一筆常答對，但結果集不乾淨」提升到：

- top-1 不退步
- top-k 更少重複與噪音
- dual-category case 不再主要依賴 booster 補第二面向
- corpus 能原生描述多分類、多意圖與 serving tier
- eval 可精確區分 corpus 改善、ranking 改善與 booster 假象

---

## 後續接續建議

這份 plan 建議拆成兩個實作工作流：

1. `schema + backfill` 工作流
2. `rerank + eval slices` 工作流

若要開始實作，建議優先從 `Phase 0 + Phase 1` 起手，因為在資料模型仍是單標籤前，直接調 ranking 權重很容易陷入局部最適。