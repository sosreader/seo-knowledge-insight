# EVAL DEFINITION: SEO QA Pipeline Quality
# 建立日期：2026-02-27
# 更新至：v2.13（2026-03-05）
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

| 指標 | 學術依據 | Laminar group |
|------|---------|--------------|
| `hit_rate` | TREC | retrieval-eval |
| `mrr` | TREC（Voorhees）| retrieval-eval |
| `precision_at_k` | IR 標準 | retrieval-eval |
| `recall_at_k` | IR 標準 | retrieval-eval |
| `f1_at_k` | IR 標準 | retrieval-eval |
| `ndcg_at_k` | Jarvelin & Kekalainen (2002) | retrieval-eval（v2.13 新增）|
| `top1_category_match` | 本專案 | retrieval-eval（v2.13 新增）|
| `top5_category_coverage` | 本專案（≡ Recall@K）| retrieval-eval（v2.13 新增）|

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

## 當前基準線（v2.12，2026-03-05）

| 指標 | 當前值 | 目標值 | 層次 |
|------|--------|--------|------|
| Relevance | **5.00** / 5 | ≥ 4.5 ✅ | L4（LLM-as-Judge）|
| Accuracy | **4.30** / 5 | ≥ 4.0 ✅ | L4（LLM-as-Judge）|
| Completeness | **3.95** / 5 | ≥ 4.0 | L4（LLM-as-Judge）|
| KW Hit Rate | **73%** | ≥ 85% | L2 |
| MRR | **0.88** | ≥ 0.85 ✅ | L2 |
| Recall@K | **80%** | ≥ 80% ✅ | L2 |
| Precision@K | **76%** | ≥ 80% | L2 |
| F1 Score | **0.73** | ≥ 0.78 | L2 |
| NDCG@K | 待測（預期 ≥ MRR=0.88）| ≥ 0.85 | L2（v2.13 新增）|
| Top-1 Category Match | 待測 | ≥ 0.85 | L2（v2.13 新增）|
| Synonym Coverage | 待測 | ≥ 0.70 | L3（v2.13 新增）|
| Context Relevance | **0.32**（1 query）| ≥ 0.70 | L4（v2.12）|
| Faithfulness | 待測 | ≥ 0.80 | L4（v2.13）|
| Context Precision | 待測 | ≥ 0.70 | L4（v2.13）|

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
