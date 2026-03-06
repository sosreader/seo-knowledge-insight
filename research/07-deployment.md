# 部署架構

> 屬於 [research/](./README.md)。涵蓋 Hono TypeScript API 架構、Lambda + Function URL 部署、Supabase 資料層。
>
> **v2.24**（2026-03-06）：Lambda + Function URL 部署。v2.3 從 FastAPI 遷移至 Hono TypeScript。

---

## 20. Hono TypeScript API：知識庫 HTTP 服務

> v2.3（2026-03-04）從 Python FastAPI 遷移至 TypeScript Hono。保持相同 API 介面，全面重寫內部實作。

### 資料層架構（Phase 2 — Supabase pgvector）

```
# Phase 1（檔案模式）              # Phase 2（Supabase，v2.24 完成）
Float32Array @ cosine similarity  →  PostgreSQL + pgvector IVFFlat
Map<string, QAItem> 啟動載入      →  Supabase REST paginated fetch（metadata only）
同步 hybridSearch()               →  async RPC match_qa_items()（pgvector + TS re-rank）
```

**Factory Pattern**：`hasSupabase()` 偵測 env → `SupabaseQAStore` 或 `QAStore`。
Route 層零修改，只有 `hybridSearch()` 從 sync 改為 async。

**Supabase 配置**：
- Project: `eqrlomuujichshkbtoat`（ap-northeast-1）
- Tables: `qa_items`（1,323 rows + vector(1536)）、`eval_runs`
- RPC: `match_qa_items()`、`search_qa_items_keyword()`
- Thin REST client（`supabase-client.ts`），不依賴 `@supabase/supabase-js`
- MCP: `https://mcp.supabase.com/mcp?project_ref=eqrlomuujichshkbtoat`

### QAStore：啟動時載入資料

```typescript
// api/src/index.ts
const isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV;

let _initPromise: Promise<void> | null = null;

export function initStores(): Promise<void> {
  if (!_initPromise) {
    _initPromise = _doInitStores().catch((err) => {
      _initPromise = null;  // 失敗時 reset，下次 retry
      throw err;
    });
  }
  return _initPromise;
}

if (process.env.NODE_ENV !== "test" && !isLambda) {
  await initStores();
  serve({ fetch: app.fetch, port }, (info) => {
    console.log(`Server running on http://localhost:${info.port}`);
  });
}
```

**雙模式啟動**：
- **Node.js 直接執行**：`initStores()` + `serve()`
- **Lambda**：由 `lambda.ts` 呼叫 `initStores()`（cold start），不啟動 HTTP server
- **Idempotency**：`_initPromise` 保證只初始化一次；失敗 reset 允許 retry
- **測試**：`NODE_ENV=test` 跳過載入，由各測試自行控制

### TypeScript cosine similarity（取代 numpy）

```typescript
// api/src/utils/cosine-similarity.ts
// 預先 L2 歸一化，讓點積 = cosine similarity
export function normalizeRows(
  data: Float32Array, rows: number, cols: number
): Float32Array { ... }

export function matrixDotVector(
  matrix: Float32Array, vec: Float32Array, rows: number, cols: number
): Float32Array { ... }
```

```typescript
// api/src/store/qa-store.ts
search(queryEmbedding: Float32Array, topK = 5, category = null) {
  const qNorm = normalizeL2(qVec);
  const scores = matrixDotVector(this.embNorm, qNorm, this.items.length, this.embDim);
  // sort + take top-K
}
```

**數學同上**：兩個 L2 歸一化向量的點積 = cosine similarity。
`Float32Array` 矩陣乘法一次計算全部 1,323 筆相似度。效能與 numpy 相當。

### Hybrid Search（語意 + 關鍵字 + 同義詞 + 時效性）

```typescript
// api/src/store/search-engine.ts
// 四層加權：cosine similarity + keyword boost + synonym match + freshness decay
engine.search(query, queryVec, topK, category, minScore);
```

- **語意**：cosine similarity（Float32Array dot product）
- **關鍵字**：CJK n-gram + keyword boost（`utils/keyword-boost.ts`）
- **同義詞**：enrichment 預計算，搜尋時匹配 synonym list
- **時效性**：`freshness_score` = `exp(-0.693 x age/540d)`

### RAG Chat 實作

```typescript
// api/src/services/rag-chat.ts
async function ragChat(message: string, history: ChatMessage[]): Promise<RagResult> {
  // 1. 把問題 embed（OpenAI API）
  const queryVec = await getEmbedding(message);

  // 2. hybrid search 找 context
  const hits = qaStore.hybridSearch(message, queryVec, config.CHAT_CONTEXT_K);

  // 3. 組裝 system message + context + history
  const messages = [
    { role: "system", content: SEO_EXPERT_SYSTEM_PROMPT },
    { role: "system", content: `--- 知識庫 ---\n${formatHits(hits)}` },
    ...history,
    { role: "user", content: message },
  ];

  // 4. GPT 生成回答
  const resp = await openai.chat.completions.create({
    model: config.OPENAI_MODEL, messages, temperature: 0.3,
  });
  return { answer: resp.choices[0].message.content, sources };
}
```

### 模組結構

```
api/src/
├── index.ts              # 入口：全域 middleware + route mounting + initStores()
├── lambda.ts             # Lambda 入口：cold start + hono/aws-lambda handler
├── config.ts             # Zod 驗證環境變數 + 資料路徑
├── routes/               # 9 個路由（v2.24）
│   ├── health.ts         # GET /health（不需認證）
│   ├── qa.ts             # GET /qa, /qa/categories, /qa/collections, /qa/{id}
│   ├── search.ts         # POST /search（hybrid + keyword fallback）
│   ├── chat.ts           # POST /chat（RAG + context-only fallback）
│   ├── reports.ts        # GET /reports, /reports/{date}, POST /reports/generate
│   ├── sessions.ts       # CRUD /sessions
│   ├── feedback.ts       # POST /feedback
│   ├── pipeline.ts       # 16 個 pipeline 管理端點
│   └── synonyms.ts       # CRUD /synonyms（v2.10 新增）
├── middleware/            # 4 個中間件
│   ├── auth.ts           # X-API-Key + timingSafeEqual
│   ├── cors.ts           # CORS origins 白名單
│   ├── error-handler.ts  # 全域錯誤處理，不洩漏 stack trace
│   └── rate-limit.ts     # Sliding window，per-IP per-path
├── store/                # 5 個資料層（v2.10+）
│   ├── qa-store.ts       # QAStore singleton（JSON + npy → 記憶體）
│   ├── search-engine.ts  # Hybrid search 引擎
│   ├── session-store.ts  # 檔案式對話儲存（Repository Pattern）
│   ├── learning-store.ts # Learning Store（失敗記憶庫）
│   └── synonyms-store.ts # 同義詞（雙層：靜態 + custom JSON）
├── services/             # 7 個服務（v2.24）
│   ├── embedding.ts      # OpenAI Embedding API
│   ├── rag-chat.ts       # RAG 問答 + context 組裝
│   ├── reranker.ts       # Claude Haiku reranker（v2.11）
│   ├── context-relevance.ts  # Context Relevance 評估（v2.12）
│   ├── report-generator-local.ts  # ECC 6 維度本地週報（v2.13）
│   ├── report-evaluator.ts  # 5 維度品質評估（v2.13）
│   └── pipeline-runner.ts # Python CLI 代理
├── schemas/              # 10 個 Zod schema（v2.24）
│   ├── api-response.ts   # ApiResponse<T> envelope（ok/fail）
│   ├── qa.ts
│   ├── search.ts
│   ├── chat.ts
│   ├── report.ts
│   ├── session.ts
│   ├── feedback.ts
│   ├── pipeline.ts
│   ├── eval.ts
│   └── synonyms.ts
└── utils/                # 8 個工具（v2.24）
    ├── npy-reader.ts     # 解析 .npy 二進制格式
    ├── cosine-similarity.ts  # L2 正規化 + 矩陣點積
    ├── keyword-boost.ts  # CJK n-gram 關鍵字加權
    ├── sanitize.ts       # HTML escape 防 XSS
    ├── cjk-tokenizer.ts  # CJK 分詞 2-gram
    ├── mode-detect.ts    # hasOpenAI() 偵測
    ├── observability.ts  # Laminar tracing
    └── laminar-scoring.ts # Online scoring
```

**設計原則**：`api/` 自包含，不 import pipeline 的 `utils/` 或 `scripts/`。日後可獨立部署。

### 技術棧

| 層級 | 技術 | 版本 |
|------|------|------|
| Runtime | Node.js | >= 22 |
| Framework | Hono | 4.x |
| Server | @hono/node-server | 1.x |
| Validation | Zod | 4.x |
| Build | tsup | 8.x |
| Dev | tsx watch | 4.x |
| Test | Vitest | 4.x |
| Package Manager | pnpm | 10.x |
| Language | TypeScript | 5.9+ |

---

## 21. AWS 部署模式

> 2026-03-06 從 App Runner 遷移至 Lambda + Function URL（成本 ~$0/月）。

### 21.1 部署選項演進

| 方案                              | 複雜度 | 月費估算    | 適合場景                      |
| --------------------------------- | ------ | ----------- | ----------------------------- |
| ~~ECR + EC2 SSM~~（v0.3--v1.20） | 中     | ~$5-10      | 已淘汰（需管主機）            |
| ~~ECR + App Runner~~（v2.3--v2.23）| 低    | ~$5-7       | 已淘汰（改用 Lambda 更便宜）  |
| ECR + ECS Fargate                 | 高     | ~$20-30     | 需要 auto-scaling + ALB       |
| **Lambda + Function URL（當前）** | **低** | **~$0**     | **Free tier 足夠低流量場景**  |

**Lambda 遷移理由**：
- **成本最優**：Free tier 含 100 萬次/月 + 400,000 GB-seconds，低流量場景月費 ~$0
- **arm64**：比 x86_64 便宜 20%（Lambda 建立後不可更改架構，需刪除重建）
- **Function URL**：免費內建 HTTPS endpoint，不需 API Gateway
- **Zero ops**：無伺服器管理、自動 scaling、自動 patch

### 21.2 Lambda + Function URL 部署流程

```
git push main
    |
GitHub Actions (.github/workflows/deploy-ts-api.yml)
    |
pnpm build（tsup Lambda build → dist-lambda/lambda.js，~3.4MB self-contained）
    |
zip dist-lambda/lambda.js + package.json（type:module）
    |
aws lambda update-function-code --function-name seo-insight-api
    |
Lambda Function URL（自動 HTTPS）
    |
https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws/
```

### 21.3 Lambda 架構設計

#### 入口檔案（`api/src/lambda.ts`）

```typescript
import { handle } from "hono/aws-lambda";
import { app, initStores } from "./index.js";
import { flushLaminar } from "./utils/observability.js";

const ready = initStores().catch((err) => {  // Cold start 初始化
  console.error("Lambda cold start initStores failed:", err);
});
const honoHandler = handle(app);

export const handler: typeof honoHandler = async (event, context) => {
  await ready;                         // 確保 stores 載入完成
  const response = await honoHandler(event, context);
  await flushLaminar().catch((err) => console.warn("Laminar flush failed:", err));
  return response;
};
```

**設計重點**：
- **Cold start pattern**：module-level `initStores()` promise，每次 invocation `await ready`
- **Idempotency guard**（`index.ts`）：`_initPromise` 失敗時 reset 為 null，下次 retry
- **`hono/aws-lambda`**：`handle()` 將 Hono app 轉為 Lambda handler
- **Laminar flush**：每次 invocation 結束前 flush traces，避免 Lambda freeze 遺失

#### Cold Start Timeout 考量

Lambda cold start 時 `initStores()` 需從 Supabase 載入 QA metadata（1,323 rows，3 pages）。
當 Supabase 本身也冷時（PostgREST connection pool 重建），預設 10 秒 timeout 可能不夠。

```typescript
// api/src/store/supabase-client.ts
export const SUPABASE_TIMEOUT_MS = 10_000;  // 一般 API 請求

// supabaseSelect() 接受 timeoutMs 參數覆蓋預設值
export async function supabaseSelect<T>(
  table: string, queryString?: string, timeoutMs?: number
): Promise<T[]> { ... }

// api/src/store/supabase-qa-store.ts
const LOAD_TIMEOUT_MS = 25_000;  // 啟動載入用較長 timeout
```

**實測數據**：
- Supabase 暖時：load 1,323 items ≈ 1.5-2 秒
- Supabase 冷時：可能超過 10 秒 → 改用 25 秒 timeout

#### Supabase RPC 函數注意事項

`match_qa_items()` RPC 需注意：
- **VOLATILE**（非 STABLE）：因為使用 `SET LOCAL ivfflat.probes = 5`
- **search_path** 必須含 `extensions`：pgvector operators 在 extensions schema
- **型別精確匹配**：`<=>` 回傳 `double precision`，function return type 若為 `real` 須 cast

#### Lambda 端點資料完整性

Lambda 無檔案系統，部分端點透過 Supabase fallback 提供資料：

| 端點 | Lambda 資料來源 | 資料量 | 說明 |
|------|----------------|--------|------|
| `GET /qa` | SupabaseQAStore | 1,323 | pgvector + in-memory metadata |
| `POST /search` | Supabase RPC `match_qa_items` | hybrid | pgvector + TS re-rank |
| `POST /sessions/*/messages` | Supabase + OpenAI | RAG 回答 | 完整 RAG pipeline |
| `GET /reports` | SupabaseReportStore | 31 | 完整 markdown content |
| `GET /sessions` | SupabaseSessionStore | 8 | CRUD 完整 |
| `GET /pipeline/status` | qaStore.collections | 6 步驟 | 從 QA metadata 計算 |
| `GET /pipeline/source-docs` | **qaStore fallback** | 230 | `buildSourceDocsFromStore()` 從 QA metadata group by 反推 |
| `GET /pipeline/metrics/snapshots` | SupabaseSnapshotStore | 2 | CRUD 完整 |
| `GET /synonyms` | SupabaseSynonymsStore | 0 custom | 讀寫完整 |
| `GET /pipeline/meetings` | 無（回傳空） | 0 | Notion JSON 為本地產物 |
| `GET /pipeline/unprocessed` | 無（回傳空） | 0 | 待處理 markdown 為本地產物 |
| `GET /pipeline/logs` | 無（回傳空） | 0 | fetch 日誌為本地產物 |

**source-docs fallback 設計**：當 `buildSourceDocs()`（檔案掃描）回傳空且 `qaStore.count > 0` 時，
自動切換至 `buildSourceDocsFromStore()`，從 `qaStore.allItems` 按 `(source_collection, source_title, source_date)` group by 反推來源文件清單。`is_processed` 恆為 true、`size_bytes` 為 0。

#### tsup 雙重 Build 設定

```typescript
// api/tsup.config.ts
export default defineConfig([
  // Node.js server build（開發用，external node_modules）
  { entry: { index: "src/index.ts" }, outDir: "dist", ... },
  // Lambda build（self-contained ESM bundle，~3.4MB）
  {
    entry: { lambda: "src/lambda.ts" },
    outDir: "dist-lambda",
    noExternal: [/.*/],          // 所有 npm packages 打包進 bundle
    banner: {
      js: "import { createRequire as __cr } from 'node:module';"
        + "const require = __cr(import.meta.url);",  // CJS deps 需要 require
    },
  },
]);
```

**ESM 注意事項**：
- Lambda zip 內需含 `package.json` with `"type": "module"`，否則 `.js` 被當 CJS 載入
- `noExternal: [/.*/]` 將所有 npm 依賴打入 bundle → zip 只需 `lambda.js` + `package.json`
- CJS 依賴（如 `dotenv`）在 ESM bundle 中需要 `createRequire` shim 提供全域 `require`
- Banner 用 alias `__cr` 避免與 tsup 內部的 `createRequire` 衝突

#### Rate Limiter Lambda 處理

```typescript
// api/src/middleware/rate-limit.ts
const isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME || !!process.env.AWS_EXECUTION_ENV;
// Lambda 每個執行環境有獨立 Map → in-memory rate limit 無效
if (isLambda) { await next(); return; }
```

> Lambda 環境不做 in-memory rate limiting。需要限流時應使用 API Gateway throttling 或外部 store。

#### Dockerfile（Docker 本地開發 + 容器驗證用）

```dockerfile
# Stage 1: Build
FROM node:22-slim AS builder
RUN corepack enable pnpm
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY tsconfig.json tsup.config.ts ./
COPY src/ ./src/
RUN pnpm build

# Stage 2: Production
FROM node:22-slim AS runner
RUN corepack enable pnpm
WORKDIR /app
ENV NODE_ENV=production
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod
COPY --from=builder /app/dist ./dist
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 appuser
USER appuser
EXPOSE 8002
CMD ["node", "dist/index.js"]
```

> Dockerfile 保留給本地開發驗證。生產環境使用 Lambda（不需 Docker image）。

### 21.4 資料層遷移路徑

> **已完成 Phase 2**：資料層已遷移至 Supabase pgvector，Lambda 不需要檔案。
> 以下為歷史參考（Phase 1 過渡方案）。

| 方案                     | 複雜度 | 資料更新方式           | 適用階段     |
| ------------------------ | ------ | ---------------------- | ------------ |
| 打包進 Docker image      | 最低   | 重建 image             | Phase 1 過渡 |
| S3 啟動時下載            | 低     | 上傳 S3，重啟容器      | Phase 1      |
| **Supabase (pgvector)**  | **中** | **API 即時寫入**       | **Phase 2（v2.24 完成）** |

**Phase 2 Supabase 遷移計畫**：

```
Phase 1（當前）                     Phase 2（Supabase）
qa_enriched.json -> QAStore Map   ->  Supabase qa_items table
qa_embeddings.npy -> Float32Array ->  pgvector embedding column
store.search() -> dot product     ->  SELECT ... ORDER BY embedding <=> $1
store.load() -> 檔案讀取          ->  DB connection pool
```

**遷移邊界**：`api/src/store/qa-store.ts` 的 `QAStore` class 是唯一抽象層。
遷移時只需替換 `QAStore` 內部實作，所有 route 和業務邏輯零修改：

```typescript
// Phase 1: qa-store.ts（當前）
export class QAStore {
  load(): void { ... }                    // 從 JSON + npy 檔案載入
  search(queryVec, topK): SearchResult[]  // Float32Array dot product
  hybridSearch(query, vec, ...): ...      // semantic + keyword + synonym + freshness
}

// Phase 2: qa-store.ts（Supabase 版）
export class QAStore {
  load(): void { ... }                    // 建立 Supabase client connection
  search(queryVec, topK): SearchResult[]  // SELECT ... ORDER BY embedding <=> $1
  hybridSearch(query, vec, ...): ...      // pgvector + ts_rank 全文搜尋
}
```

**Supabase schema 預規劃**：

```sql
-- qa_items table（對應 qa_enriched.json 每筆 Q&A）
CREATE TABLE qa_items (
    id          TEXT PRIMARY KEY,           -- stable_id (16-char hex)
    seq         INT NOT NULL,              -- sequential number for display
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    category    TEXT,
    difficulty  TEXT,
    evergreen   BOOLEAN DEFAULT TRUE,
    source_title TEXT,
    source_date DATE,
    keywords    TEXT[],
    confidence  REAL,
    embedding   vector(1536),              -- pgvector
    synonyms    TEXT[],
    freshness_score REAL DEFAULT 1.0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 向量搜尋索引
CREATE INDEX ON qa_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- 全文搜尋索引（中文需搭配 pg_jieba 或 pgroonga）
CREATE INDEX ON qa_items USING gin (to_tsvector('simple', question || ' ' || answer));
```

### 21.5 Eval CI（Supabase Fallback）

`eval.yml` 在每次 push main 時自動執行兩個 Laminar eval：

| Eval | CI 行為 | 資料來源 |
|------|---------|---------|
| `eval_retrieval.py` | 正常執行 | 本地 `qa_final.json` → 無則 fallback Supabase REST API |
| `eval_extraction.py` | Graceful skip（exit 0） | 需要本地 `output/qa_per_meeting/`，CI 無此資料 |

**Retrieval eval Supabase fallback**（`evals/eval_retrieval.py`）：

```python
def _load_qa_items() -> list[dict]:
    # 1. Try local file
    if qa_final_path.exists():
        return json.loads(...)["qa_database"]
    # 2. Fallback to Supabase REST API
    resp = requests.get(f"{supabase_url}/rest/v1/qa_items?select=...",
                        headers={"apikey": anon_key, ...})
    return resp.json()
```

CI 環境需要 `SUPABASE_URL` + `SUPABASE_ANON_KEY` secrets。

### 21.6 GitHub Actions Secrets

| Secret                     | 用途                                         |
| -------------------------- | -------------------------------------------- |
| `AWS_ACCESS_KEY_ID`        | AWS IAM 認證（`seo-insight-deployer` user）  |
| `AWS_SECRET_ACCESS_KEY`    | AWS IAM 認證                                 |
| `LMNR_PROJECT_API_KEY`     | Laminar eval + tracing                       |
| `OPENAI_API_KEY`           | OpenAI API（RAG chat 需要）                  |
| `SEO_API_KEY`              | API 認證金鑰                                 |
| `SUPABASE_URL`             | Supabase REST API URL                        |
| `SUPABASE_ANON_KEY`        | Supabase anon key（RLS SELECT）              |

### 21.7 AWS 服務與 IAM 設定

**需要開通的 AWS 服務**：

| 服務           | 用途                  | 費用         |
| -------------- | --------------------- | ------------ |
| **Lambda**     | 無伺服器函式運行      | ~$0/月（free tier） |

**Lambda 函式設定**：
- Function: `seo-insight-api`
- Architecture: **arm64**（比 x86_64 便宜 20%）
- Runtime: Node.js 22
- Memory: 512 MB
- Timeout: 30 秒
- Handler: `lambda.handler`
- Function URL: 啟用（auth type: NONE）
- Region: ap-northeast-1

**IAM User -- `seo-insight-deployer`（GitHub Actions 用）**：
- `lambda:UpdateFunctionCode`
- `lambda:GetFunction`

> **注意**：Lambda 架構建立後不可更改。需更換架構時必須刪除函式後重建。

### 21.8 docker-compose 本地開發

```yaml
services:
  seo-api-ts:
    build:
      context: ./api
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    volumes:
      - ./output:/app/output:ro      # Q&A 資料 + embeddings（檔案模式）
      - ./scripts:/app/scripts:ro    # 週報生成腳本
    environment:
      - PORT=8002
      - CORS_ORIGINS=http://localhost:3000,http://localhost:3001
      - SEO_API_KEY=
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - SUPABASE_URL=${SUPABASE_URL:-}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-}
    restart: unless-stopped
```

**注意**：本地開發建議直接用 `cd api && pnpm dev`（tsx watch），比 Docker 更快且支援 hot reload。
Docker 主要用於驗證 production image 是否正常。生產環境使用 Lambda（不經 Docker）。

### 21.9 歷史：ECR + App Runner（已淘汰）

<details>
<summary>展開 App Runner 部署流程（已淘汰，v2.3--v2.23）</summary>

```
git push main → GitHub Actions → docker build → ECR push
    → aws apprunner update-service
    → App Runner 拉取新 image → 啟動容器 → health check → 切換流量
    → https://<random>.awsapprunner.com（自動 HTTPS）
```

App Runner 月費 ~$5-7，已於 2026-03-06 遷移至 Lambda + Function URL（~$0/月）。

</details>

### 21.10 歷史：ECR + EC2 SSM（已淘汰）

<details>
<summary>展開 EC2 SSM 部署流程（已淘汰，v0.3--v1.20）</summary>

```
git push main -> GitHub Actions -> docker build -> ECR push
    -> SSM send-command -> EC2 執行：
      docker pull $IMAGE:$TAG
      docker run -d -v /data/output:/app/output:ro ...
```

EC2 透過 volume mount 掛載資料檔，SSM 遠端執行部署命令。
此模式需要管理 EC2 主機（OS 更新、Docker 安裝、SSM Agent），
已於 2026-03-03 遷移至 App Runner。

</details>

---

## 22. API 安全：Auth + Rate Limit + Error Handler

> v2.3 以 Hono middleware 重新實作。功能與 FastAPI 版相同，語法和設計模式不同。

### OWASP API Security Top 10（2023）修復狀態

| API 風險                                             | 修復方式                                                        | 狀態      |
| ---------------------------------------------------- | --------------------------------------------------------------- | --------- |
| **API2:2023 -- Broken Authentication**               | `authMiddleware` + `X-API-Key` + `timingSafeEqual`              | OK |
| **API4:2023 -- Unrestricted Resource Consumption**   | `rateLimit()` sliding window：chat 20/min, default 60/min, generate 5/min | OK |
| **API3:2023 -- Broken Object Property Authorization** | `errorHandler` 全域攔截，不洩漏 stack trace                     | OK |
| **API1:2023 -- Broken Object Level Authorization**   | 所有 QA 資料公開（低風險，當前不需修復）                        | 可接受 |

### Auth Middleware（`api/src/middleware/auth.ts`）

```typescript
import { timingSafeEqual } from "node:crypto";

export function createAuthMiddleware(getApiKey: () => string) {
  return createMiddleware(async (c, next) => {
    const expected = getApiKey();
    if (!expected) {
      // 未設定 -> 開發模式放行，生產環境應設定
      console.warn("SEO_API_KEY is not set -- authentication DISABLED");
      await next();
      return;
    }
    const apiKey = c.req.header("X-API-Key") ?? "";
    if (!apiKey || !safeCompare(apiKey, expected)) {
      c.header("WWW-Authenticate", "ApiKey");
      return c.json(fail("Invalid or missing API key"), 401);
    }
    await next();
  });
}
```

**設計重點**：
- `timingSafeEqual`：防止 timing attack（與 Python 版的 `hmac.compare_digest` 對應）
- 開發模式（`SEO_API_KEY` 未設定）自動放行 + 警告
- 認證掛在 `/api/v1/*` 路由群組，`/health` 不需認證

### Rate Limit Middleware（`api/src/middleware/rate-limit.ts`）

```typescript
export function rateLimit(maxRequests: number, windowMs: number = 60_000) {
  return createMiddleware(async (c, next) => {
    const ip = c.req.header("x-forwarded-for")?.split(",")[0]?.trim()
            ?? c.req.header("x-real-ip")
            ?? "unknown";
    const key = `${ip}:${c.req.path}`;
    // Sliding window: 過濾 windowMs 內的 timestamps
    // 超過 maxRequests 回傳 429 + Retry-After header
  });
}
```

**設計重點**：
- **Sliding window**：比 fixed window 更精確，避免邊界突發
- **Per-IP per-path**：`/chat` 和 `/search` 獨立計算，互不影響
- **自動清理**：每 5 分鐘清除過期 entry，防止記憶體洩漏
- **Response headers**：`X-RateLimit-Limit`、`X-RateLimit-Remaining`、`Retry-After`

**速率表**：

| Endpoint                      | Limit         | 說明              |
| ----------------------------- | ------------- | ----------------- |
| `POST /api/v1/chat`           | 20/min per IP | 消耗 OpenAI token |
| `POST /api/v1/search`         | 60/min per IP | 語意搜索          |
| `GET /api/v1/qa/*`            | 60/min per IP | 列表查詢          |
| `POST /api/v1/feedback`       | 60/min per IP | 回饋              |
| `GET /api/v1/reports`         | 60/min per IP | 週報列表          |
| `POST /api/v1/reports/generate` | 5/min per IP  | 週報生成（重量級） |
| `GET /api/v1/sessions`        | 60/min per IP | 對話列表          |
| `POST /api/v1/sessions/*`     | 20/min per IP | 對話操作          |

命中限制時回傳 **429 Too Many Requests**（RFC 6585）。

### Error Handler（`api/src/middleware/error-handler.ts`）

```typescript
export const errorHandler: ErrorHandler = (err, c) => {
  console.error(`Unhandled error: ${err.message}`,
    err.stack?.split("\n").slice(0, 5).join("\n"));
  return c.json(fail("Internal server error"), 500);
};
```

- Server 端記錄完整 error stack（前 5 行）
- Client 只看到 `"Internal server error"`，不洩漏任何內部細節

### Response Envelope（`api/src/schemas/api-response.ts`）

```typescript
export interface ApiResponse<T> {
  readonly data: T | null;
  readonly error: string | null;
  readonly meta: { request_id: string; version: string };
}

export function ok<T>(data: T): ApiResponse<T> { ... }
export function fail(message: string): ApiResponse<null> { ... }
```

**回應格式**：

```json
{
  "data": { "items": [...], "total": 3 },
  "error": null,
  "meta": { "request_id": "550e8400-...", "version": "1.0" }
}
```

---

## 23. 環境變數（Zod 驗證）

> `api/src/config.ts` 使用 Zod schema 驗證所有環境變數，啟動時校驗失敗立即 `process.exit(1)`。

| 變數                    | 預設值                  | 用途                                         |
| ----------------------- | ---------------------- | -------------------------------------------- |
| `PORT`                  | `8002`                 | HTTP 監聽 port                               |
| `HOST`                  | `0.0.0.0`             | 監聽位址                                     |
| `OPENAI_API_KEY`        | （空字串）             | OpenAI API（search + chat 需要）             |
| `OPENAI_MODEL`          | `gpt-5.2`             | Chat completion 模型                         |
| `OPENAI_EMBEDDING_MODEL`| `text-embedding-3-small` | Embedding 模型                             |
| `SEO_API_KEY`           | （空字串）             | API Key 認證（空 = 開發模式，跳過驗證）      |
| `ANTHROPIC_API_KEY`     | （空字串）             | Reranker + Context Relevance（v2.11+，auto 模式偵測） |
| `CHAT_MODEL`            | `gpt-5.2`             | RAG Chat 問答模型（v2.22+，獨立於 OPENAI_MODEL）     |
| `CONTEXT_EMBEDDING_WEIGHT` | `0.6`               | Contextual embedding 加權（v2.11+）                   |
| `RERANKER_ENABLED`      | `auto`                 | Reranker 開關（auto/true/false，v2.11+）              |
| `CORS_ORIGINS`          | `http://localhost:3000` | CORS 白名單（逗號分隔）                     |
| `CHAT_CONTEXT_K`        | `5`                    | RAG 搜尋回傳 top-K 筆數                     |
| `RATE_LIMIT_DEFAULT`    | `60`                   | 預設速率限制（次/分鐘）                     |
| `RATE_LIMIT_CHAT`       | `20`                   | Chat 速率限制（次/分鐘）                    |
| `RATE_LIMIT_GENERATE`   | `5`                    | 週報生成速率限制（次/分鐘）                 |

### 資料路徑

```typescript
export const paths = {
  qaJsonPath:         "output/qa_final.json",
  qaEnrichedJsonPath: "output/qa_enriched.json",   // 優先載入
  qaEmbeddingsPath:   "output/qa_embeddings.npy",
  sessionsDir:        "output/sessions",
  accessLogsDir:      "output/access_logs",
};
```

QAStore 載入優先順序：`qa_enriched.json` > `qa_final.json`。
Enriched 版本含 synonyms + freshness_score，支援更精確的 hybrid search。

---

## 24. API 請求追蹤：Audit Trail

> 資料安全需求：確認哪些 QA 資料被哪些 IP 存取過。

### 設計原則

- **JSONL append-only**：每筆 event 一行 JSON，不修改歷史紀錄
- **Zero side-effects**：寫入失敗不影響 API 回應
- **按日期分檔**：`output/access_logs/access_2026-03-04.jsonl`

### Hono 取得 client IP

```typescript
// api/src/utils/audit-logger.ts
const ip = c.req.header("x-forwarded-for")?.split(",")[0]?.trim()
        ?? c.req.header("x-real-ip")
        ?? "unknown";
```

**注意**：Lambda Function URL 和 API Gateway 會設定 `X-Forwarded-For`，rate-limit middleware 和 audit logger 使用相同的 IP 取得邏輯。

### Log 格式（JSONL）

```json
{"event": "search", "query": "canonical URL 怎麼設定", "top_k": 5, "returned_ids": ["a1b2c3d4e5f67890"], "client_ip": "1.2.3.4", "ts": "..."}
{"event": "chat", "message": "什麼是 Core Web Vitals", "returned_ids": ["f0e1d2c3b4a59687"], "client_ip": "1.2.3.4", "ts": "..."}
```

> **注意**：v2.2+ 的 `returned_ids` 為 stable_id（16-char hex），不再是 sequential int。

---

## 25. Observability（v2.7 已實作）

> **v2.7 完成**：三路 Observability 整合（CLI + API + 執行日誌），使用 Laminar JS SDK。

### 實作內容

| 路徑 | 追蹤方式 | 模組 |
|------|---------|------|
| CLI 腳本（Python） | Laminar `@observe` + `init_laminar()` | `utils/observability.py` |
| Claude Code 指令 | `log_execution()` → JSONL | `utils/execution_log.py` |
| REST API（Hono） | `@lmnr-ai/lmnr@0.8.14` + `observe()` wrapper | `api/src/utils/observability.ts` |

### 追蹤的 span

| Span | 模組 | 說明 |
|------|------|------|
| `rag_chat` | `services/rag-chat.ts` | RAG 問答完整流程 |
| `get_embedding` | `services/embedding.ts` | OpenAI embedding 呼叫 |
| OpenAI API calls | auto-instrument | `instrumentModules: { OpenAI }` |

### Online Scoring（4 evaluators）

`api/src/utils/laminar-scoring.ts`：`answer_length` / `has_sources` / `top_source_score` / `source_count`

### 環境變數

`LMNR_PROJECT_API_KEY`：在 `.env` 設定，未設定則靜默跳過（不影響正常功能）。

---

## Legacy 區段

> 以下為 Python FastAPI + Laminar 等歷史實作，保留作為參考。Hono 版本可參考對照。

<details>
<summary>展開 Python FastAPI API 架構（v1.0--v2.2，port 8001）</summary>

### FastAPI lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()          # 載入 qa_final.json + qa_embeddings.npy
    yield                 # 服務存活期間資料保持在記憶體
    # 關閉時 GC 自動回收

app = FastAPI(lifespan=lifespan)
```

### numpy cosine similarity

```python
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
self.embeddings = embeddings / norms  # shape: (655, 1536)

def search(self, query_vec, top_k=5):
    scores = self.embeddings @ query_vec  # (655,)
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(self.items[i], float(scores[i])) for i in top_idx]
```

### 模組結構

```
app/
├── config.py          # 從環境變數讀設定
├── core/
│   ├── store.py       # QAStore singleton
│   ├── chat.py        # get_embedding() + rag_chat()
│   ├── session_store.py
│   ├── security.py    # verify_api_key（hmac.compare_digest）
│   ├── limiter.py     # slowapi rate limiter
│   └── schemas.py     # ApiResponse[T] envelope（Pydantic Generic）
├── routers/
│   ├── search.py
│   ├── chat.py
│   ├── qa.py
│   ├── feedback.py
│   ├── reports.py
│   └── sessions.py
└── main.py            # lifespan + CORS + include_router
```

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt
COPY app/ ./app/
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

</details>

<details>
<summary>展開 Laminar Observability 整合（Python FastAPI 專用）</summary>

### 最小化設定

```python
# app/main.py -- 在所有 import 完成後呼叫一次
import os
from lmnr import Laminar
Laminar.initialize(project_api_key=os.getenv("LMNR_PROJECT_API_KEY"))
```

初始化後，所有 `openai` SDK 呼叫自動被追蹤，不需要修改任何 router 程式碼。

### 相依性衝突修復

1. **語意慣例屬性缺失**（lmnr 0.5.2 + opentelemetry-semantic-conventions-ai 0.4.14）：
   手動補上 `LLM_SYSTEM`、`LLM_REQUEST_MODEL`、`LLM_RESPONSE_MODEL` 屬性。

2. **OpenAI Instrumentor 參數相容性**（lmnr 0.5.2 + opentelemetry-instrumentation-openai >= 0.44.0）：
   `_patch_openai_instrumentor()` 在 `Laminar.initialize()` 之前呼叫，移除不支援的 `enrich_token_usage` kwarg。

### @observe 裝飾器

```python
from lmnr import observe

@observe(name="step_name")
def my_step(input_data: str) -> dict:
    ...
```

### 環境變數

| 變數                   | 用途                            | 必要性                              |
| ---------------------- | ------------------------------- | ----------------------------------- |
| `LMNR_PROJECT_API_KEY` | Laminar tracing + evals         | 無此 key 時 silently skip，不 crash |

</details>

<details>
<summary>展開 Python FastAPI 安全實作（v1.11）</summary>

### API Key 認證（`app/core/security.py`）

```python
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    from app import config as app_config  # lazy import 防止 circular
    expected = app_config.API_KEY
    if not expected:
        logger.warning("SEO_API_KEY is not set -- authentication DISABLED")
        return ""
    if not api_key or api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return api_key
```

### Rate Limiting（`app/core/limiter.py`）

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
```

### Response Envelope（`app/core/schemas.py`）

```python
class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    meta: dict = Field(default_factory=dict)
```

</details>
