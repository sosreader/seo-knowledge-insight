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

## gpt-5-mini Reasoning Token 行為

### 模型版本

現用：`gpt-5-mini-2025-08-07`

### reasoning_tokens 特性

gpt-5-mini 屬於 reasoning model，回應中的 `completion_tokens_details` 包含：

```json
{
  "reasoning_tokens": 1024,
  "output_tokens": 512
}
```

`reasoning_tokens` 是模型內部「思考」消耗的 tokens，不出現在 content 中。如果 `max_completion_tokens` 設定過低（預設 1024），reasoning 本身就可能耗盡預算，導致 `content = ""`。

### 與 `response_format` 的相容性問題

**症狀**：搭配 `json_schema` response_format，回傳 `content` 為空字串或 None。

**根因**：reasoning model 先算完 reasoning tokens，再輸出 content。若 token budget 不足，content 被截斷。JSON schema constraint 進一步增加輸出成本。

**正確做法**：

```python
# 錯誤：response_format + reasoning model
openai.chat.completions.create(
    model="gpt-5-mini-2025-08-07",
    response_format={"type": "json_schema", ...},  # 造成空 content
    max_completion_tokens=1024,  # 太小
)

# 正確：prompt-based JSON + 足夠的 token budget
openai.chat.completions.create(
    model="gpt-5-mini-2025-08-07",
    # 不傳 response_format
    max_completion_tokens=4096,  # 足夠 reasoning + output
    messages=[..., {"role": "user", "content": "...請以 JSON 格式輸出..."}],
)
```

### 偵測 reasoning model

```python
details = response.choices[0].message.model_dump().get("usage", {})
# 或
details = response.usage.completion_tokens_details
is_reasoning = getattr(details, "reasoning_tokens", 0) > 0
```

### 本專案受影響的地方

- `scripts/compare_providers.py` — Judge 呼叫（已修正）
- 未來任何使用 gpt-5-mini 搭配 `response_format` 的場景

詳見：`~/.claude/skills/learned/openai-reasoning-model-no-response-format.md`

---

## CHAT_MODEL 獨立設定（v2.22，2026-03-06）

v2.22 起，`CHAT_MODEL` 環境變數獨立於 `OPENAI_MODEL`，讓 Chat 問答可使用不同模型：

```python
# config.py
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")      # 萃取/分類/報告
CHAT_MODEL   = os.getenv("CHAT_MODEL", "gpt-5.2")         # RAG Chat 問答
```

**用途**：Chat 問答可切換至更便宜的模型（如 `gpt-5-mini`），而萃取/報告仍用 `gpt-5.2`。

**影響範圍**：
- `services/rag-chat.ts`：使用 `CHAT_MODEL`
- `04_generate_report.py`：使用 `OPENAI_MODEL`
- `02_extract_qa.py`：使用 `OPENAI_MODEL`
- Cache key：`extraction_model` 記錄實際使用的模型名稱

---

## Model Provenance Tracking（v2.8，2026-03-05）

### 為什麼需要追蹤模型版本

模型升級（如 gpt-5 → gpt-5.2）時，pipeline 產出品質可能改變。若不記錄「哪個模型版本產出了什麼」，無法：

1. 判斷品質變化是模型升級還是資料變動造成
2. 回滾到「上次品質穩定」的模型版本
3. 量化模型升級的 ROI

### 本專案追蹤機制

| 層級 | 欄位 | 範例值 | 記錄位置 |
|------|------|--------|---------|
| QA 萃取 | `extraction_model` | `"gpt-5.2"` | qa_all_raw.json |
| QA 萃取 | `extraction_timestamp` | `"2026-03-05T..."` | qa_all_raw.json |
| Embedding | `embedding_model` | `"text-embedding-3-small"` | eval results |
| 分類 | `classify_model` | `"gpt-5-mini"` | eval results |

### Model-Aware Cache

切換模型時，快取 key 自動隔離：

```
gpt-5.2 + 同一篇文章 → SHA256("gpt-5.2::文章內容") → cache A
gpt-5   + 同一篇文章 → SHA256("gpt-5::文章內容")   → cache B
```

不傳 model 參數時退化為 `SHA256(content)`，向下相容。

### 模型升級評估清單

切換 extraction/embedding/classify 模型前：

- [ ] 用 `/evaluate-model-ab` 抽樣 10 篇做 A/B 對比
- [ ] 確認 4 維度平均分 >= 現有基準線
- [ ] 確認 Retrieval MRR 不下降（若換 embedding model）
- [ ] 清除對應 namespace 的舊 cache（`make cache-clear ns=extraction`）
- [ ] 全量重跑後更新基準線（`eval-save --update-baseline`）

---
