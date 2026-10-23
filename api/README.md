# Hono TypeScript API (v3.6)

REST API 伺服器，主要架構採用 Hono 框架，支援雙模式執行（Node.js server / AWS Lambda）。

**特點：**

- 10 個路由器（Routers）、38 個 paths / 42+ 個 operations、838 個測試（67 檔案，coverage 80%+）
- OpenAPI 3.1 規格 + Scalar 互動式文件（`/openapi.json`、`/docs`）
- Rate limiting + API Key 認證（timingSafeEqual）
- Zod schema validation（環境變數 + 請求參數）
- Local Mode graceful degradation（無 OpenAI 時自動降級）
- vocus-warehouse（PostgreSQL＋pgvector）hybrid search，以 `warehouse_rag` 直連（設 `VW_DB_SECRET_FILE_RAG` 啟用，否則 fallback 檔案模式）
- Lambda + Function URL 部署（arm64，~$0/月，production 採 buffered mode）
- 純 TypeScript 架構——metrics-parser + report-llm 已消除 Lambda Python 依賴
- 安全加固：SSRF whitelist (pipeline schema)、auth fail-fast (production 503)、HTTP security headers middleware、session UUID validation
- CRAG 3-tier quality gate（correct / ambiguous / incorrect 三級檢索品質閘門）
- SSE streaming（`POST /chat/stream`，5 event types）
- Inline citation（[1][2] 來源標注 + `validateCitations()` 後處理）
- Exact match response cache（sha256 hash lookup）
- Categorical feedback（6 categories: wrong_answer / missing_info / wrong_source / outdated / too_basic / too_advanced）
- Timeseries anomaly detection（MA deviation / consecutive decline / linear trend）
- AI visibility 報告維度（7 維度含 AI 可見度；有 crawled-not-indexed 資料時升至 8 維度）

---

## 快速開始

### 開發環境

```bash
cd api
pnpm install                 # 首次安裝依賴
pnpm dev                     # 啟動開發伺服器（tsx watch，port 8002）
```

### 測試

```bash
pnpm test                    # 執行所有 vitest 測試
pnpm test:watch             # 監視模式
pnpm test:coverage          # 生成覆蓋率報告
```

### 部署

```bash
# Lambda 部署（生產環境）
pnpm build                   # 編譯至 dist/（server）+ dist-lambda/（Lambda bundle）
cd dist-lambda
echo '{"type":"module"}' > package.json
zip -j ../lambda.zip lambda.js package.json
aws lambda update-function-code --function-name seo-insight-api \
  --zip-file fileb://../lambda.zip --region ap-northeast-1

# 本地 server 模式
pnpm build
pnpm start                   # node dist/index.js，port 8002
```

---

## 架構概覽

```
Client → Function URL / localhost:8002
  → CORS → Security Headers → Request Logger（JSON log + X-Request-Id）
  → /health（直接回應，無 auth，不產生 log）
  → /api/v1/*、/internal/rag/* → Auth → Rate Limit → Route Handler → Service → Store → vocus-warehouse (pg) / File
```

`/internal/rag/*` 與 `/api/v1/*` 是同一組路由；EKS 上 Cloudflare tunnel ingress `^/internal/rag/` 原樣轉送路徑到 rag-api。

**分層設計：**

| 層         | 目錄          | 職責                                                               |
| ---------- | ------------- | ------------------------------------------------------------------ |
| Middleware | `middleware/` | CORS、安全標頭、Request Logger、API Key 認證、Rate Limit、錯誤處理 |
| Routes     | `routes/`     | 請求驗證（Zod schema）、回應格式化                                 |
| Services   | `services/`   | 業務邏輯（RAG、embedding、週報生成、指標解析）                     |
| Store      | `store/`      | 資料存取（Factory Pattern：vocus-warehouse PG vs 檔案模式）        |
| Schemas    | `schemas/`    | Zod 驗證 schema（請求參數、API 回應）                              |
| Utils      | `utils/`      | 純函式工具（cosine、CJK 分詞、keyword boost、sanitize）            |

**雙模式資料層：** `hasPg()` 偵測 `VW_DB_SECRET_FILE_RAG`，有設定走 `PgQAStore` 等 vocus-warehouse store（`pg` 連線池，角色 `warehouse_rag`），否則 fallback 到檔案模式（JSON + `.npy` embedding）。

**雙模式執行：** 同一份 `app` 物件由 `index.ts`（Node.js server）和 `lambda.ts`（AWS Lambda handler）共用，`initStores()` 為 idempotent singleton promise。

---

## API 文件

啟動開發伺服器後即可存取：

| 格式              | URL                                                | 說明                                                         |
| ----------------- | -------------------------------------------------- | ------------------------------------------------------------ |
| OpenAPI JSON      | `http://localhost:8002/openapi.json`               | 機器可讀規格（可匯入 Postman / Swagger Editor）              |
| 互動式文件        | `http://localhost:8002/docs`                       | Scalar UI（可直接在瀏覽器測試 API）                          |
| GitHub Pages 文件 | [`sosreader.github.io/seo-knowledge-insight`](https://sosreader.github.io/seo-knowledge-insight/) | Scalar 託管文件站（CI auto-deploy from `api/src/openapi.ts`） |

> `/openapi.json` 和 `/docs` 不需要認證，也不受 rate limit 限制。

---

## API 路由清單

### 1. 健康檢查 (health)

| 方法 | 路由      | 說明           | 認證 | Rate Limit |
| ---- | --------- | -------------- | ---- | ---------- |
| GET  | `/health` | 伺服器健康檢查 | ✗    | —          |

回傳 `version`（動態引用 `API_VERSION`，與 OpenAPI spec 同步）及 `capabilities` 物件（5 維度：`runtime`/`llm`/`store`/`agent`/`caller`）。`llm` 為有效 LLM（`"openai"` = server 內建、`"claude-code"` = Claude Code 作為 LLM 引擎、`"none"` = 無 LLM）。`caller` 由 User-Agent 推斷。注意：route 內部決策邏輯仍使用 `resolveServerCapabilities()`（server 自身能力），`resolveHealthCapabilities()` 僅供 /health 顯示。

### 2. Q&A 知識庫 (qa) — 4 個 endpoints

| 方法 | 路由                     | 說明                                                                            | 認證 | Rate Limit |
| ---- | ------------------------ | ------------------------------------------------------------------------------- | ---- | ---------- |
| GET  | `/api/v1/qa`             | 列出所有 Q&A（支援分頁、source_type/source_collection/extraction_model filter） | ✓    | 60/min     |
| GET  | `/api/v1/qa/{id}`        | 取得單筆 Q&A 詳情（id: 16-char hex 或 integer seq）                             | ✓    | 60/min     |
| GET  | `/api/v1/qa/categories`  | 列出所有分類標籤                                                                | ✓    | 60/min     |
| GET  | `/api/v1/qa/collections` | 列出所有 collection（含 source_type + count）                                   | ✓    | 60/min     |

**`GET /api/v1/qa` 查詢參數（2026-03-15）**

| 參數                 | 型別                        | 說明                                                           |
| -------------------- | --------------------------- | -------------------------------------------------------------- |
| `category`           | string                      | 舊版單一分類 filter                                            |
| `primary_category`   | string                      | 以 retrieval metadata 的主分類過濾；支援逗號分隔多值           |
| `keyword`            | string                      | question / answer / keywords 關鍵字搜尋                        |
| `difficulty`         | `基礎`\|`進階`              | 難度過濾                                                       |
| `evergreen`          | boolean                     | 是否常青                                                       |
| `source_type`        | string                      | `meeting` / `article`                                          |
| `source_collection`  | string                      | collection 名稱                                                |
| `extraction_model`   | string                      | 依 extraction model 過濾                                       |
| `maturity_relevance` | `L1`\|`L2`\|`L3`\|`L4`      | 成熟度過濾                                                     |
| `intent_label`       | string                      | retrieval intent 過濾；支援逗號分隔多值                        |
| `scenario_tag`       | string                      | retrieval scenario 過濾；支援逗號分隔多值                      |
| `serving_tier`       | string                      | `canonical` / `supporting` / `booster` 之類 serving layer 過濾 |
| `evidence_scope`     | string                      | 依證據範圍過濾，例如 `platform` / `site`                       |
| `sort_by`            | `source_date`\|`confidence` | 排序欄位                                                       |
| `sort_order`         | `asc`\|`desc`               | 排序方向                                                       |
| `limit` / `offset`   | number                      | 分頁                                                           |

**`GET /api/v1/qa` 新增回應欄位**

- `primary_category`
- `categories`
- `intent_labels`
- `scenario_tags`
- `serving_tier`
- `evidence_scope`

**相容性說明**

- 若資料仍停在舊 schema，`primary_category` 會回退到舊 `category`
- `categories` 若缺值，runtime 會回退成 `[category]`

### 3. 語意搜尋 (search) — 1 個 endpoint

| 方法 | 路由             | 說明                                                | 認證 | Rate Limit |
| ---- | ---------------- | --------------------------------------------------- | ---- | ---------- |
| POST | `/api/v1/search` | 混合搜尋（有 OpenAI: hybrid，無: keyword fallback） | ✓    | 60/min     |

**Graceful Degradation:**

- 有 OpenAI API Key：使用 embedding + cosine similarity（語意搜尋）
- 無 OpenAI API Key：自動降級至 keyword-only 搜尋

**Search Runtime（2026-03-15）:**

- `hybridSearch()` 與 `keywordSearch()` 都會讀取 retrieval metadata：`primary_category`、`categories`、`intent_labels`、`scenario_tags`、`serving_tier`
- ranking 公式除 semantic + keyword + synonym 外，額外納入 metadata feature score、`exactTermBoost`、serving tier prior、duplicate suppression、category / intent / novel-term diversity rerank
- 若 request 帶 `extraction_model` 或其他 metadata filters，route layer 會先以 `top_k × 3` over-retrieve，再做 post-filter，避免過早裁切導致結果數不足
- API response 會帶回 `primary_category`、`categories`、`all_categories`、`intent_labels`、`scenario_tags`、`serving_tier`、`evidence_scope`

`extraction_model` filter 的 `×3` multiplier 是經驗值：目的是在 mixed-model corpus 中避免 filter 後剩不到 `top_k` 筆，同時把額外查詢成本控制在固定常數倍，而不是無上限放大。

**`POST /api/v1/search` request body（2026-03-15）**

| 欄位               | 型別                   | 說明                                 |
| ------------------ | ---------------------- | ------------------------------------ |
| `query`            | string                 | 必填，1–500 字                       |
| `top_k`            | number                 | 1–20，預設 5                         |
| `category`         | string                 | 舊版 category filter                 |
| `primary_category` | string                 | 以 retrieval 主分類做 post-filter    |
| `extraction_model` | string                 | 以 extraction model 做 post-filter   |
| `maturity_level`   | `L1`\|`L2`\|`L3`\|`L4` | 對應 `applyMaturityBoost()`          |
| `intent_label`     | string                 | 以 retrieval intent 做 post-filter   |
| `scenario_tag`     | string                 | 以 retrieval scenario 做 post-filter |
| `serving_tier`     | string                 | 以 serving layer 做 post-filter      |
| `evidence_scope`   | string                 | 以證據範圍做 post-filter             |

**`POST /api/v1/search` 回應補充**

- `categories`：query-aware 投影後的主要類別；第一筆結果優先保留 `primary_category`
- `all_categories`：item 的完整多標籤類別集合
- `intent_labels` / `scenario_tags` / `serving_tier` / `evidence_scope`：供前端或評估工具直接使用

### 4. RAG 問答 (chat) — 2 個 endpoints

| 方法 | 路由                  | 說明                                                                   | 認證 | Rate Limit |
| ---- | --------------------- | ---------------------------------------------------------------------- | ---- | ---------- |
| POST | `/api/v1/chat`        | 互動式問答（有 OpenAI: RAG + GPT，無: context-only）                   | ✓    | 20/min     |
| POST | `/api/v1/chat/stream` | SSE streaming 問答（5 event types: sources/token/metadata/done/error） | ✓    | 20/min     |

**三模式 Graceful Degradation:**

- **Agent mode**（`AGENT_ENABLED=true` 或 `auto` + 有 OpenAI key）：LLM 自主決定 tool calling（search / get_qa_detail / list_categories / get_stats），多輪收集資訊後回答
- **RAG mode**（有 OpenAI key，agent 未啟用；或 request `mode: "rag"`）：單次檢索相關 Q&A + GPT 生成回答
- **Context-only mode**（無 OpenAI key）：僅回傳相關 Q&A 內容

> `POST /api/v1/chat/stream` 在本地 Node.js 開發模式可用；目前 Lambda production 使用 buffered handler，若呼叫此端點會回 `501`，請改用 `POST /api/v1/chat`。

**CRAG Quality Gate（v3.0）：** 檢索結果經 3-tier 品質閘門評估：

- **correct**（score >= 0.6）：正常 RAG flow + inline citation [1][2]
- **ambiguous**（0.4–0.6）：加入謹慎指示 + 免責聲明
- **incorrect**（< 0.4）：直接回傳 context-only，不呼叫 GPT

**Response Metadata（v3.0）：** 每次回應附帶 `metadata` 欄位，記錄 model、provider、mode、embedding_model、input/output/total/reasoning tokens、duration_ms、retrieval_count、reranker_used、`retrieval_quality`（correct/ambiguous/incorrect）、`citation_count`、`cache_hit`。Agent mode 額外記錄 `tool_calls_count`、`agent_turns`。Session assistant message 同步記錄。

### 5. SEO 週報 (reports) — 3 個 endpoints

> rag-api（vocus-warehouse 模式）不提供週報：以下路由一律回 **410** `not_available_in_rag_api`，前端改經 warehouse-api `/internal/app/reports` 讀取。只有本機檔案模式可用。

| 方法 | 路由                       | 說明                                                 | 認證 | Rate Limit |
| ---- | -------------------------- | ---------------------------------------------------- | ---- | ---------- |
| GET  | `/api/v1/reports`          | 列出所有週報                                         | ✓    | 60/min     |
| GET  | `/api/v1/reports/{date}`   | 取得單篇週報（date: YYYYMMDD）                       | ✓    | 60/min     |
| POST | `/api/v1/reports/generate` | 觸發週報生成（同步，120s timeout；`cache_hit` 欄位） | ✓    | 5/min      |

### 6. 對話管理 (sessions) — 5 個 endpoints

| 方法   | 路由                             | 說明                                                              | 認證 | Rate Limit |
| ------ | -------------------------------- | ----------------------------------------------------------------- | ---- | ---------- |
| GET    | `/api/v1/sessions`               | 列出所有對話                                                      | ✓    | 60/min     |
| GET    | `/api/v1/sessions/{id}`          | 取得單個對話詳情                                                  | ✓    | 60/min     |
| POST   | `/api/v1/sessions`               | 建立新對話                                                        | ✓    | 20/min     |
| POST   | `/api/v1/sessions/{id}/messages` | 新增訊息到對話（支援 `mode: "agent"\|"rag"` + context-only 降級） | ✓    | 20/min     |
| DELETE | `/api/v1/sessions/{id}`          | 刪除對話                                                          | ✓    | 60/min     |

### 7. 回饋收集 (feedback) — 1 個 endpoint

| 方法 | 路由               | 說明                                                                           | 認證 | Rate Limit |
| ---- | ------------------ | ------------------------------------------------------------------------------ | ---- | ---------- |
| POST | `/api/v1/feedback` | 提交使用者回饋（支援 6 類別：wrong_answer/missing_info/wrong_source/outdated/too_basic/too_advanced） | ✓    | 60/min     |

### 8. Pipeline 管理 (pipeline) — 18 個 endpoints

rag-api（PG 模式）下 `meetings`、`meetings/{id}/preview`、`unprocessed`、`logs`、四條 POST 觸發與 `source-docs/:collection/:file/preview` 回 501 `run_locally`，見「LLM 關閉時的行為」一節。

| 方法   | 路由                                                     | 說明                                                             | 認證 | Rate Limit |
| ------ | -------------------------------------------------------- | ---------------------------------------------------------------- | ---- | ---------- |
| GET    | `/api/v1/pipeline/status`                                | 各步驟完成狀態                                                   | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/meetings`                              | 會議列表（含 metadata）                                          | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/meetings/{id}/preview`                 | Markdown 預覽                                                    | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/unprocessed`                           | 待處理的 Markdown 列表                                           | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/logs`                                  | Fetch 歷史日誌                                                   | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/fetch`                                 | 觸發 Notion 增量擷取                                             | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/fetch-articles`                        | 觸發外部文章擷取（10 來源：Medium + iThome + Google Cases + Ahrefs + SEJ + Growth Memo + Google Blog + Google Blog zh-TW + Web.dev + Screaming Frog；逐來源回報，允許 partial failure） | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/extract-qa`                            | 觸發 Q&A 萃取                                                    | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/dedupe-classify`                       | 觸發去重 + 分類                                                  | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/crawled-not-indexed`                   | 分析檢索未索引路徑（Google Sheet 或 raw_tsv 解析 + 規則引擎，無 LLM、不寫表） | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/source-docs`                           | 列出所有來源文件（支援 filter + pagination）                     | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/source-docs/:collection/:file/preview` | 來源文件 Markdown 預覽                                           | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/metrics`                               | 取得 Pipeline metrics                                            | ✓    | 60/min     |
| POST   | `/api/v1/pipeline/metrics/save`                          | 儲存指標快照（支援 `maturity` JSONB 欄位）                       | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/metrics/snapshots`                     | 列出指標快照清單                                                 | ✓    | 60/min     |
| DELETE | `/api/v1/pipeline/metrics/snapshots/:id`                 | 刪除指定快照                                                     | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/metrics/trends`                        | Timeseries 異常偵測（MA deviation / decline / trend）            | ✓    | 60/min     |
| GET    | `/api/v1/pipeline/llm-usage`                             | LLM cost/latency monitoring                                      | ✓    | 60/min     |

### 9. 同義詞管理 (synonyms) — 4 個 endpoints（v2.10 新增）

| 方法   | 路由                      | 說明                          | 認證 | Rate Limit |
| ------ | ------------------------- | ----------------------------- | ---- | ---------- |
| GET    | `/api/v1/synonyms`        | 列出所有同義詞（靜態 + 自訂） | ✓    | 60/min     |
| POST   | `/api/v1/synonyms`        | 新增自訂同義詞                | ✓    | 60/min     |
| PUT    | `/api/v1/synonyms/{term}` | 更新自訂同義詞                | ✓    | 60/min     |
| DELETE | `/api/v1/synonyms/{term}` | 刪除自訂同義詞                | ✓    | 60/min     |

### 10. 顧問會議準備 (meeting-prep) — 3 個 endpoints

> rag-api（vocus-warehouse 模式）一律回 **410** `not_available_in_rag_api`，改經 warehouse-api `/internal/app/meeting-prep` 讀取。只有本機檔案模式可用。

| Method | Path                                  | Description                                             |
| ------ | ------------------------------------- | ------------------------------------------------------- |
| GET    | `/api/v1/meeting-prep`                | 列出所有會議準備報告（日期 + meta）                     |
| GET    | `/api/v1/meeting-prep/maturity-trend` | SEO 成熟度趨勢時間序列（data_points + summary）         |
| GET    | `/api/v1/meeting-prep/:date`          | 取得單篇會議準備報告（YYYYMMDD 或 YYYYMMDD_hash8 格式） |

---

## Reports API — 回應格式

### POST /api/v1/reports/generate

**Response body**：

```json
{
  "success": true,
  "data": {
    "date": "20260306",
    "report": "...",
    "cache_hit": true
  }
}
```

**Request body（optional fields）**：

- `snapshot_id: string` — 指標快照 ID（YYYYMMDD-HHMMSS 格式）
- `use_openai: boolean` — 使用 OpenAI 模式生成
- `maturity_context: Record<string, string>` — 成熟度維度等級（如 `{strategy: "L2", process: "L2"}`）。優先序：`snapshot.maturity > maturity_context > null`
- `situation_analysis`, `traffic_analysis`, `technical_analysis`, `intent_analysis`, `action_analysis`: LLM 分析注入（各 max 2000 字元）

**欄位說明**：

- `cache_hit: boolean` — 是否命中快取。若 `true` 表示該報告已存在（相同 metrics hash），直接回傳既有內容；若 `false` 表示新生成報告
- `date: string` — 報告日期（YYYYMMDD 格式）
- `report: string` — 週報 Markdown 內容

**快取機制**：

- Hash 計算移除 frontmatter 和 meta comment，避免 `generated_at` 時間戳導致 cache miss
- 質量評估（quality eval）改用 async，並包裝在 Laminar trace 內以便追蹤

---

## 認證與授權

驗證模式由 env `AUTH_MODE` 決定（`src/middleware/auth-mode.ts`）：

| 模式 | 何時 | 驗證 |
| --- | --- | --- |
| `cf-access` | 容器（EKS rag-api）的預設；無法辨識的值也落到這裡 | Cloudflare Access JWT |
| `api-key` | Lambda 的預設（Lambda 即將退役）；本機 docker-compose 明設 | `X-API-Key` |

### Cloudflare Access JWT（容器模式）

`src/middleware/cf-access.ts`，語意對齊 vocus-warehouse `auth/access_jwt.py`：

- 驗 header `Cf-Access-Jwt-Assertion`，只收 RS256，kid 必填
- 簽章 key 取自 `https://<CF_ACCESS_TEAM_DOMAIN>/cdn-cgi/access/certs`，快取 1 小時，未知 kid 重抓一次（重抓間隔至少 30 秒）
- `iss` 必須是 `https://<CF_ACCESS_TEAM_DOMAIN>`，`aud` 至少一個在 `RAG_AUDS`（逗號分隔），`exp`／`nbf` 容忍 60 秒
- 身分：JWT `sub`；service token 的 `sub` 為空，改用 `common_name`。身分寫進 context（`accessIdentity`），限流以此為 key

| 情況 | 狀態碼 | `error` |
| --- | --- | --- |
| `RAG_AUDS` 或 `CF_ACCESS_TEAM_DOMAIN` 缺值（S2.4 回填前） | 503 | `unavailable` |
| JWKS 從未取得（egress 擋住等） | 503 | `unavailable` |
| 沒帶 token、簽章／alg／kid／iss／aud／exp／nbf 任一不符、沒有身分 | 401 | `unauthorized` |

`/health`、`/openapi.json`、`/docs` 不經過驗證；tunnel 只轉送 `/internal/rag/*`，這三條不對外。
env 不熱更新：`RAG_AUDS` 變更後需 rollout restart。

### API Key（Lambda 與本機）

在 header 帶 `X-API-Key`：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8002/api/v1/qa
```

**環境變數設定：** `.env` 中設定 `SEO_API_KEY`

### Rate Limiting

根據端點不同，設定不同的限制：

- **搜尋/Q&A 端點**：60 requests / min（`RATE_LIMIT_DEFAULT`）
- **Chat 類端點**（`/chat`、`/chat/*`、`/sessions/:id/messages`）：每身分共用 10 requests / min（`RATE_LIMIT_CHAT`）＋ 200 requests / day（`RATE_LIMIT_CHAT_DAILY`）
- **Report 生成**：5 requests / min

key 是 CF Access 身分（沒有身分時退回 client IP）；計數在 process 記憶體內，不跨副本共享。超過限制時回 429＋`Retry-After`。

> **Lambda 環境**：in-memory rate limiting 無效（每個執行環境有獨立 Map），自動 bypass。需要限流時應使用 API Gateway throttling。

---

## 項目結構

```
api/
├── src/
│   ├── index.ts              # 入口點（middleware + route mount + OpenAPI/Scalar + initStores()）
│   ├── openapi.ts            # OpenAPI 3.1 spec（32 paths, 36 endpoints）
│   ├── lambda.ts             # Lambda 入口（cold start + hono/aws-lambda handler）
│   ├── config.ts             # Zod 驗證環境變數 + paths
│   ├── routes/               # 10 個路由
│   │   ├── health.ts
│   │   ├── qa.ts
│   │   ├── search.ts
│   │   ├── chat.ts
│   │   ├── reports.ts
│   │   ├── sessions.ts
│   │   ├── feedback.ts
│   │   ├── pipeline.ts
│   │   ├── pipeline-fs.ts      # Pipeline 檔案系統邏輯（source-docs 等）
│   │   ├── synonyms.ts
│   │   └── meeting-prep.ts
│   ├── middleware/
│   │   ├── auth.ts              # API Key 驗證（timingSafeEqual；Lambda／本機）
│   │   ├── auth-mode.ts         # AUTH_MODE 解析（cf-access｜api-key）
│   │   ├── cf-access.ts         # Cloudflare Access JWT 驗證（容器模式）
│   │   ├── jwks-cache.ts        # team JWKS 快取（1 h、未知 kid 重抓）
│   │   ├── access-context.ts    # context 內的 Access 身分
│   │   ├── rate-limit.ts        # Sliding window 速率限制，key 為 Access 身分（Lambda 自動 bypass）
│   │   ├── cors.ts              # CORS 設定
│   │   ├── security-headers.ts  # HTTP security headers（X-Content-Type-Options 等）
│   │   ├── request-logger.ts    # 結構化 JSON request log + X-Request-Id
│   │   └── error-handler.ts     # 錯誤處理
│   ├── store/
│   │   ├── qa-store.ts              # QAStore singleton + loadQaStore() factory
│   │   ├── qa-fns.ts                # QAStore pure module functions（FP 重構）
│   │   ├── query-term-utils.ts      # 查詢詞處理工具
│   │   ├── store-registry.ts        # Store singleton registry（snapshotStore）
│   │   ├── store-errors.ts          # DbUnavailable(503)／DbTimeout(504)／NotAvailableInRagApi(410)
│   │   ├── pg-client.ts             # pg 連線池（db-rag secret 檔、verify-full、statement_timeout 10s）
│   │   ├── pg-qa-store.ts           # PgQAStore（app_qa_item＋match_qa_items）
│   │   ├── qa-rerank.ts             # hybrid 重排純函式（自 Supabase 版原樣抽出）
│   │   ├── pg-session-store.ts      # PgSessionStore（app_session，軟刪除）
│   │   ├── session-content-hash.ts  # app_session.content_hash（與 sync_db.py 相同算法）
│   │   ├── pg-snapshot-store.ts     # PgSnapshotStore（app_metrics_snapshot，軟刪除）
│   │   ├── pg-synonyms-store.ts     # PgSynonymsStore（app_synonym_custom）
│   │   ├── pg-learning-store.ts     # app_learning 寫入
│   │   ├── pg-llm-usage-store.ts    # app_llm_usage 讀寫
│   │   ├── search-engine.ts         # 搜尋引擎（hybrid + keyword）
│   │   ├── qa-filter.ts             # 共用 QA filter 邏輯
│   │   ├── session-store.ts         # 對話歷史儲存（file fallback）
│   │   ├── learning-store.ts        # 失敗記憶（JSONL fallback）
│   │   └── synonyms-store.ts       # 同義詞（雙層：靜態 + custom JSON）
│   ├── agent/                # Agentic RAG（v2.28）
│   │   ├── types.ts            # AgentConfig, ToolResult, AgentResponse, AgentDeps
│   │   ├── tool-definitions.ts # 4 tool Zod schemas + getOpenAITools()
│   │   ├── tool-executor.ts    # Tool dispatch + validation + 15s timeout
│   │   ├── agent-loop.ts       # while-loop + 終止條件 + source 收集 + maturityLevel 注入
│   │   └── agent-deps.ts       # qaStore → AgentDeps 橋接（DI）
│   ├── services/
│   │   ├── embedding.ts      # OpenAI embedding 服務
│   │   ├── rag-chat.ts       # RAG 問答邏輯（CRAG quality gate + inline citation）
│   │   ├── rag-chat-stream.ts  # SSE streaming 問答（callback-based）
│   │   ├── retrieval-gate.ts   # CRAG 3-tier quality gate + citation validation
│   │   ├── reranker.ts       # Claude Haiku reranker
│   │   ├── response-cache.ts   # Exact match response cache（sha256）
│   │   ├── context-relevance.ts  # Context Relevance 評估
│   │   ├── timeseries-analyzer.ts # Timeseries anomaly detection（MA/decline/trend）
│   │   ├── metrics-parser.ts # SEO 指標解析（純 TS，取代 Python）
│   │   ├── crawled-not-indexed-parser.ts # 檢索未索引 TSV 解析
│   │   ├── crawled-not-indexed-analyzer.ts # 檢索未索引分析規則引擎 + LLM prompt
│   │   ├── crawled-not-indexed-evaluator.ts # 檢索未索引品質 5 維度評估器
│   │   ├── report-generator-local.ts  # 8 維度本地週報（含 AI 可見度 + 索引章節）
│   │   ├── report-llm.ts     # LLM 週報生成（純 TS，7 維度含 AI 可見度）
│   │   ├── rag-chat-pure.ts    # RAG 問答 pure functions（FP 重構）
│   │   ├── report-evaluator.ts  # 5 維度品質評估
│   │   └── pipeline-runner.ts # Python 腳本執行器
│   ├── schemas/              # Zod schemas
│   │   ├── api-response.ts   # 統一回應格式
│   │   ├── qa.ts
│   │   ├── search.ts
│   │   ├── chat.ts
│   │   ├── report.ts
│   │   ├── session.ts
│   │   ├── feedback.ts
│   │   ├── pipeline.ts
│   │   ├── synonyms.ts
│   │   └── meeting-prep.ts
│   └── utils/
│       ├── audit-logger.ts      # 安全審計日誌
│       ├── capabilities.ts      # 5 維度能力偵測（runtime/llm/store/agent/caller）
│       ├── cjk-tokenizer.ts     # CJK 分詞 2-gram
│       ├── cosine-similarity.ts # Float32Array 矩陣運算
│       ├── keyword-boost.ts     # 4 層關鍵字加權
│       ├── laminar-scoring.ts   # Online scoring
│       ├── llm-usage-logger.ts  # LLM cost monitoring（token usage tracking）
│       ├── maturity.ts          # 成熟度工具（DIMENSIONS / boost / callout / upgrade label）
│       ├── mode-detect.ts       # hasOpenAI() / isAgentEnabled() / resolveMode() 偵測
│       ├── npy-reader.ts        # numpy 檔案讀取
│       ├── observability.ts     # Laminar tracing
│       ├── report-file.ts       # 週報檔案 I/O
│       ├── result.ts            # Result<T,E> tagged union（Ok/Err/map/flatMap/unwrapOr）
│       └── sanitize.ts          # HTML escape 防 XSS
├── scripts/export-openapi.ts    # OpenAPI spec 匯出（CI 用，產生 docs-site/openapi.json）
├── scripts/
│   ├── ai-crawler-checker.ts  # AI crawler readiness CLI（GPTBot/ClaudeBot 等 10 bots）
│   ├── feedback-to-golden.ts  # 使用者回饋 → golden dataset 候選
│   └── eval-semantic.ts       # Retrieval eval（keyword/hybrid/rerank）
├── tests/                      # 67 個測試檔案，838 tests
├── tsup.config.ts            # 雙重 build（server + Lambda）
├── Dockerfile
├── package.json
├── tsconfig.json
└── vitest.config.ts
```

---

## 環境變數

建立 `.env` 檔案（或設定系統環境變數）：

```env
# 驗證模式：cf-access（容器預設）｜api-key（Lambda 預設；本機 docker-compose 明設）
AUTH_MODE=api-key
# api-key 模式
SEO_API_KEY=your-secret-api-key
# cf-access 模式（EKS 由 ConfigMap vocus-warehouse-access 的 team_domain／rag_auds 帶入）
CF_ACCESS_TEAM_DOMAIN=<team>.cloudflareaccess.com
RAG_AUDS=<aud1>,<aud2>
# chat 類路由每身分限流
RATE_LIMIT_CHAT=10
RATE_LIMIT_CHAT_DAILY=200
PORT=8002

# vocus-warehouse（設定後切換至 PG 模式；rag-api 由 K8s Secret vocus-warehouse-db-rag 掛載）
# JSON 檔（username、password、host、port、dbname）或每個 key 一個檔的目錄
VW_DB_SECRET_FILE_RAG=/var/run/secrets/db-rag
# verify-full 的 CA bundle（image 內預設已有，不必設）
# PGSSLROOTCERT=/etc/ssl/rds/global-bundle.pem

# LLM（OPENAI_API_KEY 與 LLM_BASE_URL 皆空 → LLM disabled，見「LLM 關閉時的行為」）
OPENAI_API_KEY=sk-...          # 線上 rag-api 目前不設（2026-10-23 裁決）
LLM_BASE_URL=                  # OpenAI 相容端點；空值 = OpenAI 官方；本機 Ollama：http://localhost:11434/v1
LLM_CHAT_MODEL=                # 覆寫 CHAT_MODEL（例：qwen3:8b）
LLM_EMBEDDING_MODEL=           # 覆寫 OPENAI_EMBEDDING_MODEL（例：nomic-embed-text）

# Optional
OPENAI_MODEL=gpt-6-luna
CHAT_MODEL=gpt-6-luna        # RAG Chat 問答模型（獨立於 OPENAI_MODEL）
REPORT_MODEL=gpt-6-sol           # 週報生成模型（需要深度分析）
ANTHROPIC_API_KEY=sk-ant-...   # Reranker + Context Relevance
CONTEXT_EMBEDDING_WEIGHT=0.6   # Contextual embedding 加權
RERANKER_ENABLED=auto          # Reranker 開關（auto/true/false）
AGENT_ENABLED=auto             # Agent mode 開關（auto/true/false，auto=有 OpenAI key 就啟用）
AGENT_MAX_TURNS=5              # Agent loop 最大輪數（1-10）
AGENT_TIMEOUT_MS=90000         # Agent loop 總逾時（ms）
LMNR_PROJECT_API_KEY=...       # Laminar tracing（若無則跳過）
```

---

## 資料層

### vocus-warehouse 模式（rag-api）

設定 `VW_DB_SECRET_FILE_RAG` 後啟用（角色 `warehouse_rag`，權限見 vocus-warehouse `db/roles-matrix.md`）：

- 啟動時一次 SELECT `app_qa_item` 全部 metadata（不含 embedding，statement_timeout 25s）
- `hybridSearch()` 呼叫 `match_qa_items($1::vector, LEAST($2, 200), …)` over-retrieve → TS re-rank
- `keywordSearch()` / `listQa()` / `getById()` 為 sync in-memory
- 有 `deleted_at` 的表（`app_session`、`app_metrics_snapshot`）每個 SELECT 明寫 `deleted_at IS NULL`（VW 無 RLS）
- secret 檔不在、TLS 驗證失敗、DB 連不上：路由回 503 `db_unavailable`，app 照常啟動；逾時回 504 `db_timeout`
- `/reports`、`/meeting-prep` 回 410 `not_available_in_rag_api`

本機跑整合測試需要 Docker（testcontainers 起 `pgvector/pgvector:pg17`，套 `tests/fixtures/schema/` 的 VW migration）；沒有 Docker 時設 `SKIP_PG_TESTS=1` 略過。

### 檔案模式（fallback）

未設 `VW_DB_SECRET_FILE_RAG` 時自動退回：

- 從 `qa_final.json` + `qa_embeddings.npy` 載入
- 全量 in-memory cosine similarity

---

## LLM 關閉時的行為（線上 rag-api 現況）

`OPENAI_API_KEY` 與 `LLM_BASE_URL` 皆空時視為 LLM disabled（`src/services/llm-client.ts`）。決策見 KB `wiki/decisions/2026-10-23-rag-online-llm-disabled-local-ollama-for-eval.md`。

| 路由 | LLM disabled | 說明 |
|---|---|---|
| `POST /chat`、`POST /chat/stream` | 501 `llm_disabled` | 先過 rate limit，再於 QA 載入前擋下 |
| `POST /sessions/:id/messages` | 501 `llm_disabled` | 寫入使用者訊息之前就擋下，不留半套對話 |
| `POST /search` `mode: "hybrid"`／`"semantic"` | 501 `llm_disabled` | 需要查詢 embedding |
| `POST /search` 未指定 `mode` | 200 keyword | `data` 與 `meta` 帶 `mode: "keyword"`、`llm_disabled: true` |
| reranker、任何 embedding 呼叫 | 501 `llm_disabled` | 服務層拋 `FeatureUnavailableError`，error handler 轉 501 |
| QA、keyword search、synonyms、feedback、metrics、sessions 讀與軟刪 | 200 | 不需要 LLM |

501 回應格式：

```json
{ "data": null, "error": "llm_disabled", "message": "線上未啟用 LLM，請在本機模式執行", "meta": { "request_id": "…", "version": "1.0" } }
```

`app_llm_usage` 只在實際呼叫 LLM 時寫入（chat、chat stream、agent、embedding），LLM disabled 時不會有列。

### pipeline 路由（rag-api，PG 模式）

觸發類（`fetch`、`extract-qa`、`dedupe-classify`、`fetch-articles`）與讀本機檔案的路由（`meetings`、`meetings/:id/preview`、`unprocessed`、`logs`、`source-docs/:collection/:file/preview`）回 501 `run_locally`，訊息「此流程在本機執行，請用 make pipeline」。清單在 `src/routes/pipeline-gates.ts`。本機檔案模式照舊執行。`/status`、`/source-docs` 從 `app_qa_item` 推導；metrics、crawled-not-indexed、llm-usage 照常。

## 本機 Ollama 模式

eval 與 LLM 判斷在 Mac 本機跑：rag-api 指向本機 Ollama 的 OpenAI 相容端點。

```bash
ollama serve                         # 預設 http://localhost:11434
ollama pull qwen3:8b                 # 對話模型（依機器記憶體挑）

cd api
AUTH_MODE=api-key \
SEO_API_KEY=local-dev \
LLM_BASE_URL=http://localhost:11434/v1 \
LLM_CHAT_MODEL=qwen3:8b \
VW_DB_SECRET_FILE_RAG=$HOME/.config/vocus-warehouse/db-rag.json \
pnpm dev
```

- `VW_DB_SECRET_FILE_RAG` 指向 JSON（`username`、`password`、`host`、`port`、`dbname`）或每個 key 一個檔的目錄，同 K8s Secret 格式。檔案放 repo 外，不要 commit。未設則走檔案模式（`output/qa_final.json`）。
- 連線一律 `sslmode=verify-full`，會比對主機名。經 port-forward 連 RDS 時，secret 的 `host` 要寫 RDS endpoint，並在 `/etc/hosts` 把它指到 `127.0.0.1`（本 PR 未實測，provisional）。
- **embedding 不相容**：`app_qa_item` 的向量是 `text-embedding-3-small`（1536 維）。本機 embedding 模型（例如 `nomic-embed-text`）維度與語意空間都不同，拿來查 `match_qa_items` 結果無意義。本機只用 keyword（`mode: "keyword"`），或另行用同一個本機模型重算全部向量後再做 hybrid。
- `LLM_BASE_URL` 有值時 OpenAI SDK 仍要求非空 apiKey，程式以佔位字串 `local-llm-no-key` 帶入，Ollama 不驗證。
- `app_llm_usage` 會記本機呼叫（model 為 Ollama 模型名）；與 OpenAI 時期的分數、成本不可比。

### eval 打 rag-api

`evals/eval_crawled_not_indexed.py` 讀以下 env，不改其他 eval：

| env | 預設 | 用途 |
|---|---|---|
| `EVAL_API_BASE` | `http://localhost:8002` | 服務根網址；線上 rag-api 為 `https://warehouse-api.vocus.cc` |
| `EVAL_API_PREFIX` | `/api/v1` | 路由前綴；rag-api 經 tunnel 為 `/internal/rag` |
| `SEO_API_KEY` | 空 | 有值則帶 `X-API-Key`（api-key 模式） |
| `CF_ACCESS_CLIENT_ID`、`CF_ACCESS_CLIENT_SECRET` | 空 | 兩者皆有值則帶 Cloudflare Access service token header |

## 部署架構

### Lambda + Function URL（生產環境，v2.25）

```
pnpm build → tsup dual build
  ├── dist/           # Server build（開發/Docker 用）
  └── dist-lambda/    # Lambda build（self-contained ESM ~3.4MB）
      └── lambda.js   # noExternal bundle + createRequire shim

zip lambda.js + package.json → aws lambda update-function-code
  → Lambda Function URL（HTTPS auto，arm64，~$0/月）
```

**Lambda 設定**：

- Function: `seo-insight-api`
- Architecture: arm64（便宜 20%）
- Runtime: Node.js 22
- Memory: 512 MB / Timeout: 120s
- Function URL: `https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws/`

### Docker（本地驗證用）

```bash
docker-compose up              # 啟動所有服務
docker-compose logs seo-api-ts # 監看 Hono API 日誌
```

---

## Observability（Laminar 整合）

API 伺服器透過 `@lmnr-ai/lmnr` JS SDK 整合 Laminar tracing。

### 設定

在 `.env` 加入 `LMNR_PROJECT_API_KEY`。若未設定則靜默跳過（不影響正常功能）。

### 追蹤範圍

| Span            | 模組                    | 說明                  |
| --------------- | ----------------------- | --------------------- |
| `rag_chat`      | `services/rag-chat.ts`  | RAG 問答完整流程      |
| `get_embedding` | `services/embedding.ts` | OpenAI embedding 呼叫 |

### Online Scoring

`utils/laminar-scoring.ts` 在每次 RAG 回應後自動附加 4 個評分：

- `answer_length` — 回答是否超過 50 字元
- `has_sources` — 是否有引用來源
- `top_source_score` — 最佳來源的相似度分數
- `source_count` — 來源數量 / 5（上限 1.0）

---

## Request Logging

每個 HTTP request（除 `/health`）自動產生一行結構化 JSON log，包含 `X-Request-Id` response header 供前端關聯。

### 日誌格式

```json
{
  "level": "info",
  "method": "GET",
  "path": "/api/v1/qa",
  "status": 200,
  "duration_ms": 42,
  "request_id": "a1b2c3d4-...",
  "timestamp": "2026-03-07T12:00:00.000Z"
}
```

| 欄位          | 說明                                               |
| ------------- | -------------------------------------------------- |
| `level`       | `info`（2xx/3xx）、`warn`（4xx）、`error`（5xx）   |
| `method`      | HTTP method                                        |
| `path`        | 請求路徑（不含 query string）                      |
| `status`      | HTTP status code                                   |
| `duration_ms` | 請求處理時間（毫秒）                               |
| `request_id`  | UUID v4（同時設為 `X-Request-Id` response header） |
| `timestamp`   | ISO 8601 時間戳                                    |

**安全設計**：不記錄 API key header、request body、query string（防洩漏 token）。`/health` 路徑被排除以避免高頻心跳噪音。

### 本地開發

Terminal 直接看到 JSON log，可用 `jq` 美化：

```bash
pnpm dev 2>&1 | jq .
```

### CloudWatch Logs

Lambda 部署後，可在 AWS CloudWatch 查看 request log：

| 頁面          | URL                                                                                                                                                                                      |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Log Group     | [`/aws/lambda/seo-insight-api`](https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fseo-insight-api) |
| Logs Insights | [CloudWatch Logs Insights](https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logsV2:logs-insights)                                                     |

CLI 查看（不需要登入 Console）：

```bash
# 即時追蹤最近 1 小時的 log
aws logs tail /aws/lambda/seo-insight-api --since 1h --follow --region ap-northeast-1 --profile seo-deployer

# 只看 request log（過濾 JSON 格式）
aws logs tail /aws/lambda/seo-insight-api --since 1h --region ap-northeast-1 --profile seo-deployer | grep '"level"'
```

### Logs Insights 查詢範例

在 [Logs Insights](https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logsV2:logs-insights) 頁面選擇 `/aws/lambda/seo-insight-api` log group 後，可用以下查詢：

```sql
-- 找出所有 5xx 錯誤
fields @timestamp, method, path, status, duration_ms, request_id
| filter status >= 500
| sort @timestamp desc
| limit 20

-- 依路徑統計 P95 延遲
stats percentile(duration_ms, 95) as p95, count(*) as total by path
| sort p95 desc

-- 用 request_id 關聯前端 502 錯誤
fields @timestamp, method, path, status, duration_ms
| filter request_id = "a1b2c3d4-..."

-- 錯誤率趨勢（每 5 分鐘）
stats sum(status >= 500) / count(*) * 100 as error_rate by bin(5m)
```

### 502 除錯 Workflow

1. 前端收到 502 → 檢查 response header `X-Request-Id`
2. CloudWatch Logs Insights → `filter request_id = "<id>"`
3. 若找到 → 看 `status` + `duration_ms` 判斷後端是否正常回應
4. 若找不到 → 請求未到達 Lambda（DNS / Function URL 問題）
5. 若 `duration_ms` 接近 Lambda timeout（120s）→ 考慮增加 timeout 或優化

---

## 測試

所有路由都有完整的單元 + 整合測試：

```bash
pnpm test                      # 執行所有測試
pnpm test:watch               # 監視模式
pnpm test:coverage            # 覆蓋率（目標 ≥ 80%）
```

**測試套件統計（v3.6）：**

- 總測試數：734 個（65 個測試檔案）
- 通過：734/734
- 覆蓋率：80%+

---

## 常見問題

### 1. 無法連線到 API

檢查 port 8002 是否正常運行：

```bash
curl http://localhost:8002/health
```

### 2. API Key 驗證失敗

確保 header 中帶有正確的 `X-API-Key`：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8002/api/v1/qa
```

### 3. Rate Limit 超過

等待 1 分鐘後重試，或聯絡管理員提升限額。

### 4. Search / Chat 回傳空結果

1. 確認 Supabase 環境變數已設定（或 `qa_final.json` 存在於 output/）
2. 若無 OpenAI Key，search 會自動降級至 keyword（可能會失準）
3. 檢查 Lambda logs 或本地 console 確認 QAStore 載入狀態

---

## 相關文件

- **主架構**：[`/research/06-project-architecture.md`](/research/06-project-architecture.md)
- **架構圖**：[`/research/06b-architecture-diagram.md`](/research/06b-architecture-diagram.md)
- **部署指南**：[`/research/07-deployment.md`](/research/07-deployment.md)
- **專案說明**：[`/README.md`](/README.md)
- **API 規格**：[`/openapi.json`](http://localhost:8002/openapi.json)（或 [`/docs`](http://localhost:8002/docs) 互動式探索）
- **全域指令**：[`/CLAUDE.md`](/CLAUDE.md)
