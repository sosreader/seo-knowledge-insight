# EVAL DEFINITION: SEO QA Pipeline Quality
# 建立日期：2026-02-27
# 狀態：基準線已建立（eval_report.md, 2026-02-27 01:20）

---

## 當前基準線（Baseline）

| 指標 | 當前值 | 目標值 | 成本 |
|------|--------|--------|------|
| Relevance | 4.65 / 5 | ≥ 4.5 | — |
| Accuracy | 3.80 / 5 | ≥ 4.0 | Step 2 重跑 |
| Completeness | 3.70 / 5 | ≥ 4.0 | Step 2 重跑 |
| Granularity | 4.65 / 5 | ≥ 4.5 | — |
| Category 正確率 | 10% ⚠️ | ≥ 80% | 見 BUG-001 |
| Retrieval MRR | 0.85 | ≥ 0.80 | — |
| Retrieval LLM Top-1 Precision | 10% ⚠️ | ≥ 70% | 見 BUG-002 |
| KW Hit Rate | 53% | ≥ 70% | reranker |
| Category Hit Rate | 65% | ≥ 80% | 新分類 |

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
