# SEO Q&A 資料庫建構 Pipeline

從 Notion 上累積兩年的 SEO 顧問會議紀錄中，自動萃取結構化的問答資料庫。

## 架構流程

```
Notion API 擷取 → Markdown 轉換（含圖片下載）→ OpenAI 萃取 Q&A → 去重合併 → 分類標籤 → 最終資料庫
```

```
seo-knowledge-insight/
├── config.py                    # 設定檔
├── pyproject.toml               # Package 定義（pip install -e . 用）
├── .env                         # 你的 API keys（從 .env.example 複製）
├── scripts/
│   ├── 01_fetch_notion.py       # 步驟 1：從 Notion 擷取
│   ├── 02_extract_qa.py         # 步驟 2：OpenAI 萃取 Q&A
│   ├── 03_dedupe_classify.py    # 步驟 3：去重 + 分類
│   ├── 04_generate_report.py    # 步驟 4：產生每週 SEO 週報
│   ├── 05_evaluate.py           # 步驟 5：Q&A 品質評估（LLM-as-Judge）
│   ├── run_pipeline.py          # 一鍵執行全部
│   ├── extract_qa_helpers.py    # 純邏輯函式（日期擷取、文字切分）
│   └── dedupe_helpers.py        # 純邏輯函式（cosine similarity 矩陣）
├── utils/
│   ├── notion_client.py         # Notion API 封裝
│   ├── block_to_markdown.py     # Block → Markdown 轉換
│   └── openai_helper.py         # OpenAI API 封裝
├── tests/
│   └── test_core.py             # 核心邏輯 unit tests（23 個）
├── raw_data/                    # 原始資料（source of truth）
│   ├── notion_json/             # Notion API 回傳的原始 JSON
│   ├── markdown/                # 轉換後的 Markdown（含圖片引用）
│   └── images/                  # 下載的圖片
└── output/                      # 產出
    ├── qa_per_meeting/          # 每份會議的 Q&A（中間產物）
    ├── qa_all_raw.json          # 所有原始 Q&A（去重前）
    ├── qa_final.json            # 最終 Q&A 資料庫（JSON）
    ├── qa_final.md              # 人類可讀的 Markdown 版
    ├── qa_embeddings.npy        # 持久化 embedding 向量（Step 3 產出，Step 4 載入）
    ├── metrics_sample.tsv      # 範例指標資料（可替换為實際資料）
    ├── report_YYYYMMDD.md       # 產生的每週 SEO 週報
    ├── eval_report.json         # 品質評估報告（JSON）
    └── eval_report.md           # 品質評估報告（Markdown）
```

---

## 前置準備

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 建立 Notion Integration

1. 前往 https://www.notion.so/my-integrations
2. 點「New integration」
3. 填入名稱（例如 `SEO-QA-Exporter`），選擇你的 workspace
4. **Capabilities** 只需要勾 ✅ **Read content**
5. 點「Submit」後複製 **Internal Integration Secret**（以 `ntn_` 開頭）

### 3. 分享頁面給 Integration

1. 打開你放 SEO 會議紀錄的**母頁面**（包含所有子頁面的那個）
2. 點右上角 `···` → `Connections` → 找到你剛建的 Integration → 確認
3. 複製母頁面的 **Page ID**：
   - 打開頁面，URL 長這樣：`https://www.notion.so/你的workspace/頁面標題-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - 最後面那串 32 字元的 hex 就是 Page ID
   - 或者：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` 格式也行

### 4. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入：

```env
NOTION_TOKEN=ntn_你的token
NOTION_PARENT_PAGE_ID=你的母頁面ID
OPENAI_API_KEY=sk-你的key
OPENAI_MODEL=gpt-5.2
```

---

## 使用方式

### 一鍵執行完整流程

```bash
python scripts/run_pipeline.py
```

### 分步執行

每個步驟都可以直接執行，啟動時自動檢查前置步驟的資料是否就緒：

```bash
# 步驟 1：從 Notion 擷取（增量模式，只抓新增/有更新的）
python scripts/01_fetch_notion.py
python scripts/01_fetch_notion.py --force          # 全量重抓

# → 自動檢查：NOTION_TOKEN 是否已設定

# 步驟 2：OpenAI 萃取 Q&A（增量模式，跳過已完成的）
python scripts/02_extract_qa.py
python scripts/02_extract_qa.py --limit 3          # 先試 3 份
python scripts/02_extract_qa.py --force             # 全部重新處理

# → 自動檢查：raw_data/markdown/ 是否有 .md 檔案

# 步驟 3：去重 + 分類
python scripts/03_dedupe_classify.py
python scripts/03_dedupe_classify.py --skip-dedup   # 只分類
python scripts/03_dedupe_classify.py --limit 30     # 測試模式

# → 自動檢查：output/qa_all_raw.json 是否存在

# 步驟 4：產生每週 SEO 週報
python scripts/04_generate_report.py
python scripts/04_generate_report.py --no-qa        # 不使用知識庫
python scripts/04_generate_report.py --input metrics.tsv  # 本機檔案

# → 自動檢查：output/qa_final.json 是否存在（--no-qa 可跳過）

# 步驟 5：品質評估
python scripts/05_evaluate.py
python scripts/05_evaluate.py --sample 50 --with-source
python scripts/05_evaluate.py --eval-retrieval

# → 自動檢查：output/qa_final.json（fallback: qa_all_raw.json）
```

#### 只檢查依賴（不執行）

```bash
python scripts/02_extract_qa.py --check
# 輸出：✅ Step 2: Q&A 萃取 依賴檢查通過
# 或：  ❌ raw_data/markdown/*.md 找到 0 個檔案（需 ≥ 1）
#       💡 請先執行 python scripts/01_fetch_notion.py
```

#### 全流程（保留向下相容）

```bash
python scripts/run_pipeline.py              # 完整 1→2→3
python scripts/run_pipeline.py --step 4     # 單步也行
python scripts/run_pipeline.py --check      # 只檢查所有步驟的依賴
python scripts/run_pipeline.py --dry-run    # 同 --check（向下相容）
```

### 透過 run_pipeline.py 分步（向下相容）

```bash
# 支援所有子腳本的 flags，透過 -- 轉發
python scripts/run_pipeline.py --step 1 --force
python scripts/run_pipeline.py --step 2 --limit 3
python scripts/run_pipeline.py --step 3 --skip-dedup
python scripts/run_pipeline.py --step 4 --tab vocus --input metrics.tsv
python scripts/run_pipeline.py --step 5 --sample 50 --with-source --eval-retrieval
```

---

## 資料完整性說明

### 會議記錄涵蓋範圍

- **最早記錄**：2023-03-20
- **最近記錄**：2026-02-23（持續累積中）
- **會議頻率**：每兩週一次；偶爾延至三週
- **Notion 子頁面總數**：86 筆（含非定期、顧問、特殊會議）
- **本機 Markdown 檔**：87 個（含一份重複的 `SEO_會議_20230920`）

> **檔名規則**：所有 markdown 均採 `YYYYMMDD` 格式（如 `SEO_會議_20230329.md`）。2023 年初期的幾份早期檔案原本只有 `MMDD`（如 `SEO_0614`），**已於** 2026-02-26 補齊年份重命名。

### 已確認的缺口

| 時段                | 說明                                                                                                                                             | 狀態           |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| **2023-04**         | 3/29 到 5/3 中間 35 天（預計約 2 次會議缺失）。2023-04-07 有排程會議，但 Notion 上無記錄，Notion Search API 亦查無結果。推測當時開了但未建頁面。 | ❌ Notion 無檔 |
| **2024-03-20 前後** | 3/6 到 4/3 中間 28 天（預計約 1 次缺失）。                                                                                                       | ❌ Notion 無檔 |

---

## 建議的工作流程

1. **先跑步驟 1**，確認 Notion 資料都拉下來了。去 `raw_data/markdown/` 看幾份，確認內容完整。

2. **步驟 2 先試跑 3-5 份**（`--limit 3`），看萃取出的 Q&A 格式和粒度是不是你要的。如果不滿意，可以調整 `utils/openai_helper.py` 裡的 prompt。

---

3. **確認後跑完全部步驟 2**。

4. **跑步驟 3** 去重和分類。

5. **每週產生週報**：直接執行 `python scripts/run_pipeline.py --step 4`，腳本自動從 Google Sheets 下載最新資料並產生報告，無需手動複製貼上。

6. **評估品質**：執行 `python scripts/run_pipeline.py --step 5 --sample 50`，用 LLM-as-Judge 檢查萃取品質。

7. **人工審核**：看 `output/qa_final.md`，標記需要更新或修正的內容。

---

## 步驟 4：每週 SEO 週報

### 操作流程

**一行指令搞定（最簡方式）：**

```bash
python scripts/run_pipeline.py --step 4
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
| **本週行動建議**      | 2-3 條具體 Todo（引用對應 Q&A 知識）                                  |
| **相關 SEO 知識補充** | 從 Q&A 知識庫節錄最相關的 1-2 個問答                                  |

### 知識庫來源

- 優先使用 `output/qa_final.json`（若 ≥50 筆，即步驟 3 完整跑過）
- 自動降級使用 `output/qa_all_raw.json`（696 筆，步驟 2 產出）

---

## 模型使用政策

**一律使用 GPT-5 系列模型，禁止使用 GPT-4 系列（gpt-4o、gpt-4o-mini 等已淘汰）。**

| 用途      | 模型                     | 說明                               |
| --------- | ------------------------ | ---------------------------------- |
| Q&A 萃取  | `gpt-5.2`                | 主力模型，需要高品質理解與生成     |
| Q&A 合併  | `gpt-5.2`                | 合併多源資訊需要強推理             |
| 分類標籤  | `gpt-5-mini`             | 結構化輸出，省成本                 |
| 週報生成  | `gpt-5.2`                | 需要深度分析與知識引用             |
| 品質評估  | `gpt-5.2` + `gpt-5-mini` | Judge 用主力模型，分類驗證用小模型 |
| Embedding | `text-embedding-3-small` | 去重與語意搜尋                     |

---

## 步驟 5：品質評估（Evaluation）

### 概述

用 LLM-as-Judge 對 Q&A 萃取品質做五維度自動評估，產出診斷報告。

### 操作方式

```bash
# 基本評估（抽樣 30 筆）
python scripts/run_pipeline.py --step 5

# 加大抽樣
python scripts/run_pipeline.py --step 5 --sample 50

# 帶原始 Markdown 驗證 Faithfulness（更嚴格）
python scripts/run_pipeline.py --step 5 --with-source

# 含 Retrieval 品質評估
python scripts/run_pipeline.py --step 5 --eval-retrieval

# 完整評估（品質 + 分類 + Retrieval）
python scripts/run_pipeline.py --step 5 --sample 50 --with-source --eval-retrieval
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

- 粗估範圍：約 40,916 ～ 81,832 tokens（以 4 chars/token 與 2 chars/token 夾出區間）

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

- 會議內容 tokens：$T_{raw}$（上面那個 40,916～81,832）
- 每份會議的 prompt/格式化開銷：假設 $T_{overhead}=800$ tokens/份（system prompt + JSON 格式要求等）
- 輸出 tokens：高度依「每場產出幾個 Q&A」而變，保守用 $0.6\times T_{raw}$ ～ $1.5\times T_{raw}$

則：

$$
T_{step2} \approx (T_{raw} + 87\times 800) + (0.6T_{raw} \sim 1.5T_{raw})
$$

套入你目前資料量，約：

- input：約 110,516 ～ 151,432 tokens
- output：約 24,549 ～ 122,748 tokens
- 合計：約 135,065 ～ 274,180 tokens
- 成本（`gpt-5.2` $1.75/1M）：約 **$0.24 ～ $0.48**

2. **步驟 3：Embedding 去重（`text-embedding-3-small`）**

- Embedding 的 tokens 大致跟「所有 Q&A 的文字量」同級（通常接近步驟 2 的輸出規模）。
- 若粗略用 output tokens 當 proxy：成本約 **$0.0005 ～ $0.0025**（非常低）

3. **步驟 3：合併重複（`gpt-5.2`）**

- 只有在判定重複的群組才會呼叫模型，且每群組通常 1 次。
- 成本主要看「重複群組數」與「每群組帶入的 Q&A 長度」，通常會遠小於步驟 2。

4. **步驟 3：分類標籤（`gpt-5-mini`）**

- 每個 Q&A 會呼叫 1 次分類。
- 以 **600 個 Q&A、每次約 350 tokens** 估算：成本約 **$0.02**（`gpt-5-mini` $0.10/1M）

> 總結：以你目前已匯出的 87 份 Markdown，整體通常會落在 **小於 $1** 的量級；真正差異會主要來自「每場會議產出的 Q&A 數量」與「去重合併需要呼叫模型的群組數」。

---

## 重要提醒

- **Raw data 永遠保留**：`raw_data/` 是你的 source of truth。就算 Q&A 萃取不理想，隨時可以重跑步驟 2、3。
- **圖片有效期**：Notion 內建圖片的 URL 是暫時的（1 小時過期），腳本會自動下載到本地 `raw_data/images/`。
- **重跑安全**：每個步驟都可以單獨重跑，不會影響其他步驟的資料。
- **SEO 時效性**：部分 Q&A 的建議可能隨演算法更新而過時，建議定期 review `evergreen: false` 的項目。

---

## 資料結構（Data Schema）

### `meetings_index.json`

步驟 1 產生的索引檔，記錄所有已擷取的會議紀錄。

```jsonc
[
  {
    "title": "SEO 會議_2024/05/02", // Notion 頁面標題
    "id": "052d1af9-3b5b-4de6-...", // Notion Page ID
    "created_time": "2024-05-15T01:55:00.000Z",
    "last_edited_time": "2024-09-18T01:01:00.000Z",
    "url": "https://www.notion.so/...",
    "json_file": "notion_json/SEO_會議_2024_05_02.json", // 對應的原始 JSON
    "md_file": "markdown/SEO_會議_2024_05_02.md", // 對應的 Markdown
  },
]
```

### `qa_per_meeting/{filename}_qa.json`（步驟 2 中間產物）

```jsonc
{
  "qa_pairs": [
    {
      "question": "Google 如何處理 JavaScript 渲染的頁面？",
      "answer": "Google 會用 headless Chromium 做二次渲染，但...",
      "keywords": ["JavaScript SEO", "渲染", "Googlebot"],
      "confidence": 0.9, // 0-1，萃取品質信心
      "source_file": "SEO_會議_2024_05_02.md",
      "source_title": "SEO 會議_2024/05/02",
      "source_date": "2024-05-02",
    },
  ],
  "meeting_summary": "本次會議討論了 JS 渲染問題與內部連結優化策略",
}
```

### `qa_all_raw.json`（步驟 2 最終合併）

```jsonc
{
  "total_qa_count": 342,
  "meetings_processed": 87,
  "qa_pairs": [
    /* 所有會議的 qa_pairs 合併 */
  ],
  "processing_summary": [
    {
      "file": "SEO_會議_2024_05_02.md",
      "qa_count": 5,
      "summary": "討論了 JS 渲染問題...",
    },
  ],
}
```

### `qa_final.json`（步驟 3 最終資料庫）

```jsonc
{
  "version": "1.0",
  "total_count": 280, // 去重後的數量
  "original_count": 342, // 去重前的數量
  "meetings_processed": 87,
  "qa_database": [
    {
      "id": 1, // 唯一序號
      "question": "...",
      "answer": "...",
      "keywords": ["..."],
      "category": "技術SEO", // 主分類（見下方分類列表）
      "difficulty": "進階", // 基礎 / 進階
      "evergreen": true, // true=常青知識, false=可能過時
      "source_file": "...",
      "source_title": "...",
      "source_date": "...",
      "is_merged": false, // 是否由多筆合併而來
      "merge_count": 3, // (選填) 合併了幾筆
      "merged_from": [
        // (選填) 合併來源
        { "source_title": "...", "source_date": "..." },
      ],
    },
  ],
}
```

### 分類標籤列表（`category`）

| 分類            | 說明                                              |
| --------------- | ------------------------------------------------- |
| 技術SEO         | Crawling、Indexing、Rendering、Structured Data 等 |
| 內容策略        | 內容規劃、改寫、E-E-A-T、內容行銷                 |
| 連結建設        | 外鏈、內鏈、Anchor Text 策略                      |
| 關鍵字研究      | 關鍵字挖掘、搜尋意圖、長尾策略                    |
| 網站架構        | URL 結構、導覽、分類架構、Breadcrumb              |
| Core Web Vitals | LCP、FID/INP、CLS、效能優化                       |
| 本地SEO         | Google 商家、NAP、在地搜尋                        |
| 電商SEO         | 商品頁、分類頁、結構化資料（Product）             |
| GA/GSC 數據分析 | Google Analytics、Search Console 數據解讀         |
| SEO 工具        | Ahrefs、Screaming Frog 等工具使用                 |
| 演算法更新      | Google 演算法更新、應對策略                       |
| 其他            | 無法歸類的項目                                    |

---

## Troubleshooting

### 常見錯誤

| 錯誤                                  | 原因                                         | 解法                                                                                     |
| ------------------------------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `Error code: 401 - Incorrect API key` | OpenAI API key 無效或過期                    | 確認 `.env` 裡的 `OPENAI_API_KEY` 正確，到 https://platform.openai.com/api-keys 重新產生 |
| `Unsupported parameter: 'max_tokens'` | 使用較新模型（如 `gpt-5.2`），舊參數名已棄用 | 已在 `utils/openai_helper.py` 改用 `max_completion_tokens`，若自訂 model 也需注意        |
| `必需環境變數 NOTION_TOKEN 未設定`    | `.env` 不存在或 key 為空（fail-fast 檢查）   | `cp .env.example .env` 後填入；啟動時即檢查必需變數                                      |
| `必需環境變數 OPENAI_API_KEY 未設定`  | `.env` 中 key 為空（fail-fast 檢查）         | 同上；兩個必需變數都要設定                                                               |
| `⚠️ 跳過（無存取權）`                 | Integration 沒有該子頁面的權限               | 到 Notion 母頁面 → `···` → `Connections` → 確認 Integration 已加入                       |
| `Rate limited, waiting Xs`            | API 呼叫太頻繁                               | 正常現象，腳本會自動等待重試                                                             |
| `JSON 解析失敗`                       | OpenAI 回傳非標準 JSON                       | 通常是內容太長導致截斷，可試著降低 `MAX_TOKENS_PER_CHUNK`                                |
| 圖片路徑 `[DOWNLOAD_FAILED: ...]`     | Notion 圖片 URL 已過期                       | 重跑步驟 1 會重新下載（Notion 暫存 URL 有效期約 1 小時）                                 |

### 驗證設定

```bash
# 只檢查 API key 等設定是否正確，不實際執行
python scripts/run_pipeline.py --dry-run
```

---

## 已知限制

1. **分類呼叫 API 次數 = Q&A 數量** — 沒有批次化，每筆各呼叫一次 `gpt-5-mini`。
2. **圖片只在步驟 1 下載** — 如果 Notion 上的圖片被替換，需要手動清除 `raw_data/images/` 後重跑步驟 1。

---

## 開發指南

### 環境設置

```bash
# Clone 後
cd seo-knowledge-insight
cp .env.example .env    # 填入 API keys
pip install -r requirements.txt

# （選擇性）安裝為可開發模式的 package，免去 sys.path 問題
pip install -e ".[dev]"

# 驗證設定
python scripts/run_pipeline.py --dry-run

# 執行測試
python -m pytest tests/ -v
```

### 專案慣例

- **Python 3.9+**，使用 `from __future__ import annotations` 支援新型別語法
- **非同步 I/O**：步驟 1 使用 `httpx.AsyncClient`；步驟 2、3 是同步
- **路徑管理**：所有路徑定義在 `config.py`，用 `pathlib.Path`
- **API 安全**：所有 key 透過 `.env` 載入，絕不 hardcode

### 調整 Prompt

Q&A 萃取的品質主要取決於 `utils/openai_helper.py` 中的 prompt：

- `EXTRACT_SYSTEM_PROMPT` — 控制萃取粒度、格式、語言
- `MERGE_SYSTEM_PROMPT` — 控制合併邏輯（以新日期為準等）
- `CLASSIFY_SYSTEM_PROMPT` — 控制分類維度和標籤列表

建議修改 prompt 後先用 `--limit 3` 試跑，確認效果再全量處理。

### 擴展新分類

修改 `CLASSIFY_SYSTEM_PROMPT` 中的分類列表，同步更新本 README 的「分類標籤列表」。

---

## SEO Insight API

> **狀態**：Phase 2 已完成。`app/` 目錄提供獨立的 FastAPI 服務，讀取 `output/qa_final.json` 與 `output/qa_embeddings.npy` 進記憶體，不依賴任何資料庫。

### 架構

```
app/
├── main.py              # FastAPI 應用入口、lifespan（啟動載入資料）、CORS
├── config.py            # API 專用設定（不依賴 pipeline config.py）
├── core/
│   ├── store.py         # QAStore singleton：載入 JSON+npy，search()/list_qa()
│   └── chat.py          # get_embedding() + rag_chat()（AsyncOpenAI）
└── routers/
    ├── search.py        # POST /api/v1/search
    ├── chat.py          # POST /api/v1/chat
    └── qa.py            # GET  /api/v1/qa, /qa/{id}, /qa/categories
```

### Endpoints

| Method | Path                    | 說明                                                                                 |
| ------ | ----------------------- | ------------------------------------------------------------------------------------ |
| `GET`  | `/health`               | 健康檢查，回傳 `{status, qa_count}`                                                  |
| `POST` | `/api/v1/search`        | 語意搜尋，body: `{query, top_k?, category?}`                                         |
| `POST` | `/api/v1/chat`          | RAG 問答，body: `{message, history?}`                                                |
| `GET`  | `/api/v1/qa`            | 列表查詢，query: `category`, `keyword`, `difficulty`, `evergreen`, `limit`, `offset` |
| `GET`  | `/api/v1/qa/categories` | 所有分類（依數量降序）                                                               |
| `GET`  | `/api/v1/qa/{id}`       | 單筆 Q&A                                                                             |

互動式文件：`http://localhost:8001/docs`

### 本機測試

```bash
# 方式 1：直接啟動
OPENAI_API_KEY=sk-... uvicorn app.main:app --reload --port 8001

# 方式 2：Docker
docker build -t seo-insight-api:local .
docker run -d \
  -p 127.0.0.1:8001:8001 \
  -v $(pwd)/output:/app/output:ro \
  -e OPENAI_API_KEY=sk-... \
  seo-insight-api:local

# 測試
curl http://localhost:8001/health
curl 'http://localhost:8001/api/v1/qa/categories'
```

### 部署（ECR + EC2 SSM）

GitHub Actions workflow：[.github/workflows/deploy-seo-api.yaml](.github/workflows/deploy-seo-api.yaml)

**觸發條件**：push to `main`，且 `app/**`、`requirements_api.txt` 或 `Dockerfile` 有變更。

**所需 GitHub Secrets：**

| Secret                                        | 說明                                                                 |
| --------------------------------------------- | -------------------------------------------------------------------- |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM user，需 ECR push + SSM 執行權限                                 |
| `AWS_REGION`                                  | e.g. `ap-northeast-1`                                                |
| `ECR_DOMAIN`                                  | e.g. `123456789.dkr.ecr.ap-northeast-1.amazonaws.com`                |
| `OPENAI_API_KEY`                              | 真實 key                                                             |
| `EC2_TAG_KEY` / `EC2_TAG_VALUE`               | 找 EC2 用的 tag，e.g. `Name` / `seo-api`                             |
| `OUTPUT_DATA_PATH`                            | EC2 上 output/ 的絕對路徑，e.g. `/home/ec2-user/seo-api-data/output` |

**EC2 也需要**：

- IAM role 有 `ecr:GetAuthorizationToken` + `ecr:BatchGetImage` 權限
- SSM Agent 啟動（Amazon Linux 2 預設已安裝）

### 環境變數（`app/`）

| 變數                     | 預設值                   | 說明                         |
| ------------------------ | ------------------------ | ---------------------------- |
| `OPENAI_API_KEY`         | —                        | 必填                         |
| `OPENAI_MODEL`           | `gpt-5.2`                | RAG chat 模型                |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型               |
| `CORS_ORIGINS`           | `http://localhost:3000`  | 逗號分隔多個 origin          |
| `CHAT_CONTEXT_K`         | `5`                      | RAG chat 帶入的 context 筆數 |

---

## 未來擴充（Roadmap）

### Phase 1 — 增量處理（近期）

- [x] `meetings_index.json` 增加 `status` 欄位（`fetched` / `extracted` / `classified`）
- [x] 步驟 1 比對 `last_edited_time`，只抓新增或有更新的頁面
- [x] 步驟 2 檢查 `qa_per_meeting/` 已存在就跳過（加 `--force` 強制重跑）
- [x] 步驟 2 即時寫入合併檔，中途 crash 不丟失進度

### Phase 2 — API 化（中期）

- [x] 加入 `app/` 目錄，用 FastAPI 提供 REST API（見 [SEO Insight API](#seo-insight-api)）
  - `GET /api/v1/qa` — 列表查詢（支援分類、關鍵字、難度、evergreen、分頁）
  - `GET /api/v1/qa/{id}` — 單筆詳情
  - `GET /api/v1/qa/categories` — 所有分類
  - `POST /api/v1/search` — 語意搜尋（embedding cosine similarity）
  - `POST /api/v1/chat` — RAG 問答（知識庫 + GPT 對話）
- [ ] 前端 `~/Documents/vocus-web-ui` 透過 API 讀取 Q&A 資料庫
- [x] 加入 `pyproject.toml`，讓專案可以 `pip install -e .` 安裝
- [x] Docker 化（`Dockerfile`），部署至 EC2 via ECR + SSM

### Phase 3 — 進階功能（遠期）

- [ ] **RAG 搜尋**：把 `qa_final.json` 匯入向量資料庫（Supabase pgvector / Pinecone），搭配 embedding 做語意搜尋
- [ ] **匯入 Notion**：把最終 Q&A 匯回 Notion Database，用欄位篩選查詢
- [ ] **自動更新**：Notion webhook / 定時 cron 觸發 pipeline，增量處理新紀錄
- [ ] **版本追蹤**：Q&A 修改歷程，保留「何時更新」「因哪次會議更新」
- [ ] **品質儀表板**：追蹤 `confidence` 分布、`evergreen: false` 待 review 項目數量
