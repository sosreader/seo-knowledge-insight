# /evaluate-qa-local — Q&A 品質評估（不需要 OpenAI）

你是 LLM-as-Judge，直接評估 Q&A 品質。全程不需要 OpenAI API key。

---

## 執行步驟

### Step A：抽樣

```bash
.venv/bin/python scripts/qa_tools.py eval-sample --size 20 --seed 42 --with-golden
```

將輸出的 JSON 讀入，記為 `eval_sample`。

### Step B：四維度評分（你是 Judge）

對 `eval_sample.items` 中的每筆 Q&A，分 4 批（每批 5 筆）逐批評分。

**評分標準**（與 OpenAI 版完全一致）：

1. **Relevance（相關性）**：Q&A 是否涵蓋真正有價值的 SEO 知識
   - 1 分：萃取了行政內容、閒聊或無意義的對話
   - 3 分：相關但過於表面或偏離核心議題
   - 5 分：精準捕捉到會議的關鍵 SEO 知識點

2. **Accuracy（準確性）**：A 的內容是否合理且無明顯虛構
   - 1 分：明顯失真或虛構了不可能存在的資訊
   - 3 分：大致正確但有模糊或不精確之處
   - 5 分：論述合理，無明顯問題

3. **Completeness（完整性）**：A 是否包含足夠的上下文讓讀者理解
   - 1 分：答案片段化，缺少關鍵脈絡
   - 3 分：有 What/Why 但 How 完全缺失
   - 4 分：How 含 `[補充]` 標記的通用 SEO 標準步驟（不應視為幻覺）
   - 5 分：What/Why/How 齊全，且 How 有具體到此次情境的步驟

4. **Granularity（粒度）**：Q 的範圍是否恰當
   - 1 分：多個不相關主題塞在一個 Q 裡
   - 3 分：粒度偏大或偏小，但尚可
   - 5 分：一個 Q 聚焦一個主題，可獨立理解

額外標記：
- **confidence_calibration**：confidence 分數是否與內容確定度一致（合理 / 偏高 / 偏低）
- **self_contained**：Q 是否不需要看過原會議就能理解（true / false）
- **actionable**：A 是否提供了可執行的建議（是 / 部分 / 否）

每批評完後輸出 JSON 格式：
```json
[
  {
    "stable_id": "...",
    "relevance": {"score": 5, "reason": "..."},
    "accuracy": {"score": 4, "reason": "..."},
    "completeness": {"score": 4, "reason": "..."},
    "granularity": {"score": 5, "reason": "..."},
    "confidence_calibration": "合理",
    "self_contained": true,
    "actionable": "是"
  }
]
```

**重要**：answer 超過 500 字時只看前 500 字。

### Step C：分類評估

對 `eval_sample` 中有 `expected_category` 的筆目（golden 匹配），逐一判斷：

分類選項：索引與檢索、連結策略、搜尋表現分析、內容策略、Discover與AMP、技術SEO、GA與數據追蹤、平台策略、演算法與趨勢、其他

對每筆輸出：
```json
{
  "stable_id": "...",
  "category_judgment": "correct|incorrect|borderline",
  "suggested_category": "...",
  "difficulty_reasonable": true,
  "evergreen_reasonable": true,
  "reason": "..."
}
```

### Step D：Retrieval 評估

```bash
.venv/bin/python scripts/qa_tools.py eval-retrieval-local
```

讀取輸出的 JSON。對每個 case 的 `top1_question` + `top1_answer`，判斷是否與 `query` 相關：
- 回答 `relevant` 或 `not_relevant`

### Step E：彙整結果並儲存

將 Step B/C/D 的結果彙整為以下 JSON 結構：

```json
{
  "sample_size": 20,
  "generation": {
    "relevance": 4.XX,
    "accuracy": 4.XX,
    "completeness": 3.XX,
    "granularity": 4.XX
  },
  "retrieval": {
    "kw_hit_rate": 0.XX,
    "mrr": 0.XX,
    "llm_top1_precision": 0.XX,
    "search_engine": "keyword"
  },
  "classification": {
    "category_accuracy": 0.XX,
    "difficulty_accuracy": 0.XX,
    "evergreen_accuracy": 0.XX
  },
  "details": {
    "generation_results": [...],
    "classification_results": [...],
    "retrieval_llm_judgments": [...]
  }
}
```

generation 各維度為所有筆的平均分。classification 各 accuracy 為比率。
retrieval 的 kw_hit_rate/mrr 取自 Step D 的 qa_tools 輸出，llm_top1_precision 為你判斷 relevant 的比率。

寫入 `/tmp/eval_local_result.json`，然後：

```bash
.venv/bin/python scripts/qa_tools.py eval-save --input /tmp/eval_local_result.json --extraction-engine claude-code
```

### Step F：對比報告

```bash
.venv/bin/python scripts/qa_tools.py eval-compare
```

閱讀輸出，產出以下格式報告：

```
## 評估結果（{日期}，provider: claude-code）

### 生成品質
| 維度 | 本次 | 基準線 | 變化 |
|------|------|--------|------|
| Relevance | X.XX | 4.80 | ... |
| Accuracy  | X.XX | 3.95 | ... |
| Completeness | X.XX | 3.85 | ... |
| Granularity | X.XX | 4.75 | ... |

### Retrieval 品質（搜尋引擎：關鍵字模式）
- KW 命中率：XX%（基準：78%）
- MRR：X.XX（基準：0.75）
- LLM Top-1 Precision：XX%（基準：100%）

### 分類品質
- Category 正確率：XX%（基準：68%）
- Difficulty 合理率：XX%（基準：95%）
- Evergreen 合理率：XX%（基準：75%）

### 結論
{整體評估是否達標；若有明顯差異標注搜尋引擎不同}
```
