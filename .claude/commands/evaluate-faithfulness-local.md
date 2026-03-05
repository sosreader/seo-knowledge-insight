# /evaluate-faithfulness-local — Faithfulness 評估（RAGAS，不需要 OpenAI）

你是 LLM-as-Judge，評估 Answer 是否完全基於 retrieved contexts（無幻覺）。
全程不需要任何外部 API key。

**RAGAS Faithfulness 定義**：Answer 中每個具體 claim（事實陳述），
是否都能在 retrieved contexts 中找到明確支撐。

---

## 執行步驟

### Step A：抽樣 Q&A

```bash
.venv/bin/python scripts/qa_tools.py eval-sample --size 10 --seed 42
```

讀取輸出，記為 `eval_sample`（10 筆 Q&A，含 question + answer）。

### Step B：對每筆 Q&A 搜尋 retrieved contexts

對每筆 QA 的 question，執行 keyword 搜尋取得 top-5 contexts：

```bash
.venv/bin/python scripts/qa_tools.py search --query "<question>" --top-k 5
```

收集每筆 QA 的：
- `question`
- `answer`
- `contexts`: top-5 retrieved Q&A 的 question+answer 列表

### Step C：Claude Code 判斷（LLM-as-Judge）

對每筆 (answer, contexts) pair，按以下步驟判斷 faithfulness：

1. **識別 claims**：從 answer 中提取所有具體事實陳述
   （例如：「Discover 流量下降主要來自 AMP 索引問題」是一個 claim）

2. **判斷支撐**：對每個 claim，判斷是否能從 contexts 中找到依據
   - `supported`：contexts 中有明確支撐
   - `unsupported`：contexts 中找不到任何支撐

3. **計算分數**：
   ```
   faithfulness_score = supported_claims / total_claims
   ```

**重要規則**：
- 若 answer 是問句或「無資料」類回應，標記 score = 1.0
- Claim 必須是具體陳述，不包含問句或泛泛的 SEO 通識
- Contexts 包含 retrieved Q&A 的 question 和 answer 全文

### Step D：輸出 JSON

```json
{
  "faithfulness": 0.85,
  "sample_size": 10,
  "judge": "claude-code",
  "timestamp": "<YYYY-MM-DD>",
  "per_qa": [
    {
      "stable_id": "...",
      "question_preview": "...",
      "answer_preview": "...",
      "total_claims": 3,
      "supported_claims": 3,
      "score": 1.0,
      "unsupported_claims": []
    },
    {
      "stable_id": "...",
      "question_preview": "...",
      "answer_preview": "...",
      "total_claims": 4,
      "supported_claims": 3,
      "score": 0.75,
      "unsupported_claims": ["某個具體的 claim 文字"]
    }
  ]
}
```

將結果寫入 `/tmp/eval_faithfulness_result.json`。

### Step E（選用）：推送至 Laminar

計算整體 faithfulness 平均值後推送：

```bash
.venv/bin/python scripts/_push_laminar_score.py \
  --metric faithfulness \
  --score <平均分數> \
  --label "v2.13 Claude-Code-as-Judge"
```

### Step F：產出評估報告

```
## Faithfulness 評估報告（<日期>，n=10）

| 指標 | 數值 |
|------|------|
| Faithfulness（平均） | X.XX |
| 完全支撐（1.0） | X 筆 |
| 部分支撐（0.5–0.99） | X 筆 |
| 有幻覺（< 0.5） | X 筆 |

### 發現的幻覺 Claims（若有）
- QA #{id}：<unsupported_claim>

### 結論
{是否達到 faithfulness ≥ 0.80 目標；若有幻覺，建議的修正方向}
```

---

## 與其他指標的關係

| 指標 | 框架 | 評估對象 | 本命令 |
|------|------|---------|--------|
| Faithfulness | RAGAS | Answer ← Contexts | 本命令 |
| Context Relevance | NVIDIA | Query ← Contexts | `/evaluate-context-precision-local` |
| Context Precision | RAGAS | Query ← Contexts | `/evaluate-context-precision-local` |
| Q&A 品質 | 本專案 LLM-as-Judge | Relevance/Accuracy/Completeness | `/evaluate-qa-local` |
