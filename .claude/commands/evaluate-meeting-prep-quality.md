# /evaluate-meeting-prep-quality — Meeting-Prep 內容品質評估（不需要 OpenAI）

**你（Claude Code）就是語意判斷引擎**——直接推理，不呼叫任何外部 LLM API。

Layer 3 Content Quality 評估：針對已生成的 meeting-prep 報告，評估假設品質、評分合理性、問題實用性。

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

### Step B：五維度評分（你是 Judge）

對報告的 5 個維度逐一評分（1-5 分）：

#### 1. `s3_hypothesis_grounded`（根因假設扎根度）

評估 S3「深度根因假設」是否引用 S1 的具體指標數據。

- **1 分**：假設完全是泛泛的 SEO 建議，未引用任何本次指標
- **3 分**：部分假設引用了指標，但多數假設可套用於任何網站
- **5 分**：每個假設都明確引用 S1 的具體指標（例如「保養 -57%」），假設與數據直接對應

#### 2. `s6_eeat_justified`（E-E-A-T 評分依據充分度）

評估 S6 每個 E-E-A-T 分數是否有具體依據。

- **1 分**：分數無依據或只有空泛描述（「品質不錯」）
- **3 分**：有部分依據但某些維度缺乏具體觀察
- **5 分**：每個分數都有具體依據（引用指標、KB 知識、業界比較）

#### 3. `s9_question_specificity`（提問特異性）

評估 S9 提問是否針對本次客戶/情境。

- **1 分**：提問可以套用於任何 SEO 專案（「你覺得 SEO 重要嗎？」）
- **3 分**：提問有 SEO 針對性但未引用本次數據
- **5 分**：提問明確引用本次指標/異常，只有了解本報告內容才能提出

#### 4. `s4_contradiction_quality`（矛盾項目品質）

評估 S4 交叉比對中標記為「矛盾」的項目是否存在真正的張力。

- **1 分**：矛盾是人為製造的，實際觀點並無衝突
- **3 分**：有一定張力但過度簡化了觀點差異
- **5 分**：矛盾真實存在，且清楚標示了 KB/顧問/指標/業界四方觀點的具體分歧

#### 5. `overall_coherence`（整體邏輯鏈通順度）

評估 S1 異常 → S3 假設 → S9 提問 的邏輯鏈是否通順。

- **1 分**：三者各自獨立，無邏輯連結
- **3 分**：有部分連結但存在邏輯跳躍
- **5 分**：S1 每個重要異常都有 S3 假設對應，S3 假設都衍生出 S9 提問，形成完整推理鏈

### Step C：彙整結果並儲存

將 Step B 的結果彙整為以下 JSON 結構：

```json
{
  "report_path": "output/meeting_prep_XXXXXXXX_XXXXXXXX.md",
  "evaluated_at": "2026-03-12T...",
  "dimensions": {
    "s3_hypothesis_grounded": {"score": 4, "reason": "..."},
    "s6_eeat_justified": {"score": 3, "reason": "..."},
    "s9_question_specificity": {"score": 5, "reason": "..."},
    "s4_contradiction_quality": {"score": 4, "reason": "..."},
    "overall_coherence": {"score": 4, "reason": "..."}
  },
  "average_score": 4.0,
  "summary": "一句話總結品質"
}
```

寫入 `output/eval_meeting_prep_quality_YYYYMMDD.json`。

### Step D：輸出報告

```
## Meeting-Prep 內容品質評估（{日期}）

### 報告：{report_path}

| 維度 | 分數 | 評語 |
|------|------|------|
| 根因假設扎根度 | X/5 | ... |
| E-E-A-T 評分依據 | X/5 | ... |
| 提問特異性 | X/5 | ... |
| 矛盾項目品質 | X/5 | ... |
| 整體邏輯鏈 | X/5 | ... |

**平均分：X.X/5**

### 改善建議
{列出 1-3 個可操作的改善項目}
```

---

## 注意事項

- 非 CI gate——此命令透過 Claude Code 互動執行
- 建議每份報告跑 1 次即可（Layer 1/2 已覆蓋結構品質）
- 若分數 < 3 的維度超過 2 個，建議重新生成報告
