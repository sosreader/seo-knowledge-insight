# 後端 API 入門導讀

> 屬於 [research/](./README.md)。給沒碰過後端的人，從零理解本專案 API 架構的學習路線。

---

## 1. 先跑起來

```bash
cd api
pnpm install
pnpm dev          # 啟動後瀏覽 http://localhost:8002/health
```

看到 `{"status":"ok"}` 就成功了。接著試打 API：

```bash
# 不需要 API Key
curl http://localhost:8002/health

# 需要 API Key（從 .env 找 SEO_API_KEY）
curl -H "X-API-Key: YOUR_KEY" http://localhost:8002/api/v1/qa?limit=2
```

**目標**：建立「改程式碼 → 結果會變」的回饋迴圈。`pnpm dev` 使用 tsx watch，存檔即自動重啟。

---

## 2. 追一個請求的完整旅程

### 2.1 最簡單的路線：`/health`

只有 3 行邏輯，適合第一次看：

| 順序 | 檔案 | 看什麼 |
|------|------|--------|
| 1 | `src/index.ts` | 入口：middleware 怎麼串、route 怎麼掛 |
| 2 | `src/routes/health.ts` | 最簡單的 route（一個 GET，回傳 JSON） |
| 3 | `src/middleware/auth.ts` | 為什麼 health 不需要 API Key，其他需要 |

### 2.2 有資料的路線：`/api/v1/qa`

| 順序 | 檔案 | 看什麼 |
|------|------|--------|
| 1 | `src/routes/qa.ts` | Route 怎麼接參數、呼叫 store |
| 2 | `src/schemas/qa.ts` | Zod schema 怎麼驗證請求參數 |
| 3 | `src/store/qa-store.ts` | Factory pattern：怎麼決定用 Supabase 還是檔案 |
| 4 | `src/store/qa-filter.ts` | 過濾邏輯（純函式，好理解） |

**目標**：理解 `請求 → middleware → route → store → 回應` 這條主線。

### 2.3 Agent 路線：`POST /api/v1/chat`（agent mode）

LLM 自主決定呼叫哪些 tools、搜幾次、用什麼關鍵字——最複雜但也最有趣的路線。

| 順序 | 檔案 | 看什麼 |
|------|------|--------|
| 1 | `src/routes/chat.ts` | `resolveMode(requestMode)` 如何決定走 agent 還是 single-pass（三層：Request > Server > auto） |
| 2 | `src/agent/tool-definitions.ts` | 4 個 tool 的 Zod schema + OpenAI function calling 格式 |
| 3 | `src/agent/agent-loop.ts` | while-loop 核心：LLM 回傳 tool_calls → 執行 → 回傳結果 → 再問 LLM |
| 4 | `src/agent/tool-executor.ts` | Tool dispatch：怎麼根據 tool name 呼叫正確的函式 |
| 5 | `src/agent/agent-deps.ts` | DI 橋接：agent 怎麼透過 interface 存取 qaStore（不直接依賴） |
| 6 | `src/agent/types.ts` | 所有型別定義：AgentDeps、ToolResult、AgentResponse |

**目標**：理解 `route → resolveMode(requestMode) → agent-loop（while-loop → tool_calls → executor → tool results → LLM）→ 回應` 這條進階主線。v2.29 起前端可透過 `mode: "agent"|"rag"` 參數指定模式，不帶則走 server-level 預設。

**安全重點**：注意 `ALLOWED_TOOLS` whitelist、`JSON.parse` guard、error sanitization——這些都是因為 LLM 回傳的內容被當作「不可信輸入」處理。

---

## 3. 分層架構

```
middleware/    「門衛」— 每個請求都要過的關卡（認證、限流、安全標頭）
    |
routes/       「櫃台」— 接收請求、驗證參數、回傳結果
    |
agent/        「自主助手」— LLM 自主決定搜尋策略的 agent loop（v2.28）
    |
services/     「後台」— 複雜業務邏輯（RAG、LLM、報告生成）
    |
store/        「倉庫」— 讀寫資料（Supabase 或本地檔案）
    |
schemas/      「表格」— 定義資料長什麼樣子（Zod 驗證）
utils/        「工具箱」— 可重用的純函式
```

每一層只跟相鄰層溝通。Route 不直接碰 Supabase，Store 不知道 HTTP 狀態碼。Agent 層透過 `AgentDeps` interface 與 Store 溝通（DI 解耦）。

### 業界架構模式對照

本專案的分層設計並非自創，每一層都對應業界成熟的架構模式：

| 本專案層級 | 業界模式 | 出處 | 核心原則 |
|-----------|----------|------|----------|
| **middleware/** | **Chain of Responsibility** | GoF *Design Patterns* (1994) | 請求沿鏈傳遞，每個處理器決定處理或轉交下一個 |
| **routes/** | **Controller（MVC）** | Trygve Reenskaug, 1979; Fowler *PoEAA* (2002) | 接收 HTTP 請求、委派業務邏輯、格式化回應 |
| **agent/** | **Tool-Use Agent Loop** | FM AI Agents v2 (Scott Moss); OpenAI Function Calling (2023) | LLM 自主選擇 tool、多輪執行、自主終止；DI 解耦資料存取 |
| **services/** | **Service Layer** | Fowler *Patterns of Enterprise Application Architecture* (2002) | 定義應用邊界，協調業務操作，與傳輸機制無關 |
| **store/** | **Repository Pattern** | Evans *Domain-Driven Design* (2003) | 封裝資料存取邏輯，提供 collection-like 介面 |
| **schemas/** | **Data Transfer Object (DTO) + Validation** | Fowler *PoEAA*; Zod 為 TypeScript 執行期實現 | 在系統邊界驗證資料結構，防止髒資料進入內層 |
| **utils/** | **Utility Module / Pure Functions** | 函數式程式設計通則 | 無副作用、可測試、可重用的獨立函式 |

> **ECC 實踐參考**：ECC `backend-patterns` skill 提供了 Repository Pattern、Service Layer、Middleware、Error Handler、Rate Limiter 的 TypeScript 範例實作；`api-design` skill 涵蓋 RESTful 命名、HTTP 狀態碼語意、分頁策略、回應格式標準。本專案的實作與這兩份 skill 高度對齊。

#### 整體對應的架構風格

**1. Layered Architecture（N-Tier）**

最經典的企業架構模式。Mark Richards *Software Architecture Patterns* (O'Reilly, 2015) 定義四層：Presentation → Business → Persistence → Database。本專案的 routes → services → store 即為這三層的對應。

```
┌─────────────────────────────────────┐
│  Presentation    routes/ + schemas/ │  ← 接收請求、驗證、回應
├─────────────────────────────────────┤
│  Business Logic  services/          │  ← 業務規則、RAG、LLM
├─────────────────────────────────────┤
│  Persistence     store/             │  ← 資料存取（Supabase / File）
├─────────────────────────────────────┤
│  Database        Supabase / JSON    │  ← 實際儲存
└─────────────────────────────────────┘
  middleware/ 橫跨所有層（Cross-Cutting Concerns）
```

**關鍵約束**：每層只能呼叫下一層（Strict Layering），不可跨層。這是本專案「Route 不直接碰 Supabase」的理論基礎。

**2. Ports & Adapters（Hexagonal Architecture）**

Alistair Cockburn (2005) 提出。核心理念：業務邏輯不依賴外部技術，透過「port（介面）」與「adapter（實作）」解耦。

本專案的 Factory Pattern 就是這個模式的實踐：

```
              ┌──────────────────────┐
              │   services/          │
              │   （業務邏輯核心）     │
              └──────┬───────────────┘
                     │ Port（介面）
          ┌──────────┴──────────┐
          │                     │
   SupabaseQAStore         QAStore (File)
   （Adapter A）           （Adapter B）
```

`qa-store.ts` 的 `hasSupabase()` 在啟動時選擇 adapter，services 層完全不知道底層是 Supabase 還是檔案。

> **ECC 對照**：ECC `backend-patterns` 的 Repository Pattern 範例用 `interface MarketRepository` 定義 port，`SupabaseMarketRepository implements MarketRepository` 作為 adapter——與本專案的 `QAStore` / `SupabaseQAStore` 結構一致。進階版甚至展示了 `CachedMarketRepository`（decorator pattern）包裝 Redis 快取層。

**3. Middleware Pattern（Pipeline / Chain of Responsibility）**

Express.js 發揚光大，Hono 沿用。GoF *Design Patterns* (1994) 的 Chain of Responsibility：

```
Request → CORS → SecurityHeaders → Auth → RateLimit → RouteHandler → Response
```

每個 middleware 可以：(a) 處理後傳給下一個，(b) 直接回應（如 401、429），(c) 修改 context 後傳遞。

> **ECC 對照**：ECC `backend-patterns` 的 Middleware Pattern 和 Rate Limiter 範例展示了 `withAuth(handler)` HOF 包裝、sliding window 計數器；`api-design` 則定義了 Rate Limit 回應標頭規範（`X-RateLimit-Remaining`、`Retry-After`）。本專案的 `auth.ts`、`rate-limit.ts` 即為這些模式的 Hono 版實作。

**4. Clean Architecture（Robert C. Martin, 2012）**

Uncle Bob 的同心圓模型。依賴方向從外到內，內層不知道外層存在：

| Clean Architecture 層 | 本專案對應 | 依賴方向 |
|----------------------|-----------|---------|
| Frameworks & Drivers | `index.ts`, `lambda.ts`, Hono | → 向內 |
| Interface Adapters | `routes/`, `middleware/` | → 向內 |
| Application Business Rules | `services/` | → 向內 |
| Enterprise Business Rules | `schemas/`, `utils/` | 最內層 |

### 為什麼這樣分層有效

這些模式之所以成為業界標準，解決的是以下實際問題：

| 問題 | 解法 | 本專案實例 | ECC 參考 |
|------|------|-----------|----------|
| 換資料庫要改整個系統 | Repository Pattern 隔離 | Supabase ↔ File 切換不影響 routes/services | `backend-patterns` §Repository Pattern |
| 認證邏輯散落各處 | Middleware 集中處理 | `auth.ts` 一處修改，全部路由生效 | `backend-patterns` §Middleware Pattern |
| 業務邏輯混在 HTTP 處理中 | Service Layer 抽離 | `rag-chat.ts` 可獨立測試，不需要 HTTP | `backend-patterns` §Service Layer |
| 驗證邏輯重複 | Schema 集中定義 | Zod schema 在 route 入口統一驗證 | `api-design` §Implementation Patterns |
| 測試困難 | 分層 → 各層可獨立 mock | Store 層 mock 後可測試 service 純邏輯 | `backend-patterns` §Error Handling |
| API 不一致 | RESTful 設計規範 | `/api/v1/qa`、`/api/v1/reports` 統一風格 | `api-design` §Resource Design、§API Checklist |

### 延伸閱讀

**學術 / 書籍出處（按發表時間排序）：**

| 年份 | 出處 | 貢獻的模式 |
|------|------|-----------|
| 1979 | Trygve Reenskaug — MVC 論文 | Model-View-Controller 分離 |
| 1994 | GoF — *Design Patterns: Elements of Reusable OO Software* | Chain of Responsibility、Factory、Singleton |
| 2002 | Martin Fowler — *Patterns of Enterprise Application Architecture* | Service Layer、Repository、DTO、Unit of Work |
| 2003 | Eric Evans — *Domain-Driven Design* | Repository Pattern、Bounded Context、Ubiquitous Language |
| 2005 | Alistair Cockburn — Hexagonal Architecture | Ports & Adapters（內外層解耦） |
| 2012 | Robert C. Martin — *Clean Architecture* (blog → 2017 book) | 依賴反轉、同心圓分層 |
| 2015 | Mark Richards — *Software Architecture Patterns* (O'Reilly) | Layered Architecture 分類與 trade-off 分析 |

**ECC Skills（實作範例）：**

| Skill | 涵蓋內容 |
|-------|----------|
| `backend-patterns` | Repository / Service Layer / Middleware / Cache-Aside / Rate Limiter / Error Handler / Structured Logging |
| `api-design` | RESTful 命名 / HTTP 狀態碼 / 分頁（offset vs cursor）/ 過濾排序 / 版本策略 / API Checklist |
| `coding-standards` | 通用程式風格（命名、函式大小、錯誤處理、immutability） |

### 請求流程圖

```
Client → Function URL / localhost:8002
  → CORS → Security Headers
  → /health（直接回應，無 auth）
  → /api/v1/* → Auth → Rate Limit → Route Handler → Service → Store → Supabase / File
```

---

## 4. 目錄結構速查

```
api/src/
├── index.ts              # 應用入口 + 路由掛載 + initStores()
├── lambda.ts             # Lambda 入口（cold start + hono handler）
├── config.ts             # Zod 驗證環境變數 + 資料路徑
│
├── middleware/            # 4 層中介層
│   ├── cors.ts              CORS 白名單
│   ├── security-headers.ts  HTTP 安全標頭
│   ├── auth.ts              API Key 驗證（timingSafeEqual）
│   ├── rate-limit.ts        按路由差異化限流
│   └── error-handler.ts     全域錯誤處理
│
├── routes/               # 9 個路由器（掛在 /api/v1/ 下）
│   ├── health.ts            GET /health（無 auth）
│   ├── qa.ts                Q&A CRUD + 分類/collections
│   ├── search.ts            知識庫搜尋（hybrid search）
│   ├── chat.ts              RAG 問答
│   ├── reports.ts           週報 CRUD + 生成
│   ├── sessions.ts          Chat session 管理
│   ├── feedback.ts          使用者回饋
│   ├── pipeline.ts          Pipeline 操作（fetch/extract/dedupe/metrics）
│   ├── pipeline-fs.ts       Pipeline 檔案系統邏輯（source-docs 等）
│   └── synonyms.ts          同義詞 CRUD
│
├── services/             # 業務邏輯層
│   ├── rag-chat.ts          RAG 對話引擎
│   ├── embedding.ts         OpenAI embedding 服務
│   ├── reranker.ts          Reranker（Anthropic，實驗性）
│   ├── context-relevance.ts Context 相關性評分
│   ├── metrics-parser.ts    SEO 指標解析（純 TS）
│   ├── report-generator-local.ts  本地週報生成
│   ├── report-llm.ts        LLM 週報生成（純 TS）
│   ├── report-evaluator.ts  5 維度品質評估
│   └── pipeline-runner.ts   Pipeline 步驟執行器
│
├── store/                # 資料存取層（Factory Pattern）
│   ├── qa-store.ts              QAStore factory（Supabase vs 檔案）
│   ├── supabase-client.ts       Supabase REST client
│   ├── supabase-qa-store.ts     pgvector hybrid search
│   ├── supabase-report-store.ts
│   ├── supabase-snapshot-store.ts
│   ├── supabase-session-store.ts
│   ├── supabase-learning-store.ts
│   ├── supabase-synonyms-store.ts
│   ├── search-engine.ts        搜尋引擎核心（hybrid + keyword）
│   ├── qa-filter.ts            QA 過濾邏輯
│   ├── session-store.ts        檔案模式 fallback
│   ├── learning-store.ts       失敗記憶（JSONL fallback）
│   └── synonyms-store.ts       同義詞（雙層：靜態 + custom）
│
├── schemas/              # Zod 驗證 schema
│   ├── api-response.ts      統一回應格式
│   ├── qa.ts / search.ts / chat.ts / report.ts
│   ├── pipeline.ts / session.ts / feedback.ts
│   └── synonyms.ts
│
└── utils/                # 純函式工具
    ├── cosine-similarity.ts    Float32Array 矩陣運算
    ├── keyword-boost.ts        4 層關鍵字加權
    ├── cjk-tokenizer.ts        CJK 分詞 2-gram
    ├── npy-reader.ts           numpy 檔案讀取
    ├── sanitize.ts             HTML escape 防 XSS
    ├── audit-logger.ts         存取日誌
    ├── mode-detect.ts          hasOpenAI() / hasSupabase() / resolveMode()
    ├── observability.ts        Laminar tracing
    └── laminar-scoring.ts      Online scoring
```

---

## 5. 用測試當文件讀

測試是「活的規格書」，比讀 code 更快理解行為：

```bash
pnpm test tests/routes/health.test.ts      # 最簡單的 route
pnpm test tests/routes/qa.test.ts          # 有 filter 的 route
pnpm test tests/store/qa-filter.test.ts    # 純邏輯函式
```

測試會告訴你：
- 這個函式接受什麼參數
- 正常情況回傳什麼
- 邊界情況怎麼處理（空值、錯誤、無權限）

目前共 428 個測試（45 檔案），coverage 80%+。

---

## 6. 核心概念速查表

遇到不懂的再查，不用先全部學完：

| 概念 | 在哪裡用到 | 一句話解釋 |
|------|-----------|-----------|
| **Hono** | `index.ts` | 輕量 Web 框架，類似 Express 但更快更小 |
| **Middleware** | `middleware/` | 在 route 前執行的「攔截器」，處理認證、限流等共用邏輯 |
| **Zod** | `schemas/`, `config.ts` | 執行期型別驗證，確保資料格式正確 |
| **Factory Pattern** | `qa-store.ts` | 根據環境變數決定用哪個實作（Supabase vs 檔案） |
| **REST API** | `routes/` | 用 HTTP 動詞（GET/POST/PUT/DELETE）操作資源 |
| **Rate Limit** | `rate-limit.ts` | 限制每分鐘請求數，防止濫用 |
| **Singleton** | `initStores()` | 確保初始化只執行一次，Lambda cold start 和 server 共用 |
| **pgvector** | `supabase-qa-store.ts` | PostgreSQL 向量搜尋擴充，用於語意搜尋 |
| **Hybrid Search** | `search-engine.ts` | 結合向量語意搜尋 + 關鍵字搜尋的混合策略 |
| **RAG** | `rag-chat.ts` | Retrieval-Augmented Generation — 先檢索再生成回答 |

---

## 7. 建議閱讀順序

```
health.ts → qa.ts → search.ts → chat.ts
（最簡單）                       （最複雜）
```

從左到右，每個 route 多一點邏輯。等 `chat.ts` 看懂了，就能理解 RAG 問答的完整流程。其餘 route（reports、sessions、pipeline、synonyms）都是同樣的 pattern，差別在業務邏輯。

---

## 8. 雙模式設計

本專案有兩組「雙模式」設計，理解後能看懂很多 code 裡的分支邏輯：

### 8.1 執行環境：Node.js vs Lambda

| | Node.js Server | AWS Lambda |
|--|----------------|------------|
| 入口 | `index.ts` → `@hono/node-server` | `lambda.ts` → `hono/aws-lambda` |
| 啟動 | `pnpm dev` / `pnpm start` | AWS 自動管理 |
| Rate Limit | In-memory sliding window | 自動 bypass（每個實例獨立） |
| 初始化 | 啟動時 `await initStores()` | Cold start 時 `initStores()` |

### 8.2 資料層：Supabase vs 檔案

| | Supabase pgvector | 檔案模式 |
|--|-------------------|----------|
| 偵測 | `SUPABASE_URL` + `SUPABASE_ANON_KEY` 有設定 | 環境變數未設定 |
| 搜尋 | pgvector RPC hybrid search | In-memory cosine similarity |
| 資料來源 | PostgreSQL `qa_items` table | `output/qa_final.json` + `.npy` |
| 適用場景 | 生產環境、Lambda | 本地開發、無外部依賴 |

---

## 相關文件

- **API 端點清單**：[`api/README.md`](/api/README.md)
- **架構圖**：[`06b-architecture-diagram.md`](./06b-architecture-diagram.md)
- **架構決策與 Changelog**：[`06-project-architecture.md`](./06-project-architecture.md)、[`06a-architecture-changelog.md`](./06a-architecture-changelog.md)
- **部署指南**：[`07-deployment.md`](./07-deployment.md)
