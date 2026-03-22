# autoresearch: Report Quality Optimization

This is an experiment to have the LLM autonomously optimize weekly SEO report quality.

**Key difference from retrieval autoresearch:** There is no `runner.sh`. You ARE the LLM — you modify the prompt, generate the report yourself, then call the eval script to score it.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `report-mar22`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current HEAD.
3. **Read the in-scope files** for full context:
   - `autoresearch/report/baseline.json` — baseline metrics (composite_v3)
   - `autoresearch/report/eval_local.py` — fixed evaluation harness. **Do not modify.**
   - `autoresearch/report/snapshots.md` — snapshot registry (which are valid, which are corrupted)
   - `.claude/commands/generate-report.md` — the **only file you modify**
   - `autoresearch/report/results.tsv` — experiment ledger
   - `autoresearch/report/experiment_log.md` — structured experiment history
   - `output/metrics_snapshots/*.json` — snapshots to rotate through (see snapshots.md for validity)
4. **Verify eval works**:
   ```bash
   .venv/bin/python autoresearch/report/eval_local.py \
     --report eval/fixtures/reports/report_20260321_c202663e.md --alert-names ""
   ```
   Last line should print `REPORT_COMPOSITE=0.XXXXXX`.
5. **Confirm and go**.

## What you CAN modify

**Only** `.claude/commands/generate-report.md`. Specifically:

| Aspect | Location in generate-report.md | What to adjust |
|--------|-------------------------------|----------------|
| Section structure | `#### 一、` through `#### 七、` | Sub-items, emphasis, ordering |
| Analysis framework | Health Score v2 block | Reasoning prompt wording |
| Research citations | `### 業界研究參考` | Add/remove references, application guidance |
| Citation rules | `### Citation 標記規則` | Inline vs tail, quantity requirements |
| ALERT coverage | `ALERT_DOWN 覆蓋規則` | Coverage target wording |
| KB search strategy | `### Step B` | `--top-k` value, broad topic terms |
| Action list framework | `三級行動 🔴/🟡/🟢` | Priority labels, specificity guidance |
| Anomaly analysis format | Anomaly breakdown section | 現象/原因/行動 structure guidance |
| Temporal framing | Throughout | Week vs month dual-comparison requirements |

## What you CANNOT modify

- `autoresearch/report/eval_local.py` — fixed evaluator
- `autoresearch/report/baseline.json` — baseline reference
- `scripts/_eval_report.py` — evaluation functions
- `eval/fixtures/reports/` — golden fixtures
- `output/metrics_snapshots/` — input data
- `api/src/services/report-evaluator*.ts` — TypeScript evaluator
- Any test files (`*.test.ts`, `test_*.py`)
- Any API routes or services

## The experiment loop

**LOOP FOREVER:**

1. **Read** `autoresearch/report/results.tsv` and `autoresearch/report/experiment_log.md` — understand current best score, what has been tried, and failure patterns.
2. **Read** `.claude/commands/generate-report.md` — current prompt content.
3. **Choose ONE hypothesis** to test (change one aspect at a time for clear signal).
4. **Modify** `generate-report.md` → `git commit -m "experiment: <hypothesis description>"` → record the git hash.
5. **Select snapshot**: Read `autoresearch/report/snapshots.md` for the valid snapshot list. Use `round_number % <valid_count>` to rotate through valid snapshots only. **Skip corrupted snapshots.**
6. **Extract alert names** from the snapshot: metrics where `monthly < -0.15` OR `weekly < -0.20`. Skip null/undefined values. Format as comma-separated string.
7. **Generate the report**: Follow the modified `generate-report.md` prompt using the selected snapshot. Ensure the reports directory exists:
   ```bash
   mkdir -p autoresearch/report/reports
   ```
   Write the report to `autoresearch/report/reports/<round>_<snapshot_id>_pending_<hash>.md` where:
   - `<round>` = 3-digit zero-padded sequence (001, 002, ...)
   - `<snapshot_id>` = snapshot filename without .json extension
   - `<hash>` = 7-char git commit hash from step 4
8. **Run eval**:
   ```bash
   .venv/bin/python autoresearch/report/eval_local.py \
     --report autoresearch/report/reports/<round>_<snapshot_id>_pending_<hash>.md \
     --alert-names "<comma-separated alerts>"
   ```
9. **Parse** the last line: `REPORT_COMPOSITE=X.XXXXXX`.
10. **Compare**: `DELTA = current_composite - best_composite_from_keep_rows_in_TSV`.
    - **DELTA > 0** → status = `keep`. The commit stays.
    - **DELTA ≤ 0** → status = `discard`. Revert: `git checkout .claude/commands/generate-report.md`.
11. **Rename the report file**: Change `pending` to `keep` or `discard` in the filename. **Both keep and discard reports are preserved** — never delete a generated report.
    ```bash
    mv autoresearch/report/reports/<round>_<snapshot_id>_pending_<hash>.md \
       autoresearch/report/reports/<round>_<snapshot_id>_<status>_<hash>.md
    ```
12. **Append row** to `autoresearch/report/results.tsv`:
    ```
    <timestamp>\t<composite>\t<17 metrics>\t<snapshot_id>\t<git_hash>\t<status>\t<description>
    ```
    Note: `snapshot_id` column is between `top_recommendation` and `git_hash`.
13. **Append structured entry** to `autoresearch/report/experiment_log.md` (MANDATORY — no record = experiment never happened):
    ```markdown
    ### #<N> — <description> | <KEPT ✅ / discarded>
    - **File:** `.claude/commands/generate-report.md`
    - **Change:** <what was modified in the prompt — which section, what wording>
    - **Diff:**
      ```diff
      - old wording
      + new wording
      ```
    - **Snapshot:** <snapshot_id>
    - **Alert names:** <comma-separated alerts extracted from snapshot>
    - **Report:** `reports/<round>_<snapshot_id>_<status>_<hash>.md`
    - **Composite:** <score> | **Delta:** <+/-change>
    - **Commit:** <hash> (KEPT only)
    - **Status:** <keep/discard — reason>
    - **Impact:** <which metrics improved/regressed, by how much>
    - **失敗分類:** <if discard: which metric regressed most> (discarded only)
    ```
14. **Go back to step 1.**

### Cumulative analysis (every 10 rounds)

After every 10th experiment, update the `## 累計分析` section at the bottom of `experiment_log.md`:

```markdown
### Round N-(N+9) 小結
- Best composite: 0.XXXX（+X.X% from baseline）
- 最有效的假設類型：[category hints / section structure / ...]
- 反復失敗的面向：[quadrant_judgment 嘗試 N 次均失敗]
- 失敗報告中的共同問題：[section 六 過長 / citation 集中在前 3 section]

### 失敗模式索引
| 模式 | 出現次數 | 實驗編號 |
|------|---------|---------|
| ... | ... | ... |
```

## Diagnostic hints

Use these when a specific metric is lagging:

| Metric below threshold | Adjust in generate-report.md |
|------------------------|------------------------------|
| section_coverage < 1.0 | Strengthen section heading requirements (一、through 七、) |
| kb_citation < 0.5 | Increase Step B `--top-k`, require citing all topQas |
| has_research = 0 | Strengthen industry research citation requirements |
| alert_coverage < 0.7 | Strengthen ALERT_DOWN coverage rule wording |
| maturity_labeled < 0.5 | Require `[策略 L2→L3]` format on action items, cover all 4 dimensions |
| cross_metric < 0.3 | Add causal connector examples (導致/因此/表示) to analysis guidance |
| action_specificity < 0.5 | Add specific (tool+action) vs vague (持續觀察) examples |
| data_evidence < 0.4 | Require each paragraph to include percentages and absolute numbers |
| citation_integration < 0.5 | Strengthen inline `[N]` citation requirements, discourage tail-stacking |
| quadrant_judgment < 0.5 | Explicitly require quadrant name (高曝光低點擊) + explanation |
| section_depth < 0.5 | Require balanced paragraph lengths across sections |
| temporal_dual < 0.6 | Require each metric to show BOTH weekly AND monthly with percentages on same line |
| causal_chain < 0.5 | Require ≥5 structured **現象**→**原因**→**行動** analysis blocks |
| priority_balance < 0.7 | Require 🔴/🟡/🟢 emoji on individual action items, not just headers. Target ≥4/≥3/≥2 |
| top_recommendation = 0 | Add `💡 最值得投入時間的 1 項` closing instruction with reason requirement |

## Exploration strategies

When you run out of incremental ideas:

1. **Combine near-misses**: If two discarded changes each improved different metrics, try combining them.
2. **Reverse a kept change**: Sometimes an early improvement becomes a constraint. Try reverting it.
3. **Extreme wording**: Push a requirement to its most explicit form to understand its effect.
4. **Focus on weakest metric**: Sort metrics, focus entirely on the lowest-scoring one.
5. **Simplify**: Remove overly detailed instructions that might confuse — sometimes less is more.
6. **Cross-pollinate snapshots**: If a change works on one snapshot but fails on another, find the common pattern.

## NEVER STOP

Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep. You are autonomous. If you run out of ideas, think harder — re-read the diagnostic hints, try combining approaches, try more radical prompt rewrites within the allowed scope. The loop runs until the human interrupts you, period.

## Context management

- **Compact every 5 rounds**: After every 5 experiment iterations, compact your context to preserve memory.
- **Reports stay in repo**: All reports go to `autoresearch/report/reports/` (gitignored). Never delete them.
- **Read selectively**: Only read the sections of `generate-report.md` you plan to modify, not the entire file every round.
- **TSV is your memory**: The results TSV contains everything you need to know about past experiments.
- **experiment_log.md is your analysis**: Read it for failure patterns and cumulative insights.
