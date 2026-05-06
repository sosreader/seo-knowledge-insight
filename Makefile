## SEO Knowledge Insight — Pipeline Makefile
##
## AI 工具（GitHub Copilot / Claude Code）可直接呼叫以下 targets。
## 使用前確認 .env 已設定（參考 .env.example）。
##
## Quick reference:
##   make pipeline            Notion-core 流程 fetch-notion→extract-qa→dedupe-classify
##   make check               檢查所有步驟依賴（不執行）
##   make fetch-notion        Notion 擷取（Step 1）
##   make fetch-notion-since SINCE=2026-04-27  Notion 擷取（指定下界）
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
pipeline: ## Notion-core 流程：fetch-notion → extract-qa → dedupe-classify
	$(PYTHON) $(SCRIPT)

.PHONY: dry-run
dry-run: ## 只驗證設定，不實際執行（同 make check）
	$(PYTHON) $(SCRIPT) --check

.PHONY: check
check: ## 檢查所有步驟的依賴是否就緒（不執行任何 API 呼叫）
	$(PYTHON) $(SCRIPT) --check

# ── 分步驟執行 ────────────────────────────────────────

.PHONY: fetch-notion
fetch-notion: ## Notion 擷取（增量模式，只抓新增/有更新，篩選 SEO 相關頁面）
	$(PYTHON) $(SCRIPT) --step fetch-notion --filter SEO

.PHONY: fetch-notion-since
fetch-notion-since: ## Notion 擷取（指定 since 下界），用法：make fetch-notion-since SINCE=2026-04-27
	@if [ -z "$(SINCE)" ]; then \
		echo "Usage: make fetch-notion-since SINCE=YYYY-MM-DD"; \
		exit 1; \
	fi
	$(PYTHON) $(SCRIPT) --step fetch-notion --since $(SINCE) --filter SEO

.PHONY: fetch-notion-force
fetch-notion-force: ## Notion 擷取（強制全量重抓，忽略增量比對）
	$(PYTHON) $(SCRIPT) --step fetch-notion --force --filter SEO

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

.PHONY: fetch-ahrefs
fetch-ahrefs: ## Ahrefs Blog 擷取（L4 SEO 內容，HTML → Markdown）
	$(PYTHON) scripts/01e_fetch_ahrefs.py

.PHONY: fetch-sej
fetch-sej: ## Search Engine Journal 擷取（RSS → Markdown）
	$(PYTHON) scripts/01f_fetch_sej.py

.PHONY: fetch-growthmemo
fetch-growthmemo: ## Growth Memo (Kevin Indig) 擷取（Substack RSS → Markdown）
	$(PYTHON) scripts/01g_fetch_growthmemo.py

.PHONY: fetch-google-blog
fetch-google-blog: ## Google Search Central Blog 擷取（官方 SEO 公告，Atom → Markdown）
	$(PYTHON) scripts/01h_fetch_google_blog.py

.PHONY: fetch-google-blog-zhtw
fetch-google-blog-zhtw: ## Google Search Central Blog 繁體中文版擷取（官方 SEO 公告，HTML → Markdown）
	$(PYTHON) scripts/01h_fetch_google_blog.py --lang zh-tw

.PHONY: fetch-webdev
fetch-webdev: ## Web.dev 擷取（CWV / Performance 技術文章，RSS → Markdown）
	$(PYTHON) scripts/01i_fetch_webdev.py

.PHONY: fetch-screaming-frog
fetch-screaming-frog: ## Screaming Frog Blog 擷取（技術 SEO 深度文章，RSS → Markdown）
	$(PYTHON) scripts/01j_fetch_screaming_frog.py

.PHONY: fetch-articles
fetch-articles: ## 擷取所有外部文章（10 個來源）
	$(PYTHON) scripts/01b_fetch_medium.py
	$(PYTHON) scripts/01c_fetch_ithelp.py
	$(PYTHON) scripts/01d_fetch_google_cases.py
	$(PYTHON) scripts/01e_fetch_ahrefs.py
	$(PYTHON) scripts/01f_fetch_sej.py
	$(PYTHON) scripts/01g_fetch_growthmemo.py
	$(PYTHON) scripts/01h_fetch_google_blog.py
	$(PYTHON) scripts/01h_fetch_google_blog.py --lang zh-tw
	$(PYTHON) scripts/01i_fetch_webdev.py
	$(PYTHON) scripts/01j_fetch_screaming_frog.py

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
evaluate-qa: ## 品質評估（Laminar eval push，keyword baseline）
	$(PYTHON) scripts/_eval_laminar.py

.PHONY: evaluate-qa-full
evaluate-qa-full: ## Semantic + Reranker Retrieval Eval（比較 keyword/hybrid/rerank 三種模式）
	cd api && npx tsx scripts/eval-semantic.ts

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
api: ## 啟動 TypeScript API 開發伺服器（port 8002）
	cd api && pnpm dev

.PHONY: api-test
api-test: ## 執行 TypeScript API 測試（224 tests）
	cd api && pnpm test

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
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from utils.pipeline_cache import cache_stats; print('Cache stats:'); [print(f'  {ns:<12}: {cache_stats(ns)[\"count\"]:>5} 筆  {cache_stats(ns)[\"size_bytes\"]/1024:>8.1f} KB') for ns in ('extraction', 'embedding', 'classify', 'merge', 'report')]"

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

# ── Metadata 回填 / 更新 ───────────────────────────────

.PHONY: backfill-extraction-model
backfill-extraction-model: ## 回填 extraction_model（實際寫入 Supabase）
	$(PYTHON) scripts/backfill_extraction_model.py --execute

.PHONY: backfill-extraction-model-dry
backfill-extraction-model-dry: ## 回填 extraction_model 預覽（不寫入）
	$(PYTHON) scripts/backfill_extraction_model.py --dry-run

.PHONY: backfill-extraction-model-verify
backfill-extraction-model-verify: ## 驗證 extraction_model IS NULL 筆數
	$(PYTHON) scripts/backfill_extraction_model.py --verify

.PHONY: backfill-maturity
backfill-maturity: ## 回填 maturity_relevance（實際寫入 Supabase）
	$(PYTHON) scripts/backfill_maturity_relevance.py --execute

.PHONY: backfill-maturity-dry
backfill-maturity-dry: ## 回填 maturity_relevance 預覽（不寫入）
	$(PYTHON) scripts/backfill_maturity_relevance.py --dry-run

.PHONY: backfill-maturity-verify
backfill-maturity-verify: ## 驗證 maturity_relevance 分布
	$(PYTHON) scripts/backfill_maturity_relevance.py --verify

.PHONY: backfill-qa-final-metadata
backfill-qa-final-metadata: ## 回填 qa_final.json 缺漏 metadata（實際寫入）
	$(PYTHON) scripts/backfill_qa_final_metadata.py --execute

.PHONY: backfill-qa-final-metadata-dry
backfill-qa-final-metadata-dry: ## 回填 qa_final.json 缺漏 metadata 預覽
	$(PYTHON) scripts/backfill_qa_final_metadata.py --dry-run

.PHONY: backfill-qa-final-metadata-verify
backfill-qa-final-metadata-verify: ## 驗證 qa_final.json metadata 缺漏
	$(PYTHON) scripts/backfill_qa_final_metadata.py --verify

.PHONY: backfill-maturity-llm-prepare
backfill-maturity-llm-prepare: ## 切批次（給 Claude Code sub-agents 分類用，預設 8 批）
	$(PYTHON) scripts/backfill_maturity_llm.py prepare-batches --count 8

.PHONY: backfill-maturity-llm-status
backfill-maturity-llm-status: ## 顯示 batch 與 result 進度
	$(PYTHON) scripts/backfill_maturity_llm.py status

.PHONY: backfill-maturity-llm-merge
backfill-maturity-llm-merge: ## 套用 result_*.json 到 qa_final.json（實際寫入）
	$(PYTHON) scripts/backfill_maturity_llm.py merge --execute

.PHONY: backfill-maturity-llm-merge-dry
backfill-maturity-llm-merge-dry: ## 預覽 merge（不寫入）
	$(PYTHON) scripts/backfill_maturity_llm.py merge --dry-run

.PHONY: push-qa-metadata
push-qa-metadata: ## 把本地 qa_final.json 變動 metadata（maturity + extraction_model）PATCH 至 Supabase
	$(PYTHON) scripts/push_qa_metadata_to_supabase.py --execute

.PHONY: push-qa-metadata-dry
push-qa-metadata-dry: ## push 預覽
	$(PYTHON) scripts/push_qa_metadata_to_supabase.py --dry-run

.PHONY: push-qa-metadata-verify
push-qa-metadata-verify: ## 驗證本地 vs Supabase metadata 差集
	$(PYTHON) scripts/push_qa_metadata_to_supabase.py --verify

.PHONY: update-freshness
update-freshness: ## 更新 freshness_score 指數衰減（實際寫入）
	$(PYTHON) scripts/update_freshness.py --execute

.PHONY: update-freshness-dry
update-freshness-dry: ## 更新 freshness_score 預覽（不寫入）
	$(PYTHON) scripts/update_freshness.py --dry-run

.PHONY: update-freshness-verify
update-freshness-verify: ## 驗證 freshness_score 正確性
	$(PYTHON) scripts/update_freshness.py --verify

# ── Supabase 遷移 ──────────────────────────────────────

.PHONY: migrate-supabase
migrate-supabase: ## 將 qa_final.json + qa_embeddings.npy 遷移至 Supabase pgvector
	$(PYTHON) scripts/migrate_to_supabase.py

.PHONY: migrate-supabase-dry
migrate-supabase-dry: ## 遷移試跑（不寫入）
	$(PYTHON) scripts/migrate_to_supabase.py --dry-run

.PHONY: migrate-supabase-verify
migrate-supabase-verify: ## 驗證 Supabase qa_items 筆數
	$(PYTHON) scripts/migrate_to_supabase.py --verify

.PHONY: quality-gate
quality-gate: ## ETL 品質門檻檢查（hit_rate/mrr/qa_count）
	$(PYTHON) scripts/quality_gate.py

# ── Supabase 同步 ────────────────────────────────────

.PHONY: sync-db
sync-db: ## 上傳 reports + sessions + meeting-prep 到 Supabase（跳過已存在）
	cd api && npx tsx scripts/sync-db.ts upload

.PHONY: sync-db-status
sync-db-status: ## 檢視本地 vs Supabase 差異
	cd api && npx tsx scripts/sync-db.ts status

.PHONY: sync-db-force
sync-db-force: ## 強制上傳（覆蓋已存在項目）
	cd api && npx tsx scripts/sync-db.ts upload --force

.PHONY: sync-db-dry
sync-db-dry: ## 同步試跑（不寫入）
	cd api && npx tsx scripts/sync-db.ts upload --dry-run

# ── Eval 品質門禁 ────────────────────────────────────

.PHONY: golden-from-feedback
golden-from-feedback: ## 從使用者回饋生成 golden dataset 候選（需人工審核）
	cd api && npx tsx scripts/feedback-to-golden.ts

.PHONY: check-ai-crawlers
check-ai-crawlers: ## 檢查網站 AI 爬蟲可讀性（URL=https://example.com）
	cd api && npx tsx scripts/ai-crawler-checker.ts $(URL)

.PHONY: evaluate-retrieval-by-model
evaluate-retrieval-by-model: ## 按 extraction_model 分群評估檢索品質（MODEL=claude-code）
	$(PYTHON) evals/eval_retrieval.py --model $(MODEL)

# ── Meeting-Prep Eval ────────────────────────────────

.PHONY: evaluate-meeting-prep-structure
evaluate-meeting-prep-structure: ## Meeting-Prep 結構品質評估（rule-based，零 LLM 成本）
	$(PYTHON) evals/eval_meeting_prep_structure.py

.PHONY: evaluate-meeting-prep-grounding
evaluate-meeting-prep-grounding: ## Meeting-Prep 引用根基評估（KB lookup，零 LLM 成本）
	$(PYTHON) evals/eval_meeting_prep_grounding.py

.PHONY: evaluate-meeting-prep
evaluate-meeting-prep: evaluate-meeting-prep-structure evaluate-meeting-prep-grounding ## Meeting-Prep 快速評估（L1+L2）

.PHONY: evaluate-meeting-prep-llm
evaluate-meeting-prep-llm: ## Meeting-Prep L3 LLM threshold gate（需先跑 /evaluate-meeting-prep-quality）
	$(PYTHON) evals/eval_meeting_prep_llm.py

.PHONY: evaluate-meeting-prep-web
evaluate-meeting-prep-web: ## Meeting-Prep L4 S2 時效性驗證（rule-based）
	$(PYTHON) evals/eval_meeting_prep_web.py

.PHONY: evaluate-meeting-prep-quick
evaluate-meeting-prep-quick: evaluate-meeting-prep-structure evaluate-meeting-prep-grounding ## Meeting-Prep L1+L2 快速評估（零 LLM 成本）

.PHONY: evaluate-meeting-prep-coherence
evaluate-meeting-prep-coherence: ## Meeting-Prep L2.5 跨 Section 邏輯一致性（零 LLM 成本）
	$(PYTHON) evals/eval_meeting_prep_coherence.py

.PHONY: evaluate-meeting-prep-novelty
evaluate-meeting-prep-novelty: ## Meeting-Prep L2.6 內容新穎度評估（跨週重複偵測，零 LLM 成本）
	$(PYTHON) evals/eval_meeting_prep_novelty.py

.PHONY: evaluate-meeting-prep-full
evaluate-meeting-prep-full: evaluate-meeting-prep-structure evaluate-meeting-prep-grounding evaluate-meeting-prep-coherence evaluate-meeting-prep-novelty evaluate-meeting-prep-llm evaluate-meeting-prep-web ## Meeting-Prep 完整 6 層（L1+L2+L2.5+L2.6+L3+L4）

# ── 週報品質評估 ──────────────────────────────────

.PHONY: evaluate-report
evaluate-report: ## 週報品質評估 L1+L2（rule-based，不需 API key）
	@echo "Usage: make evaluate-report REPORT=output/report_XXXXXXXX.md"
	@test -n "$(REPORT)" || (echo "ERROR: REPORT 參數必填" && exit 1)
	$(PYTHON) scripts/_eval_report.py --report "$(REPORT)"

.PHONY: evaluate-maturity-classification
evaluate-maturity-classification: ## 成熟度分類準確度評估（rule-based，零 LLM 成本）
	$(PYTHON) evals/eval_maturity_classification.py

.PHONY: evaluate-chat-maturity
evaluate-chat-maturity: ## Chat 成熟度適切性評估（需 API server + OpenAI）
	$(PYTHON) evals/eval_chat_maturity.py

# ── 會議準備 ──────────────────────────────────────

.PHONY: meeting-prep-articles
meeting-prep-articles: ## 列出顧問文章清單（去重）
	$(PYTHON) scripts/meeting_prep_helper.py list-consultant-articles

.PHONY: meeting-prep-topics
meeting-prep-topics: ## 最近 3 份會議的主題詞
	$(PYTHON) scripts/meeting_prep_helper.py extract-recent-topics

.PHONY: meeting-prep-topics-json
meeting-prep-topics-json: ## 最近 3 份會議的主題詞（JSON）
	$(PYTHON) scripts/meeting_prep_helper.py extract-recent-topics --json

# ── AutoResearch（自主循環優化）──────────────────────

.PHONY: autoresearch-baseline
autoresearch-baseline: ## AutoResearch retrieval baseline eval（需先啟動 API server + RATE_LIMIT_DEFAULT=9999）
	bash autoresearch/retrieval/runner.sh "baseline"

.PHONY: autoresearch-meeting-prep-baseline
autoresearch-meeting-prep-baseline: ## AutoResearch meeting-prep baseline eval（rule-based composite，零 LLM）
	$(PYTHON) autoresearch/meeting-prep/eval_local.py --report eval/fixtures/meeting_prep/meeting_prep_20260306_ea576a4f.md

# ── 說明 ─────────────────────────────────────────────

.PHONY: help
help: ## 顯示所有可用 targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
