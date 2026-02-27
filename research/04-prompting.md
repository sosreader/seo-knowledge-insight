# Prompt Engineering 進階

> 屬於 [research/](./README.md)。業界最佳實踐（2026-02-27 研究）。Prompt 基礎請見 [01-ai-fundamentals.md](./01-ai-fundamentals.md) 第 4 節。

---

## 13. Prompt Engineering 進階：業界最佳實踐（2026-02-27 研究）

### 四層結構：What / Why / How / Evidence

每個 Answer 應包含四個層次（對應 Google E-E-A-T 框架）：

| 層次         | 對應 E-E-A-T      | 內容                            |
| ------------ | ----------------- | ------------------------------- |
| **What**     | Expertise         | 直接說明建議或結論              |
| **Why**      | Authoritativeness | Google 演算法邏輯、SEO 影響機制 |
| **How**      | Experience        | 具體可執行步驟、工具操作路徑    |
| **Evidence** | Trustworthiness   | 可在 GSC/GA4 驗證的位置或數據   |

```
❌ Completeness 3分：
A: canonical 應該指向乾淨的 URL 版本。

✅ Completeness 5分：
A: [What] canonical 應統一指向不帶 query string 的乾淨 URL。
   [Why] Google 爬蟲有時會自行選擇錯誤的 canonical，浪費爬蟲預算。
   [How] 在帶參數頁面的 <head> 加 <link rel="canonical" href="..."> 指向標準版本。
   [Evidence] GSC「索引 > 頁面 > 系統選擇的 canonical」驗證是否生效。
```

### 多角色定義（Multi-Expert Prompting）

單一「SEO 專家」角色不夠，升級為三個視角：

```python
EXTRACT_SYSTEM_PROMPT = """
你同時扮演三個角色：

知識本體設計師：每個 Q&A 能獨立放進知識庫，讀者不需要看原始會議
SEO 實踐審計員：判斷建議是否有工具配套（GSC、GA4），步驟是否能落地
品質評估官：用「完整性 + 可執行性 + 可驗證性」衡量每個 A
"""
```

研究來源：[ExpertPrompting (arXiv:2305.14688)](https://arxiv.org/html/2305.14688v2)

### 防止幻覺（Hallucination Prevention）

SEO 知識萃取最常見的三種幻覺：

| 幻覺類型     | 錯誤範例                                          | 正確做法                                       |
| ------------ | ------------------------------------------------- | ---------------------------------------------- |
| 補充通用知識 | 會議說「title 有問題」→ 加上「通常 50-60 字最佳」 | 只寫會議有的，未提及標註「（具體做法未提及）」 |
| 模糊工具路徑 | 「在 GA4 查看」                                   | 「GSC『索引 > 頁面』」或加「（路徑未提及）」   |
| 虛構數字     | 「流量下降約 20%」                                | 「流量下降」或「（幅度未提及）」               |

研究來源：[Anthropic Hallucination Reduction](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)

### 三個 Few-Shot 範例策略

研究顯示應覆蓋 confidence 三個等級，避免過度（> 5 個）：

| 範例   | Confidence | 用途                                                   |
| ------ | ---------- | ------------------------------------------------------ |
| 範例 1 | 0.9（高）  | 顧問明確建議，有完整 What/Why/How/Evidence             |
| 範例 2 | 0.4（低）  | 觀察中議題，標註「（持續觀察中）」                     |
| 範例 3 | 0.65（中） | 部分資訊，有 What/Why/How，Evidence 標註「（未提及）」 |
| 範例 4 | 0.7（中）  | 運營型診斷問題，How 空白時使用 `[補充]` 標記           |

研究來源：[Few-Shot Prompting Guide](https://www.promptingguide.ai/techniques/fewshot)

### `[補充]` Attribution Tag：如何讓 AI 補充知識而不算幻覺 {#補充-attribution-tag}

**問題場景**：運營型會議（2024–2026）Completeness 評分 3.38，原因是 How 層大量出現「（具體做法未提及）」。防幻覺規則讓 LLM 不能補充任何非會議內容，導致 How 永遠空白，Judge 永遠給 3 分。

**解法：`[補充]` 標記（Attribution Tag）**

不是放棄防幻覺規則，而是加入明確的例外管道：

```
原先（防幻覺規則）：
只能從會議文本提取 → How 空白 → Judge 給 3 分

新機制：
How 空白時，允許補充「通用從業知識」，但必須用 [補充] 標籤明確標示來源差異

結果：
[How] （會議未提及具體步驟）[補充] 通用驗證步驟：(1) GSC 確認規則生效；(2) 觀察趨勢 1-2 週
→ Judge 給 4 分（清楚標記非會議原文，但有實質內容）
```

**五條限制**（防止 [補充] 被濫用）：

1. `[補充]` 必須與 `[How]` 在同一段落
2. 內容只能是「任何從業者都知道的通用步驟」
3. 禁止把「此次特定情況」套用到通用做法
4. 禁止在 `[補充]` 中寫入任何數字或會議未提及的具體結果
5. 只在 How 完全空白或只有「（未提及）」時才用

**Judge prompt 也必須同步更新**，加入 4 分定義和說明：

| 分數  | Completeness 標準（更新後）                    |
| ----- | ---------------------------------------------- |
| 3     | What/Why 有，How 完全缺失                      |
| **4** | **How 含 `[補充]` 通用步驟（清楚標記非原文）** |
| 5     | What/Why/How 齊全，How 有情境專屬步驟          |

**驗證結果**：Completeness 3.70 → **3.85**，Accuracy 維持 3.95（未下降）。

業界支撐（Multi-Layer Attribution / Two-Pass Extraction）：GROPROE (ACM 2024)、DO-RAG (arXiv 2505.17058)

### JSON Schema description 約束

OpenAI strict=True 不支援 minLength/maxItems 等欄位驗證，改用 description 做軟約束：

```python
"question": {"type": "string", "description": "SEO 問題，自包含，20–150 字"},
"answer":   {"type": "string", "description": "含 What/Why/How/Evidence，至少 100 字"},
"keywords": {"type": "array",  "description": "3–7 個 SEO 術語，避免通用詞"},
"confidence": {"type": "number", "description": "0.0–1.0，顧問建議≥0.8，推測≤0.7"},
```

研究來源：[OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

---

