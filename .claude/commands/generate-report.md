# /generate-report — 生成 SEO 週報（不需要 OpenAI）

**你（Claude Code）就是報告生成引擎**，從 Google Sheets 或 TSV 解析指標，
搜尋知識庫找出相關 Q&A，生成完整的 Markdown 週報。

---

## 用法

```
/generate-report <Google Sheets URL 或 TSV 路徑>
/generate-report https://docs.google.com/spreadsheets/d/...
/generate-report metrics.tsv
```

---

## 執行步驟

### Step A：解析指標

```bash
.venv/bin/python scripts/qa_tools.py load-metrics --source "<URL 或路徑>"
```

輸出格式：`[CORE] 曝光: 月 +3.2% 週 -26.1%` 等。

記錄：
- `CORE` 指標（一定納入）
- `ALERT_DOWN`（月趨勢 < -15% 或週趨勢 < -25%）
- `ALERT_UP`（月趨勢 > +15% 或週趨勢 > +25%）

### Step B：對每個關注指標搜尋知識庫

對每個 CORE + ALERT 指標，依指標名稱搜尋：

```bash
.venv/bin/python scripts/qa_tools.py search --query "<指標名稱相關問題>" --top-k 3
```

參考 `utils/metrics_parser.py` 的 `METRIC_QUERY_MAP`——若指標有對應查詢，使用精準查詢；
否則使用通用模板：`{指標} 大幅{方向} 原因 怎麼處理`。

### Step C：生成週報

依以下 Markdown 模板生成週報，儲存至 `output/report_{YYYYMMDD}.md`：

```markdown
# SEO 週報 — {日期}

## 本週核心訊號

（3-4 點，每點說明一個重要的「現象 → 意義 → 知識庫怎麼說」，不提數字）

## 異常指標解讀

### {指標名稱}：{變化方向}

**觀察**：{具體現象}
**可能原因**：{基於知識庫的分析}
**知識庫引用**：「{Q&A 關鍵句}」（來源：{source_title}，{source_date}）
**建議行動**：{具體 Todo}

---

（重複以上格式，依重要性排列異常指標）

## 本週行動清單

1. {具體 Todo 1}（依據：{知識庫來源}）
2. {具體 Todo 2}（依據：{知識庫來源}）
3. {具體 Todo 3}（依據：{知識庫來源}）

## 直接引用知識庫

**Q**：{最相關的一個 Q&A 的問題}
**A（節錄）**：{答案前 300 字}
**來源**：{source_title}（{source_date}）
```

### Step D：輸出摘要

告訴使用者：
- 解析到的指標數量、關注指標數量
- 引用了哪些 Q&A（幾筆）
- 週報儲存位置

---

## 與 OpenAI 版本的差異

| 項目 | OpenAI 版本 | Claude Code 版本 |
|------|------------|-----------------|
| 指標解析 | fetch_from_sheets() | qa_tools.py load-metrics |
| 知識庫搜尋 | get_embeddings() + cosine | qa_tools.py search（關鍵字）|
| 報告生成 | gpt-5.2 API | Claude Code 直接推理 |
| 需要 API key | 是 | 否 |
