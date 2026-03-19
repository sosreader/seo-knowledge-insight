# SEO Q&A 知識庫建構 Pipeline

從 Notion 上累積兩年的 SEO 顧問會議紀錄與多來源文章中，自動萃取結構化的問答知識庫。目前收錄 **1,809 筆 Q&A**（8 個來源），提供 REST API、語意搜尋、RAG 問答與自動化品質評估。

---

## 功能總覽

### 1. 知識庫建構 Pipeline（步驟 1–3）

- **多來源擷取** — Notion 增量擷取 + Medium RSS + iThome HTML + Google Case Studies + Ahrefs + SEJ + Growth Memo
- **AI 自動萃取** — 用 `gpt-5.2` 將 Markdown 解析為結構化 Q&A（What/Why/How/Evidence）
- **Collection-Scoped 去重合併** — 各 collection 內部獨立去重，跨 collection 保留
- **智能分類標籤** — 12 個分類 × 難度 × 時效性，雙層 metadata（source_type + source_collection）

### 2. 每週 SEO 週報生成（步驟 4）

- **四層生成模式** — template / hybrid / openai / claude-code
- **ECC 7 維度報告** — 情勢快照、流量信號、技術 SEO、搜尋意圖、優先行動、AI 可見度、知識庫引用
- **異常值偵測** — 月趨勢 ±15% 或週趨勢 ±20% 自動標記

> 操作細節見 [research/15-pipeline-operations.md](research/15-pipeline-operations.md)

### 3. Q&A 品質評估（步驟 5）

- **五維度 LLM-as-Judge** — Relevance、Accuracy、Completeness、Granularity、Faithfulness
- **Retrieval 品質指標** — Hit Rate、MRR、Precision@K、Recall@K
- **13 個 Laminar Eval Groups** — CI 自動化監控

> 評估維度詳見 [research/03-evaluation.md](research/03-evaluation.md)
> 操作細節見 [research/15-pipeline-operations.md](research/15-pipeline-operations.md)

### 4. REST API 服務（Hono + TypeScript）

- **語意搜尋** — hybrid search（有 OpenAI）/ keyword search（自動降級）
- **RAG 問答** — Agent mode / Full RAG / Context-only 三模式 + SSE streaming
- **42 個端點** — 10 routers：qa / search / chat / reports / sessions / feedback / pipeline / synonyms / meeting-prep / health

> 完整端點文件見 [api/README.md](api/README.md) 或啟動 `pnpm dev` 後存取 [`/docs`](http://localhost:8002/docs)

### 5. Claude Code 模式（不需要 OpenAI API Key）

- **`/search`** — 知識庫語意搜尋
- **`/chat`** / **`/chat-agent`** — 互動式 RAG 問答（Agentic 多輪自主搜尋）
- **`/generate-report`** — SEO 週報生成
- **`/pipeline-local`** — 完整 Pipeline Steps 1–4
- **`/evaluate-provider`** — LLM Provider SEO 洞察評估

### 6. Laminar 離線評估

- **CI 自動化** — 每次 push main 自動執行 retrieval + extraction eval
- **Meeting-Prep 三層評估** — L1 結構 / L2 grounding / L3 LLM-as-Judge

> RAG 迭代改進詳見 [research/02-rag-and-search.md](research/02-rag-and-search.md)

---

## 快速開始

### 1. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 2. 建立 Notion Integration

1. 前往 https://www.notion.so/my-integrations
2. 點「New integration」，Capabilities 只需勾 **Read content**
3. 複製 **Internal Integration Secret**（以 `ntn_` 開頭）

### 3. 分享頁面給 Integration

1. 打開 SEO 會議紀錄的**母頁面**
2. 點 `···` → `Connections` → 找到 Integration → 確認
3. 複製母頁面的 **Page ID**（URL 最後 32 字元的 hex）

### 4. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入：

```env
NOTION_TOKEN=ntn_你的token
NOTION_PARENT_PAGE_ID=你的母頁面ID
OPENAI_API_KEY=sk-你的key
OPENAI_MODEL=gpt-5.2
ANTHROPIC_API_KEY=sk-ant-你的key  # 可選：用於 Reranker
LMNR_PROJECT_API_KEY=your-laminar-key  # 可選：用於 Observability
```

---

## 使用方式

### 一鍵執行完整流程

```bash
python scripts/run_pipeline.py
```

### 分步執行

```bash
python scripts/01_fetch_notion.py            # 步驟 1：Notion 擷取（增量）
python scripts/02_extract_qa.py --limit 3    # 步驟 2：Q&A 萃取（先試 3 份）
python scripts/03_dedupe_classify.py          # 步驟 3：去重 + 分類
python scripts/04_generate_report.py          # 步驟 4：週報生成
python scripts/05_evaluate.py                 # 步驟 5：品質評估
```

### 驗證設定（不執行）

```bash
python scripts/run_pipeline.py --dry-run
```

> 完整 CLI 選項與 Claude Code 指令見 [CLAUDE.md](CLAUDE.md)

---

## 指令速查

### Pipeline 建構

| 功能                   | CLI 腳本               | Claude Code 指令          | REST API                                |
| ---------------------- | ---------------------- | ------------------------- | --------------------------------------- |
| Step 1a — Notion 擷取  | `make fetch-notion`    | 由 `/pipeline-local` 整合 | `POST /api/v1/pipeline/fetch`           |
| Step 1b-d — 文章擷取   | `make fetch-articles`  | 由 `/pipeline-local` 整合 | `POST /api/v1/pipeline/fetch-articles`  |
| Step 2 — Q&A 萃取      | `make extract-qa`      | `/extract-qa`             | `POST /api/v1/pipeline/extract-qa`      |
| Step 3 — 去重 + 分類   | `make dedupe-classify` | `/dedupe-classify`        | `POST /api/v1/pipeline/dedupe-classify` |
| Step 4 — 週報生成      | `make generate-report` | `/generate-report <URL>`  | `POST /api/v1/reports/generate`         |
| Step 5 — 品質評估      | `make evaluate-qa`     | `/evaluate-qa-local`      | —                                       |
| Steps 1–4 — 知識庫建構 | `make pipeline`        | `/pipeline-local`         | —                                       |

### 搜尋與問答

| 功能             | CLI 腳本                                          | Claude Code 指令 | REST API              |
| ---------------- | ------------------------------------------------- | ---------------- | --------------------- |
| 知識庫搜尋       | `python scripts/qa_tools.py search --query "..."` | `/search <問題>` | `POST /api/v1/search` |
| RAG 問答         | —                                                 | `/chat`          | `POST /api/v1/chat`   |
| Agentic RAG 問答 | —                                                 | `/chat-agent`    | `POST /api/v1/chat`   |

### 資料查詢

| 功能          | REST API                     |
| ------------- | ---------------------------- |
| Q&A 列表查詢  | `GET /api/v1/qa`             |
| 單筆 Q&A 詳情 | `GET /api/v1/qa/{id}`        |
| 所有分類      | `GET /api/v1/qa/categories`  |
| 資料集列表    | `GET /api/v1/qa/collections` |
| 週報列表      | `GET /api/v1/reports`        |

> 離線評估工具見 [research/03-evaluation.md](research/03-evaluation.md)
> Pipeline 監控端點見 [CLAUDE.md](CLAUDE.md)

---

## 架構概覽

```
Notion/Medium/iThome/Google Cases/Ahrefs/SEJ/Growth Memo
  → Markdown 轉換 → AI 萃取 Q&A → Collection-Scoped 去重合併 → 分類標籤 → 最終資料庫
```

> 完整目錄樹見 [research/06-project-architecture.md](research/06-project-architecture.md)
> 架構圖見 [research/06b-architecture-diagram.md](research/06b-architecture-diagram.md)
> Data Schema 見 [research/16-data-schema.md](research/16-data-schema.md)

---

## REST API

TypeScript Hono（port 8002），42 個端點、734 tests、80%+ coverage。

```bash
cd api && pnpm install && pnpm dev   # 啟動開發伺服器
```

- [`/docs`](http://localhost:8002/docs) — Scalar 互動式文件
- [`/openapi.json`](http://localhost:8002/openapi.json) — OpenAPI 3.1 規格
- [GitHub Pages 文件](https://sosreader.github.io/seo-knowledge-insight/) — Scalar 線上託管文件（Art Deco theme，雙語 zh-TW + EN）

> 完整端點清單、安全機制、部署架構見 [api/README.md](api/README.md)

---

## 模型使用政策

**一律使用 GPT-5 系列模型，禁止 GPT-4 系列。**

| 用途      | 模型                     |
| --------- | ------------------------ |
| Q&A 萃取  | `gpt-5.2`                |
| 分類標籤  | `gpt-5-mini`             |
| 週報生成  | `gpt-5.2`                |
| Embedding | `text-embedding-3-small` |

> 完整模型政策見 [research/05-models.md](research/05-models.md)

---

## 文件導覽

| 文件                                                                             | 說明                                         |
| -------------------------------------------------------------------------------- | -------------------------------------------- |
| [CLAUDE.md](CLAUDE.md)                                                           | Claude Code 指令速查、Pipeline CLI、API 啟動 |
| [api/README.md](api/README.md)                                                   | REST API 完整端點、安全機制、部署架構        |
| [research/02-rag-and-search.md](research/02-rag-and-search.md)                   | RAG 迭代改進（Phase 2–4）、評估基準線        |
| [research/03-evaluation.md](research/03-evaluation.md)                           | 評估維度、Laminar Eval Groups、離線評估      |
| [research/05-models.md](research/05-models.md)                                   | 模型選擇決策、Embedding 比較                 |
| [research/06-project-architecture.md](research/06-project-architecture.md)       | 架構決策、目錄樹                             |
| [research/06a-architecture-changelog.md](research/06a-architecture-changelog.md) | 架構變更紀錄                                 |
| [research/06b-architecture-diagram.md](research/06b-architecture-diagram.md)     | Mermaid 架構圖、工作流程圖                   |
| [research/06c-backend-onboarding.md](research/06c-backend-onboarding.md)         | 後端入門、Troubleshooting、開發指南          |
| [research/07-deployment.md](research/07-deployment.md)                           | Lambda 部署、Supabase 遷移                   |
| [research/15-pipeline-operations.md](research/15-pipeline-operations.md)         | Pipeline 操作手冊、成本估算                  |
| [research/16-data-schema.md](research/16-data-schema.md)                         | 資料結構（5 種 JSON 格式 + 分類標籤）        |
| [research/README.md](research/README.md)                                         | Research 知識庫索引                          |

---

## 開發指南

```bash
# 1. Clone + 設定
cd seo-knowledge-insight
cp .env.example .env && pip install -r requirements.txt

# 2. 驗證
python scripts/run_pipeline.py --dry-run

# 3. Pipeline
make pipeline          # 完整流程（需要 OpenAI）
make extract-qa-test   # 小量驗證（--limit 3）

# 4. API 開發
cd api && pnpm install && pnpm dev    # port 8002
pnpm test                              # 734 tests

# 5. 部署
git push origin main   # 自動觸發 GitHub Actions → Lambda
```

> 完整開發指南見 [research/06c-backend-onboarding.md](research/06c-backend-onboarding.md)
