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
make pipeline          # 完整流程 step 1→2→3
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
make fetch-articles    # 擷取所有外部文章（Medium + iThome + Google Cases）
make fetch-all         # Notion + 所有外部文章
make help              # 顯示所有可用 targets
```

### 直接呼叫 Python

```bash
.venv/bin/python scripts/run_pipeline.py                        # 完整流程
.venv/bin/python scripts/run_pipeline.py --step extract-qa --limit 3    # 測試用
.venv/bin/python scripts/run_pipeline.py --dry-run             # 只驗證設定
```

### GitHub Copilot（VS Code Tasks）

使用 `Ctrl+Shift+P` → "Tasks: Run Task" → 選擇對應的 Pipeline task。

### Claude Code Slash Command

```
/run-pipeline          # 查看完整用法說明（需要 OpenAI API key）
/pipeline-local        # 完整流程（不需要 OpenAI，AI 工具本身是 LLM）
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

### Claude Code 模式命令（不需要 OpenAI API key）

- `/pipeline-local` — 完整 pipeline Steps 1–4（你是 LLM 引擎）
- `/extract-qa` — 只執行 Step 2 Q&A 萃取（parallel sub-agents）
- `/dedupe-classify` — 只執行 Step 3 去重 + 分類
- `/generate-report <URL 或路徑>` — 生成 SEO 週報（解析指標 + 知識庫搜尋，支援 `--snapshot <snapshot_id>` 參數）
- `/search <問題>` — 搜尋知識庫（關鍵字加權，回傳 top-K Q&A）
- `/chat` — 互動式 RAG 問答（每輪自動搜尋知識庫）
- `/evaluate-qa-local` — Q&A 品質評估（Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-provider <目錄路徑>` — 評估通用 LLM Provider 的 SEO 洞察品質（Claude Code 作為 Judge）
- `/evaluate-faithfulness-local` — RAGAS Faithfulness 評估（Answer 是否有幻覺，Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-context-precision-local` — RAGAS Context Precision 評估（Retrieved contexts 有多少真正相關，Claude Code 作為 Judge）

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

前端開發環境（vocus-admin-dev）：

```bash
cd ../vocus-admin-dev
git checkout feat/admin-seo-insight  # 切換到前端開發分支
pnpm install
pnpm dev               # 啟動前端伺服器（http://localhost:3000）
```

測試（353 個測試，80% 覆蓋率）：

```bash
cd api
pnpm test              # 執行所有 vitest 測試（353 tests, 38 files）
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

- `GET /health` — 健康檢查
- 9 個路由器：qa、search、chat、reports、sessions、feedback、pipeline、synonyms、health
- Pipeline 端點：15 個（狀態、會議、來源文件、指標、快照等）
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
  - OpenAI 模式：`snapshot_id` + `use_openai` 參數（需 OpenAI API key，走 Python `04_generate_report.py`）
  - Legacy OpenAI 模式：`metrics_url` 參數指定 Google Sheets URL + `weeks` 參數（需 OpenAI API key）

Pipeline API 端點：

- `GET /api/v1/pipeline/status` — 各步驟完成狀態（6 步驟：fetch-notion/fetch-medium/fetch-ithelp/fetch-google/extract-qa/dedupe-classify）
- `GET /api/v1/pipeline/meetings` — 會議列表（含 metadata）
- `GET /api/v1/pipeline/meetings/:id/preview` — Markdown 預覽
- `GET /api/v1/pipeline/source-docs` — 列出所有來源文件（支援 source_type、source_collection、keyword、is_processed 等 filter + pagination）
- `GET /api/v1/pipeline/source-docs/:collection/:file/preview` — 來源文件預覽（會議/文章均支援）
- `GET /api/v1/pipeline/unprocessed` — 待處理的 Markdown 列表（含 source_collection）
- `GET /api/v1/pipeline/logs` — Fetch 歷史日誌
- `POST /api/v1/pipeline/fetch` — 觸發 Notion 增量擷取（不暴露 --force）
- `POST /api/v1/pipeline/fetch-articles` — 觸發外部文章擷取（Medium + iThome + Google Cases）
- `POST /api/v1/pipeline/extract-qa` — 觸發 Q&A 萃取
- `POST /api/v1/pipeline/dedupe-classify` — 觸發去重 + 分類
- `POST /api/v1/pipeline/metrics` — 取得 Pipeline metrics（解析 SEO 指標）
- `POST /api/v1/pipeline/metrics/save` — 儲存指標快照（支援 source、tab、label、weeks metadata）
- `GET /api/v1/pipeline/metrics/snapshots` — 列出指標快照清單（含 metadata）
- `DELETE /api/v1/pipeline/metrics/snapshots/:id` — 刪除指定快照

Synonyms API 端點（v2.11 新增）：

- `GET /api/v1/synonyms` — 列出所有同義詞（靜態 + 自訂，含 source 標記）
- `POST /api/v1/synonyms` — 新增自訂同義詞
- `PUT /api/v1/synonyms/:term` — 更新自訂同義詞
- `DELETE /api/v1/synonyms/:term` — 刪除自訂同義詞

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

### Claude Code 模式 vs OpenAI 模式

| 功能              | OpenAI 模式                                                  | Claude Code 模式                                                      |
| ----------------- | ------------------------------------------------------------ | --------------------------------------------------------------------- |
| Q&A 萃取          | `gpt-5.2` API                                                | Claude Code 直接讀 Markdown                                           |
| 去重 + 分類       | `text-embedding-3-small` + `gpt-5.2`                         | 語意理解取代向量                                                      |
| 指標解析          | `fetch_from_sheets()`                                        | `qa_tools.py load-metrics`                                            |
| 知識庫搜尋        | `text-embedding-3-small` + cosine                            | `qa_tools.py search`（關鍵字加權）                                    |
| 週報生成          | `04_generate_report.py` + OpenAI API（ECC 6 維度 prompt，支援 snapshot） | `/generate-report` 指令（Claude Code 直接推理，支援 snapshot）        |
| Q&A 品質評估      | `gpt-5.2` + `gpt-5-mini`                                     | `/evaluate-qa-local`（Claude Code 作為 Judge）                        |
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

| 主題                                                               | 檔案                                  |
| ------------------------------------------------------------------ | ------------------------------------- |
| LLM / Token / Embedding / Cosine / Prompt 基礎 / Structured Output | `research/01-ai-fundamentals.md`      |
| RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標                | `research/02-rag-and-search.md`       |
| 評估 / LLM-as-Judge / Reasoning Model / 評估維度設計               | `research/03-evaluation.md`           |
| Prompt Engineering 進階 / 業界最佳實踐                             | `research/04-prompting.md`            |
| 模型選擇決策 / Embedding 模型比較                                  | `research/05-models.md`               |
| 專案架構 / 技術決策 / Changelog / Mermaid 圖 / Observability       | `research/06-project-architecture.md` |
| 部署 / Lambda / Docker / Supabase 遷移 / App Runner（已淘汰）      | `research/07-deployment.md`           |
