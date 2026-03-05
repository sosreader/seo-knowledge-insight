# /evaluate-context-precision-local — Context Precision 評估（RAGAS，不需要 OpenAI）

你是 LLM-as-Judge，評估 retrieved contexts 中有多少真正有助於回答 query。
全程不需要任何外部 API key。

**RAGAS Context Precision 定義**：在 retrieved contexts 中，
「真正相關且有助於回答 query」的比例。
與 Context Relevance 的差異：Context Precision 的 graded relevance 是 binary（0 或 1）。

---

## 執行步驟

### Step A：準備 golden queries

讀取 `output/evals/golden_retrieval.json`（20 個 golden queries）。

### Step B：對每個 query 搜尋 top-5 contexts

```bash
.venv/bin/python scripts/qa_tools.py search --query "<query>" --top-k 5
```

對全部 20 個 golden queries 執行，收集每個 query 的 top-5 retrieved Q&A。

### Step C：Claude Code 判斷（LLM-as-Judge）

對每個 (query, retrieved_qas) pair，逐一判斷每筆 retrieved Q&A：

**判斷問題**：
> 「這筆 Q&A 是否真的有助於回答原始 query？」

**判斷標準**：
- `1`（有助於）：Q&A 直接涵蓋 query 的核心問題，或提供能解釋異常的相關知識
- `0`（無助於）：Q&A 雖然語意相關但對解決 query 問題無實質幫助，或是關鍵字相符但語境不同

**計算方式**：
```
context_precision = sum(relevant_flags) / len(retrieved_qas)
```

### Step D：輸出 JSON

```json
{
  "context_precision": 0.72,
  "sample_size": 20,
  "judge": "claude-code",
  "timestamp": "<YYYY-MM-DD>",
  "per_query": [
    {
      "query": "Discover 流量 大幅下降 探索演算法 內容策略",
      "scenario": "Discover 流量大幅下降",
      "retrieved_count": 5,
      "relevant_count": 4,
      "precision": 0.8,
      "relevant_flags": [1, 1, 1, 0, 1],
      "irrelevant_qa_ids": ["xxx"]
    }
  ]
}
```

將結果寫入 `/tmp/eval_context_precision_result.json`。

### Step E（選用）：推送至 Laminar

```bash
.venv/bin/python scripts/_push_laminar_score.py \
  --metric context_precision \
  --score <平均分數> \
  --label "v2.13 Claude-Code-as-Judge"
```

### Step F：產出評估報告

```
## Context Precision 評估報告（<日期>，n=20 queries）

| 指標 | 數值 |
|------|------|
| Context Precision（平均） | X.XX |
| Precision = 1.0（全部相關） | X 個 queries |
| Precision < 0.6（多筆不相關） | X 個 queries |

### 最差 queries（Precision < 0.6）
| Query | Precision | 不相關原因 |
|-------|-----------|----------|
| ... | ... | ... |

### 結論
{是否達到 context_precision ≥ 0.70 目標；建議改善方向（擴充 synonyms/調整 top-k/改善 embedding）}
```

---

## 與 Context Relevance 的差異

| 維度 | Context Precision（本命令） | Context Relevance（v2.12 API）|
|------|--------------------------|------------------------------|
| 評估方式 | Claude Code as Judge（互動）| Claude haiku API 呼叫 |
| relevance 評分 | Binary（0 or 1）| Continuous（0–1）|
| 需要 API key | 不需要 | 需要 ANTHROPIC_API_KEY |
| 使用情境 | 離線 session 評估 | 自動化 eval pipeline |
| RAGAS 對應 | Context Precision | Context Relevance（NVIDIA style）|

## Roadmap

- **v2.15**：人工標記 expected_qa_ids → 純 Python 計算（無 LLM 成本）
- **v2.16**：與 Faithfulness 合併為完整 RAG Triad 評估 pipeline
