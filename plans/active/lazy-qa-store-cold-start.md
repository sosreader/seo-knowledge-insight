# Lazy QA Store — 修好 always-cold Lambda 的 cold start 阻塞

## 背景與根因（live 證據）

2026-08-19 17:35 (UTC 09:35)，`https://staging.vocus.cc/admin/seoInsight/report` 顯示
「API 連線失敗，請確認 Docker 容器是否運行中」。追查結果**與 Docker 無關**，後端是 Lambda `seo-insight-api`。

證據鏈：

| 層 | 證據 |
|---|---|
| Envoy access log (vocus-stg) | `status:504, response_flags:"UT", duration_ms:15005` — envoy 15s route timeout，upstream 未回應 |
| Lambda CloudWatch | `QAStore load failed: Supabase SELECT qa_items failed (500): {"code":"57014","message":"canceling statement due to statement timeout"}` |
| Lambda CloudWatch | `Unhandled error: TimeoutError ... at SupabaseReportStore.list`，`duration_ms:10003` ＝ `SUPABASE_TIMEOUT_MS` |
| Lambda REPORT | `Duration: 54273 / 48794 / 46739 ms`，皆帶 `Init Duration` |
| Pod 內直打 | 暖容器下 `/api/v1/reports` → 200，快 |
| Supabase 實測 | `qa_items` 25,881 筆；現行 select（含 `answer`）PAGE_SIZE 500 → 52 頁、41MB、73–140s |
| Supabase 實測 | live schema **沒有** `primary_category` 等欄位 → `EXTENDED_SELECT_COLUMNS` 每次 cold start 白吃一個 400 (`42703`) |

機制：`src/lambda.ts` 的 handler 做 `await ready`，而 `ready = initStores()` 會 `await loadQaStore()`
（25,881 筆全量分頁撈進記憶體）。於是**所有** route——包含完全用不到 QA 的 `/reports`、`/meeting-prep`、
`/pipeline/metrics/snapshots`、`/sessions`——都被擋在 QA store 載入後面。並發 cold start 又把 Supabase 打到
statement timeout，連 route 自己的查詢也超過 10s → 500/503。

## 關鍵約束（使用者 2026-08-19 確認）

**此 API 每週只用 1-4 次 → 每次開頁面都必然是 cold start。**

推論：
- 「背景預載」無效——永遠來不及暖。
- provisioned concurrency 不划算——24/7 計費換每週 4 次使用。
- 唯一正確方向：**cold start 什麼都不載**，並讓真正需要 QA 的路徑載入成本降到可接受。

## Steps

### S1 — cold start 不阻塞（核心，修好回報的 bug）
【1 agent × Opus × ~120k tokens】

- `src/lambda.ts`：移除 handler 的全域 `await ready`。
- `src/index.ts`：`initStores()` 拆為
  - `initCore()` — 只做 `initLaminar()`（便宜，維持 await）
  - `ensureQaStoreLoaded()` — memoized lazy，失敗時允許重試（沿用現行 `_initPromise` reset 語意）
  - `ensureSynonymsLoaded()` — 同上
- 新增 Hono middleware，只掛在真正需要 QA 的掛載點：`/qa/*`、`/qa`、`/search`、`/chat`、`/chat/*`。
- 不需要 QA 的 route 完全不觸發載入：
  - `src/routes/reports.ts:235` 的 `qaStore.count` → 未載入時回 `0`，不觸發載入
  - `src/routes/pipeline.ts:144` 的 `qaStore.allItems` fallback → 未載入時視為空，不觸發載入
- 本機 server 路徑（`src/index.ts` 非 Lambda 分支）行為不變或同樣改 lazy，但不得回歸。

驗收：`/api/v1/reports`、`/meeting-prep`、`/pipeline/metrics/snapshots`、`/sessions` 在 cold start 下
**不得**出現任何 `qa_items` 查詢，且 P95 < 3s。

### S2 — QA-dependent route 的 cold start 成本瘦身
【1 agent × Sonnet × ~80k tokens】

- `SupabaseQAStore.load()`：startup select 拿掉 `answer`（最肥欄位），`PAGE_SIZE` 500 → 2000。
  實測 41MB/73s → 6MB/11s。
- `answer` 改為命中後才需要：`hybridSearch` 走的 `match_qa_items` RPC 本來就回 `answer`；
  `keywordSearch` / `getById` / `getBySeq` 命中後再補撈（或於回傳前 hydrate）。
- 移除 `EXTENDED_SELECT_COLUMNS` 與 `isMissingColumnError` fallback（live schema 沒有這些欄位，
  是 dead path，每次 cold start 白吃一個 400）。若日後補 migration 再加回。

驗收：`/api/v1/search` 冷啟後首查 < 15s；`answer` 內容在搜尋結果與 `getById` 皆完整。

### S3 — 前端錯誤訊息與重試
【1 agent × Sonnet × ~60k tokens】repo: vocus-web-ui, base: hotfix

- `pages/admin/seoInsight/report.tsx:172`、`pages/admin/seoInsight/rawData.tsx:49`、
  `components/admin/seoInsight/useQAFilters.ts:159`：移除「請確認 Docker 容器是否運行中」，
  改為帶 HTTP status 的實際訊息（`SeoApiError.statusCode` 已有）。
- `catch {}` 改為 `catch (err)`，保留 status 供訊息與判斷使用。
- 加重試按鈕；5xx 自動重試一次（backoff），因為 always-cold 首次請求本來就較慢。

### S4 — 驗收與 PR
【1 fresh-context agent × Sonnet × ~50k tokens】

- 後端：merge 到 main 觸發 `deploy-ts-api.yml` 自動部署 Lambda。
- 部署後對 Lambda function URL 做 cold-start 實測（先 `update-function-configuration` 強制換容器）。
- 前端：PR base = `hotfix`，加 preview label 驗收。
- 證據存 `.verification/2026-08-19/`。

## Dependencies

S1 → S2 → S4
S3 → S4

## 不在此次範圍

- Lambda 環境變數以明文存放 OpenAI / Supabase service key（應搬到 Secrets Manager）— 另案。
- `qa_items` 補上 `primary_category` 等 extended retrieval 欄位的 migration — 另案。
