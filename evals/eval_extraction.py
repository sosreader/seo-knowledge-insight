"""
Laminar offline evaluation: Q&A extraction quality.

Tests whether the per-meeting extraction output contains the expected
number of Q&A pairs and covers the must-extract SEO keywords.

Dataset:  eval/golden_extraction.json + output/qa_per_meeting/
Requires: LMNR_PROJECT_API_KEY, already-extracted qa_per_meeting/ JSONs

Run:
    python evals/eval_extraction.py
    lmnr eval evals/eval_extraction.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lmnr import evaluate  # type: ignore[import]

# ── Dataset ───────────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_extraction.json"
if not _golden_path.exists():
    print(f"[eval_extraction] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_QA_PER_MEETING_DIR = PROJECT_ROOT / "output" / "qa_per_meeting"

# Only include cases where the extraction output already exists on disk.
_dataset: list[dict] = []
for _item in _golden_raw:
    _qa_path = _QA_PER_MEETING_DIR / _item["per_meeting_qa_file"]
    if not _qa_path.exists():
        continue

    with open(_qa_path, encoding="utf-8") as _f:
        _qa_output: dict | list = json.load(_f)

    _dataset.append(
        {
            "data": {
                "source_file": _item["source_file"],
                "qa_output": _qa_output,
            },
            "target": {
                "min_qa_count": _item["min_qa_count"],
                "max_qa_count": _item["max_qa_count"],
                "must_extract_keywords": _item["must_extract_keywords"],
                "should_not_extract": _item.get("should_not_extract", []),
                "description": _item["description"],
            },
        }
    )

if not _dataset:
    print(
        "[eval_extraction] No extraction outputs found in "
        f"{_QA_PER_MEETING_DIR}. Run Step 2 first. Skipping.",
    )
    sys.exit(0)  # graceful skip — extraction eval requires local ETL output


# ── Executor ──────────────────────────────────────────────────────────────────

def extraction_executor(data: dict) -> dict:
    """Return already-extracted QA pairs (no new LLM call)."""
    qa_output = data["qa_output"]
    if isinstance(qa_output, list):
        qa_pairs: list[dict] = qa_output
    elif isinstance(qa_output, dict):
        qa_pairs = qa_output.get("qa_pairs", [])
    else:
        qa_pairs = []

    return {"qa_pairs": qa_pairs, "count": len(qa_pairs)}


# ── Evaluators ────────────────────────────────────────────────────────────────

def qa_count_in_range(output: dict, target: dict) -> float:
    """1 if extracted Q&A count is within [min_qa_count, max_qa_count]."""
    count = output.get("count", 0)
    return 1.0 if target["min_qa_count"] <= count <= target["max_qa_count"] else 0.0


def keyword_coverage(output: dict, target: dict) -> float:
    """Fraction of must-extract keywords present in any extracted Q&A pair."""
    qa_pairs: list[dict] = output.get("qa_pairs", [])
    must_kws: list[str] = target.get("must_extract_keywords", [])

    if not must_kws:
        return 1.0
    if not qa_pairs:
        return 0.0

    pool = " ".join(
        qa.get("question", "") + " "
        + qa.get("answer", "") + " "
        + " ".join(qa.get("keywords", []))
        for qa in qa_pairs
    ).lower()

    hits = sum(1 for kw in must_kws if kw.lower() in pool)
    return hits / len(must_kws)


def no_admin_content(output: dict, target: dict) -> float:
    """1 if none of the extracted Q&A pairs contain admin/schedule content."""
    qa_pairs: list[dict] = output.get("qa_pairs", [])
    should_not: list[str] = target.get("should_not_extract", [])

    if not should_not or not qa_pairs:
        return 1.0

    for qa in qa_pairs:
        text = (qa.get("question", "") + " " + qa.get("answer", "")).lower()
        if any(kw.lower() in text for kw in should_not):
            return 0.0

    return 1.0


def avg_confidence(output: dict, *_: object) -> float:
    """Average confidence score across all extracted Q&A pairs (0–1)."""
    qa_pairs: list[dict] = output.get("qa_pairs", [])
    if not qa_pairs:
        return 0.0

    return sum(qa.get("confidence", 0.0) for qa in qa_pairs) / len(qa_pairs)


# ── Run ───────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=extraction_executor,
    evaluators={
        "qa_count_in_range": qa_count_in_range,
        "keyword_coverage": keyword_coverage,
        "no_admin_content": no_admin_content,
        "avg_confidence": avg_confidence,
    },
    group_name="extraction_quality",
)
