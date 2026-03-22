# /evaluate-meeting-prep-quality — Meeting-Prep 內容品質評估（不需要 OpenAI）

**你（Claude Code）就是語意判斷引擎**——直接推理，不呼叫任何外部 LLM API。

Layer 3 Content Quality 評估：針對已生成的 meeting-prep 報告，評估假設品質、評分合理性、問題實用性。

> CI 批次 threshold gate：`make evaluate-meeting-prep-llm`（讀取本命令的 JSON 輸出）

---

## 用法

```
/evaluate-meeting-prep-quality                          # 評估最新一份
/evaluate-meeting-prep-quality output/meeting_prep_20260306_ea576a4f.md  # 指定檔案
```

---

## 執行步驟

### Step A：定位報告

如果使用者指定了檔案路徑，讀取該檔案。否則找 `output/meeting_prep_*.md` 中最新的一份。

讀取完整報告內容。

### Step A2：校準錨點（Calibration Anchor）

在評分目標報告**前**，先評估校準 fixture，建立評分基準：

1. 讀取 `eval/fixtures/meeting_prep/calibration_anchor_low.md`
2. 按 Step B 的 9 維度快速評分（不需輸出完整報告，只需內心校準）
3. 期望分數：`s3_data_support=2, s3_causal_logic=1, s3_alternative_considered=1, s6_eeat_justified=2, s9_question_specificity=2, s4_genuine_tension=1, s4_source_diversity=2, overall_coherence=2, s8_maturity_justified=2`
4. 若你的校準評分與期望偏差 > 1.5 分（任一維度），調低你的評分標準——校準 anchor 是刻意寫的低品質報告

接著再評估目標報告（Step B）。

### Step B：九維度評分（你是 Judge）

對報告的 9 個維度逐一評分（1-5 分）。原 6 維度拆分為 9 維度以增加鑑別度：

#### 1. `s3_data_support`（假設數據佐證）— 從 `s3_hypothesis_grounded` 拆出

評估 S3 假設是否引用 S1 的**具體指標百分比和數值**。

- **1 分**：假設未引用任何數字（「可能是技術問題」）
- **3 分**：部分假設引用了百分比，但數據點稀疏
- **5 分**：每個假設都引用具體指標名 + 百分比 + latest 值（如「Discover -55.4%、latest 915,917」）

#### 2. `s3_causal_logic`（假設因果推理）— 從 `s3_hypothesis_grounded` 拆出

評估 S3 假設是否有多步因果推理鏈。

- **1 分**：只有結論無推理（「CTR 下降是因為 SERP 變化」）
- **3 分**：有一步推理但未解釋機制
- **5 分**：有多步推理鏈（「AIO 觸發 48% 查詢 → 有機 CTR 降 61% → Position 1 CTR 年降 32% → 影評類資訊型查詢被直接回答」）

#### 3. `s3_alternative_considered`（替代解釋考量）— 從 `s3_hypothesis_grounded` 拆出

評估 S3 是否考慮了替代解釋，而非只提出單一假設。

- **1 分**：每個異常只有 1 個假設
- **3 分**：有 2-3 個假設但都是同一方向
- **5 分**：每個異常有技術面 + 內容面 + 外部面三層假設，且互相排斥

#### 4. `s6_eeat_justified`（E-E-A-T 評分依據充分度）

- **1 分**：分數無依據或只有空泛描述（「品質不錯」）
- **3 分**：有部分依據但某些維度缺乏具體觀察
- **5 分**：每個分數都有具體依據（引用指標、KB 知識、業界比較）

#### 5. `s9_question_specificity`（提問特異性）

- **1 分**：提問可以套用於任何 SEO 專案（「你覺得 SEO 重要嗎？」）
- **3 分**：提問有 SEO 針對性但未引用本次數據
- **5 分**：提問明確引用本次指標/異常，只有了解本報告內容才能提出

#### 6. `s4_genuine_tension`（矛盾真實性）— 從 `s4_contradiction_quality` 拆出

- **1 分**：矛盾是人為製造的，實際觀點並無衝突
- **3 分**：有一定張力但過度簡化了觀點差異
- **5 分**：矛盾真實存在，有清楚的邏輯衝突（「KB 說不要優化 Discover，但 Google 首次推出 Discover 獨立更新」）

#### 7. `s4_source_diversity`（四方來源實質內容）— 從 `s4_contradiction_quality` 拆出

- **1 分**：四方來源（KB/顧問/指標/業界）多數是空或「不明」
- **3 分**：3/4 方有實質內容但某些只是摘要
- **5 分**：4/4 方都有獨立觀點且互相比較，判斷欄有具體結論

#### 8. `overall_coherence`（整體邏輯鏈通順度）

- **1 分**：三者各自獨立，無邏輯連結
- **3 分**：有部分連結但存在邏輯跳躍
- **5 分**：S1 每個重要異常都有 S3 假設對應，S3 假設都衍生出 S9 提問

#### 9. `s8_maturity_justified`（成熟度評分依據充分度）

- **1 分**：等級無依據，或下一步目標與當前等級不連貫
- **3 分**：有部分依據但某些維度缺乏具體觀察
- **5 分**：每個等級都有具體證據支撐，下一步明確描述目標等級特徵

### Step C：彙整結果並儲存

將 Step B 的結果彙整為以下 JSON 結構：

```json
{
  "report_path": "output/meeting_prep_XXXXXXXX_XXXXXXXX.md",
  "evaluated_at": "2026-03-22T...",
  "dimensions": {
    "s3_data_support": {"score": 4, "reason": "..."},
    "s3_causal_logic": {"score": 3, "reason": "..."},
    "s3_alternative_considered": {"score": 4, "reason": "..."},
    "s6_eeat_justified": {"score": 3, "reason": "..."},
    "s9_question_specificity": {"score": 5, "reason": "..."},
    "s4_genuine_tension": {"score": 4, "reason": "..."},
    "s4_source_diversity": {"score": 3, "reason": "..."},
    "overall_coherence": {"score": 4, "reason": "..."},
    "s8_maturity_justified": {"score": 4, "reason": "..."}
  },
  "average_score": 3.78,
  "summary": "一句話總結品質"
}
```

> **向下相容**：`eval_meeting_prep_llm.py` 支援新 9 維度和舊 6 維度 JSON。
> 若 JSON 有 `s3_data_support` 則用 9 維度；否則從 `s3_hypothesis_grounded` 映射。

寫入 `output/eval_meeting_prep_quality_YYYYMMDD.json`。

### Step C2：推送至 Laminar Dashboard

將 9 個維度分數推送至 Laminar group `meeting_prep_quality`：

```bash
.venv/bin/python scripts/_push_laminar_score.py \
  --json-file output/eval_meeting_prep_quality_YYYYMMDD.json \
  --group meeting_prep_quality
```

此步驟將 JSON 中 `dimensions` 的 6 個 key-score 對推送至 Laminar。若 `LMNR_PROJECT_API_KEY` 未設定則靜默跳過。

### Step D：輸出報告

```
## Meeting-Prep 內容品質評估（{日期}）

### 報告：{report_path}

| 維度 | 分數 | 評語 |
|------|------|------|
| 假設數據佐證 | X/5 | ... |
| 假設因果推理 | X/5 | ... |
| 替代解釋考量 | X/5 | ... |
| E-E-A-T 評分依據 | X/5 | ... |
| 提問特異性 | X/5 | ... |
| 矛盾真實性 | X/5 | ... |
| 四方來源實質內容 | X/5 | ... |
| 整體邏輯鏈 | X/5 | ... |
| 成熟度評分依據 | X/5 | ... |

**平均分：X.X/5**（9 維度）

### 改善建議
{列出 1-3 個可操作的改善項目}
```

---

## 注意事項

- 非 CI gate——此命令透過 Claude Code 互動執行
- 建議每份報告跑 1 次即可（Layer 1/2 已覆蓋結構品質）
- 若分數 < 3 的維度超過 2 個，建議重新生成報告
