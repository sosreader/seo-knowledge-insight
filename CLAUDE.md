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
make evaluate-qa       # 只執行品質評估
make dry-run           # 驗證設定（不執行）
make test              # 執行測試
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

---

## Available Claude Commands

### Pipeline 命令（需要 OpenAI API key）

- `/run-pipeline` — 執行完整 pipeline（Steps 1–5，使用 OpenAI）

### Claude Code 模式命令（不需要 OpenAI API key）

- `/pipeline-local` — 完整 pipeline Steps 1–4（你是 LLM 引擎）
- `/extract-qa` — 只執行 Step 2 Q&A 萃取（parallel sub-agents）
- `/dedupe-classify` — 只執行 Step 3 去重 + 分類
- `/generate-report <URL 或路徑>` — 生成 SEO 週報（解析指標 + 知識庫搜尋）
- `/search <問題>` — 搜尋知識庫（關鍵字加權，回傳 top-K Q&A）
- `/chat` — 互動式 RAG 問答（每輪自動搜尋知識庫）
- `/evaluate-qa-local` — Q&A 品質評估（Claude Code 作為 Judge，不需要 OpenAI）
- `/evaluate-provider <目錄路徑>` — 評估通用 LLM Provider 的 SEO 洞察品質（Claude Code 作為 Judge）

### 評估命令（需要 OpenAI API key）

- `/evaluate-qa` — Q&A 品質評估（LLM-as-Judge）+ 與基準線比較（本地替代：`/evaluate-qa-local`）

### API 伺服器命令

#### Python FastAPI（v2.2，port 8001）——逐步替換中

- 啟動：`uvicorn app.main:app --port 8001`
- 健康檢查：`GET /health`
- 週報管理：
  - `GET /api/v1/reports` — 列出所有週報
  - `GET /api/v1/reports/{date}` — 取得單篇週報內容（YYYYMMDD 格式）
  - `POST /api/v1/reports/generate` — 觸發週報生成

#### TypeScript Hono（v2.3，port 8002）——新架構

開發環境：
```bash
cd api
pnpm install           # 首次安裝依賴
pnpm dev               # 啟動開發伺服器（tsx watch，port 8002）
```

測試：
```bash
cd api
pnpm test              # 執行所有 vitest 測試
pnpm test:watch       # 監視模式下執行測試
pnpm test:coverage    # 生成測試覆蓋率報告
```

打包 / 部署：
```bash
cd api
pnpm build             # 編譯 TypeScript 至 dist/
pnpm start             # 執行 build 版本（node dist/index.js，port 8002）
```

Docker 執行（包含 Python API）：
```bash
docker-compose up      # 同時啟動 Python (8001) 和 TypeScript (8002) API
docker-compose logs seo-api-ts  # 監看 Hono 日誌
```

API 端點（與 Python 相同）：
- `GET /health` — 健康檢查
- 6 個路由器：qa、search、chat、reports、sessions、feedback
- 認證：`X-API-Key` header
- 詳見 `api/README.md`

### 開發工具命令

- `/tdd` — 測試驅動開發工作流（先寫測試）
- `/plan` — 建立實作計畫，等待確認後再動手
- `/code-review` — Python 程式碼品質審查
- `/build-fix` — 修復建置 / 型別錯誤
- `/learn-eval` — 萃取本 session 可重用模式並存為 skill

### Claude Code 模式 vs OpenAI 模式

| 功能 | OpenAI 模式 | Claude Code 模式 |
|------|------------|-----------------|
| Q&A 萃取 | `gpt-5.2` API | Claude Code 直接讀 Markdown |
| 去重 + 分類 | `text-embedding-3-small` + `gpt-5.2` | 語意理解取代向量 |
| 指標解析 | `fetch_from_sheets()` | `qa_tools.py load-metrics` |
| 知識庫搜尋 | `text-embedding-3-small` + cosine | `qa_tools.py search`（關鍵字加權）|
| 週報生成 | `gpt-5.2` API | Claude Code 直接推理 |
| Q&A 品質評估 | `gpt-5.2` + `gpt-5-mini` | `/evaluate-qa-local`（Claude Code 作為 Judge） |
| Provider 品質評估 | 無對應 | `/evaluate-provider`（Claude Code 作為 Judge，評估任何 LLM Provider） |
| API 伺服器 | `uvicorn app.main:app --port 8001`（FastAPI） | `cd api && pnpm dev`（Hono, port 8002） |
| 需要 API key | OPENAI_API_KEY | 不需要 |

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
| 專案架構 / 技術決策 / Changelog / Mermaid 圖 / Observability        | `research/06-project-architecture.md` |
| 部署 / FastAPI / ECR+App Runner / Docker / Supabase 遷移           | `research/07-deployment.md`           |
