# CLAUDE.md

> 專案架構、指令、模型政策等深度參考：`.claude/skills/seo-qa-pipeline.md`

---

## Critical Rules

### 1. Code Organization

- Many small files over few large files（高內聚、低耦合）
- 每支腳本典型 200–400 行，上限 800 行
- 依功能/領域組織，而非依類型（scripts/ 為 pipeline 步驟，utils/ 為共用模組）

### 2. Code Style

- 不在 production code 留 `print()` 除錯語句，改用 `logging`
- Immutability：函式回傳新物件，不直接修改傳入的 list/dict
- 所有對外輸入（API response、檔案內容）皆需驗證，失敗應拋出有意義的例外
- 使用 `try/except` 明確捕捉，不吞掉例外（禁止 `except: pass`）

### 3. Testing

- TDD：先寫測試，再實作
- 最低覆蓋率 80%
- 單元測試：utils/ 純邏輯函式
- 整合測試：OpenAI / Notion API 呼叫（用 mock）
- E2E 測試：完整 pipeline 步驟（`--limit 3` 小量驗證）

### 4. Security

- 禁止 hardcode 任何 secret（API key、token）
- 所有敏感設定從 `.env` 讀取，參考 `.env.example`
- 寫入檔案前驗證路徑，防止 path traversal
- LLM 回傳內容當作不可信輸入，必須驗證 schema 後才使用

---

## Key Patterns

### LLM 回傳驗證

```python
# 推理模型（o 系列）content 可能為空，必須防守
result = response.choices[0].message.content
if not result or not result.strip():
    # 記錄並跳過，不 inflate denominator
    continue
data = json.loads(result)
```

### Pipeline 函式回傳格式

```python
# 統一回傳 dict，方便串接與測試
def process_step(input_data) -> dict:
    try:
        result = _do_work(input_data)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Step failed: %s", e)
        return {"success": False, "error": str(e)}
```

---

## Pipeline — 直接執行（CLI）

AI 工具（GitHub Copilot / Claude Code）可透過以下方式直接執行 pipeline，**不需要啟動 API 伺服器**。

### 快速入口

```bash
make pipeline          # Notion-core 流程 step 1→2→3
make fetch-notion      # 只執行 Notion 擷取
make extract-qa        # 只執行 Q&A 萃取
make dedupe-classify   # 只執行去重 + 分類
make generate-report   # 只執行週報生成
make evaluate-qa       # 品質評估（呼叫 _eval_laminar.py，推送至 Laminar Dashboard）
make dry-run           # 驗證設定（不執行）
make test              # 執行測試
make fetch-medium      # 只執行 Medium 文章擷取（RSS → Markdown）
make fetch-ithelp      # 只執行 iThome 鐵人賽擷取（HTML → Markdown）
make fetch-google-cases # 只執行 Google Case Studies 擷取（HTML → Markdown）
make fetch-ahrefs      # 只執行 Ahrefs Blog 擷取（WP API → Markdown，L4 分類篩選）
make fetch-sej         # 只執行 Search Engine Journal 擷取（RSS → Markdown）
make fetch-growthmemo  # 只執行 Growth Memo 擷取（Substack RSS → Markdown）
make fetch-google-blog # 只執行 Google Search Central Blog 擷取（Atom → Markdown）
make fetch-webdev      # 只執行 Web.dev 擷取（CWV/Performance 技術文章，RSS → Markdown）
make fetch-screaming-frog # 只執行 Screaming Frog Blog 擷取（技術 SEO 深度文章，RSS → Markdown）
make fetch-articles    # 擷取所有外部文章（9 個來源：Medium + iThome + Google Cases + Ahrefs + SEJ + Growth Memo + Google Blog + Web.dev + Screaming Frog）
make fetch-all         # Notion + 所有外部文章
make backfill-extraction-model      # 回填 extraction_model（全量 Supabase UPDATE）
make backfill-extraction-model-dry  # 回填 extraction_model（dry-run，不寫入）
make backfill-extraction-model-verify # 驗證回填結果（NULL count = 0）
make update-freshness               # 套用 freshness_score 衰減
make update-freshness-dry            # freshness_score 衰減（dry-run）
make update-freshness-verify         # 驗證 freshness_score 結果
make evaluate-retrieval-by-model MODEL=claude-code  # 按模型分群 eval
make meeting-prep-articles          # 列出顧問文章清單（去重）
make meeting-prep-topics            # 最近 3 份會議的主題詞
make evaluate-meeting-prep          # Meeting-Prep 快速評估（L1+L2）
make evaluate-meeting-prep-structure  # Meeting-Prep 結構品質評估
make evaluate-meeting-prep-grounding  # Meeting-Prep 引用根基評估
make evaluate-meeting-prep-llm       # Meeting-Prep L3 LLM threshold gate（需先跑 /evaluate-meeting-prep-quality）
make evaluate-meeting-prep-web       # Meeting-Prep L4 S2 時效性驗證
make evaluate-meeting-prep-full      # Meeting-Prep 完整 4 層（L1+L2+L3+L4）
make evaluate-report REPORT=output/report_XXXXXXXX.md  # 週報品質評估 L1+L2（rule-based）
make autoresearch-baseline  # AutoResearch baseline eval（需先啟動 API server）
make help              # 顯示所有可用 targets
```

### 直接呼叫 Python

```bash
.venv/bin/python scripts/run_pipeline.py                        # Notion-core 流程
.venv/bin/python scripts/run_pipeline.py --step extract-qa --limit 3    # 測試用
.venv/bin/python scripts/run_pipeline.py --dry-run             # 只驗證設定
```

### GitHub Copilot（VS Code Tasks）

使用 `Ctrl+Shift+P` → "Tasks: Run Task" → 選擇對應的 Pipeline task。

### Claude Code Slash Command

```
/run-pipeline          # 查看完整用法說明（需要 OpenAI API key）
/pipeline-local        # Notion-core pipeline（外部文章需先 make fetch-articles）
/extract-qa            # 只執行 Step 2 Q&A 萃取（不需要 OpenAI）
/dedupe-classify       # 只執行 Step 3 去重+分類（不需要 OpenAI）
```

### 不需要 OpenAI API Key 的流程

Claude Code / GitHub Copilot 本身作為 LLM 引擎，直接讀取 Markdown 萃取 Q&A：

```bash
make status            # 查看目前 pipeline 狀態
make list-unprocessed  # 列出待萃取的 Markdown 檔案
# （然後在 Claude Code 執行 /extract-qa）
make merge-qa          # AI 萃取完成後合併 JSON
# （然後在 Claude Code 執行 /dedupe-classify）
```

### 前置條件

確認 `.env` 已設定（參考 `.env.example`）：

```bash
make dry-run   # 輸出 ✅ 設定檢查通過 才可繼續
```

> **首次接入 OPENAI_API_KEY 注意**：現有 QA 由 Claude Code 模式生成（未走 openai_helper cache）。
> 首次執行 `make extract-qa` 會重新萃取全部文件，請先 `make cache-stats` 確認 cache 狀態。
> 若 cache 為空，建議從 `--limit 3` 小量驗證開始：`make extract-qa-test`。

---

## Available Claude Commands

### Pipeline 命令（需要 OpenAI API key）

- `/run-pipeline` — 執行完整 pipeline（Steps 1–5，使用 OpenAI）

### Claude Code 模式命令（多數流程不需要 OpenAI API key）

- `/pipeline-local` — Notion-core pipeline Steps 1–3（外部文章需先 `make fetch-articles`，你是 LLM 引擎）
- `/extract-qa` — 只執行 Step 2 Q&A 萃取（parallel sub-agents）
- `/dedupe-classify` — 只執行 Step 3 去重 + 分類
- `/generate-report <URL 或路徑>` — 生成 SEO 週報（對齊 `scripts/04_generate_report.py`，需要 `OPENAI_API_KEY`；支援 `--snapshot <snapshot_id>`）
- `/meeting-prep <snapshot 路徑 或 --report 週報路徑>` — 顧問會議準備深度研究報告（11 sections：異常地圖/業界動態/根因假設/交叉比對/審計缺口/E-E-A-T/人本要素/成熟度/提問清單/行動核查）
- `/search <問題>` — 搜尋知識庫（關鍵字加權，回傳 top-K Q&A）
- `/chat` — 互動式 RAG 問答（每輪自動搜尋知識庫）
- `/chat-agent` — Agentic RAG 問答（多輪自主搜尋，混合 Grep/Read/qa_tools.py，不需要 OpenAI）
- `/evaluate-qa-local` — Q&A 品質評估（Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-provider <目錄路徑>` — 評估通用 LLM Provider 的 SEO 洞察品質（Claude Code 作為 Judge）
- `/evaluate-faithfulness-local` — RAGAS Faithfulness 評估（Answer 是否有幻覺，Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-context-precision-local` — RAGAS Context Precision 評估（Retrieved contexts 有多少真正相關，Claude Code 作為 Judge）
- `/evaluate-crawled-not-indexed-local` — 檢索未索引分析品質評估（12 golden cases，rule-based）
- `/evaluate-meeting-prep-quality` — Meeting-Prep 內容品質評估（6 維度，Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-report-quality` — SEO 週報內容品質 L3 評估（3 維度：推理深度/可操作性/洞察原創性，Claude Code 作為 Judge，不需要 OpenAI）
- `/sync-db` — 本地 Reports + Sessions + Meeting-Prep 上傳至 Supabase（`make sync-db` / `make sync-db-status` / `make sync-db-force`；支援 `--type reports|sessions|meeting-prep|all`）
- `/backfill-extraction-model` — 追溯回填 Supabase qa_items 的 extraction_model（`--dry-run` / `--execute`）
- `/update-freshness` — 批次更新 freshness_score 指數衰減（`--dry-run` / `--execute`）
- `/evaluate-retrieval-by-model` — 按 extraction_model 分群評估檢索品質
- `/seo-frontend-hotfix` — 從 meeting-prep / weekly report 萃取「前端工程可實作」建議，先驗證 2026 最佳實踐再去 `~/Documents/vocus-web-ui` 修一版 hotfix + 發 PR（含駁回項回頭修正 source 報告，避免誤導累積）

### 評估命令（需要 OpenAI API key）

- `/evaluate-qa` — Q&A 品質評估（LLM-as-Judge）+ 與基準線比較（本地替代：`/evaluate-qa-local`）

### API 伺服器命令

#### TypeScript Hono（v2.12+，port 8002）——當前主架構

開發環境（後端 API）：

```bash
cd api
pnpm install           # 首次安裝依賴
pnpm dev               # 啟動開發伺服器（tsx watch，port 8002）
```

前端開發環境（vocus-web-ui）：

```bash
cd ../vocus-web-ui
git checkout main  # feat/admin-seo-insight 已 merge，從主線開新分支
pnpm install
pnpm dev               # 啟動前端伺服器（http://localhost:3000）
```

測試（838 個測試，80% 覆蓋率）：

```bash
cd api
pnpm test              # 執行所有 vitest 測試（838 tests, 67 files）
pnpm test:watch       # 監視模式下執行測試
pnpm test:coverage    # 生成測試覆蓋率報告
```

打包 / 部署：

```bash
cd api
pnpm build             # 編譯 TypeScript 至 dist/（server）+ dist-lambda/（Lambda）
pnpm start             # 執行 build 版本（node dist/index.js，port 8002）
```

Lambda 部署（arm64，~$0/月）：

```bash
cd api && pnpm build
cd dist-lambda && echo '{"type":"module"}' > package.json
zip -j ../lambda.zip lambda.js package.json
aws lambda update-function-code --function-name seo-insight-api \
  --zip-file fileb://../lambda.zip --region ap-northeast-1 --profile seo-deployer
```

Docker 執行（本地驗證用）：

```bash
docker-compose up      # 啟動 TypeScript (8002) API
docker-compose logs seo-api-ts  # 監看 Hono 日誌
```

API 端點特性：

- `GET /health` — 健康檢查（含 `capabilities` 物件：5 維度 runtime/llm/store/agent/caller；llm 為有效 LLM——Claude Code 呼叫且 server 無 OpenAI key 時回傳 `"claude-code"`，有 OpenAI key 回傳 `"openai"`，其餘 `"none"`）
- `GET /openapi.json` — OpenAPI 3.1 規格（機器可讀，可匯入 Postman / Swagger）
- `GET /docs` — Scalar 互動式 API 文件（瀏覽器直接測試）
- GitHub Pages 文件：[sosreader.github.io/seo-knowledge-insight](https://sosreader.github.io/seo-knowledge-insight/)（Scalar CDN + Art Deco theme + Tailwind v4，雙語 zh-TW + EN，CI auto-deploy from `api/src/openapi.ts`）
- 文件站結構：`docs-site/`（`index.html` Scalar API Reference + `style.css` + `guides/*.html` 5 頁雙語）
- OpenAPI spec 匯出：`pnpm docs:export` → `api/scripts/export-openapi.ts`（CI 產生，不 commit `docs-site/openapi.json`）
- 10 個路由器：qa（含 extraction_model filter）、search（含 extraction_model filter + search_hit_count tracking）、chat、reports、sessions、feedback、pipeline、synonyms、meeting-prep、health
- Pipeline 端點：18 個（狀態、會議、來源文件、指標、快照、趨勢分析、LLM 用量、索引覆蓋率等）
- 認證：`X-API-Key` header + 安全層（SSRF whitelist、auth fail-fast、HTTP security headers、session UUID validation）
- 詳見 `api/README.md`

QA API 端點（v2.6 多來源擴充）：

- `GET /api/v1/qa` — 列表查詢（支援 source_type、source_collection、category、difficulty、evergreen、keyword 等 filter）
- `GET /api/v1/qa/categories` — 所有分類
- `GET /api/v1/qa/collections` — 所有 collection 清單（含 source_type + count）
- `GET /api/v1/qa/{id}` — 單筆 Q&A（hex stable_id 或 integer seq）

Reports API 端點：

- `GET /api/v1/reports` — 列出所有週報
- `GET /api/v1/reports/{date}` — 取得單篇週報內容（YYYYMMDD 格式）
- `POST /api/v1/reports/generate` — 生成週報（支援三種模式）
  - 本地模式：`snapshot_id` 參數指定已儲存的指標快照（無需 OpenAI API key）
  - OpenAI 模式：`snapshot_id` + `use_openai` 參數（需 OpenAI API key，純 TypeScript `report-llm.ts`）
  - Legacy OpenAI 模式：`metrics_url` 參數指定 Google Sheets URL + `weeks` 參數（需 OpenAI API key）

Pipeline API 端點：

- `GET /api/v1/pipeline/status` — 各步驟完成狀態（12 步驟：fetch-notion + 9 個外部來源 + extract-qa + dedupe-classify）
- `GET /api/v1/pipeline/meetings` — 會議列表（含 metadata）
- `GET /api/v1/pipeline/meetings/:id/preview` — Markdown 預覽
- `GET /api/v1/pipeline/source-docs` — 列出所有來源文件（支援 source_type、source_collection、keyword、is_processed 等 filter + pagination）
- `GET /api/v1/pipeline/source-docs/:collection/:file/preview` — 來源文件預覽（會議/文章均支援）
- `GET /api/v1/pipeline/unprocessed` — 待處理的 Markdown 列表（含 source_collection）
- `GET /api/v1/pipeline/logs` — Fetch 歷史日誌
- `POST /api/v1/pipeline/fetch` — 觸發 Notion 增量擷取（不暴露 --force）
- `POST /api/v1/pipeline/fetch-articles` — 觸發外部文章擷取（9 來源：Medium + iThome + Google Cases + Ahrefs + SEJ + Growth Memo + Google Blog + Web.dev + Screaming Frog）
- `POST /api/v1/pipeline/extract-qa` — 觸發 Q&A 萃取
- `POST /api/v1/pipeline/dedupe-classify` — 觸發去重 + 分類
- `POST /api/v1/pipeline/metrics` — 取得 Pipeline metrics（解析 SEO 指標）
- `POST /api/v1/pipeline/metrics/save` — 儲存指標快照（支援 source、tab、label、weeks metadata）
- `GET /api/v1/pipeline/metrics/snapshots` — 列出指標快照清單（含 metadata）
- `DELETE /api/v1/pipeline/metrics/snapshots/:id` — 刪除指定快照
- `GET /api/v1/pipeline/metrics/trends` — Timeseries 異常偵測（MA deviation / consecutive decline / linear trend）
- `GET /api/v1/pipeline/llm-usage` — LLM cost/latency monitoring
- `POST /api/v1/pipeline/crawled-not-indexed` — 檢索未索引路徑分段分析（支援 `source` URL 模式和 `raw_tsv` 直接輸入模式）

Synonyms API 端點（v2.11 新增）：

- `GET /api/v1/synonyms` — 列出所有同義詞（靜態 + 自訂，含 source 標記）
- `POST /api/v1/synonyms` — 新增自訂同義詞
- `PUT /api/v1/synonyms/:term` — 更新自訂同義詞
- `DELETE /api/v1/synonyms/:term` — 刪除自訂同義詞

Meeting Prep API 端點（v3.3 新增 maturity-trend）：

- `GET /api/v1/meeting-prep` — 列出所有會議準備報告（日期 + meta）；Supabase 模式直查 `meeting_prep` 表，無 Supabase 退回檔案系統
- `GET /api/v1/meeting-prep/maturity-trend` — SEO 成熟度趨勢時間序列（data_points + summary）；Supabase 模式用 JSONB 查詢
- `GET /api/v1/meeting-prep/:date` — 取得單篇會議準備報告（YYYYMMDD 或 YYYYMMDD_hash8 格式）；支援精確+模糊匹配

環境變數（v2.11 新增，均可選）：

```env
ANTHROPIC_API_KEY=sk-ant-...     # Reranker（實驗性，auto 模式下自動偵測）
CONTEXT_EMBEDDING_WEIGHT=0.6     # Contextual embedding 加權（預設 0.6）
RERANKER_ENABLED=auto            # "auto"/"true"/"false"，預設 auto
```

Supabase 環境變數（v2.24，設定後自動切換至 pgvector 模式）：

```env
SUPABASE_URL=https://eqrlomuujichshkbtoat.supabase.co
SUPABASE_ANON_KEY=your_anon_key       # REST API 讀取（RLS SELECT）
SUPABASE_SERVICE_KEY=your_service_key  # Migration 寫入（bypasses RLS，不可暴露前端）
```

> `hasSupabase()` 偵測 `SUPABASE_URL` + `SUPABASE_ANON_KEY`，有設定則用 `SupabaseQAStore`（pgvector hybrid search），否則退回 `QAStore`（檔案模式）。
> 新增 Tables: `meeting_prep`（v3.7，date_key PK + JSONB meta + RLS service_role only + updated_at trigger）— `SupabaseMeetingPrepStore` + `store-registry.ts` 註冊

Agent 環境變數（v2.28 新增，v2.29 擴充 request-level mode，均可選）：

```env
AGENT_ENABLED=auto             # "auto"/"true"/"false"（auto=有 OpenAI key 就啟用 agent mode）
AGENT_MAX_TURNS=5              # Agent loop 最大輪數（1-10，預設 5）
AGENT_TIMEOUT_MS=90000         # Agent loop 總逾時（5000-300000，預設 90s）
```

> `isAgentEnabled()` 在 `utils/mode-detect.ts`，chat.ts 和 sessions.ts 共用。Agent mode 下 LLM 自主決定 tool calling（4 tools），多輪收集資訊後回答。
>
> **Request-level mode（v2.29）**：`POST /chat` 和 `POST /sessions/:id/messages` 支援 `mode: "agent" | "rag"` 參數。優先順序：Request > Server `AGENT_ENABLED` > auto fallback。Response `mode` 值統一為 `"rag" | "context-only" | "agent"`（`"full"` 已廢棄）。

### Observability（v2.7 三路整合）

| 路徑               | 追蹤方式                                                | 輸出              |
| ------------------ | ------------------------------------------------------- | ----------------- |
| CLI 腳本（Python） | Laminar `@observe` + `init_laminar()`                   | Laminar Dashboard |
| Claude Code 指令   | `utils/execution_log.py` → `output/execution_log.jsonl` | JSONL 本地日誌    |
| REST API（Hono）   | `@lmnr-ai/lmnr` JS SDK + `observe()` wrapper            | Laminar Dashboard |

環境變數：`LMNR_PROJECT_API_KEY`（`.env`），未設定則靜默跳過。

### 開發工具命令

- `/tdd` — 測試驅動開發工作流（先寫測試）
- `/plan` — 建立實作計畫，等待確認後再動手
- `/code-review` — Python 程式碼品質審查
- `/build-fix` — 修復建置 / 型別錯誤
- `/learn-eval` — 萃取本 session 可重用模式並存為 skill

### AutoResearch — Agent 自主循環優化

借鑑 karpathy/autoresearch 的 Loop-Forever 模式，agent 在隔離分支自主循環調參 → eval → keep/discard。

```bash
# 前置：啟動 API server（需 rate limit bypass）
cd api && RATE_LIMIT_DEFAULT=9999 pnpm dev

# 建立實驗分支 + 跑 baseline
git checkout -b autoresearch/<tag>
make autoresearch-baseline

# Agent 自主循環（讀 program.md 開始）
# 詳見 autoresearch/program.md
```

可修改：`search-engine.ts`（19 params）+ `query-term-utils.ts`（6 params）+ `keyword-boost.ts`（bigram prefix）的數值權重。詳見 `research/06-project-architecture.md` Section 24。

### Claude Code 模式 vs OpenAI 模式

| 功能              | OpenAI 模式                                                  | Claude Code 模式                                                      |
| ----------------- | ------------------------------------------------------------ | --------------------------------------------------------------------- |
| Q&A 萃取          | `gpt-5.4-nano` API                                           | Claude Code 直接讀 Markdown                                           |
| 去重 + 分類       | `text-embedding-3-small` + `gpt-5.4-nano`                    | 語意理解取代向量                                                      |
| 指標解析          | `metrics-parser.ts`（純 TS，v2.26）                          | `qa_tools.py load-metrics`                                            |
| 知識庫搜尋        | `text-embedding-3-small` + cosine                            | `qa_tools.py search`（關鍵字加權）                                    |
| 週報生成          | `report-llm.ts` + `gpt-5.4`（純 TS，v2.26）                  | `/generate-report` 指令（對齊 `scripts/04_generate_report.py`，需要 `OPENAI_API_KEY`） |
| Q&A 品質評估      | `gpt-5.4-nano`                                               | `/evaluate-qa-local`（Claude Code 作為 Judge）                        |
| Provider 品質評估 | 無對應                                                       | `/evaluate-provider`（Claude Code 作為 Judge，評估任何 LLM Provider） |
| API 伺服器        | `cd api && pnpm dev`（Hono, port 8002，需要 OPENAI_API_KEY） | `cd api && pnpm dev`（Hono, port 8002）                               |
| 需要 API key      | OPENAI_API_KEY                                               | 不需要                                                                |

---

## Git Workflow

- Conventional commits：`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- 禁止直接 commit 到 `main`
- PR 需通過所有測試才能合併
- Commit message 以中文或英文皆可，但須清楚描述「為什麼」而非「做了什麼」

### Commit 前知識沉澱清單（必做）

每次 commit 前，依序確認以下步驟是否適用，適用則執行：

1. **萃取 patterns** — 本次修改是否有可重用的模式？執行 `/learn-eval` 萃取並存入 `~/.claude/skills/learned/`
2. **更新 research/** — 本次修改涉及新技術知識？依下方分類指引補充到對應的 `research/*.md`
3. **更新 MEMORY.md** — 評估基準線變動、Bug 修復、模型替換等？更新 `~/.claude/projects/.../memory/MEMORY.md`
4. **更新架構圖** — 架構有重大調整？更新 `research/06-project-architecture.md` 的 Mermaid 圖和 Changelog

若本次為 typo fix、純測試修正、chore 類變更，以上可跳過。

### research/ 分類指引

新知識補充時，依主題寫入對應檔案：

| 主題                                                               | 檔案                                   |
| ------------------------------------------------------------------ | -------------------------------------- |
| LLM / Token / Embedding / Cosine / Prompt 基礎 / Structured Output | `research/01-ai-fundamentals.md`       |
| RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標                | `research/02-rag-and-search.md`        |
| 評估 / LLM-as-Judge / Reasoning Model / 評估維度設計               | `research/03-evaluation.md`            |
| Prompt Engineering 進階 / 業界最佳實踐                             | `research/04-prompting.md`             |
| 模型選擇決策 / Embedding 模型比較                                  | `research/05-models.md`                |
| 專案架構 / 技術決策 / Changelog / Mermaid 圖 / Observability       | `research/06-project-architecture.md`  |
| 部署 / Lambda / Docker / Supabase 遷移 / App Runner（已淘汰）      | `research/07-deployment.md`            |
| SEO 業界動態（Google 更新 / SER / 業界報導）                       | `research/11-seo-industry-updates.md`  |
| Meeting Prep 評分追蹤 / 交叉比對發現                               | `research/12-meeting-prep-insights.md` |
