done
# /generate-report — 執行 Step 4 週報生成

直接執行 [scripts/04_generate_report.py](scripts/04_generate_report.py)，使用 OpenAI 產生報告內容。

## 實際行為

- 報告內容由 OpenAI 產生，使用 `config.REPORT_MODEL`
- 若啟用知識庫檢索，候選 Q&A 的 rerank 也會呼叫 OpenAI
- 主要輸入支援三種：Google Sheets URL、metrics snapshot JSON、本機 TSV
- 預設輸出為 `output/report_YYYYMMDD_<hash8>.md`
- 會使用 `output/qa_final.json`、`output/qa_embeddings.npy`、`output/qa_embeddings_index.json` 做知識庫檢索
- 生成後會做內建驗證、寫入 report cache、trend memory 與 artifact version registry

## 必要條件

- `OPENAI_API_KEY`
- 至少一種 metrics 來源：
  - Google Sheets URL
  - `output/metrics_snapshots/*.json`
  - 本機 TSV
- 若不使用 `--no-qa`，建議先確認 Step 3 artifacts 存在且一致：
  - `output/qa_final.json`
  - `output/qa_embeddings.npy`
  - `output/qa_embeddings_index.json`

## 用法

```bash
/generate-report <Google Sheets URL>
/generate-report output/metrics_snapshots/20260306-184745.json
```

對應 CLI 範例：

```bash
.venv/bin/python scripts/04_generate_report.py --input "https://docs.google.com/spreadsheets/d/..." --tab vocus
.venv/bin/python scripts/04_generate_report.py --snapshot output/metrics_snapshots/20260306-184745.json
.venv/bin/python scripts/04_generate_report.py --input metrics.tsv
```

若沒有提供參數，腳本會依序使用：

1. `--input`
2. `config.SHEETS_URL`
3. `utils.metrics_parser.DEFAULT_SHEETS_URL`

## 常用參數

- `--tab vocus`：指定 Google Sheets 分頁
- `--top-k 15`：最終保留的相關 Q&A 數量
- `--weeks 2`：解析最近 N 週指標
- `--output path/to/report.md`：指定輸出檔案路徑
- `--snapshot path/to/snapshot.json`：直接從 metrics snapshot 生成
- `--no-qa`：跳過知識庫檢索
- `--no-cache`：跳過報告 cache，強制重新生成
- `--check`：只做 preflight，不實際生成

## 實際流程

1. Preflight 檢查：確認 `OPENAI_API_KEY`，以及在 QA 模式下檢查 Step 3 artifacts。
2. 解析 metrics：從 snapshot JSON、Google Sheets 或 TSV 載入指標。
3. 偵測異常：依月/週趨勢標記 `CORE`、`ALERT_DOWN`、`ALERT_UP`。
4. 搜尋 Q&A：
   - 優先載入持久化的 `qa_embeddings.npy`
   - 若 embeddings 與當前 query provider 維度不一致，Step 4 會記 warning，並在必要時暫時改用 local query embeddings 相容
   - 正式修復方式是重建 embeddings，不是長期依賴 fallback
5. Rerank 候選：用 OpenAI 從候選池選出最相關的 Q&A。
6. 生成 Markdown：用 OpenAI 根據 metrics summary 與 Q&A context 產生完整週報。
7. 寫檔與驗證：
   - 執行 `_validate_report()`
   - 寫入 `output/report_YYYYMMDD_<hash8>.md`
   - 更新 trend memory 與 artifact version registry

## Embeddings 維護

如果 Step 3 曾在沒有 OpenAI key 的情況下產生 256 維 local embeddings，而現在 Step 4 用的是 1536 維 OpenAI embeddings，建議先重建：

```bash
.venv/bin/python scripts/03_dedupe_classify.py --rebuild-embeddings
```

重建後，`qa_embeddings.npy` 應與目前 provider 維度一致。這次正常狀態應是 `1869 x 1536`。

## 輸出與驗證

- 預設檔名：`output/report_YYYYMMDD_<hash8>.md`
- 若指定 `--output`，會直接寫到指定路徑
- 成功時終端會印出最終報告路徑與版本記錄 ID

### Report meta（前端顯示副標的關鍵）

報告**必須**在檔尾 append `<!-- report_meta {...} -->` HTML 註解，否則前端列表只會顯示 date + hash + KB，**不會出現「週報/雙週報」label、生成方式、模型**等副標。

腳本生成時自動 append；**Claude Code as LLM 模式（手動撰寫）時不可遺漏**。位置在 citations 區塊之後：

```
<!-- citations [...] -->

<!-- report_meta {"weeks":1,"generated_at":"2026-04-27T03:36:23.000Z","generation_mode":"claude-code","generation_label":"Claude Code 語意推理","model":null} -->
```

欄位定義：

| 欄位 | 類型 | 說明 |
|------|------|------|
| `weeks` | number | 1 = 週報、2 = 雙週報 |
| `generated_at` | ISO8601 | 生成時間 |
| `generation_mode` | string | `"claude-code"` / `"openai"` / `"template"` |
| `generation_label` | string | 顯示用標籤：`"Claude Code 語意推理"` / `"OpenAI 生成"` |
| `model` | string \| null | OpenAI 模式填 `"gpt-5.4"`，Claude Code 模式填 `null` |
| `snapshot_id` | string? | 對應 `output/metrics_snapshots/<id>.json`（選填）|
| `experiment_tag` | string? | autoresearch 實驗標籤（選填）|

驗證：`grep -c "report_meta" output/report_*.md` 應 = 1，缺者用 force-sync 補上後重推。

## 常見問題

### 1. `OPENAI_API_KEY` 未設定

Step 4 目前不支援「完全不靠外部 LLM」的本地報告生成路徑；請先設定 API key。

### 2. `size 256 is different from 1536`

這表示 `qa_embeddings.npy` 和當前 query embedding provider 維度不一致。先執行：

```bash
.venv/bin/python scripts/03_dedupe_classify.py --rebuild-embeddings
```

### 3. 想快速確認依賴是否就緒

```bash
.venv/bin/python scripts/04_generate_report.py --check
```

會檢查 `OPENAI_API_KEY` 與 Step 4 需要的 artifacts，不實際生成報告。
