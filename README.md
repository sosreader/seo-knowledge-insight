# SEO Q&A 資料庫建構 Pipeline

從 Notion 上累積兩年的 SEO 顧問會議紀錄中，自動萃取結構化的問答資料庫。

## 架構流程

```
Notion API 擷取 → Markdown 轉換（含圖片下載）→ OpenAI 萃取 Q&A → 去重合併 → 分類標籤 → 最終資料庫
```

```
SEO_QA_Rawdata/
├── config.py                    # 設定檔
├── .env                         # 你的 API keys（從 .env.example 複製）
├── scripts/
│   ├── 01_fetch_notion.py       # 步驟 1：從 Notion 擷取
│   ├── 02_extract_qa.py         # 步驟 2：OpenAI 萃取 Q&A
│   ├── 03_dedupe_classify.py    # 步驟 3：去重 + 分類
│   └── run_pipeline.py          # 一鍵執行全部
├── utils/
│   ├── notion_client.py         # Notion API 封裝
│   ├── block_to_markdown.py     # Block → Markdown 轉換
│   └── openai_helper.py         # OpenAI API 封裝
├── raw_data/                    # 原始資料（source of truth）
│   ├── notion_json/             # Notion API 回傳的原始 JSON
│   ├── markdown/                # 轉換後的 Markdown（含圖片引用）
│   └── images/                  # 下載的圖片
└── output/                      # 產出
    ├── qa_per_meeting/          # 每份會議的 Q&A（中間產物）
    ├── qa_all_raw.json          # 所有原始 Q&A（去重前）
    ├── qa_final.json            # 最終 Q&A 資料庫（JSON）
    └── qa_final.md              # 人類可讀的 Markdown 版
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
OPENAI_MODEL=gpt-4o
```

---

## 使用方式

### 一鍵執行完整流程

```bash
python scripts/run_pipeline.py
```

### 分步執行

```bash
# 步驟 1：從 Notion 擷取（建立 raw data）
python scripts/run_pipeline.py --step 1

# 步驟 1 + 篩選特定標題
python scripts/run_pipeline.py --step 1 --filter "SEO 會議"

# 步驟 2：OpenAI 萃取 Q&A
python scripts/run_pipeline.py --step 2

# 步驟 2：先試 3 份看效果
python scripts/run_pipeline.py --step 2 --limit 3

# 步驟 3：去重 + 分類
python scripts/run_pipeline.py --step 3

# 步驟 3：只分類不去重
python scripts/run_pipeline.py --step 3 --skip-dedup
```

### 只檢查設定

```bash
python scripts/run_pipeline.py --dry-run
```

---

## 建議的工作流程

1. **先跑步驟 1**，確認 Notion 資料都拉下來了。去 `raw_data/markdown/` 看幾份，確認內容完整。

2. **步驟 2 先試跑 3-5 份**（`--limit 3`），看萃取出的 Q&A 格式和粒度是不是你要的。如果不滿意，可以調整 `utils/openai_helper.py` 裡的 prompt。

3. **確認後跑完全部步驟 2**。

4. **跑步驟 3** 去重和分類。

5. **人工審核**：看 `output/qa_final.md`，標記需要更新或修正的內容。

---

## 成本估算

以 100-200 場會議、每場約 2000 tokens 計算：

| 步驟         | 模型                   | 預估 tokens                | 預估成本  |
| ------------ | ---------------------- | -------------------------- | --------- |
| 2. 萃取 Q&A  | GPT-4o                 | ~400K input + ~200K output | ~$3-5     |
| 3. Embedding | text-embedding-3-small | ~300K                      | ~$0.01    |
| 3. 合併重複  | GPT-4o                 | ~50K                       | ~$0.5     |
| 3. 分類      | GPT-4o-mini            | ~100K                      | ~$0.05    |
| **合計**     |                        |                            | **~$4-6** |

---

## 重要提醒

- **Raw data 永遠保留**：`raw_data/` 是你的 source of truth。就算 Q&A 萃取不理想，隨時可以重跑步驟 2、3。
- **圖片有效期**：Notion 內建圖片的 URL 是暫時的（1 小時過期），腳本會自動下載到本地 `raw_data/images/`。
- **重跑安全**：每個步驟都可以單獨重跑，不會影響其他步驟的資料。
- **SEO 時效性**：部分 Q&A 的建議可能隨演算法更新而過時，建議定期 review `evergreen: false` 的項目。

---

## 未來擴充

- **RAG 搜尋**：把 `qa_final.json` 匯入向量資料庫（Supabase pgvector / Pinecone），搭配 embedding 做語意搜尋
- **匯入 Notion**：把最終 Q&A 匯回 Notion Database，用欄位篩選查詢
- **自動更新**：每次會議後自動觸發 pipeline，增量處理新紀錄
