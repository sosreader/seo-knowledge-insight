# Lambda Staging 穩定化 + 後續計畫

> 建立時間：2026-03-06
> 完成時間：2026-03-06
> 狀態：completed（P2-2 Model A/B deferred，P4 由獨立 plan 追蹤）

---

## 背景

v2.24–v2.25 完成 Lambda + Supabase 遷移後，staging 環境（`staging-v2.vocus.cc/admin/seoInsight/*`）的核心功能已可運作。本計畫整理當前狀態、未 commit 的修復、以及後續優先級。

> **前端備註**：`vocus-web-ui` 的變更一律以 worktree 形式操作（原 `vocus-admin-dev` worktree 已合併回 `vocus-web-ui` 主 repo），不直接在 `seo-knowledge-insight` repo 中修改前端程式碼。

---

## Phase 0：收尾本次修復（立即）

### 待 commit 的變更

| 檔案 | 變更 | 狀態 |
|------|------|------|
| `api/src/store/supabase-client.ts` | `supabaseSelect()` 新增 `timeoutMs` 參數 | 已部署 |
| `api/src/store/supabase-qa-store.ts` | `LOAD_TIMEOUT_MS=25s` + `allItems` getter | 已部署 |
| `api/src/store/qa-store.ts` | `allItems` getter | 已部署 |
| `api/src/routes/pipeline.ts` | `buildSourceDocsFromStore()` + fallback | 已部署 |
| `research/07-deployment.md` | cold start timeout + RPC gotchas + 端點完整性表格 | 文件 |
| Supabase `match_qa_items` RPC | VOLATILE + extensions + ::real cast | DB side |

### Supabase migration 記錄

RPC 函數修復需記錄為 migration：
```sql
-- 20260306_fix_match_qa_items.sql
-- STABLE→VOLATILE（SET LOCAL 需要）
-- search_path 加 extensions（pgvector schema）
-- similarity cast ::real（double precision→real）
```

---

## Phase 1：前端體驗優化（短期，1-2 sessions）

### P1-1：source-docs preview 在 Lambda 上不可用

`GET /source-docs/:collection/:file/preview` 需要讀取本地 markdown 檔案。
Lambda 上回傳 404。前端應：
- 偵測 `size_bytes === 0` 時隱藏「預覽」按鈕
- 或改為連結至 `source_url`（已有資料）

### P1-2：meetings 頁面空狀態

前端 rawData 頁面顯示「會議」tab 但回傳 0 筆。選項：
- 隱藏 meetings tab（Lambda 模式下）
- 或從 source-docs 中 filter `source_type=meeting` 顯示（資料已有）

### P1-3：同義詞 Supabase 初始資料

`GET /synonyms` 回傳 0 custom entries。靜態同義詞已內建但自訂同義詞未遷移。
- 確認靜態同義詞在 Lambda 上是否正常載入
- 若需遷移自訂同義詞，建 Supabase `synonyms` table

---

## Phase 2：搜尋品質提升（中期，2-3 sessions）

### P2-1：同義詞擴充

目標：KW Hit Rate 74% → 78%+（中間目標），最終 ≥ 85%

- 分析搜尋 miss 案例，找出缺失的同義詞
- 擴充 `synonym_custom.json`（或 Supabase synonyms table）
- 執行 `/evaluate-context-precision-local` 驗證改善

### P2-2：Model 升級 A/B 測試

- 執行 `/evaluate-model-ab` 比較 gpt-5.2 vs 新模型
- 評估 RAG 回答品質、Faithfulness、Context Precision
- 決定是否升級 `CHAT_MODEL` / `OPENAI_MODEL`

---

## Phase 3：安全與架構（中長期）

### P3-1：API Key 前端安全 — ✅ 已確認安全

前端架構已正確實作 server-side proxy：
- `seoFetch()` 只呼叫 `/api/seo-insight/*`（Next.js API route）
- `[...path].ts` proxy 在 server-side 注入 `X-API-Key`
- 前端 bundle 不含 `SEO_INSIGHT_API_KEY` 或 Lambda URL
- grep 確認 components/pages 無直接 API key 引用

### P3-2：Supabase RLS 強化

目前 `SUPABASE_ANON_KEY` 用於讀取，`SUPABASE_SERVICE_KEY` 用於寫入。
確認 RLS policies 足夠嚴格：
- `qa_items`: SELECT only（anon key）
- `reports`, `sessions`, `metrics_snapshots`: SELECT + INSERT（service key only for write）

### ~~P3-3：Observability 修復~~ ✅

~~Lambda 上 Laminar 初始化失敗（缺 `@opentelemetry/resources` module）~~
**修復方案**：Lambda 環境直接跳過 Laminar（`AWS_LAMBDA_FUNCTION_NAME` 偵測），tsup 排除 `@lmnr-ai/lmnr` + `@opentelemetry/*`。
- `observability.ts`：Lambda 環境 early return
- `tsup.config.ts`：`external: ["@lmnr-ai/lmnr", /^@opentelemetry\//]`
- 本地開發仍正常使用 Laminar

---

## Phase 4：功能擴展（長期）

### P4-1：Cache Redis

`plans/active/cache-redis.md` — 搜尋結果快取，減少 Supabase RPC 呼叫

### P4-2：Multi-Domain Analysis

`plans/active/multi-domain-analysis.md` — 支援多網站 SEO 分析

### P4-3：Learning Query（Phase 2）

`plans/active/phase2-learning-query.md` — 從使用者互動學習搜尋模式

---

## 優先級總覽

| 優先級 | 項目 | 預估 effort |
|--------|------|-------------|
| ~~**P0**~~ | ~~commit 本次修復 + Supabase migration 記錄~~ | ✅ 完成 |
| ~~**P1-1**~~ | ~~source-docs preview → 原文連結~~ | ✅ size_bytes=0 時顯示「原文」 |
| ~~**P1-2**~~ | ~~meetings tab 空狀態~~ | ✅ MeetingTable 未被使用，非問題 |
| ~~**P1-3**~~ | ~~同義詞確認~~ | ✅ 靜態同義詞正常，custom=0 預期行為 |
| ~~**P2-1**~~ | ~~同義詞擴充（+10 組）~~ | ✅ Category Hit 100%, Precision@5 89% |
| **P2-2** | Model 升級 A/B 測試 | ⏭️ deferred |
| ~~**P3-1**~~ | ~~API Key 前端安全~~ | ✅ proxy 架構已正確，無暴露 |
| ~~**P3-2**~~ | ~~Supabase RLS 強化~~ | ✅ 完成 |
| ~~**P3-3**~~ | ~~Observability 修復~~ | ✅ graceful skip（低優先） |
| **P4** | 功能擴展（cache/multi-domain/learning） | 各 3+ sessions |
