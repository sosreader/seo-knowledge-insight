---
name: multi-source-pipeline-extension-checklist
description: "Systematic file changes when adding a new data source to the multi-source pipeline"
user-invocable: false
origin: auto-extracted
---

# Multi-Source Pipeline Extension Checklist

**Extracted:** 2026-03-05
**Context:** Adding Google Case Studies as 4th data source required updates in 9+ files across 5 layers. Code-reviewer found 4 HIGH doc inconsistencies even after manual updates.

## Problem

Adding a new data source (e.g., Google Case Studies) to the multi-source pipeline requires coordinated changes across Python scripts, API config, API routes, frontend, and documentation. Missing any single file leads to silent inconsistencies (wrong step counts, missing endpoints, orphaned data directories).

## Solution

### Layer 1: Python Fetcher

| File | Action |
|------|--------|
| `scripts/01X_fetch_{source}.py` | New fetcher script (model after `01c_fetch_ithelp.py`) |
| `tests/test_fetch_{source}.py` | Tests: URL pattern, index load/save, content extraction, skip existing |
| `config.py` | Add `RAW_{SOURCE}_MD_DIR` path + `DIR_COLLECTION_MAP` entry |
| `Makefile` | New `fetch-{source}` target + update `fetch-articles` composite target |

### Layer 2: API Config

| File | Action |
|------|--------|
| `api/src/config.ts` | Add `raw{Source}MdDir` to `paths` object |

### Layer 3: API Routes (3 places in pipeline.ts)

| Function | Change |
|----------|--------|
| `buildPipelineStatus()` | Add `countMdFiles()` call + new step in `steps[]` array |
| `findUnprocessed()` | Add new entry to `sources[]` array |
| `POST /fetch-articles` | Add `execPython("01X_fetch_{source}.py")` + result entry |

### Layer 4: Frontend

| File | Change |
|------|--------|
| `pipeline.tsx` | Add `case "fetch-{source}":` to `handleRunStep` switch (falls through to `triggerFetchArticles()`) |

### Layer 5: Documentation (most error-prone)

Run these greps after all code changes to find stale counts:

```bash
# Find all step count references
grep -rn "步驟" CLAUDE.md README.md api/README.md research/06*.md
# Find all endpoint count references
grep -rn "endpoints" api/README.md README.md
# Find fetch-articles descriptions
grep -rn "fetch-articles" CLAUDE.md README.md api/README.md research/06*.md
```

| File | What to update |
|------|----------------|
| `CLAUDE.md` | Pipeline step count, fetch-articles description, make targets |
| `README.md` | Step count, directory tree, endpoint table, fetch-articles description |
| `api/README.md` | Pipeline endpoint count, fetch-articles row in table, total endpoint count |
| `research/06a-changelog.md` | v2.X entry: step count, directory count, script list |
| `research/06b-diagram.md` | Mermaid: data source node, pipeline step node, connection arrows, subgraph version |
| `MEMORY.md` | Step count, collection list, fetcher list, endpoint count |

### Validation

```bash
# Python tests
python -m pytest tests/test_fetch_{source}.py -v

# API tests
cd api && pnpm test

# Count consistency check
grep -c "fetch-google\|fetch-notion\|fetch-medium\|fetch-ithelp" api/src/routes/pipeline.ts
# Should show: buildPipelineStatus has N steps, findUnprocessed has N sources
```

## When to Use

- Adding a new content source (e.g., blog, documentation site, case studies)
- Pipeline `buildPipelineStatus()` step count changes
- `POST /fetch-articles` needs a new fetcher
- `DIR_COLLECTION_MAP` gets a new entry
