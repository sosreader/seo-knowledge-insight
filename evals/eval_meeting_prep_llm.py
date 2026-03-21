"""
Laminar offline evaluation: Meeting-prep LLM quality threshold gate.

Reads JSON output from /evaluate-meeting-prep-quality (Claude Code as Judge),
runs threshold checks, and pushes to Laminar Dashboard.

Phase A (interactive): /evaluate-meeting-prep-quality -> JSON
Phase B (automated):   this script -> threshold gate + Laminar push

Run:
    python evals/eval_meeting_prep_llm.py
    python evals/eval_meeting_prep_llm.py --json path/to/eval_quality.json
    lmnr eval evals/eval_meeting_prep_llm.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Meeting-prep LLM quality eval")
_parser.add_argument("--json", type=str, default=None, dest="json_path")
_parser.add_argument("--limit", type=int, default=0)
_args, _unknown = _parser.parse_known_args()

# ── Locate quality JSON ────────────────────────────────────────────────────────


def _find_latest_quality_json() -> Path | None:
    candidates = sorted(
        PROJECT_ROOT.glob("output/eval_meeting_prep_quality_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


if _args.json_path:
    _quality_json_path = Path(_args.json_path)
    if not _quality_json_path.is_absolute():
        _quality_json_path = PROJECT_ROOT / _quality_json_path
else:
    _quality_json_path = _find_latest_quality_json()

if _quality_json_path is None or not _quality_json_path.exists():
    print(
        "[eval_meeting_prep_llm] SKIPPED: no quality JSON found, "
        "run /evaluate-meeting-prep-quality first",
        file=sys.stderr,
    )
    sys.exit(0)

logger.debug("Using quality JSON: %s", _quality_json_path)

# ── Validate quality JSON ──────────────────────────────────────────────────────

with open(_quality_json_path, encoding="utf-8") as _f:
    _quality_data: dict = json.load(_f)

if not _quality_data.get("dimensions"):
    print(
        f"[eval_meeting_prep_llm] SKIPPED: JSON missing 'dimensions': {_quality_json_path}",
        file=sys.stderr,
    )
    sys.exit(0)

# ── Golden dataset ─────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
if not _golden_path.exists():
    print(
        f"[eval_meeting_prep_llm] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _gf:
    _golden_raw: list[dict] = json.load(_gf)

if not _golden_raw:
    print("[eval_meeting_prep_llm] Golden dataset is empty.", file=sys.stderr)
    sys.exit(1)

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]
    logger.debug("Limiting to %d golden cases", _args.limit)

_dataset = [
    {
        "data": {"json_path": str(_quality_json_path)},
        "target": case.get("expected_llm", {}),
    }
    for case in _golden_raw
]

# ── Executor ───────────────────────────────────────────────────────────────────


def executor(data: dict) -> dict:
    """Read quality JSON -> extract scores -> return structured dict."""
    json_path = Path(data["json_path"])
    try:
        with open(json_path, encoding="utf-8") as f:
            quality_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        logger.error("Failed to read quality JSON: %s", exc)
        return {"error": str(exc), "scores": {}, "average_score": 0.0}

    dims = quality_data.get("dimensions", {})
    return {
        "scores": {k: v.get("score", 0) for k, v in dims.items()},
        "average_score": quality_data.get("average_score", 0.0),
    }


# ── Evaluators ─────────────────────────────────────────────────────────────────

_DIMENSION_KEYS = (
    "s3_hypothesis_grounded",
    "s6_eeat_justified",
    "s9_question_specificity",
    "s4_contradiction_quality",
    "overall_coherence",
    "s8_maturity_justified",
)


def _make_dimension_evaluator(key: str):
    """Factory: return evaluator that normalises named dimension score to 0-1.

    s8_maturity_justified defaults to 1.0 when absent (pre-maturity reports).
    """
    default = 1.0 if key == "s8_maturity_justified" else 0.0

    def _evaluator(output: dict, target: dict) -> float:
        scores = output.get("scores", {})
        return scores.get(key, default) / 5.0

    _evaluator.__name__ = key
    return _evaluator


def avg_score_above_threshold(output: dict, target: dict) -> float:
    """Average of all present dimension scores normalised to 0-1."""
    scores = list(output.get("scores", {}).values())
    return sum(scores) / len(scores) / 5.0 if scores else 0.0


_EVALUATOR_MAP: dict = {key: _make_dimension_evaluator(key) for key in _DIMENSION_KEYS}
_EVALUATOR_MAP["avg_score_above_threshold"] = avg_score_above_threshold

# ── Threshold gate (CI eval gate) ─────────────────────────────────────────────

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _run_threshold_gate() -> None:
    """Run meeting_prep_llm threshold gate and populate executor cache."""
    global _exec_cache

    if not _threshold_path.exists():
        _exec_cache = {}
        return

    with open(_threshold_path, encoding="utf-8") as tf:
        thresholds: dict[str, float] = json.load(tf).get("meeting_prep_llm", {})

    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_llm thresholds ---")

    pre_results = [(executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {
        dp["data"]["json_path"]: out
        for dp, (out, _) in zip(_dataset, pre_results)
    }

    gate_failed = False
    for metric, min_val in thresholds.items():
        evaluator_fn = _EVALUATOR_MAP.get(metric)
        if not evaluator_fn:
            continue
        scores = [evaluator_fn(out, tgt) for out, tgt in pre_results]
        avg = sum(scores) / len(scores) if scores else 0.0
        if avg < min_val:
            print(f"  FAIL: {metric} = {avg:.4f} < {min_val}", file=sys.stderr)
            gate_failed = True
        else:
            print(f"  PASS: {metric} = {avg:.4f} >= {min_val}")

    if gate_failed:
        print("\nCI eval gate FAILED. Fix regressions before merging.", file=sys.stderr)
        sys.exit(1)
    print("All meeting_prep_llm thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
    """Return pre-computed result if available, otherwise call executor."""
    cached = _exec_cache.get(data["json_path"])
    if cached is not None and "error" not in cached:
        return cached
    return executor(data)


# ── Run ────────────────────────────────────────────────────────────────────────


def run_eval() -> None:
    """Run threshold gate and Laminar evaluation."""
    _run_threshold_gate()

    evaluate(
        data=_dataset,
        executor=_cached_executor if _threshold_path.exists() else executor,
        evaluators=_EVALUATOR_MAP,
        group_name="meeting_prep_llm",
    )


if __name__ == "__main__":
    run_eval()
