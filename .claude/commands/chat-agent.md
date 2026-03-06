# /chat-agent — Agentic SEO 知識庫問答

你（Claude Code）是 Agentic RAG 引擎。收到使用者問題後，
**自主決定搜尋策略、執行多輪搜尋、評估結果充足性**，最後生成結構化回答。

行為規則載入自：`.claude/skills/agentic-rag.md`

---

## 執行流程

### Step 1：問題分析

收到使用者問題 `$ARGUMENTS` 後：

1. 拆解為 1-3 個搜尋意圖（關鍵字、分類、具體術語）
2. 識別英文技術詞 vs 中文描述
3. 判斷可能的知識庫分類

### Step 2：Agent Loop（最多 3 輪）

每輪：

1. **選擇工具**（依 skill 規則路由）：
   - 精確英文術語 → `Grep "術語" output/qa_final.json`
   - 中文語意描述 → `.venv/bin/python scripts/qa_tools.py search --query "..." --top-k 5`
   - 限定分類 → `.venv/bin/python scripts/qa_tools.py search --query "..." --category "..." --top-k 5`
   - 需要完整答案 → `Read output/qa_final.json` 定位片段
   - 知識庫統計 → `.venv/bin/python scripts/qa_tools.py pipeline-status`

2. **評估結果**：
   - >= 3 筆高相關 → 資訊充足，進入 Step 3
   - 1-2 筆 → 換關鍵字 / 換工具 / 換分類再搜
   - 0 筆 → 放寬關鍵字 / 嘗試同義詞
   - 已達 3 輪 → 強制進入 Step 3

3. **記錄**：記住每輪搜了什麼、用了什麼工具、找到幾筆

### Step 3：生成回答

```
**回答**：{核心答案，直接切入重點}

**知識庫依據**：
- {Q&A 關鍵句 1}（來源：{source_title}, {source_date}）
- {Q&A 關鍵句 2}（來源：{source_title}, {source_date}）

**行動建議**：
1. {具體可執行的第一步}
2. {具體可執行的第二步}

**搜尋摘要**：共搜尋 {N} 輪，使用工具：{Grep/search/...}，找到 {M} 筆相關 Q&A
（若知識庫無直接答案，以「（推論）」標記補充內容）
```

### Step 4：維持對話

回答後等待使用者追問：
- 追問相同主題 → 引用已有結果，不重新搜尋
- 追問細節 → 用 Read 取完整 Q&A
- 新主題 → 重新進入 Step 1

---

## 使用範例

```
/chat-agent 什麼是 Core Web Vitals？
/chat-agent 網站流量突然下降怎麼辦
/chat-agent canonical 跟 hreflang 差別
/chat-agent 知識庫有多少筆資料
```

---

## 與 /chat 的差異

| | /chat | /chat-agent |
|---|---|---|
| 搜尋次數 | 固定 1 次 | 自主 1-3 次 |
| 關鍵字 | 直接用問題 | 拆解、重組 |
| 工具 | 只用 qa_tools.py search | 混合 Grep/Read/qa_tools.py |
| 結果評估 | 無 | 評估充足性，不足再搜 |
| 回答附加 | 無 | 搜尋摘要（輪數+工具+筆數） |

---

## 注意事項

- 每輪搜尋結果最多使用 5 筆 Q&A，避免 context 過長
- 引用 Q&A 時務必標示來源（source_title + source_date）
- 若 3 輪都搜不到，建議使用者執行 `/extract-qa` 擴充知識庫
- 分類清單：索引與檢索 / Discover與AMP / Core Web Vitals / 技術SEO / 內容策略 / 搜尋外觀 / 連結建設 / 評估與監控 / 爬蟲優化 / 流量分析
