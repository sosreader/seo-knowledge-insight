"""
Local report quality evaluation — no Laminar, no API dependency.

Imports evaluate_report, evaluate_report_l2, compute_composite_v3 from
scripts/_eval_report.py and outputs machine-readable results for the
autoresearch report optimization loop.

Usage:
    .venv/bin/python autoresearch/report/eval_local.py \
        --report eval/fixtures/reports/report_20260321_c202663e.md
    .venv/bin/python autoresearch/report/eval_local.py \
        --report /tmp/autoresearch_report.md \
        --alert-names "Discover,外部連結,檢索未索引"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._eval_report import (  # noqa: E402
    compute_composite_v3,
    evaluate_report,
    evaluate_report_l2,
)

# ── CLI ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(
    description="Local report eval for autoresearch (composite_v3)"
)
parser.add_argument("--report", required=True, help="Report Markdown path")
parser.add_argument(
    "--alert-names",
    default="",
    help="Comma-separated ALERT_DOWN metric names (empty = full credit)",
)
args = parser.parse_args()

# ── Load report ──────────────────────────────────────────────────────────

report_path = Path(args.report)
if not report_path.exists():
    print(f"Report not found: {report_path}", file=sys.stderr)
    sys.exit(1)

content = report_path.read_text(encoding="utf-8")
alert_names = [n.strip() for n in args.alert_names.split(",") if n.strip()]

# ── Evaluate ─────────────────────────────────────────────────────────────

l1 = evaluate_report(content, alert_names or [])
l2 = evaluate_report_l2(content)
composite = compute_composite_v3(l1, l2)

# ── stderr: human-readable debug table ───────────────────────────────────

print("\n── Report Eval (composite_v3) ──", file=sys.stderr)
print("  [L1]", file=sys.stderr)
for key in [
    "report_overall", "report_section_coverage", "report_kb_citations",
    "report_has_research", "report_has_links", "report_alert_coverage",
    "report_action_maturity_labeled",
]:
    val = l1[key]
    bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
    print(f"    {key:<40} {val:.4f}  {bar}", file=sys.stderr)

print("  [L2]", file=sys.stderr)
for key, val in l2.items():
    bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
    print(f"    {key:<40} {val:.4f}  {bar}", file=sys.stderr)

print(f"  [Composite V3]", file=sys.stderr)
bar = "█" * int(composite * 10) + "░" * (10 - int(composite * 10))
print(f"    {'composite_v3':<40} {composite:.4f}  {bar}", file=sys.stderr)
print(file=sys.stderr)

# ── stdout: machine-readable (agent parses these) ────────────────────────

metrics_values = [
    l1["report_overall"],
    l1["report_section_coverage"],
    l1["report_kb_citations"],
    l1["report_has_research"],
    l1["report_has_links"],
    l1["report_alert_coverage"],
    l1["report_action_maturity_labeled"],
    l2["report_cross_metric_reasoning"],
    l2["report_action_specificity"],
    l2["report_data_evidence_ratio"],
    l2["report_citation_integration"],
    l2["report_quadrant_judgment"],
    l2["report_section_depth_variance"],
    l2["report_temporal_dual_frame"],
    l2["report_causal_chain"],
    l2["report_priority_balance"],
    l2["report_top_recommendation"],
]

print("METRICS=" + "\t".join(f"{v:.6f}" for v in metrics_values))
print(f"REPORT_COMPOSITE={composite:.6f}")
