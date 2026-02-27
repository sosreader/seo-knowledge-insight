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

