# AI 基礎概念

> 屬於 [research/](./README.md)。涵蓋 LLM、Token、Prompt、Structured Output、Embedding、Cosine Similarity。

---

## 2. LLM 是什麼，怎麼呼叫

### 概念

LLM（Large Language Model）= GPT、Claude 等 AI 模型。
你傳一段文字進去（prompt），它根據學過的大量資料預測最合理的回應。

**它不是搜尋引擎，不是資料庫。** 它是「根據上下文預測下一段文字的機器」。

### 呼叫方式（本專案）

```python
from openai import OpenAI

client = OpenAI(api_key="sk-xxx")

response = client.chat.completions.create(
    model="gpt-5.2",
    messages=[
        {"role": "system", "content": "你是 SEO 專家，只用繁體中文回答"},
        {"role": "user",   "content": "什麼是 canonical tag？"},
    ]
)

answer = response.choices[0].message.content
# "Canonical tag 是 HTML 標籤，用來告訴搜尋引擎..."
```

### 兩種 message 角色

| 角色     | 用途                           | 前端類比         |
| -------- | ------------------------------ | ---------------- |
| `system` | 設定 AI 的角色、規則、輸出語言 | 元件的初始 props |
| `user`   | 實際問題或要處理的資料         | 使用者的 input   |

本專案所有 prompt 定義在 `utils/openai_helper.py`，包含萃取 Q&A、合併、分類等。

---

## 3. Token：AI 的計費與限制單位

### Token 是什麼

模型不是「一個字一個字」讀，而是把文字切成「token」（子詞單位）：

```
"Core Web Vitals"   → 3 tokens
"你好世界"           → 4 tokens（中文約每字 1 token）
"unassigned"        → 1 token
一份 87 頁會議紀錄   → 約 3,000–8,000 tokens
```

### 為什麼重要

**計費**：API 費用 = (輸入 tokens + 輸出 tokens) × 每 token 單價

**Context Window**：模型一次能處理的 token 上限。
本專案超過 6000 tokens 的會議紀錄會自動切段：

```python
# scripts/extract_qa_helpers.py
MAX_TOKENS_PER_CHUNK = 6000   # 超過就切段，分批送給 AI
```

### 本專案各步驟的 token 消耗

| 步驟            | 模型       | 每次輸入       | 總成本估算      |
| --------------- | ---------- | -------------- | --------------- |
| Step 2 萃取 Q&A | gpt-5.2    | 每份文件 3K–8K | 87 份 × 平均 5K |
| Step 3 合併     | gpt-5.2    | 每對 200–500   | 依重複數量      |
| Step 3 分類     | gpt-5-mini | 每筆 100–200   | 725 筆 × 150    |
| Step 5 評估     | gpt-5.2    | 每筆 300–600   | 30 筆 × 450     |

---

## 4. Prompt Engineering：怎麼跟 AI 說話

### 為什麼 Prompt 很重要

同樣的 AI，給不同的 prompt，結果差很多：

```
差的 prompt：
「幫我找出這段文字的問題和答案」
→ AI 隨便給幾個，格式不固定，內容表面

好的 prompt（本專案 Step 2 使用）：
「你是 SEO 知識萃取專家。
從以下會議紀錄中，萃取 3-8 個有價值的 Q&A。

要求：
- Q 必須可以獨立理解（不需要看原始會議）
- A 必須包含具體建議、原因或數據
- 跳過行政安排、閒聊、人名提及
- 用繁體中文

每個 Q&A 回傳：question, answer, keywords (3-5個), confidence (0-1)」
→ AI 給出符合格式、有深度的結果
```

### Completeness 3.70 → 3.85（2026-02-27 解決）

Completeness 從 3.70 提升至 **3.85**，做法是引入 `[補充]` Attribution Tag。

根本原因：運營型會議（狀態回報）本身缺少 How 步驟，防幻覺規則讓 LLM 只能寫「（具體做法未提及）」。

解法：加入明確標記的「補充通用知識」機制（見 [第 13 節進階技巧](#補充-attribution-tag)），讓 LLM 可以補充通用 SEO 標準做法，但必須用 `[補充]` 標籤明確區分。

### 小規模驗證原則

**在花錢跑全部之前，先跑 3 份驗證 prompt 改動是否有效：**

```bash
python scripts/run_pipeline.py --step 2 --limit 3 --force
python scripts/05_evaluate.py --sample 15 --skip-classify-eval
# 確認 Completeness ≥ 4.0 再跑全量
```

---

## 5. Structured Output：強制 AI 回傳固定格式

### 問題

AI 預設輸出自由文字，但程式需要固定格式才能 parse：

```
❌ 自由文字（沒辦法用程式處理）：
"這個 Q&A 品質不錯，相關性大約 4 分，完整性稍微不足..."

✅ 結構化 JSON（程式可以直接讀）：
{"relevance": {"score": 4, "reason": "..."}, "completeness": {"score": 3, "reason": "..."}}
```

### JSON Schema（本專案使用方式）

用 JSON Schema 定義格式，AI 只能照這個格式回答：

```python
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "classify_result",
            "strict": True,                  # 強制嚴格符合
            "schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [            # 只能選這 10 個其中一個
                            "索引與檢索", "連結策略", "搜尋表現分析",
                            "內容策略", "Discover與AMP", "技術SEO",
                            "GA與數據追蹤", "平台策略", "演算法與趨勢", "其他"
                        ]
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["基礎", "進階"]
                    },
                    "evergreen": {"type": "boolean"}
                },
                "required": ["category", "difficulty", "evergreen"],
                "additionalProperties": False
            }
        }
    }
)

result = json.loads(response.choices[0].message.content)
print(result["category"])   # "技術SEO"
```

### BUG-001 根因（2026-02-27 修復）

`strict: True` 應保證格式正確，但推理模型（gpt-5-mini）token 不夠時
`content` 回傳空字串 `""`，`json.loads("{}") = {}`，
空 dict 沒有 `category` 欄位，但仍被計入 `total`。

**修復**：append 前先確認必要欄位存在。

---

## 6. Embedding：把文字變成數字

### 為什麼需要

關鍵字搜尋的根本限制：

```
查詢：「網站速度對排名的影響」

關鍵字搜尋：✅ 找到含「速度」「排名」的文章
            ❌ 找不到「Core Web Vitals 與 SEO 效能」（字不一樣但意思相關）

語意搜尋：  ✅ 兩個都找得到（因為意思相近）
```

### Embedding 是什麼

把一段文字轉換成一個固定長度的數字列表（向量）。
**語意相近的文字，轉換後的數字列表也相近。**

```python
from openai import OpenAI

client = OpenAI()
result = client.embeddings.create(
    model="text-embedding-3-small",
    input="Core Web Vitals 與 SEO 效能"
)

vector = result.data[0].embedding
# [0.023, -0.156, 0.891, 0.044, -0.312, ...]
print(len(vector))  # 1536 個數字
```

### 直覺理解

把每段文字想像成 1536 維空間裡的一個點：

- 「Core Web Vitals」和「網站速度」→ 兩個點距離很近
- 「內部連結架構」和「GA 追蹤設定」→ 兩個點距離很遠

### 本專案的使用

**Step 3**：計算 725 筆 Q&A 的 embedding，儲存成 `qa_embeddings.npy`（numpy 陣列檔）。

- 去重用：找相似 Q&A（cosine ≥ 0.88 就合併）
- 搜尋用：Step 4 / Step 5 載入，做語意搜尋

計算一次存起來，後續不重新計算（省成本）。

---

## 7. Cosine Similarity：比較兩段文字的相似度

### 概念

拿到兩個 embedding 向量後，計算它們的「夾角餘弦值」：

| 數值       | 意義                       |
| ---------- | -------------------------- |
| `1.0`      | 完全相同（意思一模一樣）   |
| `0.88+`    | 非常相似（本專案去重門檻） |
| `0.7–0.88` | 相關但不重複               |
| `< 0.5`    | 意思不同                   |

### 本專案的去重邏輯

```python
import numpy as np

# qa_embs shape: (725, 1536)，725 筆 Q&A 各有 1536 維向量
qa_embs = np.load("output/qa_embeddings.npy")

# 正規化（讓長度變成 1，方便算 cosine）
norms = np.linalg.norm(qa_embs, axis=1, keepdims=True)
qa_norm = qa_embs / (norms + 1e-8)

# 計算所有 Q&A 兩兩之間的相似度矩陣
# similarity[i][j] = 第 i 筆和第 j 筆 Q&A 的相似度
similarity_matrix = qa_norm @ qa_norm.T   # (725, 725)

THRESHOLD = 0.88
# 找出 similarity > 0.88 的 pair → 送給 gpt-5.2 判斷是否合併
```

---
