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

`plans/active/cache-redis.md`

**問題**：每次 RAG chat 都呼叫 OpenAI embedding + Supabase RPC，重複查詢浪費 token 費用和延遲。

**分兩階段**：
- **Phase 1（Disk Cache）**：用本地檔案快取 embedding 結果和搜尋結果，適合目前單 Lambda 實例的規模。Python 端已有 `openai_helper.py` cache 機制，TS 端尚未實作。
- **Phase 2（Redis）**：當流量成長到需要多實例時，改用 Redis 做分散式快取。目前流量極低，不急。

**預估效益**：重複查詢省 ~80% token 費用，回應延遲降低 200-500ms。

**前提**：流量成長後才有明顯效益。

### P4-2：Multi-Domain Analysis

`plans/active/multi-domain-analysis.md`

**問題**：目前系統硬編碼為「SEO 知識庫」，prompt、分類、評估維度都綁死 SEO 領域。

**方案**：引入 **Domain Profile YAML**，把領域知識抽象化：
```yaml
domain: seo
display_name: "SEO 知識庫"
categories: [技術SEO, 內容策略, ...]
system_prompt: "你是一位資深 SEO 顧問..."
eval_dimensions: [relevance, accuracy, ...]
```

換一份 YAML 就能支援不同知識領域（例如產品管理、行銷策略）。本質是「去耦合」，讓系統變成通用 RAG 平台。

**前提**：需要有第二個領域的需求才值得做。

### P4-3：Learning Query（Phase 2）

`plans/active/phase2-learning-query.md`

**問題**：目前 feedback/miss 只記錄不分析，無法自動改善搜尋品質。

**三個子功能**：
- **Usage Aggregator**：聚合 `learning_log.jsonl` 中的 feedback 和 miss，產出統計報告（熱門查詢、低分查詢、常見 miss pattern）
- **Query Understanding**：分析使用者查詢意圖，自動建議新同義詞或知識庫缺口
- **Access Analysis**：從存取日誌分析使用模式，找出高頻但低品質的回答

**前提**：需要累積 2+ 週的實際使用紀錄才有分析價值。目前 staging 剛上線，資料量不足。

### P4 急迫性評估

| 計畫 | 急迫性 | 前提條件 |
|------|--------|----------|
| Cache | 低 | 流量成長後才有效益 |
| Multi-Domain | 低 | 需要第二個領域需求 |
| Learning Query | 中 | 需 2+ 週使用紀錄 |

三個都不急，建議先讓 staging 穩定運行、累積使用資料，再依實際需求決定優先做哪個。

---

## 優先級總覽

| 優先級 | 項目 | 預估 effort |
|--------|------|-------------|
| ~~**P0**~~ | ~~commit 本次修復 + Supabase migration 記錄~~ | ✅ 完成 |
| ~~**P1-1**~~ | ~~source-docs preview → 原文連結~~ | ✅ size_bytes=0 時顯示「原文」 |
| ~~**P1-2**~~ | ~~meetings tab 空狀態~~ | ✅ MeetingTable 未被使用，非問題 |
| ~~**P1-3**~~ | ~~同義詞確認~~ | ✅ 靜態同義詞正常，custom=0 預期行為 |
| ~~**P2-1**~~ | ~~同義詞擴充（+10 組）~~ | ✅ Category Hit 100%, Precision@5 89% |
| ~~**P2-2**~~ | ~~Model A/B：gpt-5.2 (4.43) > gpt-4.1 (4.30)~~ | ✅ 維持 gpt-5.2 + prompt 精簡化 |
| ~~**P3-1**~~ | ~~API Key 前端安全~~ | ✅ proxy 架構已正確，無暴露 |
| ~~**P3-2**~~ | ~~Supabase RLS 強化~~ | ✅ 完成 |
| ~~**P3-3**~~ | ~~Observability 修復~~ | ✅ graceful skip（低優先） |
| **P4** | 功能擴展（cache/multi-domain/learning） | 各 3+ sessions |
