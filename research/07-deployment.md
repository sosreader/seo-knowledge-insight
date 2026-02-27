# 部署架構

> 屬於 [research/](./README.md)。涵蓋 FastAPI RAG API 化、ECR + EC2 SSM 部署模式。

---

## 20. FastAPI RAG API 化：把知識庫包成服務

> 本 session（2026-02-27）實作。把 Step 3 產出的 JSON + npy 包成 HTTP API，不動任何 pipeline 架構。

### 設計原則：無 DB、No ORM、全記憶體

```
# 過度設計（不要做）       # MVP 做法（本專案選擇）
postgres + pgvector     →  numpy 矩陣 @ 向量 = cosine
redis cache             →  python dict，啟動一次載入記憶體
celery task queue       →  FastAPI lifespan 直接載入
```

**決策依據**：703 筆 Q&A × 1536 維 = 約 4MB，遠小於 EC2 記憶體。
資料不變動（pipeline 跑完才更新），不需要即時寫入。

### FastAPI lifespan：啟動時載入資料

```python
# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()          # 載入 qa_final.json + qa_embeddings.npy
    yield                 # 服務存活期間資料保持在記憶體
    # 關閉時 GC 自動回收

app = FastAPI(lifespan=lifespan)
```

**前端類比**：`useEffect(() => { fetchData() }, [])` 的伺服器端版本——只跑一次，結果存在 module-level 變數。

### numpy cosine similarity（不用 pgvector）

```python
# app/core/store.py
# 預先 L2 歸一化，讓點積 = cosine similarity
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
self.embeddings = embeddings / norms  # shape: (703, 1536)

def search(self, query_vec: np.ndarray, top_k: int = 5):
    scores = self.embeddings @ query_vec  # (703,)，dot product = cosine
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(self.items[i], float(scores[i])) for i in top_idx]
```

**數學**：兩個 L2 歸一化向量的點積 = cosine similarity。
矩陣乘法一次計算全部 703 筆相似度，比 for loop 快 100x+。

### RAG chat 實作模式

```python
# app/core/chat.py
async def rag_chat(message: str, history: list[dict]) -> dict:
    # 1. 把問題 embed
    query_vec = await get_embedding(message)  # AsyncOpenAI

    # 2. 語意搜尋找 context
    hits = store.search(query_vec, top_k=5)

    # 3. 組裝 context 進 system message
    context = format_hits_as_text(hits)
    messages = [
        {"role": "system", "content": SEO_EXPERT_SYSTEM_PROMPT},
        {"role": "system", "content": f"--- 知識庫 ---\n{context}"},
        *history,
        {"role": "user", "content": message},
    ]

    # 4. GPT 生成回答
    resp = await client.chat.completions.create(
        model="gpt-5.2", messages=messages, temperature=0.3
    )
    return {"answer": resp.choices[0].message.content, "sources": sources}
```

**關鍵**：`history` 放在 context 和 user message 之間，讓 GPT 看到對話歷史。
`temperature=0.3`：RAG 問答要準確，不要創意。

### 模組結構

```
app/
├── config.py          # 從環境變數讀設定，不 import pipeline 的 config.py
├── core/
│   ├── store.py       # QAStore singleton：load() / search() / list_qa()
│   └── chat.py        # get_embedding() + rag_chat()
├── routers/
│   ├── search.py      # POST /api/v1/search
│   ├── chat.py        # POST /api/v1/chat
│   └── qa.py          # GET  /api/v1/qa, /qa/{id}, /qa/categories
└── main.py            # lifespan + CORS + include_router
```

**設計原則**：`app/` 自包含，不 import pipeline 的 `utils/` 或 `scripts/`。
日後兩個可以獨立部署。

---

## 21. ECR + EC2 SSM 部署模式

> 本 session（2026-02-27）設計，對應 vocus 現行 infra（與 vocus-web-ui 的 EC2 段相同邏輯）。

### 三種部署選項比較

| 方案                            | 複雜度 | 適合場景                      |
| ------------------------------- | ------ | ----------------------------- |
| EC2 直接 `docker run`           | 低     | 一次性手動部署                |
| **ECR + EC2 SSM（本專案選擇）** | **中** | **內部工具，CI/CD 自動化**    |
| ECR + ECS Fargate               | 高     | Production，需要 auto-scaling |

### ECR + EC2 SSM 流程

```
git push main
    ↓
GitHub Actions
    ↓
docker build -t seo-insight-api:$TAG .
    ↓
ECR push（AWS 私有 registry）
    ↓
SSM send-command → EC2 執行：
  aws ecr get-login-password | docker login
  docker pull $IMAGE:$TAG
  docker stop seo-insight-api && docker rm seo-insight-api
  docker run -d --name seo-insight-api \
    -p 127.0.0.1:8001:8001 \
    -v /data/output:/app/output:ro \
    -e OPENAI_API_KEY=$KEY \
    $IMAGE:$TAG
```

**SSM 好處**：不需要 SSH 進 EC2，不需要開 22 port，AWS IAM 控制權限。

### Dockerfile 設計要點

```dockerfile
FROM python:3.12-slim        # slim = 沒有不必要的系統套件
WORKDIR /app
COPY requirements_api.txt .  # 先 COPY 依賴，利用 layer cache
RUN pip install --no-cache-dir -r requirements_api.txt
COPY app/ ./app/             # 只 COPY API 程式碼
# output/ 用 volume mount，不進 image（data 與 code 分離）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**`.dockerignore` 必要性**：排除 `output/`、`raw_data/`、`.venv/` 等，
把 268MB image 控制在合理範圍（否則可能超過 1GB）。

### volume mount：data 與 code 分離

```bash
# EC2 上放資料，container 只 COPY code
docker run -v /home/ec2-user/seo-data/output:/app/output:ro ...
#                 ↑ EC2 路徑                  ↑ container 內路徑  ↑ 唯讀
```

**好處**：更新 `qa_final.json`（pipeline 重跑後）只需要 `docker restart`，
不需要重新 build image。

### GitHub Actions 關鍵 Secrets

| Secret              | 用途                                        |
| ------------------- | ------------------------------------------- |
| `ECR_DOMAIN`        | `xxxx.dkr.ecr.ap-northeast-1.amazonaws.com` |
| `EC2_TAG_KEY/VALUE` | 找目標 EC2 的 tag（e.g. `Name=seo-api`）    |
| `OUTPUT_DATA_PATH`  | EC2 上的 data 路徑                          |

**EC2 所需 IAM 角色**：`ecr:GetAuthorizationToken` + `ecr:BatchGetImage` + SSM Agent 啟動。

---

