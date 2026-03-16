# Pipeline 操作手冊

> 從 [README.md](../README.md) 搬移的深度操作指南。快速入口請見 README。

---

## 步驟 4：每週 SEO 週報

### 操作流程

**一行指令搞定（最簡方式）：**

```bash
python scripts/run_pipeline.py --step generate-report
```

腳本自動從 [Google Sheets](https://docs.google.com/spreadsheets/d/1fzttLHJfl2Tnecxg0PDKsTmj0-PT5eSsYOivTI6wRdo) 下載最新資料（無需手動複製），報告儲存至 `output/report_YYYYMMDD.md`。

**資料來源優先順序：**

| 優先度 | 方式                                | 說明                              |
| ------ | ----------------------------------- | --------------------------------- |
| 1      | `--input <URL 或檔案>`              | 明確指定 URL 或本機 `.tsv` 檔     |
| 2      | `.env` 裡的 `SHEETS_URL`            | 適合換了試算表 URL 時設定         |
| 3      | `config.py` 的 `DEFAULT_SHEETS_URL` | 內建預設（目前指向 vocus 試算表） |

> **前提**：Google Sheets 須設為「任何知道連結者可檢視」（Anyone with the link - Viewer）。
> **安全性**：腳本驗證 URL 格式與主機名稱，防止注入攻擊（僅允許 `docs.google.com`），回應大小上限 10MB。

### 報告內容

| 區段                  | 說明                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| **本週 SEO 狀況概覽** | 2-3 句總結本週最重要變化                                              |
| **重點指標分析**      | 核心指標（曝光/點擊/CTR/Coverage/Organic Search 等）數值與趨勢        |
| **異常值與潛在原因**  | 月趨勢超過 ±15% 或週趨勢超過 ±20% 的指標，結合 Q&A 知識庫解釋可能原因 |
| **本週行動建議**      | 2-3 條具體 Todo（附 Notion 連結指向原始會議紀錄）                     |
| **相關 SEO 知識補充** | 從 Q&A 知識庫節錄最相關的 1-2 個問答（含原始會議紀錄連結）            |

### 知識庫來源

- 優先使用 `output/qa_enriched.json`（含 Notion 連結；需執行 `make enrich`）
- 降級使用 `output/qa_final.json`（若 ≥50 筆，即步驟 3 完整跑過；無連結）
- 自動降級使用 `output/qa_all_raw.json`（670 筆，步驟 2 產出；無連結）

---

## 步驟 5：品質評估（Evaluation）

### 概述

用 LLM-as-Judge 對 Q&A 萃取品質做五維度自動評估，產出診斷報告。

### 操作方式

```bash
# 基本評估（抽樣 30 筆）
python scripts/run_pipeline.py --step evaluate-qa

# 加大抽樣
python scripts/run_pipeline.py --step evaluate-qa --sample 50

# 帶原始 Markdown 驗證 Faithfulness（更嚴格）
python scripts/run_pipeline.py --step evaluate-qa --with-source

# 含 Retrieval 品質評估
python scripts/run_pipeline.py --step evaluate-qa --eval-retrieval

# 完整評估（品質 + 分類 + Retrieval）
python scripts/run_pipeline.py --step evaluate-qa --sample 50 --with-source --eval-retrieval
```

### 評估維度（1–5 分）

| 維度             | 說明                                           |
| ---------------- | ---------------------------------------------- |
| **Relevance**    | Q&A 是否涵蓋真正有價值的 SEO 知識              |
| **Accuracy**     | A 的內容是否合理且無明顯虛構                   |
| **Completeness** | A 是否包含足夠上下文讓讀者理解                 |
| **Granularity**  | Q 的範圍是否恰當（不太粗也不太細）             |
| **Faithfulness** | （with-source 模式）A 是否忠實反映原始會議文本 |

### Retrieval 品質評估（--eval-retrieval）

| 指標                    | 說明                                           |
| ----------------------- | ---------------------------------------------- |
| **Keyword Hit Rate**    | 檢索結果的 keywords 是否覆蓋預期關鍵字         |
| **Category Hit Rate**   | 檢索結果的分類是否命中預期類別                 |
| **MRR**                 | Mean Reciprocal Rank，第一個相關結果的排名品質 |
| **LLM Top-1 Precision** | LLM 判斷排名第一的結果是否真的相關             |

### 附加檢查

- **Confidence 校準**：模型自評的 confidence 分數是否與實際品質一致
- **Self-contained**：Q 是否不需要看過原文就能理解
- **Actionable**：A 是否提供可執行的建議
- **分類準確度**：category、difficulty、evergreen 標籤是否合理

### 產出

- `output/eval_report.json` — 完整評估結果（每筆 Q&A 的詳細分數）
- `output/eval_report.md` — 人類可讀的摘要報告

---

## 成本估算

> 定價來源：OpenAI Developers Pricing（https://developers.openai.com/api/docs/pricing）

### 使用到的模型與單價（Standard tier；每 1M tokens）

- `gpt-5.2`：$1.75
- `gpt-5-mini`：$0.10（本專案用於「分類標籤」與「分類評估」，見 `utils/openai_helper.py`）
- `text-embedding-3-small`：$0.02（Embeddings；Batch 會更便宜）

> 註：Pricing 頁面的「Text tokens」是以 tokens 計價；模型的 reasoning tokens 會算在 output tokens 內並計費。

### 用你目前已匯出的資料做估算（raw backup 規模）

你目前在 `raw_data/markdown/` 有 87 份 Markdown，總字元數約 163,664。

由於 token 與語言/符號密度有關，這裡用「字元 → tokens」做區間估算：

- 粗估範圍：約 40,916 ~ 81,832 tokens（以 4 chars/token 與 2 chars/token 夾出區間）

你可以用下面指令重算（不會呼叫 API，不花錢）：

```bash
python - <<'PY'
from pathlib import Path

md_dir = Path('raw_data/markdown')
paths = sorted(md_dir.glob('*.md'))

total_chars = 0
for p in paths:
    total_chars += len(p.read_text(encoding='utf-8', errors='replace'))

min_tokens = total_chars // 4
max_tokens = total_chars // 2

print('files=', len(paths))
print('chars=', total_chars)
print('tokens_est_range=', f'{min_tokens}..{max_tokens}')
PY
```

### 依 pipeline 各步驟估算（以你目前 87 份資料）

以下是「可重算」的估算方式（讓你之後換資料量/換模型時能快速更新）。

1. **步驟 2：萃取 Q&A（`gpt-5.2`）**

- 會議內容 tokens：$T_{raw}$（上面那個 40,916~81,832）
- 每份會議的 prompt/格式化開銷：假設 $T_{overhead}=800$ tokens/份（system prompt + JSON 格式要求等）
- 輸出 tokens：高度依「每場產出幾個 Q&A」而變，保守用 $0.6\times T_{raw}$ ~ $1.5\times T_{raw}$

則：

$$
T_{step2} \approx (T_{raw} + 87\times 800) + (0.6T_{raw} \sim 1.5T_{raw})
$$

套入你目前資料量，約：

- input：約 110,516 ~ 151,432 tokens
- output：約 24,549 ~ 122,748 tokens
- 合計：約 135,065 ~ 274,180 tokens
- 成本（`gpt-5.2` $1.75/1M）：約 **$0.24 ~ $0.48**

2. **步驟 3：Embedding 去重（`text-embedding-3-small`）**

- Embedding 的 tokens 大致跟「所有 Q&A 的文字量」同級（通常接近步驟 2 的輸出規模）。
- 若粗略用 output tokens 當 proxy：成本約 **$0.0005 ~ $0.0025**（非常低）

3. **步驟 3：合併重複（`gpt-5.2`）**

- 只有在判定重複的群組才會呼叫模型，且每群組通常 1 次。
- 成本主要看「重複群組數」與「每群組帶入的 Q&A 長度」，通常會遠小於步驟 2。

4. **步驟 3：分類標籤（`gpt-5-mini`）**

- 每個 Q&A 會呼叫 1 次分類。
- 以 **600 個 Q&A、每次約 350 tokens** 估算：成本約 **$0.02**（`gpt-5-mini` $0.10/1M）

> 總結：以你目前已匯出的 87 份 Markdown，整體通常會落在 **小於 $1** 的量級；真正差異會主要來自「每場會議產出的 Q&A 數量」與「去重合併需要呼叫模型的群組數」。

---

## 運維須知

### 重要提醒

- **Raw data 永遠保留**：`raw_data/` 是你的 source of truth。就算 Q&A 萃取不理想，隨時可以重跑步驟 2、3。
- **圖片有效期**：Notion 內建圖片的 URL 是暫時的（1 小時過期），腳本會自動下載到本地 `raw_data/images/`。
- **重跑安全**：每個步驟都可以單獨重跑，不會影響其他步驟的資料。
- **SEO 時效性**：部分 Q&A 的建議可能隨演算法更新而過時，建議定期 review `evergreen: false` 的項目。

### 已知限制

1. **分類呼叫 API 次數 = Q&A 數量** — 沒有批次化，每筆各呼叫一次 `gpt-5-mini`。
2. **圖片只在步驟 1 下載** — 如果 Notion 上的圖片被替換，需要手動清除 `raw_data/images/` 後重跑步驟 1。
