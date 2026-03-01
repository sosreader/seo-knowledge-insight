# /run-pipeline — 執行 SEO Q&A Pipeline

執行 SEO 知識庫完整建構流程（Notion 擷取 → Q&A 萃取 → 去重分類）。

## 用法

```
/run-pipeline [OPTIONS]
```

| 選項        | 說明                             |
| ----------- | -------------------------------- |
| (無)        | 執行完整 fetch-notion→extract-qa→dedupe-classify |
| `--step <name>` | 只執行指定步驟（fetch-notion / extract-qa / dedupe-classify / generate-report / evaluate-qa） |
| `--limit N` | extract-qa / dedupe-classify 只處理前 N 份（測試用） |
| `--force`   | 強制全量重處理（忽略增量比對）   |
| `--dry-run` | 只驗證設定，不實際執行           |

## 執行方式

當使用者下 `/run-pipeline` 時，執行以下命令：

```bash
make pipeline
```

或直接呼叫：

```bash
.venv/bin/python scripts/run_pipeline.py
```

## 分步執行

```bash
# Step 1：Notion 擷取
make fetch-notion

# Step 2：Q&A 萃取（測試用，只處理 3 份）
make extract-qa-test

# Step 2：Q&A 萃取（完整）
make extract-qa

# Step 3：去重 + 分類
make dedupe-classify

# Step 4：週報生成
make generate-report

# Step 5：品質評估
make evaluate-qa
```

## 前置確認

執行任何步驟前，先確認設定正確：

```bash
make dry-run
```

輸出應顯示 `✅ 設定檢查通過`，否則依提示設定 `.env` 檔案（參考 `.env.example`）。

## 輸出位置

- Q&A 資料庫：`output/qa_final.json`
- 每份會議 Q&A：`output/qa_per_meeting/`
- 評估報告：`output/eval_report.md`
- 週報：`output/report_YYYYMMDD.md`
