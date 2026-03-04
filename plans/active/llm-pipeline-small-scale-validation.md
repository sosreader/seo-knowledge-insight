---
name: llm-pipeline-small-scale-validation
description: "Before running expensive LLM batch operations, always validate on a small sample first. Define pass criteria, run small, verify, then expand."
origin: custom
---

# Small-Scale Validation Before Full LLM Pipeline Run

## When to Activate

- About to run a batch LLM operation over 10+ items
- Changing a prompt that affects a multi-step pipeline
- Adding a new classification category and need to re-classify all records
- Any step that costs money proportional to input size (Step 2: per-document, Step 3: per-QA)

## Core Pattern

```
Define pass criteria → Run small (3–5 items) → Evaluate → Pass? → Expand to full
                                                          ↘ Fail? → Fix prompt → Repeat
```

### Step 1: Define Pass Criteria First

Write down what "good enough" looks like **before** running anything:

```markdown
## Validation Gate: Step 2 Prompt Change (Completeness)
Pass criteria:
- Completeness score ≥ 4.0 on 5-item sample (LLM Judge)
- No new hallucinations (Accuracy ≥ 4.0)
- Answer length > 80 chars (structural check — free)
Sample size: 5 documents
Cost if pass: ~gpt-5.2 × 87 docs
Cost if fail: only 5 docs wasted
```

### Step 2: Run Small Scale

```bash
# Step 2: 只處理 3 份（--limit）
python scripts/run_pipeline.py --step 2 --limit 3 --force

# Step 5: 只評估那 3 份產出的 Q&A（--sample 限制抽樣數）
python scripts/05_evaluate.py --sample 15 --skip-classify-eval
```

### Step 3: Evaluate Against Criteria

```python
# 快速檢查是否通過 pass criteria（免 API，直接看 JSON）
import json
from pathlib import Path

report = json.loads(Path("output/eval_report.json").read_text())
stats = report["quality_stats"]
completeness = stats.get("completeness", {}).get("mean", 0)
accuracy = stats.get("accuracy", {}).get("mean", 0)

passed = completeness >= 4.0 and accuracy >= 4.0
print(f"Completeness: {completeness:.2f} {'✅' if completeness >= 4.0 else '❌'}")
print(f"Accuracy:     {accuracy:.2f} {'✅' if accuracy >= 4.0 else '❌'}")
print(f"Gate: {'PASS — 可擴大執行' if passed else 'FAIL — 先修 prompt'}")
```

### Step 4: Expand Only If Passed

```bash
# 通過後才跑全量
python scripts/run_pipeline.py --step 2
python scripts/run_pipeline.py --step 3
```

---

## Validation Gate Per Pipeline Step

| 步驟 | 小規模驗證 | Pass 門檻 | 全量成本 |
|------|-----------|-----------|---------|
| Step 2（Q&A 萃取）| `--limit 3` | Completeness ≥ 4.0, Accuracy ≥ 4.0 | gpt-5.2 × 87 份 |
| Step 3（分類）| `--sample 20 --classify-only` | Category 正確率 ≥ 75% | gpt-5-mini × 703 筆 |
| Step 3（去重）| 手動抽查 5 組相似對 | 合併結果合理 | embedding + gpt-5.2 |
| Step 4（週報）| `--dry-run` + 單週測試 | 週報結構完整 | gpt-5.2 × 1 次 |
| Step 5（Retrieval eval）| `--eval-retrieval`（golden set 固定）| MRR ≥ 0.8, Precision ≥ 0.7 | gpt-5-mini × golden cases |

---

## Anti-Patterns to Avoid

- **直接跑全量然後用評估結果決定要不要重跑** — 已經花錢了
- **只看 loss/score，不看實際輸出** — 先手動看 3 筆再跑全量
- **把 pass 門檻定在全量跑完之後** — 門檻必須在執行前定義
- **--limit 太大（>10）失去快速迭代優勢** — 小規模的價值在於快，3–5 份夠了

## Best Practices

- 每次改 prompt 都要重跑小規模驗證，即使「只是小改動」
- Pass 門檻記錄在 `.claude/evals/` 裡，不要只放在腦中
- 小規模失敗時，先診斷 1 筆最差案例，找出 prompt 的盲點
- 用 `--seed 42` 固定抽樣，確保每次比較的是同一批樣本
