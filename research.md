# SEO QA Pipeline 技術教學

> 專為純前端開發者設計。每個概念都會先給「前端你已知的對應物」，再解釋新東西。
> 本文件同步記錄本專案用到的所有技術決策。

---

## 目錄

1. [Python vs JavaScript](#1-python-vs-javascript)
2. [腳本與 CLI](#2-腳本與-cli)
3. [API 呼叫（你已經會了）](#3-api-呼叫你已經會了)
4. [JSON 與檔案持久化](#4-json-與檔案持久化)
5. [Pipeline：資料流水線](#5-pipeline資料流水線)
6. [LLM 與 Prompt](#6-llm-與-prompt)
7. [Token：AI 的計費單位](#7-token-ai-的計費單位)
8. [Structured Output：讓 AI 填表格](#8-structured-output讓-ai-填表格)
9. [Embedding：語意指紋](#9-embedding語意指紋)
10. [Cosine Similarity：計算相似度](#10-cosine-similarity計算相似度)
11. [RAG：給 AI 開卷考試](#11-rag給-ai-開卷考試)
12. [LLM-as-Judge：用 AI 評估 AI](#12-llm-as-judge用-ai-評估-ai)
13. [Reasoning Model：會思考的 AI](#13-reasoning-model會思考的-ai)
14. [本專案完整架構](#14-本專案完整架構)

---

## 1. Python vs JavaScript

### 你已知的對應物

| JavaScript | Python |
|-----------|--------|
| `console.log("hi")` | `print("hi")` |
| `function add(a, b) {}` | `def add(a, b):` |
| `const x = 1` | `x = 1` |
| `// comment` | `# comment` |
| `{}` 大括號定義區塊 | **縮排**定義區塊 |
| `node script.js` | `python script.py` |
| `import x from 'y'` | `from y import x` |
| `package.json` | `pyproject.toml` |
| `npm install` | `pip install` |

### 最關鍵的差異：縮排就是語法

```python
# JavaScript 你可以這樣寫（醜但合法）：
# function add(a,b){return a+b}

# Python 不行，縮排是強制的
def add(a, b):
    return a + b   # ← 這個縮排不能少
```

### 型別提示（Type Hints）

Python 是動態語言，但可以加型別提示（像 TypeScript 的感覺）：

```python
# 不加型別提示（像 JavaScript）
def greet(name):
    return f"Hello, {name}"

# 加型別提示（像 TypeScript）
def greet(name: str) -> str:
    return f"Hello, {name}"
```

本專案大量使用型別提示，閱讀時看到 `list[dict]`、`str | None` 是正常的。

---

## 2. 腳本與 CLI

### 前端對應：npm scripts

```json
// package.json
{
  "scripts": {
    "build": "next build",
    "dev": "next dev --port 3000"
  }
}
```

Python 直接在終端機跑腳本，加 `--` 參數：

```bash
# 前端
npm run build
npm run dev -- --port 3001

# Python（本專案）
python scripts/run_pipeline.py
python scripts/run_pipeline.py --step 2 --limit 3
```

### argparse：解析 CLI 參數

前端你用 `process.argv`，Python 用 `argparse`：

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--step", type=int)      # --step 2
parser.add_argument("--limit", type=int)     # --limit 3
parser.add_argument("--force", action="store_true")  # --force（布林旗標）

args = parser.parse_args()
print(args.step)   # 2
print(args.force)  # True / False
```

---

## 3. API 呼叫（你已經會了）

### 前端對應：fetch()

```javascript
// 前端：fetch API
const res = await fetch("https://api.notion.com/v1/pages/123", {
  headers: { "Authorization": `Bearer ${token}` }
});
const data = await res.json();
```

```python
# Python：requests（最常用的 HTTP 套件）
import requests

res = requests.get(
    "https://api.notion.com/v1/pages/123",
    headers={"Authorization": f"Bearer {token}"}
)
data = res.json()   # 一樣的！
```

### 環境變數：.env 檔（一模一樣）

```bash
# .env（前端 Next.js 或 Python 都一樣）
OPENAI_API_KEY=sk-xxx
NOTION_API_KEY=secret_xxx
```

```python
# Python 讀取方式
from dotenv import load_dotenv
import os

load_dotenv()  # 讀取 .env 檔
api_key = os.getenv("OPENAI_API_KEY")
```

```javascript
// 前端讀取方式（Next.js）
const apiKey = process.env.OPENAI_API_KEY;
```

---

## 4. JSON 與檔案持久化

### 前端對應：localStorage / sessionStorage

前端你用 localStorage 儲存資料，Python 直接讀寫 JSON 檔：

```python
import json
from pathlib import Path

# 寫入 JSON（相當於 localStorage.setItem）
data = {"qa_pairs": [{"question": "什麼是 SEO？", "answer": "..."}]}
Path("output/qa_final.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

# 讀取 JSON（相當於 JSON.parse(localStorage.getItem(...))）
data = json.loads(Path("output/qa_final.json").read_text(encoding="utf-8"))
```

### Path 物件（比字串拼接更安全）

```python
from pathlib import Path

# 不要這樣拼接路徑（容易出錯）
path = "output" + "/" + "qa_final.json"

# 用 Path（自動處理 / 和 \ 的差異）
path = Path("output") / "qa_final.json"
path.exists()        # 檢查是否存在
path.mkdir()         # 建立目錄
path.read_text()     # 讀取內容
path.write_text()    # 寫入內容
```

---

## 5. Pipeline：資料流水線

### 前端對應：Promise chain / async/await 串接

```javascript
// 前端 Promise chain
fetchData()
  .then(parseJson)
  .then(filterResults)
  .then(saveToStorage)
```

本專案的 pipeline 是把「每個步驟的結果存成 JSON 檔」，下一步再讀進來：

```
Step 1: Notion API → raw_data/notion_json/*.json
   ↓ 存檔
Step 2: 讀 JSON → OpenAI 萃取 Q&A → output/qa_per_meeting/*.json
   ↓ 存檔
Step 3: 讀 Q&A → 去重 + 分類 → output/qa_final.json
   ↓ 存檔
Step 4: 讀 qa_final.json → 搜尋 + 生成報告
Step 5: 讀 qa_final.json → 評估品質
```

### 為什麼每步都存檔？

- **中斷後可接續**：跑到一半 Ctrl+C，下次從上次停的地方繼續
- **增量處理**：已處理過的跳過，只處理新的
- **除錯方便**：每步的輸出都看得到，不用重跑整條鏈

這就是本專案的「增量機制」，等同於前端的 SWR/React Query 快取策略。

---

## 6. LLM 與 Prompt

### LLM 是什麼

LLM（Large Language Model）= GPT、Claude 等 AI 模型。
你傳一段文字進去（prompt），它回傳一段文字出來（completion）。

```python
# 最簡單的 OpenAI 呼叫（像 fetch + 解析 JSON）
from openai import OpenAI

client = OpenAI(api_key="sk-xxx")

response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[
        {"role": "system", "content": "你是 SEO 專家"},
        {"role": "user",   "content": "什麼是 canonical tag？"},
    ]
)

answer = response.choices[0].message.content
# answer = "Canonical tag 是用來告訴搜尋引擎..."
```

### System vs User message

```
system：給 AI 設定角色（"你是一個 SEO 專家，只用繁體中文回答"）
user：  實際的問題（"為什麼我的 CTR 一直下降？"）
```

前端類比：`system` 像元件的 props，`user` 像使用者的 input。

### Prompt 工程

Prompt 就是「你給 AI 的指令」。寫好的 prompt 非常重要：

```python
# 差的 prompt（AI 不知道你要什麼格式）
"幫我從這段文字裡找問題和答案"

# 好的 prompt（明確格式、明確角色、明確要求）
"""
你是 SEO 知識萃取專家。
從以下會議紀錄中，萃取出 3-8 個有價值的 Q&A。

要求：
- Q 必須是可以獨立理解的問題（不需要看原文）
- A 必須包含具體建議和原因
- 只萃取 SEO 相關知識，跳過行政內容

回傳格式：JSON 陣列，每個元素包含 question、answer、keywords
"""
```

本專案所有 prompt 定義在 `utils/openai_helper.py`。

---

## 7. Token：AI 的計費單位

### 前端對應：API 呼叫次數計費

前端你可能知道「每次 API 呼叫算一次費用」。
LLM 更細：**計算你傳入和收到的「字數」**，單位叫 token。

### Token 是什麼

大概 1 token ≈ 0.75 個英文單字，或 1 個中文字：

```
"Hello World"    → 2 tokens
"你好世界"        → 4 tokens（每個中文字約 1 token）
"CTR"            → 1 token
"core web vitals" → 3 tokens
```

### 為什麼本專案會遇到 token 問題（BUG-002）

今天我們修的 BUG-002：

```python
# 推理模型（gpt-5-mini）有特殊行為：
# 它會先「思考」（reasoning），再輸出答案
# 思考過程也佔用 token

max_completion_tokens=256   # ← 256 tokens 太少
# 推理：200 tokens 用於思考
# 輸出：只剩 56 tokens，不夠完成 JSON
# 結果：content = ""（空字串）

max_completion_tokens=1024  # ← 修復後，1024 tokens 夠用
```

### Token 費用估算

| 模型 | 每 1M tokens | 本專案用途 |
|------|-------------|----------|
| gpt-5-mini | 便宜 | 分類、評估 |
| gpt-5.2 | 較貴 | 萃取、合併、週報生成 |
| text-embedding-3-small | 極便宜 | embedding（向量化） |

---

## 8. Structured Output：讓 AI 填表格

### 問題

AI 預設回傳自由格式文字，但程式需要讀取固定格式資料：

```
問題：「請評估這個 Q&A 的品質」

AI 自由回答（沒辦法 parse）：
"這個 Q&A 品質不錯，相關性很高，大約 4 分左右，完整性稍微欠缺..."

AI 結構化回答（程式可以直接用）：
{"relevance": {"score": 4, "reason": "..."}, "completeness": {"score": 3, ...}}
```

### JSON Schema（強制 AI 回傳固定格式）

就像 TypeScript interface，你先定義格式，AI 只能照格式回答：

```python
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "qa_eval",
            "strict": True,           # ← 強制嚴格符合格式
            "schema": {
                "type": "object",
                "properties": {
                    "score": {
                        "type": "integer"  # ← 只能是整數
                    },
                    "reason": {
                        "type": "string"
                    }
                },
                "required": ["score", "reason"],
                "additionalProperties": False  # ← 不能有額外欄位
            }
        }
    }
)

# 保證拿到的是合法 JSON，不是自由文字
result = json.loads(response.choices[0].message.content)
print(result["score"])   # 4
```

### 本專案 BUG-001 的根因

今天修的 BUG-001 也和這裡有關：

```python
content = response.choices[0].message.content or "{}"

# gpt-5-mini（推理模型）有時 content 回傳空字串 ""
# "" or "{}"  →  "{}"
# json.loads("{}")  →  {}（空 dict）
# {} 沒有 "category_judgment" 欄位
# 但還是被計入 total
# 結果：Category 正確率顯示 10%（其實是 75%）
```

---

## 9. Embedding：語意指紋

### 這是本專案最「不前端」的概念

Embedding = 把一段文字轉換成一串數字（向量）。

### 為什麼需要這個

關鍵字搜尋的問題：

```
查詢：「網站速度影響排名嗎？」
關鍵字搜尋找：包含「速度」「排名」的文章 ✅
關鍵字搜尋找不到：「Core Web Vitals 與 SEO 的關係」❌（沒有「速度」「排名」這兩個字）
```

語意搜尋可以找到意思相近的，不只是字面上的。

### 用地圖來理解

想像把每個句子放在一個多維空間的地圖上：

```
「Core Web Vitals 與 SEO 的關係」  ← 放在這個位置
「網站速度影響排名嗎？」            ← 放在附近的位置（意思相近）
「如何做內部連結？」               ← 放在很遠的位置（不同主題）
```

Embedding 就是這個「地圖上的座標」，是一個有 1536 個數字的列表：

```python
# 呼叫 OpenAI Embedding API
from openai import OpenAI

client = OpenAI()
result = client.embeddings.create(
    model="text-embedding-3-small",
    input="Core Web Vitals 與 SEO 的關係"
)

vector = result.data[0].embedding
# vector = [0.023, -0.156, 0.891, ..., 0.042]  ← 1536 個數字
print(len(vector))  # 1536
```

本專案在 Step 3 計算所有 703 筆 Q&A 的 embedding，存成 `qa_embeddings.npy`。

---

## 10. Cosine Similarity：計算相似度

### 前端對應：沒有直接對應，但原理不難

兩個 embedding 向量有多「相近」？用 Cosine Similarity 計算。

結果是 -1 到 1 之間的數字：
- `1.0` = 完全相同（意思一樣）
- `0.88` = 非常相似（本專案的去重門檻）
- `0.5` = 有點相關
- `0.0` = 完全無關
- `-1.0` = 意思相反

### 去重的原理

本專案 Step 3 的去重（`SIMILARITY_THRESHOLD = 0.88`）：

```python
import numpy as np

# 假設我們有兩個 Q&A 的 embedding
qa1_vector = [0.1, 0.9, 0.3, ...]   # Q: Discover 流量下降原因？
qa2_vector = [0.1, 0.8, 0.4, ...]   # Q: Google Discover 為什麼流量減少？

# 計算相似度
similarity = cosine_similarity(qa1_vector, qa2_vector)
# similarity = 0.97（非常像！）

if similarity >= 0.88:
    # 這兩個問題意思一樣，合併成一筆
    merge_qa_pairs(qa1, qa2)
```

---

## 11. RAG：給 AI 開卷考試

### RAG = Retrieval Augmented Generation

問題：AI（gpt-5.2）不知道你的 SEO 會議內容。
解法：先搜尋相關知識，再把搜尋結果交給 AI 一起回答。

### 比喻：閉卷 vs 開卷

```
❌ 閉卷考試（沒有 RAG）：
User: 「上次開會說 canonical 設定有問題，怎麼解決？」
AI: 「我不知道你上次開什麼會...」（AI 沒有你的私人資料）

✅ 開卷考試（有 RAG）：
Step 1 - 搜尋：在 703 筆 Q&A 中找到 5 筆 canonical 相關的知識
Step 2 - 組裝：把這 5 筆 Q&A 塞進 prompt
Step 3 - 生成：AI 看著這些知識回答，有依據
```

### 本專案 Step 4 的 RAG 流程

```
Google Sheets 指標異常
    ↓
偵測到「有效頁面數下降 5%」
    ↓
Embed 查詢：「有效頁面數下降 Coverage 索引」
    ↓
語意搜尋 703 筆 Q&A → 找到最相關的 5 筆
    ↓
組裝 prompt：「根據以下 SEO 知識庫：[5 筆 Q&A]，分析這個異常並給建議」
    ↓
gpt-5.2 生成週報段落
```

### Hybrid Search：語意 + 關鍵字

本專案不只用語意搜尋，還加了關鍵字 boost：

```python
# 先算語意相似度分數
scores = cosine_similarity(query_vector, all_qa_vectors)

# 再加關鍵字 boost（Q&A 的 keywords 出現在查詢裡就加分）
for i, qa in enumerate(qa_pairs):
    keyword_hits = sum(1 for kw in qa["keywords"] if kw in query)
    if keyword_hits > 0:
        scores[i] += 0.08 * min(keyword_hits, 3)

# 取分數最高的前 5 筆
top_5 = argsort(scores)[::-1][:5]
```

---

## 12. LLM-as-Judge：用 AI 評估 AI

### 前端對應：用 ESLint 檢查程式碼（只是換成 AI）

傳統評估方式：人工看 30 筆 Q&A，打分數。
LLM-as-Judge：讓另一個 AI 看 Q&A，幫你打分數。

```python
# 你的 Q&A
qa = {
    "question": "Discover 流量下降的原因是什麼？",
    "answer": "可能是內容品質、AMP 設定問題..."
}

# 讓 gpt-5.2 當評審
judge_prompt = """
你是 Q&A 品質評審員。請評估這個 Q&A：
- Relevance（1-5）：是否涵蓋有價值的 SEO 知識？
- Completeness（1-5）：答案是否有足夠細節？
"""

score = ask_gpt(judge_prompt, qa)
# score = {"relevance": 4, "completeness": 3, "reason": "答案缺少具體建議"}
```

### 為什麼今天的評估數字不對

今天修的兩個 bug 都是評審系統的問題，不是 Q&A 本身的問題：

- BUG-001：分類評審（gpt-5-mini）大部分沒有成功回應，讓分母虛增
- BUG-002：Retrieval 評審（gpt-5-mini）token 不夠，全部輸出空字串

**修完後的真實基準線**：
- Category 正確率：75%（不是 10%）
- Top-1 Precision：100%（不是 10%）

---

## 13. Reasoning Model：會思考的 AI

### 標準模型 vs 推理模型

```
標準模型（GPT-3.5 時代）：
User: 什麼是 2 + 2？
AI: 4

推理模型（o1, o3, gpt-5-mini 等）：
User: 什麼是 2 + 2？
AI: <thinking>
    讓我想一想...2 加 2...
    先從 2 開始，再加 2...
    1, 2, 3, 4... 是 4
    </thinking>
AI: 4
```

### 對程式開發的影響

推理模型的「思考過程」也佔用 token，對程式有兩個影響：

**1. `max_completion_tokens` 要設得更大**
```python
# 標準模型：256 tokens 就夠回傳一個 JSON
# 推理模型：256 tokens 可能全用在思考上，輸出為空
max_completion_tokens=256   # ❌ 推理模型不夠
max_completion_tokens=1024  # ✅ 足夠
```

**2. `content` 可能為空（本專案 BUG-001/002 的根因）**
```python
content = response.choices[0].message.content
# 標準模型：永遠有內容
# 推理模型：token 用完時，content = ""（空字串）

# 防禦寫法：
if not content:
    print("⚠️ 推理模型回傳空內容")
    return fallback_value
```

---

## 14. 本專案完整架構

### 全景圖

```
資料來源：Notion 會議紀錄（87 份，2023-2026）
                    ↓
[Step 1] fetch_notion.py
  - Notion API → 下載 JSON + 轉 Markdown
  - 增量機制：只抓 last_edited_time 有更新的
                    ↓ raw_data/markdown/*.md
[Step 2] extract_qa.py
  - 讀 Markdown → gpt-5.2 萃取 Q&A → JSON
  - 長文分段：超過 6000 tokens 就切段分別萃取
                    ↓ output/qa_per_meeting/*.json
[Step 3] dedupe_classify.py
  - Embedding（text-embedding-3-small）計算每個 Q&A 的向量
  - Cosine Similarity 找相似的 Q&A（門檻 0.88）
  - gpt-5.2 合併相似 Q&A
  - gpt-5-mini 分類（10 種類別 + difficulty + evergreen）
                    ↓ output/qa_final.json + qa_embeddings.npy
[Step 4] generate_report.py
  - 讀 Google Sheets 指標（TSV 格式）
  - 偵測異常指標（月趨勢 ± 閾值）
  - RAG：語意搜尋相關 Q&A → gpt-5.2 生成週報
                    ↓ output/report_YYYYMMDD.md
[Step 5] evaluate.py
  - LLM-as-Judge：gpt-5.2 評 Q&A 品質（4 維度）
  - 分類評估：gpt-5-mini 驗分類準確度
  - Retrieval 評估：語意搜尋 + LLM 判斷相關性
                    ↓ output/eval_report.json
```

### 模型選擇決策

```
高品質理解/生成 → gpt-5.2（貴但準）
  ├── Q&A 萃取（需要理解複雜會議紀錄）
  ├── Q&A 合併（需要推理哪些可以合併）
  ├── 週報生成（需要深度分析）
  └── LLM Judge（需要準確評分）

結構化輸出/分類 → gpt-5-mini（便宜夠用）
  ├── 分類 703 筆 Q&A（重複性高，mini 夠）
  └── Retrieval 相關性判斷（簡單二元判斷）

向量計算 → text-embedding-3-small（極便宜）
  └── 計算所有 Q&A 的 embedding
```

### 今天修的問題

**本質**：gpt-5-mini 是推理模型，有以下行為：
1. 思考佔用 token → `max_completion_tokens` 需要更大
2. Token 超限時 content 回傳 `""` → 程式要做空值檢查

**結果**：兩個評估指標從假的「10%」恢復成真實的「75%」和「100%」。

---

## 延伸閱讀

- [OpenAI Embeddings 官方文件](https://platform.openai.com/docs/guides/embeddings)
- [RAG 概念介紹](https://platform.openai.com/docs/guides/retrieval-augmented-generation)
- [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- Python 相關：參考本文件旁邊的 python-patterns skill
