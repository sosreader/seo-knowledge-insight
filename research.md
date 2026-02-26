# SEO QA Pipeline 技術教學

> 專為前端開發者設計，聚焦 AI 相關技術。
> 假設你已熟悉 JavaScript / fetch / JSON，直接從 AI 概念開始。

---

## 目錄

1. [快速對照表（Python / CLI / API）](#1-快速對照表)
2. [LLM 是什麼，怎麼呼叫](#2-llm-是什麼怎麼呼叫)
3. [Token：AI 的計費與限制單位](#3-token-ai-的計費與限制單位)
4. [Prompt Engineering：怎麼跟 AI 說話](#4-prompt-engineering怎麼跟-ai-說話)
5. [Structured Output：強制 AI 回傳固定格式](#5-structured-output強制-ai-回傳固定格式)
6. [Embedding：把文字變成數字](#6-embedding把文字變成數字)
7. [Cosine Similarity：比較兩段文字的相似度](#7-cosine-similarity比較兩段文字的相似度)
8. [RAG：讓 AI 查資料再回答](#8-rag讓-ai-查資料再回答)
9. [Hybrid Search：語意 + 關鍵字混合搜尋](#9-hybrid-search語意--關鍵字混合搜尋)
10. [LLM-as-Judge：用 AI 評估 AI](#10-llm-as-judge用-ai-評估-ai)
11. [Reasoning Model：會先思考的 AI](#11-reasoning-model會先思考的-ai)
12. [本專案完整架構與決策](#12-本專案完整架構與決策)

---

## 1. 快速對照表

前端你已知的東西，直接對照：

| 你知道的 | Python / 本專案 |
|---------|----------------|
| `fetch(url, { headers })` | `requests.get(url, headers=...)` |
| `process.env.API_KEY` | `os.getenv("API_KEY")` |
| `JSON.parse / JSON.stringify` | `json.loads / json.dumps` |
| `npm run build -- --flag` | `python script.py --step 2 --limit 3` |
| `localStorage.setItem(k, v)` | `Path("file.json").write_text(...)` |
| Promise chain | 每步結果存 JSON 檔，下步再讀 |

其他語法差異（縮排、`def`、`import`）看到就懂，不需要特別記。

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

| 角色 | 用途 | 前端類比 |
|------|------|---------|
| `system` | 設定 AI 的角色、規則、輸出語言 | 元件的初始 props |
| `user` | 實際問題或要處理的資料 | 使用者的 input |

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

| 步驟 | 模型 | 每次輸入 | 總成本估算 |
|------|------|---------|----------|
| Step 2 萃取 Q&A | gpt-5.2 | 每份文件 3K–8K | 87 份 × 平均 5K |
| Step 3 合併 | gpt-5.2 | 每對 200–500 | 依重複數量 |
| Step 3 分類 | gpt-5-mini | 每筆 100–200 | 703 筆 × 150 |
| Step 5 評估 | gpt-5.2 | 每筆 300–600 | 30 筆 × 450 |

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

### 本專案 Completeness 分數 3.70 的問題

目前 Q&A 萃取品質評估中，Completeness（完整性）平均只有 3.70 / 5。
LLM Judge 觀察到 Answer 缺少「原因 + 數據 + 可執行建議」。

這是**唯一需要花錢改善的品質問題**（需重跑 Step 2 全部 87 份文件）。
改法：強化 prompt 要求 A 必須包含 What / Why / How。

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

**Step 3**：計算 703 筆 Q&A 的 embedding，儲存成 `qa_embeddings.npy`（numpy 陣列檔）。
- 去重用：找相似 Q&A（cosine ≥ 0.88 就合併）
- 搜尋用：Step 4 / Step 5 載入，做語意搜尋

計算一次存起來，後續不重新計算（省成本）。

---

## 7. Cosine Similarity：比較兩段文字的相似度

### 概念

拿到兩個 embedding 向量後，計算它們的「夾角餘弦值」：

| 數值 | 意義 |
|------|------|
| `1.0` | 完全相同（意思一模一樣） |
| `0.88+` | 非常相似（本專案去重門檻） |
| `0.7–0.88` | 相關但不重複 |
| `< 0.5` | 意思不同 |

### 本專案的去重邏輯

```python
import numpy as np

# qa_embs shape: (703, 1536)，703 筆 Q&A 各有 1536 維向量
qa_embs = np.load("output/qa_embeddings.npy")

# 正規化（讓長度變成 1，方便算 cosine）
norms = np.linalg.norm(qa_embs, axis=1, keepdims=True)
qa_norm = qa_embs / (norms + 1e-8)

# 計算所有 Q&A 兩兩之間的相似度矩陣
# similarity[i][j] = 第 i 筆和第 j 筆 Q&A 的相似度
similarity_matrix = qa_norm @ qa_norm.T   # (703, 703)

THRESHOLD = 0.88
# 找出 similarity > 0.88 的 pair → 送給 gpt-5.2 判斷是否合併
```

---

## 8. RAG：讓 AI 查資料再回答

### 核心問題

AI 不知道你的私人資料（會議紀錄、客戶資料）。
直接問 AI → AI 只能靠通用知識回答，可能不準確。

### RAG 解決方案

**R**etrieval **A**ugmented **G**eneration = 先搜尋，再生成

```
[問題] 「上次開會說 Discover 流量下降，怎麼解決？」
   ↓
[Retrieval] 把問題轉成 embedding → 在 703 筆 Q&A 中找最相關的 5 筆
   ↓
[Augmented] 把這 5 筆 Q&A 塞進 prompt：
   「根據以下 SEO 知識：
   Q: Discover 流量下降原因？ A: 可能是內容品質、AMP...
   Q: AMP 焦點新聞如何維持？ A: ...
   [3 筆省略]
   請根據以上知識，分析本週 Discover 下降 20% 的情況」
   ↓
[Generation] AI 有了具體上下文，回答更準確、有依據
```

### 比喻：開卷考試

- ❌ 無 RAG = 閉卷考試（AI 只能靠記憶）
- ✅ 有 RAG = 開卷考試（AI 可以查你的筆記本）

### 本專案 Step 4 流程

```python
# 1. 讀取本週 Google Sheets 指標
metrics = load_google_sheets_tsv("metrics.tsv")

# 2. 偵測異常（月趨勢超出閾值）
anomalies = detect_anomalies(metrics)
# → ["有效頁面數 -5%", "AMP Article -114%", "CTR -8%"]

# 3. 對每個異常，做語意搜尋
for anomaly in anomalies:
    query_vector = embed(anomaly)   # 轉成 embedding
    top5_qa = semantic_search(query_vector, qa_embeddings, top_k=5)

    # 4. 組裝 prompt（RAG 的核心）
    prompt = f"""
    本週異常：{anomaly}

    相關知識：
    {format_qa_list(top5_qa)}

    請分析原因並給出具體建議。
    """

    # 5. 生成週報段落
    report_section = gpt52(prompt)
```

---

## 9. Hybrid Search：語意 + 關鍵字混合搜尋

### 純語意搜尋的弱點

語意搜尋有時會漏掉「精確術語」：

```
查詢：「WAF 封鎖 Googlebot」
語意搜尋可能找到：「伺服器設定問題」（語意相近但沒有 WAF）
    → 但 WAF 是關鍵詞，漏掉就答非所問
```

### Hybrid Search = 語意分數 + 關鍵字加分

```python
# Step 1：計算語意相似度分數
scores = cosine_similarity(query_vector, all_qa_vectors)

# Step 2：關鍵字加分（Q&A 的 keywords 出現在查詢中）
for i, qa in enumerate(qa_pairs):
    hits = sum(1 for kw in qa["keywords"] if kw.lower() in query.lower())
    if hits > 0:
        scores[i] += 0.08 * min(hits, 3)   # 最多加 0.24 分

# Step 3：取分數最高的前 5 筆
top_indices = np.argsort(scores)[::-1][:5]
retrieved = [qa_pairs[i] for i in top_indices]
```

### 本專案 Retrieval 評估基準線

| 指標 | 數值 | 說明 |
|------|------|------|
| KW Hit Rate | 54% | 查詢的關鍵字有多少被 top-5 覆蓋 |
| Category Hit Rate | 75% | top-5 中有沒有正確分類的 Q&A |
| MRR | 0.79 | 第一筆正確結果的排名倒數（越高越好） |
| LLM Top-1 Precision | 100% | top-1 結果是否真的和查詢相關 |

KW Hit Rate 54% 偏低，未來可考慮 cross-encoder reranking 改善。

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

| 維度 | 問的問題 | 目前分數 |
|------|---------|---------|
| Relevance | 是否有價值的 SEO 知識（非閒聊） | 4.65 ✅ |
| Accuracy | 內容是否合理無虛構 | 3.80 |
| Completeness | 是否包含建議 + 原因 + 案例 | 3.70 ← 待改善 |
| Granularity | 一個 Q 只問一個主題 | 4.65 ✅ |

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

## 12. 本專案完整架構與決策

### Pipeline 全景

```
Notion 會議紀錄（87 份，2023–2026）
            ↓
[Step 1] fetch_notion.py — Notion API 擷取
  增量機制：比對 last_edited_time，只抓更新的頁面
            ↓ raw_data/markdown/*.md

[Step 2] extract_qa.py — LLM 萃取 Q&A
  模型：gpt-5.2（需要高品質理解）
  長文處理：超過 6000 tokens 自動切段
  產出：699 筆原始 Q&A
            ↓ output/qa_per_meeting/*.json

[Step 3] dedupe_classify.py — 去重 + 分類
  去重：text-embedding-3-small 計算向量
        cosine ≥ 0.88 → gpt-5.2 判斷是否合併
  分類：gpt-5-mini 貼 10 種標籤 + difficulty + evergreen
  產出：703 筆去重後 Q&A + 1536 維 embedding 向量
            ↓ output/qa_final.json + qa_embeddings.npy

[Step 4] generate_report.py — RAG 週報生成
  資料：Google Sheets 指標（TSV）
  流程：異常偵測 → Hybrid Search → RAG 組裝 → gpt-5.2 生成
            ↓ output/report_YYYYMMDD.md

[Step 5] evaluate.py — 評估
  Q&A 品質：gpt-5.2 LLM-as-Judge（4 維度）
  分類品質：gpt-5-mini 驗證分類正確率
  Retrieval 品質：語意搜尋 + gpt-5-mini 相關性判斷
            ↓ output/eval_report.json
```

### 模型選擇邏輯

```
需要理解複雜文本、推理、生成高品質輸出
  → gpt-5.2（主力模型）
  → 用於：Q&A 萃取、Q&A 合併、週報生成、LLM Judge

需要結構化輸出、分類、簡單判斷
  → gpt-5-mini（省成本）
  → 用於：Q&A 分類、Retrieval 相關性判斷

需要計算語意向量
  → text-embedding-3-small（極便宜，只做向量計算）
  → 用於：去重、Step 4/5 語意搜尋
```

### 當前品質基準線（2026-02-27）

| 指標 | 數值 | 狀態 |
|------|------|------|
| Relevance | 4.65 / 5 | ✅ 不需改善 |
| Accuracy | 3.80 / 5 | 可改善 |
| **Completeness** | **3.70 / 5** | **⚠️ 優先改善目標** |
| Granularity | 4.65 / 5 | ✅ 不需改善 |
| Category 正確率 | 75% | ✅ 可接受 |
| Retrieval MRR | 0.79 | ✅ |
| LLM Top-1 Precision | 100% | ✅ |
| KW Hit Rate | 54% | 可改善（低成本） |

### 花錢前必做：小規模驗證

任何需要 API 費用的改動，流程是：

```
1. 修改 prompt 或設定
2. --limit 3 只跑 3 份文件（驗證方向對）
3. 用 Step 5 評估那 3 份的品質
4. 通過門檻才擴大到全量
```

**不要先跑完 87 份再來評估要不要改 prompt。**
