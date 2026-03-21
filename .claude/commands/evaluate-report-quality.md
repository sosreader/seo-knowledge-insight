# /evaluate-report-quality — SEO 週報內容品質評估（不需要 OpenAI）

**你（Claude Code）就是語意判斷引擎**——直接推理，不呼叫任何外部 LLM API。

Layer 3 Content Quality 評估：針對已生成的 SEO 週報，評估推理深度、可操作性、洞察原創性。

> CI 批次 threshold gate：`make evaluate-report-llm`（讀取本命令的 JSON 輸出）

---

## 用法

```
/evaluate-report-quality                           # 評估最新一份
/evaluate-report-quality output/report_20260321.md  # 指定檔案
```

---

## 執行步驟

### Step A：定位報告

如果使用者指定了檔案路徑，讀取該檔案。否則找 `output/report_*.md` 中最新的一份。

讀取完整報告內容。

### Step B：三維度評分（你是 Judge）

對報告的 3 個維度逐一評分（1-5 分）：

#### 1. `reasoning_depth`（推理深度）

評估報告是否有跨指標因果推理，而非僅列數字。

- **1 分**：只列數字，無解讀（「CTR 3.36%，曝光 125,000」）
- **2 分**：有基本方向判斷但無因果（「CTR 下降了，需要注意」）
- **3 分**：有跨指標比較但因果推理淺層（「CTR 下降而曝光上升，可能有問題」）
- **4 分**：有多步因果推理，連結 2-3 個指標（「CTR 下降但曝光增加，表示排名位置下移——Position 3→7 時 CTR 從 11% 驟降至 3.5%」）
- **5 分**：多步因果 + 研究佐證 + 反向驗證（引用業界數據驗證假設，考慮替代解釋）

#### 2. `actionability`（可操作性）

評估行動建議是否具體到可立即執行。

- **1 分**：「注意 X」「關注 Y」— 無操作步驟
- **2 分**：「改善 CTR」「優化標題」— 有方向但無具體步驟
- **3 分**：「檢查 CTR 下降的頁面」— 有動作但缺工具/條件/數值
- **4 分**：「在 GSC 篩選 CTR < 2% 的查詢，檢查標題」— 有工具 + 條件
- **5 分**：「在 GSC 的效能報表篩選 CTR 下降 > 20% 的查詢，逐一檢查標題是否含過時年份，加入觸發詞格式，預期 CTR 提升 15-25%」— 工具 + 條件 + 預期效果

#### 3. `insight_originality`（洞察原創性）

評估報告是否發現非顯而易見的關聯。

- **1 分**：複述數字，無任何解讀（「曝光增加 5.9%」）
- **2 分**：有基本解讀但屬常識（「曝光增加是好事」）
- **3 分**：有一定深度的解讀，但套路化（任何 SEO 報告都可能這樣寫）
- **4 分**：發現指標間非顯而易見的關聯（「Discover 衰退速度快於搜尋，佔比從 64% 降至 60.6%，需關注內容新鮮度」）
- **5 分**：發現反直覺現象 + 提出可驗證假設（「曝光增加但 CTR 下降，看似矛盾——但若是新增 long-tail 關鍵字觸發了低位排名曝光，則數據合理。驗證方式：篩選 Position > 10 的新增曝光」）

### Step C：彙整結果並儲存

將 Step B 的結果彙整為以下 JSON 結構：

```json
{
  "report_path": "output/report_XXXXXXXX.md",
  "evaluated_at": "2026-03-21T...",
  "dimensions": {
    "reasoning_depth": {"score": 4, "reason": "..."},
    "actionability": {"score": 4, "reason": "..."},
    "insight_originality": {"score": 3, "reason": "..."}
  },
  "average_score": 3.67,
  "summary": "一句話總結品質"
}
```

寫入 `output/eval_report_quality_YYYYMMDD.json`。

### Step C2：推送至 Laminar Dashboard

將 3 個維度分數推送至 Laminar group `report_quality`：

```bash
.venv/bin/python scripts/_push_laminar_score.py \
  --json-file output/eval_report_quality_YYYYMMDD.json \
  --group report_quality
```

此步驟將 JSON 中 `dimensions` 的 3 個 key-score 對推送至 Laminar。若 `LMNR_PROJECT_API_KEY` 未設定則靜默跳過。

### Step D：輸出報告

```
## SEO 週報內容品質評估（{日期}）

### 報告：{report_path}

| 維度 | 分數 | 評語 |
|------|------|------|
| 推理深度 | X/5 | ... |
| 可操作性 | X/5 | ... |
| 洞察原創性 | X/5 | ... |

**平均分：X.X/5**（3 維度）

### 改善建議
{列出 1-3 個可操作的改善項目}
```

---

## Composite V2 整合

L3 分數可與 L1 + L2 合併計算 `composite_v2`：

```
composite_v2 = L1_overall×0.20 + cross_metric×0.10 + action_specificity×0.10
             + data_evidence×0.08 + citation_integration×0.07
             + quadrant_judgment×0.05 + section_depth_var×0.05
             + reasoning_depth/5×0.15 + actionability/5×0.10
             + insight_originality/5×0.10
```

無 L3 時（auto fallback）：

```
composite_v2 = L1_overall×0.30 + cross_metric×0.15 + action_specificity×0.15
             + data_evidence×0.12 + citation_integration×0.10
             + quadrant_judgment×0.10 + section_depth_var×0.08
```

---

## 注意事項

- 非 CI gate——此命令透過 Claude Code 互動執行
- L1 + L2 為 rule-based（自動化、快速），L3 為 LLM-as-Judge（需人工觸發）
- 建議每份報告跑 1 次即可
- 若任一維度 < 2 分，建議重新生成報告
