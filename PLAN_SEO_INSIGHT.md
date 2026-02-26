# Implementation Plan: SEO Insight 後端 API + Evals 系統 + 部署方案

> 日期：2026-02-27  
> 最後更新：2026-02-25（部署方案改為 AWS ECS Fargate）  
> 狀態：**Draft — 待 Review**
> UI 位置：`/Documents/vocus-web-ui/pages/admin/seo/insight`

---

## 目錄

1. [Overview](#1-overview)
2. [Phase 1: API 設計](#2-phase-1-api-設計)
3. [Phase 2: Evals / Multi-Turn Evals 系統](#3-phase-2-evals--multi-turn-evals-系統)
4. [Phase 3: 部署與基礎設施](#4-phase-3-部署與基礎設施)
5. [成本估算](#5-成本估算)
6. [風險與緩解](#6-風險與緩解)
7. [Architecture Decision Records](#7-architecture-decision-records)
8. [Success Criteria](#8-success-criteria)

---

## 1. Overview

### 現狀

- 離線 Python pipeline（Steps 1–5），輸出 JSON/Markdown 檔案
- 知識庫 703 筆 Q&A，87 份會議紀錄，10 分類
- 無 API、無即時查詢、無 UI、無持續 eval
- 所有 prompt、embedding、評估邏輯封裝在 `utils/openai_helper.py` + `scripts/05_evaluate.py`

### 目標

將現有 pipeline 包裝成可被 `vocus-web-ui` 前端互動的 HTTP API，同時建立持續品質監控的 Evals 系統。

### 架構總覽

```
┌─────────────────────────────────────────────────────────────┐
│  vocus-web-ui (Next.js)                                     │
│  pages/admin/seo/insight                                    │
│   ├── Dashboard（知識庫總覽 + eval 趨勢）                    │
│   ├── Search（語意搜尋 + 對話式問答）                        │
│   ├── Report（週報生成 / 瀏覽）                              │
│   ├── Evals（品質儀表板 + multi-turn 測試）                  │
│   └── Pipeline（觸發 / 監控 pipeline 執行）                  │
└──────────────┬──────────────────────────────────────────────┘
               │ REST API (JSON)
               ▼
┌─────────────────────────────────────────────────────────────┐
│  SEO Insight API (FastAPI)                                  │
│   ├── /api/v1/qa          — Q&A CRUD + 語意搜尋             │
│   ├── /api/v1/chat        — Multi-turn RAG 對話             │
│   ├── /api/v1/report      — 週報生成 / 列表                 │
│   ├── /api/v1/eval        — 評估觸發 / 歷史 / 趨勢         │
│   ├── /api/v1/pipeline    — Pipeline 執行狀態               │
│   └── /api/v1/admin       — 設定管理                        │
├─────────────────────────────────────────────────────────────┤
│  Core Layer                                                 │
│   ├── qa_store.py         — Q&A 資料存取（Repository）       │
│   ├── search_engine.py    — Hybrid Search (semantic + kw)   │
│   ├── chat_engine.py      — Multi-turn RAG 引擎             │
│   ├── eval_engine.py      — Eval 執行 + 歷史管理            │
│   └── report_engine.py    — 週報生成引擎                     │
├─────────────────────────────────────────────────────────────┤
│  Infra Layer                                                │
│   ├── RDS PostgreSQL (AWS) — Q&A + eval_runs + sessions     │
│   ├── pgvector             — embedding 向量索引              │
│   ├── ElastiCache Valkey   — 快取 + rate limit               │
│   └── OpenAI API           — GPT-5.2 / embedding            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: API 設計

### 2.1 技術選型

| 選項 | 決策 | 理由 |
|------|------|------|
| Web 框架 | **FastAPI** | 現有 pipeline 是 Python、async 原生支援、自動 OpenAPI 文件 |
| 序列化 | **Pydantic v2** | 與 FastAPI 深度整合、strict mode、JSON Schema 產出 |
| 資料庫 | **RDS PostgreSQL + pgvector** | 公司已在用 AWS，RDS 整合帳務、pgvector 支援語意搜尋 |
| 快取 | **ElastiCache for Valkey** | Embedding 快取、Rate Limit、Session 快取；Valkey 比 Redis 便宜 20% |
| Auth | **API Key + JWT** | 內部管理介面用 JWT、外部整合用 API Key |

### 2.2 API Endpoints 完整規格

#### 2.2.1 Q&A 知識庫

```
GET    /api/v1/qa                    # 列表（分頁 + 篩選）
GET    /api/v1/qa/:id                # 單筆詳情
POST   /api/v1/qa/search             # 語意搜尋
GET    /api/v1/qa/stats              # 統計摘要
PATCH  /api/v1/qa/:id                # 更新分類/標籤（人工校正）
```

**語意搜尋 Request/Response:**

```json
// POST /api/v1/qa/search
// Request
{
  "query": "AMP 頁面索引異常怎麼處理",
  "top_k": 5,
  "filters": {
    "categories": ["技術SEO", "Discover與AMP"],
    "difficulty": "進階",
    "evergreen": true,
    "min_confidence": 0.7
  }
}

// Response
{
  "data": [
    {
      "id": 282,
      "question": "AMP 驗證失敗時...",
      "answer": "...",
      "score": 0.91,
      "category": "技術SEO",
      "keywords": ["AMP", "amp-iframe"],
      "source_date": "2024-06-13"
    }
  ],
  "meta": {
    "total": 5,
    "query_embedding_ms": 120,
    "search_ms": 15
  }
}
```

**列表 + 篩選:**

```
GET /api/v1/qa?page=1&per_page=20&category=技術SEO&sort=-confidence
GET /api/v1/qa?q=canonical&difficulty=進階
```

**統計摘要 Response:**

```json
// GET /api/v1/qa/stats
{
  "data": {
    "total_count": 703,
    "meetings_processed": 87,
    "categories": {
      "索引與檢索": 95,
      "技術SEO": 112,
      "搜尋表現分析": 88
    },
    "difficulty": { "基礎": 380, "進階": 323 },
    "avg_confidence": 0.78,
    "date_range": { "earliest": "2023-03-20", "latest": "2025-02-20" },
    "last_pipeline_run": "2026-02-25T10:30:00Z"
  }
}
```

#### 2.2.2 Multi-Turn RAG 對話

```
POST   /api/v1/chat                  # 發送訊息（含對話歷史）
GET    /api/v1/chat/sessions         # 對話 session 列表
GET    /api/v1/chat/sessions/:id     # 單一 session 歷史
DELETE /api/v1/chat/sessions/:id     # 刪除 session
```

**對話 Request/Response:**

```json
// POST /api/v1/chat
// Request
{
  "session_id": "sess_abc123",       // 可選，空則建立新 session
  "message": "網站最近 Discover 流量掉很多，可能是什麼原因？",
  "context": {
    "include_metrics": true,         // 是否帶入最新指標
    "max_sources": 5                 // 引用 Q&A 上限
  }
}

// Response
{
  "data": {
    "session_id": "sess_abc123",
    "message_id": "msg_001",
    "response": "根據知識庫的歷史討論，Discover 流量下降通常有以下幾個可能原因...",
    "sources": [
      {
        "qa_id": 156,
        "question": "Google Discover 流量突然大幅下降...",
        "relevance_score": 0.93
      }
    ],
    "suggested_followups": [
      "AMP 與 Discover 的關聯是什麼？",
      "如何檢查是否被 Discover 降權？"
    ]
  },
  "meta": {
    "model": "gpt-5.2",
    "tokens_used": { "input": 2400, "output": 800 },
    "cost_usd": 0.019,
    "retrieval_ms": 45,
    "generation_ms": 2100
  }
}
```

**Multi-Turn 機制：**

```
Turn 1: User → "Discover 流量掉了"
         → Retrieve top-5 Q&A about Discover
         → Generate answer with sources

Turn 2: User → "跟 AMP 有關嗎？"
         → Context: [previous Q&A + Turn 1 answer]
         → Retrieve top-5 Q&A about "Discover + AMP"（query rewrite）
         → Generate answer referencing Turn 1

Turn 3: User → "實際該怎麼做？"
         → Context: [Turn 1 + Turn 2]
         → Retrieve top-5 about "AMP Discover 具體修復步驟"
         → Generate actionable checklist
```

**Query Rewrite 策略：**

```python
# 用 LLM 將 multi-turn context 改寫為 standalone 搜尋查詢
# 避免代名詞（「它」「這個」）影響語意搜尋品質
rewrite_prompt = """
根據對話歷史，將使用者最新問題改寫為一個獨立的搜尋查詢。
移除代名詞，補充隱含的主題。

對話歷史：{history}
最新問題：{latest_message}
→ 改寫查詢：
"""
```

#### 2.2.3 週報

```
POST   /api/v1/report/generate       # 觸發週報生成
GET    /api/v1/report                 # 週報列表
GET    /api/v1/report/:id            # 單份週報
GET    /api/v1/report/:id/metrics    # 週報指標原始資料
```

```json
// POST /api/v1/report/generate
// Request
{
  "sheets_url": "https://docs.google.com/spreadsheets/d/...",
  "tab": "vocus",
  "focus_metrics": ["曝光", "點擊", "Discover"]   // 可選：聚焦特定指標
}

// Response (async - 回傳 job ID)
{
  "data": {
    "job_id": "job_rpt_20260227",
    "status": "processing",
    "estimated_seconds": 120
  }
}
```

#### 2.2.4 Pipeline 管理

```
POST   /api/v1/pipeline/run           # 觸發 pipeline（指定步驟）
GET    /api/v1/pipeline/status         # 目前執行狀態
GET    /api/v1/pipeline/history        # 歷史執行紀錄
```

```json
// POST /api/v1/pipeline/run
{
  "steps": [1, 2, 3],
  "options": {
    "force": false,
    "limit": null
  }
}

// Response
{
  "data": {
    "run_id": "run_20260227_143000",
    "status": "running",
    "steps": [
      { "step": 1, "status": "completed", "duration_s": 45 },
      { "step": 2, "status": "running", "progress": "12/87" },
      { "step": 3, "status": "pending" }
    ]
  }
}
```

#### 2.2.5 Eval API（詳見 Phase 2）

```
POST   /api/v1/eval/run               # 觸發評估
GET    /api/v1/eval/runs               # 評估歷史列表
GET    /api/v1/eval/runs/:id          # 單次評估詳情
GET    /api/v1/eval/trends             # 品質趨勢（時間序列）
GET    /api/v1/eval/golden             # Golden set 管理
PUT    /api/v1/eval/golden/:id        # 更新 golden case
POST   /api/v1/eval/multi-turn/run    # 觸發 multi-turn eval
GET    /api/v1/eval/multi-turn/runs   # Multi-turn eval 歷史
```

### 2.3 Response Envelope 規範

所有 API 遵循統一 envelope：

```python
# 成功
class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: dict | None = None
    links: dict | None = None

# 錯誤
class ApiError(BaseModel):
    error: ErrorDetail

class ErrorDetail(BaseModel):
    code: str          # machine-readable: "validation_error", "not_found"
    message: str       # human-readable 繁體中文
    details: list[FieldError] | None = None
```

**HTTP Status Code 使用：**

| 場景 | Status Code |
|------|-------------|
| 成功回傳 | 200 |
| 成功建立 | 201 |
| 成功無內容 | 204 |
| 驗證失敗 | 422 |
| 未授權 | 401 |
| 找不到 | 404 |
| Rate Limit | 429 |
| 伺服器錯誤 | 500 |

### 2.4 Rate Limiting

| Tier | Limit | 適用 |
|------|-------|------|
| 搜尋/列表 | 60/min per user | GET endpoints |
| 對話 (Chat) | 20/min per user | POST /chat |
| 報告生成 | 5/hour per user | POST /report |
| Pipeline | 2/hour global | POST /pipeline |
| Eval | 10/hour per user | POST /eval |

### 2.5 資料庫 Schema

```sql
-- Q&A 知識庫（從 JSON 遷移到 PostgreSQL）
CREATE TABLE qa_items (
    id          SERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    keywords    TEXT[] NOT NULL DEFAULT '{}',
    confidence  REAL NOT NULL DEFAULT 0.5,
    category    VARCHAR(20) NOT NULL DEFAULT '其他',
    difficulty  VARCHAR(4) NOT NULL DEFAULT '基礎',
    evergreen   BOOLEAN NOT NULL DEFAULT TRUE,
    source_file VARCHAR(255),
    source_title VARCHAR(255),
    source_date DATE,
    is_merged   BOOLEAN NOT NULL DEFAULT FALSE,
    merged_from JSONB,
    embedding   vector(1536),                -- pgvector
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_qa_embedding ON qa_items USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);   -- 適合 ~1K 筆
CREATE INDEX idx_qa_category ON qa_items (category);
CREATE INDEX idx_qa_source_date ON qa_items (source_date);

-- 對話 Sessions
CREATE TABLE chat_sessions (
    id          VARCHAR(36) PRIMARY KEY,     -- uuid
    title       VARCHAR(200),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id          VARCHAR(36) PRIMARY KEY,
    session_id  VARCHAR(36) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role        VARCHAR(10) NOT NULL,        -- user / assistant
    content     TEXT NOT NULL,
    sources     JSONB,                       -- [{qa_id, score}]
    tokens_used JSONB,                       -- {input, output}
    cost_usd    REAL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 評估記錄
CREATE TABLE eval_runs (
    id          VARCHAR(36) PRIMARY KEY,
    eval_type   VARCHAR(20) NOT NULL,         -- quality / classify / retrieval / multi_turn
    config      JSONB NOT NULL,               -- {sample_size, with_source, ...}
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    results     JSONB,
    started_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Pipeline 執行記錄
CREATE TABLE pipeline_runs (
    id          VARCHAR(36) PRIMARY KEY,
    steps       INTEGER[] NOT NULL,
    options     JSONB,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    step_details JSONB,                       -- [{step, status, duration_s, ...}]
    started_at  TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 週報
CREATE TABLE reports (
    id          VARCHAR(36) PRIMARY KEY,
    report_date DATE NOT NULL,
    content_md  TEXT NOT NULL,
    metrics_raw JSONB,
    anomalies   JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.6 檔案結構（API 專案）

```
seo-insight-api/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + lifespan
│   ├── config.py                  # Settings (Pydantic BaseSettings)
│   ├── dependencies.py            # DI: db, redis, openai client
│   ├── models/                    # Pydantic schemas
│   │   ├── qa.py
│   │   ├── chat.py
│   │   ├── eval.py
│   │   ├── report.py
│   │   └── common.py             # ApiResponse, ApiError, Pagination
│   ├── routers/
│   │   ├── qa.py                  # /api/v1/qa
│   │   ├── chat.py                # /api/v1/chat
│   │   ├── eval.py                # /api/v1/eval
│   │   ├── report.py              # /api/v1/report
│   │   └── pipeline.py            # /api/v1/pipeline
│   ├── services/                  # Business logic
│   │   ├── qa_store.py            # Repository pattern
│   │   ├── search_engine.py       # Hybrid Search
│   │   ├── chat_engine.py         # Multi-turn RAG
│   │   ├── eval_engine.py         # Eval orchestration
│   │   └── report_engine.py       # Report generation
│   ├── core/                      # Shared infrastructure
│   │   ├── database.py            # async PostgreSQL pool
│   │   ├── redis.py               # Redis client
│   │   ├── openai_client.py       # OpenAI wrapper (from existing)
│   │   └── security.py            # Auth middleware
│   └── migrations/                # Alembic migrations
├── tests/
│   ├── test_qa_api.py
│   ├── test_chat_api.py
│   ├── test_eval_api.py
│   └── conftest.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## 3. Phase 2: Evals / Multi-Turn Evals 系統

> 參考 ECC eval-harness skill 的 Eval-Driven Development (EDD) 方法論

### 3.1 Eval 類型

| Eval 類型 | 頻率 | 觸發方式 | 說明 |
|----------|------|---------|------|
| **Q&A Quality** | 每次 pipeline 後 | 自動 + API | 四維度評分（Relevance、Accuracy、Completeness、Granularity） |
| **Classification** | 每次 pipeline 後 | 自動 + API | 對照 golden set 驗證分類準確度 |
| **Retrieval** | 每日 | 排程 + API | Keyword Hit Rate、Category Hit Rate、MRR、LLM Top-1 Precision |
| **Multi-Turn Chat** | 每次部署後 | 手動 + API | 端到端對話品質、引用品質、連貫性 |
| **Faithfulness** | 每季 | 手動 | 帶入原始 Markdown 驗證忠實度（成本較高） |
| **Regression** | 每次模型/prompt 變更 | CI/CD | 確保變更不降低已知指標 |

### 3.2 Multi-Turn Eval 設計

這是最核心的新增功能 — 評估 RAG 對話的端到端品質。

#### 3.2.1 Multi-Turn Eval Case 格式

```json
// eval/golden_multi_turn.json
{
  "cases": [
    {
      "id": "mt_001",
      "scenario": "Discover 流量下降診斷",
      "difficulty": "medium",
      "turns": [
        {
          "user": "最近 Discover 流量掉很多，什麼原因？",
          "expected": {
            "must_mention": ["演算法", "內容品質", "E-E-A-T"],
            "must_cite_categories": ["Discover與AMP"],
            "min_sources": 2,
            "no_hallucination": true
          }
        },
        {
          "user": "跟我們的 AMP 設定有關嗎？",
          "expected": {
            "must_mention": ["AMP Article", "amp-iframe", "驗證"],
            "must_reference_previous": true,
            "coherence_with_turn": 1,
            "must_cite_categories": ["Discover與AMP", "技術SEO"],
            "min_sources": 1
          }
        },
        {
          "user": "那具體建議怎麼做？",
          "expected": {
            "must_be_actionable": true,
            "must_include_steps": true,
            "min_action_items": 3,
            "coherence_with_turn": [1, 2]
          }
        }
      ]
    }
  ]
}
```

#### 3.2.2 Multi-Turn Eval Grader（LLM-as-Judge）

```python
MULTI_TURN_JUDGE_PROMPT = """
你是一位 RAG 系統品質評審員。

評估以下多輪對話的品質。每一輪評估：

1. **Relevance（相關性）** 1-5：回答是否切題
2. **Groundedness（引用品質）** 1-5：回答是否基於檢索到的 Q&A，而非憑空生成
3. **Coherence（連貫性）** 1-5：與前幾輪對話是否連貫、不矛盾
4. **Actionability（可執行性）** 1-5：是否提供了可執行的建議
5. **Citation Accuracy（引用準確性）** 1-5：引用的來源 Q&A 是否真的支持回答內容

整體評估：
6. **Query Understanding** 1-5：系統是否正確理解多輪對話中的指代消解
7. **Progressive Depth** 1-5：隨對話推進，回答是否逐步深入
8. **Hallucination Count**：回答中無法追溯到知識庫的陳述數量
"""
```

#### 3.2.3 Multi-Turn Eval 指標

| 指標 | 計算方式 | 目標 |
|------|---------|------|
| Turn Relevance | 每輪 LLM 評分平均 | ≥ 4.0 |
| Groundedness | 引用 Q&A 覆蓋率 | ≥ 80% |
| Coherence | 跨 turn 一致性 | ≥ 4.0 |
| Citation Precision | 引用 Q&A 確實支持論點的比例 | ≥ 85% |
| Query Rewrite Quality | 改寫查詢涵蓋意圖的比例 | ≥ 90% |
| Hallucination Rate | 幻覺陳述數 / 總陳述數 | ≤ 5% |
| pass@3 | 3 次中至少 1 次所有指標通過 | ≥ 90% |

#### 3.2.4 Eval Pipeline 自動化

```
              ┌──────────────┐
              │ 觸發 Eval     │
              │ (API / CI/CD) │
              └──────┬───────┘
                     ▼
         ┌───────────────────────┐
         │  Eval Orchestrator     │
         │  (eval_engine.py)      │
         └──────┬────────────────┘
                │
    ┌───────────┼───────────┬───────────┐
    ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│Quality │ │Classify│ │Retrieval│ │Multi-Turn│
│  Eval  │ │  Eval  │ │  Eval  │ │   Eval   │
└───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘
    │          │          │           │
    ▼          ▼          ▼           ▼
┌─────────────────────────────────────────────┐
│  eval_runs (PostgreSQL)                      │
│  + eval_history.jsonl (backup)               │
└──────────────┬──────────────────────────────┘
               ▼
         ┌───────────┐
         │ Trends API │ → UI 儀表板
         └───────────┘
```

#### 3.2.5 Eval Run Response

```json
// GET /api/v1/eval/runs/eval_20260227_143000
{
  "data": {
    "id": "eval_20260227_143000",
    "eval_type": "multi_turn",
    "status": "completed",
    "config": {
      "cases": 10,
      "model": "gpt-5.2",
      "judge_model": "gpt-5.2"
    },
    "results": {
      "overall_pass": true,
      "avg_relevance": 4.3,
      "avg_groundedness": 4.1,
      "avg_coherence": 4.5,
      "citation_precision": 0.88,
      "hallucination_rate": 0.03,
      "pass_at_3": 0.95,
      "case_details": [
        {
          "case_id": "mt_001",
          "scenario": "Discover 流量下降診斷",
          "turns": [
            {
              "turn": 1,
              "relevance": 5,
              "groundedness": 4,
              "coherence": 5,
              "actionability": 3,
              "citation_accuracy": 4,
              "hallucination_count": 0
            }
          ],
          "overall_query_understanding": 4,
          "overall_progressive_depth": 4
        }
      ]
    },
    "completed_at": "2026-02-27T14:35:00Z",
    "cost_usd": 1.20
  }
}
```

#### 3.2.6 Eval Trends API

```json
// GET /api/v1/eval/trends?eval_type=multi_turn&days=30
{
  "data": {
    "eval_type": "multi_turn",
    "period": { "from": "2026-01-28", "to": "2026-02-27" },
    "runs": 12,
    "trend": [
      {
        "date": "2026-02-01",
        "avg_relevance": 4.1,
        "avg_groundedness": 3.8,
        "citation_precision": 0.82,
        "hallucination_rate": 0.07,
        "pass_at_3": 0.85
      },
      {
        "date": "2026-02-15",
        "avg_relevance": 4.3,
        "avg_groundedness": 4.1,
        "citation_precision": 0.88,
        "hallucination_rate": 0.03,
        "pass_at_3": 0.95
      }
    ],
    "regressions": [
      {
        "date": "2026-02-10",
        "metric": "hallucination_rate",
        "previous": 0.04,
        "current": 0.09,
        "severity": "warning"
      }
    ]
  }
}
```

### 3.3 Regression Eval（CI/CD 整合）

```yaml
# .github/workflows/eval-regression.yml
name: Eval Regression Check

on:
  push:
    paths:
      - 'app/core/openai_client.py'     # prompt 變更
      - 'app/services/chat_engine.py'    # RAG 邏輯變更
      - 'app/services/search_engine.py'  # 搜尋邏輯變更

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt
      - run: |
          python -m pytest tests/test_eval_regression.py \
            --eval-type quality,retrieval,multi_turn \
            --threshold-file eval/thresholds.json
      - name: Fail on regression
        if: failure()
        run: echo "::error::Eval regression detected! Check eval report."
```

**Regression Thresholds:**

```json
// eval/thresholds.json
{
  "quality": {
    "avg_relevance": { "min": 3.8, "warn": 4.0 },
    "avg_accuracy": { "min": 3.5, "warn": 3.8 },
    "avg_completeness": { "min": 3.5, "warn": 3.8 }
  },
  "retrieval": {
    "avg_mrr": { "min": 0.60, "warn": 0.70 },
    "llm_top1_precision": { "min": 0.70, "warn": 0.80 }
  },
  "multi_turn": {
    "avg_relevance": { "min": 3.8, "warn": 4.0 },
    "citation_precision": { "min": 0.80, "warn": 0.85 },
    "hallucination_rate": { "max": 0.10, "warn": 0.05 },
    "pass_at_3": { "min": 0.85, "warn": 0.90 }
  }
}
```

### 3.4 Golden Set 管理

UI 介面讓 SEO 團隊管理 golden set：

```
GET    /api/v1/eval/golden                     # 列出所有 golden cases
GET    /api/v1/eval/golden/:id                # 單筆 golden case
POST   /api/v1/eval/golden                     # 新增 golden case
PUT    /api/v1/eval/golden/:id                # 更新 golden case
DELETE /api/v1/eval/golden/:id                # 刪除 golden case
POST   /api/v1/eval/golden/import             # 批次匯入 (JSON)
GET    /api/v1/eval/golden/export             # 匯出 (JSON)
```

---

## 4. Phase 3: 部署與基礎設施

> 公司 infra 已在 AWS 上（EC2、S3、ECR 已在使用），統一部署於 AWS 可整合帳務、VPC、IAM，避免跨雲複雜度。

### 4.1 部署架構（AWS）

```
┌── 前端（現有）──────────────────┐     ┌── AWS VPC ─────────────────────────────────────────┐
│  vocus-web-ui (Next.js)    │────▶│                                           │
│  pages/admin/seo/insight   │     │  ┌── ECS Fargate ──────────────────────────────────┐  │
└────────────────────────────┘     │  │  seo-insight-api (FastAPI)                      │  │
                                   │  │  Task: 0.5 vCPU / 1 GB RAM                      │  │
                                   │  └──────────────────┬─────────────────────────────┘  │
                                   │                      │                                │
                                   │   ┌──────────────────┼─────────────────┐              │
                                   │   ▼                  ▼                 ▼              │
                                   │  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
                                   │  │   RDS    │ │ElastiCache│ │OpenAI   │             │
                                   │  │PostgreSQL│ │  Valkey  │ │  API    │             │
                                   │  │+pgvector │ │(t3.micro)│ │ (PAYG)  │             │
                                   │  │(t4g.micro│ │          │ │         │             │
                                   │  │Single AZ)│ │          │ │         │             │
                                   │  └──────────┘ └──────────┘ └─────────┘             │
                                   └───────────────────────────────────────────────────────┘
                                            │                │
                              ┌─────────────┘                └──────────┐
                              ▼                                         ▼
                         ┌──────────┐                           ┌──────────┐
                         │  ECR     │                           │   S3     │
                         │ (已在用) │                           │ (已在用) │
                         │ Docker   │                           │ Backups  │
                         │ Image    │                           │ Reports  │
                         └──────────┘                           └──────────┘
```

### 4.2 部署選項比較（AWS 內）

| 方案 | 推薦度 | 月費估算 | 優點 | 缺點 |
|------|--------|---------|------|------|
| **A: ECS Fargate（專用）** | ⭐⭐⭐ 推薦 | $45–65 | 無需管理 EC2、serverless container、ECR 整合 | 費用較 EC2 共用高 |
| **B: 現有 EC2 加掛 Docker** | ⭐⭐ 省錢 | $15–25 | 幾乎不增加費用（EC2 已付）| 需確認 EC2 有剩餘容量、耦合度高 |
| C: ECS EC2 Launch Type | 適合量大 | $30–50 | EC2 可預留實例折扣 | 需管理 EC2 cluster |
| D: Lambda + API Gateway | 適合低頻 | $5–15 | Pay-per-use 最省 | Cold start 嚴重、不適合 WebSocket/streaming |

**推薦：方案 A（ECS Fargate）**
- 公司已有 ECR，Docker image push/pull 流程完整
- ECS Fargate 免管理 EC2，自動 HA
- 統一 VPC、IAM 權限管理
- 若月費是優先考量，短期可先用方案 B（現有 EC2）

### 4.3 ECS Fargate 設定

```json
// ecs-task-definition.json（核心部分）
{
  "family": "seo-insight-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT_ID:role/seo-insight-task-role",
  "containerDefinitions": [
    {
      "name": "seo-insight-api",
      "image": "ACCOUNT_ID.dkr.ecr.ap-northeast-1.amazonaws.com/seo-insight-api:latest",
      "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        "interval": 30, "timeout": 5, "retries": 3
      },
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "LOG_LEVEL", "value": "info"}
      ],
      "secrets": [
        {"name": "DATABASE_URL", "valueFrom": "arn:aws:secretsmanager:...:seo-insight/database-url"},
        {"name": "OPENAI_API_KEY", "valueFrom": "arn:aws:secretsmanager:...:openai-api-key"},
        {"name": "REDIS_URL", "valueFrom": "arn:aws:secretsmanager:...:seo-insight/redis-url"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/seo-insight-api",
          "awslogs-region": "ap-northeast-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 4.4 CI/CD Pipeline（GitHub Actions → ECR → ECS）

```yaml
# .github/workflows/deploy.yml
name: Deploy to ECS
on:
  push:
    branches: [main]

env:
  AWS_REGION: ap-northeast-1
  ECR_REPOSITORY: seo-insight-api
  ECS_SERVICE: seo-insight-service
  ECS_CLUSTER: vocus-cluster
  CONTAINER_NAME: seo-insight-api

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:${{ github.sha }} .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:${{ github.sha }}
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:${{ github.sha }} \
                     $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ecs-task-definition.json
          service: ${{ env.ECS_SERVICE }}
          cluster: ${{ env.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### 4.5 Dockerfile

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app
RUN useradd -r -u 1001 appuser
USER appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages \
     /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
```

### 4.6 Environment Variables（透過 AWS Secrets Manager 注入）

```bash
# ── 機密：存入 AWS Secrets Manager ────────────────────────────
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@rds-host:5432/seo_insight
REDIS_URL=rediss://seo-insight.xxxx.ng.0001.apne1.cache.amazonaws.com:6379
NOTION_TOKEN=ntn_...
JWT_SECRET=... (min 32 chars)
API_KEY_HASH=... (bcrypt hash)

# ── 非機密：直接寫入 ECS Task Definition env ──────────────────
NOTION_PARENT_PAGE_ID=...
SHEETS_URL=https://docs.google.com/spreadsheets/d/...
ENVIRONMENT=production
LOG_LEVEL=info
CORS_ORIGINS=https://vocus.cc,http://localhost:3000
AWS_REGION=ap-northeast-1
```

> **注意：** 所有機密統一存入 AWS Secrets Manager，ECS Task 透過 IAM Role 存取，  
> 不寫入 `.env` 檔，不進入 git。

---

## 5. 成本估算

> 定價基準：AWS ap-northeast-1（東京），最接近台灣，適合公司現有 AWS 區域部署。  
> 以下使用隨需（On-Demand）定價，未含 Savings Plans / 預留實例折扣。

### 5.1 基礎設施月費（方案 A：ECS Fargate 專用）

| 服務 | 規格 | 月費估算 | 說明 |
|------|------|---------|------|
| **ECS Fargate** | 0.5 vCPU × 1GB × 24/7 | **~$18** | 1 task 常駐；若流量低可縮至 0.25 vCPU≈$9 |
| **RDS PostgreSQL** | db.t4g.micro + 20GB gp3 Single AZ | **~$20** | t4g.micro ~$17/mo + storage $2.3 |
| **ElastiCache Valkey** | cache.t3.micro | **~$14** | Valkey 比 Redis 便宜 20%；可免除改用 app-level cache |  
| **ECR** | 500MB image | **~$0.05** | $0.10/GB-month |
| **ALB** | 共用現有 ALB *(推薦)* | **$0** | 若需新建 ALB：$0.0243/hr ≈ $17.5/mo |
| **S3** | 報告 Markdown 備份 | **~$0.05** | $0.023/GB；20 報告 ≈ 2MB |
| **Secrets Manager** | 8 secrets | **~$0.32** | $0.40/secret/month |
| **CloudWatch Logs** | 5GB/month | **~$2.5** | $0.50/GB |

**基礎設施小計（方案 A）：~$55/月**

---

| 服務 | 規格 | 月費估算 | 說明 |
|------|------|---------|------|
| **現有 EC2 加掛 Docker** *(方案 B)* | 共用現有 EC2 | **$0** | EC2 已付；需確認 CPU/RAM 有剩餘容量 |
| **RDS PostgreSQL** | db.t4g.micro + 20GB gp3 Single AZ | **~$20** | 同上，或加入現有 RDS cluster |
| **ElastiCache Valkey** | cache.t3.micro | **~$14** | 或跳過 Redis，用 app-level 記憶體快取 |

**基礎設施小計（方案 B，最省）：~$15–35/月**

### 5.2 OpenAI API 月費

#### 5.2.1 模型定價（2025-2026）

| 模型 | Input $/1M tokens | Output $/1M tokens | 用途 |
|------|-------------------|---------------------|------|
| text-embedding-3-small | $0.02 | — | 語意搜尋 |
| gpt-5-mini | $0.80 | $4.00 | 分類、retrieval judge |
| gpt-5.2 | $3.00 | $15.00 | 萃取、合併、週報、品質評估 |

#### 5.2.2 各功能估算（每月）

| 功能 | 次數/月 | 模型 | Input tokens | Output tokens | 月費 |
|------|---------|------|-------------|---------------|------|
| **語意搜尋** | 500 | embedding-3-small | 50K | — | **$0.001** |
| **Chat (RAG)** | 300 | gpt-5.2 | 600K | 150K | **$4.05** |
| **週報生成** | 4 | gpt-5.2 | 80K | 20K | **$0.54** |
| **Q&A Quality Eval** | 1 run × 30 筆 | gpt-5.2 | 120K | 60K | **$1.26** |
| **Classification Eval** | 1 run × 20 筆 | gpt-5-mini | 20K | 10K | **$0.06** |
| **Retrieval Eval** | 2 runs × 15 cases | gpt-5-mini | 30K | 15K | **$0.08** |
| **Multi-Turn Eval** | 2 runs × 10 cases × 3 turns | gpt-5.2 | 300K | 120K | **$2.70** |
| **Pipeline (Steps 2-3)** | 新增 ~5 篇/月 | gpt-5.2 + embedding | 100K | 30K | **$0.75** |

**OpenAI 小計：~$9.50/月**

#### 5.2.3 成本優化策略

| 策略 | 節省比例 | 說明 |
|------|---------|------|
| **Model Routing** | ~40% | 簡單任務用 gpt-5-mini（分類、retrieval judge） |
| **Prompt Caching** | ~20% | 系統 prompt 快取（>1024 tokens 的 system prompt） |
| **Embedding 快取** | ~60% | 已計算的 embedding 存入 Redis，避免重複呼叫 |
| **Budget Guardrail** | 防爆 | 設定月預算上限 $30，超過自動降級為 gpt-5-mini |

```python
# Cost Tracking（immutable pattern from ECC cost-aware-llm-pipeline）
@dataclass(frozen=True, slots=True)
class CostTracker:
    budget_limit: float = 30.00    # 月預算上限 USD
    records: tuple[CostRecord, ...] = ()

    @property
    def over_budget(self) -> bool:
        return self.total_cost > self.budget_limit
```

### 5.3 總成本摘要

| 項目 | 方案 A（ECS Fargate）| 方案 B（現有 EC2）| 說明 |
|------|---------------------|-------------------|------|
| 基礎設施（運算）| $18 | $0 | Fargate vs. 共用 EC2 |
| 基礎設施（DB）| $20 | $20 | RDS db.t4g.micro |
| 基礎設施（Cache）| $14 | $14 | ElastiCache t3.micro |
| 其他 AWS | $3 | $3 | Logs, Secrets, S3, ECR |
| OpenAI API | $9.5 | $9.5 | 視使用量 |
| **月合計** | **~$65** | **~$47** | 不含現有 EC2/ALB 費用 |
| **年合計** | **~$780** | **~$564** | |

#### 成本優化路徑

| 優化措施 | 節省金額 | 說明 |
|---------|---------|------|
| Fargate Savings Plan（1年）| -35% 運算費 | 承諾 1 年可省 ~$6/月 |
| RDS 預留實例（1年不預付）| -30% DB 費 | RDS db.t4g.micro 省 ~$6/月 |
| 跳過 ElastiCache | -$14/月 | 低流量工具用 app-level 快取即可 |
| Fargate Spot（開發環境）| -70% 運算費 | 可中斷，適合 staging 環境 |
| **最省組合**（方案 B + 省 Cache）| **~$33/月** | EC2 共用 + RDS + 無獨立 Redis |

> **對比 Cloud Run 原版方案：**  
> Cloud Run（$2–8）+ Supabase Free + Upstash Free = ~$9/月  
> 但 Cloud Run 低流量估算假設每日僅 ~500 requests + min-instances=0（Cold start 2-3s）。  
> AWS 方案最省組合 ~$33/月，但統一帳務、無縫 VPC 整合、免 Cold start（min task =1）。

---

## 6. 風險與緩解

| # | 風險 | 嚴重度 | 緩解措施 |
|---|------|--------|---------|
| 1 | OpenAI API 不穩定導致 chat/eval 失敗 | High | 實作 exponential backoff retry（僅 transient errors）；加入 circuit breaker |
| 2 | ECS Task 啟動延遲（冷啟動） | Low | ECS Fargate 保持 min task=1 常駐，無冷啟動問題；Spot 模式需設定 graceful shutdown |
| 3 | 知識庫過時（>2 年歷史） | Medium | 加入 `relevance_decay` — 較舊的 Q&A 在搜尋中加權降低 |
| 4 | Multi-turn 對話幻覺 | High | Eval 系統自動監控 hallucination_rate；強制引用 sources |
| 5 | 資料庫從 JSON 遷移遺漏 | Medium | 寫 migration script + 遷移後跑 regression eval 確認完整 |
| 6 | Prompt injection（使用者惡意輸入） | High | 輸入驗證 + system prompt 防護 + rate limit |
| 7 | 月 API 費用失控 | Medium | CostTracker 強制預算上限 + model routing 降級機制 |

---

## 7. Architecture Decision Records

### ADR-001: 使用 FastAPI 而非 Next.js API Routes

**Context:** vocus-web-ui 是 Next.js 專案，可直接用 API Routes。但現有 pipeline 全是 Python。

**Decision:** 獨立 FastAPI 服務。

**Consequences:**
- ✅ 重用現有 Python 邏輯（openai_helper, pipeline scripts）
- ✅ 獨立部署、獨立 scaling
- ✅ async 原生、自動 OpenAPI 文件
- ❌ 多一個服務要維護
- ❌ 跨服務通訊延遲（~10ms）

### ADR-002: 使用 pgvector 而非獨立向量資料庫

**Context:** 需要語意搜尋。可選 Pinecone、Weaviate、pgvector。

**Decision:** pgvector（PostgreSQL extension）。

**Consequences:**
- ✅ AWS RDS for PostgreSQL 支援 `pgvector` extension，與整體 AWS 基礎設施整合
- ✅ 同一資料庫，JOIN / filter 方便
- ✅ ~1K 筆向量，pgvector 性能綽綽有餘
- ❌ 10K+ 筆後可能需要遷移到專用向量 DB

### ADR-003: Multi-Turn Eval 使用 LLM-as-Judge

**Context:** 多輪對話品質難以用 rule-based 評估。

**Decision:** 以 gpt-5.2 作為 Judge，搭配結構化評分 schema。

**Consequences:**
- ✅ 可評估開放式回答品質
- ✅ 評估維度豐富（relevance, groundedness, coherence, etc.）
- ❌ 評估本身有成本（每次 ~$1.20）
- ❌ LLM Judge 有自身偏見，需定期校準

### ADR-004: 資料遷移策略（JSON → PostgreSQL）

**Context:** 現有 703 筆 Q&A 存在 `qa_final.json`，embedding 在 `qa_embeddings.npy`。

**Decision:** 寫一次性 migration script，保持 JSON 作為 backup。

**Migration Steps:**
1. 讀取 `qa_final.json` + `qa_embeddings.npy`
2. 寫入 `qa_items` table（含 embedding 向量）
3. 建立 ivfflat index
4. 跑 retrieval eval 確認搜尋品質不變
5. 保留 JSON 檔案作為 rollback 備份

---

### ADR-005: 部署平台選擇 AWS ECS Fargate 而非 Cloud Run

**Context:** 初版計畫採用 Google Cloud Run，但公司 infra 已在 AWS（EC2、S3、ECR 均在使用）。

**Decision:** 部署於 AWS ECS Fargate，使用 ECR 存放 Docker image。

**Consequences:**
- ✅ 整合現有 AWS 帳號、VPC、IAM、帳務
- ✅ ECR 已在使用，image push/pull 流程完整
- ✅ 可使用 AWS Secrets Manager 統一管理機密
- ✅ CloudWatch 整合系統監控（公司可能已有 dashboard）
- ❌ 月費比 Cloud Run（pay-per-use）高 $30–40（若流量極低）
- ❌ ALB 設定比 Cloud Run HTTPS 複雜（但可共用現有 ALB）

**備選方案：共用現有 EC2（方案 B）**
- 優點：幾乎零增量費用
- 缺點：耦合度高、需協調 EC2 容量、不易獨立 scaling

---

## 8. Success Criteria

### MVP（Phase 1 完成）

- [ ] API 可接受語意搜尋請求，回傳 top-K Q&A（延遲 < 500ms）
- [ ] 從 JSON 遷移到 PostgreSQL + pgvector 完成
- [ ] Chat endpoint 可進行 3 輪以上對話
- [ ] 週報 API 可從 Google Sheets 拉資料生成報告
- [ ] Pipeline API 可觸發和監控執行狀態
- [ ] OpenAPI 文件自動產出且可在 UI 互動

### Evals（Phase 2 完成）

- [ ] Q&A Quality Eval avg scores ≥ 3.8
- [ ] Classification accuracy ≥ 80%
- [ ] Retrieval MRR ≥ 0.65
- [ ] Multi-Turn Eval hallucination_rate ≤ 5%
- [ ] Multi-Turn Eval pass@3 ≥ 90%
- [ ] Eval trends UI 可視化 30 天趨勢
- [ ] Regression eval 整合到 CI/CD

### 部署（Phase 3 完成）

- [ ] ECS Fargate service 部署成功，health check 通過
- [ ] GitHub Actions CI/CD pipeline 完成：push main → ECR → ECS 自動更新
- [ ] AWS Secrets Manager 替換所有 .env 機密
- [ ] CloudWatch 告警設定：Error rate > 5% 發送通知
- [ ] 月費控制在 **方案 A $75** 或 **方案 B $50** 以內
- [ ] P95 latency < 3s（含 LLM 呼叫的 chat endpoint）
- [ ] P95 latency < 200ms（不含 LLM 呼叫的 list/search endpoint）
- [ ] 99.5% uptime

---

## 實施順序

```
Week 1-2: Phase 1.1 — DB Schema + 資料遷移 + Q&A API (CRUD + Search)
Week 2-3: Phase 1.2 — Chat Engine (Multi-turn RAG) + Chat API
Week 3-4: Phase 1.3 — Report API + Pipeline API
Week 4-5: Phase 2.1 — Eval Engine + 既有 eval 遷移
Week 5-6: Phase 2.2 — Multi-Turn Eval + Golden Set Management
Week 6-7: Phase 2.3 — Eval Trends + Regression CI/CD
Week 7-8: Phase 3   — Docker + ECS Fargate 部署 + CloudWatch 監控
```

> 每個 Phase 獨立可交付，可依優先度調整順序。
