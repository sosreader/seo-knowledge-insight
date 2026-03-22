# autoresearch: Report Quality Optimization

This is an experiment to have the LLM autonomously optimize weekly SEO report quality.

**Key difference from retrieval autoresearch:** There is no `runner.sh`. You ARE the LLM — you modify the prompt, generate the report yourself, then call the eval script to score it.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `report-mar22`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current HEAD.
3. **Read the in-scope files** for full context:
   - `autoresearch/baseline_report.json` — baseline metrics (composite_v3)
   - `autoresearch/eval_report_local.py` — fixed evaluation harness. **Do not modify.**
   - `.claude/commands/generate-report.md` — the **only file you modify**
   - `autoresearch/results_report.tsv` — experiment ledger
   - `output/metrics_snapshots/*.json` — 4 snapshots to rotate through
4. **Verify eval works**:
   ```bash
   .venv/bin/python autoresearch/eval_report_local.py \
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

- `autoresearch/eval_report_local.py` — fixed evaluator
- `autoresearch/baseline_report.json` — baseline reference
- `scripts/_eval_report.py` — evaluation functions
- `eval/fixtures/reports/` — golden fixtures
- `output/metrics_snapshots/` — input data
- `api/src/services/report-evaluator*.ts` — TypeScript evaluator
- Any test files (`*.test.ts`, `test_*.py`)
- Any API routes or services

## The experiment loop

**LOOP FOREVER:**

1. **Read** `autoresearch/results_report.tsv` — understand current best score and what has been tried.
2. **Read** `.claude/commands/generate-report.md` — current prompt content.
3. **Choose ONE hypothesis** to test (change one aspect at a time for clear signal).
4. **Modify** `generate-report.md` → `git commit -m "experiment: <hypothesis description>"`.
5. **Select snapshot**: use `round_number % 4` to rotate through the 4 available snapshots in `output/metrics_snapshots/`.
6. **Extract alert names** from the snapshot: metrics where `monthly < -0.15` OR `weekly < -0.20`. Format as comma-separated string.
7. **Generate the report**: Follow the modified `generate-report.md` prompt using the selected snapshot. Write the report to `/tmp/autoresearch_report_<short_hash>.md`.
8. **Run eval**:
   ```bash
   .venv/bin/python autoresearch/eval_report_local.py \
     --report /tmp/autoresearch_report_<hash>.md \
     --alert-names "<comma-separated alerts>"
   ```
9. **Parse** the last line: `REPORT_COMPOSITE=X.XXXXXX`.
10. **Compare**: `DELTA = current_composite - best_composite_from_keep_rows_in_TSV`.
    - **DELTA > 0** → status = `keep`. The commit stays.
    - **DELTA ≤ 0** → status = `discard`. Revert: `git checkout .claude/commands/generate-report.md`.
11. **Append row** to `results_report.tsv`:
    ```
    <timestamp>\t<composite>\t<17 metrics>\t<git_hash>\t<keep|discard>\t<description>
    ```
12. **Go back to step 1.**

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
- **Reports go to /tmp/**: Write generated reports to `/tmp/autoresearch_report_<hash>.md` — never to the repo.
- **Read selectively**: Only read the sections of `generate-report.md` you plan to modify, not the entire file every round.
- **TSV is your memory**: The results TSV contains everything you need to know about past experiments.
