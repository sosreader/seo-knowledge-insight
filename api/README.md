# Hono TypeScript API (v2.6)

REST API 伺服器，主要架構採用 Hono 框架。

**特點：**
- 9 個路由器（Routers）
- 30 個 API endpoints
- Rate limiting + API Key 認證
- Zod schema validation
- Local Mode graceful degradation（無 OpenAI 時自動降級）

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
pnpm build                   # 編譯 TypeScript 至 dist/
pnpm start                   # 執行 build 版本（node dist/index.js，port 8002）
```

---

## API 路由清單

### 1. 健康檢查 (health)

| 方法 | 路由 | 說明 |
|------|------|------|
| GET | `/health` | 伺服器健康檢查 |

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
| POST | `/api/v1/reports/generate` | 觸發週報生成（同步，120s timeout） | ✓ | 5/min |

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

### 8. Pipeline 管理 (pipeline) — 10 個 endpoints

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
| POST | `/api/v1/pipeline/metrics` | 取得 Pipeline metrics | ✓ | 60/min |

### 9. 評估工具 (eval) — 4 個 endpoints

| 方法 | 路由 | 說明 | 認證 | Rate Limit |
|------|------|------|------|-----------|
| POST | `/api/v1/eval/sample` | 隨機抽樣 Q&A（支援 seed + golden） | ✓ | 60/min |
| POST | `/api/v1/eval/retrieval` | Retrieval 評估指標（hit rate、MRR） | ✓ | 60/min |
| GET | `/api/v1/eval/compare` | 跨 Provider 品質對比 | ✓ | 60/min |
| POST | `/api/v1/eval/save` | 儲存評估結果 | ✓ | 60/min |

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

---

## 項目結構

```
api/
├── src/
│   ├── index.ts              # 入口點（middleware + route mount）
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
│   │   └── eval.ts           # v2.3 新增
│   ├── middleware/
│   │   ├── auth.ts           # API Key 驗證
│   │   ├── rate-limit.ts     # slowapi 速率限制
│   │   ├── cors.ts           # CORS 設定
│   │   └── error-handler.ts  # 錯誤處理
│   ├── store/
│   │   ├── qa-store.ts       # Q&A 資料 singleton
│   │   ├── search-engine.ts  # 搜尋引擎（hybrid + keyword）
│   │   ├── session-store.ts  # 對話歷史儲存
│   │   └── learning-store.ts # 失敗記憶（JSONL）
│   ├── services/
│   │   ├── embedding.ts      # OpenAI embedding 服務
│   │   ├── rag-chat.ts       # RAG 問答邏輯
│   │   └── pipeline-runner.ts # Python 腳本執行器
│   ├── schemas/              # Zod schemas
│   │   ├── api-response.ts   # 統一回應格式
│   │   ├── qa.ts
│   │   ├── search.ts
│   │   ├── chat.ts
│   │   ├── eval.ts           # v2.3 新增
│   │   └── ...
│   └── utils/
│       ├── npy-reader.ts     # numpy 檔案讀取
│       ├── cosine-similarity.ts
│       ├── cjk-tokenizer.ts  # v2.3 新增：CJK 分詞
│       ├── mode-detect.ts    # v2.3 新增：hasOpenAI() 檢測
│       └── ...
├── tests/
│   ├── routes/
│   │   ├── qa.test.ts
│   │   ├── search.test.ts
│   │   ├── chat.test.ts      # v2.3 新增
│   │   ├── eval.test.ts      # v2.3 新增
│   │   └── ...
│   └── utils/
│       ├── cjk-tokenizer.test.ts  # v2.3 新增
│       └── ...
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

# Optional
OPENAI_API_KEY=sk-...          # 若無，則 search/chat 自動降級
OPENAI_MODEL=gpt-5.2

# 資料路徑
QA_STORE_PATH=../output/qa_final.json
EMBEDDINGS_PATH=../output/qa_embeddings.npy
ENRICHED_PATH=../output/qa_enriched.json
```

---

## Local Mode（無 OpenAI 時的自動降級）

### Search 端點

**有 OpenAI：** Embedding + Cosine Similarity（語意搜尋）

**無 OpenAI：** Keyword-only 搜尋（CJK 分詞 + 關鍵字加權）

### Chat 端點

**有 OpenAI：** RAG Pipeline（檢索 → GPT 生成）

**無 OpenAI：** Context-only（僅回傳相關 Q&A，不生成回答）

### 切換機制

```typescript
// api/src/utils/mode-detect.ts
export function hasOpenAI(): boolean {
  return config.OPENAI_API_KEY.length > 0;
}
```

---

## 測試

所有路由都有完整的單元 + 整合測試：

```bash
pnpm test                      # 執行所有測試
pnpm test:watch               # 監視模式
pnpm test:coverage            # 覆蓋率（目標 ≥ 80%）

# 特定測試檔案
pnpm test api/tests/routes/eval.test.ts
pnpm test api/tests/utils/cjk-tokenizer.test.ts
```

**測試套件統計（v2.6）：**
- 總測試數：135 個
- 通過：135/135 (100%)
- 覆蓋率：80%+

---

## Docker 部署

整個系統可以透過 docker-compose 運行，包含 Python API（port 8001）和 TypeScript API（port 8002）：

```bash
docker-compose up              # 啟動所有服務
docker-compose logs seo-api-ts # 監看 Hono API 日誌
```

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

1. 確認 `qa_final.json` 和 `qa_embeddings.npy` 存在於 output/ 目錄
2. 若無 OpenAI Key，search 會自動降級至 keyword（可能會失準）
3. 檢查 config 中 `QA_STORE_PATH` 設定是否正確

---

## 相關文件

- **主架構**：[`/research/06-project-architecture.md`](/research/06-project-architecture.md)
- **架構圖**：[`/research/06b-architecture-diagram.md`](/research/06b-architecture-diagram.md)
- **部署指南**：[`/research/07-deployment.md`](/research/07-deployment.md)
- **專案說明**：[`/README.md`](/README.md)
- **全域指令**：[`/CLAUDE.md`](/CLAUDE.md)
