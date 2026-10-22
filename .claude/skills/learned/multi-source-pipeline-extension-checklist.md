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

Adding a new data source (e.g., Google Case Studies) to the multi-source pipeline requires coordinated changes across Python scripts and documentation. Missing any single file leads to silent inconsistencies (wrong step counts, missing endpoints, orphaned data directories).

## Solution

### Layer 1: Python Fetcher

| File | Action |
|------|--------|
| `scripts/01X_fetch_{source}.py` | New fetcher script (model after `01c_fetch_ithelp.py`) |
| `tests/test_fetch_{source}.py` | Tests: URL pattern, index load/save, content extraction, skip existing |
| `config.py` | Add `RAW_{SOURCE}_MD_DIR` path + `DIR_COLLECTION_MAP` entry |
| `Makefile` | New `fetch-{source}` target + update `fetch-articles` composite target |

> 原 Layer 2–4（TypeScript API config、`pipeline.ts` routes、前端 `pipeline.tsx`）已隨 Lambda `seo-insight-api` 退役於 2026-10 移除，不再需要同步。

### Layer 2: Documentation（原 Layer 5，最容易漏）

Run these greps after all code changes to find stale counts:

```bash
# Find all step count references
grep -rn "步驟" CLAUDE.md README.md research/06*.md
# Find fetch-articles descriptions
grep -rn "fetch-articles" CLAUDE.md README.md research/06*.md
```

| File | What to update |
|------|----------------|
| `CLAUDE.md` | Pipeline step count, fetch-articles description, make targets |
| `README.md` | Step count, directory tree, fetch-articles description |
| `research/06a-changelog.md` | v2.X entry: step count, directory count, script list |
| `research/06b-diagram.md` | Mermaid: data source node, pipeline step node, connection arrows, subgraph version |
| `MEMORY.md` | Step count, collection list, fetcher list |

### Validation

```bash
# Python tests
python -m pytest tests/test_fetch_{source}.py -v
```

## When to Use

- Adding a new content source (e.g., blog, documentation site, case studies)
- `DIR_COLLECTION_MAP` gets a new entry
