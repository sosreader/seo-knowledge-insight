# SEO QA Pipeline — Research 知識庫

> 原 `research.md`（1,240 行）依主題拆分為以下分類檔案。

---

## 分類索引

| 檔案                                                             | 主題                                                                        |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------- |
| [01-ai-fundamentals.md](./01-ai-fundamentals.md)                 | LLM / Token / Prompt / Structured Output / Embedding / Cosine               |
| [02-rag-and-search.md](./02-rag-and-search.md)                   | RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標                         |
| [03-evaluation.md](./03-evaluation.md)                           | LLM-as-Judge / Reasoning Model / 評估維度 / Judge 設計原則                  |
| [04-prompting.md](./04-prompting.md)                             | Prompt Engineering 進階（業界最佳實踐）                                     |
| [05-models.md](./05-models.md)                                   | 模型選擇決策 / Embedding 模型比較                                           |
| [06-project-architecture.md](./06-project-architecture.md)       | 本專案架構 / Pipeline 全景 / 技術決策學術支撐                               |
| [06a-architecture-changelog.md](./06a-architecture-changelog.md) | 架構變更紀錄（Changelog），每次架構調整後新增一行                           |
| [06b-architecture-diagram.md](./06b-architecture-diagram.md)     | Mermaid 架構圖 + 更新 SOP（最新 v2.12，Hono API + Reranker + Context Relevance；v2.13 eval 腳本新增）|
| [07-deployment.md](./07-deployment.md)                           | Hono API 部署 / ECR + App Runner / Supabase 遷移路徑                        |
| [08-fetch-optimization.md](./08-fetch-optimization.md)           | Notion 爬取優化 / ETag / 增量更新                                           |
| [09-provider-comparison.md](./09-provider-comparison.md)         | AI Provider 輸出品質比較方法論與歷次跑分結果                                |
| [10-multi-layer-context.md](./10-multi-layer-context.md)         | Multi-Layer Context / enrichment / 同義詞擴展 / 時效性衰減 / Learning Store |

---

## 術語速查（常見未定義術語）

| 術語                    | 定義                                                    | 詳細說明                                                                                                               |
| ----------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **enrichment**          | 離線預計算：對每筆 Q&A 加入同義詞、時效分數等 metadata  | [10-multi-layer-context.md §23](./10-multi-layer-context.md#23-offline-enrichment-pipeline-enrich_qapy)                |
| **qa_enriched.json**    | `make enrich` 產生的豐富化知識庫，含 `_enrichment` 欄位 | [10-multi-layer-context.md §23](./10-multi-layer-context.md#23-offline-enrichment-pipeline-enrich_qapy)                |
| **Learning Store**      | `utils/learning_store.py`，JSONL 失敗記憶庫             | [10-multi-layer-context.md §24](./10-multi-layer-context.md#24-learning-store--staleness-feedback-loop)                |
| **Multi-Layer Context** | 三層知識庫：Knowledge + Context + Learnings             | [10-multi-layer-context.md §20](./10-multi-layer-context.md#20-multi-layer-context-architecture)                       |
| **Staleness**           | Q&A 超過 18 個月，chat 加 ⚠️ 警示                       | [10-multi-layer-context.md §24](./10-multi-layer-context.md#24-learning-store--staleness-feedback-loop)                |
| **Version Registry**    | `utils/pipeline_version.py`，不可變 artifact 版本記錄   | [06-project-architecture.md §B](./06-project-architecture.md#b-immutable-artifact-version-registry-pipeline_versionpy) |
| **hybrid_search**       | 語意（cosine）+ 關鍵字（BM25 boost）混合搜尋            | [02-rag-and-search.md](./02-rag-and-search.md)                                                                         |
| **freshness_score**     | `exp(-0.693 × age/540d)`，時效性衰減分數（min=0.5）     | [10-multi-layer-context.md §22](./10-multi-layer-context.md#22-時效性衰減temporal-freshness-decay)                     |

---

## 當前指標現況（2026-03-05，v2.13 — Eval 4 層框架整合 + RAGAS Faithfulness/Context Precision）

| 指標                   | 數值       | 說明                                                      |
| ---------------------- | ---------- | --------------------------------------------------------- |
| Q&A 總量               | **1,317 筆** | 4 來源：notion-seo-meetings 584、medium-genehong 505、ithelp-gsc-kpi 185、google-case-studies 43 |
| QA ID 格式             | 16-char hex | stable_id（SHA256[:16]），取代 sequential int             |
| KW Hit Rate            | **73%**    | CJK n-gram + synonym 展開（目標 ≥ 85%；中間目標 78%+）  |
| Precision@K            | **76%**    | category-level（目標 ≥ 80%）                              |
| Recall@K               | **80%**    | ✅（目標 ≥ 80%）                                          |
| F1 Score               | **0.73**   | Precision/Recall 調和平均                                 |
| NDCG@K                 | 待測       | v2.13 新增（預期 ≥ MRR=0.88，Jarvelin & Kekalainen, 2002）|
| freshness_rank_quality | **1.0**    | 時效衰減正常，舊文件未擠掉新文件                          |
| synonym_coverage       | **1.0**    | 所有 Q&A 已完成 enrichment                               |
| avg_synonyms / Q&A     | 11.09      | enrichment 後平均同義詞數                                |
| avg_freshness          | 0.9076     | 知識庫整體新鮮度（max=1.0）                              |
| MRR                    | **0.88**   | 平均倒數排名（v2.12）                                    |
| Relevance              | **5.00** / 5 | Claude Code as Judge（v2.12）                           |
| Accuracy               | **4.30** / 5 | Claude Code as Judge（v2.12）                           |
| Completeness           | **3.95** / 5 | Claude Code as Judge（v2.12）                           |
| Context Relevance      | **0.32**（1 query）| NVIDIA style，keyword fallback（v2.12）          |
| Faithfulness           | 待測       | RAGAS，v2.13 `/evaluate-faithfulness-local`（目標 ≥ 0.80）|
| Context Precision      | 待測       | RAGAS，v2.13 `/evaluate-context-precision-local`（目標 ≥ 0.70）|
| **Test 通過率**        | **215/215** | Hono TypeScript Vitest（25 test files，v2.13）           |
| **API endpoints**      | **37 個**   | 10 routers：qa/search/chat/reports/sessions/feedback/pipeline(15)/eval(6)/synonyms/health |
| **Observability**      | **完備**    | Laminar traces + Audit logs + Scoring events（三柱）     |

---

## 1. 快速對照表

前端你已知的東西，直接對照：

| 你知道的                      | Python / 本專案                                |
| ----------------------------- | ---------------------------------------------- |
| `fetch(url, { headers })`     | `requests.get(url, headers=...)`               |
| `process.env.API_KEY`         | `os.getenv("API_KEY")`                         |
| `JSON.parse / JSON.stringify` | `json.loads / json.dumps`                      |
| `npm run build -- --flag`     | `python script.py --step extract-qa --limit 3` |
| `localStorage.setItem(k, v)`  | `Path("file.json").write_text(...)`            |
| Promise chain                 | 每步結果存 JSON 檔，下步再讀                   |

其他語法差異（縮排、`def`、`import`）看到就懂，不需要特別記。

---
