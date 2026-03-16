# AI Provider 輸出品質比較 — 方法論與歷史結果

本文記錄「同一份 SEO 數據輸入給不同 AI provider，產出洞察品質比較」的基礎設施、
跑分方式與歷次結果。

---

## 目的

驗證 seo-knowledge-insight 系統相對於通用 LLM（ChatGPT / Claude / Gemini）的差異：

- 是否更接地（grounding）於原始數據？
- 建議是否更可執行（actionability）？
- 分析是否更聚焦（relevance）於 SEO 診斷？

---

## 檔案架構

```
eval/
  golden_seo_analysis.json        # 基準 case 定義（required_topics + topic_aliases + evaluation_criteria）

output/
  provider_<name>_<YYYYMMDD>.md   # 各 provider 原始輸出（手動貼入或程式生成）
  metrics_<YYYYMMDD>.tsv          # 當週原始 SEO 指標（複製自 Google Sheet）
  comparison_report_<YYYYMMDD>.md # 自動生成的比較報告（含分數+評語）

scripts/
  compare_providers.py            # 比較腳本（LLM-as-Judge + 主題覆蓋率）
  04_generate_report.py           # 系統自身報告生成（輸入 .tsv，輸出 .md）
```

---

## Provider 命名規則

`output/provider_<label>_<YYYYMMDD>.md`

| 檔案名                                 | Provider                     |
| -------------------------------------- | ---------------------------- |
| `provider_chatgpt_gpt52_<date>.md`     | ChatGPT GPT-5.2              |
| `provider_claude_sonnet46_<date>.md`   | Claude Sonnet 4.6            |
| `provider_gemini_research_<date>.md`   | Gemini 2.0 深入研究          |
| `provider_gemini_thinking_<date>.md`   | Gemini 2.0 思考型            |
| `provider_system_seoinsight_<date>.md` | 本系統 seo-knowledge-insight |

---

## 如何執行一次新的比較

### Step 1 — 準備 provider 輸出檔

每份 provider 輸出存為 `output/provider_<name>_<YYYYMMDD>.md`。

系統自身報告由腳本生成：

```bash
# 先將試算表數據存成 TSV
# 執行系統報告（--no-qa 可跳過知識庫，加快速度）
.venv/bin/python scripts/04_generate_report.py \
  --input output/metrics_<YYYYMMDD>.tsv \
  --output output/provider_system_seoinsight_<YYYYMMDD>.md
```

### Step 2 — 執行比較

```bash
# 自動掃描 output/provider_*.md，輸出 output/comparison_report_<date>.md
.venv/bin/python scripts/compare_providers.py

# 指定特定日期的檔案
.venv/bin/python scripts/compare_providers.py \
  --files output/provider_chatgpt_gpt52_20260228.md \
          output/provider_system_seoinsight_20260228.md

# 指定不同 judge model
.venv/bin/python scripts/compare_providers.py --judge-model gpt-4o
```

### Step 3 — 查看結果

- 終端機即時列印排名總覽
- 完整報告（含評語）儲存於 `output/comparison_report_<date>.md`
- Laminar 追蹤：所有 LLM judge 呼叫自動記錄到 Laminar（需設定 `LMNR_PROJECT_API_KEY`）

---

## Golden Case 格式（`eval/golden_seo_analysis.json`）

```jsonc
[
  {
    "id": "seo_metrics_analysis_20260228",
    "description": "...",
    "data_snapshot": "2026-02-28 週：曝光 63,673,783 ...",
    "required_topics": ["CTR", "檢索未索引", "回應時間", "Discover", "建議"],
    "topic_aliases": {
      "CTR": ["點擊率", "CTR"],
      "回應時間": ["回應時間", "TTFB", "伺服器回應"],
      "Discover": ["Discover", "探索"],
      "建議": ["建議", "行動", "優先"],
    },
    "evaluation_criteria": {
      "grounding": "分析中的數字/趨勢是否忠實呈現原始資料（不捏造）",
      "actionability": "建議是否具體可執行（有明確行動步驟）",
      "relevance": "分析是否緊扣 SEO 診斷主題，未偏題",
    },
  },
]
```

### 注意事項

- `required_topics` 命中任一 `topic_aliases` 中的字串即算覆蓋（case-insensitive）
- `data_snapshot` 作為 LLM judge 的接地參照，應包含關鍵數字（讓 judge 可驗算）
- `comparison_report_*.md` 不符合 `provider_*.md` glob，不會被誤判為 provider

---

## 評估維度說明（LLM-as-Judge，gpt-5-mini）

| 維度              | 說明                   | 1分           | 5分                      |
| ----------------- | ---------------------- | ------------- | ------------------------ |
| **Grounding**     | 數字是否忠實於原始資料 | 捏造/誇大數字 | 所有數字可在數據中找到   |
| **Actionability** | 建議是否具體可執行     | 空泛方向      | 有明確行動步驟與查詢範本 |
| **Relevance**     | 分析是否聚焦 SEO 診斷  | 大量偏題      | 完全聚焦，沒有不必要填充 |

### 已知限制

1. **Judge 偏差**：gpt-5-mini 評分本身有偏差，建議長期趨勢觀察而非單次絕對值
2. **推理模型 + response_format 問題**：`json_schema`/`json_object` 格式會讓推理模型回傳空 content（reasoning tokens 耗盡）。腳本已改為不限格式 + retry 修正
3. **內容截斷**：judge 只看前 5000 字，超長文件（如 Gemini deep research 2 萬字）會被截斷
4. **主題覆蓋 vs 品質**：覆蓋率 100% 不等於高分（如 chatgpt 主題全覆蓋但 grounding 3）

---

## 歷次跑分記錄

### 2026-02-28 — 首次 5 provider 比較

**數據快照**：曝光 63,673,783（週 +31.8%）、點擊 1,397,190（週 +20.3%）、CTR 2.19%（月 -10.9%）、
檢索未索引 394,406（月 +36.2%）、週平均回應時間 948ms（週 +72.7%）、GA 工作階段月 -16%

**Judge**：gpt-5-mini

| Provider          | 字元數 | 主題覆蓋 | Grounding | Actionability | Relevance | **平均** |
| ----------------- | ------ | -------- | --------- | ------------- | --------- | -------- |
| system_seoinsight | 5,011  | 80%      | **5**     | **5**         | **5**     | **5.0**  |
| chatgpt_gpt52     | 2,582  | 100%     | 3         | 4             | 5         | 4.0      |
| gemini_thinking   | 1,787  | 80%      | 3         | 4             | 5         | 4.0      |
| claude_sonnet46   | 1,225  | 60%      | 1         | 3             | 5         | 3.0      |
| gemini_research   | 19,896 | 80%      | 1         | 3             | 3         | 2.33     |

**主要觀察**：

- **system_seoinsight 最佳**（5.0/5）：以「推論」標記假設，未捏造數字；每個建議附帶具體操作步驟；完全聚焦 SEO 診斷。缺點：漏掉「回應時間」主題（系統的知識庫對此指標的 Q&A 較少）
- **ChatGPT / Gemini thinking 並列第二**（4.0）：主題覆蓋更廣，但 grounding 3 分 — 引用了原始快照未明確提供的月比值與細項趨勢
- **Claude Sonnet 4.6 第四**（3.0）：只拿到 3/5 required topics；大量引用快照外的細項數字（AI 導流細項、各管道月比、2/14 失敗數目），捏造情況嚴重（grounding 1）
- **Gemini 深入研究最低**（2.33）：文章最長（2 萬字）但 relevance 3 — 有大量台灣股市/AI 平台市佔等偏題內容；grounding 1 — 引用大量無法從快照驗算的「研究數字」

**Laminar trace**：已記錄（judge 呼叫 × 5）

---

## 如何新增下一期比較

1. 蒐集各 provider 在新一週數據下的輸出，存入 `output/provider_*_<新日期>.md`
2. 準備 `output/metrics_<新日期>.tsv`，執行 `04_generate_report.py` 生成本系統輸出
3. 若測試場景不同（新數據、新指標重點），在 `eval/golden_seo_analysis.json` 新增一個 case
4. 執行 `scripts/compare_providers.py`
5. 將新結果補充到本文「歷次跑分記錄」section
