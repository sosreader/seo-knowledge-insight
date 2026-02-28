# Plan: 系統演算法審視 + 全模組 Eval/Observability

> 日期：2026-02-28
> 狀態：v1 — 初始設計
> 前置計畫：[modular-pipeline-with-dep-checks.md](.claude/plan/modular-pipeline-with-dep-checks.md)（已完成）

**TL;DR** — 系統現有 5 個 pipeline step + 1 個 API 搜尋層。目前演算法選用大部分合理但有幾個缺口：API 層缺 hybrid search、dedup 沒有獨立 eval、分類準確率 68% 偏低、Laminar 只覆蓋 API 層。本計畫分 4 個 Phase：(1) 將 Laminar tracing 擴展到全 pipeline；(2) 為每個 Step 建立 golden set + eval metric；(3) 基於 eval 數據決定演算法改善；(4) 落實改善並用 eval 驗證。每個改善建議附學術/業界佐證。

---

## 一、現況審視：各模組演算法 + 學術佐證

### A. Semantic Search（API 層 — app/core/store.py）

| 項目          | 現狀                               | 評估                                                                                                                                                              |
| ------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Embedding     | `text-embedding-3-small` (1536d)   | **合適**。MTEB benchmark 上此模型在中文 STS 表現良好，且 <1000 筆不需要降維                                                                                       |
| 檢索          | 純 cosine similarity (brute-force) | **合適**。<1000 筆 brute-force 比 ANN index (HNSW/Faiss) 更快，無近似誤差                                                                                         |
| Hybrid search | **API 層完全沒有**                 | **缺口**。Step 4/5 有 keyword boost 但 API 沒有。BEIR benchmark (Thakur et al., 2021 — NIPS) 證實 hybrid (lexical + semantic) 在 18 個 dataset 上一致優於單一方法 |
| Reranking     | API 層無，Step 4 用 LLM rerank     | **合理但可改善**。RankGPT (Sun et al., 2023) 證實 LLM reranking 有效，但 cross-encoder reranking 在小量候選時更穩定且便宜                                         |

### B. BM25 適用性分析

**結論：對 <1000 筆中文語料，正式 BM25 效益有限，但 hybrid 原則成立。**

| 因素     | 分析                                                                                                                                |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 語料規模 | BM25 的 IDF 項需要足夠文件數才有鑑別力。703 筆太少，很多 term 的 IDF 差異不大                                                       |
| 中文分詞 | BM25 依賴良好分詞。中文 SEO 術語（如「已檢索未索引」）不切分才是正確 token，jieba 等工具會切碎。你目前的 keyword 精準匹配反而更適合 |
| 學術佐證 | Okapi BM25 (Robertson et al., 1994) 設計給大型文件集。小語料場景下 TF-IDF 或精準匹配通常等效 (Manning et al., IR textbook §6.3)     |
| **建議** | 保留現有 `_compute_keyword_boost` 作為 lexical signal，但統一到 API 層。如果未來到 5000+ 筆再考慮 `rank_bm25` 或 Elasticsearch      |

### C. Q&A 萃取（scripts/02_extract_qa.py + utils/openai_helper.py）

| 項目                          | 現狀                                                           | 學術佐證                                                                                                                          | 評估       |
| ----------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| Multi-Expert Prompting        | 3 角色（知識設計師、SEO 審計員、品質評估官）                   | 與 ExpertPrompting (Xu et al., 2023 — arXiv:2305.14688) 和 Multi-Persona (Wang et al., 2024) 一致。已被證實提升萃取品質           | **強**     |
| What/Why/How/Evidence         | 四層結構 Answer                                                | 對應 Bloom's Taxonomy 的知識層次（Knowledge→Comprehension→Application→Evidence），在 knowledge base 設計中是標準框架              | **強**     |
| `[補充]` Attribution Tag      | 區分會議原文 vs 通用知識                                       | 對應 provenance tracking (Longpre et al., 2023 — "Entity Attribution")。是忠實度的正確做法                                        | **強**     |
| Structured Output             | `json_schema` + `strict: true`                                 | OpenAI best practice，避免 JSON 解析失敗                                                                                          | **強**     |
| Chunking                      | 按 `##` 或 `\n\n`，閾值 18000 字元                             | **可改善**。Semantic chunking (Greg Kamradt, 2023) 或 overlapping window 可避免切斷語意完整段落。但對會議記錄（自然段落）影響較小 | **可接受** |
| **缺口：萃取品質無獨立 eval** | Step 5 評的是 qa_final（經過 dedup+classify 後），不是原始萃取 | 無法分離「萃取品質差」vs「dedup/classify 引入問題」                                                                               | **需補**   |

### D. 去重（scripts/03_dedupe_classify.py + scripts/dedupe_helpers.py）

| 項目                        | 現狀                                                                                                       | 學術佐證                                                                                                                                      | 評估       |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 全量 cosine matrix          | O(n²)，703 筆 ≈ 250K 比較                                                                                  | 對 <1000 完全可行。>5000 應改用 ANN 或 LSH                                                                                                    | **合適**   |
| 閾值 0.88                   | 硬閾值，greedy single-link                                                                                 | STS benchmark 的 "duplicate" 通常在 0.85-0.92。0.88 合理。但 single-link clustering 可能漏掉 transitive duplicates (A~B, B~C, A≁C 但語意相同) | **可改善** |
| LLM 合併                    | gpt-5.2 合併重複群組                                                                                       | 比簡單"取最長"更好，保留多來源資訊                                                                                                            | **強**     |
| **缺口：無 dedup eval**     | 不知道 0.88 閾值是否最佳，不知道有多少 false positive (不該合併的被合併) / false negative (該合併的沒合併) | 需要 golden set 來調閾值                                                                                                                      | **需補**   |
| **缺口：100% blast radius** | 改 1 份會議 → 全量重算                                                                                     | 已在 `.claude/plan/` 識別                                                                                                                     | **已知**   |

### E. 分類（utils/openai_helper.py `classify_qa()`）

| 項目                  | 現狀                                                                                                                    | 評估                                                                                |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| LLM 分類 (gpt-5-mini) | 10 類 + difficulty + evergreen                                                                                          | 合理策略                                                                            |
| 準確率 68%            | 低於可接受標準 (80%)                                                                                                    | **需改善**                                                                          |
| 原因分析              | Prompt 只有類別名稱和 enum，**沒有 few-shot examples**。10 類之間可能有語意重疊（如「搜尋表現分析」vs「GA與數據追蹤」） | 缺 few-shot 是主因                                                                  |
| **建議**              | (1) 為每個類別加 2-3 個 few-shot example；(2) 加入類別定義文字（不只是名稱）；(3) 考慮合併語意重疊的類別                | 有文獻支持 few-shot 在分類上有 10-15% 準確率提升 (Brown et al., 2020 — GPT-3 paper) |

### F. 週報生成（scripts/04_generate_report.py）

| 項目                       | 現狀                                            | 評估                                                                         |
| -------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------- |
| 異常偵測                   | 月趨勢 ≥15% / 週趨勢 ≥20% 硬閾值                | 簡單但可解釋。更精確做法是 z-score 或 IQR-based，但對週度 SEO 指標差異已足夠 |
| METRIC_QUERY_MAP           | 200+ 手動映射                                   | 有效但維護負擔大。可改為 LLM 自動生成 query（但目前效果已很好不急改）        |
| Hybrid search + LLM rerank | 語意 + keyword boost → top-2N → gpt-5-mini 精選 | 符合 two-stage retrieval 最佳實踐 (Nogueira & Cho, 2019)                     |
| **缺口：報告品質無 eval**  | 沒有 golden report 或 report quality 判斷機制   | **需補**                                                                     |

---

## 二、實施步驟

### Phase 1: Laminar 全 Pipeline Tracing（~2 天）

目標：讓每個 Step 的 LLM 呼叫和關鍵操作都在 Laminar 可見。

1. 在 `requirements.txt` 加入 `lmnr>=0.5.0`
2. 建立 `utils/observability.py`：封裝 Laminar 初始化 + context manager，用於 pipeline scripts
   - `init_laminar()` — 讀 `LMNR_PROJECT_API_KEY` env var，呼叫 `Laminar.initialize()`
   - 使用 `@observe()` decorator（Laminar SDK 提供）wrap 每個 LLM 呼叫
3. 在每個 Script 的 `main()` 入口加 `init_laminar()`：
   - `scripts/02_extract_qa.py` — trace 每份 meeting 的萃取
   - `scripts/03_dedupe_classify.py` — trace embedding 計算、dedup 分組、LLM merge、LLM classify
   - `scripts/04_generate_report.py` — trace metrics parsing、query construction、hybrid search、LLM rerank、report generation
   - `scripts/05_evaluate.py` — trace 每筆 LLM-as-Judge 呼叫
4. 在 `utils/openai_helper.py` 的關鍵函式加 `@observe()` decorator：`extract_qa_from_text()`、`get_embeddings()`、`merge_similar_qas()`、`classify_qa()`
5. 每個 Step 完成時，用 Laminar 的 `evaluate` API 記錄 step-level metrics（萃取數量、合併率、token 用量等）

**驗證**：執行 `python scripts/02_extract_qa.py --limit 1`，在 Laminar dashboard 看到完整 trace span。

### Phase 2: Per-Step Golden Set + Eval Metric（~1 週）

建立每個 Step 的獨立評估機制，讓演算法改善可量化。

#### Step 2 — 萃取品質 Eval

1. 建立 `eval/golden_extraction.json`：從 5 份代表性會議手動標註預期萃取結果
   - 每份含：`source_file`、`expected_qa_count`（±2）、`must_extract`（必須出現的知識點關鍵句）、`must_not_extract`（行政內容不該出現）
2. 新增 `scripts/05_evaluate.py --eval-extraction` flag
   - Metrics：Extraction Precision（萃取的 Q&A 中，多少是有意義的）、Extraction Recall（必須萃取的知識點是否都有）、Hallucination Rate（答案中有多少內容在原文找不到根據）
3. 在 Laminar 記錄：`extraction_precision`、`extraction_recall`、`hallucination_rate`

#### Step 3a — 去重品質 Eval

1. 建立 `eval/golden_dedup.json`：標註 20 對已知重複 + 20 對已知不重複
   - 格式：`{"pairs": [{"q1_id": ..., "q2_id": ..., "should_merge": true/false}]}`
2. 新增 `scripts/05_evaluate.py --eval-dedup` flag
   - Metrics：Dedup Precision（合併的對中，真正重複的比例）、Dedup Recall（已知重複對中，被成功合併的比例）、最佳閾值搜尋（0.80-0.95 掃描，找 F1 最佳點）
3. 在 Laminar 記錄：`dedup_precision`、`dedup_recall`、`dedup_f1`、`optimal_threshold`

#### Step 3b — 分類品質 Eval（強化現有）

1. 擴充 `eval/golden_qa.json` 從 10 筆到 50 筆（覆蓋每類至少 3 筆）
2. 加入 category confusion matrix 分析（哪些類別容易互相混淆）
3. 在 Laminar 記錄：`classification_accuracy`、`per_category_f1`、`confusion_pairs`

#### Step 4 — 週報品質 Eval

1. 建立 `eval/golden_report.json`：3 份歷史週報 + 人工標註品質等級
   - 評估維度：Data Grounding（引用的數字是否正確）、Knowledge Relevance（引用的 Q&A 是否切題）、Actionability（行動建議是否具體）
2. 新增 `scripts/05_evaluate.py --eval-report` flag，用 LLM-as-Judge 評分
3. 在 Laminar 記錄：`report_grounding`、`report_relevance`、`report_actionability`

#### Step 5 — Retrieval Eval（強化現有）

1. 擴充 `eval/golden_retrieval.json` 從 21 到 40 場景
2. 加入 `expected_qa_ids`（精確期望結果）以計算 Precision@k、Recall@k、NDCG@k
3. 在 Laminar 記錄：`retrieval_mrr`、`retrieval_ndcg@5`、`kw_hit_rate`、`llm_top1_precision`

**驗證**：執行 `python scripts/05_evaluate.py --eval-extraction --eval-dedup`，在 Laminar 看到多維度 eval 結果。

### Phase 3: 演算法改善（~1 週，基於 Phase 2 數據）

有了 baseline eval 後，逐步改善：

#### 3a. API 層加入 Hybrid Search

1. 將 `_compute_keyword_boost` 從 `scripts/04_generate_report.py` 抽取到 `utils/search_engine.py`
2. `SearchEngine` 類別統一 semantic + keyword hybrid 邏輯
3. API 的 `app/core/store.py` `search()` 改用 `SearchEngine`
4. hybrid weight 可配置（`config.SEMANTIC_WEIGHT=0.7`、`KEYWORD_WEIGHT=0.3`）
5. 學術佐證：hybrid weight 通常 0.6-0.8 semantic + 0.2-0.4 lexical (Luan et al., 2021 — "Sparse, Dense, and Attentional Representations for Text Retrieval")
6. 用 Phase 2 的 retrieval eval golden set 比較 pure semantic vs hybrid 的 MRR/NDCG

#### 3b. 分類準確率提升（68% → 目標 80%+）

1. 為 `classify_qa()` prompt 加入 few-shot examples（每類 2 筆，從 golden set 取）
2. 加入類別定義描述（不只是名稱）
3. 分析 confusion matrix，考慮合併「搜尋表現分析」與「GA與數據追蹤」等高混淆對
4. 用 Phase 2 的 classification eval 驗證

#### 3c. Dedup 閾值優化

1. 用 Phase 2 golden_dedup.json 跑 threshold sweep（0.80-0.95，step 0.01）
2. 選 F1 最佳閾值取代固定 0.88
3. 考慮改用 connected-component clustering 取代 greedy single-link（避免漏 transitive duplicates）

#### 3d.（可選）Cross-encoder Reranking

1. 如果 retrieval eval 顯示 LLM reranking 不穩定（nano 35% 失敗率），考慮引入 `sentence-transformers` 的 cross-encoder（如 `cross-encoder/ms-marco-MiniLM-L-6-v2`）
2. 學術佐證：Nogueira & Cho (2019) — "Passage Re-ranking with BERT"，cross-encoder 穩定性顯著優於 bi-encoder
3. 權衡：引入 PyTorch 依賴（~2GB），對輕量部署有影響。可以用 ONNX runtime 替代（~50MB）

### Phase 4: Laminar Dashboard 整合（~2 天）

1. 在 Laminar 建立 3 個 dashboard view：
   - **Pipeline Health**：每次 run 的 step duration、token usage、error rate
   - **Quality Metrics**：per-step eval scores 隨時間趨勢
   - **A/B Comparison**：algorithm change 前後的 eval 差異
2. 設定 Laminar labels 分類 traces：`step=extraction`、`step=dedup`、`step=classify`、`step=report`、`step=eval`
3. 每個 LLM 呼叫記錄 `model`、`tokens_used`、`latency_ms` 作為 span attributes

---

## 三、驗證方式

| Phase   | 驗證方法                                                                                    |
| ------- | ------------------------------------------------------------------------------------------- |
| Phase 1 | `python scripts/02_extract_qa.py --limit 1` → Laminar dashboard 顯示完整 trace tree         |
| Phase 2 | `python scripts/05_evaluate.py --eval-extraction --eval-dedup` → 產出 baseline metrics JSON |
| Phase 3 | 比較改善前後的 eval metrics（MRR、classification accuracy、dedup F1）                       |
| Phase 4 | Laminar dashboard 可看到趨勢圖和 A/B 比較                                                   |

---

## 四、決策記錄

| 決策                       | 選擇                                         | 原因                                                              |
| -------------------------- | -------------------------------------------- | ----------------------------------------------------------------- |
| BM25 vs 現有 keyword boost | **保留 keyword boost**                       | <1000 筆中文語料，BM25 的 IDF 鑑別力不足，現有精準匹配更適合      |
| 向量資料庫                 | **不導入**                                   | <1000 筆，numpy brute-force 延遲 <1ms，HNSW 只增加複雜度          |
| Cross-encoder              | **Phase 3 依數據決定**                       | 先看 LLM rerank 穩定性數據，不穩定才引入                          |
| Laminar 範圍               | **全 pipeline + API**                        | 現有只有 API 層，pipeline 是主要品質控制點                        |
| Golden set 規模            | **50 筆 QA + 40 retrieval + 20 dedup pairs** | Research-grade 需要統計顯著性，但不需要 1000+ 的 production-grade |

---

## 五、建議執行順序

```
Phase 1 → Phase 2 → Phase 3a & 3b（並行）→ Phase 3c → Phase 4
```

Phase 1 和 2 是基礎設施，必須先完成才能量化 Phase 3 的改善效果。Phase 3d (cross-encoder) 視 Phase 3 數據決定是否需要。

---

## 六、參考文獻

| 主題                     | 文獻                                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Hybrid Search            | Thakur et al., "BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models" (NeurIPS 2021) |
| BM25                     | Robertson et al., "Okapi at TREC-3" (1994); Manning et al., "Introduction to Information Retrieval" §6.3                 |
| LLM Reranking            | Sun et al., "Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents" (RankGPT, 2023)        |
| Cross-encoder            | Nogueira & Cho, "Passage Re-ranking with BERT" (2019)                                                                    |
| Hybrid Weight            | Luan et al., "Sparse, Dense, and Attentional Representations for Text Retrieval" (2021)                                  |
| Multi-Expert Prompting   | Xu et al., "ExpertPrompting: Instructing Large Language Models to be Distinguished Experts" (arXiv:2305.14688, 2023)     |
| Few-shot Classification  | Brown et al., "Language Models are Few-Shot Learners" (GPT-3 paper, NeurIPS 2020)                                        |
| Attribution / Provenance | Longpre et al., "Entity-Based Knowledge Conflicts in Question Answering" (2023)                                          |
| Bloom's Taxonomy         | Bloom et al., "Taxonomy of Educational Objectives" (1956) — What/Why/How/Evidence 對應知識層次                           |
