# Plan: maturity-l4-retighten

**Status**: active
**Created**: 2026-05-07
**Issue**: [#41](https://github.com/sosreader/seo-knowledge-insight/issues/41)
**Related**: KB report `2026-05-06-seo-knowledge-insight-repo-and-pipeline-checkup.md` §17.2 / §18

---

## Why

Supabase L4 占比 13.4%（業界典型 5–10%）。MEMORY.md 中 03 月 L4=189，2026-05-07 verified L4=457。

**漂移源頭定位**：`scripts/03_dedupe_classify.py:117 _infer_maturity_relevance()` **完全沒呼叫 LLM**，純走 `utils/maturity_classifier.py` 的 keyword scoring。L4_KEYWORDS 含大量 trendy term（`ai overview` / `ai-driven` / `geo` / `aeo` / `ai 可見度`），外部 article 一觸發就 +2 分達 L4 threshold。

**證據**（§17.2）：

| 維度 | 數值 |
|------|------|
| L4 by extraction_model | gpt-5.4-nano 284 / claude-code 87 / legacy-unknown 62 / gpt-5.2 16 / mixed 7 / heuristic 1 |
| L4 by source_collection | ahrefs-blog 276 / genehong-medium 121 / growth-memo 25 / seo-meetings 20 / 其餘 < 10 |
| seo-meetings 占比 | 20/457 = 4.4%（會議內容 L4 比例正常） |
| 外部 article 占比 | 422/457 = 92.3%（過度集中） |

---

## What

實作 maturity 分類「rule + LLM gate」三層架構：

```
Layer 1 (rule scoring)  → utils/maturity_classifier.py（收緊 keyword + 提高 threshold）
Layer 2 (LLM gate)      → utils/maturity_llm_judge.py（新增；只對 L4 候選 reality-check）
Layer 3 (orchestrator)  → scripts/03_dedupe_classify.py:_infer_maturity_relevance() 串接
```

---

## Tasks

### A. 收緊 L4_KEYWORDS（`utils/maturity_classifier.py`）

從 `L4_KEYWORDS` 移除「趨勢詞」（這些是 topic，不是 maturity），新增 `TREND_TOPIC_TERMS` 容納它們：

**移除**（趨勢詞，移到 `TREND_TOPIC_TERMS`，只給 +1 輔助分）：

- `ai overview`, `ai overviews`, `aio`
- `ai search`, `生成式搜尋`
- `geo`, `generative engine optimization`
- `aeo`, `answer engine optimization`
- `llm seo`
- `ai 可見度`, `ai visibility`
- `ai 驅動`, `ai-driven`, `ai-powered`
- `品牌可見度`, `brand visibility`

**保留**（實作層級詞，繼續 +2）：

- `預測模型`, `predictive`, `forecasting`, `排名預測`, `流量預測`
- `跨通路整合`, `cross-channel`, `omnichannel`
- `歸因分析`, `attribution model`, `multi-touch`, `歸因模型`
- `competitive intelligence`, `競爭情報系統`
- `programmatic seo`, `程式化 seo`
- `knowledge graph`, `知識圖譜`
- `seo 自動化測試`, `regression testing`, `自動化測試`
- `推薦系統`, `recommendation engine`
- `情境規劃`, `scenario planning`
- `decision gates`
- `增量價值`, `incremental value`
- `citation growth`, `引用成長`, `authority building`

### B. 提高 L4 confidence threshold（`utils/maturity_classifier.py:191-194`）

**現行邏輯**：

```python
max_score = max(scores.values())
if max_score < 2:
    return None
```

L4 只要 1 個 keyword 命中就 +2 分達標 → 偽陽性高。

**新規則（雙重證據）**：

```python
# L4 雙重證據規則
if scores["L4"] >= 2:
    has_advanced = any(p.search(answer) for p in ADVANCED_PATTERNS)
    has_strategy = any(t in full_text for t in L4_STRATEGY_TERMS)
    has_long_answer = len(answer) > 500
    if not (has_advanced or has_strategy or has_long_answer):
        scores["L4"] = 0  # demote — single keyword 不足以判 L4
```

加 unit test 鎖住「`ai overview` alone（trend 詞）→ L3, not L4」。

### C. 新增 LLM gate（`utils/maturity_llm_judge.py`）

當 rule layer 判 L4 時，呼叫 `gpt-5.4-nano` 做 reality check。

**接口**：

```python
def llm_validate_l4(question: str, answer: str, keywords: list[str]) -> bool:
    """
    Returns True if answer truly meets L4 criteria
    (具體實作步驟 / 系統設計 / 預測模型 / 跨通路整合).
    Returns False if it's just a trendy-topic article without operational depth.
    """
```

**System prompt**：

```text
你是 SEO 成熟度分類的「真實性審查員」。

L4（領先期）的判定不能只看是否提到 AI / 預測 / 跨通路等趨勢詞——
這些是「主題」（topic），不是「成熟度」（maturity）。

L4 必須同時具備以下兩個條件：

  1. 實作具體性：答案中有可執行的系統設計、模型架構、自動化流程、
     跨工具整合步驟，或可量化的測試/驗證機制
  2. 領先級判斷：超出單一指標追蹤、單一工具設定、單一頁面優化的範疇，
     涉及策略/組織/系統層級的決策

純談趨勢、純列舉名詞、純解釋概念（即使概念是 AI Overview / GEO / 程式化 SEO）
不算 L4。

回傳格式：JSON {"is_l4": true|false, "reason": "<繁中 30 字內>"}
```

**User prompt template**：

```text
請審查以下 QA 是否真為 L4 等級：

[Question]
{question}

[Answer]
{answer}

[Keywords]
{keywords}

依規則回 JSON。is_l4=false 代表 rule layer 偽陽性，應降為 L3。
```

**成本控制**：

- 只對 rule layer 判 L4 的呼叫 LLM（預估 < 500 筆/次 dedupe）
- 用 `gpt-5.4-nano`（低成本）
- 走 `utils/openai_helper.py` 既有 cache（`response_cache` table），同樣的 (q, a) hash 不重複呼叫

### D. 整合 `scripts/03_dedupe_classify.py:117`

修改 `_infer_maturity_relevance()`：

```python
def _infer_maturity_relevance(qa: dict) -> str | None:
    existing = qa.get("maturity_relevance")
    if existing:
        return str(existing)
    level = classify_maturity_level(
        qa.get("keywords", []),
        qa.get("question", ""),
        qa.get("answer", ""),
    )
    # LLM gate only on L4 candidates and only when LLM available
    if level == "L4" and os.getenv("OPENAI_API_KEY"):
        from utils.maturity_llm_judge import llm_validate_l4
        if not llm_validate_l4(
            qa.get("question", ""),
            qa.get("answer", ""),
            qa.get("keywords", []),
        ):
            return "L3"  # Demoted by LLM gate
    return level
```

無 `OPENAI_API_KEY` 時 fallback 到純 rule（保持 PR #38 的 OpenAI-less 流程）。

### E. 回歸測試（`tests/test_maturity_classifier.py`）

新增固定 fixture（從現有 Supabase L4 取代表性樣本）：

- **5 筆 true-positive L4**（程式化 SEO 系統設計 / 預測模型 / 跨通路整合 / 推薦系統架構 / 自動化測試框架）→ 應維持 L4
- **5 筆 false-positive L4**（純談 AI Overview 趨勢 / 純列舉 GEO 名詞 / 純解釋 ai-driven 概念）→ 應降 L3

通過率 > 80% 視為合格。LLM gate 部分用 mock。

### F. 重跑歷史資料

完成後執行：

```bash
# Step 1: rule layer 重新分類（含 LLM gate）
python scripts/03_dedupe_classify.py --reclassify-l4-only --execute

# Step 2: 推到 Supabase
python scripts/push_qa_metadata_to_supabase.py --execute

# Step 3: 抽樣驗收
python scripts/qa_tools.py sample-by-maturity L4 --limit 20
```

---

## Out of Scope

- L1/L2/L3 閾值調整（現況分布合理，先動 L4）
- Supabase 1,085 孤兒清理（97.6% 是 dedupe lineage，保留現狀）
- ALTER TABLE 加 `is_deleted` soft-delete（跨 frontend/API/search 影響大，拒絕）
- 修改 extract-qa step 的 maturity 預判（那是 LLM 自填，不是漂移源頭）

---

## Definition of Done

- [ ] L4 占比 ≤ 10%（Supabase 重跑後抽樣驗證）
- [ ] `tests/test_maturity_classifier.py` 新增 10 筆 fixture，通過率 > 80%
- [ ] `--reclassify-l4-only` flag 加到 `scripts/03_dedupe_classify.py`
- [ ] `utils/maturity_llm_judge.py` 新檔含 `llm_validate_l4()` + 對應 unit test
- [ ] PR description 含 `Closes #41`
- [ ] MEMORY.md 更新 L4 為新值，標記重訓日期
- [ ] 抽 20 筆人工檢視 ≥ 16 筆分類合理

---

## References

- Issue: <https://github.com/sosreader/seo-knowledge-insight/issues/41>
- KB 診斷報告: `~/Documents/knowledge-base/reports/2026-05-06-seo-knowledge-insight-repo-and-pipeline-checkup.md` §17.2 / §18
- 受影響檔案:
  - `scripts/03_dedupe_classify.py:117` `_infer_maturity_relevance()`
  - `utils/maturity_classifier.py:21-46` `L4_KEYWORDS`
  - `utils/maturity_classifier.py:191-194` threshold 邏輯
  - `utils/openai_helper.py` 既有 cache 機制
- 相關 PR：#38（OpenAI-less fallback）/ #40（metadata 回填基礎）
