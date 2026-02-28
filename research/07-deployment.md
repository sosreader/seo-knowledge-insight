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

## 22. Laminar Observability（2026-02-28 新增）

> LLM 呼叫的 trace / span 可觀測平台，讓每一次 OpenAI 呼叫都有完整紀錄。

### 最小化設定（3 步驟）

```bash
pip install lmnr
```

```python
# app/main.py — 在所有 import 完成後呼叫一次
import os
from lmnr import Laminar

Laminar.initialize(project_api_key=os.getenv("LMNR_PROJECT_API_KEY"))
```

```
# .env
LMNR_PROJECT_API_KEY=your_laminar_project_api_key
```

初始化後，所有 `openai`、`anthropic` 等 SDK 呼叫自動被追蹤，**不需要修改任何 router 程式碼**。

### 手動追蹤（不依賴 LLM）

使用 `@observe` 裝飾器追蹤任意函式（測試用或自訂 span）：

```python
from lmnr import observe

@observe()
def seo_answer(question: str) -> str:
    return "..."

# span input = {"question": "..."}, span output = "..."
```

### 相依性衝突修復（Python 3.9 + lmnr 0.5.2）

`opentelemetry-semantic-conventions-ai 0.4.14` 移除了 `LLM_SYSTEM`、`LLM_REQUEST_MODEL`、`LLM_RESPONSE_MODEL` 三個屬性，但 `lmnr 0.5.2` 的內部程式碼仍然參照它們。

**修復方式**：在 `.venv/lib/.../opentelemetry/semconv_ai/__init__.py` 的 `SpanAttributes` class 補上：

```python
LLM_SYSTEM = "gen_ai.system"
LLM_REQUEST_MODEL = "gen_ai.request.model"
LLM_RESPONSE_MODEL = "gen_ai.response.model"
```

> 這是 `lmnr` 的 upstream bug，升級版本後可移除此補丁。

### 注意事項

- `Laminar.initialize()` 必須在 `load_dotenv()` 之後呼叫（本專案 `from app import config` 已隱含 `load_dotenv()`）
- 啟動本身不會建立 trace；第一個 LLM 呼叫才會送出第一個 span
- 可至 https://laminar.sh dashboard 的 Traces 頁面驗證

---

## 23. API 安全：Auth + Rate Limit（OWASP Top 10 風險修復）

> v1.8 識別的 CRITICAL 缺口，本章說明標準做法。

### OWASP API Security Top 10（2023）識別的風險

| API 風險          | 本專案現況      | 修復優先度 | 修復工時 |
| ----------------- | --------------- | --------- | ------- |
| **API2:2023 — Broken Authentication**（無認證） | `/api/v1/*` 無 API Key 驗證 | CRITICAL | 2h      |
| **API4:2023 — Unrestricted Resource Consumption**（無速率限制） | `/api/v1/chat` 每次消耗 GPT token，無限制 | CRITICAL | 2h      |
| **API1:2023 — Broken Object Level Authorization** | `GET /api/v1/qa/{id}` 無權限檢查（當前所有 QA 公開） | LOW | —       |

### FastAPI API Key 驗證實作（`Depends()` pattern）

標準做法：

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    """驗證 API Key，格式 'sk-...'。"""
    expected = os.getenv("API_KEY")
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key"
        )
    return api_key

@router.post("/api/v1/chat")
async def chat(body: ChatRequest, api_key: str = Depends(verify_api_key)):
    # api_key 已驗證，可安全使用
    return await rag_chat(body.message)
```

**設定**（`.env`）：
```
API_KEY=sk-your-secret-key-here
```

### Rate Limiting：slowapi（FastAPI 官方推薦）

安裝：`pip install slowapi`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

@router.post("/api/v1/chat")
@limiter.limit("10/minute")  # 每分鐘最多 10 次
async def chat(body: ChatRequest, request: Request):
    return await rag_chat(body.message)
```

**觀測**：命中限制時自動回傳 429 Too Many Requests（RFC 6585）。

### Response Envelope Pattern（Microsoft REST API Guidelines 2024）

統一所有回應格式，方便前端錯誤處理：

```python
@dataclass
class APIResponse(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None

# 成功
return APIResponse(success=True, data=results)

# 錯誤
return APIResponse(success=False, error="Invalid query", metadata={"timestamp": "..."})
```

---

## 24. API 請求追蹤：Audit Trail（2026-02-28 新增）

> 資料安全需求：確認哪些 QA 資料被哪些 IP 存取過。

### 設計原則

- **JSONL append-only**：每筆 event 一行 JSON，不修改歷史紀錄
- **Zero side-effects**：`_append_jsonl()` 內包 `try/except`，寫入失敗不影響 API 回應
- **按日期分檔**：`output/fetch_logs/fetch_2026-02-28.jsonl`、`output/access_logs/access_2026-02-28.jsonl`
- **session_id 串接**：每次 Step 1 fetch 生成 8-char UUID，關聯同一批 fetch events

### FastAPI 取得 client IP

```python
from fastapi import APIRouter, Request

@router.post("/search")
async def search(body: SearchRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    audit_logger.log_search(
        query=body.query,
        returned_ids=[r["id"] for r in results],
        client_ip=client_ip,
    )
```

**注意**：`request: Request` 必須是非依賴注入的普通參數（直接放在函式簽名），不能用 `Depends()`。
部署在反向代理後面時需要額外處理 `X-Forwarded-For`。

### Log 格式（JSONL）

```json
// fetch_logs/fetch_2026-02-28.jsonl
{"event": "fetch_start", "session_id": "a1b2c3d4", "mode": "incremental", "ts": "..."}
{"event": "fetch_page", "session_id": "a1b2c3d4", "page_id": "...", "title": "SEO 會議", "block_count": 42, "ts": "..."}
{"event": "fetch_skip", "session_id": "a1b2c3d4", "page_id": "...", "reason": "no_change_incremental", "ts": "..."}
{"event": "fetch_complete", "session_id": "a1b2c3d4", "fetched": 5, "skipped": 82, "duration_sec": 12.3, "ts": "..."}

// access_logs/access_2026-02-28.jsonl
{"event": "search", "query": "canonical URL 怎麼設定", "top_k": 5, "returned_ids": [42, 17, 8], "client_ip": "1.2.3.4", "ts": "..."}
{"event": "chat", "message": "什麼是 Core Web Vitals", "returned_ids": [3, 91], "client_ip": "1.2.3.4", "ts": "..."}
{"event": "list_qa", "filters": {"category": "技術SEO"}, "total": 89, "client_ip": "1.2.3.4", "ts": "..."}
```

### 查詢工具

```bash
make audit           # 今天完整報告（fetch stats + 被存取最多 QA）
make audit-fetch     # fetch session 摘要
make audit-access    # access event 列表
make audit-top       # Top 30 最常被存取的 QA

# 直接呼叫
.venv/bin/python scripts/audit_trail.py report
.venv/bin/python scripts/audit_trail.py access --top 10 --event search
.venv/bin/python scripts/audit_trail.py fetch --sessions
```

---

---

## Laminar Observability 整合（2026-02-28）

### 初始化方式

**FastAPI（`app/main.py`）**：
```python
from lmnr import Laminar
Laminar.initialize(project_api_key=os.getenv("LMNR_PROJECT_API_KEY"))
# 在 module load 時執行一次（非 lifespan，避免熱重啟問題）
```

**Pipeline CLI scripts（02–05）**：
```python
from utils.observability import init_laminar, flush_laminar

def main(args):
    init_laminar()
    try:
        do_work()
    finally:
        flush_laminar()    # 必須！避免 in-flight spans 在 process exit 時丟失
```

### @observe 裝飾器

```python
from utils.observability import observe    # pipeline scripts
from lmnr import observe                   # app/ 層（直接 import）

@observe(name="step_name")
def my_step(input_data: str) -> dict:
    ...
```

### lmnr eval CLI

```bash
pip install 'lmnr>=0.5.0'
export LMNR_PROJECT_API_KEY=<key>

lmnr eval                           # 掃描 evals/ 目錄，執行所有 eval_*.py
lmnr eval evals/eval_retrieval.py   # 單一腳本
python evals/eval_retrieval.py      # 也可直接用 python 執行
```

### CI/CD 整合（建議）

```yaml
# .github/workflows/eval.yml
- name: Run Laminar evals
  env:
    LMNR_PROJECT_API_KEY: ${{ secrets.LMNR_PROJECT_API_KEY }}
  run: |
    lmnr eval evals/eval_retrieval.py
    lmnr eval evals/eval_extraction.py
    # eval_chat.py 需要 OPENAI_API_KEY，在 nightly 跑
```

### Online Scoring 工具（`utils/laminar_scoring.py`）

```python
from utils.laminar_scoring import score_trace, score_rag_response

# 在 @observe 函式內取得 trace_id
from lmnr import Laminar
span_ctx = Laminar.get_laminar_span_context()
trace_id = str(span_ctx.trace_id) if span_ctx else None

score_rag_response(trace_id=trace_id, answer=answer, sources=sources, query=message)
```

### 環境變數

| 變數 | 用途 | 必要性 |
|------|------|--------|
| `LMNR_PROJECT_API_KEY` | Laminar tracing + evals | 無此 key 時 silently skip，不 crash |
| `OPENAI_API_KEY` | eval_chat.py + pipeline scripts | eval_chat.py 和 pipeline 必需 |
