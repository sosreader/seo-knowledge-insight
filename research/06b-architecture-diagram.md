# 本專案架構圖（Mermaid）

> 屬於 [research/](./README.md)，從 [06-project-architecture.md](./06-project-architecture.md) 拆出。
> 每次架構調整後依 [SOP](#更新架構圖的-sop) 更新此圖，並在 [06a-architecture-changelog.md](./06a-architecture-changelog.md) 新增一行。

---

## 架構圖（最新：v2.3，2026-03-04）

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
        S2 --> RAW[output/qa_all_raw.json<br/>670 筆原始 Q&A]
        RAW --> S3[Step 3: dedupe_classify.py<br/>embedding 去重 + gpt-5-mini 分類<br/>或 Claude Code 本地關鍵字分類]
        S3 --> QA[output/qa_final.json<br/>655 筆 + 10 分類]
        S3 --> EMB[output/qa_embeddings.npy<br/>655 x 1536 維向量]
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

    subgraph Hono_API["API Layer v2.3（Hono + TypeScript，port 8002）"]
        QA --> HAPI["SEO Insight API<br/>Hono + TypeScript<br/>QAStore（npy-reader 向量解析）"]
        EMB --> HAPI
        SE -.->|hybrid_search| HAPI
        HAPI --> HMID["middleware/<br/>auth.ts（X-API-Key）<br/>rate-limit.ts（chat:20/min search/qa:60/min reports/gen:5/min）<br/>cors.ts + error-handler.ts"]
        HMID --> HEP["6 個 Router + health<br/>qa.ts — GET /qa, /qa/{id}（hex+int）<br/>search.ts — POST /search<br/>chat.ts — POST /chat<br/>reports.ts — GET/POST /reports<br/>sessions.ts — CRUD /sessions（60/min, msg:20/min）<br/>feedback.ts — POST /feedback"]
        HEP --> HENV["ApiResponse[T]<br/>Zod schema validation<br/>data / error / meta"]
        HEP -->|not_relevant / helpful| LS
        HAPI --> HSTORE["store/<br/>qa-store.ts（QAStore singleton）<br/>search-engine.ts（hybrid search + keyword boost）<br/>session-store.ts（FileSessionStore）<br/>learning-store.ts"]
        HAPI --> HUTIL["utils/<br/>npy-reader.ts（NumPy .npy 解析）<br/>cosine-similarity.ts（Float32Array）<br/>keyword-boost.ts（4 層匹配）<br/>sanitize.ts（HTML escape 防 XSS）"]
        HAPI --> HSVC["services/<br/>embedding.ts（OpenAI wrapper）<br/>rag-chat.ts（RAG 問答）"]
        HAPI --> HSCHEMA["schemas/<br/>Zod runtime validation<br/>qa / search / chat / feedback<br/>report / session"]
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

    subgraph Observability["可觀測性（Python CLI+Evals；Hono TODO）"]
        S2 -->|"@observe + init_laminar"| LM["Laminar SDK v0.5<br/>OpenTelemetry-based<br/>lmnr observe"]
        S3 -->|"@observe + init_laminar"| LM
        S4 -->|"@observe + init_laminar"| LM
        S5 -->|"@observe + init_laminar"| LM
        QT["qa_tools.py 6 subcommands<br/>@observe + flush_laminar"] -->|"search/merge_qa/etc"| LM
        HAPI -.->|"TODO: Laminar 整合"| LM
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
