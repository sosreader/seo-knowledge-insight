---
name: hono-file-route-checklist
description: "Checklist for new Hono routes serving markdown files from output dir"
user-invocable: false
origin: auto-extracted
---

# Hono File-Serving Route Checklist

**Extracted:** 2026-03-12
**Context:** When creating a new API route that lists/serves markdown files from the output directory (e.g., reports, meeting-prep)

## Problem
New file-serving routes in this project repeatedly hit the same issues: path traversal, duplicated utilities, unvalidated embedded JSON, missing test edge cases.

## Solution

### Security
1. **Path traversal guard** — after `join()` or `resolve()`, verify the path stays inside the allowed base dir:
   ```typescript
   import { resolve } from "node:path";
   if (!resolve(filepath).startsWith(resolve(paths.outputDir))) {
     return c.json(fail("Invalid path"), 400);
   }
   ```
2. **Date param validation** — use a strict regex before building file paths

### DRY
3. **Reuse `readTail`** from `utils/report-file.ts` — never copy the implementation
4. **Reuse `listReportFiles` pattern** but with a different filename regex

### Validation
5. **Field-by-field JSON validation** for embedded `<!-- meta {...} -->` comments — never `JSON.parse() as Type`:
   ```typescript
   const raw = JSON.parse(m[1]) as Record<string, unknown>;
   if (typeof raw.date !== "string") return undefined;
   // validate each field...
   ```

### Testing (minimum 7+ tests)
6. List endpoint: returns items, each has date/filename/size_bytes, meta parsing works
7. Detail endpoint: exact match, fuzzy match by date prefix, 404 for missing, 400 for invalid format
8. Edge cases: malformed meta JSON → `meta: undefined`, file without meta comment
9. Cleanup: `afterAll(() => rmSync(tmpDir, { recursive: true, force: true }))`

### Registration
10. Import + mount in `index.ts`, add rate limit middleware, update CLAUDE.md router count

## When to Use
- Creating any new Hono route that reads markdown files from `paths.outputDir`
- Mirroring an existing route pattern (e.g., reports → meeting-prep)
