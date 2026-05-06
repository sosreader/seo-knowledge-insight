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
- 掃描 `output/qa_per_meeting/*.json` 與 `output/qa_per_article/*.json` 反查 stable_id → extraction_model
- 明確 `extraction_model` 優先保留原值
- 找得到 local artifact 但無模型欄位時，推定為 `"claude-code"`（legacy pipeline artifact，而不是把它改寫成目前預設模型）
- 完全無本地證據時，標記 `"legacy-unknown"`，避免捏造最新模型
- 批次 PATCH 至 Supabase（100 rows/batch）

## 判定順序

`backfill_extraction_model.py` 會依 evidence ladder 判定回填值：

1. QA item 或 per-file artifact 已有 `extraction_model`：直接沿用原值。
2. 找得到 local artifact，但該 artifact 沒有模型欄位：視為 legacy Claude pipeline 產物，回填 `"claude-code"`。
3. 完全查無本地對應證據：回填 `"legacy-unknown"`，保留不確定性。

`--dry-run` 會額外輸出 `model_stats`，方便先檢查各 provenance bucket 的分布再決定是否執行寫入。

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
