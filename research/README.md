# SEO QA Pipeline — Research 知識庫

> 原 `research.md`（1,240 行）依主題拆分為以下分類檔案。

---

## 分類索引

| 檔案                                                             | 主題                                                                         |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| [01-ai-fundamentals.md](./01-ai-fundamentals.md)                 | LLM / Token / Prompt / Structured Output / Embedding / Cosine                |
| [02-rag-and-search.md](./02-rag-and-search.md)                   | RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標 / RAG 迭代改進           |
| [03-evaluation.md](./03-evaluation.md)                           | LLM-as-Judge / Reasoning Model / 評估維度 / Laminar Eval Groups / 離線評估  |
| [04-prompting.md](./04-prompting.md)                             | Prompt Engineering 進階（業界最佳實踐）                                      |
| [05-models.md](./05-models.md)                                   | 模型選擇決策 / Embedding 模型比較 / 模型使用政策                             |
| [06-project-architecture.md](./06-project-architecture.md)       | 本專案架構 / Pipeline 全景 / 技術決策學術支撐 / 完整目錄樹                   |
| [06a-architecture-changelog.md](./06a-architecture-changelog.md) | 架構變更紀錄（Changelog）/ 資料來源完整性 / Roadmap                          |
| [06b-architecture-diagram.md](./06b-architecture-diagram.md)     | Mermaid 架構圖 + 工作流程圖（Production / 本地開發 / 互動關係）              |
| [06c-backend-onboarding.md](./06c-backend-onboarding.md)         | 後端 API 入門導讀 / Troubleshooting / 開發指南 / JS↔Python 對照              |
| [07-deployment.md](./07-deployment.md)                           | Hono API 部署 / Lambda + Function URL / Supabase 遷移 / App Runner（已淘汰） |
| [08-fetch-optimization.md](./08-fetch-optimization.md)           | Fetch 優化 / Notion 增量 / Medium Scrapling / 多來源爬取架構                 |
| [09-retrieval-dimensions.md](./09-retrieval-dimensions.md)       | Retrieval metadata 欄位、runtime re-rank 邏輯與 migration/fallback 策略      |
| [10-multi-layer-context.md](./10-multi-layer-context.md)         | Multi-Layer Context / enrichment / 同義詞擴展 / 時效性衰減 / Learning Store  |
| [11-seo-industry-updates.md](./11-seo-industry-updates.md)       | SEO 業界動態（Google 更新 / SER / 業界報導）                                 |
| [12-meeting-prep-insights.md](./12-meeting-prep-insights.md)     | Meeting-Prep 評分追蹤 / 交叉比對發現                                        |
| [13-local-fallback.md](./13-local-fallback.md)                   | 無 OpenAI / 舊 schema / timeout 場景下的 local fallback 設計與邊界           |
| [14-provider-comparison.md](./14-provider-comparison.md)         | AI Provider 輸出品質比較方法論與歷次跑分結果                                 |
| [15-pipeline-operations.md](./15-pipeline-operations.md)         | Pipeline 操作手冊（步驟 4/5 詳細 + 成本估算 + 運維須知）                     |
| [16-data-schema.md](./16-data-schema.md)                         | 資料結構（5 種 JSON 格式 + 分類標籤列表）                                    |

---

## 術語速查

| 術語                    | 定義                                                    | 詳細說明                                                                                                               |
| ----------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **enrichment**          | 離線預計算：對每筆 Q&A 加入同義詞、時效分數等 metadata  | [10-multi-layer-context.md §23](./10-multi-layer-context.md#23-offline-enrichment-pipeline-enrich_qapy)                |
| **qa_enriched.json**    | `make enrich` 產生的豐富化知識庫，含 `_enrichment` 欄位 | [10-multi-layer-context.md §23](./10-multi-layer-context.md#23-offline-enrichment-pipeline-enrich_qapy)                |
| **Learning Store**      | `utils/learning_store.py`，JSONL 失敗記憶庫             | [10-multi-layer-context.md §24](./10-multi-layer-context.md#24-learning-store--staleness-feedback-loop)                |
| **Multi-Layer Context** | 三層知識庫：Knowledge + Context + Learnings             | [10-multi-layer-context.md §20](./10-multi-layer-context.md#20-multi-layer-context-architecture)                       |
| **Staleness**           | Q&A 超過 18 個月，chat 加警示                           | [10-multi-layer-context.md §24](./10-multi-layer-context.md#24-learning-store--staleness-feedback-loop)                |
| **Version Registry**    | `utils/pipeline_version.py`，不可變 artifact 版本記錄   | [06-project-architecture.md §B](./06-project-architecture.md#b-immutable-artifact-version-registry-pipeline_versionpy) |
| **hybrid_search**       | 語意（cosine）+ 關鍵字（BM25 boost）混合搜尋            | [02-rag-and-search.md](./02-rag-and-search.md)                                                                         |
| **freshness_score**     | `exp(-0.693 * age/540d)`，時效性衰減分數（min=0.5）     | [10-multi-layer-context.md §22](./10-multi-layer-context.md#22-時效性衰減temporal-freshness-decay)                     |
| **stable_id**           | `SHA256(source_collection::source_file::question)[:16]`，路徑無關的 Q&A 唯一識別碼 | [06-project-architecture.md](./06-project-architecture.md)                              |
| **maturity_relevance**  | L1–L4 SEO 成熟度等級，標記 Q&A 適用的客戶階段           | [03-evaluation.md](./03-evaluation.md)                                                                                 |

---
