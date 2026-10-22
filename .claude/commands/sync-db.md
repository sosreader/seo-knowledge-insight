# /sync-db — 本地報告與 sessions 推送到 vocus-warehouse

把本機的週報、會議準備與 sessions 經 warehouse-api（Cloudflare Access 保護）寫進 vocus-warehouse 的
`app_report`／`app_meeting_prep`／`app_session`。單向（local → 倉儲）。2026-10-22 起取代舊版
「寫 Supabase」的 TypeScript 版 `sync-db`（隨 Lambda `seo-insight-api` 退役，已自 repo 移除，見 git history）。

## 用法

```bash
make sync-db-status   # 本機候選、發布帳冊狀態、遠端是否已有（只讀）
make sync-db-dry      # 試跑：列出會送出的項目與批次，零 HTTP、不需憑證
make sync-db          # 上傳（遠端 hash 相同則 skipped）
make sync-db-force    # 強制覆寫遠端（仍受發布閘門限制）
make sync-db-import-ndjson-dry DIR=<匯出目錄>   # 歷史匯入試跑（零 HTTP、不需憑證）
make sync-db-import-ndjson DIR=<匯出目錄>       # 歷史匯入（跳過發布閘門，見下方「歷史匯入模式」）

# 只同步單一類型
make sync-db TYPE=reports        # 或 meeting_prep、sessions
.venv/bin/python scripts/sync_db.py upload --type sessions --no-readback
```

exit code：`0` 成功；`1` 閘門中止、HTTP 失敗或逐筆核對失敗；`2` 參數、憑證或匯出檔設定錯誤。

## 目標與資料流

| 資料 | 本地位置 | 寫入路由 | 讀回路由 | 鍵 |
|------|---------|---------|---------|----|
| Reports | `output/report_*.md` | `POST /internal/sync/reports` | `GET /internal/app/reports/{date_key}` | `date_key` |
| Meeting-Prep | `output/meeting_prep_*_<hash8>.md` | `POST /internal/sync/meeting_prep` | `GET /internal/app/meeting-prep/{date_key}` | `date_key` |
| Sessions | `output/sessions/*.json` | `POST /internal/sync/sessions` | `GET /internal/app/sessions/{id}` | UUID `id` |

Host 預設 `https://warehouse-api.vocus.cc`（`--base-url` 可改，只收 https）。每批 ≤50 筆且 body ≤2 MB，
超過自動切批；單筆就超過 2 MB 時整批中止、不送任何請求。伺服器逐筆回 `created`／`updated`／`skipped`，
腳本逐筆核對回傳的 `content_hash` 與送出的一致，寫入後再用讀取路由讀回核對。
API 契約見 vocus-warehouse `docs/sync-api.md`。

## 憑證

| 檔案（權限 600） | 用途 | 覆寫路徑的環境變數 |
|------|------|------|
| `~/.config/vocus-warehouse/sync.env` | 寫入 `/internal/sync/*` | `VW_SYNC_ENV_FILE` |
| `~/.config/vocus-warehouse/app-read.env` | 讀回核對與 `status` 的遠端比對 `/internal/app/*` | `VW_APP_READ_ENV_FILE` |

兩檔都需 `CF_ACCESS_CLIENT_ID`、`CF_ACCESS_CLIENT_SECRET`（Access service token）。腳本只從檔案讀，
刻意不吃同名環境變數，也絕不印出值。沒有 `app-read.env` 時 `status` 只列本機與帳冊，`upload` 會在寫入前
中止，除非加 `--no-readback`。`.env` 裡的 Supabase 變數與本指令無關。

## 發布閘門（reports、meeting_prep）

只上傳 `data/content-publication-review.json` 登記為 `approved`、且本機檔案 SHA-256 與帳冊相符的版本：

| 本機檔狀態 | 行為 |
|------|------|
| approved 且 hash 相符 | 上傳，`approved_version` 帶 `review:<reviewed_at>:<sha256>` |
| 未登記（`missing_review`）、`pending`、`historical` | 排除，不上傳、不算錯誤 |
| approved 但 hash 不符（`content_changed`） | **整批中止**，列出帳冊與本機 hash，零 HTTP |
| 帳冊缺檔、破損、格式不合 | 整批中止（fail closed） |

`--force` 只影響「遠端 hash 相同要不要覆寫」，不能略過閘門。新版本上傳前必須重新審核，把檔名與
`shasum -a 256 output/<檔名>` 登記進帳冊。Sessions 沿用舊行為，不走閘門。

## content_hash 演算法

- reports／meeting_prep：`sha256:` ＋ 檔案 UTF-8 位元組的 SHA-256 hex（與帳冊 `sha256` 同值）。
- sessions：`sha256:` ＋ `{"title", "messages"}` 以 `sort_keys=True`、`separators=(",", ":")`、
  `ensure_ascii=False` 序列化後 UTF-8 的 SHA-256 hex（不送也不納入 metadata，同舊版）。

## 歷史匯入模式（`--from-ndjson`）

一次性把 Supabase 匯出的 `reports.ndjson.gz`、`meeting_prep.ndjson.gz`、`sessions.ndjson.gz`（連同 `manifest.json`）
搬進 vocus-warehouse。用法：

```bash
make sync-db-import-ndjson-dry DIR=~/Documents/seo-knowledge-insight-backups/2026-10-22/supabase-app-tables
make sync-db-import-ndjson DIR=...                  # 遠端已有且內容不同的列不覆寫，標紅列出並 exit 1
make sync-db-import-ndjson DIR=... TYPE=sessions    # 只匯單一表
.venv/bin/python scripts/sync_db.py upload --from-ndjson DIR --force   # 確認以匯出檔為準後，覆寫內容不同的列
```

| 項目 | 行為 |
|------|------|
| 發布閘門 | **跳過**（歷史列沒有帳冊，`approved_version` 不送，為 NULL）；輸出開頭固定印「歷史匯入模式，未經發布閘門」 |
| 去重 | 先用讀取路由查遠端同鍵：內容相同 → 不送（`[skipped]`）；不同 → 不送、標紅 `[conflict]`、exit 1；`--force` 才覆寫（標紅 `[overwrite]`）。不直接送讓 endpoint 判斷，因為 hash 不同時 endpoint 會直接覆寫既有列（含 S2.2 已登記的 approved_version） |
| 切批 | 每批 ≤50 筆且序列化後 ≤2 MB（依位元組）；單列 >2 MB 時列出全部超大的鍵並整批中止，零 HTTP |
| 輸入檢查 | `manifest.json` 的 sha256 與列數必須相符（缺檔只警告）；格式不合的列（鍵、檔名、NUL、孤立 surrogate、title >200 字、重複鍵）整批中止並列出鍵；`deleted_at` 非 NULL 的列排除，不復活 |
| 讀回對帳 | 逐鍵讀回：reports／meeting_prep 重算 content hash，sessions 比 id／title／訊息筆數；輸出 `verified N｜mismatch M`，任何 mismatch、錯誤或未覆寫的衝突都 exit 1 |
| 憑證 | 需要 sync 與 app-read 兩份（預檢和讀回都要讀取），不支援 `--no-readback` |

欄位對照：`meta`／`metadata` 一律加 `"source": "supabase-2026-10-22"`（不影響 content_hash，前端也不讀）；
reports 的 `meta` 為 NULL 時，先用內文 `report_meta` 解析再加 source（否則讀取路由「meta NULL 才從內文解析」的 fallback 失效）；
`filename` 逐列帶原值（meeting_prep 有 10 列不是預設檔名）；`id`／`size_bytes`／`deleted_at` 不送；
meeting_prep 的原始 `updated_at` 沒有欄位可帶，匯入後為匯入時刻。timestamp 先轉成帶 offset 的 ISO 8601。

## 委派界線（每週例行流程適用）

- **可委派（唯讀）**：`make sync-db-status`（只打讀取路由）、`make sync-db-dry`（零 HTTP）不寫入，可交給
  `general-purpose`（sonnet）或 `Explore`（haiku，僅狀態查詢）subagent 執行並回報差異清單。
- **不可委派（寫入）**：`make sync-db`、`make sync-db-force` 與 `make sync-db-import-ndjson` 皆對共享的 vocus-warehouse 執行真實寫入
  （sync service token），一律留在主對話執行；或由 subagent 以 `sync-db-dry` 回報待上傳清單後，經主對話
  明確確認再於主對話執行。

> QA Items 和 Snapshots 不在此工具範圍內。
