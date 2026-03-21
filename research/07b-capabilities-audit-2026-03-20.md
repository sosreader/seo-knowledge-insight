# Capabilities System Audit Report（2026-03-20）

## 排查範圍

| Audit 層 | 範圍 | 檔案數 |
|----------|------|--------|
| Slash Commands | `.claude/commands/*.md` 全 20 檔 | 20 |
| TS Routes | `api/src/routes/*.ts` + `capabilities.ts` | 8 |
| Python | `scripts/qa_tools.py` + `utils/openai_helper.py` + 全 Python | 5 |
| Documentation | CLAUDE.md + README + research + memory + docs-site | 9 |
| Test Coverage | `capabilities.test.ts` + `health.test.ts` | 2 |
| 業界參考 | RFC / K8s / AWS / Google / Fowler / Nygard / Netflix | 15 sources |

---

## 5 層 Audit 摘要

### 層 1：Slash Commands（20/20 檢查完畢）

**結論：PASS**（1 個 P2 修正、1 個 False Positive）

- 20 個 command 全部檢查完畢
- 3 個有 API 相關邏輯：`generate-report`、`meeting-prep`、`chat-agent`
  - `generate-report` Step 0：API-first + Local fallback 模式偵測 — **PASS**（正確使用 curl health check）
  - `meeting-prep`：**False Positive** — 探查確認無 API 呼叫，純本地文件操作
  - `chat-agent` Step 3.5：**P2 — 缺 error handling**（已修正：加 best-effort 指引）
- 其餘 17 個 command 無 capabilities 相關邏輯

### 層 2：TS Routes（8/8 檢查完畢）

**結論：PASS**

- 所有 route 使用 `resolveServerCapabilities()` 或 `resolveCapabilities(ua)` — 一致
- `caps.llm` 決策分支正確：`"openai"` → hybrid search / full chat / agent mode；`"none"` → keyword / context-only
- `caps.store` 決策分支正確：`"supabase"` → pgvector；`"file"` → in-memory
- `/health`（`health.ts:6-13`）：回傳有效 capabilities（`resolveHealthCapabilities(ua)`），含 caller + 有效 llm（Claude Code 呼叫時 `"claude-code"`）— **PASS**（v3.6.1 更新）
- 無 dead code path（所有 fallback chain 在測試中覆蓋）

### 層 3：Python（5/5 檢查完畢）

**結論：PASS**

- `qa_tools.py`：`_get_local_capabilities()` 正確偵測 `OPENAI_API_KEY` + `SUPABASE_URL`，mode line 輸出至 stderr
- `openai_helper.py`：`get_capabilities()` + `format_capability_tag()` 正確分離 CLI 與 Pipeline 語意
- Python 永遠回傳 `llm: "claude-code"`（CLI 場景）或 `llm: "openai"`（Pipeline 場景）— 與 TS server-level 語意正確分離
- 無跨層語意混淆

### 層 4：Documentation（9/9 檢查完畢）

**結論：PASS**（2 處需補充設計決策，已修正）

- CLAUDE.md：capabilities 描述與程式碼一致
- `api/README.md`：`/health` capabilities 物件描述正確
- `research/06-project-architecture.md`：第 5 點已補充業界 tradeoff 註記
- `memory/tech-decisions.md`：已新增「為什麼 capabilities 放在 /health」設計決策
- OpenAPI spec：runtime enum `["lambda", "local-server"]` — 正確（server-level 不回傳 `"cli"`）
- docs-site guide 頁面：與 OpenAPI spec 一致

### 層 5：Test Coverage（21 → 23 → 29 test cases）

**結論：PASS**（v3.6.1 再補 6 個 test cases）

- `capabilities.test.ts`：21 → 27 test cases
  - v3.6：`AGENT_ENABLED="auto"` 無 OpenAI key → `"disabled"`；`SUPABASE_URL` 有設定但 `SUPABASE_ANON_KEY` 空 → `"file"`
  - v3.6.1：+4 `resolveHealthCapabilities` 測試（Claude Code UA + no OpenAI / + OpenAI / Browser UA / no UA）
- `health.test.ts`：3 → 5 test cases
  - v3.6.1：+2 route-level 測試（Claude Code UA → `llm: "claude-code"`；Browser UA → `llm: "none"`）

---

## 交叉驗證矩陣

| 檢查項目 | Commands | TS Routes | Python | Docs | Tests | 業界參考 |
|----------|----------|-----------|--------|------|-------|---------|
| Runtime type 完整性 | N/A | PASS | PASS | PASS | PASS | #7 TS Handbook |
| LLMProvider type 語意 | PASS | PASS | PASS | PASS（補充 JSDoc） | PASS | #1 Fowler |
| /health capabilities | N/A | PASS | N/A | PASS（補充 tradeoff） | PASS | #2 K8s, #3 AWS, #4 Google |
| Server vs Request-level 分離 | N/A | PASS | PASS | PASS | PASS | N/A |
| Agent auto mode | N/A | PASS | N/A | PASS | PASS（補齊） | N/A |
| Supabase 雙條件 | N/A | PASS | PASS | PASS | PASS（補齊） | N/A |
| chat-agent upload | FOUND P2 | N/A | N/A | N/A | N/A | #5 Netflix, #6 Nygard |
| meeting-prep API | FP | N/A | N/A | N/A | N/A | N/A |
| OpenAPI runtime enum | N/A | N/A | N/A | PASS | PASS | N/A |

---

## 發現與修正對照表

| ID | 優先級 | 問題 | 發現層 | 交叉驗證 | 業界依據 | 修正狀態 |
|----|--------|------|--------|---------|---------|---------|
| F-01 | P0 | `Runtime`/`LLMProvider` type 含 server-level 永遠不回傳的值，未文件化 | Docs + Tests | 2 層確認 | #1 Fowler + #7 TS Handbook | **已修正**（JSDoc） |
| F-02 | P1 | `/health` 含 capabilities 的業界 tradeoff 未記錄 | 業界研究 | 3 sources | #2 K8s + #3 AWS + #4 Google | **已修正**（tech-decisions + architecture） |
| F-03 | P2 | `chat-agent` Step 3.5 auto-upload 無 error handling | Commands | 1 層 | #5 Netflix + #6 Nygard | **已修正**（best-effort 指引） |
| F-04 | P3 | 2 個測試分支缺覆蓋（agent auto + supabase partial） | Tests | 1 層 | #7 TS Handbook | **已修正**（+2 tests） |
| F-05 | — | `meeting-prep` 缺 health check | Commands | **False Positive** | 探查確認無 API 呼叫 | 無需修正 |
| F-06 | — | OpenAPI runtime enum 缺 `"cli"` | Docs | 確認正確 | `resolveServerCapabilities` 不回傳 `"cli"` | 無需修正 |

---

## 業界參考清單

| # | 來源 | 核心建議 | 適用發現 |
|---|------|---------|---------|
| 1 | Martin Fowler, "Refactoring" p.88, Speculative Generality | 移除未使用的 type/class；但若跨層共用則保留並文件化 | F-01：保留 type union，加 JSDoc |
| 2 | Kubernetes Pod Lifecycle spec, liveness/readiness probes | Health probe 應 binary yes/no，不含 metadata | F-02：/health 設計決策 |
| 3 | AWS ELB health check documentation | ELB 只看 HTTP status code，不解析 body | F-02：額外欄位無害 |
| 4 | Google API Design Guide, Standard Methods | `GetHealth` 與 `GetServiceInfo` 應分離 | F-02：未來遷移路徑 |
| 5 | Netflix Hystrix fallback pattern | 每個 upstream call 定義 fallback；降級不影響主路徑 | F-03：best-effort upload |
| 6 | Michael Nygard, "Release It!" Ch.5, Circuit Breaker | 連續失敗後 open circuit，避免重複 timeout | F-03：連續 2 次失敗跳過 |
| 7 | TypeScript Handbook, Discriminated Union Exhaustiveness | Union type 應窮舉所有分支或明確標示保留值 | F-01 + F-04：JSDoc + 測試覆蓋 |
| 8 | RFC 9110, HTTP Semantics, User-Agent | User-Agent 是 informational，不應作為授權/能力決策依據 | 驗證 inferCaller 僅用於 logging |
| 9 | RFC 7230, HTTP/1.1 Message Syntax | Health check 慣例：200 = healthy, 5xx = unhealthy | 驗證 /health 回傳 200 |
| 10 | AWS Lambda best practices | Cold start 時 health 應快速回應，避免重計算 | F-02：capabilities 是靜態值 |
| 11 | Google SRE Book, Ch.6 Monitoring | 區分 health（是否活著）vs metadata（系統狀態） | F-02：合併 vs 分離 tradeoff |
| 12 | Twelve-Factor App, Config | 環境變數在啟動時讀取，runtime 不變 | 驗證 capabilities 靜態性 |
| 13 | OWASP API Security Top 10 | 避免在 health endpoint 暴露過多內部資訊 | capabilities 不含敏感資訊（只有 mode flags） |
| 14 | OpenAPI 3.1 Specification | Enum 應反映實際 API 回傳值，非全域 union | 驗證 OpenAPI spec 正確性 |
| 15 | Martin Fowler, "Patterns of Enterprise Application Architecture" | Separated Interface — 跨層共用 type 時保持一致 | F-01：跨層 schema 一致性 |
