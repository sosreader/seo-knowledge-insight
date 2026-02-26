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
20. [FastAPI RAG API 化：把知識庫包成服務](#20-fastapi-rag-api-化把知識庫包成服務)
21. [ECR + EC2 SSM 部署模式](#21-ecr--ec2-ssm-部署模式)

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

══════════════ API 層（2026-02-27 新增）══════════════

[SEO Insight API] app/ — FastAPI，讀 Step 3 產出進記憶體
  啟動時載入：qa_final.json（703 筆）+ qa_embeddings.npy（703×1536）
  endpoints：
    POST /api/v1/search  → numpy cosine 語意搜尋
    POST /api/v1/chat    → RAG 問答（gpt-5.2）
    GET  /api/v1/qa      → 篩選列表
  部署：Docker image → ECR → EC2（SSM 遠端換容器）
            ↓ http://EC2:8001
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

---

## 13. Prompt Engineering 進階：業界最佳實踐（2026-02-27 研究）

### 四層結構：What / Why / How / Evidence

每個 Answer 應包含四個層次（對應 Google E-E-A-T 框架）：

| 層次 | 對應 E-E-A-T | 內容 |
|------|------------|------|
| **What** | Expertise | 直接說明建議或結論 |
| **Why** | Authoritativeness | Google 演算法邏輯、SEO 影響機制 |
| **How** | Experience | 具體可執行步驟、工具操作路徑 |
| **Evidence** | Trustworthiness | 可在 GSC/GA4 驗證的位置或數據 |

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

| 幻覺類型 | 錯誤範例 | 正確做法 |
|---------|---------|---------|
| 補充通用知識 | 會議說「title 有問題」→ 加上「通常 50-60 字最佳」 | 只寫會議有的，未提及標註「（具體做法未提及）」 |
| 模糊工具路徑 | 「在 GA4 查看」 | 「GSC『索引 > 頁面』」或加「（路徑未提及）」 |
| 虛構數字 | 「流量下降約 20%」 | 「流量下降」或「（幅度未提及）」 |

研究來源：[Anthropic Hallucination Reduction](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)

### 三個 Few-Shot 範例策略

研究顯示應覆蓋 confidence 三個等級，避免過度（> 5 個）：

| 範例 | Confidence | 用途 |
|------|-----------|------|
| 範例 1 | 0.9（高）| 顧問明確建議，有完整 What/Why/How/Evidence |
| 範例 2 | 0.4（低）| 觀察中議題，標註「（持續觀察中）」|
| 範例 3 | 0.65（中）| 部分資訊，有 What/Why/How，Evidence 標註「（未提及）」|

研究來源：[Few-Shot Prompting Guide](https://www.promptingguide.ai/techniques/fewshot)

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

## 14. 評估維度詳解與基準線

### 四個評估維度說明

| 維度 | 問的核心問題 | 評分標準（1-5） |
|------|------------|--------------|
| **Relevance** | 這是真正有價值的 SEO 知識嗎？ | 1=完全無關閒聊；5=高濃度可複用知識 |
| **Accuracy** | A 是否忠實反映原始會議內容？ | 1=明顯錯誤或虛構；5=完全符合來源 |
| **Completeness** | A 是否有足夠深度讓讀者理解並行動？ | 1=只有結論無原因；5=What+Why+How+Evidence 齊全 |
| **Granularity** | Q 的聚焦程度是否恰當？ | 1=問題過於廣泛；5=聚焦單一具體主題 |

### 評估分數要求的完整行動建議

| 維度 | 目標分數 | 當前基準線 | 狀態 | 提升方法 |
|------|---------|----------|------|---------|
| Relevance | ≥ 4.5 | 4.65 | ✅ | 無需調整 |
| Accuracy | ≥ 4.0 | 3.80 | 可改善 | 加入 faithfulness 檢查 |
| **Completeness** | **≥ 4.0** | **3.70** | **⚠️ 優先** | 強化 EXTRACT_SYSTEM_PROMPT（見第 13 節） |
| Granularity | ≥ 4.5 | 4.65 | ✅ | 無需調整 |

### 額外評估指標說明

- **Confidence 校準**：Q&A 的 `confidence` 值應與實際品質相關（高 confidence → 高 Accuracy）
- **Self-contained**：Q 不依賴原始會議就能理解（目前 Granularity 4.65 說明已做好）
- **Actionable**：A 提供具體可執行建議（Completeness 的核心要求）
- **Faithfulness**：A 的內容來自原始文件，不是 AI 自行補充（Accuracy 的核心要求）

---

## 15. 模型選擇決策

### GPT-5 系列全為推理模型（2026-02-27 驗證）

**重要發現**：gpt-5 整個系列（nano / mini / 5.2）**全部都是推理模型**，不存在非推理的 gpt-5 選項。

```python
# 實驗驗證 gpt-5-nano：
response.model = "gpt-5-nano-2025-08-07"
reasoning_tokens = 100  # 全部用於推理，content=""
```

測試結果：

| 模型 | max_tokens | 空回應率 | Category 正確率 |
|------|-----------|---------|--------------|
| gpt-5-mini | 2048 | ~5-10% | **75%** ✅ |
| gpt-5-nano | 2048 | **35%** | 65% ❌ |

→ gpt-5-nano 表現比 gpt-5-mini 更差，原因是 nano 推理 token 佔用比例更高。

### 正確解法：調整 token budget，而非換模型

所有 gpt-5 系列做 JSON 輸出時的必要設定：

```python
# 分類任務：max_completion_tokens 要夠（reasoning + JSON output 共享）
max_completion_tokens=2048  # 分類任務

# 空回應保護（必須）：
if "category_judgment" not in result:
    continue  # skip-empty，不計入統計
```

### 本專案模型選擇總覽

| 任務 | 模型 | 理由 |
|------|------|------|
| Q&A 萃取 | gpt-5.2 | 需要高品質理解與生成 |
| Q&A 合併 | gpt-5.2 | 需要強推理 |
| Q&A 分類 | gpt-5-mini | 省成本，max_tokens=2048 穩定 |
| 週報生成 | gpt-5.2 | 需要深度分析 |
| LLM Judge（品質評估） | gpt-5.2 | 需要推理能力 |
| Retrieval 相關性判斷 | gpt-5-mini | max_tokens=1024 穩定 |
| Embedding | text-embedding-3-small | 語意向量計算 |

---

## 16. Embedding 模型比較與升級時機

### 主流 Embedding 模型比較

| 模型 | 維度 | MTEB 準確度 | 成本 | 語言支援 |
|------|------|-----------|------|---------|
| **text-embedding-3-small**（現用）| 1536 | 75.8% | $0.00002/1K | 多語言 |
| text-embedding-3-large | 3072 | 80.5% | $0.00013/1K（6.5x）| 多語言 |
| Qwen3-Embedding-8B（開源）| 自訂 | MTEB 榜首 | 免費（自架）| 中英混合最佳 |

### 何時考慮升級 Embedding

**現階段維持 text-embedding-3-small**，原因：
- Retrieval MRR = 0.79，Top-1 Precision = 100%
- 目前 KW Hit Rate 54% 的瓶頸不在 embedding 品質，而在搜尋策略（Reranking）

**升級觸發條件**：
1. 實作 Cross-encoder Reranking 後，KW Hit Rate 仍 < 60%
2. 新增非結構化資料來源（PDF、圖片）需要多模態 embedding
3. 若要支援更精準的中英混合搜尋，考慮 Qwen3-Embedding

---

## 17. RAG 框架比較與整合策略

### 主流框架比較

| 框架 | 定位 | 優點 | 缺點 |
|------|------|------|------|
| **自建 pipeline**（現用）| 輕量自定義 | 低依賴、高彈性 | 需要自己維護 |
| LangChain | 工作流編排 | 生態豐富、鏈式組合 | 複雜、版本頻繁變動 |
| LlamaIndex | 文件檢索優化 | Retrieval 提升 35%、支援多種資料源 | 較重 |
| txtai | 輕量無依賴 | 嵌入式、極簡 | 功能受限 |

### 現階段決策：不引入外部框架

**原因**：現有 pipeline 已驗證、穩定，引入框架的收益不值得增加的複雜度。

**未來整合時機**：
- 若需要支援 PDF、資料庫、圖片等多來源 → 考慮 LlamaIndex
- 若需要複雜的多步驟 AI 工作流 → 考慮 LangChain
- 目前只有 Notion Markdown 作為資料源 → 繼續自建

---

## 18. Retrieval 指標說明與 Cross-encoder Reranking

### Retrieval 評估指標詳解

| 指標 | 計算方式 | 直覺理解 | 本專案基準線 |
|------|---------|---------|-----------|
| **MRR**（Mean Reciprocal Rank）| 第一筆正確結果排名的倒數取平均 | 第 1 筆正確 = 1.0；第 2 筆正確 = 0.5 | 0.79 ✅ |
| **NDCG**（Normalized Discounted Cumulative Gain）| 考慮排名位置的累積相關度，越靠前越值錢 | 比 MRR 更細緻 | 未實作 |
| **Hit Rate**（Recall@K）| top-K 結果中有沒有包含正確答案 | Hit@5 = 前 5 筆有沒有 | KW 54% / Category 75% |
| **LLM Top-1 Precision** | top-1 結果是否與查詢真實相關（LLM 判斷）| 最重要的第一筆準不準 | 100% ✅ |

### KW Hit Rate 54% 的問題與 Reranking 方案

**現況**：Bi-encoder（語意搜尋）+ keyword boost → KW Hit Rate 54%

**Cross-encoder Reranking 架構**：

```
[查詢]
  ↓
[Bi-encoder 語意搜尋] → top-50 候選（快速，但精度有限）
  ↓
[Cross-encoder 重排序] → top-5 精排（慢但精準）
  ↓
[最終結果]
```

**效果預期**：Hit Rate 提升 8-15 個百分點（從 54% → 約 62-68%）

**推薦模型**：BGE-reranker-v2-m3
- 開源（Apache 2.0 授權）
- 支援 100+ 語言（含中文）
- 需要新增依賴：`sentence-transformers`

**為什麼還沒實作**：
- 需要新增依賴（增加複雜度）
- 先在 Step 5 evaluation 中做實驗性對比，確認提升幅度再整合進 Step 4
- LLM Top-1 Precision 已是 100%，當下用戶體驗不差

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

| 偏差類型 | 現象 | 避免方法 |
|---------|------|---------|
| 冗長偏差 | 長答案自動得高分 | 強調「精準簡潔也可以得 5 分」 |
| 位置偏差 | 第一個選項偏高 | 固定評分順序，不做對比評估 |
| 自我偏好 | 用 GPT-5.2 評 GPT-5.2 生成的內容 | 可接受，但需注意過度膨脹的分數 |

### 本專案 Judge 模型維持 gpt-5.2

**理由**：
- 研究顯示 gpt-5.2 在評分一致性上表現良好
- 換成 Claude Opus 會增加跨平台複雜度
- 開源 Judge 模型（Prometheus-7B）需要自建推理環境

**改善方向**：不換模型，而是改善 Judge prompt（加入 CoT、反向偏差提示）。

---

## 20. FastAPI RAG API 化：把知識庫包成服務

> 本 session（2026-02-27）實作。把 Step 3 產出的 JSON + npy 包成 HTTP API，不動任何 pipeline 架構。

### 設計原則：無 DB、No ORM、全記憶體

```
# 過度設計（不要做）       # MVP 做法（本專案選擇）
postgres + pgvector     →  numpy 矩陣 @ 向量 = cosine
redis cache             →  python dict，啟動一次載入記憶體
celery task queue       →  FastAPI lifespan 直接載入
```

**決策依據**：703 筆 Q&A × 1536 維 = 約 4MB，遠小於 EC2 記憶體。
資料不變動（pipeline 跑完才更新），不需要即時寫入。

### FastAPI lifespan：啟動時載入資料

```python
# app/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    store.load()          # 載入 qa_final.json + qa_embeddings.npy
    yield                 # 服務存活期間資料保持在記憶體
    # 關閉時 GC 自動回收

app = FastAPI(lifespan=lifespan)
```

**前端類比**：`useEffect(() => { fetchData() }, [])` 的伺服器端版本——只跑一次，結果存在 module-level 變數。

### numpy cosine similarity（不用 pgvector）

```python
# app/core/store.py
# 預先 L2 歸一化，讓點積 = cosine similarity
norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
self.embeddings = embeddings / norms  # shape: (703, 1536)

def search(self, query_vec: np.ndarray, top_k: int = 5):
    scores = self.embeddings @ query_vec  # (703,)，dot product = cosine
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(self.items[i], float(scores[i])) for i in top_idx]
```

**數學**：兩個 L2 歸一化向量的點積 = cosine similarity。
矩陣乘法一次計算全部 703 筆相似度，比 for loop 快 100x+。

### RAG chat 實作模式

```python
# app/core/chat.py
async def rag_chat(message: str, history: list[dict]) -> dict:
    # 1. 把問題 embed
    query_vec = await get_embedding(message)  # AsyncOpenAI

    # 2. 語意搜尋找 context
    hits = store.search(query_vec, top_k=5)

    # 3. 組裝 context 進 system message
    context = format_hits_as_text(hits)
    messages = [
        {"role": "system", "content": SEO_EXPERT_SYSTEM_PROMPT},
        {"role": "system", "content": f"--- 知識庫 ---\n{context}"},
        *history,
        {"role": "user", "content": message},
    ]

    # 4. GPT 生成回答
    resp = await client.chat.completions.create(
        model="gpt-5.2", messages=messages, temperature=0.3
    )
    return {"answer": resp.choices[0].message.content, "sources": sources}
```

**關鍵**：`history` 放在 context 和 user message 之間，讓 GPT 看到對話歷史。
`temperature=0.3`：RAG 問答要準確，不要創意。

### 模組結構

```
app/
├── config.py          # 從環境變數讀設定，不 import pipeline 的 config.py
├── core/
│   ├── store.py       # QAStore singleton：load() / search() / list_qa()
│   └── chat.py        # get_embedding() + rag_chat()
├── routers/
│   ├── search.py      # POST /api/v1/search
│   ├── chat.py        # POST /api/v1/chat
│   └── qa.py          # GET  /api/v1/qa, /qa/{id}, /qa/categories
└── main.py            # lifespan + CORS + include_router
```

**設計原則**：`app/` 自包含，不 import pipeline 的 `utils/` 或 `scripts/`。
日後兩個可以獨立部署。

---

## 21. ECR + EC2 SSM 部署模式

> 本 session（2026-02-27）設計，對應 vocus 現行 infra（與 vocus-web-ui 的 EC2 段相同邏輯）。

### 三種部署選項比較

| 方案 | 複雜度 | 適合場景 |
|------|--------|----------|
| EC2 直接 `docker run` | 低 | 一次性手動部署 |
| **ECR + EC2 SSM（本專案選擇）** | **中** | **內部工具，CI/CD 自動化** |
| ECR + ECS Fargate | 高 | Production，需要 auto-scaling |

### ECR + EC2 SSM 流程

```
git push main
    ↓
GitHub Actions
    ↓
docker build -t seo-insight-api:$TAG .
    ↓
ECR push（AWS 私有 registry）
    ↓
SSM send-command → EC2 執行：
  aws ecr get-login-password | docker login
  docker pull $IMAGE:$TAG
  docker stop seo-insight-api && docker rm seo-insight-api
  docker run -d --name seo-insight-api \
    -p 127.0.0.1:8001:8001 \
    -v /data/output:/app/output:ro \
    -e OPENAI_API_KEY=$KEY \
    $IMAGE:$TAG
```

**SSM 好處**：不需要 SSH 進 EC2，不需要開 22 port，AWS IAM 控制權限。

### Dockerfile 設計要點

```dockerfile
FROM python:3.12-slim        # slim = 沒有不必要的系統套件
WORKDIR /app
COPY requirements_api.txt .  # 先 COPY 依賴，利用 layer cache
RUN pip install --no-cache-dir -r requirements_api.txt
COPY app/ ./app/             # 只 COPY API 程式碼
# output/ 用 volume mount，不進 image（data 與 code 分離）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**`.dockerignore` 必要性**：排除 `output/`、`raw_data/`、`.venv/` 等，
把 268MB image 控制在合理範圍（否則可能超過 1GB）。

### volume mount：data 與 code 分離

```bash
# EC2 上放資料，container 只 COPY code
docker run -v /home/ec2-user/seo-data/output:/app/output:ro ...
#                 ↑ EC2 路徑                  ↑ container 內路徑  ↑ 唯讀
```

**好處**：更新 `qa_final.json`（pipeline 重跑後）只需要 `docker restart`，
不需要重新 build image。

### GitHub Actions 關鍵 Secrets

| Secret | 用途 |
|--------|------|
| `ECR_DOMAIN` | `xxxx.dkr.ecr.ap-northeast-1.amazonaws.com` |
| `EC2_TAG_KEY/VALUE` | 找目標 EC2 的 tag（e.g. `Name=seo-api`）|
| `OUTPUT_DATA_PATH` | EC2 上的 data 路徑 |

**EC2 所需 IAM 角色**：`ecr:GetAuthorizationToken` + `ecr:BatchGetImage` + SSM Agent 啟動。

