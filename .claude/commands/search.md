# /search — 搜尋 SEO 知識庫（不需要 OpenAI）

**你（Claude Code）就是 RAG 引擎**，呼叫 qa_tools.py 搜尋本地知識庫，
格式化輸出後直接回答使用者問題。

---

## 執行步驟

### Step A：執行關鍵字搜尋

```bash
.venv/bin/python scripts/qa_tools.py search --query "<使用者問題>" --top-k 5
```

- 將使用者問題直接作為 `--query` 參數
- 若使用者指定特定主題，加 `--category`（見下方分類清單）
- 搜尋引擎以關鍵字加權（keywords×3 / question×2 / answer×1）

**可用 category 值**：
- 索引與檢索 / Discover與AMP / Core Web Vitals / 技術SEO / 內容策略
- 搜尋外觀 / 連結建設 / 評估與監控 / 爬蟲優化 / 流量分析

### Step B：格式化輸出

閱讀搜尋結果，依照以下格式回答：

```
## 搜尋結果：{使用者問題}

### 知識庫找到 N 筆相關 Q&A

**[1] {question}**

{完整 answer}

來源：{source_title}（{source_date}）

---

**[2] ...**
```

- 若搜尋到 0 筆，告訴使用者找不到，建議換用其他關鍵字
- 若相關性很高（score > 5），優先展示
- 答案要完整引用，不要自行截短

### Step C：判斷是否需要補充

若知識庫回答不完整，你可以：
1. 基於 SEO 原理補充（但要標明「（推論補充）」）
2. 建議使用者執行 `/extract-qa` 萃取更多會議資料

---

## 使用範例

```
/search canonical 設定問題
/search Discover 流量下降
/search AMP Article 索引
```
