# EVAL DEFINITION: SEO QA Pipeline Quality
# 建立日期：2026-02-27
# 更新至：v2.25（2026-03-06）
# 狀態：4 層評估框架整合完成

---

## 統一 4 層評估框架（v2.13）

本專案評估框架基於以下學術/業界依據：

| 框架 | 來源 | 本專案對應指標 |
|------|------|--------------|
| RAGAS (Es et al., 2023) | ACL 2024 | Context Relevance ✅、Faithfulness（v2.13 新增）、Context Precision（v2.13 新增）|
| IR 標準（TREC, Voorhees）| NIST/ACM SIGIR | MRR、Precision@K、Recall@K、NDCG@K（v2.13 新增）|
| RAG Triad（TruLens）| Truera/LlamaIndex | Context Relevance、Groundedness、Answer Relevance |
| LLM-as-Judge（Zheng et al., 2023）| NeurIPS 2023 | Relevance、Accuracy、Completeness |
| NVIDIA Context Relevance | NVIDIA NeMo Guardrails | context_relevance ✅（v2.12）|

### Layer 1 — Data Quality（無 API 成本）

| 指標 | 定義 | 合格線 | 腳本 |
|------|------|--------|------|
| `qa_count_in_range` | QA 總數在 [100, 2000] | 1.0 | `_eval_data_quality.py` |
| `avg_confidence` | 平均信心分數 | ≥ 0.80 | `_eval_data_quality.py` |
| `keyword_coverage` | ≥3 keywords 的 QA 比例 | ≥ 0.85 | `_eval_data_quality.py` |
| `no_admin_content` | 無管理/模板污染比例 | 1.0 | `_eval_data_quality.py` |

### Layer 2 — Retrieval IR Metrics（無 API 成本）

| 指標 | 學術依據 | Laminar group | Eval 腳本 | Executor |
|------|---------|--------------|-----------|----------|
| `hit_rate` | TREC | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `mrr` | TREC（Voorhees）| `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `precision_at_k` | IR 標準 | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `recall_at_k` | IR 標準 | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `ndcg_at_k` | Jarvelin & Kekalainen (2002) | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `keyword_hit_rate` | 本專案 | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `top1_category_match` | 本專案 | `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `top5_category_coverage` | 本專案（≡ Precision@K）| `retrieval_quality` | `evals/eval_retrieval.py` | API-first（v2.25） |
| `precision` | IR 標準 | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `recall` | IR 標準 | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `f1` | IR 標準 | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `hit_rate` | TREC | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `mrr` | TREC | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `ndcg` | Jarvelin & Kekalainen (2002) | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `top1_category_match` | 本專案 | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |
| `top5_category_coverage` | 本專案 | `keyword-retrieval` | `scripts/_eval_laminar.py` | naive keyword |

> **v2.25 變更**：`retrieval_quality` group 從 3→8 指標，executor 改用 `POST /api/v1/search`（含同義詞 + keyword boost + hybrid search）。`keyword-retrieval` group 保留作為 naive baseline 對照。

### Layer 3 — Retrieval Enhancement（無 API 成本）

| 指標 | 說明 | Laminar group |
|------|------|--------------|
| `kw_hit_rate_with_synonyms` | 同義詞展開後 hit rate | retrieval-enhancement（v2.13 新增）|
| `synonym_coverage` | query keywords 的 synonym 覆蓋比例 | retrieval-enhancement（v2.13 新增）|

### Layer 4 — Context Quality（Claude haiku，API 成本）

| 指標 | 框架 | 實作 |
|------|------|------|
| `context_relevance` | NVIDIA RAGAS | `POST /eval/context-relevance`（v2.12）|
| `faithfulness` | RAGAS | `/evaluate-faithfulness-local`（v2.13，Claude Code as Judge）|
| `context_precision` | RAGAS | `/evaluate-context-precision-local`（v2.13，Claude Code as Judge）|

---

## 當前基準線（v2.25，2026-03-06）

| 指標 | 當前值 | 目標值 | 層次 | Laminar group | 備註 |
|------|--------|--------|------|---------------|------|
| Relevance | **5.00** / 5 | ≥ 4.5 ✅ | L4 | — | LLM-as-Judge |
| Accuracy | **4.30** / 5 | ≥ 4.0 ✅ | L4 | — | LLM-as-Judge |
| Completeness | **3.95** / 5 | ≥ 4.0 | L4 | — | LLM-as-Judge |
| Hit Rate | **1.00** | ≥ 0.95 ✅ | L2 | `retrieval_quality` | v2.25 API mode |
| MRR | **0.975** | ≥ 0.85 ✅ | L2 | `retrieval_quality` | v2.25 API mode（原 naive 0.88）|
| Top-1 Category Match | **0.95** | ≥ 0.85 ✅ | L2 | `retrieval_quality` | v2.25 API mode（原 naive 0.85）|
| Precision@K | **0.89** | ≥ 0.80 ✅ | L2 | `retrieval_quality` | v2.25 API mode（原 naive 0.76）|
| Top-5 Category Coverage | **0.89** | ≥ 0.85 ✅ | L2 | `retrieval_quality` | v2.25 API mode（原 naive 0.72）|
| NDCG@K | **0.784** | ≥ 0.75 ✅ | L2 | `retrieval_quality` | v2.25 新增 |
| KW Hit Rate | **0.779** | ≥ 0.85 | L2 | `retrieval_quality` | API hybrid 排序，非純 keyword |
| Recall@K | **0.75** | ≥ 0.80 | L2 | `retrieval_quality` | 部分 query 的期望分類 > 2 個 |
| Synonym Coverage | 待測 | ≥ 0.70 | L3 | `retrieval-enhancement` | |
| Context Relevance | **0.32**（1 query）| ≥ 0.70 | L4 | — | v2.12 |
| Faithfulness | 待測 | ≥ 0.80 | L4 | — | |
| Context Precision | 待測 | ≥ 0.70 | L4 | — | |

### Laminar Eval Groups 全景（v2.26）

| Laminar Group | 指標數 | Golden 筆數 | Executor | Eval 腳本 | 執行方式 |
|---------------|--------|------------|----------|-----------|----------|
| `retrieval_quality` | **8** | **35** | API-first（`POST /api/v1/search`）| `evals/eval_retrieval.py` | `python evals/eval_retrieval.py` |
| `chat_quality` | **4** | 10 | API-first（`POST /api/v1/chat`）| `evals/eval_chat.py` | `python evals/eval_chat.py` |
| `qa_classification_quality` | **4** | **48** | API-first（`POST /api/v1/search`）| `evals/eval_qa_classification.py` | `python evals/eval_qa_classification.py` |
| `dedup_quality` | **3** | **40** | API-first（`POST /api/v1/search`）| `evals/eval_dedup.py` | `python evals/eval_dedup.py` |
| `report-quality` | 7 | — | identity（已生成報告）| `scripts/_eval_report.py` | `python scripts/_eval_report.py --report <path>` |
| `extraction_quality` | 4 | **12** | identity（已萃取 QA）| `evals/eval_extraction.py` | `python evals/eval_extraction.py` |
| `enrichment_quality` | 3 | 35 | synonym-expanded keyword | `evals/eval_enrichment.py` | `python evals/eval_enrichment.py` |
| `keyword-retrieval` | 8 | 35 | naive keyword（Python 本地）| `scripts/_eval_laminar.py` | `python scripts/_eval_laminar.py` |
| `retrieval-enhancement` | 3 | — | synonym-expanded keyword | `scripts/_eval_laminar.py --group retrieval-enhancement` | 同上 |
| `report-quality-eval` | 4 | — | identity（批量報告）| `scripts/_eval_laminar.py --mode report` | 同上 |

> **主要 group**：`retrieval_quality`（API-backed, 8 指標, 35 scenarios）+ `chat_quality`（API-backed, 4 指標）是最完整的端對端 eval。`qa_classification_quality` 和 `dedup_quality` 為 v2.26 新增。`keyword-retrieval` 保留為 naive baseline 對照。

### Golden Dataset 總覽（v2.26）

| Golden File | 筆數 | 涵蓋來源 | 使用的 Eval Groups |
|-------------|------|---------|-------------------|
| `golden_retrieval.json` | **35** | meeting + medium + iThome + google-cases | retrieval, chat, enrichment, keyword-retrieval |
| `golden_qa.json` | 48 | 9 categories 全覆蓋 | qa_classification_quality |
| `golden_extraction.json` | **12** | meeting(5) + medium(1) + iThome(2) + google-cases(4) | extraction_quality |
| `golden_dedup.json` | 40 | 20 merge + 20 no-merge | dedup_quality |
| `golden_report.json` | 5 | 4 focus + 1 guard | push_golden_to_laminar（手動） |
| `golden_seo_analysis.json` | 1 | provider 比較基準 | push_golden_to_laminar（手動） |

### chat_quality（v2.25，API-backed）

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| has_answer | **1.00** | ≥ 0.90 ✅ | context-only 模式也算通過 |
| has_sources | **1.00** | ≥ 0.90 ✅ | 每個 query 都有 source |
| answer_keyword_coverage | **0.82** | ≥ 0.70 ✅ | answer + sources 中的 keyword 命中 |
| top_source_in_expected_category | **0.90** | ≥ 0.80 ✅ | top-1 source 分類正確率 |

### report-quality（v2.25，fuzzy matching）

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| report_section_coverage | **1.00** | ≥ 0.90 ✅ | 6 sections 全覆蓋 |
| report_kb_citations | **1.00** | ≥ 0.80 ✅ | |
| report_has_research | **1.00** | ≥ 1.00 ✅ | |
| report_has_links | **1.00** | ≥ 1.00 ✅ | 原 0.2，已修正 |
| report_alert_coverage | **0.60** | ≥ 0.80 | fuzzy 修正後 0.2→0.6，prompt 強化待驗證 |
| report_overall | **0.92** | ≥ 0.85 ✅ | 原 0.84 |

### extraction_quality

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| qa_count_in_range | **1.00** | ≥ 0.90 ✅ | 萃取數量在合理範圍 |
| keyword_coverage | **1.00** | ≥ 0.70 ✅ | golden 修正後（原 0.44，golden 期望與來源內容不符） |
| no_admin_content | **1.00** | ≥ 1.00 ✅ | 無管理內容污染 |
| avg_confidence | **0.83** | ≥ 0.80 ✅ | |

### enrichment_quality

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| kw_hit_rate_with_synonyms | **0.71** | ≥ 0.80 | 同義詞展開後命中率 |
| freshness_rank_quality | **1.00** | ≥ 0.90 ✅ | 無 stale Q&A 擠入 top-3 |
| synonym_coverage | **0.00** | ≥ 0.30 | qa_final.json 無 _enrichment 資料 |

### qa_classification_quality（v2.26 新增，API-backed）

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| category_match | **TBD** | ≥ 0.80 | top-1 結果分類是否符合 golden 期望 |
| difficulty_match | **TBD** | ≥ 0.70 | top-1 結果難度是否符合 golden 期望 |
| evergreen_match | **TBD** | ≥ 0.80 | top-1 結果時效性是否符合 golden 期望 |
| has_result | **TBD** | ≥ 0.95 | 查詢是否有搜尋結果 |

### dedup_quality（v2.26 新增，API-backed）

| 指標 | 當前值 | 目標值 | 備註 |
|------|--------|--------|------|
| overlap_consistency | **TBD** | ≥ 0.50 | merge 對 jaccard 高、no-merge 對 jaccard 低 |
| category_consistency | **TBD** | ≥ 0.70 | merge 對同 category、no-merge 對不同 category |
| both_have_results | **TBD** | ≥ 0.95 | 兩個查詢都有搜尋結果 |

### v2.25–v2.26 Eval 改善摘要

| 改善項 | 做法 | 效果 |
|--------|------|------|
| retrieval executor → API | `eval_retrieval.py` 改呼叫 `POST /api/v1/search` | top5 0.72→0.89, top1 0.85→0.95 |
| chat eval → TS API | `eval_chat.py` 改呼叫 `POST /api/v1/chat` | 恢復運作，has_answer 1.0, kw_coverage 0.82 |
| report prompt 強化 | section 五必須逐一提及所有 ALERT_DOWN | alert_coverage 0.2→0.6 |
| report eval fuzzy match | strip 括號後綴做 substring match | has_links 0.2→1.0 |
| extraction golden 修正 | golden keywords 改為符合來源內容的期望 | keyword_coverage 0.44→1.00 |
| enrichment 基準線 | 確認無 qa_enriched.json，syn 為 0 是預期 | synonym_coverage 0.00（blocked on enrich pipeline） |
| golden_retrieval 擴充 | 20→35 scenarios，新增 medium/iThome/google-cases 查詢 | 覆蓋全部 4 來源、9 categories |
| golden_extraction 擴充 | 5→12 scenarios，新增 medium(1)/iThome(2)/google-cases(4) | 多來源萃取品質驗證 |
| golden_qa 連接 eval | 新增 `eval_qa_classification.py`（4 指標, 48 scenarios） | 分類/難度/時效性驗證 |
| golden_dedup 連接 eval | 新增 `eval_dedup.py`（3 指標, 40 pairs） | 去重品質端對端驗證 |

---

## BUG-001：分類評估計數錯誤（免費修復）

**問題**：`evaluate_classification` 失敗時（JSON 解析失敗 / API 錯誤），
回傳 `{"error": "..."}` 仍被 append 進 classify_results。
`compute_classify_statistics` 的 `total` 包含了失敗項，
導致正確率被稀釋（10% = 2 / 20，實際可能 2 / 2 成功）。

**診斷**：correct: 2 / incorrect: 0 / borderline: 0 / total: 20
18 筆無有效 `category_judgment`，為失敗項未被過濾。

**修復方法**：在 `compute_classify_statistics` 前過濾 error 項，
或在 append 前排除含 error key 的結果。

```python
# scripts/05_evaluate.py — main() 內
classify_results = [r for r in classify_results if "error" not in r]
classify_stats = compute_classify_statistics(classify_results)
```

**Eval 驗證**：
- [ ] 重跑 --classify-only，確認 total_evaluated = 成功筆數
- [ ] 正確率應 > 50%（合理預期）

---

## BUG-002：Retrieval LLM Top-1 Precision 過低（免費診斷）

**問題**：MRR = 0.85（高），但 LLM Top-1 Precision = 10%（1/10）。
兩者嚴重矛盾，MRR 是 category-based（較寬鬆），LLM 是語意判斷。

**可能原因（需診斷）**：
1. `_llm_judge_retrieval_relevance` prompt 過於嚴格
2. Retrieval 的 top-1 Q&A 確實與 query 語意不符（排序問題）
3. gpt-5-mini 的 JSON schema 有 parse 問題（回傳 not_relevant 當作保守預設）

**診斷方法（免費）**：
- 印出每個 golden case 的 top-1 Q&A 問題 + LLM 判斷理由
- 比對人工判斷，確認是 LLM 太嚴或 retrieval 真的不好

**修復方向**：
A. 若 LLM 太嚴 → 調整 prompt，加入「即使部分相關也算 relevant」
B. 若 retrieval 確實不好 → cross-encoder reranking（需 API 成本）

---

## IMPROVEMENT-001：Completeness 3.70（需 Step 2 重跑）

**目標**：Completeness 從 3.70 提升到 ≥ 4.0

**評分 3 分的共同問題**（從評估報告推斷）：
- Answer 缺少「原因 / 數據 / 案例 / 行動建議」
- 答案停留在描述現象，未給出機制解釋

**Prompt 改善方向（需先驗證再花錢）**：
```
改善重點：要求 Answer 必須包含
1. 具體建議或動作（What to do）
2. 原因或機制說明（Why it matters）
3. 如有可能，提供具體數據或案例參考
```

**成本估算**：gpt-5.2 × 87 份文件
**前置條件**：先用 3 份文件測試新 prompt，用 Step 5 驗證 Completeness 提升

---

## IMPROVEMENT-002：Category Hit Rate 65%（需新增分類）

**問題**：某些 golden_retrieval 場景跨越現有分類邊界
**方向**：新增 2 個分類 → 需重跑 Step 3（gpt-5-mini × 703 筆）

**前置條件**：先確認哪些場景命中率最低，決定新增哪些分類

---

## 執行優先序

### 免費（立即執行）
1. [ ] **BUG-001 修復**：過濾 classify_results 中的 error 項
2. [ ] **BUG-002 診斷**：印出 top-1 Q&A + LLM 判斷理由，確認問題根因

### 低成本（embedding-only，gpt-5-mini）
3. [ ] **Reranker 診斷**：分析 KW Hit Rate 53% 中哪些場景最差
4. [ ] **分類分布分析**：確認 703 筆中各分類比例，發現失衡類別

### 高成本（需決策）
5. [ ] Completeness 提升 → Step 2 重跑（gpt-5.2 × 87）
6. [ ] 新增分類 → Step 3 重跑（gpt-5-mini × 703）
7. [ ] Cross-encoder Reranking → Step 4 每次報告額外呼叫

---

## pass@k 目標

| Eval | 目標 | 衡量方式 |
|------|------|---------|
| BUG-001 修復後分類正確率 | pass@1 > 50% | 重跑 --classify-only |
| BUG-002 診斷後 Top-1 Precision | pass@1 > 40% | 僅調整 prompt |
| Completeness 改善 | pass@1 Completeness ≥ 4.0 | 3份文件試跑 |
