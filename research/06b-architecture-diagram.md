# 本專案架構圖（Mermaid）

> 屬於 [research/](./README.md)，從 [06-project-architecture.md](./06-project-architecture.md) 拆出。
> 每次架構調整後依 [SOP](#更新架構圖的-sop) 更新此圖，並在 [06a-architecture-changelog.md](./06a-architecture-changelog.md) 新增一行。

---

## 架構圖（最新：v2.2，2026-03-04）

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

    subgraph Eval["評估層 v1.4 v1.5 v1.17（Claude Code 本地評估）"]
        GoldenSets["eval/ Golden Sets<br/>extraction(5) dedup(40) qa(50) report(5)"]
        QA --> S5[Step 5: evaluate.py<br/>LLM-as-Judge<br/>4 維度評估 + 本地選項]
        EMB --> S5
        GoldenSets --> S5
        S5 --> ER["eval_report.json<br/>Completeness 3.85<br/>+ eval_local_*.json<br/>(Claude Code 評分)"]
    end

    subgraph RAG_Search["RAG和Hybrid Search v1.5"]
        GS[Google Sheets 指標 TSV] --> S4[Step 4: generate_report.py<br/>異常偵測 Hybrid Search RAG]
        QA --> S4
        EMB --> S4
        SE["SearchEngine v1.5<br/>compute_keyword_boost"] -.->|kw match| S4
        S4 --> RPT[report_YYYYMMDD.md]
    end

    subgraph RAG_API["API Layer v2.2（stable_id + reports + sessions）"]
        QA --> API[SEO Insight API<br/>FastAPI QAStore singleton<br/>QAItem.id: stable_id hex]
        EMB --> API
        SE -.->|hybrid_search| API
        API --> SEC["app/core/security.py<br/>verify_api_key<br/>X-API-Key header<br/>SEO_API_KEY env"]
        API --> LIM["app/core/limiter.py<br/>slowapi Limiter<br/>chat:20/min search:60/min<br/>qa:60/min reports/gen:5/min"]
        API --> EXC["@app.exception_handler<br/>500 不流展 traceback"]
        SEC --> EP["POST /api/v1/search — 60/min<br/>POST /api/v1/chat — 20/min<br/>GET  /api/v1/qa — 60/min<br/>GET  /api/v1/qa/{id} — hex validated<br/>POST /api/v1/feedback — 60/min"]
        LIM --> EP
        EXC --> EP
        EP --> ENV["ApiResponse[T]<br/>data / error / meta<br/>request_id + version"]
        EP -->|not_relevant / helpful| LS
        EP -->|staleness 警示 18個月| STALE["chat.py _is_stale()<br/>超過 18 個月提示"]
        SEC --> RPT_EP["GET  /api/v1/reports — 60/min<br/>GET  /api/v1/reports/{date}<br/>POST /api/v1/reports/generate — 5/min"]
        LIM --> RPT_EP
        RPT_EP --> RPT_STORE["app/routers/reports.py<br/>output/report_YYYYMMDD.md<br/>subprocess + SSRF 防護"]
        SEC --> SS_EP["GET/POST /api/v1/sessions<br/>GET/POST/DELETE .../sessions/{id}"]
        SS_EP --> SS_STORE["app/core/session_store.py<br/>output/sessions/{uuid}.json<br/>Repository Pattern"]
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

    subgraph Observability["可觀測性 v1.19 完整整合（FastAPI+CLI+Evals）"]
        S2 -->|"@observe + init_laminar"| LM["Laminar SDK v0.5<br/>OpenTelemetry-based<br/>lmnr observe"]
        S3 -->|"@observe + init_laminar"| LM
        S4 -->|"@observe + init_laminar"| LM
        S5 -->|"@observe + init_laminar"| LM
        QT["qa_tools.py 6 subcommands<br/>@observe + flush_laminar"] -->|"search/merge_qa/etc"| LM
        API -->|"auto OpenAI trace"| LM
        EC["evals/eval_chat.py<br/>Laminar.initialize()"] -->|"lmnr eval"| LM
        LM --> LD["Laminar Dashboard<br/>Traces + Spans + Events"]
        OS -.->|"score_event"| LM
    end

    subgraph OfflineEvals["離線評估 v1.10"]
        GoldenSets2["eval/ Golden Sets<br/>retrieval(307) extraction chat(10)"]
        GoldenSets2 --> EvalR["evals/eval_retrieval.py<br/>keyword_hit_rate<br/>category_match"]
        GoldenSets2 --> EvalE["evals/eval_extraction.py<br/>qa_count<br/>keyword_coverage"]
        GoldenSets2 --> EvalC["evals/eval_chat.py<br/>answer_length<br/>has_sources"]
        GoldenSets2 --> EvalEnrich["evals/eval_enrichment.py v1.19<br/>kw_hit_rate_with_synonyms 79.67%<br/>freshness_rank_quality 1.0<br/>synonym_coverage 1.0"]
        EvalR -->|lmnr eval| LM
        EvalE -->|lmnr eval| LM
        EvalC -->|lmnr eval| LM
        EvalEnrich -->|lmnr eval group=enrichment_quality| LM
        EP -->|score_rag_response| OS["laminar_scoring.py v1.19<br/>score_enrichment_boost<br/>score_search_miss"]
        OS -->|attach to trace| LM
    end

    subgraph Deploy["部署（ECR + App Runner）"]
        API --> Docker[Docker Image]
        Docker --> ECR[AWS ECR]
        ECR --> AR[AWS App Runner<br/>HTTPS auto<br/>port 8001]
    end

    subgraph DataLayer["資料層（Supabase-ready）"]
        direction LR
        QA -.->|"Phase 1: 檔案載入"| STORE["app/core/store.py<br/>QAStore 抽象層<br/>（遷移邊界）"]
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
