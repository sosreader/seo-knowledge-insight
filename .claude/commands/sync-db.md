# /sync-db — 本地報告與 sessions 推送到 vocus-warehouse

把本機的週報、會議準備與 sessions 經 warehouse-api（Cloudflare Access 保護）寫進 vocus-warehouse 的
`app_report`／`app_meeting_prep`／`app_session`。單向（local → 倉儲）。2026-10-22 起取代舊版
「寫 Supabase」的 `api/scripts/sync-db.ts`。

## 用法

```bash
make sync-db-status   # 本機候選、發布帳冊狀態、遠端是否已有（只讀）
make sync-db-dry      # 試跑：列出會送出的項目與批次，零 HTTP、不需憑證
make sync-db          # 上傳（遠端 hash 相同則 skipped）
make sync-db-force    # 強制覆寫遠端（仍受發布閘門限制）

# 只同步單一類型
make sync-db TYPE=reports        # 或 meeting_prep、sessions
.venv/bin/python scripts/sync_db.py upload --type sessions --no-readback
```

exit code：`0` 成功；`1` 閘門中止、HTTP 失敗或逐筆核對失敗；`2` 參數或憑證設定錯誤。

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

## 委派界線（每週例行流程適用）

- **可委派（唯讀）**：`make sync-db-status`（只打讀取路由）、`make sync-db-dry`（零 HTTP）不寫入，可交給
  `general-purpose`（sonnet）或 `Explore`（haiku，僅狀態查詢）subagent 執行並回報差異清單。
- **不可委派（寫入）**：`make sync-db` 與 `make sync-db-force` 皆對共享的 vocus-warehouse 執行真實寫入
  （sync service token），一律留在主對話執行；或由 subagent 以 `sync-db-dry` 回報待上傳清單後，經主對話
  明確確認再於主對話執行。

> QA Items 和 Snapshots 不在此工具範圍內。
