# CLAUDE.md

> 專案架構、指令、模型政策等深度參考：`.claude/skills/seo-qa-pipeline.md`

---

## 語言規則

- 回覆與產出**唯一允許繁體中文（台灣用語，zh-TW）**；對齊全域 `~/.claude/CLAUDE.md`。
- 技術術語可保留英文（`useState`、`git commit`、API、schema 名稱、指標欄位）。
- **次要 agent / subagent 的 prompt 與回傳摘要也要求繁體中文**（除非任務本質是擷取英文原文，如業界來源標題/引文可保留原文，但分析與結論用繁體中文）。
- 報告產出（週報 / meeting-prep）、commit message、PR 說明一律繁體中文（commit 可夾英文技術術語，但敘述主體為繁體中文）。

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

### 5. Database Migrations

**`supabase/migrations/` 不是原始碼目錄，是部署佇列。** 檔案放進去就等於排隊上 prod。

- `supabase db push` 掃的是**整個目錄的待套用檔案，不看 git 狀態**——一個 `??` 未追蹤
  的草稿，在它眼裡跟已 review 已 merge 的檔完全一樣。這代表 **DDL 可以在沒經過
  stage / commit / review 任何一道關卡的情況下進 production**，而且不是被作者推的：
  任何一個併行 session 或使用者跑一次 `db push` 都會帶上去。
- **因此：沒有驗完的 migration 不要放進 `supabase/migrations/`。** 草稿寫在別處
  （scratchpad 或 `/tmp`），本機驗過再 `mv` 進來。放進來 = 宣告可以上線。
- **執行 `supabase db push` 之前，先跑：**
  ```bash
  git status --short supabase/migrations/     # 必須是空的
  supabase migration list                     # 看 pending 是不是只有你預期的那些
  ```
  `migrations/` 有任何未追蹤或未 stage 的檔案就**停下來問**，不要 push——
  那些是別人的草稿，你會替他們部署。
- 實例（2026-09-01）：一個 agent 的 016 草稿**從建檔到進 prod 不到 83 秒**
  （檔案 mtime `16:34:25` → 另一個 session 的 commit `3f191f8` 於 `16:35:48`，
  而那次 `db push` 發生在該 commit 之前），而草稿作者**從未執行過非 dry-run 的 push**。
  它的本機驗證恰好趕在那次 push 之前跑完，**是時間上的僥倖不是機制上的保證**——
  順序反過來，語法錯的 migration 就已經在 prod 了。
- 同版本號的兩份 migration 會撞 `schema_migrations_pkey`，**先套用者勝出、
  後者的 DDL 隨交易靜默回滾**——執行 push 的人不一定會發現自己那份沒生效。
  版本號若剛好不同，則兩份都會套用，同名物件誰最後生效**取決於檔名的字母序**。
  詳見 knowledge-base `wiki/learned/migrations-dir-is-a-deploy-queue-any-session-push-applies-your-draft.md`

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
make fetch-google-blog-zhtw # 只執行 Google Search Central Blog 繁體中文版擷取（HTML → Markdown）
make fetch-webdev      # 只執行 Web.dev 擷取（CWV/Performance 技術文章，RSS → Markdown）
make fetch-screaming-frog # 只執行 Screaming Frog Blog 擷取（技術 SEO 深度文章，RSS → Markdown）
make fetch-articles    # 擷取所有外部文章（10 個來源：Medium + iThome + Google Cases + Ahrefs + SEJ + Growth Memo + Google Blog + Google Blog zh-TW + Web.dev + Screaming Frog）
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
make autoresearch-meeting-prep-baseline  # AutoResearch meeting-prep baseline eval（rule-based，零 LLM）
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
/pipeline-local        # Notion-core pipeline（外部文章需先 `make fetch-articles`）
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

> **無 OPENAI_API_KEY 時的 fallback（PR #38, 2026-05-06）**：`make extract-qa`、`make dedupe-classify` 與 `make generate-report` 偵測到 `OPENAI_API_KEY` 為空時自動 fallback — `extract-qa` 走 heuristic 萃取（`utils/openai_helper.py:_LOCAL_EXTRACTION_MODEL = "claude-code-heuristic"`），`dedupe-classify` 走 hash-based embedding（`get_local_embeddings`）+ 最長 question + concat answers + 規則匹配 classify（`_classify_qa_locally`），`generate-report` 改用本地 metrics summary builder + rerank no-op，整段 pipeline 不會 fail。產出 QA 的 `extraction_model` 欄位會標記為 `claude-code-heuristic`。已知限制：heuristic difficulty 規則嚴重偏向「進階」（實測 98%）；若需正確分布需改用 OpenAI 模式重跑。

> **L4 maturity retighten（PR #42, 2026-05-07）**：`scripts/03_dedupe_classify.py` 新增三層 L4 防偽機制 — (1) `utils/maturity_classifier.py` 拆 `L4_KEYWORDS` ↔ `TREND_TOPIC_TERMS`（趨勢詞給 +1 而非 +2）+ 雙重證據規則（L4 必須伴隨 advanced pattern / `L4_STRATEGY_TERMS` / answer > 500 字）；(2) `utils/maturity_llm_judge.py`（新檔）gpt-5.4-nano LLM gate 對 rule-promoted L4 做 reality check；(3) 無 `OPENAI_API_KEY` 時跳過 LLM gate，純規則層 fallback。新增 `python scripts/03_dedupe_classify.py --reclassify-l4-only --execute` flag 對現有 `qa_final.json` 重跑分類（搭配 `push_qa_metadata_to_supabase.py --execute` 推 Supabase）。實測效果：本地 L4 13.4% → 7.5%、Supabase L4 13.7% → 9.3%。

---

## Available Claude Commands

### Pipeline 命令（需要 OpenAI API key）

- `/run-pipeline` — 執行 Notion-core pipeline（Steps 1–5，使用 OpenAI）

### Claude Code 模式命令（多數流程不需要 OpenAI API key）

- `/pipeline-local` — Notion-core pipeline Steps 1–3（外部文章需先 `make fetch-articles`，你是 LLM 引擎）
- `/extract-qa` — 只執行 Step 2 Q&A 萃取（parallel sub-agents）
- `/dedupe-classify` — 只執行 Step 3 去重 + 分類
- `/generate-report <URL 或路徑>` — 生成 SEO 週報（對齊 `scripts/04_generate_report.py`；`OPENAI_API_KEY` 設定時走 OpenAI rerank + LLM 摘要，未設定時 fallback 到本地 metrics summary builder；支援 `--snapshot <snapshot_id>`）
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
- `/sync-db` — 本地 Reports + Meeting-Prep（只送發布帳冊核准版本）+ Sessions 經 warehouse-api 推到 vocus-warehouse（`make sync-db` / `make sync-db-status` / `make sync-db-dry` / `make sync-db-force`；`TYPE=reports|meeting_prep|sessions|all`）
- `/backfill-extraction-model` — 追溯回填 Supabase qa_items 的 extraction_model（`--dry-run` / `--execute`）
- `/update-freshness` — 批次更新 freshness_score 指數衰減（`--dry-run` / `--execute`）
- `/evaluate-retrieval-by-model` — 按 extraction_model 分群評估檢索品質
- `/seo-frontend-hotfix` — 從 meeting-prep / weekly report 萃取「前端工程可實作」建議，先驗證 2026 最佳實踐再去 `~/Documents/vocus-web-ui` 修一版 hotfix + 發 PR（含駁回項回頭修正 source 報告，避免誤導累積）

### 評估命令（需要 OpenAI API key）

- `/evaluate-qa` — Q&A 品質評估（LLM-as-Judge）+ 與基準線比較（本地替代：`/evaluate-qa-local`）

### API 伺服器（已退役）

TypeScript Hono API（`api/`）與其 AWS Lambda 部署 `seo-insight-api`、GitHub Pages API 文件（`docs-site/`）已於 2026-10 退役並自 repo 移除，
前端 vocus-web-ui 改接 vocus-warehouse。需要查舊實作時用 `git log -- api/`；退役前最後一版為 main 的 92ed520。

仍保留在本 repo 的資料面指令：

- `make sync-db*` / `scripts/sync_db.py` — 本地報告、會議準備、sessions 經 warehouse-api 推到 vocus-warehouse
- `scripts/qa_tools.py` — 本地知識庫搜尋、pipeline 狀態、指標解析（取代舊 REST API 的對應端點）

Supabase 環境變數（Python 腳本與 eval 仍使用）：

```env
SUPABASE_URL=https://eqrlomuujichshkbtoat.supabase.co
SUPABASE_ANON_KEY=your_anon_key       # REST API 讀取（RLS SELECT）
SUPABASE_SERVICE_KEY=your_service_key  # Migration 寫入（bypasses RLS，不可暴露前端）
```

### Observability（v2.7 三路整合）

| 路徑               | 追蹤方式                                                | 輸出              |
| ------------------ | ------------------------------------------------------- | ----------------- |
| CLI 腳本（Python） | Laminar `@observe` + `init_laminar()`                   | Laminar Dashboard |
| Claude Code 指令   | `utils/execution_log.py` → `output/execution_log.jsonl` | JSONL 本地日誌    |

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
# 建立實驗分支 + 跑 baseline
git checkout -b autoresearch/<tag>
make autoresearch-meeting-prep-baseline

# Agent 自主循環（讀 program.md 開始）
# 詳見 autoresearch/meeting-prep/program.md
```

> `autoresearch/retrieval/`（調 TS 版 `search-engine.ts` 權重）隨 TS API 退役，已無可調標的，`make autoresearch-baseline` 已移除；
> 目錄只留實驗紀錄供查。詳見 `research/06-project-architecture.md` Section 24。

### Claude Code 模式 vs OpenAI 模式

| 功能              | OpenAI 模式                                                  | Claude Code 模式                                                      |
| ----------------- | ------------------------------------------------------------ | --------------------------------------------------------------------- |
| Q&A 萃取          | `gpt-5.4-nano` API                                           | Claude Code 直接讀 Markdown                                           |
| 去重 + 分類       | `text-embedding-3-small` + `gpt-5.4-nano`                    | 語意理解取代向量                                                      |
| 指標解析          | `utils/metrics_parser.py`                                    | `qa_tools.py load-metrics`                                            |
| 知識庫搜尋        | `text-embedding-3-small` + cosine                            | `qa_tools.py search`（關鍵字加權）                                    |
| 週報生成          | `scripts/04_generate_report.py` + OpenAI                     | `/generate-report` 指令（對齊 `scripts/04_generate_report.py`；`OPENAI_API_KEY` 設定時走 OpenAI，未設定時 fallback 到本地 metrics summary） |
| Q&A 品質評估      | `gpt-5.4-nano`                                               | `/evaluate-qa-local`（Claude Code 作為 Judge）                        |
| Provider 品質評估 | 無對應                                                       | `/evaluate-provider`（Claude Code 作為 Judge，評估任何 LLM Provider） |
| 需要 API key      | OPENAI_API_KEY                                               | 不需要                                                                |

---

## Git Workflow

- Conventional commits：`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- 禁止直接 commit 到 `main`
- PR 需通過所有測試才能合併
- Commit message 以繁體中文為主（可夾英文技術術語），須清楚描述「為什麼」而非「做了什麼」

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
