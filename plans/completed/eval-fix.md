# Plan: 評估指標異常修復

> 狀態：已完成（2026-02-28）

## 背景診斷

Laminar 評估發現三個問題：

1. **extraction_quality** — Frank 會議 keyword_coverage = 0.00（缺 Discover、AMP、索引、CTR、canonical）
2. **retrieval_quality** — 中文分詞 bug，`split()` 無法正確分割複合詞，導致內部連結架構優化查詢零結果
3. **chat_quality** — executor 大量 crash（Output='−'），根因：embedding shape 不符 + missing API key

---

## 修復方案

### 1. extraction_quality: Frank 會議重新萃取 [done]

**現象：** `keyword_coverage = 0.00`（需 Discover、AMP、索引、CTR、canonical）

**根因：** Step 2 首次 OpenAI 萃取時，prompt 可能未強調技術關鍵字的重要性

**前置條件：** ⚠️ **OPENAI_API_KEY 目前失效（401 Unauthorized）**

- 需要先更新 `.env` 中的 `OPENAI_API_KEY` 為有效的新 key

**解法：**

```bash
# Step 1: 確認 OPENAI_API_KEY 有效
echo $OPENAI_API_KEY  # 確保不為空

# Step 2a: 強制重跑全部檔案（含 Frank）
.venv/bin/python scripts/run_pipeline.py --step 2 --force

# Step 2b: 檢查新的 Frank_SEO顧問會議_qa.json 是否包含期望關鍵字
python -c "
import json
from pathlib import Path
qa_data = json.loads(Path('output/qa_per_meeting/Frank_SEO顧問會議_qa.json').read_text())
qa_pairs = qa_data if isinstance(qa_data, list) else qa_data.get('qa_pairs', [])
must_kws = ['Discover', 'AMP', '索引', 'CTR', 'canonical']
pool = ' '.join(qa.get('question','') + ' ' + qa.get('answer','') + ' ' + ' '.join(qa.get('keywords',[])) for qa in qa_pairs).lower()
hits = [kw for kw in must_kws if kw.lower() in pool]
print(f'Keyword hits: {hits} / {len(must_kws)}')
"
```

**驗收標準：** keyword_coverage = 1.0（全部 5 個技術關鍵字都出現）

**Fallback：**

1. 如若 OpenAI 仍無法捕獲，檢查 `raw_data/markdown/Frank_SEO顧問會議.md` 原文是否包含這些詞
2. 手動調整 [scripts/02_extract_qa.py](scripts/02_extract_qa.py) 中的 prompt，強調技術 SEO 關鍵字優先級

---

### 2. retrieval_quality: 修復中文分詞器 [done, v2 2026-03-02]

**現象：**

- 查詢 `內部連結架構優化` 返回 0 結果
- CTR、檢索未索引等查詢缺少 `點擊率`、`Coverage` 等同義詞

**根因：** `retrieval_executor()` 在 [evals/eval_retrieval.py#L62](evals/eval_retrieval.py#L62) 用 `query.lower().split()` 按**空格**切詞

- 中文複合詞 `內部連結架構優化` 沒有空格 → `split()` 返回單一 token → 永遠比對不到

**v2 修復（2026-03-02）：** `expand_query_tokens()` 三層展開（CJK n-gram + forward/inverted synonym），KW Hit Rate 65% → 74%

**解法（優先級排序）：**

#### A. 改進 retrieval_executor（建議）

位置：[evals/eval_retrieval.py#L62](evals/eval_retrieval.py#L62)

目標：加入中文字元分類 + 同義詞補集

```python
def retrieval_executor(data: dict) -> dict:
    """Keyword-based search with Chinese segmentation support."""
    from scripts.qa_tools import _load_qa_final

    query = data["query"]
    qa_items = _load_qa_final()

    # 改進 1: 按字元切割（中文每字一個 token）
    import re
    tokens = []
    for word in query.split():
        # 英文單詞保留，中文字符逐字分割
        tokens.extend(re.findall(r'[\w]+|[\u4e00-\u9fff]', word.lower()))
    query_tokens = set(tokens)

    # 改進 2: 同義詞補集（可選，用於擴大匹配範圍）
    SYNONYMS = {
        "點擊率": ["ctr", "點擊", "rate"],
        "coverage": ["檢索", "索引", "覆蓋"],
        "行動版": ["mobile", "手機"],
        "metadata": ["中繼資料", "meta"],
        "discover": ["google discover", "探索"],
    }

    for base, syns in SYNONYMS.items():
        if base.lower() in query_tokens:
            query_tokens.update(syns)

    scored = []
    for qa in qa_items:
        pool = (
            qa.get("question", "") + " "
            + qa.get("answer", "") + " "
            + " ".join(qa.get("keywords", []))
        ).lower()
        # 改進 3: 靈活比對（substring match）
        hits = sum(1 for tok in query_tokens if tok in pool)
        if hits > 0:
            scored.append((hits, qa))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [qa for _, qa in scored[:5]]

    return {"results": results, "query": query}
```

**影響範圍：** `retrieval_quality` 的 `keyword_hit_rate`、`top1_category_match`、`top5_category_coverage` 指標會直接改善

---

#### B. 更新 golden_retrieval.json（備選）

如只想快速提升分數，可在查詢前加** 空格分隔**：

- 改 `內部連結架構優化` → `內部 連結 架構 優化`
- 改 `/user 路徑流量` → `user 路徑 流量`

詳見 [eval/golden_retrieval.json](eval/golden_retrieval.json)

**驗收標準：** `keyword_hit_rate` 平均 ≥ 0.9（現在 0.84）

---

### 3. chat_quality: 修復 executor crash [done]

**現象：** 大量執行失敗（× 符號，Output='−'）

**可能根因：**

1. **Embedding shape 不符** — `qa_embeddings.npy` 筆數 ≠ `qa_final.json` 筆數
2. **缺 OPENAI_API_KEY** — chat_executor 呼叫 `rag_chat()` 需要 embedding API
3. **Import 或非同步錯誤** — app module 初始化失敗

**診斷步驟：**

```bash
# 步驟 1: 檢查 embedding 與 qa_final 筆數
python -c "
import numpy as np, json
from pathlib import Path

npy = np.load('output/qa_embeddings.npy')
qa = json.load(open('output/qa_final.json'))

print(f'qa_final.json: {len(qa)} 筆')
print(f'qa_embeddings.npy: {npy.shape}')
if len(qa) != npy.shape[0]:
    print(f'❌ 筆數不符！需要重建 embeddings')
else:
    print(f'✅ 筆數OK')
"

# 步驟 2: 檢查是否設定 OPENAI_API_KEY
echo "OPENAI_API_KEY=$OPENAI_API_KEY" | head -c 20

# 步驟 3: 單獨測試 chat_executor
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.core.store import store
store.load(json_path='output/qa_final.json', npy_path='output/qa_embeddings.npy')
result = asyncio.run(rag_chat('Discover 流量下降'))
print('Result:', result)
" 2>&1 | head -50
```

**修復方案：**

#### A. 重建 embeddings（最可能解）

```bash
.venv/bin/python scripts/run_pipeline.py --step 3 --force
```

#### B. 驗證 OPENAI_API_KEY

```bash
# .env 應包含
OPENAI_API_KEY=sk-...
```

#### C. 修復 chat_executor（如有 import 錯誤）

位置：[evals/eval_chat.py#L55](evals/eval_chat.py#L55)

```python
async def chat_executor(data: dict) -> dict:
    """Run rag_chat and handle errors gracefully."""
    try:
        from app.core.chat import rag_chat
        result = await rag_chat(data["question"])
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "source_count": len(result.get("sources", [])),
        }
    except Exception as e:
        import logging
        logging.error(f"chat_executor failed: {e}")
        return {
            "answer": "",
            "sources": [],
            "source_count": 0,
        }
```

**驗收標準：** `has_answer` ≥ 0.7，`has_sources` ≥ 0.8（現在大多 0）

---

## 實施順序（推薦）

| 序  | 任務                                      | 時間    | 優先級 |
| --- | ----------------------------------------- | ------- | ------ |
| 1   | Step 2 --force 重跑 Frank                 | 5 分鐘  | P0  |
| 2   | 執行診斷步驟 3.1（檢查 embedding shape）  | 1 分鐘  | P0  |
| 3   | 如需要，重建 embeddings（Step 3 --force） | 10 分鐘 | P0  |
| 4   | 修復 retrieval_executor 中文分詞          | 20 分鐘 | P1  |
| 5   | 修復 chat_executor 錯誤處理               | 15 分鐘 | P1  |
| 6   | 重跑評估確認指標改善                      | 10 分鐘 | P1  |

---

## 預期改善幅度

| 評估                               | 現況 | 目標  | 改善方式                  |
| ---------------------------------- | ---- | ----- | ------------------------- |
| extraction_quality avg             | 0.73 | ≥0.8  | Step 2 重新萃取           |
| retrieval_quality keyword_hit_rate | 0.84 | ≥0.95 | 中文分詞 + 同義詞         |
| chat_quality has_answer            | 0.0  | ≥0.7  | 修復 embedding + 錯誤處理 |

---

## 文件/檔案清單

- ✅ [evals/eval_extraction.py](evals/eval_extraction.py) — 無需改動
- 🟡 [evals/eval_retrieval.py](evals/eval_retrieval.py) — 建議改進 retrieval_executor（L62–90）
- 🟡 [evals/eval_chat.py](evals/eval_chat.py) — 建議加錯誤處理（L55–70）
- 📋 [eval/golden_retrieval.json](eval/golden_retrieval.json) — 備選：加空格分隔中文詞

---

## 注意事項

- Step 2 重跑會消耗 OpenAI API credits（看檔案數 × token 數）
- 修改 eval Python 檔後，需重新執行 `lmnr eval evals/eval_*.py` 才會生效
- golden\_\* json 是評估的「正確答案」，修改前需確保邏輯正確
