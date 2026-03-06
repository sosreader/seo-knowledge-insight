# 本專案架構與決策紀錄

> 屬於 [research/](./README.md)。涵蓋 Pipeline 全景、技術決策、架構圖、Changelog。

---

## 12. 本專案完整架構與決策

### Frontend UI 架構（v2.5，2026-03-05）

**核心理念**：前端採用 custom hook + toolbar/dashboard 組件模式，提升 SPA 應用的可維護性與可測試性。

**SEO 知識庫頁面（/admin/seoInsight/chunk，v2.10 改名）- UI 層次**：

```
                  QAFilterToolbar
                 /      |      \      \
        Keyword   Category  Difficulty  Evergreen
        Input      Select     Select      Select
           |         |          |          |
           └─────────┴──────────┴──────────┘
                     ↓
           useQAFilters (hook)
                     ↓
           QA Table + Pagination
```

**useQAFilters Hook**（248 行）：

- **State Management**：
  - `filters` (Filters object)：category、keyword、difficulty、evergreen
  - `page`、`sorting`、`items`、`total`、`categories`
  - `isLoading`、`error`
- **Derived State**（useMemo）：
  - `hasActiveFilters`：判定是否有篩選條件
  - `activeFilterChips`：已套用的篩選條件 array（用於 badge 顯示）
- **Debouncing**：
  - `debouncedKeyword` (300ms)：避免頻繁 API 呼叫
  - 當 debouncedKeyword 變更時重置 page=0
- **Actions**：
  - `setFilter(key, value)`：設定篩選，非 keyword 時重置分頁
  - `removeFilter(key)`：移除單一篩選
  - `clearFilters()`：清除所有篩選
  - `handleSortingChange()`：排序變更時重置分頁
- **API 整合**（useEffect）：
  - 依賴：[page, filters.category, debouncedKeyword, filters.difficulty, filters.evergreen, sorting]
  - 呼叫 `getQAList({offset, limit, category, keyword, difficulty, evergreen, sort_by, sort_order})`
  - Abort pattern：`cancelled` flag 防止競態條件

**QAFilterToolbar 組件**（168 行）：

- **Input 層**（shadcn-ui）：
  - `InputWithClear`：keyword with X 按鈕
  - `FilterSelect` (wrapper around Select)：category、difficulty、evergreen，支援 CLEAR_VALUE 機制
- **Filter Chips**（Badge）：
  - 顯示已套用的篩選條件
  - 每個 badge 右側有 X 按鈕，點擊移除該篩選
  - Display mapping：evergreen: {true: "新鮮", false: "老化"}
- **Action 按鈕**：
  - 「清除篩選」（條件：hasActiveFilters=true）
  - Ghost variant，text-xs

**設計決策**：

1. **Separation of Concerns**：hook 負責狀態 + API，component 只負責 UI 渲染
2. **Debouncing Strategy**：keyword 輸入延遲 300ms，避免 API 訪問頻率過高
3. **Keyword 搜尋**：純關鍵字篩選（後端支援 CJK n-gram），移除語意搜尋 UI
4. **Filter Chips 互動**：視覺反饋 + 單獨移除，提升 UX
5. **Stateless FilterSelect**：CLEAR_VALUE 讓使用者可用鍵盤導航回到「全部」狀態

**RAG 問答頁面（/admin/seoInsight/chat）- Context-Only 模式（v2.5）**：

```
                  chat.tsx
                    |
        chatMode state ("full" | "context-only" | null)
                    |
        ┌───────────┼───────────┐
        ↓           ↓           ↓
  Context-Only   Message     ChatMessage
    Banner       Bubbles      Bubble
  (mode banner)  (list)    (null content
                            → fallback 文字
                            + auto-expand
                              SourcesList)
```

- `sendSessionMessage` 回傳 `mode` 欄位，驅動 `chatMode` state
- `ChatMessageBubble` 的 `content` prop 支援 `string | null`
- 無 content 且 role=assistant 時，顯示「OpenAI 未設定，僅顯示相關參考來源」
- SourcesList 在 context-only 模式自動展開（`defaultExpanded={!hasContent}`）
- `handleNewChat` 和 `loadSession` 重設 `chatMode` 避免殘留 badge

**Q&A 評估儀表板（已於 v2.18 移除）**：

eval.tsx、useEvalDashboard.ts 及四個 Eval 組件（EvalMetricsCards/EvalProviderComparison/EvalSampleTable/EvalSaveForm）已全部刪除。評估結果改直接使用 Laminar Dashboard 追蹤（`report-quality`、`keyword-retrieval`、`data-quality` groups）。

**Pipeline 指標分析（PipelineMetrics 組件，嵌入 pipeline.tsx）**：

- Source URL/path input + tab select（vocus/custom）
- POST /pipeline/metrics 載入，結果以 key-value 表格顯示

---

### Pipeline 全景（ETL 架構）

本專案 pipeline 遵循經典 **ETL（Extract → Transform → Load）** 模式：

| ETL 階段 | Pipeline 步驟 | 說明 |
|----------|--------------|------|
| **Extract** | Step 1：fetch | 從 Notion / Medium / iThome / Google Cases 擷取原始 Markdown |
| **Transform** | Step 2：extract-qa | LLM 萃取 Q&A pairs |
| | Step 3：dedupe-classify | 去重 + 分類 + embedding 向量化 |
| **Load** | Step 3 產出 → Supabase | `qa_final.json` 寫入 pgvector，供 RAG 搜尋使用 |
| （應用層） | Step 4：generate-report | RAG 週報生成（異常偵測 → Hybrid Search → LLM 生成） |
| （評估層） | Step 5：evaluate | LLM-as-Judge 品質評估 |

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
  產出：1,317 筆去重後 Q&A（去除 96 組重複）+ 1536 維 embedding 向量
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

══════════════ API 層（v1.9 安全層；v2.2 stable_id + reports/sessions；v2.3 Hono TypeScript）══════════════

**Python FastAPI（v2.2，port 8001）**——舊架構，逐步替換中
[SEO Insight API] app/ — FastAPI，讀 Step 3 產出進記憶體
  認證：X-API-Key header（SEO_API_KEY env）
  速率限制：chat 20/min・search/qa 60/min・reports/generate 5/min（slowapi）
  回應格式：ApiResponse[T] envelope（data / error / meta）
  全局例外：500 不洩漏 traceback
  QA ID：stable_id（SHA256[:16] hex），QAItem.id: str + seq: int
  endpoints：
    POST /api/v1/search    → hybrid_search（語意 + 關鍵字）
    POST /api/v1/chat      → RAG 問答（gpt-5.2）
    GET  /api/v1/qa        → 篩選列表（id=stable_id hex）
    GET  /api/v1/qa/{id}   → 單筆查詢（^[0-9a-f]{16}$ 驗證）
    POST /api/v1/feedback  → 使用者回饋（helpful / not_relevant）
    GET  /api/v1/reports   → 週報列表（newest first）
    GET  /api/v1/reports/{date} → 單篇週報 Markdown（YYYYMMDD）
    POST /api/v1/reports/generate → 觸發週報生成（subprocess，timeout 120s）
    GET  /api/v1/sessions  → 對話 session 列表
    POST /api/v1/sessions  → 建立 session
    GET  /api/v1/sessions/{id} → 取得 session 對話記錄
    POST /api/v1/sessions/{id}/messages → 新增訊息
    DELETE /api/v1/sessions/{id} → 刪除 session
  部署：Lambda + Function URL（arm64，~$0/月）
  資料層：SupabaseQAStore（pgvector hybrid search）/ QAStore（檔案模式 fallback）
  Session 儲存：output/sessions/{uuid}.json（Repository Pattern）
            ↓ Lambda Function URL（https://...lambda-url.ap-northeast-1.on.aws/）

**TypeScript Hono（v2.12，port 8002，新架構）**——直接取代 Python API
[SEO Insight API v2] api/src — Hono + TypeScript，完全移植 Python 功能 + Local Mode 降級
  框架：Hono（輕量、Cloudflare Workers / Node.js 相容）
  驗證：Zod schema validation（TypeScript-first）
  回應格式：ApiResponse[T] envelope（data / error / meta）
  認證：X-API-Key middleware
  速率限制：Hono 內置 middleware（chat 20/min・search/qa 60/min・reports/generate 5/min）
  QA ID：stable_id（SHA256[:16] hex），與 Python 相同驗證規則
  Local Mode：無 OpenAI API key 時自動降級（search→keyword-only，chat→context-only）
  endpoint（9 個 router，31 端點，v2.12～v2.18）：
    - routes/qa.ts        — GET /qa, /qa/categories, /qa/{id}（hex+int）
    - routes/search.ts    — POST /search（mode: hybrid|keyword，hasOpenAI() 自動切換；v2.11 over-retrieve + rerank）
    - routes/chat.ts      — POST /chat（mode: full|context-only，無 OpenAI 時回傳 sources + answer:null；v2.11 rerank 可啟用）
    - routes/reports.ts   — GET /reports, /reports/{id}, POST /reports/generate
    - routes/sessions.ts  — GET /sessions, POST /sessions, GET /sessions/{id}, POST /sessions/{id}/messages（context-only fallback）, DELETE /sessions/{id}
    - routes/feedback.ts  — POST /feedback
    - routes/pipeline.ts  — GET /status, /source-docs, /source-docs/:collection/:file/preview, /unprocessed, /logs, POST /fetch, /fetch-articles, /extract-qa, /dedupe-classify, /metrics
    - routes/synonyms.ts  — GET /synonyms, POST /synonyms, PUT /synonyms/{term}, DELETE /synonyms/{term}（雙層設計：28 靜態術語 + 32 新增（v2.11）+ custom JSON）
  核心模組：
    - store/qa-store.ts：QAStore（讀 qa_final.json + embedding 向量，embedding optional）
    - store/session-store.ts：FileSessionStore（Repository Pattern）
    - store/learning-store.ts：LearningStore（feedback + miss 記錄）
    - store/synonyms-store.ts：SynonymsStore（雙層設計：28 基礎術語 + 31 補充術語（v2.11）= 59 靜態術語 + output/synonym_custom.json 自訂覆蓋，v2.10 新增）
    - store/search-engine.ts：SearchEngine（hybrid search + keyword boost + keywordOnlySearch）
    - utils/npy-reader.ts：NumPy .npy 檔案解析（numpy 相容）
    - utils/cosine-similarity.ts：向量運算（Float32Array）
    - utils/keyword-boost.ts：4 層關鍵字匹配
    - utils/cjk-tokenizer.ts：CJK 分詞（2-gram + 單字，中文 keyword search 支援）
    - utils/mode-detect.ts：hasOpenAI() helper（Local Mode 偵測）
    - services/embedding.ts：OpenAI embedding wrapper
    - services/rag-chat.ts：RAG 問答（需要 OpenAI API key；v2.11 支援 reranker）
    - services/reranker.ts：Haiku reranker（v2.11 新增，需要 ANTHROPIC_API_KEY）
    - services/context-relevance.ts：Context Relevance 評估（v2.12 新增，Claude haiku judge；per-context 細分；escapeXml() 防 prompt injection）
    - services/report-generator-local.ts：本地週報生成（v2.13 新增；6 維度 ECC 分析；無需 OpenAI API；含 RESEARCH_CITATIONS 業界研究引用庫；v2.14 加入 CitationTracker — `[N]` 標記 + `<!-- citations [...] -->` block）
    - services/report-evaluator.ts：報告品質規則式評估（v2.13 新增；5 維度 section_coverage/kb_citation/research/kb_links/alert_coverage；online scoring；v2.18 修正 KB_LINK_RE 格式）
    - services/metrics-parser.ts：純 TS 指標解析（v2.26 新增；Google Sheets CSV fetch + TSV parse + anomaly detect；取代 Python qa_tools.py load-metrics）
    - services/report-llm.ts：純 TS OpenAI 報告生成（v2.26 新增；同 Python 04_generate_report.py 的 system prompt + QA context 建構；取代 Python 依賴）
    - services/pipeline-runner.ts：Python CLI 代理（execPython / execQaTools；v2.18 stdout/stderr 分離，修復 Laminar log 混入 JSON parse bug；v2.26 metrics 端點已不再使用）
  評估工具：
    - scripts/_eval_report.py：週報品質評估（v2.18 新增，Python port，複製 report-evaluator.ts 邏輯；7 維度推送 Laminar `report-quality` group；供 `/generate-report` 存檔後呼叫）
  schemas：
    - qa / search / chat / feedback / report / session / pipeline / synonyms / api-response
  測試：Vitest（39 個 test files，367 tests passing）
  部署：Lambda + Function URL（arm64，~$0/月）/ docker-compose（本地開發）
            ↓ http://localhost:8002 (開發) 或 https://pu4fsreadnjcsqnfuqpyzndm4m0nctua.lambda-url.ap-northeast-1.on.aws/ (生產)

## v2.11 — RAG 迭代改進計畫：Synonym 擴充 + Contextual Embeddings + Reranker（2026-03-05）

### 核心新增

**Phase 0 — 評估指標擴充**
- `scripts/qa_tools.py`：`cmd_eval_retrieval_local()` 新增 precision_at_k、recall_at_k（cat_hit_rate alias）、f1_score
  - 計算：precision = hits / k，recall = hits / total_relevant，f1 = 2×(p×r)/(p+r)
  - 5 個 Laminar score events 直接記錄
- `scripts/_eval_laminar.py`（新建，v2.12 增強）：Laminar 離線 eval run
  - 5 個 evaluator：precision, recall, f1, hit_rate, mrr
  - CLI 參數：`--top-k 5` 改變檢索深度、`--group "keyword-retrieval"` 指定 group（預設固定值，便於趨勢圖）
  - 執行者防護：`safe_executor` try-except 包裝，失敗時回傳空列表
  - NDCG@K 修正：每個 expected_category 只計算一次（防止 NDCG > 1）
  - 並發限制：`concurrency_limit=1` 避免上傳失敗

**Phase 1 — Synonym Dict 擴充**
- `utils/synonym_dict.py`：新增 32 個術語（214 個詞條），覆蓋技術 SEO、關鍵字、UX、GSC 指標
  - 三層合併：METRIC_QUERY_MAP（基礎） < _SUPPLEMENTAL_SYNONYMS（v2.11 新增 31 項） < custom JSON（使用者自訂層，v2.10）
  - KW Hit Rate baseline 提升預期：73% → 78%+

**Phase 2 — Contextual Embeddings** ✅ 已完成（2026-03-06）
- `scripts/_generate_context.py`（新建）：用 Claude Haiku 生成 QA 情境 context → `output/qa_context.json`（**1317 筆**）
  - 每筆 Q&A 生成 2-3 句繁體中文 situating context（來源集合 + 分類 + 核心概念）
  - 離線預生成，無運行時成本；key 為 str(id)（"1"~"1317"）
- `api/src/config.ts`：新增環境變數
  - `ANTHROPIC_API_KEY`：Anthropic API key（用於 reranker）
  - `CONTEXT_EMBEDDING_WEIGHT`：context 加權因子（0–1，**預設 0.6**）
  - `RERANKER_ENABLED`：是否啟用 reranker（`"auto"/"true"/"false"`，預設 `"auto"`）

**Phase 3 — Re-ranking**
- `api/src/services/reranker.ts`（新建）：Claude Haiku reranker service
  - `rerank(candidates, query, topK)` → 重排序、評分、篩選 top-K
  - XML prompt：結構化輸入/輸出
  - 錯誤時自動 fallback 至原始排序
- `api/src/store/search-engine.ts`：新增 over-retrieve 機制
  - `overRetrieveFactor`（預設 3）：初期檢索 K×3 候選，再 rerank
  - `searchOverRetrieve(query, k)`：K×3 檢索 → rerank → top-K
- `api/src/services/rag-chat.ts`：有 ANTHROPIC_API_KEY 時啟用 reranker
  - `const overRetrieve = ANTHROPIC_API_KEY ? (k * overRetrieveFactor) : k`
- `api/src/routes/eval.ts`：新增 POST `/eval/reranking` endpoint
  - 評估 reranker 對搜尋品質的提升幅度
- `api/src/schemas/eval.ts`：新增 `evalRerankingRequestSchema`
- `api/src/tests/services/reranker.test.ts`（新建）：4 個測試
  - 正常 rerank / 空結果 fallback / 錯誤恢復 / score 排序

**前端更新**（vocus-web-ui，branch: feat/admin-seo-insight）
- `apis/seoInsight.api.ts`：EvalRetrievalResponse 擴展
  - 新增欄位：`avg_precision_at_k`、`avg_recall_at_k`、`f1_score`
- `components/admin/seoInsight/EvalMetricsCards.tsx`：從 3 欄擴展至 5 欄
  - 原 3 欄：Hit Rate / MRR / Category Hit Rate
  - 新增 2 欄：Precision@K / F1 Score
  - 色彩編碼：達標（black）/ 接近（gray）/ 未達（light gray）
- `components/admin/seoInsight/useEvalDashboard.ts`：metrics state 新增 3 個欄位
  - `avg_precision_at_k`、`avg_recall_at_k`、`f1_score`

**測試結果（v2.11 snapshot）**：23 個 test files，179 tests passing（v2.12 更新至 24 files，189 tests；v2.13 更新至 25 files，215 tests；v2.14 更新至 216 tests）

**評估基準線（v2.11，20 cases，top-k=5）**：
| 指標 | 數值 | 說明 |
|------|------|------|
| KW Hit Rate | 73% | 同義詞擴充中（目標 78%+） |
| Precision@K | 76% | Reranker 未啟用時的基礎精準度 |
| Recall@K | 80% | 涵蓋率良好 |
| F1 Score | 0.73 | 精確度與涵蓋率平衡指標 |
| MRR | 0.88 | 排名靠後提升空間 |

**預期效益**：
- Precision@K：reranker 啟用後預期 76% → 85%+（Haiku 輕量級重排序）
- Top-1 Hit 提升：通過 over-retrieve + rerank，命中率 → 90%+
- 搜尋延遲：reranker 額外成本 ~200ms（可接受，總 <1s）

**後續優化方向**：
- Phase 4：Fine-tune reranker prompt（基於 A/B 評估結果）
- Phase 5：Cache reranked results（避免重複重排）
- Phase 6：User feedback loop（不相關點擊 → reranker 學習信號）

---

══════════════ Audit Trail（2026-02-28 新增）══════════════

[AuditLogger] utils/audit_logger.py — 零副作用 JSONL 日誌
  fetch 事件：每次 Step 1 執行記錄 session → output/fetch_logs/fetch_YYYY-MM-DD.jsonl
    log_fetch_start → log_fetch_page / log_fetch_skip → log_fetch_complete
  access 事件：每次 API 呼叫記錄 query + returned QA IDs + client IP + top_score
    → output/access_logs/access_YYYY-MM-DD.jsonl
  查詢工具：scripts/audit_trail.py fetch|access|report
            ↓ make audit / make audit-top

══════════════ Observability（2026-03-02 新增，v1.19；2026-03-03 patch）══════════════

[Laminar Tracing] OpenTelemetry-based distributed tracing（optional）
  FastAPI lifespan：Laminar.initialize() @ startup
    → utils/observability.py._patch_openai_instrumentor()：在 Laminar 初始化前修補 lmnr 0.5.x 與 opentelemetry-instrumentation-openai 0.44.0+ 的相容問題
    → 根因：lmnr 0.5.x 傳遞 enrich_token_usage 參數，但 OTel OpenAI Instrumentor 0.44.0 已移除該參數
    → 修補方式：auto-detect native support，若不支援則 monkey-patch `init_openai_instrumentor`，移除 enrich_token_usage kwarg
    → 說明：lmnr 發佈相容版本後，此修補自動失效（no-op）
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
  輸入：output/qa_final.json（1,317 筆，v2.12+，多來源）
  計算：utils/synonym_dict.py（avg 11.09 個同義詞/筆，@lru_cache 執行緒安全）
        utils/freshness.py（avg freshness 0.9076，half_life=540d，min_score=0.5）
        utils/notion_url_map.py（source_file → Notion URL 映射）
        output/access_logs（search_hit_count，需積累 14 天新格式 log）
  輸出：output/qa_enriched.json（含 _enrichment 欄位 + notion_url；已歸檔至 archive_v1/，API 直接讀 qa_final.json）
  store.py load()：直接載入 qa_final.json（qa_enriched.json 已歸檔至 archive_v1/）
  SearchEngine.__init__()：預計算 synonym_boost_vec + freshness_vec（shape=(1317,) numpy）

[LearningStore] utils/learning_store.py — 失敗記憶 JSONL
  record_miss()：rag_chat() top_score < 0.35 時自動記錄
  record_feedback()：POST /api/v1/feedback（helpful / not_relevant）
  get_relevant_learnings()：keyword token 匹配歷史失敗
            ↓ output/learnings.jsonl
```

## 13. API 層架構遷移 — Python FastAPI → TypeScript Hono（v2.3，2026-03-04）

### 遷移背景與決策

**版本演進**：

- v2.0—v2.2：Python FastAPI（單體 8001 port），完整 API 功能
- **v2.3**：開始 TypeScript Hono 並行架構（port 8002）

**決策核心**：

1. **分層遷移**：新功能優先在 Hono 實作，Python 保留作為穩定層
2. **邊界清晰**：Hono 層與 Python Pipeline 共享 output/ 資料；search/chat graceful degradation（有 OpenAI → hybrid/full，無 → keyword/context-only）
3. **測試優先**：Vitest 路由覆蓋（25 個 test files，216 tests），unit + integration
4. **資料相容**：QAStore 完全鏡像，支援 .npy embedding 檔案讀取（optional，無 .npy 時 keyword-only mode）

**實作成果（v2.12 更新）**：

- ~44 個源碼檔案（routes 10、store 5、utils 5、middleware 4、schemas 10、services 4）
- 25 個測試檔案（routes 10 個完整測試套件 + utils 2 + store 4 + middleware 2 + services 3 + observability/laminar-scoring 2 + others 2）
- 9 個完整路由器（qa、search、chat、reports、sessions、feedback、pipeline、synonyms）+ health 檢查（v2.18 移除 eval router）
- 224 tests passing（25 test files）
- NumPy .npy 檔案解析引擎（向量相容）
- 速率限制 middleware（同步 Python layer 配置）
- Local Mode 降級（無 OpenAI 時 keyword-only search + context-only chat）
- CJK 分詞支援（中文 keyword search）
- Python CLI 代理（pipeline 端點透過 subprocess 執行 qa_tools.py）

**技術決策**：

1. **Hono 框架選擇**
   - 輕量（<5KB runtime）vs Express（50KB）
   - Cloudflare Workers + Node.js 雙支援（未來邊緣計算選項）
   - TypeScript 內置，無需額外 transpiler
   - 無狀態設計天然適合無伺服器環境

2. **Zod 驗證**
   - 比 io-ts 更簡潔（TypeScript-first）
   - Runtime schema validation，完全型別安全
   - 與 Hono 深度整合

3. **NumPy 相容讀取**
   - `npy-reader.ts`：實作 .npy 格式解析（IEEE 754 float32/float64）
   - 無 numpy / pandas 依賴（純 JavaScript）
   - 支援多維陣列 reshape（1,317 筆 × 1536 維）

4. **測試策略**
   - Vitest（Vite native test runner）
   - Unit tests：純邏輯（search、store、validators、cjk-tokenizer）
   - Integration tests：mocked external calls（OpenAI、Python CLI subprocess）
   - Router tests：完整 HTTP 請求/回應循環（含 Local Mode 降級測試）
   - 100% endpoint 覆蓋（10 個 routers × ~2-6 tests per endpoint，v2.14 共 216 tests）

**向下相容**：

- Python API（port 8001）保持不變，允許 2-4 週過渡期
- 前端同時支援兩個 port（通過 .env 開關）
- QA ID 驗證規則完全同步（16-char hex）
- Response envelope 格式一致（data / error / meta）

**遷移路徑**：

```
Phase 1（現在）：Hono 並行運行 (port 8002)
  ↓ 前端測試、性能驗證 (1-2 週)
Phase 2：逐步遷移流量（10% → 50% → 100%）
  ↓ 監控指標、錯誤率、延遲
Phase 3（4 週後）：下線 Python API (port 8001)
  ↓ 專注 Hono 優化與擴展
```

---

## 14. QA ID 遷移與週報 API（v2.2，2026-03-04）

### QA ID 從 Sequential Int 遷移至 Stable UUID（v2.2）

**決策**：QAItem.id 從 sequential int 變更為 16 字元 hex string（stable_id），保留原始 seq 欄位供顯示用。

**背景**：

- Sequential int 在 append-only 知識庫中容易引發歧義（重新排序、去重時改變）
- stable_id 是 qa_final.json 產生時的 SHA256(question+answer) 截短 16 字元，保證不可變性與唯一性
- 影響範圍：API endpoint path、URL validation、audit log 記錄

**實作細節**：

1. **數據層（QAItem 定義）** — `/app/core/store.py`

   ```python
   @dataclass
   class QAItem:
       id: str           # stable_id，16-char hex，primary key
       seq: int          # 原始 sequential number，僅供顯示
       ...               # 其他欄位不變
   ```

2. **API Schema 更新** — `/app/routers/qa.py`
   - QAResponse.id: str（16-char hex）
   - GET `/api/v1/qa/{id}` 改用 regex validation：`^[0-9a-f]{16}$`
   - QAListResponse 仍支援分頁 & 篩選

3. **Audit Trail 更新** — `/utils/audit_logger.py`
   - `log_access()` 的 returned_ids 參數改為 `list[str]`（16-char hex）
   - `/scripts/audit_trail.py` 查詢語句不變，自動適配

4. **API 回應格式** — 保持向下相容
   - QAResponse 同時包含 id（stable_id）和 seq（sequential number）
   - 客戶端可用任一欄位判讀，建議優先使用 id

**向下相容**：

- Q&A 搜尋/列表 endpoint 變更最小（只需調整驗證規則）
- 沒有 breaking change（seq 欄位始終存在）
- 測試套件已全數更新（247 passing）

**優勢**：

- stable_id 保證長期穩定性，不受 pipeline 重跑影響
- 便於外部系統建置永久參考（如知識庫外部連結、行銷素材引用）
- 提升 API 安全性（id 無法通過順序猜測下一個）

---

### 週報 REST API（新增 v2.2，現已在 Hono 實作）

**新增三個 endpoint** — Python: `/app/routers/reports.py` / TypeScript: `api/src/routes/reports.ts`

1. **GET /api/v1/reports** — 列出所有週報（newest first）

   ```json
   {
     "data": {
       "items": [
         {"date": "20260304", "filename": "report_20260304.md", "size_bytes": 12345},
         ...
       ],
       "total": 42
     }
   }
   ```

   - 速率限制：60/minute
   - 用途：前端「週報列表」頁面展示

2. **GET /api/v1/reports/{date}** — 取得單篇週報（Markdown 原文）

   ```json
   {
     "data": {
       "date": "20260304",
       "filename": "report_20260304.md",
       "content": "# SEO 週報 2026-03-04\n...",
       "size_bytes": 12345
     }
   }
   ```

   - date 格式：YYYYMMDD（regex validated）
   - 404 if not found
   - 用途：前端「週報詳情」頁面展示 Markdown 內容

3. **POST /api/v1/reports/generate** — 觸發週報生成（4 種模式）

   **Request Schema** 支援 3 種路由模式：
   ```json
   {
     "snapshot_id": "20260306-103000",  // 本地/OpenAI 模式：指標快照 ID
     "use_openai": true,               // OpenAI 模式開關
     "metrics_url": "...",             // Legacy URL 模式
     "weeks": 4,                       // Legacy URL 模式參數
     "situation_analysis": "...",      // hybrid 模式：5 維度 LLM 分析注入
     "traffic_analysis": "...",
     "technical_analysis": "...",
     "intent_analysis": "...",
     "action_analysis": "..."
   }
   ```

   回應：
   ```json
   {
     "data": {
       "date": "20260304_a1b2c3d4",
       "filename": "report_20260304_a1b2c3d4.md",
       "size_bytes": 12345,
       "cache_hit": false
     }
   }
   ```
   > 注意：`generation_mode` 不在 API response 中，而是記錄在報告檔案內的 `<!-- report_meta -->` HTML comment。

   - 速率限制：5/minute（計算密集）
   - Timeout：120 秒
   - 快取機制：基於 frontmatter + metrics 內容 hash，避免時間戳造成 cache miss

   **4 種 Report Generation Mode**：

   | 模式 | 驅動引擎 | 使用場景 | 參數 | 需要 API Key |
   |------|--------|--------|------|-----------|
   | `template` | 本地模板（Markdown render） | 靜態內容展示 | 無 | 否 |
   | `hybrid` | 本地模板 + LLM 5 維度分析 | 結合固定內容與 AI 洞見 | 無 | 否 |
   | `openai` | TypeScript `report-llm.ts` + OpenAI API（v2.26 從 Python 移植） | 高品質 6 維度 ECC 分析 | `snapshot_id` + `use_openai: true` | 是 |
   | `claude-code` | Claude Code 語意推理（Interactive 模式） | 開發/本地驗證 | `/generate-report` 指令 | 否 |

   **OpenAI 模式詳解**（v2.26+，純 TypeScript）：
   - 前端提交 `snapshot_id` + `use_openai: true`
   - API 呼叫 `generateReportLlm(snapshotMetrics, weeks)`（`services/report-llm.ts`）
   - 純 TypeScript 實作：從 Supabase/本地讀取指標快照，建構 QA context，呼叫 OpenAI API
   - System prompt：ECC 6 維度框架（Situation Snapshot + Health Score + CTR 四象限分析 + 研究引用 + KB 連結 + 行動建議）
   - 回傳 markdown + `report_meta` JSON comment（`<!-- report_meta {"generation_mode":"openai","model":"gpt-5.2",...} -->`）
   - 前端 `cache_hit` 欄位：指示是否命中快取

   **Report Metadata 格式**（附加於報告尾部）：
   ```html
   <!-- report_meta {
     "weeks": 1,
     "generated_at": "2026-03-06T10:30:00Z",
     "generation_mode": "openai",
     "generation_label": "OpenAI gpt-5.2 生成",
     "model": "gpt-5.2"
   } -->
   ```

**架構決策**：

- 週報儲存位置：`config.OUTPUT_DIR`（預設 `./output/`）
- 檔案格式：`report_YYYYMMDD.md`（immutable）
- API 層路由邏輯：區分 OpenAI / 本地 / Legacy URL 三路，3 路均落地同一檔案（檔名基於生成日期）
- `generation_mode` metadata：記錄於 HTML comment，便於前端顯示和快取策略
- Frontmatter strip：hash 計算前清除 `---...\n`，避免時間戳造成快取失效

**測試覆蓋**：

- 目錄掃描、日期驗證、超時處理、錯誤回應
- 已整合 conftest.py fixture `mock_output_dir`

---

### 模型選擇邏輯

```
需要理解複雜文本、推理、生成高品質輸出
  → gpt-5.2（主力模型，OPENAI_MODEL env var）
  → 用於：Q&A 萃取、Q&A 合併、週報生成、LLM Judge

需要即時對話回應（RAG Chat）
  → gpt-5.2（預設，CHAT_MODEL env var，可降至 gpt-5-mini 節省成本）
  → 用於：POST /chat endpoint（v2.22 獨立設定）

需要結構化輸出、分類、簡單判斷
  → gpt-5-mini（省成本，CLASSIFY_MODEL env var）
  → 用於：Q&A 分類、Retrieval 相關性判斷

需要計算語意向量
  → text-embedding-3-small（極便宜，只做向量計算）
  → 用於：去重、Step 4/5 語意搜尋
```

> **v2.22 更新**：`CHAT_MODEL` 與 `OPENAI_MODEL` 解耦，允許以不同成本策略配置萃取品質（高）vs 對話速度（低）。

### 當前品質基準線（最新：2026-03-02，v2.0+cjk，CJK N-gram + Synonym 修復後）

| 指標                    | v1.0 初始 baseline | v2.0+cjk 最新數值 | 狀態                                               |
| ----------------------- | ------------------ | ----------------- | -------------------------------------------------- |
| **Relevance**           | 4.65               | **5.00** / 5      | ✅ 提升至滿分                                      |
| **Accuracy**            | 3.80               | **4.30** / 5      | ✅ 大幅提升                                        |
| **Completeness**        | 3.70               | **3.95** / 5      | ✅ 達標（目標 3.8）                                |
| **Granularity**         | 4.65               | **4.75** / 5      | ✅ 達標                                            |
| Category 正確率         | 75%                | 80%               | ✅ 提升                                            |
| Retrieval MRR           | 0.79               | 0.87              | ✅ 大幅提升                                        |
| LLM Top-1 Precision     | 100%               | 80%               | ✅ 符合預期（20 案例評估）                         |
| **KW Hit Rate（eval）** | 54%                | **74%** ✅        | +20pp（含 9pp enrichment delta）、目標 85% 差 11pp |
| freshness_rank_quality  | —                  | **1.0**           | ✅ 完全保留排名序序                                |
| synonym_coverage        | —                  | **1.0**           | ✅ 1,317 筆全覆蓋                                  |

> **v2.0+cjk 評估完成（2026-03-02）**：
>
> - 知識庫規模：717 筆（v1.0）→ 655 筆（v2.0，去重+防幻覺）→ 1,317 筆（v2.12，多來源知識庫）
> - Embeddings 重建：(1317, 1536) numpy array（v2.12 重建）
> - 生成維度（4 項）基於 20 案例 golden set，Claude Code 本地評估
> - Retrieval 維度基於 307 案例 golden retrieval set
> - CJK n-gram 修復後 KW Hit Rate 回升：65% → 74%（+9pp vs baseline）

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

> 架構圖（最新 v2.7，Hono API 主架構）維護於 [06b-architecture-diagram.md](./06b-architecture-diagram.md)

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

### E. FastAPI + In-Memory QAStore（Supabase-ready 抽象）

**決策**：啟動時載入全量 1,317 筆 QA + 1317×1536 embedding matrix 到 module-level singleton，FastAPI lifespan 管理。所有資料存取透過 `QAStore` 抽象層，為 Phase 2 Supabase 遷移預留介面。

**學術 / 業界支撐**：

- **FAISS**（Johnson et al., 2019, _IEEE Trans. on Big Data_）：小規模向量（<100K）in-memory brute-force search 延遲 < 1ms，不需要 ANN 索引。1,317 筆完全在此範圍內。
- **12-Factor App Factor VI — Stateless processes**（Wiggins, 2011, Heroku）：唯讀查詢層用 in-memory 是合理優化，不違反無狀態原則。
- **Offline Feature Store + Online Serving**（Feast, 2019, Google/Tecton）：離線 pipeline 產出特徵 → 物化到 online store → API 讀取。與 Pipeline → qa_final.json → API 模式完全對應。
- **Repository Pattern**（Fowler, 2003, _PoEAA_）：`QAStore` 封裝資料存取邏輯，業務層透過 `search()` / `hybrid_search()` / `list_qa()` / `get_qa_item()` 介面操作，遷移至不同 backend 時 router 層零修改。

**評估**：符合當前規模（4.3MB）。

**遷移路徑（Phase 2）**：`QAStore` 內部實作從檔案載入切換至 Supabase client，schema 預規劃見 `research/07-deployment.md` §21.4。資料透過 API 有即時更新需求，Supabase 為最終目標。

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

- ~~向量資料庫（655 筆，numpy 已足夠快）~~ → Phase 2 將遷移至 Supabase pgvector（因 API 有即時更新需求）
- 模型 Fine-tuning（學習機制 + 人工回饋更靈活）
- Real-time Schema Introspection（schema 穩定，無必要）

### 架構圖演進

**現狀（v2.0）**：

```
qa_final.json（1,317 筆）
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

| 模組                | 檔案                        | 行數        | 責任層級        |
| ------------------- | --------------------------- | ----------- | --------------- |
| **L1 同義詞**       | `utils/synonym_dict.py`     | ~120        | Query Patterns  |
| **L4 時效性**       | `utils/freshness.py`        | ~60         | Runtime Context |
| **L3 失敗學習**     | `utils/learning_store.py`   | ~150        | Learnings       |
| **L4 使用聚合**     | `utils/usage_aggregator.py` | ~100        | Runtime Context |
| **Enrichment 主控** | `scripts/enrich_qa.py`      | ~200        | Pipeline Step   |
| **回饋路徑**        | `app/routers/feedback.py`   | ~80         | Annotations     |
| **合計新增**        |                             | **~710 行** |                 |

### 修改模組清單

| 檔案                            | 修改項目                                                    | 向下相容  |
| ------------------------------- | ----------------------------------------------------------- | --------- |
| `utils/search_engine.py`        | `_hybrid_scores()` 新增 4 個加權因子                        | ✅        |
| `app/core/store.py`             | 優先載入 qa_enriched.json，fallback qa_final.json           | ✅        |
| `scripts/04_generate_report.py` | Step 4 記錄 learnings（top_score < 0.35）                   | ✅ 副作用 |
| `app/core/chat.py`              | 整合 learning + staleness 警示                              | ✅ 副作用 |
| `config.py`                     | 新增 5 常數（SYNONYM_BOOST 等）                             | ✅        |
| `qa_tools.py`                   | 新增子命令：analyze-access、annotate-category、compare-eval | ✅        |
| `Makefile`                      | 新增 targets：enrich-qa、pipeline-v2、eval-compare          | ✅        |

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

| 指標          | 目前（v2.0） | 目標（v1.17） | 機制          |
| ------------- | ------------ | ------------- | ------------- |
| KW Hit Rate   | 78%          | 85%+          | L1 + L3 + L4  |
| Accuracy      | 3.95         | 4.2+          | L2 + L4       |
| Completeness  | 3.85         | 4.1+          | L1 + L3       |
| Category Acc. | 68%          | 80%+          | P2-B 人工回饋 |
| 搜尋延遲      | 50ms         | 30ms          | 預計算 + 緩存 |

### 後續研究方向（v2.0+）

- **Query Understanding 進階**：從 zero-hit queries 自動提取新同義詞
- **Active Learning**：自動篩選最具信息量的樣本進行人工標記
- **LLM-based Reranking**：top-5 結果上的語意再排序（成本 vs 收益評估）
- **多步 Agent 推理**：支援複雜、多條件查詢（L6 層，後期優先）

詳見完整實作計畫：`plans/in-progress/multi-layer-context.md`。

---

## v2.8 — ECC 全面安全審查修復與 Model Provenance Pipeline（2026-03-05）

### 核心新增

**Part A: 安全性與代碼品質加固**

所有層級執行 ECC（everything-claude-code）全面審查與修復：

1. **SSRF 防護加強** — `01b_fetch_medium.py`
   - 新增 `_validate_medium_url()` 函數
   - Domain allowlist：medium.com / genehong.medium.com
   - 所有抓取均通過此驗證，防止開放重定向與 SSRF 攻擊

2. **Logging 統一化** — 3 個 Fetcher
   - `01b_fetch_medium.py`、`01c_fetch_ithelp.py`、`01d_fetch_google_cases.py` 從 `print()` 改為 `logging` module
   - 支援審計追蹤與調試等級控制

3. **Exception 分級** — 所有 Fetcher
   - HTTPError（網路問題）/ ValueError（資料驗證） → logger.warning
   - Exception（未預期） → logger.exception
   - 提升錯誤診斷品質與故障復原

4. **不可變性強化** — Pipeline 核心腳本
   - `02_extract_qa.py`：dict unpacking 取代 in-place mutation
   - `03_dedupe_classify.py`：dict 複製而非直接修改

5. **Schema 驗證強化** — TypeScript API
   - `pipeline.ts` 新增 SAFE*MD_FILENAME regex：`^[a-zA-Z0-9.*\u4e00-\u9fff-]+\.md$`（含中文字元）
   - `metricsRequestSchema` 新增 URL format + regex validation
   - `readMeetingsIndex()` 改用 Zod schema 驗證取代 bare type assertion

6. **Path Traversal 防護** — Eval 路由
   - `eval.ts` POST /save handler 用 `resolve() + startsWith()` 替代正則表達式
   - 防止「..」轉義攻擊（e.g., `..%2F..` 超出 output/evals/ 目錄）

7. **XSS 防護** — HTML 轉換器
   - `html_to_markdown.py` strip dangerous HTML tags（script/style/iframe）與 attributes（onclick/onerror）
   - 確保擷取文章時無惡意程式碼注入

8. **文件鎖定機制** — Execution Log
   - `execution_log.py` 新增 `fcntl.flock()`（UNIX） + symlink guard
   - 防止 Claude Code 並行執行時 log 檔損毀

9. **並行化優化** — Pipeline API
   - `pipeline.ts` POST /fetch-articles 改為 `Promise.all([fetch_medium, fetch_ithelp, fetch_google])`
   - 3 個 fetcher 並行執行，預期總時間減半

10. **Observability 修復** — 防止前向引用錯誤
    - `observability.py` contextlib import 改為全局，防止動態載入時 NameError

**Part B: Model Provenance Pipeline（模型追蹤層）**

新增跨模型品質對比的基礎架構：

1. **QA Item 元數據擴展**
   - `extraction_model`：萃取使用的模型名稱（e.g., "gpt-5.2"）
   - `extraction_timestamp`：萃取時間戳，便於時序追蹤

2. **Cache Key 模型感知**
   - `pipeline_cache.py` cache key = `SHA256(model::content)`
   - 同一內容用不同模型處理會產生不同快取項，避免迴避

3. **Eval Schema 擴展**
   - Python + TypeScript eval 結構化定義新增 optional `model` 欄位
   - 支援評估特定模型的輸出品質

4. **Cross-Model A/B 評估命令**
   - 新增 `.claude/commands/evaluate-model-ab.md`
   - 提供標準化工作流：抽樣 → 評估 → 對比 → 報告

**預期效益**：

- 安全性：覆蓋 OWASP Top 10（SSRF/Path Traversal/XSS）中的 3 項關鍵風險
- 代碼品質：logging 統一、exception 分級、不可變性強化
- Model Traceability：未來可溯源任一答案由哪個模型生成、何時生成
- A/B 測試：支援模型升級前後的品質量化對比

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

## v2.12 — Semantic Reranker Evaluation 與離線 Laminar Eval（2026-03-05）

### 新增評估腳本架構

#### 1. **`scripts/_eval_laminar.py`** — Laminar 正式 Eval Run

**目的**：將 golden_retrieval.json 的 20 筆 cases 推送至 Laminar Dashboard 作為離線評估資料集。

**主要特性**：
- Golden set：`output/evals/golden_retrieval.json`（20 cases）
- 評估模式：keyword-only baseline（純關鍵字搜尋）
- 評估器數量：5 個（precision、recall、f1、hit_rate、mrr）
- 資料來源：優先 `qa_enriched.json`，降級至 `qa_final.json`
- 並發策略：`concurrency_limit=1`（避免 Laminar SDK 上傳失敗）
- Group 名稱：固定 `"keyword-retrieval"`（所有 run 納入同一組，利於 Dashboard 折線圖）

**使用方式**：
```bash
python scripts/_eval_laminar.py              # 使用預設 group
python scripts/_eval_laminar.py --top-k 10  # 改變 top-K
python scripts/_eval_laminar.py --group custom_name  # 自訂 group
```

**實作細節**：
- Executor：`_keyword_search()` 執行關鍵字搜尋，回傳精簡欄位（id/category/question[:120]）
- Safe executor：try-except 防護，搜尋失敗回傳空列表而非拋例外
- NDCG@K bug 修正：每個 expected_category 只計算第一次命中，確保 NDCG ≤ 1
- 連接 Laminar 後自動推送評估結果至 Dashboard，可追蹤歷史趨勢

#### 2. **`api/scripts/eval-semantic.ts`** — 語意 + Reranker 對比評估

**目的**：量化三種檢索模式的品質差異。

**評估三種模式**：
1. **Keyword-only**（baseline）— 純關鍵字搜尋，無語意評估
2. **Hybrid search** — embedding + keyword boost + synonym + freshness
3. **Hybrid + Rerank** — over-retrieve K×3 → Claude haiku reranker → top-K

**主要特性**：
- Golden set：`output/evals/golden_retrieval.json`（20 cases）
- 評估指標：Precision@K、Recall@K、F1、Hit Rate、MRR（category level）
- Reranker 模型：Claude haiku-4-5-20251001
- Over-retrieve 因子：3×（給 reranker 足夠池子）
- 支援參數：`--top-k`（預設 5）、`--mode`（keyword/hybrid/rerank/all，預設 all）、`--json`（JSON 輸出）

**使用方式**：
```bash
cd api && npx tsx scripts/eval-semantic.ts              # 三模式對比
cd api && npx tsx scripts/eval-semantic.ts --top-k 3   # 改變 top-K
cd api && npx tsx scripts/eval-semantic.ts --json      # JSON 輸出
make eval-semantic                                      # Makefile wrapper
make eval-semantic-k3                                   # top-k=3 版本
```

**評估結果儲存**：輸出至 stdout（可重導向至檔案或 Laminar Dashboard），包含：
- 聚合指標（5 個）
- 每個 case 的詳細分析（query、expected categories、retrieved categories、四項指標）

**實作細節**：
- Store initialization：`new QAStore()` 載入 qa_final.json 與 embeddings
- Reranker integration：動態 import 防護（SDK 不存在時自動 fallback）
- Metric computation：四層嵌套計算，確保計算的準確性（category-level 而非 QA-level）

#### 3. **Makefile 新增 targets（v2.12）**

```makefile
.PHONY: eval-semantic
eval-semantic: ## Semantic + Reranker Retrieval Eval（比較 keyword/hybrid/rerank 三種模式）
	cd api && npx tsx scripts/eval-semantic.ts

.PHONY: eval-semantic-k3
eval-semantic-k3: ## 同上，top-k=3
	cd api && npx tsx scripts/eval-semantic.ts --top-k 3

.PHONY: eval-laminar
eval-laminar: ## Laminar 正式 Eval Run（keyword baseline，推送至 Dashboard）
	$(PYTHON) scripts/_eval_laminar.py
```

### Laminar Evaluators（v2.13，4 層架構）

#### Layer 2 — keyword-retrieval group（8 evaluators）

| 評估器 | 計算方式 | 學術依據 |
|--------|---------|---------|
| `precision_evaluator` | `|relevant ∩ retrieved| / K` | IR 標準（Voorhees）|
| `recall_evaluator` | `|expected ∩ retrieved| / len(expected)` | IR 標準 |
| `f1_evaluator` | `2×P×R/(P+R)` | IR 標準 |
| `hit_rate_evaluator` | `1.0 if any match else 0.0` | TREC |
| `mrr_evaluator` | `1 / rank_of_first_match` | TREC |
| `ndcg_at_k_evaluator` | `DCG / IDCG`（graded relevance）| Jarvelin & Kekalainen (2002) |
| `top1_category_match_evaluator` | `1.0 if output[0].category in expected else 0.0` | 本專案 |
| `top5_category_coverage_evaluator` | ≡ `recall_evaluator`（語意更清楚）| 本專案 |

#### Layer 3 — retrieval-enhancement group（2 evaluators）

| 評估器 | 說明 |
|--------|------|
| `kw_hit_rate_with_synonyms_evaluator` | 同義詞展開 executor 後的 hit rate（vs baseline）|
| `synonym_coverage_evaluator` | expected_keywords 有多少比例有 synonym 覆蓋 |

#### Layer 1 — data-quality group（`scripts/_eval_data_quality.py`）

| 評估器 | 合格線 |
|--------|--------|
| `qa_count_in_range` | [100, 2000] |
| `avg_confidence` | ≥ 0.80 |
| `keyword_coverage` | ≥ 0.85（≥3 keywords per QA）|
| `no_admin_content` | 1.0（無污染）|

#### Layer 4 — generation-quality group（`scripts/_push_laminar_score.py`）

由 Claude Code as Judge slash commands 執行後，用 `_push_laminar_score.py` 推送：
- `faithfulness`（RAGAS Faithfulness，`/evaluate-faithfulness-local`）
- `context_precision`（RAGAS Context Precision，`/evaluate-context-precision-local`）

### Observability 擴充（v2.12）

- `score_event("precision_at_k", value)`
- `score_event("recall_at_k", value)`
- `score_event("f1_score", value)`
- `score_event("hit_rate", value)`
- `score_event("mrr", value)`

每次評估執行後自動發送至 Laminar Dashboard，可在 Evaluations 頁面查看歷史趨勢。

### 評估結果基準線（v2.12，2026-03-05）

**三模式對比（20 golden cases，top-k=5）**：

| 模式 | Precision | Recall | F1 | Hit Rate | MRR |
|------|-----------|--------|-----|----------|-----|
| Keyword（Python 手動）| 0.810 | 0.800 | 0.768 | 1.0 | 0.938 |
| Keyword（TS eval-semantic.ts）| 0.700 | — | — | — | — |
| Keyword + Claude Rerank | **0.950** | **0.825** | **0.861** | 1.0 | **1.0** |
| Delta vs Python baseline | **+14pp** | **+2.5pp** | **+9.3pp** | — | **+6.2pp** |

**主要發現**：
- Precision +14pp：Reranker 有效過濾語意不相關的結果
- MRR 達到 1.0：第一筆結果 100% 正確，排序最優化
- Recall 小幅提升：受 over-retrieve pool 限制

### 依賴更新

```
lmnr[openai]>=0.5.0                                        # +new
opentelemetry-semantic-conventions-ai>=0.4.13,<0.4.14    # +new, pinned
anthropic>=0.39.0                                         # +new (reranker SDK)
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

---

## v2.25（2026-03-06）— Architecture & Security Hardening

**核心亮點**：
- Security: SSRF whitelist、auth fail-fast (production 503)、HTTP security headers、session UUID validation
- Refactor: qa-filter.ts 共用模組（消除 200+ 行重複）、itemToSource 共用化
- Fix: SupabaseQAStore.listQa mutation bug（immutable sort）
- Cleanup: 刪除 legacy Python FastAPI（app/ 17 files + Dockerfile + 8 tests + CI workflow）
- Supabase: Migrations 004-007 補齊 + IVFFlat probes=5 tuning
- Test: 224→353 tests, 25→38 files, 63%→80% coverage
- Python: 65 處 print→logging 替換（3 files）

**詳細 Changelog**：見 [06a-architecture-changelog.md](./06a-architecture-changelog.md)
