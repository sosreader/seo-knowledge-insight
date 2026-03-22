# autoresearch: Retrieval Quality Optimization

This is an experiment to have the LLM autonomously optimize search retrieval quality.

## Setup

To set up a new experiment, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar21`). The branch `autoresearch/<tag>` must not already exist.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current HEAD.
3. **Read the in-scope files** for full context:
   - `autoresearch/retrieval/baseline.json` — v3.1 baseline metrics
   - `autoresearch/retrieval/eval_local.py` — fixed evaluation harness. Do not modify.
   - `api/src/store/search-engine.ts` — the primary file you modify (scoring formula + reranking)
   - `api/src/utils/keyword-boost.ts` — keyword matching layers
   - `api/src/store/query-term-utils.ts` — query term utilities
   - `eval/eval_thresholds.json` — minimum thresholds (retrieval_stable section)
4. **Verify server is running**: `curl -sf http://localhost:8002/health`
   - If not: `cd api && RATE_LIMIT_DEFAULT=9999 pnpm dev`
5. **Run the baseline**: `bash autoresearch/retrieval/runner.sh "baseline"` — first entry in results.tsv.
6. **Confirm and go**.

Once you get confirmation, kick off the experimentation.

## Experimentation

Each experiment runs against 35 golden retrieval cases via the search API. The eval script takes ~30-45 seconds. You launch it as: `bash autoresearch/retrieval/runner.sh "description"`.

**What you CAN do:**

Modify numerical parameters in these 3 files:

### `api/src/store/search-engine.ts`

DEFAULT_CONFIG (6 params):
| Parameter | Current | Range |
|-----------|---------|-------|
| semanticWeight | 0.7 | 0.3–0.9 |
| synonymBoost | 0.05 | 0.01–0.15 |
| kwBoost.boost | 0.1 | 0.05–0.2 |
| kwBoost.maxHits | 3 | 2–5 |
| kwBoost.partial | 0.05 | 0.01–0.08 |
| overRetrieveFactor | 3 | 2–6 |

metadataFeatureScore weights (11 params):
| Parameter | Current | Range |
|-----------|---------|-------|
| phraseBoost multiplier | 2.0 | 1.0–3.5 |
| surfaceBoost per-token | 0.03 | 0.01–0.08 |
| categoryBoost per-match | 0.08 | 0.04–0.15 |
| intentBoost per-match | 0.06 | 0.02–0.12 |
| scenarioBoost per-match | 0.05 | 0.02–0.10 |
| exactTermBoost per-match | 0.04 | 0.01–0.08 |
| hardNegativePenalty | -0.05 | -0.01–-0.15 |
| servingTier booster_targeted | +0.05 | 0.0–0.15 |
| servingTier booster_untargeted | -0.08 | -0.02–-0.15 |
| servingTier supporting | +0.02 | 0.0–0.08 |
| servingTier canonical | +0.08 | 0.03–0.15 |

rerankCandidates weights (4 params):
| Parameter | Current | Range |
|-----------|---------|-------|
| duplicate signature penalty | -0.25 | -0.10–-0.40 |
| categoryDiversityBoost base | 0.12 | 0.05–0.20 |
| categoryDiversityBoost step | 0.06 | 0.02–0.12 |
| intent diversity boost | +0.04 | 0.01–0.10 |

### `api/src/utils/keyword-boost.ts`

- You may add new matching layers (do not remove the existing 4 layers)
- Bigram prefix length (currently 2, range 2–4)

### `api/src/store/query-term-utils.ts`

| Parameter | Current | Range |
|-----------|---------|-------|
| MIN_QUERY_TERM_LENGTH | 2 | 2–3 |
| novelQueryTermBoost tier-8 coeff | 0.01 | 0.005–0.02 |
| novelQueryTermBoost tier-5 coeff | 0.015 | 0.01–0.03 |
| novelQueryTermBoost default coeff | 0.02 | 0.01–0.04 |

**What you CANNOT do:**

- Modify `autoresearch/retrieval/eval_local.py`, `autoresearch/retrieval/runner.sh`, `autoresearch/retrieval/baseline.json`
- Modify `eval/golden_retrieval.json` or `eval/eval_thresholds.json`
- Modify `evals/eval_retrieval.py`
- Modify any files in `api/src/routes/`, `api/src/services/`
- Modify `api/src/store/qa-store.ts`, `api/src/store/supabase-qa-store.ts`
- Modify any test files (`*.test.ts`)
- Modify `output/qa_final.json`
- Install new packages or add dependencies

**The goal is simple: get the highest composite score.** The composite score is a weighted average of 8 retrieval metrics (hit_rate, mrr, precision_at_k, ndcg_at_k, keyword_hit_rate, multi_label_f1_at_k, dual_category_recall_at_k, boosterless_precision_at_k). Baseline ≈ 0.905.

**Safety constraint**: No individual metric may drop below the `retrieval_stable` thresholds in `eval/eval_thresholds.json`.

**Simplicity criterion**: All else being equal, simpler is better. A small improvement that adds ugly complexity is not worth it. Removing something and getting equal or better results is a great outcome. A 0.001 composite improvement that adds 20 lines of hacky code? Not worth it. A 0.001 improvement from deleting code? Definitely keep.

## Output format

The runner script outputs:

```
---
COMPOSITE_SCORE=0.905432
PREV_BEST=0.905000
DELTA=+0.000432
GIT_HASH=a1b2c3d
---
```

## The experiment loop

LOOP FOREVER:

1. Read `autoresearch/retrieval/results.tsv` — understand current best score and what has been tried.
2. Read the current values in the target files.
3. Choose ONE hypothesis to test (change one aspect at a time for clear signal).
4. Modify the code.
5. **Wait 5 seconds** for tsx watch to hot-reload the server.
6. Run: `bash autoresearch/retrieval/runner.sh "description of change"`
7. Parse the output:
   - If DELTA > 0 (composite improved): `git add api/src/store/search-engine.ts api/src/utils/keyword-boost.ts api/src/store/query-term-utils.ts && git commit -m "perf: [score] description"`
   - If DELTA <= 0: `git checkout api/src/store/search-engine.ts api/src/utils/keyword-boost.ts api/src/store/query-term-utils.ts`
8. **Append structured entry** to `autoresearch/retrieval/experiment_log.md` (MANDATORY — no record = experiment never happened):
   ```markdown
   ### #<N> — <description> | <KEPT ✅ / discarded>
   - **File:** <which file was modified>
   - **Change:** <specific parameter/value change>
   - **Diff:** (for KEPT experiments, include the actual diff)
     ```diff
     - old value
     + new value
     ```
   - **Composite:** <score> | **Delta:** <+/-change>
   - **Commit:** <hash> (KEPT only)
   - **Status:** <keep/discard — reason, which cases regressed>
   ```
9. Go back to step 1.

## Diagnostic hints

Use these when a specific metric is lagging:

| Symptom | Try adjusting |
|---------|---------------|
| mrr < 0.95 | categoryBoost, intentBoost (relevant results ranked too low) |
| keyword_hit_rate < 0.85 | kwBoost.boost, kwBoost.maxHits (keywords not surfacing) |
| precision_at_k < 0.85 | duplicate penalty, overRetrieveFactor (irrelevant results in top-K) |
| ndcg_at_k < 0.80 | categoryDiversityBoost, rerank weights (ranking order suboptimal) |
| hit_rate = 1.0 | Already maxed — do NOT sacrifice other metrics for this |
| multi_label_f1 < 0.85 | Balance precision vs recall — check category coverage |
| boosterless_prec low | servingTier weights (boosters displacing canonical results) |

## Exploration strategies

When you run out of incremental ideas:

1. **Combine near-misses**: If two discarded changes each improved different metrics, try combining them.
2. **Reverse a kept change**: Sometimes an early improvement becomes a constraint. Try reverting it.
3. **Extreme values**: Push a parameter to its range boundary to understand its effect direction.
4. **Correlated params**: semanticWeight + kwBoost.boost are inversely related — try shifting the balance.
5. **Rerank focus**: If base scores are good but final output is bad, focus on rerankCandidates weights.

## NEVER STOP

Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep. You are autonomous. If you run out of ideas, think harder — re-read the code, try combining approaches, try more radical changes within the allowed parameter space. The loop runs until the human interrupts you, period.
