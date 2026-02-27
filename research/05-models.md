# 模型選擇與 Embedding 比較

> 屬於 [research/](./README.md)。涵蓋 GPT 系列決策、Embedding 模型比較與升級時機。

---

## 15. 模型選擇決策

### GPT-5 系列全為推理模型（2026-02-27 驗證）

**重要發現**：gpt-5 整個系列（nano / mini / 5.2）**全部都是推理模型**，不存在非推理的 gpt-5 選項。

```python
# 實驗驗證 gpt-5-nano：
response.model = "gpt-5-nano-2025-08-07"
reasoning_tokens = 100  # 全部用於推理，content=""
```

測試結果：

| 模型       | max_tokens | 空回應率 | Category 正確率 |
| ---------- | ---------- | -------- | --------------- |
| gpt-5-mini | 2048       | ~5-10%   | **75%** ✅      |
| gpt-5-nano | 2048       | **35%**  | 65% ❌          |

→ gpt-5-nano 表現比 gpt-5-mini 更差，原因是 nano 推理 token 佔用比例更高。

### 正確解法：調整 token budget，而非換模型

所有 gpt-5 系列做 JSON 輸出時的必要設定：

```python
# 分類任務：max_completion_tokens 要夠（reasoning + JSON output 共享）
max_completion_tokens=2048  # 分類任務

# 空回應保護（必須）：
if "category_judgment" not in result:
    continue  # skip-empty，不計入統計
```

### 本專案模型選擇總覽

| 任務                  | 模型                   | 理由                         |
| --------------------- | ---------------------- | ---------------------------- |
| Q&A 萃取              | gpt-5.2                | 需要高品質理解與生成         |
| Q&A 合併              | gpt-5.2                | 需要強推理                   |
| Q&A 分類              | gpt-5-mini             | 省成本，max_tokens=2048 穩定 |
| 週報生成              | gpt-5.2                | 需要深度分析                 |
| LLM Judge（品質評估） | gpt-5.2                | 需要推理能力                 |
| Retrieval 相關性判斷  | gpt-5-mini             | max_tokens=1024 穩定         |
| Embedding             | text-embedding-3-small | 語意向量計算                 |

---

## 16. Embedding 模型比較與升級時機

### 主流 Embedding 模型比較

| 模型                               | 維度 | MTEB 準確度 | 成本                | 語言支援     |
| ---------------------------------- | ---- | ----------- | ------------------- | ------------ |
| **text-embedding-3-small**（現用） | 1536 | 75.8%       | $0.00002/1K         | 多語言       |
| text-embedding-3-large             | 3072 | 80.5%       | $0.00013/1K（6.5x） | 多語言       |
| Qwen3-Embedding-8B（開源）         | 自訂 | MTEB 榜首   | 免費（自架）        | 中英混合最佳 |

### 何時考慮升級 Embedding

**現階段維持 text-embedding-3-small**，原因：

- Retrieval MRR = 0.79，Top-1 Precision = 100%
- 目前 KW Hit Rate 54% 的瓶頸不在 embedding 品質，而在搜尋策略（Reranking）

**升級觸發條件**：

1. 實作 Cross-encoder Reranking 後，KW Hit Rate 仍 < 60%
2. 新增非結構化資料來源（PDF、圖片）需要多模態 embedding
3. 若要支援更精準的中英混合搜尋，考慮 Qwen3-Embedding

---

