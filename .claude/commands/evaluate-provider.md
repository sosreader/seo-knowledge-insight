# /evaluate-provider — LLM Provider SEO 洞察品質評估（不需要 OpenAI）

你是 LLM-as-Judge，評估各 LLM Provider 對 SEO 原始資料的分析品質。全程不需要 OpenAI API key。

引數：`$ARGUMENTS`（目錄路徑，例如 `output/eval_llm_20260302`）

---

## 執行步驟

### Step A：確認原始資料

1. 設定 `eval_dir` = `$ARGUMENTS`（若為空則詢問使用者）
2. 用 Read 工具讀取 `{eval_dir}/source_data.md`（原始資料）
3. 記為 `source_data`，記錄 word_count
4. 若檔案不存在，提示使用者先準備原始資料

**關鍵約束**：Judge 必須看到與各 Provider 完全相同的原始資料，不做摘要、不做篩選。所有 Grounding 評分的佐證必須可追溯至此份 `source_data`。

### Step B：掃描 Provider 輸出

1. 用 Glob 工具搜尋 `{eval_dir}/provider_*.md`
2. 逐一用 Read 工具讀取每份 provider 檔案
3. 記錄每個 provider 的：
   - `provider_name`：從檔名或內容提取（例如 `provider_chatgpt.md` → `chatgpt`）
   - `model`：若內容有標注模型名稱則記錄
   - `word_count`：字數統計
4. 列出掃描結果表格，確認涵蓋範圍後繼續

### Step C：逐 Provider 評分（Judge 協議）

對每個 provider 的輸出，依以下 4 個維度評分。

**評分維度**：

1. **Grounding (1-5)**：引用數字是否可追溯至原始資料
   - 5 = 所有引用數字可逐一追溯至原始資料
   - 4 = 大部分數字正確，少數缺乏精確來源
   - 3 = 引用了部分正確數字，但有模糊或未驗證之處
   - 2 = 多數數字無法對應原始資料，可能來自推測
   - 1 = 未引用任何原始數據，或數字明顯捏造

2. **Actionability (1-5)**：建議是否可執行
   - 5 = 建議有明確對象 + 步驟 + 量化條件
   - 4 = 建議有對象和步驟，但量化條件不足
   - 3 = 有方向但缺乏具體步驟
   - 2 = 建議模糊，難以直接執行
   - 1 = 純描述，無可執行建議

3. **Relevance (1-5)**：是否聚焦 SEO 分析
   - 5 = 聚焦 SEO 診斷，未偏題
   - 4 = 主體為 SEO 但有少量偏題內容
   - 3 = 有 SEO 相關但夾雜偏題內容
   - 2 = SEO 內容佔比不足一半
   - 1 = 完全偏離 SEO 分析

4. **Topic Coverage (0-100%)**：必要主題涵蓋率
   - 預設 5 個必要主題：CTR、檢索未索引、回應時間、Discover、建議
   - 可依原始資料實際內容調整主題清單
   - 計算公式：(涵蓋主題數 / 必要主題總數) * 100%

**評分流程**：

對每個 provider：
1. 逐段比對其輸出與 `source_data`，標記正確引用與錯誤引用
2. Grounding 必須列出至少 3 個具體數字比對（provider 引用值 vs 原始資料值）
3. 檢查是否涵蓋各必要主題
4. 輸出 JSON 格式：

```json
{
  "provider": "chatgpt",
  "model": "gpt-5.2",
  "word_count": 1200,
  "scores": {
    "grounding": {"score": 4, "evidence": [
      {"claim": "CTR 下降 15%", "source_value": "CTR -15.2%", "match": true},
      {"claim": "索引頁面 2000", "source_value": "索引頁面 1,847", "match": false}
    ], "reason": "大部分數字正確，索引頁面數有誤差"},
    "actionability": {"score": 4, "reason": "..."},
    "relevance": {"score": 5, "reason": "..."},
    "topic_coverage": {"score": 80, "covered": ["CTR", "檢索未索引", "回應時間", "建議"], "missing": ["Discover"],
      "notes": "主題清單可依原始資料內容調整，預設 5 項僅為參考"}
  }
}
```

### Step D：儲存結果

1. 彙整所有 provider 的評分為 `eval_results.json`：

```json
{
  "eval_date": "{YYYY-MM-DD，用 Bash date +%Y-%m-%d 取得當天日期}",
  "source_data_path": "{eval_dir}/source_data.md",
  "required_topics": ["CTR", "檢索未索引", "回應時間", "Discover", "建議"],
  "providers": [
    { "provider": "...", "model": "...", "word_count": 0, "scores": { ... } }
  ]
}
```

2. 寫入 `{eval_dir}/eval_results.json`

3. 產出對比報告 `{eval_dir}/comparison_report.md`，格式：

```markdown
## Provider LLM 評估報告（{日期}）

### 原始資料
- 路徑：{source_data_path}
- 字數：{word_count}

### 評分總表

| Provider | Model | 字數 | Grounding | Actionability | Relevance | Topic Coverage |
|----------|-------|------|-----------|---------------|-----------|----------------|
| ... | ... | ... | X/5 | X/5 | X/5 | XX% |

### 各 Provider 詳細評析

#### {provider_name}（{model}）
- **Grounding**：X/5 — {reason}，佐證：{evidence 摘要}
- **Actionability**：X/5 — {reason}
- **Relevance**：X/5 — {reason}
- **Topic Coverage**：XX% — 涵蓋 {covered}，缺少 {missing}

### 結論
{整體排名、優劣勢分析、建議}
```

### Step E：與前次比較（如有）

1. 搜尋 `output/eval_llm_*/eval_results.json` 以及 `{eval_dir}/eval_results.json`，按 `eval_date` 排序
2. 排除本次結果後，取最新一筆作為比較對象
3. 輸出 delta 表格：

```markdown
### 與前次評估比較（{前次日期} vs {本次日期}）

| Provider | Grounding | Actionability | Relevance | Topic Coverage |
|----------|-----------|---------------|-----------|----------------|
| chatgpt  | 3 -> 4 (+1) | 4 -> 4 (=) | 5 -> 5 (=) | 60% -> 80% (+20pp) |
```

若無前次結果，跳過此步驟並說明。

---

## 注意事項

- 此命令不需要 OpenAI API key，Claude Code 本身即為 Judge
- 不新增 Python 檔案，完全由 Claude Code 的推理能力完成評分
- 若原始資料恰好是 TSV 格式，可用 `qa_tools.py load-metrics` 輔助解析
- 若需要知識庫搜尋輔助判斷，可用 `qa_tools.py search`
