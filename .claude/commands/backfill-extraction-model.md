# /backfill-extraction-model — 追溯回填 extraction_model

追溯回填 Supabase qa_items 的 extraction_model 欄位。

## 用法

### 預覽（預設，不寫入）

```bash
make backfill-extraction-model-dry
```

### 實際寫入

```bash
make backfill-extraction-model
```

### 驗證

```bash
make backfill-extraction-model-verify
```

## 底層

呼叫 `scripts/backfill_extraction_model.py`：
- 掃描 `output/qa_per_meeting/*.json` 反查 stable_id → extraction_model
- 查無者標記 `"claude-code"`（歷史資料主要由 /extract-qa 生成）
- 批次 PATCH 至 Supabase（100 rows/batch）

## 參數

| 參數 | 說明 |
|------|------|
| `--dry-run` | 預覽模式（預設） |
| `--execute` | 實際寫入 |
| `--verify` | 只檢查 NULL 筆數 |
| `--limit N` | 只處理前 N 筆 |

## 驗收

回填後 `SELECT count(*) FROM qa_items WHERE extraction_model IS NULL` 應為 0。

$ARGUMENTS
