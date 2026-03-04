# /evaluate-model-ab — Cross-Model A/B Evaluation

Compare QA extraction quality across two different models. Uses Claude Code as the Judge.

## Usage

```
/evaluate-model-ab
/evaluate-model-ab --sample 10
```

## Workflow

1. **Sample**: Pick N unprocessed or random Markdown files (default: 5)
2. **Extract Model A**: Use the current `OPENAI_MODEL` (from `.env`) to extract Q&A
3. **Extract Model B**: Use Claude Code (you) to extract Q&A from the same files
4. **Judge**: Compare each pair on 4 dimensions (relevance, accuracy, completeness, granularity)
5. **Report**: Output a comparison table with per-dimension scores and winner

## Steps

### Step 1: Sample Selection

Read `output/qa_all_raw.json` and select $ARGUMENTS or 5 source files at random:

```bash
.venv/bin/python scripts/qa_tools.py eval-sample --size ${ARGUMENTS:-5} --json
```

Take the `source_file` values from the sample to identify the Markdown files.

### Step 2: Model A Extraction (OpenAI)

For each sampled file, check if Q&A already exists in `output/qa_per_meeting/` or `output/qa_per_article/`.
If not, run extraction via OpenAI:

```bash
.venv/bin/python scripts/02_extract_qa.py --file <filename>.md --limit 1
```

### Step 3: Model B Extraction (Claude Code)

For each sampled file, read the Markdown content and extract Q&A pairs yourself using the same prompt format as `02_extract_qa.py`. Output structured JSON with `question`, `answer`, `keywords` fields.

### Step 4: Judge

For each file, compare Model A vs Model B extractions on:
- **Relevance** (1-5): How relevant are the Q&A pairs to SEO practitioners?
- **Accuracy** (1-5): Are the answers factually correct based on the source?
- **Completeness** (1-5): Did the model capture all important information?
- **Granularity** (1-5): Are Q&A pairs appropriately scoped (not too broad/narrow)?

### Step 5: Report

Output a Markdown comparison table:

```
| File | Dim | Model A (OpenAI) | Model B (Claude) | Winner |
|------|-----|-----------------|-----------------|--------|
| ... | relevance | 4.5 | 4.8 | B |
```

And a summary:
- Overall average scores per model
- Per-dimension winner
- Recommendation on which model to use

### Step 6: Save Results

Save the A/B comparison to `output/evals/ab_<date>_<model_a>_vs_<model_b>.json` with:
- `model_a`, `model_b` identifiers
- Per-file scores
- Aggregate scores
- `extraction_model` fields for provenance tracking

```bash
.venv/bin/python scripts/qa_tools.py eval-save \
  --input output/evals/ab_<date>.json \
  --extraction-engine claude-code \
  --extraction-model "claude-code" \
  --update-baseline
```
