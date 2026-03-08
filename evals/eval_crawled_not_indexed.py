"""
Laminar offline evaluation: Crawled-not-indexed analysis quality.

Tests whether the POST /api/v1/pipeline/crawled-not-indexed endpoint:
- Correctly classifies overall severity
- Correctly identifies worsening paths (recall)
- Correctly identifies improving paths (recall)
- Produces markdown that covers all path segments (path_coverage)
- Achieves a minimum overall score

Dataset:  eval/golden_crawled_not_indexed.json
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_crawled_not_indexed.py
    lmnr eval evals/eval_crawled_not_indexed.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── Golden dataset ─────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_crawled_not_indexed.json"
if not _golden_path.exists():
    print(
        f"[eval_crawled_not_indexed] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_dataset = [
    {
        "data": {"raw_tsv": case["input_tsv"]},
        "target": {
            "expected_severity": case["expected_severity"],
            "expected_worsening_paths": case.get("expected_worsening_paths", []),
            "expected_improving_paths": case.get("expected_improving_paths", []),
            "min_path_coverage": case.get("min_path_coverage", 0.8),
            "min_overall_eval": case.get("min_overall_eval", 0.6),
            # Preserve raw_tsv in target so path_coverage can parse segments
            "input_tsv": case["input_tsv"],
        },
    }
    for case in _golden_raw
]


# ── Executor ───────────────────────────────────────────────────────────────────

_API_BASE = os.environ.get("EVAL_API_BASE", "http://localhost:8002")
_API_KEY = os.environ.get("SEO_API_KEY", "")


def executor(data: dict) -> dict:
    """Call POST /api/v1/pipeline/crawled-not-indexed with raw_tsv mode."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if _API_KEY:
        headers["X-API-Key"] = _API_KEY

    try:
        resp = requests.post(
            f"{_API_BASE}/api/v1/pipeline/crawled-not-indexed",
            json={"raw_tsv": data["raw_tsv"]},
            headers=headers,
            timeout=15,
        )
    except requests.ConnectionError:
        logger.warning("[eval_crawled_not_indexed] API not reachable at %s", _API_BASE)
        return {"error": "API not reachable"}
    except Exception as exc:
        logger.warning("[eval_crawled_not_indexed] Request failed: %s", exc)
        return {"error": str(exc)}

    if resp.status_code != 200:
        logger.warning(
            "[eval_crawled_not_indexed] API returned %s: %s",
            resp.status_code,
            resp.text[:200],
        )
        return {"error": f"API returned {resp.status_code}"}

    body = resp.json()
    return body.get("data", {})


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_path_segments(raw_tsv: str) -> list[str]:
    """Extract slash-prefixed path segments from a raw TSV string.

    Rows whose first column starts with '/' are path rows (e.g. /article/, /tag/).
    Summary rows like '總合', '全網域', '差距', '總合/全網域', '檢索未索引 (全部)'
    are excluded.
    """
    segments: list[str] = []
    for line in raw_tsv.splitlines():
        line = line.strip()
        if not line:
            continue
        first_col = line.split("\t")[0].strip()
        if first_col.startswith("/"):
            segments.append(first_col)
    return segments


# ── Evaluators ─────────────────────────────────────────────────────────────────


def severity_accuracy(output: dict, target: dict) -> float:
    """1.0 if overall_severity matches expected_severity, else 0.0."""
    actual = output.get("insight", {}).get("overall_severity", "")
    expected = target.get("expected_severity", "")
    return 1.0 if actual == expected else 0.0


def worsening_path_recall(output: dict, target: dict) -> float:
    """Recall of worsening path segments: found / expected.

    Returns 1.0 when no worsening paths are expected (vacuous truth).
    """
    expected = set(target.get("expected_worsening_paths", []))
    if not expected:
        return 1.0

    actual_list = output.get("insight", {}).get("worsening_paths", [])
    actual_segments = {p.get("segment", "") for p in actual_list}
    found = expected & actual_segments
    return len(found) / len(expected)


def improving_path_recall(output: dict, target: dict) -> float:
    """Recall of improving path segments: found / expected.

    Returns 1.0 when no improving paths are expected (vacuous truth).
    """
    expected = set(target.get("expected_improving_paths", []))
    if not expected:
        return 1.0

    actual_list = output.get("insight", {}).get("improving_paths", [])
    actual_segments = {p.get("segment", "") for p in actual_list}
    found = expected & actual_segments
    return len(found) / len(expected)


def path_coverage(output: dict, target: dict) -> float:
    """Fraction of TSV path segments mentioned in the response markdown.

    Parses the original TSV (stored in target["input_tsv"]) to get the list of
    path segments, then checks how many appear in the markdown output.
    Returns 1.0 when there are no path segments to cover.
    """
    raw_tsv = target.get("input_tsv", "")
    segments = _extract_path_segments(raw_tsv)
    if not segments:
        return 1.0

    markdown = output.get("markdown", "")
    if not markdown:
        return 0.0

    mentioned = sum(1 for seg in segments if seg in markdown)
    return mentioned / len(segments)


def overall(output: dict, target: dict) -> float:
    """Average of the four evaluator scores."""
    scores = [
        severity_accuracy(output, target),
        worsening_path_recall(output, target),
        improving_path_recall(output, target),
        path_coverage(output, target),
    ]
    return sum(scores) / len(scores)


# ── Run ────────────────────────────────────────────────────────────────────────

evaluate(
    data=_dataset,
    executor=executor,
    evaluators={
        "severity_accuracy": severity_accuracy,
        "worsening_path_recall": worsening_path_recall,
        "improving_path_recall": improving_path_recall,
        "path_coverage": path_coverage,
        "overall": overall,
    },
    group_name="crawled_not_indexed_quality",
)
