## SEO Knowledge Insight — Pipeline Makefile
##
## AI 工具（GitHub Copilot / Claude Code）可直接呼叫以下 targets。
## 使用前確認 .env 已設定（參考 .env.example）。
##
## Quick reference:
##   make pipeline           完整流程 step 1→2→3
##   make check              檢查所有步驟依賴（不執行）
##   make step1              Notion 擷取
##   make step2              Q&A 萃取
##   make step3              去重 + 分類
##   make step4              週報生成（需指定 INPUT）
##   make step5              品質評估
##   make rebuild-embeddings 修復 qa_embeddings.npy 與 qa_final.json 不一致
##   make test               執行測試
##   make dry-run            同 make check（向下相容）
##   make install            安裝依賴

PYTHON := .venv/bin/python
SCRIPT := scripts/run_pipeline.py

# ── 環境設定 ─────────────────────────────────────────

.PHONY: install
install: ## 安裝所有依賴
	pip install -r requirements.txt
	pip install -e ".[dev]"

# ── Pipeline 主流程 ───────────────────────────────────

.PHONY: pipeline
pipeline: ## 完整流程：step 1 → 2 → 3
	$(PYTHON) $(SCRIPT)

.PHONY: dry-run
dry-run: ## 只驗證設定，不實際執行（同 make check）
	$(PYTHON) $(SCRIPT) --check

.PHONY: check
check: ## 檢查所有步驟的依賴是否就緒（不執行任何 API 呼叫）
	$(PYTHON) $(SCRIPT) --check

# ── 分步驟執行 ────────────────────────────────────────

.PHONY: step1
step1: ## 步驟 1：從 Notion 擷取會議紀錄
	$(PYTHON) $(SCRIPT) --step 1

.PHONY: step1-force
step1-force: ## 步驟 1：強制全量重抓（忽略增量比對）
	$(PYTHON) $(SCRIPT) --step 1 --force

.PHONY: step2
step2: ## 步驟 2：OpenAI Q&A 萃取
	$(PYTHON) $(SCRIPT) --step 2

.PHONY: step2-test
step2-test: ## 步驟 2：只處理前 3 份（快速測試用）
	$(PYTHON) $(SCRIPT) --step 2 --limit 3

.PHONY: step3
step3: ## 步驟 3：去重 + 分類
	$(PYTHON) $(SCRIPT) --step 3

.PHONY: step3-classify-only
step3-classify-only: ## 步驟 3：只分類（跳過去重）
	$(PYTHON) $(SCRIPT) --step 3 --skip-dedup

.PHONY: rebuild-embeddings
rebuild-embeddings: ## 從現有 qa_final.json 重建 qa_embeddings.npy（優先走 cache，不重跑 dedup/classify）
	$(PYTHON) scripts/03_dedupe_classify.py --rebuild-embeddings

.PHONY: step4
step4: ## 步驟 4：週報生成（使用 Google Sheets 預設指標）
	$(PYTHON) $(SCRIPT) --step 4

.PHONY: step4-local
step4-local: ## 步驟 4：使用本機 TSV 指標 (INPUT=path/to/metrics.tsv)
	$(PYTHON) $(SCRIPT) --step 4 --input $(INPUT)

.PHONY: step5
step5: ## 步驟 5：品質評估（預設抽樣 30 筆）
	$(PYTHON) $(SCRIPT) --step 5

.PHONY: step5-full
step5-full: ## 步驟 5：完整評估 + 來源驗證 + Retrieval 評估
	$(PYTHON) $(SCRIPT) --step 5 --sample 100 --with-source --eval-retrieval

# ── 測試 ─────────────────────────────────────────────

.PHONY: test
test: ## 執行所有測試
	$(PYTHON) -m pytest tests/ -v

.PHONY: test-unit
test-unit: ## 只執行核心邏輯單元測試
	$(PYTHON) -m pytest tests/test_core.py -v

.PHONY: test-api
test-api: ## 執行 API 測試
	$(PYTHON) -m pytest tests/test_api_chat.py tests/test_api_qa.py tests/test_api_search.py -v

# ── API 伺服器（開發用） ──────────────────────────────

.PHONY: api
api: ## 啟動 FastAPI 開發伺服器（port 8000）
	$(PYTHON) -m uvicorn app.main:app --reload --port 8000

# ── Pipeline 狀態（AI 工具輔助） ──────────────────────

.PHONY: status
status: ## 顯示 pipeline 目前狀態（AI 工具用，不需要任何 API key）
	$(PYTHON) scripts/list_pipeline_state.py --status

.PHONY: list-unprocessed
list-unprocessed: ## 列出尚未萃取 Q&A 的 Markdown 檔案（供 AI 工具處理）
	$(PYTHON) scripts/list_pipeline_state.py --step 2

.PHONY: merge-qa
merge-qa: ## 合併所有 per-meeting Q&A → qa_all_raw.json（AI 工具完成萃取後執行）
	$(PYTHON) scripts/list_pipeline_state.py --merge

# ── Cache 管理 ────────────────────────────────────────

.PHONY: cache-stats
cache-stats: ## 查看各 namespace 的 cache 使用量
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, '.')\n\
from utils.pipeline_cache import cache_stats\n\
print('Cache stats:')\n\
for ns in ['extraction', 'embedding', 'classify', 'merge', 'report']:\n\
    s = cache_stats(ns)\n\
    kb = s['size_bytes'] / 1024\n\
    print(f'  {ns:<12}: {s[\"count\"]:>5} 筆  {kb:>8.1f} KB')\n\
"

# 使用方式: make cache-clear ns=embedding
.PHONY: cache-clear
cache-clear: ## 清除指定 ns 的 cache（不指定則清除全部），e.g. make cache-clear ns=embedding
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, '.')\n\
from utils.pipeline_cache import cache_clear\n\
ns = '$(ns)'\n\
if ns:\n\
    n = cache_clear(ns)\n\
    print(f'Cleared {n} entries from namespace [{ns}]')\n\
else:\n\
    total = 0\n\
    for namespace in ['extraction','embedding','classify','merge','report']:\n\
        n = cache_clear(namespace)\n\
        total += n\n\
        print(f'  {namespace}: {n} 筆')\n\
    print(f'Total cleared: {total} entries')\n\
"

.PHONY: version-history
version-history: ## 查看 pipeline 版本歷史與 token 統計
	@$(PYTHON) -c "\
import sys; sys.path.insert(0, '.')\n\
from utils.pipeline_version import get_version_history, get_all_token_stats\n\
for step in [2, 3, 4]:\n\
    versions = get_version_history(step)\n\
    if versions:\n\
        print(f'\\n=== Step {step} ({len(versions)} versions) ===')\n\
        for v in versions[:5]:\n\
            ts = v['timestamp'][:10]\n\
            tokens = v.get('tokens_used', 0)\n\
            saved = v.get('tokens_saved', 0)\n\
            print(f'  {v[\"version_id\"]}  {ts}  tokens={tokens}  saved={saved}')\n\
stats = get_all_token_stats()\n\
print(f'\\nTotal tokens used : {stats[\"total_used\"]:,}')\n\
print(f'Total tokens saved: {stats[\"total_saved\"]:,}')\n\
"

# ── 稽核日誌 ─────────────────────────────────────────

.PHONY: audit
audit: ## 今天完整稽核報告（fetch + access）
	$(PYTHON) scripts/audit_trail.py report

.PHONY: audit-fetch
audit-fetch: ## Notion fetch 操作記錄（session 摘要）
	$(PYTHON) scripts/audit_trail.py fetch --sessions

.PHONY: audit-access
audit-access: ## 資料存取記錄（今天）
	$(PYTHON) scripts/audit_trail.py access

.PHONY: audit-top
audit-top: ## Top 30 最常被存取的 QA
	$(PYTHON) scripts/audit_trail.py access --top 30

# ── 說明 ─────────────────────────────────────────────

.PHONY: help
help: ## 顯示所有可用 targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
