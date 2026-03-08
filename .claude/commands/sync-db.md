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
