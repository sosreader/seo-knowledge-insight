---
name: core-flag-alert-bucket-testing
description: "CORE metrics bypass ALERT_DOWN — test enrichment with non-CORE metrics that substring-match"
user-invocable: false
origin: auto-extracted
---

# CORE Flag Alert Bucket Testing Pattern

**Extracted:** 2026-03-16
**Context:** SEO report generator where metrics are categorized into CORE / ALERT_DOWN / ALERT_UP buckets, and enrichment (maturity upgrade labels) is applied only to ALERT_DOWN items.

## Problem
When adding inline annotations (e.g. `**[流程 L2→L3]**`) to action items built from `down` (ALERT_DOWN) metrics, tests using CORE metrics (AMP Article, CTR, etc.) will always fail because `detectAlerts()` prioritizes CORE classification over ALERT thresholds. All metrics in `METRIC_MATURITY_DIMENSION_MAP` happen to also be in `CORE_METRICS`, creating a 100% miss rate in naive test data.

## Solution
Use non-CORE metric names that **substring-match** a dimension map key:

```typescript
// BAD: "AMP Article" is CORE → flag="CORE", never enters `down`
const metrics = { "AMP Article": { monthly: -0.5, weekly: -0.3 } };

// GOOD: "AMP Article 內頁" is NOT in CORE_METRICS → flag="ALERT_DOWN"
// getDimensionForMetric("AMP Article 內頁") → substring matches "AMP Article" → "process"
const metrics = { "AMP Article 內頁": { monthly: -0.4, weekly: -0.25 } };
```

The key insight: `detectAlerts()` uses `CORE_METRICS.has(name)` (exact match), while `getDimensionForMetric()` uses substring fallback. Exploit this asymmetry in tests.

## When to Use
- Adding enrichment to filtered/bucketed collections in this project
- Writing tests for `buildPriorityActions()` with maturity labels
- Any time a test expects data in `down` but metrics keep landing in `core`
