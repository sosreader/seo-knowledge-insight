---
name: seo-insight-frontend-page-checklist
description: "Checklist for new seoInsight admin pages mirroring report.tsx pattern"
user-invocable: false
origin: auto-extracted
---

# SEO Insight Frontend Page Checklist

**Extracted:** 2026-03-12
**Context:** When creating a new admin page in vocus-web-ui that displays markdown reports from the seo-knowledge-insight API

## Problem
New seoInsight pages (meetingPrep, future pages) mirror the report.tsx pattern but repeatedly hit the same issues: missing date validation on API client, duplicated citation parsing, NaN edge cases in display helpers, forgotten navigation/barrel exports.

## Solution

### 1. API Client (`apis/seoInsight.<feature>.api.ts`)
- Import `SeoApiError` + `seoFetch` from `./seoInsight.fetch`
- **Date parameter validation** before URL interpolation:
  ```typescript
  if (!/^\d{8}(_[0-9a-f]{1,8})?$/.test(date)) {
    throw new SeoApiError(400, "Invalid date format");
  }
  ```
- Export types + functions (list + get detail)

### 2. Barrel Re-export (`apis/seoInsight.api.ts`)
- Add `export * from "./seoInsight.<feature>.api"` in alphabetical order

### 3. Page Component (`pages/admin/seoInsight/<feature>.tsx`)
- Wrap with `withAdmin()` HOC
- Use `<Layout title="...">` wrapper
- Structure: aside (220px sidebar) + divider + main
- Print styles: `@media print` hiding sidebar
- Reuse `CitationsPanel` + `MarkdownContent` from existing components
- `parseCitations()` with `CITATION_RE` — identical to report.tsx (known duplication, extract later)

### 4. Display Helpers
- **NaN guard** on numeric parsers for badge/color functions:
  ```typescript
  const n = Number.parseInt(level.replace(/\D/g, ""), 10);
  if (Number.isNaN(n)) return "bg-[#e5e5e5] text-[#525252]";
  ```
- Monochrome color scheme: `bg-black text-white` (high) → `bg-[#f5f5f5] text-[#525252]` (low)

### 5. Navigation
- Add entry in `components/admin/navigation-items.ts` under "SEO 管理" group

### 6. Worktree Workflow
- Create worktree from main (not from merged feature branches)
- Branch naming: avoid hierarchical names if parent name exists as branch (e.g., `hotfix/x` fails if `hotfix` branch exists)

## When to Use
- Creating any new page under `/admin/seoInsight/` in vocus-web-ui
- Adding a new markdown report viewer that reads from seo-knowledge-insight API
