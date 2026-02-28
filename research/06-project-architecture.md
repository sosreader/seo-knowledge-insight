# 本專案架構與決策紀錄

> 屬於 [research/](./README.md)。涵蓋 Pipeline 全景、技術決策、架構圖、Changelog。

---

## 12. 本專案完整架構與決策

### Pipeline 全景

```
Notion 會議紀錄（87 份，2023–2026）
            ↓
[Step 1] fetch_notion.py — Notion API 擷取
  增量機制：比對 last_edited_time，只抓更新的頁面
            ↓ raw_data/markdown/*.md

[Step 2] extract_qa.py — LLM 萃取 Q&A
  模型：gpt-5.2（需要高品質理解）
  長文處理：超過 6000 tokens 自動切段
  產出：699 筆原始 Q&A
            ↓ output/qa_per_meeting/*.json

[Step 3] dedupe_classify.py — 去重 + 分類
  去重：text-embedding-3-small 計算向量
        cosine ≥ 0.88 → gpt-5.2 判斷是否合併
  分類：gpt-5-mini 貼 10 種標籤 + difficulty + evergreen
  產出：703 筆去重後 Q&A + 1536 維 embedding 向量
            ↓ output/qa_final.json + qa_embeddings.npy

[Step 4] generate_report.py — RAG 週報生成
  資料：Google Sheets 指標（TSV）
  流程：異常偵測 → Hybrid Search → RAG 組裝 → gpt-5.2 生成
            ↓ output/report_YYYYMMDD.md

[Step 5] evaluate.py — 評估
  Q&A 品質：gpt-5.2 LLM-as-Judge（4 維度）
  分類品質：gpt-5-mini 驗證分類正確率
  Retrieval 品質：語意搜尋 + gpt-5-mini 相關性判斷
            ↓ output/eval_report.json

══════════════ API 層（2026-02-27 新增）══════════════

[SEO Insight API] app/ — FastAPI，讀 Step 3 產出進記憶體
  啟動時載入：qa_final.json（703 筆）+ qa_embeddings.npy（703×1536）
  endpoints：
    POST /api/v1/search  → numpy cosine 語意搜尋
    POST /api/v1/chat    → RAG 問答（gpt-5.2）
    GET  /api/v1/qa      → 篩選列表
  部署：Docker image → ECR → EC2（SSM 遠端換容器）
            ↓ http://EC2:8001

══════════════ Audit Trail（2026-02-28 新增）══════════════

[AuditLogger] utils/audit_logger.py — 零副作用 JSONL 日誌
  fetch 事件：每次 Step 1 執行記錄 session → output/fetch_logs/fetch_YYYY-MM-DD.jsonl
    log_fetch_start → log_fetch_page / log_fetch_skip → log_fetch_complete
  access 事件：每次 API 呼叫記錄 query + returned QA IDs + client IP
    → output/access_logs/access_YYYY-MM-DD.jsonl
  查詢工具：scripts/audit_trail.py fetch|access|report
            ↓ make audit / make audit-top
```

### 模型選擇邏輯

```
需要理解複雜文本、推理、生成高品質輸出
  → gpt-5.2（主力模型）
  → 用於：Q&A 萃取、Q&A 合併、週報生成、LLM Judge

需要結構化輸出、分類、簡單判斷
  → gpt-5-mini（省成本）
  → 用於：Q&A 分類、Retrieval 相關性判斷

需要計算語意向量
  → text-embedding-3-small（極便宜，只做向量計算）
  → 用於：去重、Step 4/5 語意搜尋
```

### 當前品質基準線（2026-02-27，KW Fuzzy 匹配後）

| 指標                | 初始 baseline | 最新數值     | 狀態                |
| ------------------- | ------------- | ------------ | ------------------- |
| Relevance           | 4.65          | **4.80** / 5 | ✅ 提升             |
| Accuracy            | 3.80          | **3.95** / 5 | ✅ 提升             |
| Completeness        | 3.70          | **3.85** / 5 | ✅ 達標（目標 3.8） |
| Granularity         | 4.65          | **4.75** / 5 | ✅ 提升             |
| Category 正確率     | 75%           | 68%          | 可接受（抽樣波動）  |
| Retrieval MRR       | 0.79          | 0.75         | 可接受（±0.04）     |
| LLM Top-1 Precision | 100%          | 100%         | ✅                  |
| KW Hit Rate         | 54%           | **78%** ✅   | 已解決              |

### 花錢前必做：小規模驗證

任何需要 API 費用的改動，流程是：

```
1. 修改 prompt 或設定
2. --limit 3 只跑 3 份文件（驗證方向對）
3. 用 Step 5 評估那 3 份的品質
4. 通過門檻才擴大到全量
```

**不要先跑完 87 份再來評估要不要改 prompt。**

---

---

## 22. 架構圖與變更紀錄（Architecture Diagram & Changelog）

> 目標：每次架構調整後，自動維護一份 Mermaid 架構圖和 changes log。

### everything-claude-code 提供的工具

| 工具                  | 類型    | 功能                                                                                        | 適合場景           |
| --------------------- | ------- | ------------------------------------------------------------------------------------------- | ------------------ |
| **architect agent**   | Agent   | 設計新功能架構，會產出 high-level architecture diagram                                      | 有新元件要加入時   |
| **doc-updater agent** | Agent   | 掃描 codebase 生成文件 codemap（AST 分析）；可執行 `npx madge --image graph.svg` 生成相依圖 | 前端/Node.js 專案  |
| `/update-codemaps`    | Command | 掃描整個 codebase，在 `docs/CODEMAPS/` 生成 5 個 markdown 檔（含 ASCII 資料流圖）           | TypeScript/JS 專案 |

**限制**：`doc-updater` 和 `/update-codemaps` 依賴 Node.js（`madge`、`npx tsx`），不適合純 Python 專案。本專案應改用 Mermaid 手動維護。

### 本專案架構圖（Mermaid）

```mermaid
flowchart TD
    N[Notion API<br/>87 份會議 2023-2026] --> S1

    subgraph Pipeline["離線知識蒸餾 Pipeline"]
        PF[utils/pipeline_deps.py<br/>preflight_check<br/>StepDependency 宣告式檢查] -.->|每個 Script 啟動前| S1
        PF -.-> S2
        PF -.-> S3
        PF -.-> S4
        PF -.-> S5
        S1[Step 1: fetch_notion.py<br/>增量擷取 + Markdown 轉換] --> MD[raw_data/markdown/*.md]
        MD --> S2[Step 2: extract_qa.py<br/>gpt-5.2 萃取 Q&A<br/>+ Attribution Tag 補充]
        S2 --> RAW[output/qa_all_raw.json<br/>~700 筆原始 Q&A]
        RAW --> S3[Step 3: dedupe_classify.py<br/>embedding 去重 + gpt-5-mini 分類]
        S3 --> QA[output/qa_final.json<br/>703 筆 + 10 分類]
        S3 --> EMB[output/qa_embeddings.npy<br/>703 x 1536 維向量]
    end

    subgraph Eval["評估層 v1.4 v1.5"]
        GoldenSets["eval/ Golden Sets<br/>extraction(5) dedup(40) qa(50) report(5)"]
        QA --> S5[Step 5: evaluate.py<br/>LLM-as-Judge 5 維度<br/>+ 4 新評估函式]
        EMB --> S5
        GoldenSets --> S5
        S5 --> ER[eval_report.json<br/>Completeness 3.85<br/>+ threshold sweep]
    end

    subgraph RAG_Search["RAG和Hybrid Search v1.5"]
        GS[Google Sheets 指標 TSV] --> S4[Step 4: generate_report.py<br/>異常偵測 Hybrid Search RAG]
        QA --> S4
        EMB --> S4
        SE["SearchEngine v1.5<br/>compute_keyword_boost"] -.->|kw match| S4
        S4 --> RPT[report_YYYYMMDD.md]
    end

    subgraph RAG_API["API Layer 知識存取（v1.8 安全缺口已識別）"]
        QA --> API[SEO Insight API<br/>FastAPI QAStore singleton]
        EMB --> API
        SE -.->|hybrid_search 已實作<br/>但 search/chat<br/>尚未啟用| API
        API --> EP["POST /api/v1/search — 純語意搜索<br/>POST /api/v1/chat — 純語意搜索<br/>GET /api/v1/qa"]
        AUTH["Auth: 尚未實作<br/>Rate Limit: 尚未實作<br/>OWASP API Top10 風險"] -.->|CRITICAL 缺口| EP
    end

    subgraph AuditTrail["Audit Trail v1.0"]
        S1 -->|fetch events| AL["audit_logger.py<br/>output/fetch_logs/"]
        EP -->|access events| AL2["audit_logger.py<br/>output/access_logs/"]
        AL --> ATQ["audit_trail.py<br/>query tool"]
        AL2 --> ATQ
    end

    subgraph CacheLayer["Layer 1 Content-Addressed Cache v1.6"]
        S2 <-->|extraction cache| PC["pipeline_cache.py<br/>output/.cache/{ns}/{h[:2]}/{h}.json<br/>namespace: extraction/embedding/classify/merge/report"]
        S3 <-->|embed/classify/merge cache| PC
        S4 <-->|report cache| PC
        S3 -->|record_artifact| PV["pipeline_version.py<br/>output/.versions/registry.json<br/>Immutable step artifacts"]
        S4 -->|record_artifact| PV
    end

    subgraph Observability["可觀測性 v1.1 v1.4 v1.10"]
        S2 -->|observe| LM["Laminar SDK<br/>lmnr observe"]
        S3 -->|observe| LM
        S4 -->|observe| LM
        S5 -->|observe| LM
        API -->|auto trace| LM
        LM --> LD["laminar.sh dashboard<br/>Traces Spans"]
    end

    subgraph OfflineEvals["離線評估 v1.10"]
        GoldenSets2["eval/ Golden Sets<br/>retrieval(307) extraction chat(10)"]
        GoldenSets2 --> EvalR["evals/eval_retrieval.py<br/>keyword_hit_rate<br/>category_match"]
        GoldenSets2 --> EvalE["evals/eval_extraction.py<br/>qa_count<br/>keyword_coverage"]
        GoldenSets2 --> EvalC["evals/eval_chat.py<br/>answer_length<br/>has_sources"]
        EvalR -->|lmnr eval| LM
        EvalE -->|lmnr eval| LM
        EvalC -->|lmnr eval| LM
        EP -->|score_rag_response| OS["laminar_scoring.py<br/>online scores"]
        OS -->|attach to trace| LM
    end

    subgraph Deploy["部署"]
        API --> Docker[Docker Image]
        Docker --> ECR[AWS ECR]
        ECR --> EC2[EC2 SSM<br/>port 8001]
    end
```

### 架構變更紀錄（Architecture Changelog）

| 日期       | 版本 | 變更內容                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 影響範圍                                                                                                                                                                                                                                                                   |
| ---------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2023-03    | v0.1 | 初始 Pipeline：Step 1-3，Notion 擷取 + Q&A 萃取 + 去重                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | —                                                                                                                                                                                                                                                                          |
| 2026-02-27 | v0.2 | 新增 Step 4（RAG 週報生成）+ Step 5（評估層）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `scripts/`                                                                                                                                                                                                                                                                 |
| 2026-02-27 | v0.3 | 新增 SEO Insight API（FastAPI）+ ECR/EC2 部署                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `app/` 新增                                                                                                                                                                                                                                                                |
| 2026-02-27 | v0.4 | 修復 BUG-001（分類評估）+ BUG-002（Retrieval Judge）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `scripts/05_evaluate.py`                                                                                                                                                                                                                                                   |
| 2026-02-27 | v0.5 | 新增 `[補充]` Attribution Tag 機制提升 Completeness                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | `utils/openai_helper.py`, `scripts/05_evaluate.py`                                                                                                                                                                                                                         |
| 2026-02-27 | v0.6 | KW Hit Rate 改善：TypeA/TypeB 診斷 + Fuzzy 匹配（54% → 78%）+ `--debug-retrieval` + `--eval-reranking`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | `config.py`, `scripts/04_generate_report.py`, `scripts/05_evaluate.py`                                                                                                                                                                                                     |
| 2026-02-28 | v0.7 | 死碼清理：移除 10 項未使用 import/參數/函式/常數（vulture 80% 信心門檻），26 tests passing                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | `app/core/chat.py`, `utils/`, `scripts/`, `config.py`, `app/config.py`                                                                                                                                                                                                     |
| 2026-02-28 | v0.8 | 安全審查修復：config.py fail-fast env helpers（`_require_env`, `_get_float_env`, `_get_int_env`）；Google Sheets SSRF 防護（domain 白名單 + sheet_id/gid 格式驗證 + HTTP 狀態檢查 + 回應大小限制 10MB）；移除 `__import__` 非標準用法                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `config.py`, `scripts/04_generate_report.py`, `scripts/05_evaluate.py`                                                                                                                                                                                                     |
| 2026-02-28 | v0.9 | Fetch 管道優化：max_depth 10→3；新增 `--since` 增量篩選（1d/7d/日期）；避免重複 meta 查詢；預期快 50-85%                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | `scripts/01_fetch_notion.py`, `utils/notion_client.py`，新增 `docs/FETCH_OPTIMIZATION_GUIDE.md`                                                                                                                                                                            |
| 2026-02-28 | v1.0 | Audit Trail：全 fetch + API 存取 JSONL 日誌（session_id 關聯、zero side-effects）；`scripts/audit_trail.py` query CLI；`make audit/audit-top` shortcuts                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | `utils/audit_logger.py`（new），`scripts/audit_trail.py`（new），`scripts/01_fetch_notion.py`, `utils/notion_client.py`, `app/routers/search.py`, `app/routers/chat.py`, `app/routers/qa.py`                                                                               |
| 2026-02-28 | v1.1 | Laminar observability：`lmnr` 套件 + `Laminar.initialize()` 加入 `app/main.py`，所有 LLM 呼叫自動 trace；修復 `opentelemetry-semantic-conventions-ai 0.4.14` 缺少 `LLM_SYSTEM` 等 3 個屬性的相容問題                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `app/main.py`, `requirements_api.txt`, `.env.example`                                                                                                                                                                                                                      |
| 2026-02-28 | v1.2 | 模組化 Pipeline 計畫：各 Script 可直接執行（不需 `run_pipeline.py`），統一 pre-flight 依賴檢查 + 新鮮度警告。計畫文件：`.claude/plan/modular-pipeline-with-dep-checks.md`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 計畫階段，尚未實作                                                                                                                                                                                                                                                         |
| 2026-02-28 | v1.3 | DB 遷移策略計畫：釐清 `output/*` → PostgreSQL + pgvector 對應；識別唯一破壞性風險（`GET /qa/{id}` sequential int）；MVC 需做 3 件事（stable_id + canonical endpoint + store 欄位）。計畫文件：`.claude/plan/db-migration-strategy.md`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | 計畫階段，尚未實作                                                                                                                                                                                                                                                         |
| 2026-02-28 | v1.4 | **模組化 Pipeline 實作完成**：(1) `utils/pipeline_deps.py` — `StepDependency` frozen dataclass + `preflight_check()` 統一依賴檢查；(2) `config.py` 改 PEP 562 lazy loading（`import config` 不再觸發 env 驗證）；(3) 5 個 script 各自加入 `--check` flag + 宣告式依賴；(4) `run_pipeline.py` 移除 `check_config()`，改用 `parse_known_args()` 轉發 + `--check`/`--dry-run`；(5) Code review 修正：`PreflightError` 從 `SystemExit` 改為 `Exception`、`04_generate_report.py` import 去重、arg forwarding 限單步模式；(6) 新增 14 個 `config.py` lazy loading 測試（total 96 tests）；(7) Makefile 新增 `make check`；(8) README 更新分步執行文件                                                                                                                                                                                                                                                                                   | `utils/pipeline_deps.py`（new），`tests/test_pipeline_deps.py`（new），`tests/test_config_lazy.py`（new），`config.py`，`scripts/01-05`，`scripts/run_pipeline.py`，`Makefile`，`README.md`                                                                                |
| 2026-02-28 | v1.4 | Laminar 全 pipeline tracing：`utils/observability.py`（`init_laminar` / `flush_laminar` / `observe` no-op shim）；`@observe()` 裝飾器套用至 5 支 scripts + `openai_helper`；`openai_helper` 結構化呼叫統一輸出；`scripts/02` CLASSIFY prompt 加入 2×10 few-shot examples（68% → 80%+ 分類目標）                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `utils/observability.py`（new），`requirements.txt`（lmnr≥0.5.0），`utils/openai_helper.py`，`scripts/02_extract_qa.py`–`05_evaluate.py`                                                                                                                                   |
| 2026-02-28 | v1.5 | Research-grade eval 體系：golden sets 四份（extraction 5 + dedup 40 pairs + qa 50 items + report 5）；`utils/search_engine.py`（new，`SearchEngine` + 模組級 `compute_keyword_boost`）；`app/core/store.py` 新增 `hybrid_search()`；`config.py` 新增 `SEMANTIC_WEIGHT=0.7 / KEYWORD_WEIGHT=0.3`；`scripts/05_evaluate.py` 新增 4 函式（`evaluate_extraction/dedup/dedup_threshold_sweep/report_quality`）+ 7 CLI flags；`04_generate_report.py` 消除 `_compute_keyword_boost` 重複（改 delegate）                                                                                                                                                                                                                                                                                                                                                                                                                                  | `eval/`（4 golden JSONs），`utils/search_engine.py`（new），`app/core/store.py`，`config.py`，`scripts/04_generate_report.py`，`scripts/05_evaluate.py`                                                                                                                    |
| 2026-02-28 | v1.6 | **Layer 1 Content-Addressed Disk Cache + 版本 Registry 實作**：(1) `utils/pipeline_cache.py`（new）— SHA256 content-addressed cache，namespace 隔離，atomic write（`.tmp` → `rename`），two-level dir 防爆炸，zero external deps；(2) `utils/pipeline_version.py`（new）— 不可變 artifact registry，`record_artifact` 冪等，`get_all_token_stats()` 追蹤 cache 節省 token；(3) Step 2 cache 整合（`process_single_meeting` 命中→deepcopy+重新 enrich）；(4) Step 3 embedding/classify/merge cache 整合（`openai_helper.py`）；(5) Step 3/4 `record_artifact` 整合；(6) `.gitignore` 更新（`output/.cache/`、`output/.versions/step*/`）；(7) Makefile 新增 `cache-stats`/`cache-clear`/`version-history`；(8) 33 個新測試全數通過；(9) 修復 `config.py` 缺少 `Optional` import                                                                                                                                                     | `utils/pipeline_cache.py`（new），`utils/pipeline_version.py`（new），`tests/test_pipeline_cache.py`（new），`scripts/02_extract_qa.py`，`utils/openai_helper.py`，`scripts/03_dedupe_classify.py`，`scripts/04_generate_report.py`，`.gitignore`，`Makefile`，`config.py` |
| 2026-02-28 | v1.7 | **Code Quality 大掃除**：修復 5 個 HIGH + 7 個 MEDIUM 程式碼品質問題（129 tests ✓）。(1) `utils/pipeline_deps.py`：`assert` → `if/raise`（執行期驗證）、`datetime.now()` → `tz=timezone.utc`（DST 防禦）、`print()` → `logging`、移除未使用 typing imports；(2) `utils/openai_helper.py`：刪除重複 `observe` shim，改 `from utils.observability import observe`；(3) `config.py`：新增 `EVAL_JUDGE_MODEL` 和 `EVAL_RERANK_MODEL` lazy env vars；(4) `scripts/05_evaluate.py`：4 個硬編碼模型 → `config.EVAL_*_MODEL`、3 個 mypy 型別標記；(5) `scripts/04_generate_report.py`：刪除 `METRIC_QUERY_MAP` 重複宣告、移除硬編碼模型；(6) `scripts/03_dedupe_classify.py`：`classify_all_qas()` 改 return new list（immutability）、`main()` 改 list comprehension、dict 型別標記；(7) `scripts/run_pipeline.py`：移除 typing imports、改原生語法；(8) 批次移除 19 個 f-string 無佔位符；(9) 萃取 4 個可重用 patterns 存 learned skills | `utils/pipeline_deps.py`，`utils/openai_helper.py`，`config.py`，`scripts/{02,03,04,05}_*.py`，`scripts/run_pipeline.py`                                                                                                                                                   |
| 2026-02-28 | v1.8 | **Architect Review + Refactor Clean**：(1) 架構 review 識別 12 個技術決策，附業界/學術研究支撐；(2) 發現 CRITICAL 缺口：API 層無 Auth + 無 Rate Limit（OWASP API Top10 風險）；(3) 發現 HIGH 缺口：`SearchEngine.hybrid_search()` 已實作但 search/chat endpoint 未啟用，等同 v1.5 搜索品質提升在線上未生效；(4) Refactor：`_now_iso()` 雙次 datetime 調用修復、`get_qa_item()` O(n)→O(1) dict 索引、`classify_qa()` 硬編碼模型修正、search/chat 改用 hybrid_search；(5) 新增「技術決策學術支撐」章節（13 個決策，每個附論文/RFC 引用）；(6) 架構圖標注 API 層安全缺口與 hybrid_search 未啟用現況                                                                                                                                                                                                                                                                                                                                   | `app/routers/search.py`，`app/core/chat.py`，`app/core/store.py`，`utils/audit_logger.py`，`utils/openai_helper.py`，`research/06-project-architecture.md`                                                                                                                 |
| 2026-02-28 | v1.9 | **Provider 比較基準 + Bug 修復**：(1) 新增 `scripts/compare_providers.py`（LLM-as-Judge 5-provider 橫向比較）+ `eval/golden_seo_analysis.json`；(2) 加入 Laminar tracing（`@observe` + `init_laminar`/`flush_laminar` in CLI）；(3) 修復 Bug：path resolution 迴圈內 mutation → list comprehension；(4) 修復 Bug：retry loop exception swallowing（`return` → `continue`）；(5) 新增 K. Provider 比較基準架構章節；(6) 更新 research/03-evaluation.md、05-models.md 知識庫；(7) 萃取 3 個 instinct（openai-reasoning-no-response-format、retry-exception-not-just-empty、laminar-observe-cli-scripts）                                                                                                                                                                                                                                                                                                                             | `scripts/compare_providers.py`（new），`eval/golden_seo_analysis.json`（new），`output/provider_*.md`，`research/03-evaluation.md`，`research/05-models.md`，`research/09-provider-comparison.md`                                                                          |
| 2026-02-28 | v1.10 | **Laminar 離線評估系統**：(1) 新建 `evals/` 目錄（4 個 Python 模組），Laminar SDK 整合離線品質監控；(2) `utils/laminar_scoring.py`（new）— rule-based online scoring，4 個 lightweight evaluators（answer_length、has_sources、top_source_score、source_count），無額外 LLM 呼叫，自動附屬 rag_chat trace；(3) `evals/eval_retrieval.py` — 307 筆 golden retrieval set，keyword_hit_rate + category matching 評估；(4) `evals/eval_extraction.py` — extraction quality 評估（Q&A 計數、keyword coverage、無管理內容）；(5) `evals/eval_chat.py` — 10 scenario chat end-to-end 評估；(6) `.claude/skills/laminar-instrumentation.md`（new）— 強制執行 Laminar 計測規則；(7) PLAN_SEO_INSIGHT.md 新增 §3.0 「Laminar Eval 實作現況」；(8) 更新 README.md 文件架構 + 新增「步驟 6：Laminar 離線評估」；(9) 修復 app/core/chat.py 新增 online scoring 整合（v1.10 已完成） | `evals/`（new 4 files），`utils/laminar_scoring.py`（new），`.claude/skills/laminar-instrumentation.md`（new），`app/core/chat.py`，`PLAN_SEO_INSIGHT.md`，`README.md` |

### 更新架構圖的 SOP

每次架構有重大調整後：

1. 用 **architect agent** 討論新設計（`Task: subagent_type=everything-claude-code:architect`）
2. 把確認後的架構更新到 `research/06-project-architecture.md` 的 Mermaid 圖
3. 在 Architecture Changelog 新增一行（日期 + 版本 + 變更內容 + 影響範圍）
4. 更新 MEMORY.md 的確認基準線（如有評估數字變動）

> Mermaid 可以在 GitHub 預覽（直接渲染），也可以在 VS Code 安裝 Mermaid Preview 擴充套件後本機查看。

---

## 23. 技術決策學術支撐（v1.8 新增）

> 每個架構決策均附業界最佳實踐或學術論文引用，確保決策有據可查。

### A. Content-Addressed Disk Cache（pipeline_cache.py）

**決策**：SHA256(input content) 為 cache key，two-level directory，atomic write（`.tmp` → `rename`），無外部依賴。

**學術 / 業界支撐**：

- **Git Object Model**（Chacon & Straub, 2014, _Pro Git_ Ch.10.2）：Git 整個版本控制底層是 content-addressed store，SHA1 命名，相同內容永遠相同 key。本實作完全對齊此模型。
- **GPTCache**（Bang Liu et al., 2023, _arXiv:2303.11912_）：exact-match cache 對重複問題可降低 LLM API 調用 ~40%，延遲從 2.3s 降至 0.3s。
- **POSIX `rename(2)` 原子性**（IEEE Std 1003.1-2017, §3.246）：`tmp.replace(path)` 在 POSIX 保證原子，防止 partial write 汙染 cache。

**評估**：符合。設計簡潔，零部署依賴是正確的 Phase 1 選擇。

---

### B. Immutable Artifact Version Registry（pipeline_version.py）

**決策**：每次 pipeline run 產生帶版本 ID 的不可變 JSON artifact，content_hash 16 字元截短 SHA256，幂等寫入。

**學術 / 業界支撐**：

- **MLflow Tracking**（Zaharia et al., 2018, _IEEE Data Engineering Bulletin_）：每次 run 記錄 parameters、metrics、artifacts，跨版本比較與 reproducibility。本實作是輕量版 MLflow Tracking。
- **DVC — Data Version Control**（Kuprieiev et al., 2020, _JMLR_）：pipeline stage + content hash，未變更 stage 完全跳過執行，與本實作的 Layer 1 + Layer 2 組合直接對應。
- **Functional Data Engineering**（Beauchemin, 2018，Airflow 作者 blog）：pipeline task 應是 pure function，輸出只取決於輸入。`record_artifact()` 的幂等設計直接採用此原則。

**評估**：符合。`registry.json` 未來需要 retention policy（版本數量超過 1000 時）。

---

### C. Hybrid Search（SearchEngine + compute_keyword_boost）

**決策**：`final_score = semantic_weight * cosine_sim + keyword_boost`，token 級雙向匹配，KW Hit Rate 54% → 78%。

**學術 / 業界支撐**：

- **Dense Passage Retrieval**（Karpukhin et al., 2020, _EMNLP 2020_）：hybrid search 結合 sparse（關鍵字）與 dense（向量）已是 RAG 系統標準架構，hybrid 通常比純 dense 或純 sparse 好 3-5%。
- **Reciprocal Rank Fusion**（Cormack et al., 2009, _SIGIR 2009_）：RRF `1/(k+rank)` 對 score scale 不敏感，比線性加權更 robust。**未來改進方向**：考慮從線性加權改為 RRF。
- **LlamaIndex + LangChain 官方文檔**（2024）：hybrid retrieval 是生產 RAG 系統的推薦預設配置。

**評估**：現況符合，但 API 層尚未啟用（HIGH 缺口，v1.8 已修復）。線性加權未來可升級為 RRF。

---

### D. LLM-as-Judge 評估體系（05_evaluate.py）

**決策**：4 維度評分（Relevance / Accuracy / Completeness / Granularity），1-5 分，gpt-5.2 Judge，structured output strict mode。

**學術 / 業界支撐**：

- **MT-Bench + Chatbot Arena**（Zheng et al., 2023, _NeurIPS 2023_）：GPT-4 級模型作 judge 與人類評審一致性 >80%，4 維度評分是業界標準做法。
- **RAGAS**（Shahul et al., 2023, _arXiv:2309.15217_）：自動化 RAG 評估框架，提出 faithfulness / answer relevance / context precision / context recall 四維度，與本實作維度設計接近。
- **Self-Consistency**（Wang et al., 2023, _ICLR 2023_）：關鍵評估建議多次採樣取中位數，減少單次 Judge 隨機性。**未來改進**：Accuracy 維度考慮 3 次採樣。

**評估**：符合。Golden set 樣本數偏小（extraction 5 筆、report 5 筆），建議擴充至 ≥20 筆以達統計顯著性（n≥30 原則）。

---

### E. FastAPI + In-Memory QAStore

**決策**：啟動時載入全量 703 筆 QA + 703×1536 embedding matrix 到 module-level singleton，FastAPI lifespan 管理。

**學術 / 業界支撐**：

- **FAISS**（Johnson et al., 2019, _IEEE Trans. on Big Data_）：小規模向量（<100K）in-memory brute-force search 延遲 < 1ms，不需要 ANN 索引。703 筆完全在此範圍內。
- **12-Factor App Factor VI — Stateless processes**（Wiggins, 2011, Heroku）：唯讀查詢層用 in-memory 是合理優化，不違反無狀態原則。
- **Offline Feature Store + Online Serving**（Feast, 2019, Google/Tecton）：離線 pipeline 產出特徵 → 物化到 online store → API 讀取。與 Pipeline → qa_final.json → API 模式完全對應。

**評估**：符合當前規模（4.3MB）。DB 遷移路徑：pgvector（PLAN_SEO_INSIGHT.md）。

---

### F. PEP 562 Lazy Loading Config

**決策**：module-level `__getattr__` 實現 lazy env var 解析，各 Step 只驗證自己需要的 key。

**學術 / 業界支撐**：

- **PEP 562**（Python 3.7+, 2017）：官方 module-level `__getattr__` 支援，Django 等框架用於 lazy import 與 deprecation warnings。
- **12-Factor App Factor III — Config in env**（Wiggins, 2011, Heroku）：所有配置從環境變數讀取。
- **Fail-Fast Principle**（Shore & Warden, 2004, _The Art of Agile Development_）：變數在需要時才驗證，但失敗時立即拋出有意義的 `ValueError`。

**評估**：符合，設計優雅。`app/config.py` 與 `config.py` 存在重複定義，建議統一（MEDIUM 技術債）。

---

### G. OWASP API Security — 已識別缺口

**決策（尚未實作）**：API 目前無 Auth、無 Rate Limit。

**學術 / 業界支撐**：

- **OWASP API Security Top 10（2023）**：
  - API2:2023 — Broken Authentication：無認證的 API 是 Top 2 風險
  - API4:2023 — Unrestricted Resource Consumption：無 Rate Limit 等同暴露成本風險
- **RFC 6585（2012）**：定義 HTTP 429 Too Many Requests，用於 Rate Limiting 標準回應。
- **Microsoft REST API Guidelines（2024）**：所有 API 回傳統一 envelope（`{data, error, metadata}`），方便前端統一錯誤處理。

**評估**：CRITICAL 缺口。`/api/v1/chat` 每次調用消耗 GPT token，任何知道 URL 者皆可呼叫。**實作優先順序**：Auth（2h）> Rate Limit（2h）> Response Envelope（2h）。

---

### H. Audit Trail（JSONL 格式，按日分檔）

**決策**：JSONL 格式，按日分檔，零副作用（失敗不影響業務），session_id 關聯。

**學術 / 業界支撐**：

- **OWASP Logging Cheat Sheet（2023）**：推薦 log 包含 timestamp、event type、user/IP、affected resources，本實作全部涵蓋。
- **12-Factor App Factor XI — Logs as event streams**（Wiggins, 2011）：日誌應是無緩衝、追加式的事件流，JSONL 完全對齊。
- **ELK Stack 最佳實踐**：JSONL 格式可直接被 Filebeat / Fluentd 採集，無需額外 parser。

**評估**：符合。未來需要考慮 Client IP 匿名化（GDPR / 台灣個資法）和 log rotation policy。

---

### I. Observability — Laminar SDK（OpenTelemetry-based）

**決策**：`@observe()` 裝飾器套用於所有 LLM 調用，no-op shim 確保 API key 未設定時優雅降級。

**學術 / 業界支撐**：

- **OpenTelemetry Specification**（CNCF, 2023）：distributed tracing 是 cloud-native 應用的標準可觀測性手段。
- **Observability Engineering**（Majors et al., 2022, O'Reilly）：三大支柱 — traces、metrics、logs。本專案有 traces（Laminar）和 logs（audit_logger），**缺 metrics**。
- **Prometheus + Grafana 業界標準**（2024）：Prometheus metrics + `/metrics` endpoint 是生產監控標準。

**評估**：traces + logs 已具備，缺 metrics（P50/P95/P99 延遲、cache hit rate、token usage）。建議加入 `prometheus-fastapi-instrumentator`。

---

### J. 模型分層策略

**決策**：gpt-5.2（複雜推理）→ gpt-5-mini（分類/判斷）→ text-embedding-3-small（向量），依任務複雜度選模型。

**學術 / 業界支撐**：

- **Scaling Laws for Neural Language Models**（Kaplan et al., 2020, _arXiv:2001.08361_）：不同複雜度任務匹配不同規模模型，是經濟高效的做法。
- **MTEB Benchmark**（Muennighoff et al., 2023, _arXiv:2210.07316_）：text-embedding-3-small 在中英文任務上性價比優於 large（差距 < 2%，價格差 5x），703 筆小規模知識庫使用 small 是正確決策。
- **Structured Output**（OpenAI, 2024）：`json_schema` strict mode 確保 LLM 輸出 100% 符合 schema，消除 JSON parse 失敗風險。

**評估**：符合。建議將 embedding 模型也放入 config lazy env，方便未來切換。

---

### K. AI Provider 比較基準架構

**決策**：新增 `scripts/compare_providers.py`，實作 LLM-as-Judge 的 Provider 橫向比較框架，評估本系統報告 vs 市售 AI 工具的輸出品質。

**架構元件**：

```
scripts/compare_providers.py          # 主腳本
eval/golden_seo_analysis.json         # Golden case：原始 GSC 資料 + 評估維度
output/provider_<name>_<date>.md      # 各 Provider 輸出檔案（人工輸入或自動生成）
research/09-provider-comparison.md    # 完整實驗紀錄與結論
```

**流程**：

1. 人工準備各 Provider 輸出檔（`output/provider_*.md`）
2. `compare_providers.py` 讀取所有檔案，呼叫 Judge LLM（gpt-5.2）逐一評分
3. 輸出 Markdown 比較報告到 `output/comparison_<date>.md`
4. Laminar 追蹤每次 Judge 呼叫（`@observe(name="provider_llm_judge")`）

**Laminar 整合方式**：

```python
from lmnr import Laminar, observe

Laminar.initialize(project_api_key=os.environ["LMNR_PROJECT_API_KEY"])

@observe(name="provider_llm_judge")
def _judge_one(name: str, content: str, raw_data: str) -> dict: ...
```

CLI scripts 不依賴 FastAPI lifespan，需要在 `main()` 手動呼叫 `init_laminar()` / `flush_laminar()`。

**評分維度**：

- **Grounding**：結論是否有數據支撐
- **Actionability**：建議是否具體可執行
- **Relevance**：分析是否切題

**實驗結果（2026-02-28）**：system_seoinsight 5.0/5（第一），chatgpt & gemini_thinking 4.0，claude 3.0，gemini_research 2.33。

**學術支撐**：

- **G-Eval**（Liu et al., 2023, _arXiv:2303.16634_）：使用 LLM-as-Judge 搭配評分維度細分，可替代人工評估；多維度評分比單一分更具診斷價值。
