# Migration 追蹤表整併紀錄 — 2026-08-29

## 為什麼有這份文件

遠端 Supabase（`eqrlomuujichshkbtoat`）的 `supabase_migrations.schema_migrations`
與本地 `supabase/migrations/` 的檔案命名**交集為零**：

- 本地：`001_initial_schema.sql` … `013_warehouse_core_tables.sql`（序號命名）
- 遠端：15 筆時間戳版本（`20260305215414` … `20260321185022`）

`supabase db push` 因此拒絕執行：

```
LegacyDbPushMissingLocalError:
Remote migration versions not found in local migrations directory.
```

整併時會把那 15 筆從追蹤表移除（CLI 的 `--status reverted` 是**刪除追蹤記錄**，
不執行任何還原 DDL，schema 不受影響）。**本檔在移除前保存它們的版本號**，
把審計軌跡從資料庫搬到 git —— 資料庫那份沒有備份，git 這份有。

## 被移除的 15 筆遠端追蹤記錄

| # | 版本號 | 對應時間 |
|---|---|---|
| 1 | `20260305215414` | 2026-03-05 21:54:14 |
| 2 | `20260305230028` | 2026-03-05 23:00:28 |
| 3 | `20260306014009` | 2026-03-06 01:40:09 |
| 4 | `20260306014328` | 2026-03-06 01:43:28 |
| 5 | `20260306014908` | 2026-03-06 01:49:08 |
| 6 | `20260306093010` | 2026-03-06 09:30:10 |
| 7 | `20260306093149` | 2026-03-06 09:31:49 |
| 8 | `20260306101011` | 2026-03-06 10:10:11 |
| 9 | `20260308133616` | 2026-03-08 13:36:16 |
| 10 | `20260308133619` | 2026-03-08 13:36:19 |
| 11 | `20260310091602` | 2026-03-10 09:16:02 |
| 12 | `20260313230745` | 2026-03-13 23:07:45 |
| 13 | `20260315154631` | 2026-03-15 15:46:31 |
| 14 | `20260321153639` | 2026-03-21 15:36:39 |
| 15 | `20260321185022` | 2026-03-21 18:50:22 |

### 未能保存的部分（誠實標註）

**SQL statements 內文沒有撈到。** `supabase db dump` 需要 DB password：
直連（`db.*.supabase.co:5432`）在本機 IPv6 逾時；pooler URL 不含密碼。
而 `supabase migration list` 走的是 access token 路徑，讀得到版本清單但讀不到內文。

判斷是不值得為此卡住：**這些 migration 實際做了什麼，最終真相是 schema 本身**，
而 schema 已於同日逐欄驗證（見下）。版本號與時間是可追溯的錨點，
內文是過程紀錄。

## 整併前的實際 schema 狀態（2026-08-29 逐欄驗證）

用 PostgREST 對每個 migration 實際動到的物件逐一探測：

| 本地 migration | 狀態 | 驗證依據 |
|---|---|---|
| `001` ~ `009` | ✓ 已套用 | `qa_items` 存在且有資料、`009` 的 `maturity_relevance` / `metadata` 欄位在 |
| `010_retrieval_metadata_columns` | ✗ 未套用 | `qa_items.primary_category` → `42703 column does not exist` |
| `011_snapshot_maturity_column` | ✗ 未套用 | `qa_items.maturity` → `42703` |
| `012_meeting_prep_table` | ✓ 已套用 | `meeting_prep` 存在且有資料 |
| `012_soft_delete` | ✓ 已套用 | `reports.deleted_at` / `sessions.deleted_at` / `metrics_snapshots.deleted_at` 三張皆在 |
| `013_warehouse_core_tables` | ✗ 未套用 | `cwv_hourly` → `PGRST205 table not found` |

> **探測時的一個教訓**：初次探測誤查 `qa_items.deleted_at` 與 `learnings.deleted_at`
> 並據此判定 `012_soft_delete` 只套用三分之一 —— 但那個 migration 從來沒碰過那兩張表。
> **探測目標必須從該 migration 的 DDL 推導，不能從印象。**
> 同時，初次以 PostgREST 探測 `supabase_migrations` 得到 404 而判定「沒有追蹤表」，
> 實際是 PostgREST 預設只暴露 `public` schema。兩則已沉澱為 KB learned skill
> `probe-blindness-absence-in-a-tool-that-cannot-see-it`。

## 整併動作

1. 保存本檔（審計軌跡進 git）
2. `supabase migration repair --status applied` 標記 `001`–`009`、`012`
   —— 把上表已驗證的真相寫進追蹤表，不執行任何 DDL
3. `supabase migration repair --status reverted <上表 15 筆>`
   —— 移除冗餘簿記，schema 不受影響
4. `supabase db push` —— 屆時只會執行 `010`、`011`、`013`

### 為什麼這個順序比「整批重跑」安全

`012_soft_delete` 含 **4 條 `ALTER POLICY`**，而 PostgreSQL 的 `ALTER POLICY`
**沒有 `IF EXISTS` 語法** —— 若目標 policy 不存在就會報錯並中斷該檔。
步驟 2 把 `012` 標成 applied 而不重跑它，**這個風險在本方案中不會被觸發**。
只有走「整批重跑 001–013」才會撞到。與直覺相反：完整整併比保守重跑更安全。
