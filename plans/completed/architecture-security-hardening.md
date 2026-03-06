# Architecture & Security Hardening Plan

> 來源：4-agent 全面審查（Architect + Security + Database + Code Reviewer）
> 建立日期：2026-03-06
> **完成日期：2026-03-06**
> 發現總數：51 項（CRITICAL 4 / HIGH 16 / MEDIUM 23 / LOW 8）
> **狀態：已完成** — 6 Phase 全部完成，353 tests passing，coverage 80%+
>
> **未處理項目（LOW/需手動）：**
> - 1.1/1.2 Lambda CORS 收緊（需確認前端網域後用 AWS CLI 設定）
> - 5.2 Python emoji 移除（LOW 優先級，不影響功能）

---

## Phase 1: 安全緊急修復（CRITICAL + HIGH Security）

預計影響：生產環境安全風險直接降低

### 1.1 [CRITICAL] Lambda CORS AllowOrigins 收緊

**問題**：Lambda Function URL 的 `AllowOrigins=*` + `AuthType=NONE`，任何 origin 可直接呼叫。
**修復**：

```bash
aws lambda update-function-url-config \
  --function-name seo-insight-api \
  --cors '{"AllowOrigins":["https://admin.vocus.cc"],...}' \
  --region ap-northeast-1 --profile seo-deployer
```

> 注意：需確認實際前端網域，可能需要 AskUserQuestion。

### 1.2 [CRITICAL] Lambda 環境變數設定 CORS_ORIGINS

**問題**：應用層 CORS 預設 `localhost:3000`，生產環境未覆寫。
**修復**：Lambda 環境變數加入 `CORS_ORIGINS=https://admin.vocus.cc`。

### 1.3 [HIGH] POST /metrics SSRF 修復 — URL 白名單

**檔案**：`api/src/schemas/pipeline.ts:28-31`
**修復**：`metricsRequestSchema.source` 加 `.refine()` 限制為 `docs.google.com` / `sheets.google.com`。

### 1.4 [HIGH] HTTP Security Headers middleware

**新增檔案**：`api/src/middleware/security-headers.ts`
**修改檔案**：`api/src/index.ts`（掛載 middleware）
**Headers**：`X-Content-Type-Options: nosniff`、`X-Frame-Options: DENY`、`Strict-Transport-Security`、`Referrer-Policy`

### 1.5 [HIGH] Auth fail-fast（生產環境）

**檔案**：`api/src/middleware/auth.ts:15-21`
**修復**：`NODE_ENV=production` 且 `SEO_API_KEY` 未設定時回傳 503，而非靜默放行。

### 1.6 [HIGH] Session ID 格式驗證

**檔案**：`api/src/routes/sessions.ts:85-86, 96, 177`
**修復**：在路由層加入 UUID regex 驗證，防止 PostgREST filter bypass。

---

## Phase 2: 資料庫安全 + Migration 補齊

### 2.1 [CRITICAL] 確認 sessions/synonym_custom/learnings RLS 狀態

**動作**：透過 Supabase MCP 執行 SQL 確認 `rowsecurity`。
**後續**：若 RLS 未啟用，立即啟用 + 設定 policy。

### 2.2 [HIGH] 補齊 3 個 table 的 migration

**新增檔案**：
- `supabase/migrations/004_sessions_table.sql`
- `supabase/migrations/005_synonym_custom_table.sql`
- `supabase/migrations/006_learnings_table.sql`

包含：CREATE TABLE、RLS 啟用、policy 定義、索引。

### 2.3 [HIGH] match_qa_items() 加 ivfflat.probes

**檔案**：`supabase/migrations/003_match_qa_rpc.sql`
**修復**：新 migration `007_rpc_ivfflat_probes.sql`，將 RPC 改為 `plpgsql` + `SET LOCAL ivfflat.probes = 5`。

### 2.4 [MEDIUM] search_qa_items_keyword() 加 `AND embedding IS NOT NULL`

**檔案**：同 007 migration 一併處理。

---

## Phase 3: Tech Debt 清除

### 3.1 [HIGH] 移除 Legacy Python API

**刪除**：
- `app/` 整個目錄（17 檔）
- `Dockerfile`（root，服務 Python API）
- `requirements_api.txt`
- `docker-compose.yml` 中 `seo-api` service
- `.github/workflows/deploy-seo-api.yaml`
- Python API 相關 tests（`tests/test_api_*.py` 中測 Python FastAPI 的部分）

**保留**：`docker-compose.yml` 中 `seo-api-ts` service。

### 3.2 [MEDIUM] 統一 CI workflow NOTION_TOKEN 命名

**檔案**：`.github/workflows/etl-and-deploy.yml:39,46`
**修復**：`NOTION_API_KEY` → `NOTION_TOKEN`（與 `.env.example` 和 `config.py` 一致）。

---

## Phase 4: 程式碼品質重構

### 4.1 [HIGH] 抽取 IQAStore interface + 消除 listQa 重複

**新增檔案**：`api/src/store/qa-filter.ts`（共用篩選/排序邏輯）
**修改檔案**：
- `api/src/store/qa-store.ts` — 使用共用邏輯
- `api/src/store/supabase-qa-store.ts` — 使用共用邏輯 + 修復 `results.sort()` mutation

**關鍵修復**：`SupabaseQAStore.listQa:273` in-place `results.sort()` → `[...results].sort()`

### 4.2 [HIGH] 拆分 pipeline.ts（798 行）

**新增檔案**：
- `api/src/utils/pipeline-fs.ts`（readMeetingsIndex、buildSourceDocs、findUnprocessed、readFetchLogs）
- `api/src/utils/snapshot-store.ts`（listSnapshots、readSnapshot、generateSnapshotId）

**修改檔案**：
- `api/src/routes/pipeline.ts` — 只保留路由處理器 + import 移到頂部
- 移除 `countQAPerArticle()` dead code
- `meetingEntrySchema` 移至 `schemas/pipeline.ts` 統一匯出

### 4.3 [HIGH] 合併 itemToSource 重複

**新增**：在 `api/src/schemas/chat.ts` 匯出 `itemToSource()`
**修改**：
- `api/src/routes/chat.ts:12-27` — import 共用版本
- `api/src/services/rag-chat.ts:51-63` — import 共用版本

### 4.4 [HIGH] search.ts 行內型別 → QAItem

**檔案**：`api/src/routes/search.ts:20-21`
**修復**：`import type { QAItem }` 取代 300 字元行內型別。

### 4.5 [MEDIUM] SUPABASE_TIMEOUT_MS 統一至 supabase-client.ts

**修改**：移除 `supabase-learning-store.ts:11`、`supabase-session-store.ts:14`、`supabase-synonyms-store.ts:13` 的重複定義，改為從 `supabase-client.ts` import。

### 4.6 [MEDIUM] getBySeq O(1) 查找

**修改**：`qa-store.ts` + `supabase-qa-store.ts` — 在 `load()` 時建立 `seqIndex: Map<number, QAItem>`。

---

## Phase 5: Python 程式碼清理

### 5.1 [HIGH] print() → logging

**檔案**：
- `scripts/02_extract_qa.py`（5 處 print）
- `utils/notion_client.py`（19 處 print）
- 其他含 print 的 scripts/、utils/ 檔案

**修復**：全部替換為 `logger.info()` / `logger.debug()`。

### 5.2 [LOW] 移除 Python 腳本中的 emoji 輸出

**檔案**：`scripts/02_extract_qa.py`、`scripts/03_dedupe_classify.py`、`utils/notion_client.py`

---

## Phase 6: 測試覆蓋率提升（80% 門檻）

> 現狀：Line 65.48% / Function 61.39% / Branch 46.74%

### 6.1 [CRITICAL] QAStore file-mode 測試

**新增檔案**：`api/tests/store/qa-store.test.ts`
**覆蓋**：load、hybridSearch（含 engine null fallback）、keywordSearch、listQa、categories、collections、getBySeq

### 6.2 audit-logger 測試

**新增檔案**：`api/tests/utils/audit-logger.test.ts`

### 6.3 Supabase store 測試補齊

**修改**：`supabase-session-store.test.ts`、`supabase-synonyms-store.test.ts`、`supabase-learning-store.test.ts` — 補齊 edge cases。

### 6.4 修復測試描述不一致

**檔案**：`api/tests/store/supabase-qa-store.test.ts:196` — 測試名稱改為 "rethrows RPC error"。

### 6.5 pipeline.test.ts 加 afterAll cleanup

**檔案**：`api/tests/routes/pipeline.test.ts` — 加入 `afterAll` 清理 `tmpDir`。

---

## 執行順序與依賴

```
Phase 1 (Security) ──→ Phase 2 (Database) ──→ Phase 3 (Tech Debt)
                                                      │
                                               Phase 4 (Refactor)
                                                      │
                                               Phase 5 (Python)
                                                      │
                                               Phase 6 (Tests)
```

Phase 1 和 2 可部分並行（1.3–1.6 程式碼修改與 2.1 SQL 確認同時進行）。
Phase 4 和 5 互不依賴可並行。
Phase 6 依賴 Phase 4（重構後才能寫正確的測試）。

---

## 驗證清單

- [x] Phase 1: `pnpm test` 通過 + SSRF/auth/headers/UUID 驗證（Lambda CORS 待手動設定）
- [x] Phase 2: migrations 004-007 apply + IVFFlat probes=5
- [x] Phase 3: `app/` 目錄已刪 + `deploy-seo-api.yaml` 已刪 + CI 已用 NOTION_TOKEN
- [x] Phase 4: `pnpm test` 通過 + `pipeline.ts` 436 行 + `pipeline-fs.ts` 439 行
- [x] Phase 5: 65 處 print→logging 替換
- [x] Phase 6: 38 test files / 353 tests / coverage 80%+
