# 模型選擇與 Embedding 比較

> 屬於 [research/](./README.md)。涵蓋 GPT 系列決策、Embedding 模型比較與升級時機。

---

## 2026-09-23 模型盤點與更新

本節以目前原始碼為準；下方早期實驗與 benchmark 屬歷史紀錄，不代表本次升級已完成品質評估。

| 使用位置 | 設定／原模型 | 更新後 | 備註 |
| --- | --- | --- | --- |
| Python Q&A 萃取、合併 | `OPENAI_MODEL` / gpt-5.4-nano | `gpt-6-luna` | `utils/openai_helper.py`；cache 依模型隔離 |
| Python 分類、L4 reality check | `CLASSIFY_MODEL` / gpt-5.4-nano | `gpt-6-luna` | `utils/openai_helper.py`、`utils/maturity_llm_judge.py` |
| Python 週報候選 Q&A rerank | `EVAL_JUDGE_MODEL` / gpt-5.4-nano | `gpt-6-luna` | `scripts/04_generate_report.py`；目前此變數的實際呼叫僅在這裡 |
| TypeScript 一般模型設定 | `OPENAI_MODEL` / gpt-5.4-nano | `gpt-6-luna` | `api/src/config.ts`；Chat 與週報使用各自的設定 |
| TypeScript Chat、SSE、Agent | `CHAT_MODEL` / gpt-5.4-nano | `gpt-6-luna` | `rag-chat.ts`、`rag-chat-stream.ts`、`agent-loop.ts` |
| Python／TypeScript 週報 | `REPORT_MODEL` / gpt-5.4 | `gpt-6-sol` | `04_generate_report.py`、`report-llm.ts` |
| 語意向量 | `OPENAI_EMBEDDING_MODEL` | 保留 `text-embedding-3-small` | 不改向量空間與既有索引 |
| Anthropic rerank、context relevance、context enrichment | 寫死模型 ID | 保留 `claude-haiku-4-5-20251001` | `reranker.ts`、`context-relevance.ts`、`_generate_context.py`；屬獨立供應商路徑 |
| AI SOV OpenAI API CLI | `DEFAULT_MODEL`／workflow input | 保留 `gpt-5.4` | `ingest_ai_sov.py`；屬觀測對象，換模型會改變時序比較口徑。原每週 CI 已於 PR #73 移除 |
| AI SOV Claude CLI | `DEFAULT_CLAUDE_CODE_MODEL` | 保留 `claude-sonnet-5` | `ai_sov_cli_providers.py`；此列為原始碼盤點，未驗證供應商可用性 |
| AI SOV Codex CLI | 未指定時沿用 Codex 使用者設定 | 保留 | `codex-default` 是 metadata fallback label，非 API 型號 |
| 無 OpenAI key 的 fallback | heuristic／本地 hash embedding | 保留 | `claude-code-heuristic`、`local-embed-v1` 是實作識別，不是遠端模型 |
| Claude Code 語意指令 | session 模型 | 保留 | 不受 `OPENAI_MODEL` 等 env 控制 |

### 選型依據與相容性

官方標準價（美元／百萬 token，2026-09-23 查核）：

| 任務層級 | 舊模型輸入／輸出 | 新模型輸入／輸出 |
| --- | --- | --- |
| 高量任務 | gpt-5.4-nano：0.20／1.25 | gpt-6-luna：0.10／0.50 |
| 週報 | gpt-5.4：2.50／15.00 | gpt-6-sol：2.00／10.00 |

此為單價比較；實際費用仍取決於輸入、輸出、cache write 與重試用量，不能直接當成每次任務的節省比例。

- 新模型預設 reasoning effort 為 `medium`，原 5.4 / nano 為 `none`。兩端透過 `model_options.py`／`model-options.ts` 明確保留 `none`，沿用原 token budget、temperature 與 JSON schema。
- Luna／Sol 在 Chat Completions 使用 function calling 需要 `reasoning_effort: none`；Agent 的工具回合與最後收斂請求均帶入。未切換 Responses API。
- 相容參數僅套用精確 ID `gpt-6-luna`、`gpt-6-sol`；其他 env 覆寫維持原請求。若指定快照或其他模型，需另外核對其參數。
- Python `.env` 的 `OPENAI_MODEL` 會覆蓋程式預設。TypeScript 載入順序為既有 process env → `api/.env` → 根目錄 `.env`；升級時需同步檢查這些覆寫值。
- Lambda 與 CI 實際環境覆寫尚未查核；本次未部署。部署前需確認舊 env 不會蓋過新 defaults。
- Python 週報 cache 以 REPORT_MODEL 與 EVAL_JUDGE_MODEL 的組合隔離，本地 fallback 使用獨立 scope；cache key 另含報告日期、weeks 與 QA 版本。切換模型時不會讀到舊模型報告。
- 萃取、合併、分類、L4 與 embedding cache 依模型隔離；不重寫歷史 QA 的 `extraction_model`，不重跑全量萃取或向量建置。

來源：[GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)、[GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)、[GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano)、[GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4)、[GPT-6 遷移指引](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md#migration-quickstart)。

### 驗證

- Python 60 項相關測試通過：設定覆寫、模型參數、週報、分類、L4、cache、本地 fallback。
- TypeScript 29 項相關測試通過：模型參數、週報、Chat、SSE、Agent；`pnpm typecheck` 通過。
- 模型相容性測試涵蓋精確 ID 的 reasoning 參數、其他模型覆寫，以及 Agent 工具回合與最後收斂請求；mock 測試不代表真實 SEO 品質已提升。
- 尚未執行完整 SEO 品質 A/B 評估；上述 mock 測試只能驗證請求參數、路由與快取行為。

---

## 15. 模型選擇決策

### GPT-5 系列全為推理模型（2026-02-27 驗證）

以下為 2026-02-27 對舊版 nano / mini / 5.2 的觀察，不可推廣到所有後續型號；5.4 nano 與 GPT-6 Luna／Sol 均支援 `none` reasoning effort。

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

當時受測模型做 JSON 輸出的設定建議（新模型另依官方規格與任務測試）：

```python
# 分類任務：max_completion_tokens 要夠（reasoning + JSON output 共享）
max_completion_tokens=2048  # 分類任務

# 空回應保護（必須）：
if "category_judgment" not in result:
    continue  # skip-empty，不計入統計
```

### 本專案模型選擇總覽（現行 runtime defaults）

| 任務                  | 模型                   | 理由                         |
| --------------------- | ---------------------- | ---------------------------- |
| Q&A 萃取              | gpt-6-luna           | 萃取預設；品質 A/B 待驗證   |
| Q&A 合併              | gpt-6-luna           | 合併多源資訊，延續 shared default |
| Q&A 分類              | gpt-6-luna           | 結構化輸出，省成本           |
| 週報生成              | gpt-6-sol                | 需要深度分析                 |
| RAG Chat / Agent      | gpt-6-luna           | 對話延遲與成本優先           |
| 週報 Q&A rerank / L4 Judge | gpt-6-luna | 分別由 EVAL_JUDGE_MODEL / CLASSIFY_MODEL 控制 |
| Retrieval Reranker    | claude-haiku-4-5-20251001 | 與 OpenAI 分流，獨立做 re-rank |
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

- Retrieval MRR = 0.88，Hit Rate = 100%（v2.12 基準，20 golden cases，top-k=5）
- v2.11 已實作 Reranker（Claude haiku，over-retrieve×3），KW Hit Rate 提升至 100%
- 目前瓶頸已從 embedding 品質轉移至 Recall@K（77.5%）和 NDCG@K（0.72）

**升級觸發條件**：

1. Recall@K < 70% 或 NDCG@K < 0.65（品質退步）
2. 新增非結構化資料來源（PDF、圖片）需要多模態 embedding
3. 若要支援更精準的中英混合搜尋，考慮 Qwen3-Embedding

---

## gpt-5-mini Reasoning Token 行為

### 模型版本

歷史實驗模型：`gpt-5-mini-2025-08-07`（非現行預設）

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

```env
# 現行預設；Python 設定見 config.py，Chat 設定見 api/src/config.ts
OPENAI_MODEL=gpt-6-luna
REPORT_MODEL=gpt-6-sol
CHAT_MODEL=gpt-6-luna
```

**用途**：Chat 問答可與萃取/合併分流配置，週報生成則用 `REPORT_MODEL` 獨立拉高能力上限。

**影響範圍**：
- `services/rag-chat.ts`：使用 `CHAT_MODEL`
- `04_generate_report.py`：生成使用 `REPORT_MODEL`，候選 Q&A rerank 使用 `EVAL_JUDGE_MODEL`
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
| QA 萃取 | `extraction_model` | `"gpt-6-luna"` | qa_all_raw.json |
| QA 萃取 | `extraction_timestamp` | `"2026-03-05T..."` | qa_all_raw.json |
| QA 合併 provenance | `extraction_provenance` | `{"source_models": ["claude-code", "local-heuristic"], "provenance_status": "mixed-source"}` | qa_final.json / qa_enriched.json |
| Embedding | `embedding_model` | `"text-embedding-3-small"` | eval results |
| 分類 | `classify_model` | `"gpt-6-luna"` | eval results |

### Model-Aware Cache

切換模型時，快取 key 自動隔離：

```
gpt-6-luna + 同一篇文章 → SHA256("gpt-6-luna::文章內容") → cache A
claude-code  + 同一篇文章 → SHA256("claude-code::文章內容")   → cache B
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

## 模型使用政策（從 README 搬入）

**OpenAI 任務使用下表指定的 GPT-5 / GPT-6 模型；禁止新增 GPT-4 系列。Anthropic 與本地 fallback 依各自路由。**

| 用途      | 模型                     | 說明                               |
| --------- | ------------------------ | ---------------------------------- |
| Q&A 萃取  | `gpt-6-luna`           | 萃取預設；品質 A/B 待驗證         |
| Q&A 合併  | `gpt-6-luna`           | 合併多源資訊                       |
| 分類標籤  | `gpt-6-luna`           | 結構化輸出，省成本                 |
| 週報生成  | `gpt-6-sol`（REPORT_MODEL）| 需要深度分析與知識引用             |
| RAG Chat  | `gpt-6-luna`（CHAT_MODEL） | 對話延遲與成本優先            |
| 週報候選 rerank / L4 驗證 | `gpt-6-luna` | 分別使用 `EVAL_JUDGE_MODEL` / `CLASSIFY_MODEL` |
| Reranker  | `claude-haiku-4-5-20251001` | Anthropic 獨立服務，不綁 OPENAI env |
| Embedding | `text-embedding-3-small` | 去重與語意搜尋                     |

> merged / backfilled QA 保留原本的 `extraction_model`，另外以 `extraction_provenance` 記錄來源模型與 merge 策略。

---
