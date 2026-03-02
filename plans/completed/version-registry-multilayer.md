# Version Registry 增強 + Multi-Layer Context 實作計畫

**狀態：已完成（2026-03-02）**
**對應 global plan：** `~/.claude/plans/jaunty-coalescing-stonebraker.md`

---

## 背景

### 問題 1：Version Registry 停在舊版

`qa_final.json` v2.0（655 筆，重新萃取）繞過 `record_artifact()` 直接輸出，
導致 registry 顯示的仍是舊版 717 筆的 version ID。
需要補登機制（`register_existing_file()`）和語意標籤（`label_version()`）。

### 問題 2：搜尋品質瓶頸（KW Hit Rate 78%）

OpenAI data agent（March 2026）啟發的三層架構：
- **Knowledge Layer**：靜態知識庫（qa_final.json）
- **Learnings Layer**：動態失敗記錄（learnings.jsonl）
- **Context Layer**：同義詞 + 時效性調整（enrichment）

---

## 研究支撐

### 同義詞擴展
- Xu & Croft, "Query Expansion Using Local and Global Document Analysis" (SIGIR 1996)
- BM25F + synonym expansion 是企業搜尋標準作法（Elasticsearch synonym token filter）
- Ma et al. "Query2Doc" (EMNLP 2023)：查詢豐富化顯著改善 retrieval

### 時效性衰減
- Dong et al. "Towards Recency Ranking in Web Search" (WWW 2010)
- Google Freshness Update (Nov 2011)：時效性是官方排名因素
- SEO 演算法年更，2023 年的建議在 2026 年可能有害

### Learning from Failures
- Asai et al. "Self-RAG" (ICLR 2024)：自適應 RAG 改善回饋迴路
- OpenAI data agent：Knowledge 層 vs Learnings 層的業界驗證

---

## ECC 整合策略

| ECC 工具 | 使用情況 |
|---------|---------|
| `everything-claude-code:python-reviewer` | Phase A~C 完成後審查，修復 5 個 HIGH 問題 |
| `everything-claude-code:tdd-guide` | 每個 Phase 先寫測試（44 個新 tests） |
| `/learn-eval` | Session 結束萃取 1 個 Global skill（23/25）|

---

## 實作範圍（已完成）

### Phase A：Version Registry 增強

**新增 `utils/pipeline_version.py`：**
- `STEP_NAMES / _NAME_TO_STEP`：步驟名稱雙向映射
- `resolve_step(int|str) → int`：int / str 名稱 / 數字字串三種輸入
- `label_version(version_id, label)`：語意標籤（不可變 dict 更新）
- `register_existing_file(step, file_path, label)`：補登既有檔案
- `record_artifact()` 加入 `label` 參數 + `step_name` 欄位
- `get_latest_version()` / `get_version_history()` 支援 str 名稱

**新增 `scripts/qa_tools.py` 子命令：**
- `register-version --step <name|int> --file <path> [--label]`
- `version-history [--step <name|int>]`
- `label-version --version-id <id> --label <label>`
- `merge-qa` 合併後自動補登 qa_all_raw.json

**Makefile：** `version-history` 委派 qa_tools.py

**版本補登與標記：**
```
step2_2026-03-01_ef7527a9b2dd6645 [防幻覺規則全量重萃取@2026-03-02]
step3_2026-03-01_6d77c583cf502d6a [KW去重分類重跑@2026-03-02]
step2_2026-02-28_4a34a0b61ff169f2 [初版萃取含KW-Fuzzy匹配@2026-02-28]
step3_2026-02-28_e71549b48cdf62b7 [初版去重分類@2026-02-28]
```

**測試：** +21 tests（TestResolveStep/TestRecordArtifactStepName/TestLabelVersion/TestRegisterExistingFile/TestVersionHistoryStepName）

### Phase B：Multi-Layer Context Phase 1

**前置修復（HIGH/MEDIUM）：**
- `app/core/store.py`：`hybrid_search()` 改用 `self._id_index`（O(1)，HIGH-1）
- `app/config.py`：新增 `QA_ENRICHED_JSON_PATH`（HIGH-3）
- `utils/audit_logger.py`：`log_search()` / `log_chat()` 加入 `top_score` 欄位（MEDIUM-5）
- `config.py`：新增 `SYNONYM_BOOST=0.05` / `FRESHNESS_MIN=0.5`

**新增模組：**
- `utils/synonym_dict.py`：METRIC_QUERY_MAP 衍生 + 補充詞典，`@functools.lru_cache`
- `utils/freshness.py`：指數衰減，半衰期 540 天，min_score=0.5
- `scripts/enrich_qa.py`：Offline pipeline，輸出 `qa_enriched.json`
- Makefile `enrich` target

**搜尋引擎更新（`utils/search_engine.py`）：**
- `SearchEngine.__init__()` 預計算 `_synonym_boost_vec` + `_freshness_vec`
- `_hybrid_scores()` 加入 `_compute_synonym_bonus()` + freshness 乘數
- `search_multi()` 加入同義詞 bonus 矩陣 + freshness broadcast

**store.py 更新：**
- `QAItem` 新增 `synonyms / freshness_score / search_hit_count`
- `load()` 優先載入 `qa_enriched.json`，fallback `qa_final.json`

**測試：** +13 tests（TestSynonymDict/TestFreshnessDecay/TestEnrichedSearch）

### Phase C：Learning Store + Feedback API

- `utils/learning_store.py`：JSONL append-only，`record_miss()` / `record_feedback()` / `get_relevant_learnings()`
- `app/routers/feedback.py`：POST /api/v1/feedback（helpful / not_relevant，Literal 型別驗證）
- `app/main.py`：掛載 feedback router
- `app/core/chat.py`：staleness 警示（`_is_stale()` 18 個月閾值），搜尋 miss 記錄

**測試：** +8 tests（TestFeedbackEndpoint/TestLearningStore）

### Phase D：Laminar 整合

- `evals/eval_enrichment.py`：enrichment 前後 KW Hit Rate 比較（已連線 Laminar）
- `utils/laminar_scoring.py`：新增 `score_enrichment_boost()` / `score_search_miss()`

---

## Laminar 評估結果

### 初次執行（2026-03-02，無 enrichment）

使用 `eval/golden_retrieval.json`（20 筆 cases），qa_enriched.json 尚未產生：

| 指標 | 結果 | 目標 |
|------|------|------|
| kw_hit_rate_with_synonyms | 70.4%（baseline） | ≥ 85% |
| freshness_rank_quality | 1.0 | ≥ 0.9 |
| synonym_coverage | 0.0（無 qa_enriched.json） | TBD |

### 第二次執行（2026-03-02，make enrich 後）

執行 `make enrich` → `avg_synonyms=11.09`、`avg_freshness=0.9076`（655 筆），重跑 eval：

| 指標 | Baseline | After enrichment | Delta | 目標 |
|------|---------|-----------------|-------|------|
| kw_hit_rate_with_synonyms | 70.4% | **79.67%** | +9.27pp | ≥ 85% |
| freshness_rank_quality | 1.0 | **1.0** | 0 | ≥ 0.9 |
| synonym_coverage | 0.0 | **1.0** | +100% | — |

**結論：** 同義詞擴展有效（+9.27pp），但距 ≥85% 仍差 5.33pp。
**下一步：** 擴充 synonym_dict 覆蓋率（見 `plans/active/phase2-learning-query.md` E2-2）。

---

## 測試統計

| Phase | 新增 tests | 累積 |
|-------|-----------|------|
| 起始 | 141 | 141 |
| Phase A | +21 | 162 |
| Phase B | +13 | 175 |（含 Phase B 前置修復的 API tests）
| Phase C | +8 | 206 |
| Phase D | 0（eval，非 pytest）| 206 |
| **最終** | **+65** | **206** |

所有測試通過率：206/206 ✅

---

## 修復的 HIGH 問題（Python Reviewer 審查後）

| 問題 | 位置 | 修復方式 |
|------|------|---------|
| 寫入失敗後仍更新 registry | `record_artifact()` | 加入 `raise` |
| in-place mutate registry entry | `label_version()` | 改用 `{**entry, "label": ...}` immutable pattern |
| self-import anti-pattern | `learning_store._learnings_path()` | 直接引用 `_LEARNINGS_PATH` |
| global mutable cache race condition | `synonym_dict._get_synonyms()` | 改用 `@functools.lru_cache(maxsize=1)` |
| `logging.basicConfig` 在 module 層級 | `scripts/enrich_qa.py` | 移入 `__main__` 區塊 |
