# 部署架構

> 屬於 [research/](./README.md)。涵蓋 FastAPI RAG API 化、ECR + App Runner 部署、Supabase 遷移路徑。

---

## 20. FastAPI RAG API 化：把知識庫包成服務

> 本 session（2026-02-27）實作。把 Step 3 產出的 JSON + npy 包成 HTTP API，不動任何 pipeline 架構。

### 設計原則：無 DB、No ORM、全記憶體（Phase 1）

```
# Phase 1（當前）               # Phase 2（Supabase 遷移後）
numpy 矩陣 @ 向量 = cosine  →  PostgreSQL + pgvector
python dict，啟動載入記憶體  →  Supabase REST / PostgREST
FastAPI lifespan 直接載入    →  store.py 切換為 DB 查詢
```

**決策依據**：655 筆 Q&A × 1536 維 = 約 4MB，遠小於容器記憶體。
Phase 1 使用記憶體載入，Phase 2 遷移至 Supabase 後支援 API 即時寫入。

> **Supabase 遷移預備**：所有資料存取均透過 `app/core/store.py` 的 `QAStore` 抽象層。
> 遷移時只需替換 `store.py` 內部實作（file → Supabase client），router 層零修改。
> 詳見 §21.4「資料層遷移路徑」。

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
self.embeddings = embeddings / norms  # shape: (725, 1536)

def search(self, query_vec: np.ndarray, top_k: int = 5):
    scores = self.embeddings @ query_vec  # (725,)，dot product = cosine
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(self.items[i], float(scores[i])) for i in top_idx]
```

**數學**：兩個 L2 歸一化向量的點積 = cosine similarity。
矩陣乘法一次計算全部 725 筆相似度，比 for loop 快 100x+。

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

## 21. ECR + App Runner 部署模式

> 2026-03-03 從 ECR + EC2 SSM 遷移至 ECR + App Runner（無伺服器容器）。

### 21.1 部署選項演進

| 方案                              | 複雜度 | 月費估算    | 適合場景                      |
| --------------------------------- | ------ | ----------- | ----------------------------- |
| ~~ECR + EC2 SSM~~（v0.3–v1.20）  | 中     | ~$5-10      | 已淘汰（需管主機）            |
| **ECR + App Runner（當前選擇）**  | **低** | **~$5-7**   | **無伺服器，push image 即部署** |
| ECR + ECS Fargate                 | 高     | ~$20-30     | 需要 auto-scaling + ALB       |

**遷移理由**：
- 不需要管 EC2 主機（OS 更新、Docker 安裝、SSM Agent）
- Push image 到 ECR 後，App Runner 自動部署
- 內建 HTTPS、health check、auto-scaling
- 成本與最小 EC2 相當

### 21.2 ECR + App Runner 流程

```
git push main
    ↓
GitHub Actions (.github/workflows/deploy-seo-api.yaml)
    ↓
docker build -t seo-insight-api:$TAG .
    ↓
ECR push（AWS 私有 registry）
    ↓
aws apprunner update-service
    ↓
App Runner 拉取新 image → 啟動容器 → health check → 切換流量
    ↓
https://<random>.awsapprunner.com（自動 HTTPS）
```

### 21.3 Dockerfile 設計要點

```dockerfile
FROM python:3.12-slim        # slim = 沒有不必要的系統套件
WORKDIR /app
COPY requirements_api.txt .  # 先 COPY 依賴，利用 layer cache
RUN pip install --no-cache-dir -r requirements_api.txt
COPY app/ ./app/             # 只 COPY API 程式碼
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**`.dockerignore` 必要性**：排除 `output/`、`raw_data/`、`.venv/` 等，
控制 image 在合理範圍。

### 21.4 資料層遷移路徑

> **當前（Phase 1）**：資料檔（qa_final.json、qa_embeddings.npy）需透過某種方式提供給容器。
> App Runner 不支援 volume mount，需選擇以下方案之一。

| 方案                     | 複雜度 | 資料更新方式           | 適用階段     |
| ------------------------ | ------ | ---------------------- | ------------ |
| 打包進 Docker image      | 最低   | 重建 image             | Phase 1 過渡 |
| S3 啟動時下載            | 低     | 上傳 S3，重啟容器      | Phase 1      |
| **Supabase (pgvector)**  | **中** | **API 即時寫入**       | **Phase 2（目標）** |

**Phase 2 Supabase 遷移計畫**：

資料透過 API 有即時更新需求，因此最終目標是遷移至 Supabase（PostgreSQL + pgvector）：

```
Phase 1（當前）                    Phase 2（Supabase）
qa_final.json → 記憶體 QAStore  →  Supabase qa_items table
qa_embeddings.npy → numpy       →  pgvector embedding column
store.search() → dot product    →  SELECT ... ORDER BY embedding <=> $1
store.load() → 檔案讀取         →  DB connection pool
```

**遷移邊界**：`app/core/store.py` 的 `QAStore` 是唯一抽象層。
遷移時只需替換 `QAStore` 內部實作，所有 router 和業務邏輯零修改：

```python
# Phase 1: store.py（當前）
class QAStore:
    def load(self): ...           # 從 JSON 檔案載入
    def search(self, vec): ...    # numpy dot product
    def hybrid_search(self, ...): # numpy + keyword boost

# Phase 2: store.py（Supabase 版）
class QAStore:
    def load(self): ...           # 建立 Supabase client connection
    def search(self, vec): ...    # SELECT ... ORDER BY embedding <=> $1
    def hybrid_search(self, ...): # pgvector + ts_rank 全文搜尋
```

**Supabase schema 預規劃**：

```sql
-- qa_items table（對應 qa_final.json 每筆 Q&A）
CREATE TABLE qa_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    category    TEXT,
    difficulty  TEXT,
    evergreen   BOOLEAN DEFAULT TRUE,
    source_date DATE,
    meeting_id  TEXT,
    tags        TEXT[],
    confidence  REAL,
    embedding   vector(1536),     -- pgvector
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 向量搜尋索引
CREATE INDEX ON qa_items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);

-- 全文搜尋索引（中文需搭配 pg_jieba 或 pgroonga）
CREATE INDEX ON qa_items USING gin (to_tsvector('simple', question || ' ' || answer));
```

### 21.5 GitHub Actions Secrets

| Secret                     | 用途                                         | 階段   |
| -------------------------- | -------------------------------------------- | ------ |
| `AWS_ACCESS_KEY_ID`        | AWS IAM 認證                                 | 所有   |
| `AWS_SECRET_ACCESS_KEY`    | AWS IAM 認證                                 | 所有   |
| `AWS_REGION`               | AWS 區域（如 `ap-northeast-1`）              | 所有   |
| `ECR_DOMAIN`               | `xxxx.dkr.ecr.<region>.amazonaws.com`        | 所有   |
| `APP_RUNNER_SERVICE_ARN`   | App Runner 服務 ARN                          | 所有   |
| `APP_RUNNER_ECR_ROLE_ARN`  | App Runner 拉 ECR image 的 IAM Role          | 所有   |
| `OPENAI_API_KEY`           | OpenAI API（RAG chat 需要）                  | 所有   |
| `SEO_API_KEY`              | API 認證金鑰                                 | 所有   |
| `LMNR_PROJECT_API_KEY`     | Laminar 追蹤（選配）                         | 選配   |
| ~~`EC2_TAG_KEY/VALUE`~~    | ~~EC2 tag 篩選~~                             | 已移除 |
| ~~`OUTPUT_DATA_PATH`~~     | ~~EC2 data 路徑~~                            | 已移除 |

### 21.6 AWS 服務與 IAM 設定

**需要開通的 AWS 服務**：

| 服務           | 用途                  | 費用         |
| -------------- | --------------------- | ------------ |
| **ECR**        | Docker image 倉庫     | ~$0.10/GB/月 |
| **App Runner** | 無伺服器容器運行      | ~$5-7/月     |

**App Runner 服務設定**：
- Source: ECR private image
- Port: 8001
- Health check path: `/health`
- Min instances: 1
- Max instances: 1（低流量場景）

**IAM Role — App Runner ECR Access**：
- Trust: `build.apprunner.amazonaws.com`
- Policy: `AmazonEC2ContainerRegistryReadOnly`

**IAM User — GitHub Actions**：
- `ecr:GetAuthorizationToken` + `ecr:BatchCheckLayerAvailability` + `ecr:PutImage` + `ecr:InitiateLayerUpload` + `ecr:UploadLayerPart` + `ecr:CompleteLayerUpload`
- `apprunner:UpdateService` + `apprunner:DescribeService`

### 21.7 歷史：ECR + EC2 SSM（已淘汰）

> 以下為 v0.3–v1.20 使用的 EC2 SSM 部署模式，保留作為參考。

<details>
<summary>展開 EC2 SSM 部署流程（已淘汰）</summary>

```
git push main → GitHub Actions → docker build → ECR push
    → SSM send-command → EC2 執行：
      docker pull $IMAGE:$TAG
      docker run -d -v /data/output:/app/output:ro ...
```

EC2 透過 volume mount 掛載資料檔，SSM 遠端執行部署命令。
此模式需要管理 EC2 主機（OS 更新、Docker 安裝、SSM Agent），
已於 2026-03-03 遷移至 App Runner。

</details>

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

## 23. API 安全：Auth + Rate Limit（v1.11 已實作，2026-02-28）

> v1.8 識別的 CRITICAL 缺口，v1.11 完整修復。實作位置：`app/core/security.py`、`app/core/limiter.py`、`app/core/schemas.py`。

### OWASP API Security Top 10（2023）識別的風險 — 修復狀態

| API 風險                                             | v1.8 現況                          | v1.11 修復方式                                          | 狀態      |
| ---------------------------------------------------- | ---------------------------------- | ------------------------------------------------------- | --------- |
| **API2:2023 — Broken Authentication**                | `/api/v1/*` 無 API Key 驗證        | `verify_api_key` FastAPI dependency，`X-API-Key` header | ✅ 已修復 |
| **API4:2023 — Unrestricted Resource Consumption**    | `/api/v1/chat` 無速率限制          | slowapi：chat 20/min・search/qa 60/min                  | ✅ 已修復 |
| **API3:2023 — Broken Object Property Authorization** | 例外洩漏 Python traceback          | 全局 `@app.exception_handler(Exception)` 統一 500       | ✅ 已修復 |
| **API1:2023 — Broken Object Level Authorization**    | `GET /api/v1/qa/{id}` 無細粒度權限 | 所有 QA 資料公開（低風險，當前不需修復）                | ℹ️ 可接受 |

### Phase A — API Key 認證（`app/core/security.py`）

**關鍵設計決策**：避免循環相依，`verify_api_key` 中 lazy import `app.config`。
開發模式（`SEO_API_KEY` 未設定）→ 自動放行 + 警告，方便本地開發。

```python
# app/core/security.py
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    from app import config as app_config  # lazy import 防止 circular
    expected: str = app_config.API_KEY
    if not expected:
        # 未設定 → 開發模式放行，生產環境應設定！
        logger.warning("SEO_API_KEY is not set — authentication DISABLED")
        return ""
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key
```

**掛載方式**（`app/main.py`）：統一在 `include_router` 時掛上，router 本身不需感知 auth：

```python
_auth = [Depends(verify_api_key)]
app.include_router(search.router, dependencies=_auth)
app.include_router(chat.router, dependencies=_auth)
app.include_router(qa.router, dependencies=_auth)
# /health 不在此列，不需認證
```

**設定**（`.env`）：

```
SEO_API_KEY=your-secret-api-key-here   # openssl rand -hex 32 生成
```

### Phase B — Rate Limiting（`app/core/limiter.py`）

**設計重點**：`limiter` 抽成獨立模組，避免 `app.main` ← routers ← `app.main` 循環相依。

```python
# app/core/limiter.py  ← 單例，各 router import
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)

# app/main.py
from app.core.limiter import limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# app/routers/chat.py
from app.core.limiter import limiter

@router.post("")
@limiter.limit("20/minute")
async def chat(req: ChatRequest, request: Request) -> ApiResponse[ChatResponse]:
    ...
```

**速率表**（符合 `plans/completed/api-security.md` 設計）：

| Endpoint              | Limit         | 說明              |
| --------------------- | ------------- | ----------------- |
| `POST /api/v1/chat`   | 20/min per IP | 消耗 OpenAI token |
| `POST /api/v1/search` | 60/min per IP | 純語意搜索        |
| `GET /api/v1/qa`      | 60/min per IP | 列表查詢          |

命中限制時回傳 **429 Too Many Requests**（RFC 6585）。

### Phase C — 全局 Exception Handler（`app/main.py`）

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)   # 伺服器端完整 log
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "Internal server error", "meta": {}},
    )
```

**測試策略**：使用 `TestClient(app, raise_server_exceptions=False)` 讓測試能接到 500 response（starlette 參數名稱，非 `raise_server_errors`）。

### Phase D — Response Envelope（`app/core/schemas.py`）

採用 Pydantic Generic Model，型別安全且 OpenAPI 文件自動生成：

```python
# app/core/schemas.py
from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field
import uuid

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    meta: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(data=data, error=None,
                   meta={"request_id": str(uuid.uuid4()), "version": "1.0"})

    @classmethod
    def fail(cls, message: str) -> "ApiResponse[None]":
        return cls(data=None, error=message,
                   meta={"request_id": str(uuid.uuid4()), "version": "1.0"})
```

**回應格式**：

```json
{
  "data": { "items": [...], "total": 3 },
  "error": null,
  "meta": { "request_id": "550e8400-...", "version": "1.0" }
}
```

### 測試覆蓋（`tests/test_api_security.py`）— 17 個測試

- `test_no_key_returns_401` / `test_wrong_key_returns_401` / `test_correct_key_returns_200`
- `test_401_body_does_not_leak_traceback`
- `test_health_does_not_require_auth`（/health 不需認證）
- `test_{search,chat,qa_single,qa_categories}_requires_auth`（4 個 endpoint）
- `test_unhandled_exception_returns_500_without_traceback`（Phase C）
- `test_successful_response_has_data_key` / `test_meta_has_request_id_and_version`（Phase D）

**conftest.py 調整**：`client` fixture 改用 `monkeypatch` 注入 `SEO_API_KEY`，並在 `TestClient` context 前 `c.headers.update(API_KEY_HEADER)` 預設帶入 key，所有現有測試無需逐一修改。

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

**FastAPI（`app/main.py`）—重要：initialize() 必須在所有 app import 之前**：

> **❗屏障**：`Laminar.initialize()` 會 monkey-patch openai / anthropic 等 SDK。
> 若在 `from app.routers import chat`（間接 import openai）之後才初始化，patch 失效，
> 導致 dashboard Top LLM spans / Tokens / Cost 全空白。

```python
# app/main.py 頂部，所有其他 import 之前
import os
_lmnr_key = os.getenv("LMNR_PROJECT_API_KEY", "")
try:
    from lmnr import Laminar
    if _lmnr_key:
        Laminar.initialize(project_api_key=_lmnr_key)
except ImportError:
    Laminar = None  # type: ignore

# — 之後才是所有 FastAPI / app.routers 等 import —
from fastapi import FastAPI
from app.routers import chat, qa, search
# ...
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

| 變數                   | 用途                            | 必要性                              |
| ---------------------- | ------------------------------- | ----------------------------------- |
| `LMNR_PROJECT_API_KEY` | Laminar tracing + evals         | 無此 key 時 silently skip，不 crash |
| `OPENAI_API_KEY`       | eval_chat.py + pipeline scripts | eval_chat.py 和 pipeline 必需       |
