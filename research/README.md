# SEO QA Pipeline — Research 知識庫

> 原 `research.md`（1,240 行）依主題拆分為以下分類檔案。

---

## 分類索引

| 檔案 | 主題 |
|------|------|
| [01-ai-fundamentals.md](./01-ai-fundamentals.md) | LLM / Token / Prompt / Structured Output / Embedding / Cosine |
| [02-rag-and-search.md](./02-rag-and-search.md) | RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標 |
| [03-evaluation.md](./03-evaluation.md) | LLM-as-Judge / Reasoning Model / 評估維度 / Judge 設計原則 |
| [04-prompting.md](./04-prompting.md) | Prompt Engineering 進階（業界最佳實踐）|
| [05-models.md](./05-models.md) | 模型選擇決策 / Embedding 模型比較 |
| [06-project-architecture.md](./06-project-architecture.md) | 本專案架構 / 決策紀錄 / Changelog |
| [07-deployment.md](./07-deployment.md) | FastAPI RAG API 化 / ECR + EC2 部署 |
| [08-fetch-optimization.md](./08-fetch-optimization.md) | Notion 爬取優化 / ETag / 增量更新 |
| [09-provider-comparison.md](./09-provider-comparison.md) | AI Provider 輸出品質比較方法論與歷次跑分結果 |

---

## 1. 快速對照表

前端你已知的東西，直接對照：

| 你知道的                      | Python / 本專案                       |
| ----------------------------- | ------------------------------------- |
| `fetch(url, { headers })`     | `requests.get(url, headers=...)`      |
| `process.env.API_KEY`         | `os.getenv("API_KEY")`                |
| `JSON.parse / JSON.stringify` | `json.loads / json.dumps`             |
| `npm run build -- --flag`     | `python script.py --step 2 --limit 3` |
| `localStorage.setItem(k, v)`  | `Path("file.json").write_text(...)`   |
| Promise chain                 | 每步結果存 JSON 檔，下步再讀          |

其他語法差異（縮排、`def`、`import`）看到就懂，不需要特別記。

---

