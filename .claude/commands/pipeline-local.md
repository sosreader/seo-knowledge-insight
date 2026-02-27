# /pipeline-local — 完整 Pipeline（不需要 OpenAI API Key）

**你（Claude Code）就是 LLM 引擎**，可以執行完整的 SEO 知識庫建構 pipeline，
包含 Q&A 萃取、去重、分類，**完全不呼叫 OpenAI API**。

## 架構說明

```
Notion API → [Step 1] 擷取 → raw_data/markdown/
                                    ↓
               [Step 2] 你來萃取 Q&A → output/qa_per_meeting/ → qa_all_raw.json
                                    ↓
               [Step 3] 你來去重+分類 → output/qa_final.json
```

- **Step 1**：由 Python 腳本呼叫 Notion API（只需要 NOTION_TOKEN）
- **Step 2**：你讀取 Markdown，直接用語言能力萃取 Q&A（不需要 OpenAI）
- **Step 3**：你對 Q&A 做語意去重、合併、分類（不需要 OpenAI Embedding）

---

## 執行流程

### 0. 確認設定

```bash
make dry-run
```

- ✅ `NOTION_TOKEN` 有設定 → Step 1 可執行
- 其他 API key 不需要（Step 2、3 由你負責）

---

### 1. 執行 Step 1（Notion 擷取）

```bash
make step1
```

這只需要 `NOTION_TOKEN`，完全不使用 OpenAI。
執行完後，`raw_data/markdown/` 目錄下會有 `.md` 會議紀錄檔案。

若 NOTION_TOKEN 未設定，跳過此步驟（前提是 `raw_data/markdown/` 已有檔案）。

---

### 2. 執行 Step 2（Q&A 萃取 — 由你負責，parallel sub-agent）

查看待處理的檔案：

```bash
.venv/bin/python scripts/list_pipeline_state.py --step 2
```

然後，**按照 `/extract-qa` 命令的規則**，對每個未萃取的 Markdown 檔案**同時（parallel）啟動 sub-agent Task**：

- 每個 Task 只負責一個 `.md` 檔，獨立讀取、萃取、存檔
- 所有 Task 並行執行，不要等前一個完成才啟動下一個
- 已有對應 `_qa.json` 的檔案自動跳過（不重複處理）

完成後合併：

```bash
.venv/bin/python scripts/list_pipeline_state.py --merge
```

---

### 3. 執行 Step 3（去重 + 分類 — 由你負責）

確認 `output/qa_all_raw.json` 存在後，**按照 `/dedupe-classify` 命令的規則**：

1. 讀取所有 Q&A
2. 語意去重（你的語言理解，不需要 embedding）
3. 合併重複群組
4. 對每個 Q&A 加分類標籤（category / difficulty / evergreen）
5. 儲存到 `output/qa_final.json`

---

### 4. 完成

輸出摘要：

- 處理的會議數量
- 最終 Q&A 數量
- 各 category 分布
- 輸出檔案位置：`output/qa_final.json`

---

## 快速執行

如果使用者只想完整跑一遍，直接依序執行上面的 Step 1、2、3。

如果只想跑特定步驟：

- 只萃取新增的會議：直接執行 Step 2（會自動跳過已萃取的）
- 只重新分類：執行 Step 3，使用 `--skip-dedup` 等效（只做分類，不去重）

---

## 與 OpenAI 版本的差異

| 項目             | OpenAI 版本            | 本地 AI 版本          |
| ---------------- | ---------------------- | --------------------- |
| Step 2 萃取      | GPT-5.2 API            | Claude Code / Copilot |
| Step 3 embedding | text-embedding-3-small | 語意理解取代向量      |
| Step 3 合併      | GPT-5.2 API            | Claude Code / Copilot |
| Step 3 分類      | GPT-5-mini API         | Claude Code / Copilot |
| 費用             | $$                     | $0 額外費用           |
| 速度             | 依 API 限速            | 依 AI 工具速度        |
