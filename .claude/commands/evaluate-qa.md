# /evaluate-qa — Q&A 品質評估（需要 OpenAI）

呼叫 `scripts/05_evaluate.py` 執行品質評估，並解讀結果與基準線比較。

> **注意**：評估本身需要 OpenAI API key（用於 LLM-as-Judge）。
> 解讀結果、對比基準線由 Claude Code 負責。

---

## 用法

```
/evaluate-qa                          # 標準評估（30 筆）
/evaluate-qa --sample 50             # 更大樣本
/evaluate-qa --extraction-engine claude-code   # 標記萃取引擎為 Claude Code
/evaluate-qa --update-baseline       # 若超過基準線 +0.05 則更新基準線
```

---

## 執行步驟

### Step A：執行評估

```bash
.venv/bin/python scripts/05_evaluate.py \
  --sample 30 \
  --eval-retrieval \
  --provider openai \
  --extraction-engine <openai|claude-code> \
  [--update-baseline]
```

### Step B：查看 eval-compare

```bash
.venv/bin/python scripts/qa_tools.py eval-compare
```

### Step C：解讀結果

閱讀評估輸出，按以下結構報告：

```
## 評估結果（{日期}）

### 生成品質
| 維度 | 本次 | 基準線 | 變化 |
|------|------|--------|------|
| Relevance | X.XX | 4.80 | Δ... |
| Accuracy  | X.XX | 3.95 | Δ... |
| Completeness | X.XX | 3.85 | Δ... |
| Granularity | X.XX | 4.75 | Δ... |

### Retrieval 品質
- KW 命中率：XX%（基準：78%）
- MRR：X.XX（基準：0.75）
- LLM Top-1 Precision：XX%（基準：100%）

### 結論
{整體評估是否達標；若未達標，建議改善方向}
```

### Step D：若分數下滑，診斷原因

常見原因：
- Completeness 下滑 → 萃取時 [How] 區塊不完整
- Accuracy 下滑 → 幻覺率上升，需加強防幻覺規則
- KW 命中率下滑 → keywords 欄位覆蓋不足

---

## 基準線保護規則

```python
# 需同時滿足才更新基準線：
# 1. 所有核心維度平均分超過基準線 +0.05
# 2. 明確使用 --update-baseline flag
```

受保護的基準線（output/eval_baseline.json）：
- Relevance: 4.80 / Accuracy: 3.95 / Completeness: 3.85 / Granularity: 4.75
- KW Hit Rate: 78% / MRR: 0.75 / LLM Top-1 Precision: 100%
