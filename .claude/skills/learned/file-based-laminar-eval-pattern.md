---
name: file-based-laminar-eval-pattern
description: "Build Laminar evaluate() for LLM-generated docs using .md fixtures + structural evaluators + threshold gate"
user-invocable: false
origin: auto-extracted
---

# File-Based Laminar Eval for Generated Documents

**Extracted:** 2026-03-12
**Context:** When adding offline evaluation for LLM-generated reports/documents that cannot be auto-generated in CI (e.g., Claude Code commands), use file-based fixtures instead of API-backed executors.

## Problem

Standard eval pattern calls an API endpoint as executor. But some features (like `/meeting-prep`) are Claude Code commands with no API — eval must work on pre-generated files. Also, golden datasets can't specify expected output text (LLM is non-deterministic), only structural properties.

## Solution

### 1. Golden Dataset: Structural Properties, Not Text Match

```json
[{
  "id": "report_20260306",
  "report_path": "eval/fixtures/meeting_prep/report.md",
  "expected_structure": {
    "section_count": 11,
    "citation_count_range": [10, 30],
    "question_by_type": {"A": [3, 5], "B": [4, 6]}
  },
  "expected_grounding": {
    "citation_id_resolution_min": 0.9
  }
}]
```

### 2. File Reader Executor (Not API Caller)

```python
def executor(data: dict) -> dict:
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"error": f"File not found: {report_path}"}
    return {
        "sections": _parse_sections(content),
        "metadata": _parse_meta(content),
        "citations": _parse_citations(content),
        "raw_content": content,
    }
```

### 3. CI Fixtures (Solve .gitignore Problem)

```
eval/fixtures/meeting_prep/    # Committed to git, CI can read
  ├── report_20260306.md       # Copied from output/ (which is in .gitignore)
  └── report_20260309.md
```

Golden dataset `report_path` points to `eval/fixtures/` not `output/`.

### 4. Threshold Gate + Cached Executor

```python
_exec_cache: dict[str, dict] = {}

def _run_threshold_gate() -> None:
    # Pre-run all executors, cache results
    pre_results = [(executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {dp["data"]["report_path"]: out for dp, (out, _) in zip(_dataset, pre_results)}

    # Check thresholds
    for metric, min_val in thresholds.items():
        scores = [evaluator_fn(out, tgt) for out, tgt in pre_results]
        avg = sum(scores) / len(scores)
        if avg < min_val:
            sys.exit(1)  # CI gate failure

def _cached_executor(data: dict) -> dict:
    """Reuse pre-computed results for Laminar evaluate()."""
    cached = _exec_cache.get(data["report_path"])
    if cached is not None and "error" not in cached:  # Skip error cache
        return cached
    return executor(data)
```

### 5. KB Graceful Fallback (for Grounding Eval)

```python
# Pre-check KB availability before running gate
kb_items = _load_qa_items()
if not kb_items:
    print("SKIP: KB empty, grounding gate skipped.", file=sys.stderr)
    return  # Don't sys.exit(1) — that's a false CI failure
```

### 6. Stable ID Resolution

Citations reference `stable_id` (hex string like `"63c7b5042b8a8827"`), not integer `id`. KB index must handle both formats:

```python
def _build_kb_index(kb_items):
    index = {}
    for item in kb_items:
        sid = item.get("stable_id")  # Local file format
        if sid:
            index[sid] = item
        elif isinstance(item.get("id"), str):  # Supabase format
            index[item["id"]] = item
    return index
```

## Checklist for Adding a New Eval Layer

1. [ ] Create `evals/eval_<name>.py` with executor + evaluators + threshold gate
2. [ ] Add golden cases to `eval/golden_<name>.json`
3. [ ] Commit fixtures to `eval/fixtures/<name>/`
4. [ ] Add threshold group to `eval/eval_thresholds.json`
5. [ ] Add CI step to `.github/workflows/eval.yml` (env vars!)
6. [ ] Add Makefile target(s)
7. [ ] Update `CLAUDE.md` and `README.md`
8. [ ] Run full eval to verify all cases pass

## When to Use

- Adding offline eval for any LLM-generated document (reports, analyses, summaries)
- The generation step is a Claude Code command (no API endpoint)
- Output is non-deterministic — can only verify structural/grounding properties
- Need CI gate that fails on quality regression
