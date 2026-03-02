# API Security Plan

> 來源：v1.8 Architect Review（2026-02-28）
> 前置計畫：`plans/in-progress/seo-insight.md` Phase 1（Auth + Rate Limit 已規劃但未實作）
> 狀態：**待實作**

---

## 背景

v1.8 架構審查（`research/06-project-architecture.md` 第 23 節）發現 API 層存在三個安全缺口：

| 缺口           | OWASP 分類                                     | 說明                                               |
| -------------- | ---------------------------------------------- | -------------------------------------------------- |
| 無認證         | API2:2023 Broken Authentication                | 任何人可呼叫 `/api/v1/chat`，直接消耗 OpenAI token |
| 無速率限制     | API4:2023 Unrestricted Resource Consumption    | burst 攻擊可耗盡 OpenAI 月額度                     |
| 錯誤訊息未遮蔽 | API3:2023 Broken Object Property Authorization | 未捕獲的例外會洩漏 Python traceback                |

**業界支撐**：OWASP API Security Top 10（2023）、RFC 6585（HTTP 429）、Microsoft REST API Guidelines（2024）。

### 兩條使用路徑的安全現況對比

本專案有兩條獨立的使用路徑，安全考量不同：

#### 路徑 1：API 層（網路暴露）— ⚠️ CRITICAL 缺口

```
前端 / 外部呼叫 → FastAPI /api/v1/* → OpenAI
```

**缺口**：無 Auth、無 Rate Limit、錯誤訊息洩漏（本 plan 處理）

#### 路徑 2：本地 CLI / 直接執行（無網路暴露）— ✅ 已防護

```
make pipeline / scripts/*.py / slash commands → 直接讀寫本地檔案
```

**已有防護**（v0.8 以來）：

- SSRF 防護：Google Sheets domain 白名單 + sheet_id/gid 格式驗證（`04_generate_report.py` L71-130）
- JSON schema 驗證：Structured Output strict mode，100% 符合才接受（`openai_helper.py`）
- Env fail-fast：PEP 562 lazy loading，只驗證當前 step 所需的 API key（`config.py`）
- `.env` 隔離：`.gitignore` 排除，未簽入版控

**剩下的低風險問題**（內部工具，不緊急）：

- **Prompt injection from Notion**：內容直接進 LLM prompt，但前提是 Notion 存取權已被入侵（Notion 層面防護）
- **`.env` 文件權限**：建議 `chmod 600`（執行腳本的人本身就有寫入權，攻擊面極小）
- **Path traversal in CLI**：`--output` 參數可指定任意路徑，但本地執行者權限本身就包含此操作

**結論**：路徑 2 安全風險遠低於路徑 1，主要威脅來自網路暴露（API），本 plan 專注解決 API 層缺口。

---

## 實作清單

### Phase A — CRITICAL：API Key 認證（估計 2h）

**目標**：所有 endpoint 必須帶 `X-API-Key` header，否則回傳 401。

**實作位置**：`app/core/security.py`（新增）、`app/main.py`（掛 dependency）

```python
# app/core/security.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    expected = config.API_KEY  # lazy env
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key
```

```python
# app/main.py — 在 router include 時掛上 dependency
from app.core.security import verify_api_key

app.include_router(
    search_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    chat_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    qa_router,
    prefix="/api/v1",
    dependencies=[Depends(verify_api_key)],
)
```

**config.py 新增**：

```python
"API_KEY": _LazyEnv("SEO_API_KEY", required=True),
```

**.env.example 新增**：

```
SEO_API_KEY=your-secret-api-key-here
```

**測試**：

- 無 header → 401
- 錯誤 key → 401
- 正確 key → 200

---

### Phase B — HIGH：Rate Limiting（估計 2h）

**目標**：防止 burst 消耗 OpenAI 額度。

**套件**：`slowapi`（FastAPI 官方推薦，基於 `limits` 和 `redis` / in-memory 後端）

**安裝**：

```bash
pip install slowapi
```

**Rate 設定**（對齊 plans/in-progress/seo-insight.md 第 2.4 節）：

| Endpoint              | Limit         | 說明              |
| --------------------- | ------------- | ----------------- |
| `POST /api/v1/chat`   | 20/min per IP | 消耗 OpenAI token |
| `POST /api/v1/search` | 60/min per IP | 純語意搜索        |
| `GET /api/v1/qa`      | 60/min per IP | 列表查詢          |

**實作位置**：`app/main.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

```python
# app/routers/chat.py
from app.main import limiter

@router.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, ...):
    ...
```

**回應**：429 Too Many Requests（RFC 6585）

---

### Phase C — HIGH：全局 Exception Handler（估計 1h）

**目標**：未預期例外不洩漏 Python traceback。

```python
# app/main.py
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "data": None},
    )
```

---

### Phase D — MEDIUM：Response Envelope（估計 2h）

**目標**：統一所有 API 回應格式（Microsoft REST API Guidelines 2024）。

**目標格式**：

```json
{
  "data": { ... },
  "error": null,
  "meta": { "request_id": "uuid", "version": "1.0" }
}
```

**實作位置**：`app/core/schemas.py`（新增通用 `ApiResponse[T]`）

```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    error: Optional[str] = None
    meta: dict = {}
```

**影響**：所有 router 的回傳型別需更新，前端整合時一起做。

---

## 優先順序

```
Phase A（Auth）→ Phase B（Rate Limit）→ Phase C（Exception Handler）→ Phase D（Envelope）
```

Phase A + B + C 可在同一個 PR 完成（共 ~5h），Phase D 建議在前端整合前一起做。

---

## 相關改進（MEDIUM，非安全）

這些來自 v1.8 Architect Review，與安全無關但同樣重要：

| 項目                  | 說明                                                                              | 估計 | 優先   |
| --------------------- | --------------------------------------------------------------------------------- | ---- | ------ |
| Golden set 擴充       | extraction 5→20 筆，report 5→10 筆，提升統計顯著性（n≥30 原則）                   | 3h   | MEDIUM |
| Hybrid Search → RRF   | 線性加權改為 Reciprocal Rank Fusion（Cormack 2009, SIGIR），消除 score scale 問題 | 4h   | MEDIUM |
| Prometheus metrics    | `/metrics` endpoint，追蹤 P50/P95/P99 延遲、cache hit rate、token usage           | 2h   | MEDIUM |
| `app/config.py` 合併  | 與 `config.py` 重複定義 `OPENAI_API_KEY` 等，統一為 lazy env                      | 1h   | MEDIUM |
| Admin reload endpoint | `POST /admin/reload` 讓 pipeline 更新後 API 熱載，不需重啟                        | 1h   | LOW    |

---

## 測試計畫

- [ ] Phase A：`tests/test_api_security.py` — 無 key / 錯誤 key / 正確 key 各場景
- [ ] Phase B：`tests/test_rate_limit.py` — 模擬 burst 請求觸發 429
- [ ] Phase C：`tests/test_exception_handler.py` — 模擬內部錯誤確認無 traceback 洩漏
- [ ] Phase D：所有現有 API 測試更新為 envelope 格式

---

## 連結

- 原始計畫：`plans/in-progress/seo-insight.md` Phase 1（Auth + Rate Limit 已規劃，未實作）
- 架構決策：`research/06-project-architecture.md` 第 23 節 G（OWASP API Security）
- 部署安全範例：`research/07-deployment.md` 第 23 章（FastAPI Auth + Rate Limit 實作）
- 相關計畫：`plans/active/cache-redis.md`（Phase B Rate Limit 後端若要改用 Redis 可對照）
