# Cache & Redis 架構設計計畫

> 目標：讓每次 pipeline 產生的版本可被記憶、避免重複消耗 LLM token；
> 同時為 API 層提供可擴展的 cache 架構。

---

## 一、現況分析：目前需要 Redis 嗎？

**短答：目前不需要，但有明確的升級觸發條件。**

| 面向 | 現況 | 潛在痛點 |
|------|------|----------|
| Pipeline Step 2 Q&A 萃取 | 每次執行都重跑 OpenAI，已有 `qa_per_meeting/*.json` 作為隱式 cache | 重新執行時若 Markdown 沒改，仍會重建（浪費 token） |
| Pipeline Step 3 去重+分類 | 批量呼叫 embedding + LLM merge；輸出到 `qa_final.json` | 每次跑都重算全量 embedding |
| Pipeline Step 4 週報生成 | 同一份指標 + 同版本知識庫 → 每次都重新產生報告 | 相同輸入無 cache，反覆消耗 token |
| API Chat | 每次 `/chat` 都呼叫 embedding API + GPT | 相同問題重複收費；無 server-side session |
| API Session | history 由 client 攜帶，server 無狀態 | 單機 OK；多實例後 session 無法共享 |
| 部署規模 | 單一 uvicorn process，in-memory store | scale out 後 QAStore 各自載入，embedding cache 無法共享 |

**觸發升級 Redis 的條件：**
1. API 需要 horizontal scaling（多 pod/process）
2. Chat 有大量重複問題（命中率 > 30% 時 cache 值回）
3. pipeline 需要 scheduled 定期執行（避免重複萃取）
4. 需要 server-side session（對話記憶跨會話保留）

---

## 二、Redis 常用模式介紹

### 2.1 String — 最基本的 KV Cache

```
SET key value EX 3600     # TTL 1小時
GET key
SETNX key value           # set-if-not-exist（分散式鎖的建構塊）
```

**本專案用途：**
- LLM response cache：`hash(prompt) → json_response`
- Embedding cache：`hash(text) → base64_encoded_vector`
- 週報 cache：`hash(metrics_tsv + qa_version) → report_markdown`

---

### 2.2 Hash — 結構化物件

```
HSET session:abc user_id U1 created_at 1234567890
HGET session:abc user_id
HGETALL session:abc
EXPIRE session:abc 86400  # TTL 1天
```

**本專案用途：**
- Session store：`session:{id}` → `{history: [...], created_at, last_active}`
- Pipeline run metadata：`pipeline:run:{run_id}` → `{step, status, started_at, token_used}`

---

### 2.3 Sorted Set — 排行 / TTL 管理

```
ZADD leaderboard 95.5 "canonical tag 設定"
ZRANGE leaderboard 0 9 WITHSCORES REV   # top-10
```

**本專案用途：**
- 熱門查詢追蹤：記錄使用者問了哪些問題、哪些 Q&A 被取用最多次
- 決定哪些 embedding 值得納入 cache（依使用頻率淘汰冷門 cache）

---

### 2.4 Pub/Sub — 事件通知

```python
# publisher（pipeline）
redis.publish("pipeline:events", json.dumps({"step": 2, "status": "done"}))

# subscriber（API / dashboard）
for msg in redis.subscribe("pipeline:events"):
    handle(msg)
```

**本專案用途：**
- Pipeline 完成通知 → API server 自動熱載 QAStore（不需要重啟）
- Step 4 週報產出 → 推送通知

---

### 2.5 Streams — 持久化事件日誌

```
XADD audit:chat * user_id U1 question "CTR 下降？" source_ids "[1,3,5]"
XREAD COUNT 100 STREAMS audit:chat 0
```

**本專案用途：**
- 取代目前的 JSONL 稽核日誌（`output/access_logs/`）
- 支援 consumer group，多個消費者（分析、告警）同時讀取

---

### 2.6 TTL 策略（所有資料類型通用）

| Cache 類型 | 建議 TTL | 理由 |
|-----------|---------|------|
| Embedding（查詢向量） | 24 小時 | 相同問題在同一天多次出現機率高 |
| RAG 答案 | 2 小時 | 知識庫可能更新 |
| Session（對話歷史） | 7 天 | 合理的對話保留期 |
| Pipeline 結果（週報） | 30 天 | 同份指標不會重算 |
| Meeting Q&A 萃取 | 永久（以 hash 為 key） | 只要 Markdown 沒改就不重萃取 |

---

## 三、Cache 架構設計

### 3.1 整體架構圖

```
┌─────────────────────────────────────────────────────┐
│                 Pipeline (CLI)                       │
│                                                     │
│  Step 1 ──► Notion → Markdown                       │
│               └─ fingerprint: page_id + last_edited │
│                                                     │
│  Step 2 ──► Markdown → Q&A                         │
│               └─ cache key: sha256(markdown_text)   │
│               └─ miss → OpenAI → store result       │
│                                                     │
│  Step 3 ──► Q&A → Embeddings → Dedup + Classify    │
│               └─ embed cache: sha256(qa_text)       │
│               └─ classify cache: sha256(qa_text)    │
│                                                     │
│  Step 4 ──► Metrics + QA → Weekly Report            │
│               └─ cache key: sha256(metrics + qa_v)  │
│                                                     │
└─────────────────────────────────────────────────────┘
           │  pipeline:events  (Pub/Sub)
           ▼
┌─────────────────────────────────────────────────────┐
│                   Redis                             │
│                                                     │
│  cache:extraction:{md_hash}  → qa_pairs JSON       │
│  cache:embedding:{text_hash} → float32 vector      │
│  cache:classify:{qa_hash}    → category/difficulty │
│  cache:report:{input_hash}   → markdown text       │
│  session:{session_id}        → history Hash        │
│  pipeline:run:{run_id}       → metadata Hash       │
└─────────────────────────────────────────────────────┘
           ▲
           │
┌─────────────────────────────────────────────────────┐
│                 API (FastAPI)                        │
│                                                     │
│  /chat  ──► embed query (cache hit check first)     │
│          ──► hybrid search (in-memory, no cache)    │
│          ──► LLM answer (semantic cache)            │
│          ──► session store                          │
│                                                     │
│  /search ──► embed query (cache)                    │
│           ──► return QAItems (no LLM cost)          │
└─────────────────────────────────────────────────────┘
```

---

### 3.2 Pipeline Cache 層設計

#### Phase 1：無 Redis 版本（立即可實作）

用磁碟 JSON 作為 deterministic cache，key = 內容 hash。

**實作位置：** `utils/pipeline_cache.py`

```python
# utils/pipeline_cache.py

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

CACHE_DIR = Path("output/.cache")

def _cache_key(namespace: str, content: str) -> str:
    h = hashlib.sha256(content.encode()).hexdigest()[:24]
    return h

def cache_get(namespace: str, content: str) -> Optional[Any]:
    key = _cache_key(namespace, content)
    path = CACHE_DIR / namespace / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None

def cache_set(namespace: str, content: str, value: Any) -> None:
    key = _cache_key(namespace, content)
    path = CACHE_DIR / namespace / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
```

**Step 2 整合範例：**

```python
# scripts/02_extract_qa.py 中的 process_single_meeting()

from utils.pipeline_cache import cache_get, cache_set

def process_single_meeting(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")

    # ── cache check ──
    cached = cache_get("extraction", content)
    if cached:
        print(f"  [cache hit] {md_path.name}")
        return cached

    # ── 實際呼叫 OpenAI ──
    result = extract_qa_from_text(content, title, date)

    # ── 寫入 cache ──
    cache_set("extraction", content, result)
    return result
```

**Step 4 整合範例：**

```python
# scripts/04_generate_report.py

import hashlib, json
from utils.pipeline_cache import cache_get, cache_set

def generate_report(metrics_tsv: str, qa_version: str) -> str:
    cache_input = metrics_tsv + qa_version
    cached = cache_get("report", cache_input)
    if cached:
        return cached["report_text"]

    report = _call_llm_to_generate(metrics_tsv, qa_version)
    cache_set("report", cache_input, {"report_text": report})
    return report
```

---

#### Phase 2：加入 Redis（當需要 scale 時）

**新增 `utils/redis_cache.py`，與 Phase 1 同介面：**

```python
# utils/redis_cache.py

import hashlib
import json
import os
from typing import Any, Optional

import redis

_client: Optional[redis.Redis] = None

def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0,
            decode_responses=True,
        )
    return _client

def cache_get(namespace: str, content: str, ttl: int = 0) -> Optional[Any]:
    r = _get_client()
    key = f"cache:{namespace}:{hashlib.sha256(content.encode()).hexdigest()[:24]}"
    raw = r.get(key)
    return json.loads(raw) if raw else None

def cache_set(namespace: str, content: str, value: Any, ttl: int = 0) -> None:
    r = _get_client()
    key = f"cache:{namespace}:{hashlib.sha256(content.encode()).hexdigest()[:24]}"
    serialized = json.dumps(value, ensure_ascii=False)
    if ttl > 0:
        r.setex(key, ttl, serialized)
    else:
        r.set(key, serialized)
```

**`config.py` 新增：**

```python
CACHE_BACKEND = os.getenv("CACHE_BACKEND", "disk")  # "disk" | "redis"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
```

**`utils/cache.py` — 統一入口（後端可切換）：**

```python
import config

if config.CACHE_BACKEND == "redis":
    from utils.redis_cache import cache_get, cache_set
else:
    from utils.pipeline_cache import cache_get, cache_set

__all__ = ["cache_get", "cache_set"]
```

---

### 3.3 API Cache 層設計

#### Embedding Cache（避免 embedding API 重複呼叫）

```python
# app/core/chat.py — 改造 get_embedding()

from utils.cache import cache_get, cache_set
import base64, numpy as np

async def get_embedding(text: str) -> np.ndarray:
    # 1. cache check
    cached = cache_get("embedding", text)
    if cached:
        raw = base64.b64decode(cached["v"].encode())
        return np.frombuffer(raw, dtype=np.float32).copy()

    # 2. 呼叫 OpenAI
    resp = await _client.embeddings.create(
        model=config.OPENAI_EMBEDDING_MODEL,
        input=text.strip(),
    )
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    norm = np.linalg.norm(vec)
    vec = vec / norm if norm > 0 else vec

    # 3. 存入 cache（TTL 24h）
    cache_set("embedding", text, {
        "v": base64.b64encode(vec.tobytes()).decode()
    }, ttl=86400)
    return vec
```

#### Semantic RAG Cache（問答級別 cache）

相同或高度相似的問題直接回傳 cache，不呼叫 GPT。

```python
# app/core/chat.py — rag_chat() 加 cache layer

async def rag_chat(message: str, history: list[dict] | None = None) -> dict:
    # 無歷史對話時才走 cache（multi-turn 對話不 cache）
    if not history:
        cached = cache_get("rag_answer", message)
        if cached:
            return cached

    # ... 正常 RAG 流程 ...
    result = {"answer": answer, "sources": sources}

    if not history:
        cache_set("rag_answer", message, result, ttl=7200)  # TTL 2h

    return result
```

---

### 3.4 Session 管理設計

目前 history 由 client 攜帶（無狀態），若需要 server-side session：

```python
# app/core/session.py （新增）

import json
import os
import uuid
from typing import Optional
import redis

_r = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), decode_responses=True)

SESSION_TTL = 7 * 24 * 3600  # 7 天

def create_session() -> str:
    session_id = str(uuid.uuid4())
    _r.hset(f"session:{session_id}", mapping={
        "history": "[]",
        "created_at": str(int(__import__("time").time())),
    })
    _r.expire(f"session:{session_id}", SESSION_TTL)
    return session_id

def get_history(session_id: str) -> list[dict]:
    raw = _r.hget(f"session:{session_id}", "history")
    return json.loads(raw) if raw else []

def append_history(session_id: str, role: str, content: str) -> None:
    history = get_history(session_id)
    history.append({"role": role, "content": content})
    _r.hset(f"session:{session_id}", "history", json.dumps(history))
    _r.expire(f"session:{session_id}", SESSION_TTL)
```

---

### 3.5 Pipeline 版本追蹤設計

每次 pipeline 執行記錄版本，防止用到舊版資料：

```python
# utils/pipeline_version.py （新增）

import hashlib
import json
from pathlib import Path
from datetime import datetime

VERSION_FILE = Path("output/.pipeline_versions.json")

def record_version(step: int, input_hash: str, output_path: str, token_used: int = 0) -> dict:
    """記錄 pipeline step 的執行版本"""
    versions = _load_versions()
    entry = {
        "step": step,
        "input_hash": input_hash,
        "output_path": output_path,
        "token_used": token_used,
        "timestamp": datetime.utcnow().isoformat(),
    }
    versions.setdefault(f"step{step}", []).append(entry)
    VERSION_FILE.write_text(json.dumps(versions, ensure_ascii=False, indent=2))
    return entry

def get_last_version(step: int) -> dict | None:
    versions = _load_versions()
    entries = versions.get(f"step{step}", [])
    return entries[-1] if entries else None

def _load_versions() -> dict:
    if VERSION_FILE.exists():
        return json.loads(VERSION_FILE.read_text())
    return {}
```

---

## 四、實作計畫（分三期）

### Phase 1：磁碟 Cache（立即可做，不需要 Redis）

**目標：讓 Step 2/4 不重複消耗 token**

| # | 任務 | 檔案 | 估計工時 |
|---|------|------|----------|
| 1 | 建立 `utils/pipeline_cache.py` | 新增 | 1h |
| 2 | Step 2 整合 cache（per-meeting 萃取） | `scripts/02_extract_qa.py` | 1h |
| 3 | Step 3 整合 embedding cache | `utils/openai_helper.py` | 1h |
| 4 | Step 4 整合 report cache | `scripts/04_generate_report.py` | 1h |
| 5 | 建立 `utils/pipeline_version.py` | 新增 | 1h |
| 6 | `.gitignore` 加入 `output/.cache/` | `.gitignore` | 5min |
| 7 | 測試：相同輸入跑兩次驗證 cache hit | `tests/test_cache.py` | 1h |

**預期效果：**
- Step 2 重跑時，未修改的 Markdown 全數命中 cache，節省 ~90% token
- Step 4 同一週指標重跑，直接回傳 cache，節省 100% token

---

### Phase 2：Redis Cache（當 API 需要 scale 時）

**觸發條件：** API 需要多 instance、chat 呼叫量顯著增加

| # | 任務 | 檔案 | 估計工時 |
|---|------|------|----------|
| 1 | 建立 `utils/redis_cache.py` | 新增 | 1h |
| 2 | 建立 `utils/cache.py` 統一入口 | 新增 | 30min |
| 3 | `config.py` 加入 CACHE_BACKEND / REDIS_* 設定 | `config.py` | 30min |
| 4 | API chat embedding cache | `app/core/chat.py` | 1h |
| 5 | API RAG answer semantic cache | `app/core/chat.py` | 1h |
| 6 | `docker-compose.yml` 加入 Redis service | 新增/修改 | 30min |
| 7 | 測試：Redis cache 命中率驗證 | `tests/test_redis_cache.py` | 1h |

---

### Phase 3：進階功能（視需求）

| 功能 | 說明 | 前提條件 |
|------|------|----------|
| Server-side Session | `app/core/session.py` + `/chat` route 改回傳 session_id | Phase 2 Redis 就緒 |
| Pipeline Auto-Reload | Step 3 完成後 Pub/Sub 通知 API 熱載 QAStore | Phase 2 Redis 就緒 |
| Audit Log → Redis Streams | 取代 JSONL 檔案，支援即時查詢 | Phase 2 Redis 就緒 |
| Semantic Dedup Cache | 去重時已計算過的 pair 不重算 cosine | Phase 1 磁碟 cache 先驗證 ROI |
| Hot Query Tracking | SortedSet 記錄問題頻率 → 優化知識庫 | Phase 2 |

---

## 五、不需要 Redis 的理由（目前）

以下是常見的「誤用 Redis」情境，本專案目前不屬於這些：

| 情境 | 為什麼目前不需要 |
|------|----------------|
| 分散式 Session | API 是 stateless single instance |
| Rate Limiting | 沒有公開 API，不需要 |
| Message Queue | Pipeline 是 CLI sequential，無 async job |
| Leaderboard | 使用量尚小，SQLite 或 JSON 更輕量 |
| Pub/Sub | 單進程不需要跨進程通訊 |

**結論：Phase 1 磁碟 cache 解決 80% 的 token 浪費問題，且無部署依賴。**
**Redis 在 Phase 2 才真正發揮價值（API scale out、embedding cache 共享）。**

---

## 六、Token 節省估算

| 步驟 | 目前每次消耗 | Cache 後 | 節省 |
|------|------------|---------|------|
| Step 2 全量萃取（30份會議） | ~150,000 tokens | ~0（全命中） | 100% |
| Step 2 增量（1份新會議） | ~5,000 tokens | 5,000 tokens | 0%（新內容） |
| Step 3 全量 embedding（300 QA） | ~30,000 tokens embed | ~0（版本未變） | 100% |
| Step 3 分類（300 QA） | ~60,000 tokens | ~0 | 100% |
| Step 4 週報生成 | ~8,000 tokens | 0（同週指標） | 100% |
| API chat（每次） | ~500 tokens | 0（相同問題） | ~30%（估計命中率） |

---

## 七、目錄結構變化

```
utils/
  pipeline_cache.py     # Phase 1：磁碟 KV cache
  redis_cache.py        # Phase 2：Redis KV cache（同介面）
  cache.py              # 統一入口（CACHE_BACKEND 切換）
  pipeline_version.py   # 版本追蹤

output/
  .cache/               # Phase 1 磁碟 cache（gitignored）
    extraction/         # Step 2 per-meeting Q&A 萃取結果
    embedding/          # 文字 → 向量 cache
    classify/           # Q&A 分類結果 cache
    report/             # 週報 cache

.env.example            # 新增 CACHE_BACKEND, REDIS_HOST, REDIS_PORT
```

---

*計畫產出日期：2026-02-28*
*適用版本：目前 seo-knowledge-insight 架構（單一 FastAPI + CLI pipeline）*
