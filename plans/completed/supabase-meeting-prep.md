# Implementation Plan: Supabase Meeting-Prep 整合

> Generated on 2026-03-21
> Status: PENDING APPROVAL

## Overview

將 meeting-prep 從純檔案系統儲存遷移至 Supabase，與 reports/sessions/snapshots 一致。包含 migration、store、router 改造、sync-db、測試。

## 現況分析

- **儲存**：`output/meeting_prep_YYYYMMDD_hash8.md`（5-8 檔，各 20-26KB）
- **Metadata**：嵌入 HTML comment `<!-- meeting_prep_meta {...} -->`
- **路由**：`api/src/routes/meeting-prep.ts`（223 行）— 3 GET 端點直讀檔案系統
- **Schema**：`api/src/schemas/meeting-prep.ts`（57 行）— 已有完整型別定義
- **測試**：`api/tests/routes/meeting-prep.test.ts`（267 行，18 tests）

## 參考模式

| 元件 | 參考 | 行數 |
|------|------|------|
| Store | `supabase-report-store.ts` | 87 |
| Migration | `004_sessions_table.sql` | 25 |
| Registry | `store-registry.ts` | 14 |
| Sync | `/sync-db` 指令（reports 同步流程） | — |

## Architecture Decisions

| 決策 | 選擇 | 原因 |
|------|------|------|
| 主鍵 | `date_key TEXT`（YYYYMMDD_hash8） | 與 reports 一致，便於識別 |
| Meta 欄位 | `JSONB NOT NULL DEFAULT '{}'` | 結構化查詢 + 未來擴充零 migration |
| Fallback | Supabase → filesystem（與 reports 一致） | Lambda 有 Supabase 但無本地檔案 |
| RLS | SELECT for anon, INSERT/UPDATE/DELETE for service_key | 前端唯讀，寫入走 sync-db |
| Maturity trend | DB 查詢 `meta->'scores'->'maturity'` | 取代掃描全部 .md 檔 |
| 同步方向 | 本地 → Supabase（sync-db）| 報告由 Claude Code 本地生成 |

## Implementation Steps

### Phase 1: Migration + Store（後端核心）

- [x] **Step 1**: 新增 `supabase/migrations/012_meeting_prep_table.sql`（含 RLS service_role only + updated_at trigger，security review 後強化）
  ```sql
  CREATE TABLE IF NOT EXISTS meeting_prep (
    date_key    TEXT        PRIMARY KEY,
    filename    TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    size_bytes  INTEGER     NOT NULL,
    meta        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
  );

  CREATE INDEX IF NOT EXISTS meeting_prep_created_at_idx
    ON meeting_prep (created_at DESC);

  -- GIN index for meta JSONB queries (maturity trend)
  CREATE INDEX IF NOT EXISTS meeting_prep_meta_gin_idx
    ON meeting_prep USING gin(meta jsonb_path_ops);

  ALTER TABLE meeting_prep ENABLE ROW LEVEL SECURITY;

  CREATE POLICY "meeting_prep_select" ON meeting_prep
    FOR SELECT USING (true);

  CREATE POLICY "meeting_prep_service_write" ON meeting_prep
    FOR ALL USING (auth.role() = 'service_role');
  ```

- [x] **Step 2**: 新增 `api/src/store/supabase-meeting-prep-store.ts`（130 行，含 assertSafeDateKey 防注入）
  - `list(): Promise<MeetingPrepSummary[]>` — SELECT date_key, filename, size_bytes, meta ORDER BY created_at DESC
  - `getByDate(dateKey: string): Promise<{summary, content} | null>` — 精確 + 模糊匹配（`date_key LIKE 'YYYYMMDD%'`）
  - `exists(dateKey: string): Promise<boolean>`
  - `save(dateKey: string, filename: string, content: string, meta?: MeetingPrepMeta): Promise<void>` — upsert on date_key
  - `delete(dateKey: string): Promise<boolean>`
  - `listWithMeta(): Promise<MaturityDataPoint[]>` — maturity trend 專用查詢

- [x] **Step 3**: 更新 `api/src/store/store-registry.ts`
  - 新增 `meetingPrepStore` singleton（`hasSupabase() ? new SupabaseMeetingPrepStore() : null`）

### Phase 2: Router 改造

- [x] **Step 4**: 重構 `api/src/routes/meeting-prep.ts`（雙模式 + try/catch 503 + 共用 computeTrendSummary）
  - 三個端點改為雙模式：
    ```typescript
    // GET /api/v1/meeting-prep
    if (meetingPrepStore) {
      items = await meetingPrepStore.list();
    } else {
      items = listMeetingPrepFromFilesystem();
    }
    ```
  - 抽出檔案系統邏輯為 private functions（保持 fallback 可測試）
  - `maturity-trend` 端點：Supabase 模式用 `listWithMeta()` 直接查 JSONB
  - 模糊匹配邏輯在 store 層實作（`date_key LIKE ?%`）

### Phase 3: sync-db 整合

- [ ] **Step 5**: 擴充 `scripts/sync_db.py`（或新增 meeting-prep sync 區塊）
  - 掃描 `output/meeting_prep_*.md`
  - 解析 `<!-- meeting_prep_meta {...} -->` 提取 meta
  - Upsert 至 `meeting_prep` 表
  - 支援 `--dry-run` / `--force`
  - 新增 Makefile targets：`sync-meeting-prep` / `sync-meeting-prep-status`

- [ ] **Step 6**: 更新 `/sync-db` slash command
  - 新增 meeting-prep sync 步驟（在 reports sync 之後）

### Phase 4: 測試

- [x] **Step 7**: 新增 `api/tests/store/supabase-meeting-prep-store.test.ts`（16 tests）
  - list / getByDate（精確+模糊）/ save / delete / exists / listWithMeta
  - Mock supabase client（與其他 store tests 一致）

- [ ] **Step 8**: 更新 `api/tests/routes/meeting-prep.test.ts`
  - 新增 Supabase 模式測試（mock meetingPrepStore）
  - 保留現有 filesystem 測試（meetingPrepStore = null）
  - 預計 +10-12 tests

### Phase 5: 部署 + 資料遷移

- [x] **Step 9**: 執行 migration（via Supabase MCP apply_migration + RLS/trigger hotfix）
  ```bash
  # 透過 Supabase MCP 或 SQL Editor
  mcp__supabase__apply_migration("012_meeting_prep_table")
  ```

- [x] **Step 10**: 初始同步（6/6 檔案已 sync，Python urllib 腳本）
  ```bash
  make sync-meeting-prep          # 本地 5-8 檔 → Supabase
  make sync-meeting-prep-status   # 驗證筆數
  ```

- [ ] **Step 11**: Lambda 重新部署
  ```bash
  cd api && pnpm build
  # deploy lambda（router 改動需重新部署）
  ```

### Phase 6: 文件

- [x] **Step 12**: 更新 CLAUDE.md — meeting-prep 端點加 Supabase 說明 + 新增 Tables 備註
- [x] **Step 13**: 更新 MEMORY.md — 部署架構加 meeting_prep 表 + test count 766

## 資料模型

```
meeting_prep
├── date_key (PK)    TEXT     "20260321_0a708ab1"
├── filename         TEXT     "meeting_prep_20260321_0a708ab1.md"
├── content          TEXT     完整 Markdown（20-26KB）
├── size_bytes       INTEGER  ~22000
├── meta             JSONB    {date, scores: {eeat, maturity}, alert_down_count, question_count, generation_mode, web_sources, web_source_count}
├── created_at       TIMESTAMPTZ
└── updated_at       TIMESTAMPTZ
```

## Risks & Mitigations

| 風險 | 影響 | 對策 |
|------|------|------|
| content 太大（26KB）| Supabase row size | TEXT 無限制，26KB 遠低於 1GB 上限 |
| meta JSON schema drift | 新版報告多欄位 | JSONB 天生 schema-free + 應用層驗證 |
| 模糊匹配效能 | LIKE 'YYYYMMDD%' | 資料量小（<100 rows），無需擔心 |
| Lambda cold start 變慢 | 多一個 store init | meetingPrepStore 為 singleton，無額外 init 成本 |
| sync-db 重複執行 | upsert 衝突 | ON CONFLICT (date_key) DO UPDATE |

## Acceptance Criteria

- [ ] `mcp__supabase__list_tables` 包含 `meeting_prep`
- [ ] `make sync-meeting-prep` 成功同步 5-8 筆
- [ ] `GET /api/v1/meeting-prep` Supabase 模式回傳正確列表
- [ ] `GET /api/v1/meeting-prep/:date` 精確+模糊匹配正常
- [ ] `GET /api/v1/meeting-prep/maturity-trend` 從 JSONB 查詢正確
- [ ] Lambda 端點正常（Supabase 模式）
- [ ] 無 Supabase 時 filesystem fallback 行為不變
- [ ] 新增 tests 全 PASS（預計 +22-27 tests）
- [ ] 現有 18 tests 零退化

## Estimated Scope

| 項目 | 新增/修改 | 預估行數 |
|------|----------|---------|
| Migration SQL | 新增 | ~25 |
| Store class | 新增 | ~100 |
| Store registry | 修改 | +3 |
| Router refactor | 修改 | +40, -20 |
| sync-db | 修改 | +60 |
| Store tests | 新增 | ~120 |
| Route tests | 修改 | +80 |
| Docs | 修改 | +10 |
| **Total** | | **~440 行** |

## Completion

- **完成日期**：2026-03-22
- **驗證結果**：PR #17 已合併；`meeting_prep` 表建立完成（含 RLS + GIN index）；6 筆資料已從本地同步至 Supabase；Lambda 端點 `GET /api/v1/meeting-prep`、`GET /api/v1/meeting-prep/:date`、`GET /api/v1/meeting-prep/maturity-trend` 驗證正常；`SupabaseMeetingPrepStore` + store-registry 整合完成
