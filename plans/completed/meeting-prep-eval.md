# Meeting-Prep Eval — 評估基礎設施建設計畫

> Status: ✅ 完成（2026-03-12）
> Created: 2026-03-12

## 驗證結果

- **Phase 0（回測生成）**：4 份 golden reports 全部生成完成（2/20, 2/27, 3/6, 3/9）
- **Phase 1（Structure Eval）**：11 evaluators × 4 cases，全部 1.0 通過
- **Phase 2（Grounding Eval）**：5 evaluators × 4 cases 通過（citation_id_resolution 1.0, inline_citation_coverage 0.895 > 0.55 threshold）
- **Phase 3（CI + Makefile）**：eval.yml +2 steps, Makefile +3 targets, eval_thresholds.json +2 groups
- **Phase 4（Content Quality Command）**：`/evaluate-meeting-prep-quality` command 建立完成
- **Code Review 修正**：`_cached_executor` error cache 跳過、KB 空值 graceful skip
- **偏差**：`question_total_range` golden dataset 欄位未被 evaluator 使用（dead field），列為 tech debt

## Context

`/meeting-prep` 是專案中唯一沒有任何 eval 覆蓋的主要功能。現有 11 個 eval groups 覆蓋了 retrieval、extraction、dedup、chat、crawled-not-indexed 等，但 meeting-prep 的 11-section 深度報告完全沒有品質保障機制。

**核心挑戰**：其他 eval 都是「呼叫 API → 比對輸出」，但 meeting-prep 是 Claude Code command，無法自動觸發生成。Eval 必須作用在**已生成的報告檔案**上（靜態分析），而非即時生成。

---

## 目前結構問題分析

### CRITICAL

**P1: Executor 架構斷層**
- 所有現有 eval（retrieval、chat、crawled-not-indexed）都呼叫 API endpoint 作為 executor
- Meeting-prep 沒有生成 API——它是 Claude Code command
- Eval 必須是 **file reader executor**（讀取 `output/meeting_prep_*.md`），這是全新的 executor 模式
- 影響：golden dataset 格式需重新設計（不能指定 input → expected output，只能指定 expected structural properties）

### HIGH

**P2: E-E-A-T 分數解析假陽性**
- 報告中有 `**E-E-A-T 平均分：2.75/5**` 這種自由文字
- Naive regex `\d+/5` 會從 `2.75/5` 中誤擷取 `75`
- 正確做法：只從 Markdown table rows 解析 `| Experience | 3/5 |` 格式
- 同時 `<!-- meeting_prep_meta -->` JSON 中有結構化分數，應以此為 ground truth

**P3: Citation 完整性系統缺陷**
- 現有報告 19 筆 citations 的 `chunk_url` 全為 `""`、`source_url` 全為 `null`
- 這是 KB 本身的限制（Notion 來源的 QA 缺少 URL），非報告問題
- 但 eval 必須明確標註此 known limitation，不檢查這兩個欄位
- Citation ID 驗證（`stable_id` 是否存在於 KB）才是可靠的 grounding check

**P4: Inline citation 覆蓋率不足**
- 19 筆 citations 中只有約 11 筆在報告正文被 `[N]` 引用
- 覆蓋率 ~58%，意味著 8 筆引用只出現在 citations block 但從未在正文使用
- 這是真實的品質缺口——要嘛移除未使用的 citation，要嘛在正文中引用

### MEDIUM

**P5: Alert count 與 S1 table rows 不一致**
- `meta.alert_down_count = 24`，但 S1 分成 3 個子表格（嚴重異常 6 + 資料斷層 10 + 月趨勢 ~8）
- 跨子表格加總接近 24，但 eval 若只數單一表格會產生 false failure
- Eval 必須理解 S1 的多表格結構

**P6: 提問來源標注寬鬆**
- Spec 規定 B 類提問來源為 S7，但實際報告中 B4 來源為 S6、B5 來源為 S1
- Command 允許 cross-section sourcing，eval 不應限制為單一 section

**P7: LLM 輸出非確定性**
- 相同 snapshot 在不同時間執行會產生不同的業界動態（WebFetch live data）、不同假設措辭、不同提問數量
- Golden dataset 不能用 text-match——所有 evaluator 必須是 structural 或 semantic

**P8: S4 交叉比對完整性**
- Spec 要求比對 4 個來源（KB/顧問/指標/業界），但無機制驗證每列是否真的有 4 個來源的實質內容
- 可能出現「佔位但無實質分析」的情況

### LOW

**P9: 業界資料時效性**
- Eval 作用在已生成檔案上，無法驗證 S2 資料的「即時性」
- 但可驗證 S2 至少有 3 個具名外部來源（表示 fetch 成功）

---

## Laminar 整合架構

### 現有 Eval 系統（必須對齊）

```python
# 所有現有 eval 的核心模式（eval_retrieval.py, eval_crawled_not_indexed.py）
from lmnr import evaluate

evaluate(
    data=_dataset,           # golden dataset → [{data: {...}, target: {...}}]
    executor=executor,       # 呼叫 API 或處理資料 → dict
    evaluators={...},        # metric_name → fn(output, target) → float
    group_name="...",        # Laminar Dashboard group name
)
```

**CI 整合點**：
- `eval/eval_thresholds.json` — threshold gate（`_run_threshold_gate()` + `sys.exit(1)`）
- `.github/workflows/eval.yml` — `lmnr eval evals/eval_*.py`
- `LMNR_PROJECT_API_KEY` — 推送結果至 Laminar Dashboard

### Meeting-Prep 的特殊挑戰

| 項目 | 現有 eval | Meeting-Prep eval |
|------|----------|------------------|
| Executor 來源 | API endpoint（`requests.post()`） | **本地 .md 檔案**（`Path.read_text()`） |
| Golden dataset | input → expected output | report_path → **expected structural properties** |
| CI 可用性 | ✅ API 可在 CI 啟動 | ⚠️ `output/` 在 `.gitignore`，CI 無報告檔案 |
| 資料來源 | 即時生成 | 預先生成的靜態檔案 |

### CI 可用性解法：Golden Reports 子目錄

```
eval/
├── golden_meeting_prep.json          # golden dataset（指向 fixtures）
└── fixtures/meeting_prep/            # 新增：committed 報告副本
    ├── meeting_prep_20260306_ea576a4f.md
    ├── meeting_prep_20260220_xxxx.md  # 回測生成
    ├── meeting_prep_20260227_xxxx.md  # 回測生成
    └── meeting_prep_20260309_xxxx.md  # 回測生成
```

- Golden dataset 中 `report_path` 指向 `eval/fixtures/meeting_prep/` 而非 `output/`
- 這些是 **test fixtures**，committed to git，CI 可讀取
- 與 `eval/golden_*.json` 同層級，邏輯一致

---

## 三層 Eval 架構

```
Layer 1: Structure（rule-based，零 LLM 成本）
  ├─ 11 個 evaluator → 結構完整性 + 格式驗證
  ├─ Laminar group: "meeting_prep_structure"
  ├─ Threshold gate: eval_thresholds.json → sys.exit(1)
  ├─ CI: ✅（fixtures committed）
  └─ 對應：P2, P5, P6, P7

Layer 2: Grounding（rule-based + KB lookup）
  ├─ 5 個 evaluator → citation 完整性 + KB 一致性
  ├─ Laminar group: "meeting_prep_grounding"
  ├─ Threshold gate: eval_thresholds.json → sys.exit(1)
  ├─ CI: ✅（Supabase fallback for KB, fixtures for reports）
  └─ 對應：P3, P4, P8

Layer 3: Content Quality（Claude Code as Judge，零外部 API 成本）
  ├─ 5 個 evaluator → 假設品質 + 評分合理性 + 問題實用性
  ├─ Claude Code command: /evaluate-meeting-prep-quality
  ├─ 非 CI gate（Claude Code 命令無法在 CI 執行）
  └─ 對應：P8 深度驗證
```

### Layer 1: Structure Eval（rule-based）

| Metric | 定義 | 計分 |
|--------|------|------|
| `section_completeness` | 11 個 H2 sections 是否全部存在 | 11/11 = 1.0 |
| `metadata_valid` | `<!-- meeting_prep_meta {...} -->` 可解析；eeat 1-5, maturity L1-L4 | 1.0 / 0.0 |
| `citation_block_valid` | `<!-- citations [...] -->` 可解析 JSON array | 1.0 / 0.0 |
| `question_count_valid` | S9 四類各在 spec 範圍（A:3-5, B:4-6, C:2-3, D:2-3） | 在範圍比例 |
| `question_source_annotated` | 所有提問有 `（來源：S\d...）` 標注 | 有標注比例 |
| `eeat_score_format` | S6 table 有 4 rows，分數 1-5 整數 | 1.0 / 0.0 |
| `maturity_level_format` | S8 table 有 4 rows，等級 L1-L4 | 1.0 / 0.0 |
| `s3_hypothesis_structure` | S3 至少 3 個 ### 子 section，每個 >= 3 假設 | 合規比例 |
| `s5_all_layers_present` | S5 含 L1-L5 所有層 | 5/5 = 1.0 |
| `s7_seven_elements` | S7 有 7 個編號行 | 1.0 / 0.0 |
| `s10_checklist_present` | S10 有 >= 5 個 `- [ ]` 項目 | 1.0 / 0.0 |

### Layer 2: Grounding Eval（KB lookup）

| Metric | 定義 | 計分 |
|--------|------|------|
| `citation_id_resolution` | citation ID 在 KB 中存在的比例 | 0.0-1.0 |
| `citation_category_consistency` | citation.category == KB item.category 的比例 | 0.0-1.0 |
| `citation_count_in_range` | 總 citation 數在 10-30 範圍 | 1.0 / 0.0 |
| `s4_four_sources_populated` | S4 每列 4 個來源欄都有實質內容的比例 | 0.0-1.0 |
| `inline_citation_coverage` | 正文中被 `[N]` 引用的 citation / 總 citation 數 | 0.0-1.0 |

### Layer 3: Content Quality（LLM-as-Judge）

| Metric | 定義 |
|--------|------|
| `s3_hypothesis_grounded` | 根因假設是否引用 S1 的具體指標，而非泛泛 SEO 建議 |
| `s6_eeat_justified` | E-E-A-T 每個分數是否有具體依據而非空泛描述 |
| `s9_question_specificity` | 提問是否針對本次客戶/情境，而非通用 SEO 問題 |
| `s4_contradiction_quality` | 標記為「矛盾」的項目是否存在真正的張力 |
| `overall_coherence` | S1 異常 → S3 假設 → S9 提問的邏輯鏈是否通順 |

---

## CI Thresholds

```json
{
  "meeting_prep_structure": {
    "section_completeness": 1.0,
    "metadata_valid": 1.0,
    "citation_block_valid": 1.0,
    "question_count_valid": 1.0,
    "question_source_annotated": 0.9,
    "eeat_score_format": 1.0,
    "maturity_level_format": 1.0,
    "s3_hypothesis_structure": 0.8,
    "s5_all_layers_present": 1.0,
    "s7_seven_elements": 1.0,
    "s10_checklist_present": 1.0
  },
  "meeting_prep_grounding": {
    "citation_id_resolution": 0.9,
    "citation_category_consistency": 0.8,
    "citation_count_in_range": 1.0,
    "s4_four_sources_populated": 0.8,
    "inline_citation_coverage": 0.55
  }
}
```

> `inline_citation_coverage` 設為 0.55（現有報告 ~0.58），因部分 citation 可能僅作為參考背景存在。

---

## Golden Dataset 設計

### 格式

```json
[
  {
    "id": "meeting_prep_20260306_ea576a4f",
    "description": "基線：24 ALERT_DOWN（含 10 資料斷層），19 citations，15 提問",
    "report_path": "output/meeting_prep_20260306_ea576a4f.md",
    "snapshot_id": "20260306-184745",
    "expected_structure": {
      "section_count": 11,
      "citation_count_range": [10, 30],
      "question_total_range": [11, 17],
      "question_by_type": {"A": [3,5], "B": [4,6], "C": [2,3], "D": [2,3]},
      "s3_anomaly_subsections_min": 3,
      "s5_layer_count": 5,
      "s7_element_count": 7,
      "s10_checklist_min": 5
    },
    "expected_grounding": {
      "citation_id_resolution_min": 0.9,
      "citation_category_consistency_min": 0.8,
      "s4_row_count_min": 3
    },
    "notes": "首次生成的基線報告，S1 含 3 個子表格（嚴重異常 + 資料斷層 + 月趨勢）"
  }
]
```

### 回測策略：用歷史週報產生 Golden Cases

兩週開一次會，現有歷史週報覆蓋 3 個不同日期週期：

| Case | 來源週報 | 日期 | 說明 |
|------|---------|------|------|
| 1 | `meeting_prep_20260306_ea576a4f.md` | 3/6 | 已存在，基線 |
| 2 | `/meeting-prep --report output/report_20260220.md` | 2/20 | 回測生成 |
| 3 | `/meeting-prep --report output/report_20260227_b47f1eb7.md` | 2/27 | 回測生成 |
| 4 | `/meeting-prep --report output/report_20260309_f4d6dcb9.md` | 3/9 | 回測生成 |

**實作時自動回測**：在 Phase 0 執行 3 次 `/meeting-prep --report`，產生 Case 2-4。一次性 token 成本約 200-300K tokens。生成後每份報告自動加入 `eval/golden_meeting_prep.json`。

> 注意：回測生成的業界動態（S2）會反映執行當天的 WebFetch 結果，而非歷史日期的真實動態。這是 known limitation，Structure/Grounding eval 不受影響，僅 Content Quality eval 需考慮。

---

## Implementation Steps

### Phase 0: 回測生成 Golden Reports（一次性）

執行 3 次 `/meeting-prep --report`，產生 Case 2-4：
```bash
/meeting-prep --report output/report_20260220.md
/meeting-prep --report output/report_20260227_b47f1eb7.md
/meeting-prep --report output/report_20260309_f4d6dcb9.md
```

生成後：
1. 複製 4 份報告至 `eval/fixtures/meeting_prep/`
2. 每份報告的實際結構值填入 `eval/golden_meeting_prep.json`

### Phase 1: Golden Dataset + Structure Eval

**Step 1**: 建立 `eval/fixtures/meeting_prep/` + `eval/golden_meeting_prep.json`
- 報告副本 committed 為 test fixtures（解決 CI `output/` gitignore 問題）
- Golden dataset `report_path` 指向 `eval/fixtures/meeting_prep/`

**Step 2**: 建立 `evals/eval_meeting_prep_structure.py`（~250 行）

```python
# 核心架構（對齊 eval_crawled_not_indexed.py + eval_retrieval.py 模式）
from lmnr import evaluate

# ── Golden dataset ──
_dataset = [
    {
        "data": {"report_path": case["report_path"]},  # executor 的輸入
        "target": case["expected_structure"],            # evaluator 的比對目標
    }
    for case in _golden_raw
]

# ── Executor（file reader，非 API caller）──
def executor(data: dict) -> dict:
    """讀取 .md 檔案 → 解析結構 → 回傳 structured dict."""
    report_path = PROJECT_ROOT / data["report_path"]
    content = report_path.read_text(encoding="utf-8")
    return {
        "sections": _parse_sections(content),      # H2 list
        "metadata": _parse_meta(content),           # meeting_prep_meta JSON
        "citations": _parse_citations(content),     # citations JSON array
        "questions": _parse_questions(content),     # {A: [...], B: [...], ...}
        "raw_content": content,
    }

# ── 11 個 Evaluators（fn(output, target) → float）──
def section_completeness(output, target): ...
def metadata_valid(output, target): ...
# ...（同 Layer 1 表格）

# ── Threshold gate（跟 eval_retrieval.py 完全對齊）──
def _run_threshold_gate(): ...  # sys.exit(1) on failure

# ── Laminar evaluate ──
evaluate(
    data=_dataset,
    executor=_cached_executor,
    evaluators=_EVALUATOR_MAP,
    group_name="meeting_prep_structure",  # → Laminar Dashboard
)
```

- CLI flags: `--report <path>`（單檔測試）、`--limit N`
- 參考 pattern: `eval_crawled_not_indexed.py`（executor 結構）+ `eval_retrieval.py`（threshold gate）

**Step 3**: 加入 `eval/eval_thresholds.json`：`meeting_prep_structure` key
```json
{
  "retrieval": { ... },
  "extraction": { ... },
  "meeting_prep_structure": {
    "section_completeness": 1.0,
    "metadata_valid": 1.0,
    ...
  }
}
```

### Phase 2: Grounding Eval

**Step 4**: 建立 `evals/eval_meeting_prep_grounding.py`（~200 行）

```python
# 核心差異：executor 讀取報告 + KB lookup
from lmnr import evaluate

def executor(data: dict) -> dict:
    """讀取報告 → 解析 citations → 查 KB 比對."""
    content = _read_report(data["report_path"])
    citations = _parse_citations(content)
    kb_items = _load_qa_items()  # 參考 eval_retrieval.py 的 local → Supabase fallback
    return {
        "citations": citations,
        "kb_lookup": _resolve_citations(citations, kb_items),
        "inline_refs": _extract_inline_refs(content),
        "s4_rows": _parse_s4_table(content),
    }

evaluate(
    data=_dataset,
    executor=_cached_executor,
    evaluators={
        "citation_id_resolution": citation_id_resolution,
        "citation_category_consistency": citation_category_consistency,
        "citation_count_in_range": citation_count_in_range,
        "s4_four_sources_populated": s4_four_sources_populated,
        "inline_citation_coverage": inline_citation_coverage,
    },
    group_name="meeting_prep_grounding",  # → Laminar Dashboard
)
```

- KB 載入: `_load_qa_items()` 複製自 `eval_retrieval.py`（local `qa_final.json` → Supabase fallback）
- **CI 可執行**：fixtures 提供報告，Supabase 提供 KB

**Step 5**: 加入 `eval/eval_thresholds.json`：`meeting_prep_grounding` key

### Phase 3: Makefile + CI

**Step 6**: Makefile 新增 targets
```makefile
evaluate-meeting-prep-structure:
	.venv/bin/python evals/eval_meeting_prep_structure.py

evaluate-meeting-prep-grounding:
	.venv/bin/python evals/eval_meeting_prep_grounding.py

evaluate-meeting-prep: evaluate-meeting-prep-structure evaluate-meeting-prep-grounding
```

**Step 7**: `.github/workflows/eval.yml` 新增 steps
```yaml
- name: Run meeting-prep structure eval
  env:
    LMNR_PROJECT_API_KEY: ${{ secrets.LMNR_PROJECT_API_KEY }}
  run: lmnr eval evals/eval_meeting_prep_structure.py

- name: Run meeting-prep grounding eval
  env:
    LMNR_PROJECT_API_KEY: ${{ secrets.LMNR_PROJECT_API_KEY }}
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
  run: lmnr eval evals/eval_meeting_prep_grounding.py
```

> 兩個 eval 都不需要 API server、不需要 OpenAI — 純 file read + KB lookup
> 與現有 retrieval / extraction eval 並行執行

### Phase 4: Content Quality（Claude Code as Judge）

**Step 8**: 建立 Claude Code 命令 `/evaluate-meeting-prep-quality`
- 模式：跟 `/evaluate-qa-local`、`/evaluate-faithfulness-local` 相同
- **Claude Code 本身就是 Judge**——直接讀報告、推理品質，不呼叫外部 API
- 5 個評分維度：
  - `s3_hypothesis_grounded`：根因假設是否引用 S1 具體指標
  - `s6_eeat_justified`：E-E-A-T 每個分數是否有具體依據
  - `s9_question_specificity`：提問是否針對本次情境
  - `s4_contradiction_quality`：矛盾項目是否有真正張力
  - `overall_coherence`：S1 → S3 → S9 邏輯鏈通順度
- 輸出：每個維度 1-5 分 + 評語
- 結果寫入 `output/eval_meeting_prep_quality_YYYYMMDD.json`
- 非 CI gate（Claude Code 命令無法在 CI 執行）
- Makefile: 無（Claude Code 命令，直接 `/evaluate-meeting-prep-quality` 執行）

> **為何不用 Python + Anthropic API？**
> 本專案「Claude Code as LLM」原則：所有 LLM 推理由 Claude Code 直接處理，零外部 API 成本。
> Layer 1/2 是 rule-based（Python + Laminar），不需要 LLM。
> Layer 3 需要語意判斷，由 Claude Code 直接執行。

---

## 驗證

對現有報告執行 Layer 1，預期結果：

| Metric | 預期值 | 根據 |
|--------|--------|------|
| section_completeness | 1.0 | 11/11 H2 已確認 |
| metadata_valid | 1.0 | JSON 可解析，分數格式正確 |
| citation_block_valid | 1.0 | 19 筆 JSON array |
| question_count_valid | 1.0 | A:4 B:5 C:3 D:3 均在範圍 |
| question_source_annotated | 1.0 | 15/15 有標注 |
| eeat_score_format | 1.0 | 4 rows × 1-5 分 |
| maturity_level_format | 1.0 | 4 rows × L1-L4 |
| s3_hypothesis_structure | 1.0 | 5 子 section × 3 假設 |
| s5_all_layers_present | 1.0 | L1-L5 |
| s7_seven_elements | 1.0 | 7 行 |
| s10_checklist_present | 1.0 | 11 items |

Layer 2 預期：
- `citation_id_resolution`: 1.0（19/19 存在）
- `citation_category_consistency`: ~1.0
- `inline_citation_coverage`: **~0.58**（可能低於理想，但高於 0.55 threshold）

---

## 關鍵檔案

| 動作 | 路徑 | 說明 |
|------|------|------|
| 新增 | `eval/golden_meeting_prep.json` | Golden dataset |
| 新增 | `eval/fixtures/meeting_prep/*.md` | Golden report fixtures（committed，CI 可讀） |
| 新增 | `evals/eval_meeting_prep_structure.py` | Layer 1: Structure eval + Laminar `evaluate()` |
| 新增 | `evals/eval_meeting_prep_grounding.py` | Layer 2: Grounding eval + Laminar `evaluate()` |
| 新增（後續） | `evals/eval_meeting_prep_quality.py` | Layer 3: LLM-as-Judge + Laminar `evaluate()` |
| 修改 | `eval/eval_thresholds.json` | +2 threshold groups（`meeting_prep_structure` + `meeting_prep_grounding`） |
| 修改 | `.github/workflows/eval.yml` | +2 eval steps（structure + grounding） |
| 修改 | `Makefile` | +3 eval targets |
| 參考 | `evals/eval_crawled_not_indexed.py` | Executor 結構 pattern（file-based） |
| 參考 | `evals/eval_retrieval.py` | Threshold gate + KB fallback + Laminar 整合 pattern |
| 來源 | `output/meeting_prep_20260306_ea576a4f.md` | 基線報告（複製為 fixture） |

## Eval 整合總覽

| Group / Command | Layer | 系統 | Evaluator 數 | CI Gate |
|-----------------|-------|------|-------------|---------|
| `meeting_prep_structure` | L1 | Laminar `evaluate()` | 11 | ✅ threshold gate |
| `meeting_prep_grounding` | L2 | Laminar `evaluate()` | 5 | ✅ threshold gate |
| `/evaluate-meeting-prep-quality` | L3 | Claude Code command | 5 | ❌ 本地互動 |

> Laminar groups：現有 11 個 + 新增 2 個 = **13 個**
> Claude Code eval commands：現有 5 個 + 新增 1 個 = **6 個**

## Known Limitations

1. **`chunk_url`/`source_url` 永遠為空**：KB 限制，eval 不檢查這兩欄
2. **Layer 3 judge 非確定性**：建議每次跑 3 輪取平均
3. **Fixtures 同步問題**：`/meeting-prep` command 改動報告格式時，需同步更新 fixtures + golden dataset
4. **回測報告的 S2 時效性**：回測生成的業界動態反映執行當天，非歷史日期。Structure/Grounding eval 不受影響
