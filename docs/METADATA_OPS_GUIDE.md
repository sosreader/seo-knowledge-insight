# QA Metadata 全資料操作指南

> 適用於 `extraction_model`、`freshness_score`、`search_hit_count` 三個欄位的批次操作。
> 所有指令預設 `--dry-run`（不寫入），需加 `--execute` 或使用對應的 Makefile target 才會實際寫入。

---

## 前置條件

```bash
# 確認 .env 已設定 Supabase 連線（SERVICE_KEY 有寫入權限）
grep SUPABASE_URL .env
grep SUPABASE_SERVICE_KEY .env

# 確認 Python 虛擬環境
source .venv/bin/activate
```

---

## 執行順序

建議依序執行，每步先 dry-run 確認再實際寫入。

### Step 1: 回填 extraction_model

標注每筆 QA 由哪個模型萃取（如 `claude-code`、`gpt-4o`）。

```bash
# 1a. 預覽（不寫入）
make backfill-extraction-model-dry

# 1b. 確認統計合理後，實際寫入
make backfill-extraction-model

# 1c. 驗證：NULL count 應為 0
make backfill-extraction-model-verify
```

**原理**：從 `output/qa_per_meeting/*.json` 反查 stable_id 對應的 `extraction_model`，查無者標記 `"claude-code"`。

### Step 2: 套用 freshness_score 指數衰減

根據 `source_date` 計算時效分數，越舊分數越低（用於搜尋排序降權）。

```bash
# 2a. 預覽（不寫入）
make update-freshness-dry

# 2b. 確認衰減值合理後，實際寫入
make update-freshness

# 2c. 驗證：非 evergreen 舊筆 < 1.0
make update-freshness-verify
```

**公式**：`score = exp(-λ * age_days)`，half_life=540 天，floor 0.01，evergreen 永遠 1.0。

**篩選更新**：只更新指定日期之後的筆：

```bash
.venv/bin/python scripts/update_freshness.py --execute --since 2025-01-01
```

### Step 3: 驗證 + 測試

```bash
# TypeScript API 測試（566 tests）
cd api && pnpm test

# 全量 eval（可選，需要 LMNR_PROJECT_API_KEY）
python evals/eval_retrieval.py --model claude-code   # 按模型分群
python evals/eval_retrieval.py                       # 全量（向下相容）
```

---

## search_hit_count（自動追蹤）

此欄位無需手動操作。搜尋 API 命中時自動遞增（fire-and-forget，僅在 Supabase 模式下啟用）。

相關程式碼：
- `api/src/routes/search.ts` — `trackHits()` 函式
- `api/src/store/supabase-qa-store.ts` — `incrementSearchHitCount()` 方法
- Supabase RPC — `increment_search_hit_count(qa_ids TEXT[])`

---

## 定期排程

| 項目 | 排程 | 設定檔 |
|------|------|--------|
| freshness_score 更新 | 每週一 02:00 UTC | `.github/workflows/update-freshness.yml` |
| search_hit_count | 即時（每次搜尋自動） | API 內建 |

GitHub Actions 需設定 Secrets：`SUPABASE_URL` + `SUPABASE_SERVICE_KEY`。

---

## 疑難排解

### dry-run 顯示 0 筆需更新

- `backfill`：所有筆已有 `extraction_model`（已回填過）
- `freshness`：所有筆的 freshness_score 差異 < 0.001（不需更新）

### Supabase PATCH 失敗

- 確認 `SUPABASE_SERVICE_KEY`（非 `ANON_KEY`）有寫入權限
- 檢查網路連線和 Supabase project 狀態

### verify 失敗

- `backfill-verify`：仍有 NULL → 重新執行 `make backfill-extraction-model`
- `freshness-verify`：非 evergreen 舊筆仍為 1.0 → 重新執行 `make update-freshness`

---

## 相關檔案

| 檔案 | 說明 |
|------|------|
| `scripts/backfill_extraction_model.py` | extraction_model 回填腳本 |
| `scripts/update_freshness.py` | freshness_score 衰減腳本 |
| `.github/workflows/update-freshness.yml` | 週排程 workflow |
| `Makefile` L229–301 | 所有 Metadata targets |
