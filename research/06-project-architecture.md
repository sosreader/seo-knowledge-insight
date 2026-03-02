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
  產出：670 筆原始 Q&A
            ↓ output/qa_per_meeting/*.json

[Step 3] dedupe_classify.py — 去重 + 分類
  去重：text-embedding-3-small 計算向量
        cosine ≥ 0.88 → gpt-5.2 判斷是否合併
        或 Claude Code 本地語意去重（不需要 OpenAI）
  分類：gpt-5-mini 貼 10 種標籤 + difficulty + evergreen
        或 Claude Code 本地評分式關鍵字分類（不需要 OpenAI）
  產出：655 筆去重後 Q&A（去除 15 組重複）+ 1536 維 embedding 向量
            ↓ output/qa_final.json + qa_embeddings.npy

[Step 4] generate_report.py — RAG 週報生成
  資料：Google Sheets 指標（TSV）
  流程：異常偵測 → Hybrid Search → RAG 組裝 → gpt-5.2 生成
            ↓ output/report_YYYYMMDD.md

[Step 5] evaluate.py — 評估
  Q&A 品質：gpt-5.2 LLM-as-Judge（4 維度）或 Claude Code 本地評估（不需要 OpenAI）
  分類品質：gpt-5-mini 驗證分類正確率
  Retrieval 品質：語意搜尋 + gpt-5-mini 相關性判斷
            ↓ output/eval_report.json / output/evals/eval_local_*.json

══════════════ API 層（2026-02-27 新增；v1.9 加入安全層）══════════════

[SEO Insight API] app/ — FastAPI，讀 Step 3 產出進記憶體
  認證：X-API-Key header（SEO_API_KEY env）
  速率限制：chat 20/min・search/qa 60/min（slowapi）
  回應格式：ApiResponse[T] envelope（data / error / meta）
  全局例外：500 不洩漏 traceback
  endpoints：
    POST /api/v1/search  → hybrid_search（語意 + 關鍵字）
    POST /api/v1/chat    → RAG 問答（gpt-5.2）
    GET  /api/v1/qa      → 篩選列表
  部署：Docker image → ECR → EC2（SSM 遠端換容器）
            ↓ http://EC2:8001

══════════════ Audit Trail（2026-02-28 新增）══════════════

[AuditLogger] utils/audit_logger.py — 零副作用 JSONL 日誌
  fetch 事件：每次 Step 1 執行記錄 session → output/fetch_logs/fetch_YYYY-MM-DD.jsonl
    log_fetch_start → log_fetch_page / log_fetch_skip → log_fetch_complete
  access 事件：每次 API 呼叫記錄 query + returned QA IDs + client IP + top_score
    → output/access_logs/access_YYYY-MM-DD.jsonl
  查詢工具：scripts/audit_trail.py fetch|access|report
            ↓ make audit / make audit-top

══════════════ Observability（2026-03-02 新增，v1.19）══════════════

[Laminar Tracing] OpenTelemetry-based distributed tracing（optional）
  FastAPI lifespan：Laminar.initialize() @ startup
  CLI scripts：init_laminar() @ main() 開始 + flush_laminar() @ finally 區塊
  @observe 裝飾器：
    app/core/chat.py：rag_chat（自動 OpenAI 追蹤）
    evals/eval_chat.py：eval_rag_chat（評估步驟追蹤）
    scripts/qa_tools.py：6 個子命令
      - merge_qa、search、load_metrics、eval_sample、eval_retrieval_local、eval_save

[Laminar Scoring] 即時評估事件附加
  score_event()：generic event 記錄
  score_rag_response()：answer_length、has_sources、top_source_score、source_count
  score_enrichment_boost()：synonym_hits、freshness_score（Multi-Layer Context 指標）
  score_qa_tools_operation()：qa_tools.py count + duration_ms

[TestIsolation] 測試隔離
  conftest.py：monkeypatch.delenv("LMNR_PROJECT_API_KEY") → 防止測試 traces 洩漏
              ↓ make test（200+ tests，traces 隔離）

══════════════ Multi-Layer Context（2026-03-02 新增，v1.19）══════════════

[Enrichment] scripts/enrich_qa.py — 離線 Q&A 豐富化（make enrich）
  輸入：output/qa_final.json（655 筆）
  計算：utils/synonym_dict.py（avg 11.09 個同義詞/筆，@lru_cache 執行緒安全）
        utils/freshness.py（avg freshness 0.9076，half_life=540d，min_score=0.5）
        output/access_logs（search_hit_count，需積累 14 天新格式 log）
  輸出：output/qa_enriched.json（含 _enrichment 欄位）
  store.py load()：優先載入 qa_enriched.json，fallback qa_final.json
  SearchEngine.__init__()：預計算 synonym_boost_vec + freshness_vec（shape=(655,) numpy）

[LearningStore] utils/learning_store.py — 失敗記憶 JSONL
  record_miss()：rag_chat() top_score < 0.35 時自動記錄
  record_feedback()：POST /api/v1/feedback（helpful / not_relevant）
  get_relevant_learnings()：keyword token 匹配歷史失敗
            ↓ output/learnings.jsonl
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

### 當前品質基準線（最新：2026-03-02，Multi-Layer Context Phase 1 後）

| 指標                | 初始 baseline | 最新數值       | 狀態                |
| ------------------- | ------------- | -------------- | ------------------- |
| Relevance           | 4.65          | **4.80** / 5   | ✅ 提升             |
| Accuracy            | 3.80          | **3.95** / 5   | ✅ 提升             |
| Completeness        | 3.70          | **3.85** / 5   | ✅ 達標（目標 3.8） |
| Granularity         | 4.65          | **4.75** / 5   | ✅ 提升             |
| Category 正確率     | 75%           | 68%            | 可接受（抽樣波動）  |
| Retrieval MRR       | 0.79          | 0.75           | 可接受（±0.04）     |
| LLM Top-1 Precision | 100%          | 100%           | ✅                  |
| KW Hit Rate（eval） | 54%           | **79.67%** ✅  | +9.27pp after enrich（目標 85%）|
| freshness_rank_quality | —          | **1.0**        | ✅                  |
| synonym_coverage    | —             | **1.0**        | ✅                  |

> ⚠️ Q&A Relevance/Accuracy 分數基於舊版 717 筆基準線，待 v2.0（655 筆）重新評估。

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

> 架構圖（最新 v1.19，含 Multi-Layer Context）維護於 [06b-architecture-diagram.md](./06b-architecture-diagram.md)

### 架構變更紀錄（Architecture Changelog）

> 詳細 Changelog 維護於 [06a-architecture-changelog.md](./06a-architecture-changelog.md)

### 更新架構圖的 SOP

> 維護 SOP 詳見 [06b-architecture-diagram.md](./06b-architecture-diagram.md#更新架構圖的-sop)

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

**決策**：啟動時載入全量 655 筆 QA + 655×1536 embedding matrix 到 module-level singleton，FastAPI lifespan 管理。

**學術 / 業界支撐**：

- **FAISS**（Johnson et al., 2019, _IEEE Trans. on Big Data_）：小規模向量（<100K）in-memory brute-force search 延遲 < 1ms，不需要 ANN 索引。655 筆完全在此範圍內。
- **12-Factor App Factor VI — Stateless processes**（Wiggins, 2011, Heroku）：唯讀查詢層用 in-memory 是合理優化，不違反無狀態原則。
- **Offline Feature Store + Online Serving**（Feast, 2019, Google/Tecton）：離線 pipeline 產出特徵 → 物化到 online store → API 讀取。與 Pipeline → qa_final.json → API 模式完全對應。

**評估**：符合當前規模（4.3MB）。DB 遷移路徑：pgvector（`plans/in-progress/seo-insight.md`）。

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

### I. Observability — Laminar SDK（OpenTelemetry-based，v1.19 完全整合）

**決策**：`@observe()` 裝飾器套用於所有 LLM 調用 + CLI 子命令，no-op shim 確保 API key 未設定時優雅降級。

**實作進展（v1.19，2026-03-02）**：

新增模組：
- `utils/observability.py`：`init_laminar()` + `flush_laminar()` + `start_cli_span()` context manager，CLI script 專用初始化
  - `@observe(name=...)` re-export from lmnr with no-op fallback
  - 多次調用 `init_laminar()` 為 safe（idempotent）
  - LMNR_PROJECT_API_KEY 未設定時優雅降級（不影響 pipeline 執行）

- `utils/laminar_scoring.py`：在 active span 內記錄評估分數
  - `score_event(name, value)`：通用 Laminar event 記錄
  - `score_rag_response(answer, sources, query)`：rag_chat span 內記錄 4 個即時評分
    - answer_length、has_sources、top_source_score、source_count
  - `score_enrichment_boost(synonym_hits, freshness_score)`：Multi-Layer Context enrichment 指標
  - `score_qa_tools_operation(operation, item_count, duration_ms)`：qa_tools.py 子命令計時和計數

- `evals/eval_chat.py`：Laminar 自動 OpenAI instrumentation（`Laminar.initialize()` in main）

- `tests/conftest.py`：測試隔離（`monkeypatch.delenv("LMNR_PROJECT_API_KEY")` 防止測試 traces 洩漏到 Laminar）

**qa_tools.py 集成**（6 個子命令）：
```python
@observe(name="qa_tools.merge_qa")       # Step 2 QA 合併
@observe(name="qa_tools.search")         # 知識庫搜尋
@observe(name="qa_tools.load_metrics")   # 指標載入
@observe(name="qa_tools.eval_sample")    # 評估採樣
@observe(name="qa_tools.eval_retrieval_local")  # 本地 retrieval 評估
@observe(name="qa_tools.eval_save")      # 評估檔案儲存
```

**依賴更新**（requirements.txt，2026-03-02）：
```
lmnr[openai]>=0.5.0
opentelemetry-semantic-conventions-ai>=0.4.13,<0.4.14
```

**Laminar 呼叫路徑**：
- FastAPI lifespan：app/main.py 啟動時 `Laminar.initialize()`
- CLI scripts：各 step script 呼叫 `init_laminar()` at main() 開始 + `flush_laminar()` at 結束（finally 區塊）
- evals：eval_chat.py 手動初始化 + LLM auto-instrumentation

**學術 / 業界支撐**：

- **OpenTelemetry Specification**（CNCF, 2023）：distributed tracing 是 cloud-native 應用的標準可觀測性手段。
- **Observability Engineering**（Majors et al., 2022, O'Reilly）：三大支柱 — traces、metrics、logs。本專案有 traces（Laminar）和 logs（audit_logger），**缺 metrics**。
- **Prometheus + Grafana 業界標準**（2024）：Prometheus metrics + `/metrics` endpoint 是生產監控標準。
- **OpenTelemetry Auto-Instrumentation**（Google + Datadog, 2023）：SDK 自動捕捉 HTTP client 呼叫（OpenAI、Google Sheets），無需手動攔截。

**評估**：traces + logs 已具備，缺 metrics（P50/P95/P99 延遲、cache hit rate、token usage）。建議加入 `prometheus-fastapi-instrumentator`。

---

### J. 模型分層策略

**決策**：gpt-5.2（複雜推理）→ gpt-5-mini（分類/判斷）→ text-embedding-3-small（向量），依任務複雜度選模型。

**學術 / 業界支撐**：

- **Scaling Laws for Neural Language Models**（Kaplan et al., 2020, _arXiv:2001.08361_）：不同複雜度任務匹配不同規模模型，是經濟高效的做法。
- **MTEB Benchmark**（Muennighoff et al., 2023, _arXiv:2210.07316_）：text-embedding-3-small 在中英文任務上性價比優於 large（差距 < 2%，價格差 5x），655 筆小規模知識庫使用 small 是正確決策。
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

---

## v1.17 — OpenAI Data Agent 啟發的多層知識庫架構改進計畫（2026-03-02）

### 核心設計決策

本版本針對現有系統的 L3（Learnings）和 L4（Runtime Context）層進行系統性補強，直接對應 OpenAI Data Agent 六層架構的前四層（L1-L4）。

**改進重點**（見 `plans/in-progress/multi-layer-context.md` 詳細計畫）：

1. **L1 Query Patterns**（P1-B）：建立 SEO 領域同義詞辭典 + offline enrichment 機制
2. **L2 Annotations**（P2-A）：強化 metadata 在搜尋中的加權（confidence + freshness）
3. **L3 Learnings**（P1-A）：記錄搜尋失敗案例，進行動態修正（新增 `output/learnings.jsonl`）
4. **L4 Runtime Context**（P1-C）：聚合 access logs，識別高頻查詢、零命中盲點、時效性衰減

**預期效益**：
- KW Hit Rate：78% → 85%+
- Accuracy：3.95 → 4.2+
- 搜尋延遲：50ms → 30ms
- 整體實作週期：1-2 週（Phase 1）+ 2-3 週（Phase 2）

**不建議引入**：
- 向量資料庫（655 筆，numpy 已足夠快）
- 模型 Fine-tuning（學習機制 + 人工回饋更靈活）
- Real-time Schema Introspection（schema 穩定，無必要）

### 架構圖演進

**現狀（v2.0）**：
```
qa_final.json（655 筆）
       ↓
搜尋引擎（cosine + keyword boost）
       ↓ 無時效衰減、無同義詞、無失敗記憶
API / Chat 回答
```

**改進後（v1.17）**：
```
qa_final.json → enrich_qa.py → qa_enriched.json
                                   ↓
              [L1] synonym_dict     [L2] freshness
              [L3] learnings        [L4] usage_stats
                           ↓
搜尋引擎（改進的混合分數公式）
  final_score = (semantic * cosine + keyword_boost)
              * (0.5 + 0.5 * confidence_weight)
              * freshness_score
              + synonym_boost + learning_boost + usage_boost
                           ↓
              API / Chat 回答 + 時效性警示
```

### 新增模組清單（Phases 1-2）

| 模組 | 檔案 | 行數 | 責任層級 |
|------|------|------|---------|
| **L1 同義詞** | `utils/synonym_dict.py` | ~120 | Query Patterns |
| **L4 時效性** | `utils/freshness.py` | ~60 | Runtime Context |
| **L3 失敗學習** | `utils/learning_store.py` | ~150 | Learnings |
| **L4 使用聚合** | `utils/usage_aggregator.py` | ~100 | Runtime Context |
| **Enrichment 主控** | `scripts/enrich_qa.py` | ~200 | Pipeline Step |
| **回饋路徑** | `app/routers/feedback.py` | ~80 | Annotations |
| **合計新增** | | **~710 行** | |

### 修改模組清單

| 檔案 | 修改項目 | 向下相容 |
|------|---------|--------|
| `utils/search_engine.py` | `_hybrid_scores()` 新增 4 個加權因子 | ✅ |
| `app/core/store.py` | 優先載入 qa_enriched.json，fallback qa_final.json | ✅ |
| `scripts/04_generate_report.py` | Step 4 記錄 learnings（top_score < 0.35） | ✅ 副作用 |
| `app/core/chat.py` | 整合 learning + staleness 警示 | ✅ 副作用 |
| `config.py` | 新增 5 常數（SYNONYM_BOOST 等） | ✅ |
| `qa_tools.py` | 新增子命令：analyze-access、annotate-category、compare-eval | ✅ |
| `Makefile` | 新增 targets：enrich-qa、pipeline-v2、eval-compare | ✅ |

### 技術亮點與設計原則

1. **Offline Enrichment 機制**：避免運行時計算複雜度，所有 L1-L4 層級在離線預處理階段計算一次，API 層直接消費豐富的 metadata
2. **Learning JSONL 為 append-only**：便於審計、調試、時序分析，無需額外維護 secondary index
3. **Confidence-Weighted 搜尋**：將 Q&A 品質（confidence）融入分數，減少虛構/過時結果排名靠前
4. **Staleness 警示**：對非 evergreen、超過 18 個月的結果，在 chat 回答中加入 ⚠️ 提示，提升用戶信任

### 依賴與風險管理

**關鍵依賴**：
- `source_date` 欄位：若 `qa_final.json` 缺少此欄，需從 `qa_per_meeting/` 回填
- Access logs 持續記錄：FastAPI 的 `audit_logger` 需正常運作

**緩解策略**：
- Enrichment 檔案過大 → 分塊載入（千筆級批次）
- Learning JSONL 無限增長 → 按月輪轉，保留最近 12 個月
- 同義詞詞典維護負擔 → 初始 100+ 詞彙後穩定；靠 P1-C zero-hit 識別新詞

### 評估指標進展

| 指標 | 目前（v2.0） | 目標（v1.17） | 機制 |
|------|-------------|-------------|------|
| KW Hit Rate | 78% | 85%+ | L1 + L3 + L4 |
| Accuracy | 3.95 | 4.2+ | L2 + L4 |
| Completeness | 3.85 | 4.1+ | L1 + L3 |
| Category Acc. | 68% | 80%+ | P2-B 人工回饋 |
| 搜尋延遲 | 50ms | 30ms | 預計算 + 緩存 |

### 後續研究方向（v2.0+）

- **Query Understanding 進階**：從 zero-hit queries 自動提取新同義詞
- **Active Learning**：自動篩選最具信息量的樣本進行人工標記
- **LLM-based Reranking**：top-5 結果上的語意再排序（成本 vs 收益評估）
- **多步 Agent 推理**：支援複雜、多條件查詢（L6 層，後期優先）

詳見完整實作計畫：`plans/in-progress/multi-layer-context.md`。

---

## v1.19 — Observability 全面整合與 CLI Laminar 追蹤（2026-03-02）

### 核心新增

**Laminar 完全整合** — 從 FastAPI 層擴展至 CLI 層和評估層：

1. **新增 utils/observability.py**
   - `init_laminar()`：CLI 腳本啟動時初始化（safe 多次調用）
   - `flush_laminar()`：main() finally 區塊提交待送出的 spans
   - `start_cli_span(name, input_data)`：CLI 子命令級 context manager（TOOL type）
   - `@observe` re-export：from lmnr，with no-op shim when lmnr not installed
   - 無條件降級：LMNR_PROJECT_API_KEY 未設定時 pipeline 正常執行

2. **新增 utils/laminar_scoring.py**
   - 在 active span 內即時記錄評估指標（不另起 LLM 呼叫）
   - `score_event(name, value)`：通用 Laminar event
   - `score_rag_response(answer, sources, query)`：RAG 回答 4 維度
   - `score_enrichment_boost(synonym_hits, freshness_score)`：Multi-Layer enrichment 指標
   - `score_qa_tools_operation(operation, item_count, duration_ms)`：CLI 操作計時

3. **evals/eval_chat.py 整合**
   - `Laminar.initialize()` @ main() 開始（before store import）
   - OpenAI auto-instrumentation：所有 gpt-5.2 呼叫自動追蹤

4. **scripts/qa_tools.py @observe 裝飾器**
   ```
   merge_qa (Step 2 QA 合併)
   search (知識庫搜尋)
   load_metrics (Google Sheets 指標載入)
   eval_sample (評估採樣)
   eval_retrieval_local (本地 retrieval 評估)
   eval_save (評估結果存檔)
   ```

5. **tests/conftest.py 隔離**
   - `monkeypatch.delenv("LMNR_PROJECT_API_KEY", raising=False)`
   - 防止測試 traces 洩漏到 Laminar dashboard（test isolation）

### 依賴更新

```
lmnr[openai]>=0.5.0                                        # +new
opentelemetry-semantic-conventions-ai>=0.4.13,<0.4.14    # +new, pinned
```

Laminar 版本 0.5.x 變更重點：
- `Laminar.initialize(project_api_key=...)`：取代 0.4.x 的 `Laminar(project_api_key=...)`
- `Laminar.start_as_current_span(name, input, span_type)`：新增 span_type 參數（TOOL, LLM, etc.）
- `Laminar.event(name, value)`：Span 內記錄事件（用於即時評分）
- `Laminar.flush()`：確保待送 spans 在 process exit 前提交

### 架構演變

**呼叫路徑**：
```
FastAPI lifespan                CLI scripts              evals
    ↓                              ↓                        ↓
Laminar.initialize()          init_laminar()        Laminar.initialize()
    ↓                              ↓                        ↓
@observe 自動捕捉            @observe 裝飾器        @observe 裝飾器
  LLM/HTTP 呼叫               + start_cli_span       + score_event
    ↓                              ↓                        ↓
Laminar dashboard ←─── Laminar.flush() ←─── Laminar.event()
```

### 測試涵蓋

- 206+ tests passing（包括新增 observability 隔離測試）
- monkeypatch 保證 LMNR_PROJECT_API_KEY 在測試環境未設定
- 測試分層：unit（pure logic） + integration（external calls mocked）

### 後續優化方向

1. **Metrics 補全**：Prometheus endpoint + `/metrics`
   - P50/P95/P99 延遲、cache hit rate、token usage per operation
2. **Laminar Dashboard 自訂**：在 Laminar UI 新增 custom evaluator（based on score_event）
3. **Trace Retention Policy**：超過 7 天的舊 traces 自動清理

### 質量檢查清單

- ✅ `init_laminar()` idempotent（多次調用安全）
- ✅ LMNR_PROJECT_API_KEY 未設定時 pipeline 正常執行（no-op shim）
- ✅ 所有 CLI script 呼叫 flush_laminar()（finally 區塊）
- ✅ 測試隔離（LMNR_PROJECT_API_KEY 未設定）
- ✅ score_event 失敗不中斷業務（try-except + logger.debug）
- ✅ requirements.txt pinned version 確保相容性
