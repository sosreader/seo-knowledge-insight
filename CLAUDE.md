# CLAUDE.md

> 專案架構、指令、模型政策等深度參考：`.claude/skills/seo-qa-pipeline.md`

---

## Critical Rules

### 1. Code Organization

- Many small files over few large files（高內聚、低耦合）
- 每支腳本典型 200–400 行，上限 800 行
- 依功能/領域組織，而非依類型（scripts/ 為 pipeline 步驟，utils/ 為共用模組）

### 2. Code Style

- 不在 production code 留 `print()` 除錯語句，改用 `logging`
- Immutability：函式回傳新物件，不直接修改傳入的 list/dict
- 所有對外輸入（API response、檔案內容）皆需驗證，失敗應拋出有意義的例外
- 使用 `try/except` 明確捕捉，不吞掉例外（禁止 `except: pass`）

### 3. Testing

- TDD：先寫測試，再實作
- 最低覆蓋率 80%
- 單元測試：utils/ 純邏輯函式
- 整合測試：OpenAI / Notion API 呼叫（用 mock）
- E2E 測試：完整 pipeline 步驟（`--limit 3` 小量驗證）

### 4. Security

- 禁止 hardcode 任何 secret（API key、token）
- 所有敏感設定從 `.env` 讀取，參考 `.env.example`
- 寫入檔案前驗證路徑，防止 path traversal
- LLM 回傳內容當作不可信輸入，必須驗證 schema 後才使用

---

## Key Patterns

### LLM 回傳驗證

```python
# 推理模型（o 系列）content 可能為空，必須防守
result = response.choices[0].message.content
if not result or not result.strip():
    # 記錄並跳過，不 inflate denominator
    continue
data = json.loads(result)
```

### Pipeline 函式回傳格式

```python
# 統一回傳 dict，方便串接與測試
def process_step(input_data) -> dict:
    try:
        result = _do_work(input_data)
        return {"success": True, "data": result}
    except Exception as e:
        logger.error("Step failed: %s", e)
        return {"success": False, "error": str(e)}
```

---

## Available Claude Commands

- `/tdd` — 測試驅動開發工作流（先寫測試）
- `/plan` — 建立實作計畫，等待確認後再動手
- `/code-review` — Python 程式碼品質審查
- `/build-fix` — 修復建置 / 型別錯誤
- `/learn-eval` — 萃取本 session 可重用模式並存為 skill

---

## Git Workflow

- Conventional commits：`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- 禁止直接 commit 到 `main`
- PR 需通過所有測試才能合併
- Commit message 以中文或英文皆可，但須清楚描述「為什麼」而非「做了什麼」

### Commit 前知識沉澱清單（必做）

每次 commit 前，依序確認以下步驟是否適用，適用則執行：

1. **萃取 patterns** — 本次修改是否有可重用的模式？執行 `/learn-eval` 萃取並存入 `~/.claude/skills/learned/`
2. **更新 research/** — 本次修改涉及新技術知識？依下方分類指引補充到對應的 `research/*.md`
3. **更新 MEMORY.md** — 評估基準線變動、Bug 修復、模型替換等？更新 `~/.claude/projects/.../memory/MEMORY.md`
4. **更新架構圖** — 架構有重大調整？更新 `research/06-project-architecture.md` 的 Mermaid 圖和 Changelog

若本次為 typo fix、純測試修正、chore 類變更，以上可跳過。

### research/ 分類指引

新知識補充時，依主題寫入對應檔案：

| 主題 | 檔案 |
|------|------|
| LLM / Token / Embedding / Cosine / Prompt 基礎 / Structured Output | `research/01-ai-fundamentals.md` |
| RAG / Hybrid Search / RAG 框架比較 / Retrieval 指標 | `research/02-rag-and-search.md` |
| 評估 / LLM-as-Judge / Reasoning Model / 評估維度設計 | `research/03-evaluation.md` |
| Prompt Engineering 進階 / 業界最佳實踐 | `research/04-prompting.md` |
| 模型選擇決策 / Embedding 模型比較 | `research/05-models.md` |
| 專案架構 / 技術決策 / Changelog / Mermaid 圖 | `research/06-project-architecture.md` |
| 部署 / FastAPI / ECR+EC2 / Docker | `research/07-deployment.md` |
