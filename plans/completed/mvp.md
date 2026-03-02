# MVP 計畫：SEO Insight API（最小可行版）

> 狀態：Draft  
> 目標：最快 1 週上線，讓 UI 可以查詢 Q&A 知識庫 + 基本對話

---

## 核心思路

**不遷移任何資料、不建任何新服務。**  
直接讓 FastAPI 在啟動時讀取現有的 `qa_final.json` + `qa_embeddings.npy` 進記憶體，所有查詢都在記憶體中處理。

```
vocus-web-ui (Next.js)
    │
    ▼ REST API
FastAPI（現有 EC2 上跑，nginx 反向代理）
    │
    ├── 記憶體：qa_final.json（703筆 Q&A）
    ├── 記憶體：qa_embeddings.npy（numpy array）
    └── OpenAI API（語意搜尋 + 對話）
```

**省掉的東西（之後可以加）：**

- ❌ DB 遷移（PostgreSQL / pgvector）→ 直接讀 JSON
- ❌ Redis / ElastiCache → 記憶體快取即可
- ❌ ECS / Fargate → 跑在現有 EC2
- ❌ Eval 系統 → 現有 `05_evaluate.py` 手動跑
- ❌ Pipeline API → SSH 進去手動執行
- ❌ 週報 API → 先跳過

---

## API Endpoints（只有 3 個）

### `POST /api/v1/search`

語意搜尋 Q&A 知識庫。

```json
// Request
{ "query": "meta description 怎麼寫比較好？", "top_k": 5 }

// Response
{
  "results": [
    {
      "id": "qa_001",
      "question": "...",
      "answer": "...",
      "category": "on-page SEO",
      "score": 0.87,
      "source_date": "2024-06-13"
    }
  ]
}
```

### `POST /api/v1/chat`

單輪 RAG 對話（上下文由前端帶入，API 本身 stateless）。

```json
// Request
{
  "message": "Core Web Vitals 對排名影響大嗎？",
  "history": [
    { "role": "user", "content": "之前問題..." },
    { "role": "assistant", "content": "之前回答..." }
  ]
}

// Response
{
  "answer": "...",
  "sources": [{ "id": "qa_042", "question": "...", "score": 0.91 }]
}
```

### `GET /api/v1/qa`

列表 + 篩選（不含語意搜尋）。

```
GET /api/v1/qa?category=技術SEO&limit=20&offset=0
GET /api/v1/qa?keyword=crawl&difficulty=基礎
```

---

## 檔案結構（最精簡）

```
app/
  main.py          # FastAPI app + 啟動時載入資料
  routers/
    search.py      # /search endpoint
    chat.py        # /chat endpoint
    qa.py          # /qa list endpoint
  core/
    store.py       # 讀取 JSON + npy，提供查詢介面
    search.py      # cosine similarity（直接用 numpy）
    chat.py        # RAG：搜尋 → 組 prompt → GPT
  config.py        # 讀 .env
requirements_api.txt
```

**總計約 300–400 行 Python，1 週可完成。**

---

## 關鍵實作細節

### 資料載入（啟動一次，常駐記憶體）

```python
# app/core/store.py
import json, numpy as np
from pathlib import Path

class QAStore:
    def __init__(self):
        data = json.loads(Path("output/qa_final.json").read_text())
        self.items = data["qa_items"]          # list of dicts
        self.embeddings = np.load("output/qa_embeddings.npy")  # (703, 1536)

    def search(self, query_embedding: np.ndarray, top_k: int = 5):
        scores = self.embeddings @ query_embedding  # cosine sim（已歸一化）
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [(self.items[i], float(scores[i])) for i in top_idx]

qa_store = QAStore()   # module-level singleton
```

### 語意搜尋流程

```python
# app/routers/search.py
@router.post("/search")
async def search(req: SearchRequest):
    embedding = await get_embedding(req.query)   # 複用現有 openai_helper
    results = qa_store.search(embedding, req.top_k)
    return {"results": [format_result(item, score) for item, score in results]}
```

### Chat（RAG）

1. 對 `message` 做 embedding
2. 從 `qa_store.search()` 取 top-5
3. 組 system prompt：「以下是相關 SEO 知識：{context}，請根據這些資料回答」
4. 帶入 `history` + `message` 呼叫 gpt-5.2

---

## 部署（Docker 包好丟上現有 EC2）

### Step 1：Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
```

> vocus-trends 因為 Next.js 需要 build-time 注入環境變數才用 `ARG`/`ENV`。  
> Python FastAPI 不需要，env 全用 runtime `-e` 傳，Dockerfile 不用寫任何機密。

### Step 2：在 EC2 上跑

```bash
# 拉 image（或直接 build）
docker build -t seo-insight-api .
# 或從 ECR pull（公司已有）：
# docker pull ACCOUNT.dkr.ecr.ap-northeast-1.amazonaws.com/seo-insight-api:latest

# 啟動，掛載資料目錄 + 傳入 API key
docker run -d \
  --name seo-insight-api \
  --restart always \
  -p 127.0.0.1:8001:8001 \
  -v /data/seo_qa/output:/app/output:ro \
  -e OPENAI_API_KEY=sk-... \
  -e CORS_ORIGINS=https://vocus.cc \
  seo-insight-api
```

> `-v /data/seo_qa/output:/app/output:ro`：把 EC2 上現有的 `qa_final.json` + `qa_embeddings.npy` 掛進容器，不用 copy 進 image。

### Step 3：nginx 加一個 location block

```nginx
location /api/seo-insight/ {
    proxy_pass http://127.0.0.1:8001/;
}
```

### 更新流程（之後每次）

```bash
docker build -t seo-insight-api .
docker stop seo-insight-api && docker rm seo-insight-api
docker run -d ...（同上）
```

**不需要 ECS、不需要 ECR、不需要 Load Balancer。**

---

## 成本

| 項目                  | 月費           |
| --------------------- | -------------- |
| EC2 新增費用          | $0（共用現有） |
| OpenAI（搜尋 + 對話） | ~$3–8          |
| **合計**              | **$3–8/月**    |

---

## 實施時程（1 週）

```
Day 1: store.py + search.py（資料載入 + cosine search）
Day 2: /search endpoint + 測試
Day 3: chat.py（RAG 流程）+ /chat endpoint
Day 4: /qa list endpoint + CORS + .env 設定
Day 5: 部署到 EC2 + nginx 設定 + 與 UI 串接測試
```

---

## 升級路徑（之後有需要再加）

| 當遇到這個問題                   | 才需要加                     |
| -------------------------------- | ---------------------------- |
| JSON 太大讀取慢 / 需要複雜查詢   | 遷移到 PostgreSQL + pgvector |
| 多人同時使用、embedding 重複計算 | 加 Redis 快取                |
| EC2 資源不夠 / 需要獨立 scaling  | 改用 ECS Fargate             |
| 需要持續監控 Q&A 品質            | 建 Eval 系統                 |
| 需要觸發 pipeline / 看執行狀態   | 加 Pipeline API              |
