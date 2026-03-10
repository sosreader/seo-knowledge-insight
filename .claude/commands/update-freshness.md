# /update-freshness — 更新 freshness_score

批次更新 Supabase qa_items 的 freshness_score，使用指數衰減公式。

## 用法

### 預覽（預設，不寫入）

```bash
make update-freshness-dry
```

### 實際寫入

```bash
make update-freshness
```

### 驗證

```bash
make update-freshness-verify
```

## 底層

呼叫 `scripts/update_freshness.py`：
- 公式：`score = exp(-λ * age_days / half_life)`，half_life = 540 天
- evergreen=true 一律維持 1.0
- 差異 < 0.001 的筆跳過
- 批次 PATCH（100 rows/batch）

## 參數

| 參數 | 說明 |
|------|------|
| `--dry-run` | 預覽模式（預設） |
| `--execute` | 實際寫入 |
| `--verify` | 驗證正確性 |
| `--since YYYY-MM-DD` | 只處理指定日期之後 |
| `--limit N` | 只處理前 N 筆 |

## 排程

GitHub Actions 每週一 02:00 UTC 自動執行（`.github/workflows/update-freshness.yml`）。

$ARGUMENTS
