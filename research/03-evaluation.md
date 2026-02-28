# 評估系統

> 屬於 [research/](./README.md)。涵蓋 LLM-as-Judge、Reasoning Model、評估維度、Judge 設計原則。

---

## 10. LLM-as-Judge：用 AI 評估 AI

### 概念

傳統方法：人工看 30 筆 Q&A 打分數（慢、貴、主觀）。
LLM-as-Judge：讓另一個 AI 當評審，自動評分（快、便宜、可重複）。

```
[待評估的 Q&A]
Q: Discover 流量下降的原因？
A: 可能是內容品質或 AMP 問題，建議觀察 GSC...

   ↓ 送給 gpt-5.2（評審）

[評分結果]
{
  "relevance": {"score": 5, "reason": "精準捕捉核心 SEO 知識"},
  "completeness": {"score": 3, "reason": "缺少具體行動建議"},
  "accuracy": {"score": 4, "reason": "論述合理"},
  "granularity": {"score": 5, "reason": "問題聚焦單一主題"}
}
```

### 本專案四個評估維度

| 維度         | 問的問題                        | 目前分數      |
| ------------ | ------------------------------- | ------------- |
| Relevance    | 是否有價值的 SEO 知識（非閒聊） | 4.65 ✅       |
| Accuracy     | 內容是否合理無虛構              | 3.80          |
| Completeness | 是否包含建議 + 原因 + 案例      | 3.70 ← 待改善 |
| Granularity  | 一個 Q 只問一個主題             | 4.65 ✅       |

### 注意：Judge 本身也可能出錯

今天（2026-02-27）修的兩個 bug 就是 Judge 失效：

- BUG-001：分類 Judge 大量回傳空結果 → 正確率假的 10%，真實 75%
- BUG-002：Retrieval Judge token 不夠 → Precision 假的 10%，真實 100%

**原則**：看到評估結果異常（< 20% 或 > 98%），先懷疑是評估系統本身的問題。

---

## 11. Reasoning Model：會先思考的 AI

### 兩種模型的差異

```
標準模型（如 gpt-3.5, gpt-4）：
  輸入 → 直接輸出

推理模型（如 o1, o3-mini, gpt-5-mini, gpt-5.2）：
  輸入 → [內部思考過程] → 輸出
```

推理模型在回答前會先做「chain of thought」（思維鏈），
能處理更複雜的推理問題，但使用上有兩個陷阱。

### 陷阱一：`max_completion_tokens` 要給更多

```python
# max_completion_tokens 由「思考 + 輸出」共用

# 標準模型：
# 256 tokens 全給輸出 → 夠了

# 推理模型：
# 256 tokens：200 tokens 用於思考，只剩 56 給輸出
# → finish_reason: "length"（被截斷）
# → content = ""（空字串）

# 本專案 BUG-002 的根因，修復：
max_completion_tokens=256   # ❌
max_completion_tokens=1024  # ✅
```

### 陷阱二：content 可能回傳空字串

```python
# 標準模型：content 永遠有值
# 推理模型：token 超限時，content = ""

# 錯誤寫法（本專案修復前）：
content = response.choices[0].message.content or "{}"
# "" or "{}"  →  "{}"  →  json.loads("{}")  →  {}  →  靜默失敗

# 正確寫法（修復後）：
content = response.choices[0].message.content
if not content:
    print("⚠️ 推理模型回傳空內容，可能 token 不足")
    return fallback

# 或者，append 前先驗證必要欄位存在：
if "category_judgment" not in result:
    continue   # 不計入統計
```

### 診斷方法

```python
# 確認是否被截斷
print(response.choices[0].finish_reason)
# "stop"   → 正常完成
# "length" → token 超限，輸出不完整
```

---

---

## 14. 評估維度詳解與基準線

### 四個評估維度說明

| 維度             | 問的核心問題                       | 評分標準（1-5）                                |
| ---------------- | ---------------------------------- | ---------------------------------------------- |
| **Relevance**    | 這是真正有價值的 SEO 知識嗎？      | 1=完全無關閒聊；5=高濃度可複用知識             |
| **Accuracy**     | A 是否忠實反映原始會議內容？       | 1=明顯錯誤或虛構；5=完全符合來源               |
| **Completeness** | A 是否有足夠深度讓讀者理解並行動？ | 1=只有結論無原因；5=What+Why+How+Evidence 齊全 |
| **Granularity**  | Q 的聚焦程度是否恰當？             | 1=問題過於廣泛；5=聚焦單一具體主題             |

### 評估分數要求的完整行動建議

| 維度             | 目標分數  | 最新數值 | 狀態         | 提升方法                              |
| ---------------- | --------- | -------- | ------------ | ------------------------------------- |
| Relevance        | ≥ 4.5     | 4.80     | ✅           | 無需調整                              |
| Accuracy         | ≥ 4.0     | 3.95     | 接近目標     | 加入 faithfulness 檢查                |
| **Completeness** | **≥ 4.0** | **3.85** | **↑ 改善中** | `[補充]` Tag 機制已實作（見第 13 節） |
| Granularity      | ≥ 4.5     | 4.75     | ✅           | 無需調整                              |

### 額外評估指標說明

- **Confidence 校準**：Q&A 的 `confidence` 值應與實際品質相關（高 confidence → 高 Accuracy）
- **Self-contained**：Q 不依賴原始會議就能理解（目前 Granularity 4.65 說明已做好）
- **Actionable**：A 提供具體可執行建議（Completeness 的核心要求）
- **Faithfulness**：A 的內容來自原始文件，不是 AI 自行補充（Accuracy 的核心要求）

---

---

## 19. LLM-as-Judge 設計原則

### Judge Prompt 最佳實踐

**Chain-of-Thought（CoT）**：先給理由，再給分數：

```python
JUDGE_PROMPT = """
評估以下 Q&A 的 Completeness（完整性），1-5分。

請先給出你的分析，再給出分數：
<analysis>
[先分析 Answer 包含了哪些要素，缺少哪些要素]
</analysis>
<score>
{"completeness": {"score": X, "reason": "一句話原因"}}
</score>
"""
```

**為什麼 CoT 重要**：強制 LLM 先思考再評分，減少直覺偏差，分數更穩定。

### 常見 Judge 偏差與避免方法

| 偏差類型 | 現象                             | 避免方法                       |
| -------- | -------------------------------- | ------------------------------ |
| 冗長偏差 | 長答案自動得高分                 | 強調「精準簡潔也可以得 5 分」  |
| 位置偏差 | 第一個選項偏高                   | 固定評分順序，不做對比評估     |
| 自我偏好 | 用 GPT-5.2 評 GPT-5.2 生成的內容 | 可接受，但需注意過度膨脹的分數 |

### 本專案 Judge 模型維持 gpt-5.2

**理由**：

- 研究顯示 gpt-5.2 在評分一致性上表現良好
- 換成 Claude Opus 會增加跨平台複雜度
- 開源 Judge 模型（Prometheus-7B）需要自建推理環境

**改善方向**：不換模型，而是改善 Judge prompt（加入 CoT、反向偏差提示）。

---

## 20. Pipeline 全步驟 Eval 覆蓋（Per-step Golden Sets）

> 對應 `scripts/05_evaluate.py` 的 4 個新函式（v1.5 加入）。

### 設計原則

每個 pipeline 步驟都有**不同的評估指標**，必須分別設計 golden set：

| 步驟              | 函式                               | Golden Set                                                | 核心指標                                                    |
| ----------------- | ---------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------- |
| Step 2 萃取       | `evaluate_extraction()`            | `eval/golden_extraction.json`（5 cases）                  | count_accuracy, keyword_coverage_rate, hallucination_rate   |
| Step 3 去重       | `evaluate_dedup()`                 | `eval/golden_dedup.json`（40 pairs：20 dup + 20 non-dup） | precision, recall, F1                                       |
| Step 3 閾值最佳化 | `evaluate_dedup_threshold_sweep()` | 同上 golden pairs                                         | optimal_threshold（F1-optimal sweep 0.80–0.95）             |
| Step 4 週報       | `evaluate_report_quality()`        | `eval/golden_report.json`（5 cases）                      | topic_coverage, kw_grounding, llm_actionability             |
| Step 5 Q&A 品質   | `evaluate_qa_quality()`            | `eval/golden_qa.json`（50 items，10 categories）          | Relevance/Accuracy/Completeness/Granularity（LLM-as-Judge） |

### Step 2 萃取評估：`evaluate_extraction()`

```python
result = evaluate_extraction(golden_cases, per_meeting_dir="output/qa_per_meeting")
# {
#   "count_accuracy": 0.80,         # 萃出數量與 golden 期望的 ± tolerance 內佔比
#   "avg_keyword_coverage_rate": 0.73,  # golden 關鍵字實際出現在萃出結果的比例
#   "avg_hallucination_rate": 0.05,     # 萃出內容無法對應到原始文字的估計比例
# }
```

- **count_accuracy**：`abs(actual_count - expected_count) <= tolerance`（default tolerance=2）
- **keyword_coverage_rate**：golden `expected_keywords` 中有多少出現在萃出結果的 Q+A+keywords 合集
- **hallucination_rate**：需 LLM-as-Judge 二次確認（未來擴充）

### Step 3 去重評估：`evaluate_dedup()` + threshold sweep

```python
# 單一閾值評估
result = evaluate_dedup(golden_pairs, threshold=0.88)
# {"precision": 0.90, "recall": 0.85, "f1": 0.875, "tp": 17, "fp": 2, "fn": 3, "tn": 18}

# F1-optimal sweep（16 步，0.80–0.95）
sweep = evaluate_dedup_threshold_sweep(golden_pairs)
# {
#   "optimal_threshold": 0.86,
#   "optimal_f1": 0.91,
#   "current_threshold": 0.88,  ← config.SIMILARITY_THRESHOLD
#   "current_f1": 0.875,
#   "recommendation": "降低至 0.86 可提升 F1 +0.035",
#   "sweep": [{"threshold": 0.80, "f1": 0.82}, ...]  # 16 entries
# }
```

**Threshold Sweep 原則**：

1. 先建立 labeled golden pairs（人工標記是否為重複）
2. 一次性計算所有 pairs 的 cosine similarity（避免 N×API 呼叫）
3. sweep 只改門檻值，不重複呼叫 API
4. F1-optimal 取 precision/recall 平衡點（不偏向任一側）

### Step 4 週報評估：`evaluate_report_quality()`

```python
result = evaluate_report_quality(golden_cases, reports_dir="output")
# {
#   "avg_topic_coverage": 0.78,        # required_topics 實際出現在報告的比例
#   "avg_kw_grounding": 0.83,          # source_qa_keywords 有多少出現在報告（接地氣）
#   "avg_llm_grounding": 4.2,          # LLM-as-Judge 評分（1-5），每週報用 2–3 個問題
#   "avg_llm_actionability": 3.9,      # 報告是否提供具體可行建議（1-5）
# }
```

### CLI 整合

```bash
# 個別執行
python scripts/run_pipeline.py --step 5 --eval-extraction
python scripts/run_pipeline.py --step 5 --eval-dedup
python scripts/run_pipeline.py --step 5 --dedup-threshold-sweep
python scripts/run_pipeline.py --step 5 --eval-report

# 完整評估（預設 LLM-as-Judge）
python scripts/run_pipeline.py --step 5 --sample 50 --with-source
```

### Golden Set 設計要點

- **萃取 golden**：每 case 包含 `meeting_id`、`expected_count`（±2）、`expected_keywords`、`notes`
- **去重 golden**：40 pairs；20 dup（high sim）+ 20 non-dup（模糊相似但語意不同）；手工標記 `is_duplicate: bool`
- **Q&A golden**：50 items；10 categories 各 ≥3 條；包含 `expected_category`、`expected_difficulty`、`expected_evergreen`
- **週報 golden**：5 scenarios；含 `required_topics[]`、`optional_topics[]`、`source_qa_keywords[]`、`min_grounding_score`

### 樣本數不足的統計風險

目前 extraction（5 筆）和 report（5 筆）golden set 樣本數偏小（建議 ≥20 筆達統計顯著性，參考「樣本數 n≥30 原則」）。

**影響**：

- 5 筆樣本只能檢測巨幅品質變化（±20%），無法發現細微回歸（±5%）
- 95% 信心區間寬度 ≈ ±35%，決策的確信度有限

**未來擴充建議**：每個場景增加至 ≥20 筆，共 100+ golden cases。

### Self-Consistency 採樣減少隨機性

**Wang et al.（2023, ICLR）** 提出的自洽推理方法：對同一問題採樣多次，取多數意見（majority vote），比單次採樣更穩定。

**本專案建議應用場景**：

- Accuracy 維度：目前單次評估，建議 3 次採樣後取中位數，減少 Judge 隨機波動
- 成本估算：700 筆 Q&A × 3 倍採樣 × `gpt-5-mini` $0.10/1M tokens ≈ 額外 $0.03

---

## 五大 AI Provider 比較評估

> 參考：`scripts/compare_providers.py`、`research/09-provider-comparison.md`、`eval/golden_seo_analysis.json`

### 實驗設計

**任務**：給定相同 SEO GSC 資料（impressions/clicks/CTR/position 表），五個 Provider 各自生成分析報告，Judge 模型（gpt-5.2）對每份報告的 grounding、actionability、relevance 三個維度進行 1–5 分打分。

**五個 Provider**：
| Provider | 描述 |
|---|---|
| `system_seoinsight` | 本專案 `04_generate_report.py` 生成的結構化報告 |
| `chatgpt` | ChatGPT 手動操作輸出 |
| `gemini_thinking` | Google Gemini 思考模式 |
| `claude` | Anthropic Claude 直接輸出 |
| `gemini_research` | Google Gemini Deep Research 模式 |

### 結果

| Provider          | Grounding | Actionability | Relevance | 平均     |
| ----------------- | --------- | ------------- | --------- | -------- |
| system_seoinsight | 5         | 5             | 5         | **5.00** |
| chatgpt           | 4         | 4             | 4         | **4.00** |
| gemini_thinking   | 4         | 4             | 4         | **4.00** |
| claude            | 3         | 3             | 3         | **3.00** |
| gemini_research   | 3         | 2             | 2         | **2.33** |

### 為何 system_seoinsight 5.0 滿分

1. **Grounding**：報告引用數字時加上 `(參考：...)` 格式，Judge 可以追溯每項論斷到原始資料
2. **Actionability**：每個洞察附帶具體行動建議，而非泛泛而論
3. **Relevance**：推論型結論加上 `(推論)` 標籤，讓 Judge 區分事實與推斷

### Golden Case 設計原則（來自本次實驗）

1. **提供結構化資料**：Judge 需要有數字可查核；純文字分析很難判斷 grounding
2. **輸出格式要有說明**：告訴 LLM Judge 要評估的是哪份檔案，避免格式混淆
3. **reason 欄位必填**：Judge prompt 要求 reason 非空，否則分數缺乏解釋
4. **多維度分離評分**：將 grounding / actionability / relevance 分開評估，比單一分更有診斷價值

### gpt-5-mini + `response_format` 導致空白輸出

**現象**：Judge 呼叫 `gpt-5-mini` 搭配 `json_schema` response_format，回傳 `content = ""`（空字串）。

**根因**：reasoning model（`gpt-5-mini-2025-08-07`）將大量 tokens 用於 `reasoning_tokens`，導致 `output_tokens` 耗盡，content 被截斷為空。

**修正**：

- 移除 `response_format` 參數，改用 prompt 指示輸出 JSON
- 設定 `max_completion_tokens >= 4096`（而非預設 1024）
- 加上重試邏輯（空白 → sleep 1s → retry）

詳見：`~/.claude/skills/learned/openai-reasoning-model-no-response-format.md`

---


---

## Laminar Eval 框架（2026-02-28 實作紀錄）

> 本節記錄將 SEO QA pipeline 接入 Laminar 的完整 eval 設計決策。

### 三層 Eval 架構

```
Layer 1: Tracing（@observe）
  → 每個 LLM 呼叫都建立 span，記錄 input/output/latency

Layer 2: Online Scoring（LaminarClient.evaluators.score()）
  → 在 @observe 函式內，LLM 回應後立即發送 rule-based scores
  → 不需要額外 LLM 呼叫（binary + continuous 指標）

Layer 3: Offline Evals（lmnr.evaluate()）
  → 批次評估，用 golden dataset 驗證能力品質
  → 可排程執行，結果顯示在 Laminar dashboard
```

### Online Evaluators 設計原則

**Rule-based（免費，無延遲）**：
- `answer_length`: `float(len(answer) > 50)` — 回答是否非空
- `has_sources`: `float(len(sources) > 0)` — 是否有知識庫引用
- `top_source_score`: cosine similarity 最佳命中 — 量化 retrieval 品質
- `source_count`: `min(count/5, 1.0)` — 引用數規範化

**LLM-as-Judge（有費用）**：
- 僅用於 offline eval 批次評估（不在每次 API 呼叫中執行）
- 用 `evaluate()` 的 `evaluators` 參數傳入 async judge 函式
- 適合：answer_relevance、faithfulness、coherence 等主觀維度

### Offline Eval 腳本結構（lmnr pattern）

```python
from lmnr import evaluate

data = [
    {"data": {"input": ...}, "target": {"expected": ...}},
]

def executor(data: dict) -> dict:
    return {"output": my_function(data["input"])}

def binary_evaluator(output: dict, target: dict) -> float:
    return 1.0 if condition else 0.0

def continuous_evaluator(output: dict, target: dict) -> float:
    return some_score_between_0_and_1(output, target)

evaluate(
    data=data,
    executor=executor,
    evaluators={"name_a": binary_evaluator, "name_b": continuous_evaluator},
    group_name="capability_name",   # 用於在 dashboard 追蹤趨勢
)
```

**規則**：
- 每個 eval 至少 2 個 evaluators（一個 binary，一個 continuous）
- `group_name` 統一命名格式：`{capability}_quality`
- 腳本放在 `evals/eval_{capability}.py`，可用 `lmnr eval` 批次執行

### Eval 覆蓋率表（本專案）

| Capability | Eval file | Evaluators | Golden dataset |
|------------|-----------|------------|----------------|
| Retrieval | `evals/eval_retrieval.py` | keyword_hit_rate, top1_category_match, top5_category_coverage | `eval/golden_retrieval.json` (307 筆) |
| Extraction | `evals/eval_extraction.py` | qa_count_in_range, keyword_coverage, no_admin_content, avg_confidence | `eval/golden_extraction.json` |
| Chat (E2E) | `evals/eval_chat.py` | has_answer, has_sources, answer_keyword_coverage, top_source_in_expected_category | 前 10 retrieval scenarios |

### lmnr 0.5.x SDK 已知 API 差異

官方文件使用 `Laminar.get_trace_id()`，但 lmnr 0.5.x 沒有此方法。

正確做法：

```python
span_ctx = Laminar.get_laminar_span_context()
trace_id = str(span_ctx.trace_id) if span_ctx else None   # UUID → str
span_id  = str(span_ctx.span_id)  if span_ctx else None
```

詳見 `~/.claude/skills/learned/laminar-0.5x-span-context-api.md`。
