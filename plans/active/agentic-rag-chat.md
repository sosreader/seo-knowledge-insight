# Agentic RAG Chat — 多階段實作計畫

> 狀態：Phase 1+2 已完成 | 建立日期：2026-03-06 | 更新：2026-03-07 | 參考：FM AI Agents v2 課程

## Context

**問題**：目前 `/chat` command 是固定單輪流程：`qa_tools.py search` → Claude Code 回答。LLM 無法自主決定是否需要搜尋、用什麼關鍵字搜、是否需要再搜一次、或查詢特定 Q&A 詳情。

**參考**：Frontend Masters AI Agents v2 課程（Scott Moss, `Hendrixer/agent-from-scratch`）示範了 agent loop 模式——LLM 自主決策呼叫工具，直到認為資訊足夠才回答。

**核心借鑑**：agent loop 模式（課程）+ 領域知識深度（本專案）= **Agentic RAG**。

---

## 架構差異摘要（FM 課程 vs 本專案）

| 維度 | FM AI Agents v2 | SEO Knowledge Insight |
|------|-----------------|----------------------|
| **定位** | 通用 CLI Agent（教學用，21 檔 ~500 行） | 領域專用 ETL + RAG 系統（生產級，300+ 檔） |
| **Agent Loop** | while-loop，LLM 自主停止 | Phase 1: Claude Code 自主執行；Phase 2: API while-loop |
| **Tool Calling** | OpenAI function calling + Zod schema | Phase 1: 混合工具（Grep/Read/CLI）；Phase 2: OpenAI function calling |
| **記憶體** | lowdb JSON（chat history） | Supabase pgvector + session store |
| **RAG** | 僅概念講解 | 完整 4 層 hybrid search |
| **Eval** | Laminar + 基礎 evaluator | 10 eval groups + 6 golden datasets |
| **部署** | 本地 CLI | Lambda arm64 + Supabase + CI/CD |

---

## Phase 1：Claude Code as LLM（已完成）

### 三層架構

```
Layer 3：/chat-agent command（入口 + 流程控制）
Layer 2：混合工具（Grep/Read + qa_tools.py CLI）
Layer 1：agentic-rag skill（行為規則 + 判斷策略）
```

### Agent Loop 流程

```
使用者提問
     |
     v
Claude Code 分析問題 -> 決定搜尋策略
     |
     v
+-- Agent Loop（最多 3 輪）---------------------+
|                                                |
|  1. 選擇工具：                                  |
|     +- 精確術語 -> Grep qa_final.json           |
|     +- 模糊語意 -> qa_tools.py search           |
|     +- 特定分類 -> qa_tools.py search --category |
|     +- 完整答案 -> Read 特定 Q&A 區段            |
|                                                |
|  2. 評估結果：                                  |
|     +- 資訊充足 -> 跳出 loop，生成回答          |
|     +- 資訊不足 -> 換關鍵字 / 換工具再搜        |
|     +- 需要交叉驗證 -> 搜另一個分類             |
|                                                |
+------------------------------------------------+
     |
     v
生成結構化回答（含來源引用 + 搜尋摘要）
```

### 實作產出

| 檔案 | 職責 |
|------|------|
| `.claude/skills/agentic-rag.md` | 行為規則：何時搜、搜什麼、工具路由、結果評估、回答格式 |
| `.claude/commands/chat-agent.md` | Agent loop 入口：問題分析 -> 多輪搜尋 -> 結構化回答 |

### 與現有 `/chat` 的差異

| | `/chat` | `/chat-agent` |
|---|---|---|
| 搜尋次數 | 固定 1 次 | 自主 1-3 次 |
| 關鍵字選擇 | 直接用使用者問題 | 拆解、重組關鍵字 |
| 工具選擇 | 只用 `qa_tools.py search` | 混合 Grep/Read/qa_tools.py |
| 結果評估 | 無（搜到就回答） | 評估充足性，不足再搜 |
| 交叉驗證 | 無 | 可搜不同分類交叉驗證 |
| 回答附加 | 無 | 搜尋摘要（輪數+工具+筆數） |

---

## Phase 2：TypeScript API Agent Loop（已完成）

### 目標

將 agent loop 搬入 TypeScript API，讓前端 `/chat` 端點也能使用 agentic 模式。

### 設計要點

- OpenAI function calling + while-loop
- 4 tools：`search_knowledge_base`、`get_qa_detail`、`list_categories`、`get_stats`
- Feature flag `AGENT_ENABLED`（預設 auto，有 OpenAI key 就啟用）
- 終止條件：`finish_reason === "stop"` / MAX_TURNS(5) / TIMEOUT(90s) / loop detection
- Response 新增 `mode: "agent"` + `tool_calls_count`
- 詳細設計見下方「Phase 2 詳細設計」

### Security Hardening（Phase 2 完成後執行）

- `getQaDetailSchema` id regex 收緊為 `/^([0-9a-f]{16}|\d{1,6})$/`
- `ALLOWED_TOOLS` runtime whitelist + `JSON.parse` guard
- 錯誤訊息 sanitization（統一 "Tool execution failed"）
- `tool_calls` array 不暴露到 wire response（只回傳 count）
- `isAgentEnabled()` 抽取至 shared `utils/mode-detect.ts`
- Session history depth cap `MAX_HISTORY=20`

### 檔案變更（7 新增 + 6 修改）

**新增**：
| 檔案 | 行數 | 職責 |
|------|------|------|
| `api/src/agent/types.ts` | ~60 | AgentConfig, ToolResult, AgentResponse, AgentDeps interface |
| `api/src/agent/tool-definitions.ts` | ~150 | 4 tool 的 Zod schema + `getOpenAITools()` |
| `api/src/agent/tool-executor.ts` | ~120 | Tool dispatch + Zod validation + 15s timeout |
| `api/src/agent/agent-loop.ts` | ~180 | while-loop + 終止條件 + source 收集 |
| `api/tests/agent/tool-definitions.test.ts` | ~80 | Schema parse/reject + OpenAI format |
| `api/tests/agent/tool-executor.test.ts` | ~150 | 各 tool happy/error path |
| `api/tests/agent/agent-loop.test.ts` | ~250 | 終止/max turns/timeout/loop detection |

**修改**：
| 檔案 | 變更 |
|------|------|
| `api/src/config.ts` | envSchema 新增 `AGENT_ENABLED`、`AGENT_MAX_TURNS`、`AGENT_TIMEOUT_MS` |
| `api/src/schemas/chat.ts` | mode 加 `"agent"`、新增 `tool_calls_count?` |
| `api/src/routes/chat.ts` | Feature flag 分流（`isAgentEnabled()`） |
| `api/src/routes/sessions.ts` | 同步 agent 分流（shared `isAgentEnabled()`） |
| `api/src/utils/mode-detect.ts` | 新增 `isAgentEnabled()` 共用函式 |

---

## Phase 3：Request-Level Mode（已完成）

### 目標

讓前端在每次請求中選擇 `mode: "agent" | "rag"`，不再完全依賴 server-level `AGENT_ENABLED`。

### 設計

三層優先順序：`Request mode` > `AGENT_ENABLED` > `auto fallback`

- `resolveMode(requestMode?)` — 封裝優先順序邏輯
- `chatRequestSchema` / `sendMessageSchema` 新增 `mode: z.enum(["agent","rag"]).optional()`
- Response `mode` 統一為 `"rag" | "context-only" | "agent"`（breaking: `"full"` → `"rag"`）

### 檔案變更

| 檔案 | 變更 |
|------|------|
| `api/src/utils/mode-detect.ts` | 新增 `resolveMode()` + `RequestMode` type |
| `api/src/schemas/chat.ts` | schema + response type |
| `api/src/schemas/session.ts` | schema |
| `api/src/services/rag-chat.ts` | `"full"` → `"rag"` |
| `api/src/routes/chat.ts` | `resolveMode(requestMode)` |
| `api/src/routes/sessions.ts` | 同上 |
| `api/tests/utils/mode-detect.test.ts` | 新增 9 tests |
| `api/tests/routes/chat.test.ts` | +5 tests |
| `api/tests/routes/sessions.test.ts` | +4 tests |

---

## Phase 4：Streaming + Session 整合（待實作）

- Lambda Response Streaming + 前端即時顯示 tool 呼叫進度
- Session metadata 存 tool_calls 細節
- Human Approval（破壞性操作確認機制）
- Context Compaction（長對話 LLM-based summarization）

---

## 路線圖

| Phase | 內容 | LLM 引擎 | 需要 API key | 狀態 |
|-------|------|----------|-------------|------|
| **Phase 1** | Skill + Command + 混合工具 | Claude Code | 不需要 | 已完成 |
| **Phase 2** | TypeScript API agent loop | OpenAI gpt-5.2 function calling | OPENAI_API_KEY | 已完成 |
| **Phase 3** | Request-level mode parameter | 同 Phase 2 | 同 Phase 2 | 已完成 |
| Phase 4 | Streaming + Session 整合 | 同 Phase 2 | 同 Phase 2 | 待實作 |

---

## 驗證計畫（Phase 1）

1. **基本問答**：`/chat-agent 什麼是 Core Web Vitals？` — 驗證多輪搜尋 + 來源引用
2. **模糊問題**：`/chat-agent 網站流量突然下降怎麼辦` — 驗證能拆解為多個搜尋意圖
3. **精確術語**：`/chat-agent canonical 跟 hreflang 差別` — 驗證 Grep 被使用
4. **知識庫外問題**：`/chat-agent React 怎麼用` — 驗證推論標記
5. **對比**：同樣問題分別用 `/chat` 和 `/chat-agent`，比較回答品質
6. **追問**：連續追問 2-3 輪，驗證上下文維持
