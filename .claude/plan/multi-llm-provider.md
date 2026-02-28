# 實作計畫：Multi-LLM Provider Support

> 日期：2026-02-28
> 狀態：待確認

---

## 目標

讓系統支援兩種 LLM 提供商：
1. **OpenAI**（現有，`OPENAI_API_KEY`）
2. **Anthropic / Claude**（新增，`ANTHROPIC_API_KEY`）

Docker 使用者只需設定 `ANTHROPIC_API_KEY`，不需要 OpenAI API Key，即可完整使用 chat、search、pipeline 功能。

---

## 技術挑戰分析

### 挑戰一：Embedding 維度
- OpenAI `text-embedding-3-small`：**1536 維**
- Anthropic **不提供** embedding API
- 解法：引入 `sentence-transformers`（本地端）作為 embedding backend
  - 建議模型：`BAAI/bge-m3`（多語系，1024 維）或 `all-MiniLM-L6-v2`（英文，384 維）
  - 切換 embedding provider 時須重新計算 `qa_embeddings.npy`

### 挑戰二：Structured Output（JSON Schema）
- OpenAI：`response_format={"type": "json_object"}` 強制 JSON
- Anthropic：透過 prompt 要求 JSON + 驗證（無強制 schema，但 Claude 遵守率高）
- 解法：抽象層統一介面，各 provider 自行處理 structured output 細節

### 挑戰三：Embedding 維度不相容
- 現有 `qa_embeddings.npy` 是 OpenAI 1536 維
- 切換到 local embedding 後維度不同，向量餘弦相似度不可混用
- 解法：
  - 分開命名：`qa_embeddings.npy`（OpenAI）、`qa_embeddings_local.npy`（local）
  - 啟動時自動偵測 provider 並載入對應 .npy
  - 提供 `make re-embed` 指令重新計算

---

## 架構設計

### 新增抽象層

```
utils/
├── llm_provider.py        # NEW: 同步 Chat completion 抽象
├── async_llm_provider.py  # NEW: 非同步 Chat completion 抽象（供 app/ 用）
├── embedding_provider.py  # NEW: Embedding 抽象（同步 + 非同步）
└── openai_helper.py       # MODIFY: 改用 llm_provider + embedding_provider
```

### Provider 介面

```python
# utils/llm_provider.py（Protocol）
class ChatProvider(Protocol):
    def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        json_mode: bool = False,
    ) -> str: ...

# utils/embedding_provider.py（Protocol）
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
    def embed_one(self, text: str) -> list[float]: ...
    @property
    def dim(self) -> int: ...
```

### Provider 實作

| Class | File | Backend |
|-------|------|---------|
| `OpenAIChatProvider` | `utils/llm_provider.py` | openai SDK |
| `AnthropicChatProvider` | `utils/llm_provider.py` | anthropic SDK |
| `OpenAIEmbeddingProvider` | `utils/embedding_provider.py` | openai SDK |
| `LocalEmbeddingProvider` | `utils/embedding_provider.py` | sentence-transformers |
| `AsyncOpenAIChatProvider` | `utils/async_llm_provider.py` | openai AsyncOpenAI |
| `AsyncAnthropicChatProvider` | `utils/async_llm_provider.py` | anthropic AsyncAnthropic |
| `AsyncOpenAIEmbeddingProvider` | `utils/embedding_provider.py` | openai async |
| `AsyncLocalEmbeddingProvider` | `utils/embedding_provider.py` | sentence-transformers (run_in_executor) |

### Provider 選擇邏輯

```python
# 由環境變數決定
LLM_PROVIDER=openai|anthropic        # 決定 chat completion
EMBEDDING_PROVIDER=openai|local      # 決定 embedding
# 預設：EMBEDDING_PROVIDER 跟隨 LLM_PROVIDER（openai→openai, anthropic→local）
```

### 模型對應表（Anthropic mode）

| OpenAI model | Anthropic 對應 | 環境變數 |
|-------------|---------------|---------|
| gpt-5.2 | claude-sonnet-4-6 | `ANTHROPIC_MAIN_MODEL` |
| gpt-5-mini | claude-haiku-4-5-20251001 | `ANTHROPIC_FAST_MODEL` |
| gpt-5-nano | claude-haiku-4-5-20251001 | `ANTHROPIC_NANO_MODEL` |

---

## 實作步驟

### Phase 1：Provider 抽象層（utils/）

**Step 1.1** 新增 `utils/llm_provider.py`
- `ChatProvider` Protocol（同步）
- `OpenAIChatProvider`：包裝現有 openai 呼叫
- `AnthropicChatProvider`：用 `anthropic.Anthropic` SDK，json_mode 用 prompt 強制
- `get_chat_provider()` factory function（讀 `LLM_PROVIDER` env var）

**Step 1.2** 新增 `utils/embedding_provider.py`
- `EmbeddingProvider` Protocol（含 `.dim` property）
- `OpenAIEmbeddingProvider`：包裝現有 openai embeddings API
- `LocalEmbeddingProvider`：用 `sentence-transformers`，預設模型 `BAAI/bge-m3`
- `AsyncOpenAIEmbeddingProvider`、`AsyncLocalEmbeddingProvider`
- `get_embedding_provider()` factory（讀 `EMBEDDING_PROVIDER` env var）

**Step 1.3** 新增 `utils/async_llm_provider.py`
- `AsyncChatProvider` Protocol
- `AsyncOpenAIChatProvider`（AsyncOpenAI）
- `AsyncAnthropicChatProvider`（AsyncAnthropic）
- `get_async_chat_provider()` factory

---

### Phase 2：重構 utils/openai_helper.py

改名概念：`openai_helper.py` 保留原名（向下相容），但內部改用 provider。

**Step 2.1** 修改 `extract_qa_from_text()`
- 改用 `get_chat_provider().complete()` 取代直接呼叫 `_client().chat.completions.create()`
- 同樣改 `merge_similar_qas()`、`classify_qa()`

**Step 2.2** 修改 `get_embeddings()`
- 改用 `get_embedding_provider().embed()` 取代直接呼叫 openai embeddings

**Step 2.3** 保持函式簽名不變（external interface 不破壞 scripts/）

---

### Phase 3：重構 app/core/chat.py

**Step 3.1** 移除 `AsyncOpenAI` 直接依賴
- 改用 `get_async_chat_provider()`
- 改用 `AsyncEmbeddingProvider`

**Step 3.2** `get_embedding()` → 呼叫 `_async_embed_provider.embed_one()`

**Step 3.3** `rag_chat()` → 呼叫 `_async_chat_provider.complete()`

---

### Phase 4：Config 更新

**Step 4.1** 修改 `config.py`
- `OPENAI_API_KEY`：從 `_require_env()` 改為 `_get_optional_env()`（允許空值）
- 新增：`LLM_PROVIDER`、`EMBEDDING_PROVIDER`
- 新增：`ANTHROPIC_API_KEY`、`ANTHROPIC_MAIN_MODEL`、`ANTHROPIC_FAST_MODEL`
- 新增：`LOCAL_EMBEDDING_MODEL`（default: `BAAI/bge-m3`）
- 啟動驗證：至少一個 API key 存在（OpenAI 或 Anthropic）

**Step 4.2** 修改 `app/config.py`
- 同上，新增 Anthropic 相關設定
- 新增 `EMBEDDING_PROVIDER`、`LOCAL_EMBEDDING_MODEL`

---

### Phase 5：Embedding 維度相容

**Step 5.1** 修改 `app/core/store.py`
- `load()` 時判斷 `EMBEDDING_PROVIDER`
  - `openai` → 載入 `qa_embeddings.npy`（1536 維）
  - `local` → 載入 `qa_embeddings_local.npy`（1024 維，bge-m3）
- 新增 `embedding_dim` 屬性，Search 時驗證 query vector 維度

**Step 5.2** 新增 Makefile target
```makefile
re-embed:  ## 使用當前 EMBEDDING_PROVIDER 重新計算 qa_embeddings
	@echo "Re-computing embeddings with provider: $${EMBEDDING_PROVIDER:-openai}"
	.venv/bin/python scripts/recompute_embeddings.py
```

**Step 5.3** 新增 `scripts/recompute_embeddings.py`
- 載入 `output/qa_final.json`
- 使用當前 embedding provider 重新計算所有 Q&A 的 embedding
- 根據 provider 儲存為 `qa_embeddings.npy` 或 `qa_embeddings_local.npy`

---

### Phase 6：Docker 更新

**Step 6.1** 修改 `Dockerfile`
```dockerfile
# 新增 sentence-transformers 和 anthropic
COPY requirements_api.txt .
RUN pip install --no-cache-dir -r requirements_api.txt

# 可選：預下載 local embedding model（避免 runtime 首次下載慢）
ARG PRELOAD_LOCAL_MODEL=""
RUN if [ -n "$PRELOAD_LOCAL_MODEL" ]; then \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"; \
    fi
```

**Step 6.2** 新增 `docker-compose.yml`
```yaml
version: '3.8'
services:
  api:
    build: .
    ports: ["8001:8001"]
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-openai}
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - LMNR_PROJECT_API_KEY=${LMNR_PROJECT_API_KEY:-}
    volumes:
      - ./output:/app/output  # 掛載 qa_final.json + qa_embeddings*.npy
```

**Step 6.3** 新增 `.env.claude.example`（Claude mode 範例）
```env
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=local
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MAIN_MODEL=claude-sonnet-4-6
ANTHROPIC_FAST_MODEL=claude-haiku-4-5-20251001
```

---

### Phase 7：依賴更新

**Step 7.1** 修改 `requirements.txt`
```
anthropic>=0.42.0
sentence-transformers>=3.0.0  # optional, for local embeddings
```

**Step 7.2** 修改 `requirements_api.txt`
```
anthropic>=0.42.0
sentence-transformers>=3.0.0
```

---

### Phase 8：測試更新

**Step 8.1** 修改 `tests/conftest.py`
- 新增 fixture：`mock_anthropic_chat_provider`、`mock_local_embedding_provider`
- 新增 fixture：允許在 OpenAI 或 Anthropic mode 下執行

**Step 8.2** 修改現有測試
- `tests/test_core.py`：provider interface 測試
- `tests/test_api_chat.py`：確保兩種 provider 都 mock 正確
- `tests/test_api_search.py`：確保 embedding provider mock 正確

**Step 8.3** 新增 `tests/test_llm_provider.py`
- `OpenAIChatProvider` 和 `AnthropicChatProvider` 的單元測試
- `LocalEmbeddingProvider` 的維度驗證測試

---

## 使用者流程（完成後）

### OpenAI 模式（現有）
```bash
# .env
OPENAI_API_KEY=sk-...
LLM_PROVIDER=openai  # 可省略（預設值）

docker-compose up
```

### Claude 模式（新）
```bash
# 第一次：重新計算 embedding（僅需一次）
EMBEDDING_PROVIDER=local make re-embed

# .env
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=anthropic
EMBEDDING_PROVIDER=local

docker-compose up
```

### Pipeline 腳本（Claude 模式）
```bash
LLM_PROVIDER=anthropic make step2  # 萃取 Q&A（用 Claude）
LLM_PROVIDER=anthropic make step3  # 去重分類（用 Claude）
```

---

## 關鍵檔案對照表

| 檔案 | 操作 | 說明 |
|------|------|------|
| `utils/llm_provider.py` | 新增 | ChatProvider Protocol + OpenAI/Anthropic 實作 |
| `utils/async_llm_provider.py` | 新增 | AsyncChatProvider Protocol + 實作 |
| `utils/embedding_provider.py` | 新增 | EmbeddingProvider Protocol + OpenAI/Local 實作 |
| `scripts/recompute_embeddings.py` | 新增 | 重算 embedding 腳本 |
| `docker-compose.yml` | 新增 | Multi-provider compose |
| `.env.claude.example` | 新增 | Claude mode 設定範例 |
| `utils/openai_helper.py` | 修改 | 改用 provider 抽象 |
| `app/core/chat.py` | 修改 | 改用 async provider |
| `app/core/store.py` | 修改 | 根據 provider 載入對應 .npy |
| `config.py` | 修改 | OPENAI_API_KEY 非強制，加 Anthropic 設定 |
| `app/config.py` | 修改 | 加 Anthropic 設定 |
| `Dockerfile` | 修改 | 加 anthropic + sentence-transformers |
| `requirements.txt` | 修改 | 加 anthropic, sentence-transformers |
| `requirements_api.txt` | 修改 | 加 anthropic, sentence-transformers |
| `Makefile` | 修改 | 加 re-embed target |
| `tests/conftest.py` | 修改 | 加新 provider fixtures |
| `tests/test_llm_provider.py` | 新增 | Provider 單元測試 |

---

## 風險與緩解

| 風險 | 緩解 |
|------|------|
| Anthropic JSON 遵守率 < 100% | 加 retry（最多 3 次）+ fallback 解析 |
| Local embedding model 首次下載慢 | Dockerfile ARG PRELOAD_LOCAL_MODEL 預先下載 |
| Embedding 維度切換後搜尋品質下降 | 文件說明需重跑評估；維度資訊存入 metadata |
| sentence-transformers 增加 Docker image 大小 | 使用 multi-stage build 或 optional install |
| 現有測試假設 OpenAI provider | 以 Provider mock 取代 OpenAI mock，向下相容 |

---

## 成功標準

- [ ] `LLM_PROVIDER=anthropic docker-compose up` 正常啟動
- [ ] `/api/v1/chat` 使用 Claude 回答，sources 正確
- [ ] `/api/v1/search` 使用 local embedding 搜尋，結果合理
- [ ] 所有現有測試通過（OpenAI mock mode）
- [ ] 新增測試覆蓋 Anthropic + local embedding provider
- [ ] `make re-embed` 成功產生 `qa_embeddings_local.npy`
