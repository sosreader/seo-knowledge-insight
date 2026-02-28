---
name: batch-code-quality-fix-workflow
description: "Systematic code review issue fix workflow: identify → prioritize → batch fix → test → commit"
user-invocable: false
origin: auto-extracted
confidence: 0.85
---

# Batch Code Quality Fix Workflow

**Extracted:** 2026-02-28
**Context:** Fixed 5 HIGH + 7 MEDIUM code quality issues across 8 files in a single coordinated session

## Problem

Large code reviews can identify dozens of issues scattered across multiple files, making it hard to:
- Know which fixes to tackle first (CRITICAL vs HIGH vs MEDIUM)
- Avoid duplicating similar fixes across files
- Verify fixes don't break anything
- Create a clear, trackable commit

## Solution

### Phase 1: Triage & Prioritize

Run code review tools and categorize by severity:

```
CRITICAL (2 issues) → Fix immediately
HIGH (8 issues) → Fix before test
MEDIUM (7 issues) → Fix after tests pass
```

Create a Task List with 7 focused tasks:

```
Task 1: utils/pipeline_deps.py (assert → if/raise, datetime, logging, imports)
Task 2: utils/openai_helper.py (observe shim dedup)
Task 3: config.py + hardcoded models (05_evaluate.py, 04_generate_report.py)
Task 4: 04_generate_report.py (METRIC_QUERY_MAP dedup)
Task 5: 03_dedupe_classify.py (dict mutation → immutability)
Task 6: 05_evaluate.py (mypy types) + all f-string cleanup
Task 7: Run tests + commit
```

### Phase 2: Batch Fixes by Category

Instead of fixing one-by-one across files, group by fix type:

#### 2a. Critical Structural Fixes

```python
# Task 1: utils/pipeline_deps.py
assert dep.glob_pattern is not None  # ❌ BAD
↓
if dep.glob_pattern is None:  # ✅ GOOD
    raise ValueError(...)

mtime = datetime.now()  # ❌ BAD (DST issue)
↓
mtime = datetime.now(tz=timezone.utc)  # ✅ GOOD
```

#### 2b. Configuration Centralization

```python
# Task 3: All hardcoded models → config constants
# Before (5 scattered locations):
model="gpt-5-mini",
model="gpt-5-nano",

# After (all 5 use config):
model=config.EVAL_JUDGE_MODEL,
model=config.EVAL_RERANK_MODEL,
```

#### 2c. Immutability Refactor

```python
# Task 5: Dict mutation → immutability
# Before
def classify_all_qas(qa_pairs):
    for qa in qa_pairs:
        qa["category"] = "..."  # Direct mutation
    return qa_pairs

# After
def classify_all_qas(qa_pairs):
    return [
        {**qa, "category": "..."}  # New dict each time
        for qa in qa_pairs
    ]
```

#### 2d. Batch Text Cleanup

```python
# Task 6: Remove f-string prefixes on non-templated strings
# Python regex fix:
re.sub(r'f"([^{]*)"', r'"\1"', content)

# Applies to all scripts/*.py in one pass
```

### Phase 3: Verify After Each Task

```bash
# After Task 1, 2, 3, 4, 5:
git diff HEAD -- <modified-files>  # Review the changes
git status  # Sanity check

# After Task 6:
.venv/bin/python -m pytest tests/ -q  # Full suite
# ✅ 129 tests passing
```

### Phase 4: Single Comprehensive Commit

```bash
git add -A
git commit -m "fix: 修復 5 個 HIGH + 7 個 MEDIUM 程式碼品質問題（129 tests ✓）"
```

## Benefits

| Aspect | Single-Issue Fix | Batch Workflow |
|--------|-----------------|-----------------|
| Time | 7 small commits | 1 large commit |
| Clarity | Scattered context | Clear pattern grouping |
| Testing | 7× test runs | 1 final test run |
| Review | Hard to see scope | Reviewer sees full picture |
| Revert | Risky (affects one issue) | Clean (all-or-nothing) |

## Checklist

- [ ] Run code review tools (ruff, mypy, bandit)
- [ ] Categorize issues by severity
- [ ] Create task list with focused scopes
- [ ] Group fixes by type (structure, config, idiom, style)
- [ ] Fix in priority order (CRITICAL → HIGH → MEDIUM)
- [ ] Verify each task doesn't break existing tests
- [ ] Run full test suite before final commit
- [ ] Write comprehensive commit message summarizing all fixes
- [ ] Include test results in commit message (e.g., "129 tests ✓")

## When to Use This Workflow

**Triggers:**
- Code review identifies 10+ issues across 5+ files
- Mix of severity levels (CRITICAL, HIGH, MEDIUM)
- Similar patterns to fix in multiple places
- Large refactoring that benefits from atomicity

**Avoid for:**
- Single-file fixes
- Emergency hotfixes (commit early)
- Features (use separate PR per feature)

## Anti-patterns

❌ Fix one issue, commit, fix another, commit, commit, commit...
→ Hard to see overall scope, too many small PRs

✅ Batch related issues, comprehensive commit
→ Clear intent, reviewable scope, atomicity

## Related Patterns

- **Code Review Automation** - Use tools to identify issues systematically
- **Test Coverage** - Ensure 80%+ before batch commit
- **Task Tracking** - Use Task List to manage fix scope
