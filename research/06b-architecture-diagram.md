# 本專案架構圖（Mermaid）

> 屬於 [research/](./README.md)，從 [06-project-architecture.md](./06-project-architecture.md) 拆出。
> 每次架構調整後依 [SOP](#更新架構圖的-sop) 更新此圖，並在 [06a-architecture-changelog.md](./06a-architecture-changelog.md) 新增一行。

---

## 架構圖（最新：v2.7，2026-03-05）

```mermaid
flowchart TD
    N[Notion API<br/>87 份會議 2023-2026] --> S1
    MED_SRC["Medium RSS<br/>genehong.medium.com"] --> S1M
    ITH_SRC["iThome 鐵人賽<br/>30 篇 SC KPI 系列"] --> S1I
    GC_SRC["Google Search Central<br/>Case Studies (12 篇)"] --> S1G

    subgraph Pipeline["離線知識蒸餾 Pipeline"]
        PF[utils/pipeline_deps.py<br/>preflight_check<br/>StepDependency 宣告式檢查] -.->|每個 Script 啟動前| S1
        PF -.-> S2
        PF -.-> S3
        PF -.-> S4
        PF -.-> S5
        S1[Step 1a: fetch_notion.py<br/>增量擷取 + Markdown 轉換] --> MD[raw_data/markdown/*.md]
        S1M[Step 1b: fetch_medium.py<br/>RSS → Markdown] --> MD_MED[raw_data/medium_markdown/*.md]
        S1I[Step 1c: fetch_ithelp.py<br/>HTML → Markdown] --> MD_ITH[raw_data/ithelp_markdown/*.md]
        S1G[Step 1d: fetch_google_cases.py<br/>HTML → Markdown] --> MD_GC[raw_data/google_cases_markdown/*.md]
        MD --> S2[Step 2: extract_qa.py<br/>gpt-5.2 萃取 Q&A<br/>+ Attribution Tag 補充<br/>DIR_COLLECTION_MAP 自動偵測來源]
        MD_MED --> S2
        MD_ITH --> S2
        MD_GC --> S2
        S2 --> RAW[output/qa_all_raw.json<br/>source_type + source_collection 標記]
        RAW --> S3[Step 3: dedupe_classify.py<br/>Collection-Scoped Dedup<br/>各 collection 內部獨立去重]
        S3 --> QA[output/qa_final.json<br/>655+ 筆 + 10 分類]
        S3 --> EMB[output/qa_embeddings.npy<br/>跨 collection 統一向量]
    end

    subgraph Eval["評估層（Claude Code 本地評估 + LLM Judge）"]
        GoldenSets["eval/ Golden Sets<br/>extraction(5) dedup(40) qa(50)<br/>report(5) retrieval(307) seo_analysis"]
        QA --> S5[Step 5: evaluate.py<br/>LLM-as-Judge<br/>4 維度評估 + 本地選項]
        EMB --> S5
        GoldenSets --> S5
        S5 --> ER["eval_report.json<br/>Completeness 3.95<br/>+ eval_local_*.json<br/>(Claude Code 評分)"]
    end

    subgraph RAG_Search["RAG和Hybrid Search v1.5"]
        GS[Google Sheets 指標 TSV] --> S4[Step 4: generate_report.py<br/>異常偵測 Hybrid Search RAG]
        QA --> S4
        EMB --> S4
        SE["SearchEngine v1.5<br/>compute_keyword_boost"] -.->|kw match| S4
        S4 --> RPT[report_YYYYMMDD.md]
    end

    subgraph Frontend["Frontend（vocus-admin-dev，Next.js，port 3000）"]
        FE["6 頁 SPA<br/>SEO 知識庫 / QA 詳情 / RAG 問答<br/>SEO 週報 / Pipeline / Q&A 評估"]
        FE --> FEHOOK["Custom Hooks<br/>useQAFilters / useEvalDashboard"]
        FE --> FECOMP["Components<br/>ChatMessage（null content 支援）<br/>EvalMetricsCards / EvalProviderComparison<br/>EvalSampleTable / EvalSaveForm<br/>PipelineMetrics / QAFilterToolbar"]
        FECOMP -->|context-only 模式| FEFB["Context-Only Badge<br/>+ SourcesList auto-expand"]
    end

    FE -->|"seoInsight.api.ts<br/>seoFetch（port 8002）"| HAPI

    subgraph Hono_API["API Layer v2.7（Hono + TypeScript，port 8002，Local Mode + Laminar）"]
        QA --> HAPI["SEO Insight API<br/>Hono + TypeScript<br/>QAStore（npy-reader 向量解析，embedding optional）"]
        EMB -.->|"optional（Local Mode 不需要）"| HAPI
        SE -.->|hybrid_search / keywordOnlySearch| HAPI
        HAPI --> HMID["middleware/<br/>auth.ts（X-API-Key）<br/>rate-limit.ts（chat:20 search/qa:60 reports/gen:5 eval:60/min）<br/>cors.ts + error-handler.ts"]
        HMID --> HEP["9 個 Router + health<br/>qa.ts — GET /qa, /qa/categories, /qa/{id}（hex+int）<br/>search.ts — POST /search（mode: hybrid|keyword）<br/>chat.ts — POST /chat（mode: full|context-only）<br/>reports.ts — GET/POST /reports<br/>sessions.ts — CRUD /sessions + messages（context-only fallback）<br/>feedback.ts — POST /feedback<br/>pipeline.ts — GET status/meetings/unprocessed/logs, POST fetch/fetch-articles/extract-qa/dedupe-classify/metrics<br/>eval.ts — POST sample/retrieval/save, GET compare"]
        HEP --> HENV["ApiResponse[T]<br/>Zod schema validation<br/>data / error / meta"]
        HEP -->|not_relevant / helpful| LS
        HEP -->|"pipeline/eval proxy"| QT
        HAPI --> HSTORE["store/<br/>qa-store.ts（QAStore singleton，embedding optional）<br/>search-engine.ts（hybrid + keyword boost + keywordOnlySearch）<br/>session-store.ts（FileSessionStore）<br/>learning-store.ts"]
        HAPI --> HUTIL["utils/<br/>npy-reader.ts（NumPy .npy 解析）<br/>cosine-similarity.ts（Float32Array）<br/>keyword-boost.ts（4 層匹配）<br/>sanitize.ts（HTML escape 防 XSS）<br/>cjk-tokenizer.ts（CJK 分詞 2-gram）<br/>mode-detect.ts（hasOpenAI 偵測）"]
        HAPI --> HSVC["services/<br/>embedding.ts（OpenAI wrapper）<br/>rag-chat.ts（RAG 問答）<br/>pipeline-runner.ts（Python CLI 代理）"]
        HAPI --> HSCHEMA["schemas/ 9 個<br/>Zod runtime validation<br/>qa / search / chat / feedback<br/>report / session / pipeline / eval<br/>api-response"]
    end

    subgraph Legacy_API["Python API Layer（FastAPI，port 8001，legacy — 預計下線）"]
        QA -.-> API["FastAPI QAStore singleton<br/>app/ 目錄<br/>277 tests passing"]
        EMB -.-> API
        API -.-> EP["15 endpoints<br/>同 Hono 功能對等"]
    end

    subgraph AuditTrail["Audit Trail"]
        S1 -->|fetch events| AL["audit_logger.py<br/>output/fetch_logs/"]
        HEP -->|access events| AL2["output/access_logs/<br/>JSONL per day"]
        AL --> ATQ["audit_trail.py<br/>query tool"]
        AL2 --> ATQ
    end

    subgraph CacheLayer["Layer 1 Content-Addressed Cache v1.6"]
        S2 <-->|extraction cache| PC["pipeline_cache.py<br/>output/.cache/{ns}/{h[:2]}/{h}.json<br/>namespace: extraction/embedding/classify/merge/report"]
        S3 <-->|embed/classify/merge cache| PC
        S4 <-->|report cache| PC
        S3 -->|record_artifact| PV["pipeline_version.py v1.19<br/>STEP_NAMES + resolve_step()<br/>label_version() + register_existing_file()<br/>output/.versions/registry.json"]
        S4 -->|record_artifact| PV
    end

    subgraph MultiLayerContext["Multi-Layer Context v1.19（離線 Enrichment）"]
        QA --> ENRICH["scripts/enrich_qa.py<br/>make enrich<br/>冪等 / 無 LLM / atomic write"]
        SYN["utils/synonym_dict.py<br/>METRIC_QUERY_MAP 衍生<br/>@lru_cache(maxsize=1)"] --> ENRICH
        FRESH["utils/freshness.py<br/>exp(-0.693×age/540d)<br/>min_score=0.5"] --> ENRICH
        ENRICH --> QAE["output/qa_enriched.json<br/>655 筆 + _enrichment<br/>avg_synonyms=11.09<br/>avg_freshness=0.9076"]
        QAE -->|優先載入 fallback qa_final| SE
        QAE -->|synonym_boost_vec<br/>freshness_vec 預計算| SE
        LS["utils/learning_store.py<br/>output/learnings.jsonl<br/>record_miss / record_feedback<br/>get_relevant_learnings"] -.->|query learnings| SE
    end

    subgraph Observability["可觀測性（三路整合：Python CLI + Hono API + 執行日誌）"]
        S2 -->|"@observe + init_laminar"| LM["Laminar SDK<br/>Python v0.5 + JS v0.8<br/>OpenTelemetry-based"]
        S3 -->|"@observe + init_laminar"| LM
        S4 -->|"@observe + init_laminar"| LM
        S5 -->|"@observe + init_laminar"| LM
        QT["qa_tools.py 6 subcommands<br/>@observe + flush_laminar<br/>+ execution_log.jsonl"] -->|"search/merge_qa/etc"| LM
        QT -->|"log_execution()"| ELOG["output/execution_log.jsonl<br/>command/args/duration/result"]
        HAPI -->|"initLaminar + observe"| LM
        HSVC -->|"observe(rag_chat)<br/>observe(get_embedding)"| LM
        EC["evals/eval_chat.py<br/>Laminar.initialize()"] -->|"lmnr eval"| LM
        LM --> LD["Laminar Dashboard<br/>Traces + Spans + Events"]
        OS -.->|"score_event"| LM
    end

    subgraph OfflineEvals["離線評估"]
        GoldenSets2["eval/ Golden Sets<br/>retrieval(307) extraction(5)<br/>chat(10) seo_analysis"]
        GoldenSets2 --> EvalR["evals/eval_retrieval.py<br/>keyword_hit_rate<br/>category_match"]
        GoldenSets2 --> EvalE["evals/eval_extraction.py<br/>qa_count<br/>keyword_coverage"]
        GoldenSets2 --> EvalC["evals/eval_chat.py<br/>answer_length<br/>has_sources"]
        GoldenSets2 --> EvalEnrich["evals/eval_enrichment.py v1.19<br/>kw_hit_rate_with_synonyms 79.67%<br/>freshness_rank_quality 1.0<br/>synonym_coverage 1.0"]
        EvalR -->|lmnr eval| LM
        EvalE -->|lmnr eval| LM
        EvalC -->|lmnr eval| LM
        EvalEnrich -->|lmnr eval group=enrichment_quality| LM
        HEP -->|score_rag_response| OS["laminar_scoring<br/>score_enrichment_boost<br/>score_search_miss"]
        OS -->|attach to trace| LM
    end

    subgraph Deploy["部署"]
        HAPI --> HDK["Docker Image<br/>TypeScript Hono"]
        HDK --> ECR[AWS ECR]
        ECR --> AR["AWS App Runner<br/>HTTPS auto<br/>port 8002"]
        API -.->|"legacy port 8001"| ECR
    end

    subgraph DataLayer["資料層（Supabase-ready）"]
        direction LR
        QA -.->|"Phase 1: 檔案載入"| STORE["store/qa-store.ts<br/>QAStore 抽象層<br/>（遷移邊界）"]
        STORE -.->|"Phase 2: Supabase"| SB["Supabase<br/>PostgreSQL + pgvector<br/>API 即時讀寫"]
    end
```

> Mermaid 可以在 GitHub 預覽（直接渲染），也可以在 VS Code 安裝 Mermaid Preview 擴充套件後本機查看。

---

## 更新架構圖的 SOP

每次架構有重大調整後：

1. 用 **architect agent** 討論新設計（`Task: subagent_type=everything-claude-code:architect`）
2. 把確認後的架構更新到本檔（`06b-architecture-diagram.md`）的 Mermaid 圖
3. 在 [06a-architecture-changelog.md](./06a-architecture-changelog.md) 新增一行（日期 + 版本 + 變更內容 + 影響範圍）
4. 更新 MEMORY.md 的確認基準線（如有評估數字變動）
