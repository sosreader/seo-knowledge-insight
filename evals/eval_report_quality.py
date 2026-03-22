"""
Laminar offline evaluation: Report quality (L1 + L2 → composite_v2).

Verifies that the report evaluator code produces consistent scores
on golden fixture reports and that scores meet minimum thresholds.

Dataset:  eval/golden_report_quality.json
Fixtures: eval/fixtures/reports/*.md
Thresholds: eval/eval_thresholds.json → report_quality_v2

Run:
    python evals/eval_report_quality.py
    python evals/eval_report_quality.py --report path/to/report.md
    python evals/eval_report_quality.py --limit 1
    lmnr eval evals/eval_report_quality.py
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

from scripts._eval_report import (  # noqa: E402
    compute_composite_v2,
    evaluate_report,
    evaluate_report_l2,
)

logger = logging.getLogger(__name__)

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Report quality eval")
_parser.add_argument(
    "--report", type=str, default=None, help="Single report path to evaluate"
)
_parser.add_argument(
    "--limit", type=int, default=0, help="Limit golden cases (0=all)"
)
_args, _unknown = _parser.parse_known_args()


# ── Pure evaluator functions ─────────────────────────────────────────────────


def _load_thresholds() -> dict[str, float]:
    """Load report_quality_v2 thresholds from eval_thresholds.json."""
    thresholds_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
    if not thresholds_path.exists():
        return {}
    with open(thresholds_path, encoding="utf-8") as f:
        return json.load(f).get("report_quality_v2", {})


def _evaluate_case(case: dict) -> dict[str, float]:
    """Run L1 + L2 evaluation on a single golden report."""
    report_path = PROJECT_ROOT / case["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Report fixture not found: %s", report_path)
        return {}

    l1 = evaluate_report(content, [])
    l2 = evaluate_report_l2(content)
    cv2 = compute_composite_v2(l1["report_overall"], l2)

    return {
        "section_coverage": l1["report_section_coverage"],
        "has_kb_links": l1["report_has_links"],
        "cross_metric_reasoning": l2["report_cross_metric_reasoning"],
        "action_specificity": l2["report_action_specificity"],
        "composite_v2": cv2,
    }


def _check_thresholds(
    scores: dict[str, float], thresholds: dict[str, float]
) -> dict[str, float]:
    """Return 1.0 for each threshold check that passes, 0.0 for failures."""
    results: dict[str, float] = {}
    threshold_map = {
        "composite_v2": thresholds.get("composite_v2", 0.65),
        "section_coverage": thresholds.get("section_coverage", 1.0),
        "has_kb_links": thresholds.get("has_kb_links", 1.0),
        "action_specificity": thresholds.get("action_specificity", 0.5),
        "cross_metric_reasoning": thresholds.get("cross_metric_reasoning", 0.25),
    }
    for metric, threshold in threshold_map.items():
        actual = scores.get(metric, 0.0)
        passed = actual >= threshold
        results[f"{metric}_pass"] = 1.0 if passed else 0.0
        if not passed:
            logger.warning("FAIL: %s=%.4f < %s", metric, actual, threshold)
    return results


# ── Main entry point ─────────────────────────────────────────────────────────


def run_eval() -> None:
    """Load golden dataset, evaluate, and push results."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    golden_path = PROJECT_ROOT / "eval" / "golden_report_quality.json"
    if not golden_path.exists():
        logger.error("Golden dataset not found: %s", golden_path)
        sys.exit(1)

    with open(golden_path, encoding="utf-8") as f:
        golden: list[dict] = json.load(f)

    # --report: ad-hoc single report evaluation
    if _args.report:
        if not golden:
            logger.error("--report requires at least one golden case for thresholds")
            sys.exit(1)
        golden = [
            {
                "id": "adhoc",
                "report_path": _args.report,
                "expected": golden[0]["expected"],
            }
        ]

    if _args.limit > 0:
        golden = golden[: _args.limit]
        logger.info("Limiting to %d golden cases", _args.limit)

    thresholds = _load_thresholds()

    # Filter to only existing fixture files
    golden_filtered: list[dict] = []
    for case in golden:
        report_file = PROJECT_ROOT / case["report_path"]
        if report_file.exists():
            golden_filtered.append(case)
        else:
            logger.warning(
                "Skipping %s: fixture not found at %s", case["id"], report_file
            )

    if not golden_filtered:
        logger.warning("No fixture files found. Skipping.")
        sys.exit(0)

    # ── Laminar integration ──────────────────────────────────────────────────

    try:
        from lmnr import evaluate  # type: ignore[import]

        def _executor(inputs: dict) -> dict:
            case_id = inputs["id"]
            case = next(
                (c for c in golden_filtered if c["id"] == case_id), None
            )
            if case is None:
                raise ValueError(f"Golden case not found for id={case_id!r}")
            scores = _evaluate_case(case)
            if not scores:
                return {}
            checks = _check_thresholds(scores, thresholds)
            return {**scores, **checks}

        def _composite_v2_pass(output: dict, target: dict) -> float:  # noqa: ARG001
            return output.get("composite_v2_pass", 0.0)

        def _section_coverage_pass(output: dict, target: dict) -> float:  # noqa: ARG001
            return output.get("section_coverage_pass", 0.0)

        def _has_kb_links_pass(output: dict, target: dict) -> float:  # noqa: ARG001
            return output.get("has_kb_links_pass", 0.0)

        def _action_specificity_pass(output: dict, target: dict) -> float:  # noqa: ARG001
            return output.get("action_specificity_pass", 0.0)

        def _cross_metric_reasoning_pass(output: dict, target: dict) -> float:  # noqa: ARG001
            return output.get("cross_metric_reasoning_pass", 0.0)

        data = [
            {"data": {"id": case["id"]}, "target": {"id": case["id"]}}
            for case in golden_filtered
        ]

        evaluate(
            data=data,
            executor=_executor,
            evaluators={
                "composite_v2_pass": _composite_v2_pass,
                "section_coverage_pass": _section_coverage_pass,
                "has_kb_links_pass": _has_kb_links_pass,
                "action_specificity_pass": _action_specificity_pass,
                "cross_metric_reasoning_pass": _cross_metric_reasoning_pass,
            },
            group_name="report-quality-v2",
        )
        logger.info("Evaluated %d golden reports", len(golden_filtered))

    except ImportError:
        # Fallback: run without Laminar
        logger.warning("lmnr not installed, running standalone")
        all_passed = True
        for case in golden_filtered:
            scores = _evaluate_case(case)
            if not scores:
                logger.error("Empty scores for %s", case["id"])
                all_passed = False
                continue
            checks = _check_thresholds(scores, thresholds)
            case_passed = all(v == 1.0 for v in checks.values())
            status = "PASS" if case_passed else "FAIL"
            logger.info(
                "[%s] %s  composite_v2=%.4f",
                status, case["id"], scores["composite_v2"],
            )
            if not case_passed:
                all_passed = False

        if not all_passed:
            sys.exit(1)
        logger.info("All %d golden reports passed", len(golden_filtered))


if __name__ == "__main__":
    run_eval()
