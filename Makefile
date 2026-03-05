## SEO Knowledge Insight — Pipeline Makefile
##
## AI 工具（GitHub Copilot / Claude Code）可直接呼叫以下 targets。
## 使用前確認 .env 已設定（參考 .env.example）。
##
## Quick reference:
##   make pipeline            完整流程 fetch-notion→extract-qa→dedupe-classify
##   make check               檢查所有步驟依賴（不執行）
##   make fetch-notion        Notion 擷取（Step 1）
##   make extract-qa          Q&A 萃取（Step 2）
##   make dedupe-classify     去重 + 分類（Step 3）
##   make generate-report     週報生成（Step 4）
##   make evaluate-qa         品質評估（Step 5）
##   make rebuild-embeddings  修復 qa_embeddings.npy 與 qa_final.json 不一致
##   make test                執行測試
##   make dry-run             同 make check（向下相容）
##   make install             安裝依賴

PYTHON := .venv/bin/python
SCRIPT := scripts/run_pipeline.py

# ── 環境設定 ─────────────────────────────────────────

.PHONY: install
install: ## 安裝所有依賴
	pip install -r requirements.txt
	pip install -e ".[dev]"

# ── Pipeline 主流程 ───────────────────────────────────

.PHONY: pipeline
pipeline: ## 完整流程：fetch-notion → extract-qa → dedupe-classify
	$(PYTHON) $(SCRIPT)

.PHONY: dry-run
dry-run: ## 只驗證設定，不實際執行（同 make check）
	$(PYTHON) $(SCRIPT) --check

.PHONY: check
check: ## 檢查所有步驟的依賴是否就緒（不執行任何 API 呼叫）
	$(PYTHON) $(SCRIPT) --check

# ── 分步驟執行 ────────────────────────────────────────

.PHONY: fetch-notion
fetch-notion: ## Notion 擷取（增量模式，只抓新增/有更新）
	$(PYTHON) $(SCRIPT) --step fetch-notion

.PHONY: fetch-notion-force
fetch-notion-force: ## Notion 擷取（強制全量重抓，忽略增量比對）
	$(PYTHON) $(SCRIPT) --step fetch-notion --force

.PHONY: extract-qa
extract-qa: ## Q&A 萃取（增量模式，跳過已完成）
	$(PYTHON) $(SCRIPT) --step extract-qa

.PHONY: extract-qa-test
extract-qa-test: ## Q&A 萃取（只處理前 3 份，快速測試用）
	$(PYTHON) $(SCRIPT) --step extract-qa --limit 3

.PHONY: fetch-medium
fetch-medium: ## Medium 文章擷取（RSS → Markdown）
	$(PYTHON) scripts/01b_fetch_medium.py

.PHONY: fetch-medium-full
fetch-medium-full: ## Medium 完整文章擷取（Sitemap → Playwright fallback，突破 RSS 10 篇限制）
	$(PYTHON) scripts/01b_fetch_medium.py --playwright

.PHONY: fetch-ithelp
fetch-ithelp: ## iThome 鐵人賽擷取（HTML → Markdown）
	$(PYTHON) scripts/01c_fetch_ithelp.py

.PHONY: update-ithelp-titles
update-ithelp-titles: ## 從集合頁更新 iThome 文章標題（不重抓內容）
	$(PYTHON) scripts/01c_fetch_ithelp.py --update-titles

.PHONY: fetch-google-cases
fetch-google-cases: ## Google Search Central Case Studies 擷取（HTML → Markdown）
	$(PYTHON) scripts/01d_fetch_google_cases.py

.PHONY: fetch-articles
fetch-articles: ## 擷取所有外部文章（Medium + iThome + Google Cases）
	$(PYTHON) scripts/01b_fetch_medium.py
	$(PYTHON) scripts/01c_fetch_ithelp.py
	$(PYTHON) scripts/01d_fetch_google_cases.py

.PHONY: fetch-all
fetch-all: fetch-notion fetch-articles ## Notion + 所有外部文章

.PHONY: dedupe-classify
dedupe-classify: ## 去重 + 分類（collection-scoped）
	$(PYTHON) $(SCRIPT) --step dedupe-classify

.PHONY: dedupe-only
dedupe-only: ## 只去重（跳過分類，用於診斷）
	$(PYTHON) $(SCRIPT) --step dedupe-classify --skip-dedup

.PHONY: rebuild-embeddings
rebuild-embeddings: ## 從現有 qa_final.json 重建 qa_embeddings.npy（優先走 cache，不重跑 dedup/classify）
	$(PYTHON) scripts/03_dedupe_classify.py --rebuild-embeddings

.PHONY: enrich
enrich: ## Offline enrichment（synonym + freshness + usage，不消耗 token）
	$(PYTHON) scripts/enrich_qa.py

.PHONY: generate-report
generate-report: ## 週報生成（使用 Google Sheets 預設指標）
	$(PYTHON) $(SCRIPT) --step generate-report

.PHONY: generate-report-local
generate-report-local: ## 週報生成（使用本機 TSV 指標，INPUT=path/to/metrics.tsv）
	$(PYTHON) $(SCRIPT) --step generate-report --input $(INPUT)

.PHONY: evaluate-qa
evaluate-qa: ## 品質評估（預設抽樣 30 筆）
	$(PYTHON) $(SCRIPT) --step evaluate-qa

.PHONY: evaluate-qa-full
evaluate-qa-full: ## 品質評估（完整：100 筆 + 來源驗證 + Retrieval 評估）
	$(PYTHON) $(SCRIPT) --step evaluate-qa --sample 100 --with-source --eval-retrieval

.PHONY: eval-semantic
eval-semantic: ## Semantic + Reranker Retrieval Eval（比較 keyword/hybrid/rerank 三種模式）
	cd api && npx tsx scripts/eval-semantic.ts

.PHONY: eval-semantic-k3
eval-semantic-k3: ## 同上，top-k=3
	cd api && npx tsx scripts/eval-semantic.ts --top-k 3

.PHONY: eval-laminar
eval-laminar: ## Laminar 正式 Eval Run（keyword baseline，推送至 Dashboard）
	$(PYTHON) scripts/_eval_laminar.py

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
	$(PYTHON) scripts/list_pipeline_state.py --step extract-qa

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
version-history: ## 查看 pipeline 版本歷史（所有步驟的最新版本）
	@$(PYTHON) scripts/qa_tools.py version-history

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
