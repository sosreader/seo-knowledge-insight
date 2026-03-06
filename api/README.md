# Hono TypeScript API (v2.25)

REST API 伺服器，主要架構採用 Hono 框架。

**特點：**
- 9 個路由器（Routers）、32 個 API endpoints
- Rate limiting + API Key 認證（timingSafeEqual）
- Zod schema validation
- Local Mode graceful degradation（無 OpenAI 時自動降級）
- Supabase pgvector hybrid search（自動偵測，fallback 檔案模式）
- Lambda + Function URL 部署（arm64，~$0/月）
- 安全加固：SSRF whitelist (pipeline schema)、auth fail-fast (production 503)、HTTP security headers middleware、session UUID validation

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

## API 路由清單

### 1. 健康檢查 (health)

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/health` | 伺服器健康檢查 | ✗ | — |

### 2. Q&A 知識庫 (qa) — 4 個 endpoints

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/api/v1/qa` | 列出所有 Q&A（支援分頁、source_type/source_collection filter） | ✓ | 60/min |
| GET | `/api/v1/qa/{id}` | 取得單筆 Q&A 詳情（id: 16-char hex 或 integer seq） | ✓ | 60/min |
| GET | `/api/v1/qa/categories` | 列出所有分類標籤 | ✓ | 60/min |
| GET | `/api/v1/qa/collections` | 列出所有 collection（含 source_type + count） | ✓ | 60/min |

### 3. 語意搜尋 (search) — 1 個 endpoint

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| POST | `/api/v1/search` | 混合搜尋（有 OpenAI: hybrid，無: keyword fallback） | ✓ | 60/min |

**Graceful Degradation:**
- 有 OpenAI API Key：使用 embedding + cosine similarity（語意搜尋）
- 無 OpenAI API Key：自動降級至 keyword-only 搜尋

### 4. RAG 問答 (chat) — 1 個 endpoint

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| POST | `/api/v1/chat` | 互動式問答（有 OpenAI: RAG + GPT，無: context-only） | ✓ | 20/min |

**Graceful Degradation:**
- 有 OpenAI API Key：檢索相關 Q&A + GPT 生成回答
- 無 OpenAI API Key：僅回傳相關 Q&A 內容

### 5. SEO 週報 (reports) — 3 個 endpoints

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/api/v1/reports` | 列出所有週報 | ✓ | 60/min |
| GET | `/api/v1/reports/{date}` | 取得單篇週報（date: YYYYMMDD） | ✓ | 60/min |
| POST | `/api/v1/reports/generate` | 觸發週報生成（同步，120s timeout；`cache_hit` 欄位） | ✓ | 5/min |

### 6. 對話管理 (sessions) — 5 個 endpoints

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/api/v1/sessions` | 列出所有對話 | ✓ | 60/min |
| GET | `/api/v1/sessions/{id}` | 取得單個對話詳情 | ✓ | 60/min |
| POST | `/api/v1/sessions` | 建立新對話 | ✓ | 20/min |
| POST | `/api/v1/sessions/{id}/messages` | 新增訊息到對話（支援 context-only 降級） | ✓ | 20/min |
| DELETE | `/api/v1/sessions/{id}` | 刪除對話 | ✓ | 60/min |

### 7. 回饋收集 (feedback) — 1 個 endpoint

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| POST | `/api/v1/feedback` | 提交使用者回饋 | ✓ | 60/min |

### 8. Pipeline 管理 (pipeline) — 16 個 endpoints

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/api/v1/pipeline/status` | 各步驟完成狀態 | ✓ | 60/min |
| GET | `/api/v1/pipeline/meetings` | 會議列表（含 metadata） | ✓ | 60/min |
| GET | `/api/v1/pipeline/meetings/{id}/preview` | Markdown 預覽 | ✓ | 60/min |
| GET | `/api/v1/pipeline/unprocessed` | 待處理的 Markdown 列表 | ✓ | 60/min |
| GET | `/api/v1/pipeline/logs` | Fetch 歷史日誌 | ✓ | 60/min |
| POST | `/api/v1/pipeline/fetch` | 觸發 Notion 增量擷取 | ✓ | 60/min |
| POST | `/api/v1/pipeline/fetch-articles` | 觸發外部文章擷取（Medium + iThome + Google Cases） | ✓ | 60/min |
| POST | `/api/v1/pipeline/extract-qa` | 觸發 Q&A 萃取 | ✓ | 60/min |
| POST | `/api/v1/pipeline/dedupe-classify` | 觸發去重 + 分類 | ✓ | 60/min |
| GET | `/api/v1/pipeline/source-docs` | 列出所有來源文件（支援 filter + pagination） | ✓ | 60/min |
| GET | `/api/v1/pipeline/source-docs/:collection/:file/preview` | 來源文件 Markdown 預覽 | ✓ | 60/min |
| POST | `/api/v1/pipeline/metrics` | 取得 Pipeline metrics | ✓ | 60/min |
| POST | `/api/v1/pipeline/metrics/save` | 儲存指標快照 | ✓ | 60/min |
| GET | `/api/v1/pipeline/metrics/snapshots` | 列出指標快照清單 | ✓ | 60/min |
| DELETE | `/api/v1/pipeline/metrics/snapshots/:id` | 刪除指定快照 | ✓ | 60/min |

### 9. 同義詞管理 (synonyms) — 4 個 endpoints（v2.10 新增）

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| GET | `/api/v1/synonyms` | 列出所有同義詞（靜態 + 自訂） | ✓ | 60/min |
| POST | `/api/v1/synonyms` | 新增自訂同義詞 | ✓ | 60/min |
| PUT | `/api/v1/synonyms/{term}` | 更新自訂同義詞 | ✓ | 60/min |
| DELETE | `/api/v1/synonyms/{term}` | 刪除自訂同義詞 | ✓ | 60/min |

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

**欄位說明**：

- `cache_hit: boolean` — 是否命中快取。若 `true` 表示該報告已存在（相同 metrics hash），直接回傳既有內容；若 `false` 表示新生成報告
- `date: string` — 報告日期（YYYYMMDD 格式）
- `report: string` — 週報 Markdown 內容

**快取機制**：

- Hash 計算移除 frontmatter 和 meta comment，避免 `generated_at` 時間戳導致 cache miss
- 質量評估（quality eval）改用 async，並包裝在 Laminar trace 內以便追蹤

---

## 認證與授權

### API Key

在 header 帶 `X-API-Key`：

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8002/api/v1/qa
```

**環境變數設定：** `.env` 中設定 `SEO_API_KEY`

### Rate Limiting

根據端點不同，設定不同的限制：

- **搜尋/Q&A 端點**：60 requests / min
- **Chat 端點**：20 requests / min
- **Report 生成**：5 requests / min

超過限制時，伺服器回傳 429 Limit Exceeded。

> **Lambda 環境**：in-memory rate limiting 無效（每個執行環境有獨立 Map），自動 bypass。需要限流時應使用 API Gateway throttling。

---

## 項目結構

```
api/
├── src/
│   ├── index.ts              # 入口點（middleware + route mount + initStores()）
│   ├── lambda.ts             # Lambda 入口（cold start + hono/aws-lambda handler）
│   ├── config.ts             # Zod 驗證環境變數 + paths
│   ├── routes/               # 9 個路由
│   │   ├── health.ts
│   │   ├── qa.ts
│   │   ├── search.ts
│   │   ├── chat.ts
│   │   ├── reports.ts
│   │   ├── sessions.ts
│   │   ├── feedback.ts
│   │   ├── pipeline.ts
│   │   └── synonyms.ts
│   ├── middleware/
│   │   ├── auth.ts              # API Key 驗證（timingSafeEqual）
│   │   ├── rate-limit.ts        # Sliding window 速率限制（Lambda 自動 bypass）
│   │   ├── cors.ts              # CORS 設定
│   │   ├── security-headers.ts  # HTTP security headers（X-Content-Type-Options 等）
│   │   └── error-handler.ts     # 錯誤處理
│   ├── store/
│   │   ├── qa-store.ts              # QAStore singleton + loadQaStore() factory
│   │   ├── supabase-client.ts       # Supabase REST thin client（no SDK）
│   │   ├── supabase-qa-store.ts     # SupabaseQAStore（pgvector hybrid search）
│   │   ├── supabase-session-store.ts # SupabaseSessionStore
│   │   ├── supabase-report-store.ts  # SupabaseReportStore
│   │   ├── supabase-snapshot-store.ts # SupabaseSnapshotStore
│   │   ├── supabase-synonyms-store.ts # SupabaseSynonymsStore
│   │   ├── supabase-learning-store.ts # SupabaseLearningStore
│   │   ├── search-engine.ts         # 搜尋引擎（hybrid + keyword）
│   │   ├── session-store.ts         # 對話歷史儲存（file fallback）
│   │   ├── learning-store.ts        # 失敗記憶（JSONL fallback）
│   │   └── synonyms-store.ts       # 同義詞（雙層：靜態 + custom JSON）
│   ├── services/
│   │   ├── embedding.ts      # OpenAI embedding 服務
│   │   ├── rag-chat.ts       # RAG 問答邏輯
│   │   ├── reranker.ts       # Claude Haiku reranker
│   │   ├── context-relevance.ts  # Context Relevance 評估
│   │   ├── report-generator-local.ts  # ECC 6 維度本地週報
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
│   │   ├── eval.ts
│   │   └── synonyms.ts
│   └── utils/
│       ├── npy-reader.ts     # numpy 檔案讀取
│       ├── cosine-similarity.ts  # Float32Array 矩陣運算
│       ├── keyword-boost.ts  # 4 層關鍵字加權
│       ├── cjk-tokenizer.ts  # CJK 分詞 2-gram
│       ├── sanitize.ts       # HTML escape 防 XSS
│       ├── mode-detect.ts    # hasOpenAI() / hasSupabase() 偵測
│       ├── observability.ts  # Laminar tracing
│       ├── qa-filter.ts        # 共用 QA filter 邏輯
│       └── laminar-scoring.ts  # Online scoring
├── tests/                      # 38 個測試檔案，353 tests
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
# 必要
SEO_API_KEY=your-secret-api-key
PORT=8002

# Supabase（設定後自動切換至 pgvector 模式）
SUPABASE_URL=https://eqrlomuujichshkbtoat.supabase.co
SUPABASE_ANON_KEY=your_anon_key

# Optional
OPENAI_API_KEY=sk-...          # 若無，則 search/chat 自動降級
OPENAI_MODEL=gpt-5.2
CHAT_MODEL=gpt-5.2             # RAG Chat 問答模型（獨立於 OPENAI_MODEL）
ANTHROPIC_API_KEY=sk-ant-...   # Reranker + Context Relevance
CONTEXT_EMBEDDING_WEIGHT=0.6   # Contextual embedding 加權
RERANKER_ENABLED=auto          # Reranker 開關（auto/true/false）
LMNR_PROJECT_API_KEY=...       # Laminar tracing（若無則跳過）
```

---

## 資料層

### Supabase pgvector 模式（預設）

設定 `SUPABASE_URL` + `SUPABASE_ANON_KEY` 後自動啟用：

- 啟動時 paginated fetch 所有 QA metadata（不含 embedding）
- `hybridSearch()` 透過 pgvector RPC over-retrieve → TS re-rank
- `keywordSearch()` / `listQa()` / `getById()` 為 sync in-memory

### 檔案模式（fallback）

無 Supabase 設定時自動退回：

- 從 `qa_final.json` + `qa_embeddings.npy` 載入
- 全量 in-memory cosine similarity

---

## Local Mode（無 OpenAI 時的自動降級）

### Search 端點

**有 OpenAI：** Embedding + Cosine Similarity（語意搜尋）

**無 OpenAI：** Keyword-only 搜尋（CJK 分詞 + 關鍵字加權）

### Chat 端點

**有 OpenAI：** RAG Pipeline（檢索 → GPT 生成）

**無 OpenAI：** Context-only（僅回傳相關 Q&A，不生成回答）

---

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
- Memory: 512 MB / Timeout: 30s
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

| Span | 模組 | 說明 |
|------|------|------|
| `rag_chat` | `services/rag-chat.ts` | RAG 問答完整流程 |
| `get_embedding` | `services/embedding.ts` | OpenAI embedding 呼叫 |

### Online Scoring

`utils/laminar-scoring.ts` 在每次 RAG 回應後自動附加 4 個評分：

- `answer_length` — 回答是否超過 50 字元
- `has_sources` — 是否有引用來源
- `top_source_score` — 最佳來源的相似度分數
- `source_count` — 來源數量 / 5（上限 1.0）

---

## 測試

所有路由都有完整的單元 + 整合測試：

```bash
pnpm test                      # 執行所有測試
pnpm test:watch               # 監視模式
pnpm test:coverage            # 覆蓋率（目標 ≥ 80%）
```

**測試套件統計（v2.25）：**
- 總測試數：353 個（38 個測試檔案）
- 通過：353/353 (100%)
- 覆蓋率：80%

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
- **全域指令**：[`/CLAUDE.md`](/CLAUDE.md)
