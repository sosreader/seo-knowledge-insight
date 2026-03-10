# /evaluate-retrieval-by-model — 按模型分群評估

按 extraction_model 分群評估檢索品質。

## 用法

```bash
make evaluate-retrieval-by-model MODEL=claude-code
```

## 底層

呼叫 `evals/eval_retrieval.py --model <MODEL>`：
- 搜尋結果按 extraction_model 過濾
- Laminar group_name 帶入 model 名稱（如 `retrieval_quality_claude-code`）
- 無 `--model` 時行為完全不變（向下相容）

## 參數

| 參數 | 說明 |
|------|------|
| `MODEL` | extraction_model 值（如 `claude-code`、`gpt-4o`） |
| `--limit N` | 限制 golden cases 數量 |

$ARGUMENTS
