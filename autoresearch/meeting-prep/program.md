# autoresearch: Meeting-Prep Quality Optimization

This is an experiment to have the LLM autonomously optimize meeting-prep report quality.

**Key difference from report autoresearch:** You generate the meeting-prep report yourself using the prompt in `meeting-prep.md`, then call the eval script to score it. No web research — use `--report` mode with fixed fixtures for determinism.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `meeting-prep-mar22`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current HEAD.
3. **Read the in-scope files** for full context:
   - `autoresearch/meeting-prep/baseline.json` — baseline metrics (composite_v1 = 0.8305)
   - `autoresearch/meeting-prep/eval_local.py` — fixed evaluation harness. **Do not modify.**
   - `autoresearch/meeting-prep/snapshots.md` — fixture registry (which are valid)
   - `.claude/commands/meeting-prep.md` — the **only file you modify**
   - `autoresearch/meeting-prep/results.tsv` — experiment ledger
   - `autoresearch/meeting-prep/experiment_log.md` — structured experiment history
   - `eval/fixtures/meeting_prep/*.md` — golden fixtures to use as input
4. **Verify eval works**:
   ```bash
   .venv/bin/python autoresearch/meeting-prep/eval_local.py \
     --report eval/fixtures/meeting_prep/meeting_prep_20260306_ea576a4f.md
   ```
   Last line should print `MEETING_PREP_COMPOSITE=0.XXXXXX`.
5. **Confirm and go**.

## What you CAN modify

**Only** `.claude/commands/meeting-prep.md`. Specifically:

| Aspect | Location in meeting-prep.md | What to adjust |
|--------|---------------------------|----------------|
| Alert extraction | Step A | Threshold wording, grouping rules |
| KB search strategy | Step C | `--top-k` value, query terms, broad topic words |
| Root cause hypothesis framing | Step E / Section 3 | 3-hypothesis structure, L1-L5 layer balance, verification tags |
| Cross-reference table | Step E / Section 4 | Column requirements, judgment criteria |
| Audit gap format | Step E / Section 5 | L1-L5 layer descriptions, specificity level |
| E-E-A-T scoring guidance | Step E / Section 6 | Rubric wording, required evidence types |
| Human elements | Step E / Section 7 | 7-element descriptors, consultant article usage |
| Maturity framework | Step E / Section 8 | L1-L4 descriptors, next-step guidance |
| Question generation | Step E / Section 9 | A/B/C/D type balance, specificity requirements, source annotation rules |
| Action checklist | Step E / Section 10 | Tool name requirements, maturity label rules |
| Citation integration | Throughout | Inline citation density, relevance matching |
| Section headings | Throughout | Chinese vs English format, alert name inclusion |

## What you CANNOT modify

- `autoresearch/meeting-prep/eval_local.py` — fixed evaluator
- `autoresearch/meeting-prep/baseline.json` — baseline reference
- `evals/eval_meeting_prep_*.py` — evaluation layer functions
- `eval/golden_meeting_prep.json` — golden fixtures
- `eval/fixtures/meeting_prep/` — input fixtures
- `api/src/` — any API code
- Any test files

## The experiment loop

**LOOP FOREVER:**

1. **Read** `autoresearch/meeting-prep/results.tsv` and `experiment_log.md` — understand current best score, what has been tried, and failure patterns.
2. **Read** `.claude/commands/meeting-prep.md` — only the sections you plan to modify.
3. **Choose ONE hypothesis** to test (change one aspect at a time for clear signal).
4. **Modify** `meeting-prep.md` → `git commit -m "experiment: <hypothesis description>"` → record the git hash.
5. **Select fixture**: Read `autoresearch/meeting-prep/snapshots.md` for the valid fixture list. Use `round_number % 4` to rotate through valid fixtures.
6. **Extract ALERT_DOWN names** from the fixture: scan Section 1 for ALERT_DOWN table rows.
7. **Generate the meeting-prep report**: Follow the modified `meeting-prep.md` prompt using the selected fixture as input (`--report` mode). **Skip Step B (web research)** — instead, write a minimal S2 section with placeholder industry updates (3+ content lines, 2+ source names) to avoid L4 eval zeroing out. Execute Steps A, C, D, E as normal. Ensure the reports directory exists:
   ```bash
   mkdir -p autoresearch/meeting-prep/reports
   ```
   Write the report to `autoresearch/meeting-prep/reports/<round>_<fixture_id>_pending_<hash>.md` where:
   - `<round>` = 3-digit zero-padded sequence (001, 002, ...)
   - `<fixture_id>` = fixture filename without .md extension
   - `<hash>` = 7-char git commit hash from step 4
8. **Run eval**:
   ```bash
   .venv/bin/python autoresearch/meeting-prep/eval_local.py \
     --report autoresearch/meeting-prep/reports/<round>_<fixture_id>_pending_<hash>.md
   ```
9. **Parse** the last line: `MEETING_PREP_COMPOSITE=X.XXXXXX`.
10. **Compare**: `DELTA = current_composite - best_composite_from_keep_rows_in_TSV`.
    - **DELTA > 0** → status = `keep`. The commit stays.
    - **DELTA ≤ 0** → status = `discard`. Revert: `git checkout .claude/commands/meeting-prep.md`.
11. **Rename the report file**: Change `pending` to `keep` or `discard` in the filename. **Both keep and discard reports are preserved** — never delete a generated report.
12. **Append row** to `autoresearch/meeting-prep/results.tsv`:
    ```
    <timestamp>\t<composite>\t<l1_avg>\t<l2g_avg>\t<l2c_cross_section>\t<l2c_action_spec>\t<l2c_hypo_falsif>\t<l2c_temporal>\t<l2c_citation_rel>\t<l4_avg>\t<fixture_id>\t<git_hash>\t<status>\t<description>
    ```
13. **Append structured entry** to `experiment_log.md` (MANDATORY — no record = experiment never happened):
    ```markdown
    ### #<N> — <description> | <KEPT ✅ / discarded>
    - **File:** `.claude/commands/meeting-prep.md`
    - **Change:** <what was modified — which section, what wording>
    - **Diff:**
      ```diff
      - old wording
      + new wording
      ```
    - **Fixture:** <fixture_id>
    - **Report:** `reports/<round>_<fixture_id>_<status>_<hash>.md`
    - **Composite:** <score> | **Delta:** <+/-change>
    - **Commit:** <hash> (KEPT only)
    - **Status:** <keep/discard — reason>
    - **Impact:** <which metrics improved/regressed, by how much>
    - **失敗分類:** <if discard: which metric regressed most> (discarded only)
    ```
14. **Go back to step 1.**

### Cumulative analysis (every 10 rounds)

After every 10th experiment, update the `## 累計分析` section at the bottom of `experiment_log.md`.

## Diagnostic hints

Use these when a specific metric is lagging:

| Metric below threshold | Adjust in meeting-prep.md |
|------------------------|--------------------------|
| cross_section_coherence < 0.6 | S3 subsection headings must include S1 ALERT_DOWN metric names verbatim |
| action_specificity < 0.5 | S10 items must include tool name (GSC/Ahrefs/PageSpeed/Screaming Frog/GA4) + action verb (排查/篩選/檢查/驗證/建立) |
| hypothesis_falsifiability < 0.8 | S3 each hypothesis must end with **可驗證**/**需人工確認**/**需顧問判斷** tag |
| temporal_consistency < 0.8 | E-E-A-T scores should not jump > 1 point from prior reports |
| citation_relevance < 0.7 | Citations in S3/S6 must use KB items from matching categories (技術SEO for L1, 連結策略 for L4) |
| s2_content_density < 0.7 | S2 subsections must have ≥3 non-header lines each |
| source_diversity < 0.7 | S2 must reference ≥5 distinct named sources |
| s4_four_sources_populated < 0.8 | S4 table rows must have >5 chars in all 4 source columns |

## Exploration strategies

When you run out of incremental ideas:

1. **Combine near-misses**: If two discarded changes each improved different metrics, try combining them.
2. **Reverse a kept change**: Sometimes an early improvement becomes a constraint. Try reverting it.
3. **Extreme wording**: Push a requirement to its most explicit form to understand its effect.
4. **Focus on weakest metric**: Sort metrics, focus entirely on the lowest-scoring one.
5. **Simplify**: Remove overly detailed instructions that might confuse — sometimes less is more.
6. **Cross-fixture validation**: If a change works on one fixture but fails on another, find the common pattern.
7. **Section heading format**: Try switching between `## Section N：` and `## N、` Chinese numbering.

## NEVER STOP

Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep. You are autonomous. If you run out of ideas, think harder — re-read the diagnostic hints, try combining approaches, try more radical prompt rewrites within the allowed scope. The loop runs until the human interrupts you, period.

## Context management

- **Compact every 5 rounds**: After every 5 experiment iterations, compact your context to preserve memory.
- **Reports stay in repo**: All reports go to `autoresearch/meeting-prep/reports/` (gitignored). Never delete them.
- **Read selectively**: Only read the sections of `meeting-prep.md` you plan to modify, not the entire file every round.
- **TSV is your memory**: The results TSV contains everything you need to know about past experiments.
- **experiment_log.md is your analysis**: Read it for failure patterns and cumulative insights.
