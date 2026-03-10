# /extract-qa — Q&A 萃取（不需要 OpenAI API Key）

**你（Claude Code）就是 LLM 引擎**，從會議紀錄 Markdown 萃取 Q&A，
輸出格式與 `scripts/02_extract_qa.py` 完全相容。

**執行模式：parallel sub-agent（預設）**
你是 orchestrator，對每個未處理的檔案同時啟動獨立的 sub-agent（Task），
全部並行執行後再合併結果，速度大幅提升。

---

## 執行步驟（依序執行，不要跳過）

### Step A：找出待處理的檔案

執行以下命令，列出尚未萃取的 Markdown 檔案：

```bash
.venv/bin/python scripts/qa_tools.py list-unprocessed
```

- 如果所有檔案都已處理完畢，輸出 "全部完成" 並結束。
- 如果待處理數量 > 10 份，先詢問使用者要處理全部或前 N 份。

**追蹤機制說明**：已有對應 `output/qa_per_meeting/{stem}_qa.json`（含有效 `qa_pairs`）的檔案會自動跳過，不會重複處理。

---

### Step B：**並行** 啟動 sub-agents（每個檔案一個 Task）

對 Step A 列出的每個待處理 `.md` 檔案，**同時**（parallel）啟動一個 sub-agent Task。

每個 sub-agent 的指令模板如下（每次填入對應的 `FILE_PATH` 和 `OUTPUT_PATH`）：

```
你是 SEO Q&A 萃取員。
請執行以下工作，完成後回報「完成：{檔名} — {N} 筆 Q&A」：

1. 讀取檔案：{FILE_PATH}
2. 按照下方「Q&A 萃取規則」萃取 Q&A pairs
3. 輸出 JSON 並儲存到：{OUTPUT_PATH}

[Q&A 萃取規則請參考 .claude/commands/extract-qa.md 的完整規則區段]
```

**重要**：所有 sub-agent Task 必須同時（parallel）啟動，不要等前一個完成才啟動下一個。

---

### Step C：等待所有 sub-agents 完成，合併結果

確認全部 Task 都已完成後，執行：

```bash
.venv/bin/python scripts/qa_tools.py merge-qa
```

這會把所有 `output/qa_per_meeting/*_qa.json` 合併成 `output/qa_all_raw.json`。

完成後輸出摘要：「萃取完成：處理 N 個檔案，合併後共 M 筆 Q&A」。

---

## Q&A 萃取規則（你必須遵守）

你同時扮演三個角色來完成 SEO 知識萃取任務：

**知識本體設計師**：每個 Q&A 必須能獨立放進知識庫，讀者不需要看過原始會議就能理解問題與答案。

**SEO 實踐審計員**：在判斷「可執行性」時，評估建議是否有實際工具配套（GSC、GA4 等），以及步驟是否可在真實環境落地。

**品質評估官**：用「完整性 + 可執行性 + 可驗證性」來衡量每個 A 的品質，並根據資訊來源確定程度給出 confidence。

### 萃取規則

1. 每個 Q 必須是一個**自包含**（self-contained）的 SEO 問題
2. 每個 A 應包含具體建議、原因說明和行動方向
3. 如果會議中提到具體的工具、數據或案例，請在 A 中保留
4. **不要萃取**：純行政內容、日程安排、閒聊、模糊對話
5. 萃取粒度要適中：一個 Q&A 聚焦在一個主題，不要拆得太細

### Answer 完整度要求（What / Why / How / Evidence）

- **[What]**：直接說明建議或結論是什麼
- **[Why]**：解釋原因或背後的機制
- **[How]**：給出具體可執行的做法、步驟或工具
- **[Evidence]**：提供數據、工具位置、案例或可驗證的來源

### confidence 評分標準

- 0.85–1.0：顧問明確給出的建議或結論，有具體做法
- 0.7–0.85：會議有討論且有初步共識，但未必是顧問直接建議
- 0.5–0.7：與會者的推測、假設，或僅有部分線索
- 0.3–0.5：待確認事項、尚在觀察中、無明確結論

### keywords 規則

- 限 3–7 個
- 必須是 SEO 領域術語或具體名詞（如 canonical、Discover、CTR）
- 避免通用詞（如「方法」「建議」「討論」）

### 防止幻覺（嚴格遵守）

- **僅從會議文本提取**：不要用通用 SEO 知識補充會議未提及的細節
- **工具路徑要具體**：「在 GSC『索引 > 頁面』查看」而非「在 GA4 查看」
- **不要虛構數字**：會議說「流量下降」，你不能寫「下降約 20%」

---

## 輸出 JSON 格式（每個檔案必須輸出此格式）

```json
{
  "qa_pairs": [
    {
      "question": "問題文字（自包含、可獨立理解）",
      "answer": "包含 [What]/[Why]/[How]/[Evidence] 的完整回答",
      "keywords": ["SEO術語1", "SEO術語2", "SEO術語3"],
      "confidence": 0.85,
      "source_file": "原始檔案名稱.md",
      "source_title": "會議標題",
      "source_date": "YYYY-MM-DD",
      "extraction_model": "claude-code"
    }
  ],
  "meeting_summary": "一句話概述這次會議的主要內容"
}
```

**儲存路徑**：`output/qa_per_meeting/{原始檔名}_qa.json`

---

## 範例

**輸入片段**：「顧問建議把 canonical 都指向沒有 query string 的版本，因為 Google 有時候會自己選錯 canonical。」

**正確萃取**：

```json
{
  "question": "網站有多個帶 query string 的 URL 版本時，canonical 應該如何設定？",
  "answer": "[What] 顧問建議將 canonical 統一指向不帶 query string 的乾淨 URL 版本。[Why] Google 有時會自行選擇錯誤的 canonical，導致爬蟲資源浪費和索引混亂。[How] 在所有帶參數的頁面 <head> 加上 `<link rel=\"canonical\" href=\"https://example.com/page\">` 指向乾淨版本。[Evidence] 可在 GSC「索引 > 頁面 > 系統選擇的 canonical」欄位驗證設定是否生效。",
  "keywords": ["canonical", "query string", "爬蟲預算", "索引"],
  "confidence": 0.9
}
```
