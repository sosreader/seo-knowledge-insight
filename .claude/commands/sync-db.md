# /sync-db — 本地檔案上傳至 Supabase

將本地的 Reports 和 Sessions 上傳到 Supabase。單向（local → DB），跳過已存在項目。

## 用法

### 檢視同步狀態
```bash
make sync-db-status
```

### 執行上傳（跳過已存在）
```bash
make sync-db
```

### 試跑（不寫入）
```bash
make sync-db-dry
```

### 強制覆蓋已存在項目
```bash
make sync-db-force
```

### 只同步特定類型
```bash
cd api && npx tsx scripts/sync-db.ts upload --type reports
cd api && npx tsx scripts/sync-db.ts upload --type sessions
```

## 委派界線（每週例行流程適用）

- **可委派（唯讀）**：`make sync-db-status`、`make sync-db-dry` 不寫入 DB，可交給 `general-purpose`（sonnet）或 `Explore`（haiku，僅狀態查詢）subagent 執行並回報差異清單。
- **不可委派（寫入）**：`make sync-db`（非 `--force` 的實際上傳）與 `make sync-db-force` 皆對共享 Supabase 執行真實寫入（`SUPABASE_SERVICE_KEY`，bypass RLS），一律留在主對話執行；或由 subagent 以 `sync-db-dry` 回報待上傳清單後，經主對話明確確認再於主對話執行。

## 前置條件

`.env` 須設定：
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`（讀取）
- `SUPABASE_SERVICE_KEY`（寫入）

## 同步範圍

| 資料 | 本地位置 | DB 表 | Key |
|------|---------|-------|-----|
| Reports | `output/report_*.md` | `reports` | `date_key` |
| Sessions | `output/sessions/*.json` | `sessions` | UUID `id` |

> QA Items 和 Snapshots 已同步，不在此工具範圍內。
