"""
Laminar offline evaluation: Meeting-prep report structure quality.

Tests whether generated meeting-prep reports have correct structure:
- All 11 H2 sections present
- Valid metadata and citation JSON blocks
- Question counts within spec ranges
- E-E-A-T and maturity table formats
- Section-specific structural requirements (S3, S5, S7, S10)

Dataset:  eval/golden_meeting_prep.json
Fixtures: eval/fixtures/meeting_prep/*.md
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_meeting_prep_structure.py
    python evals/eval_meeting_prep_structure.py --report path/to/report.md
    python evals/eval_meeting_prep_structure.py --limit 1
    lmnr eval evals/eval_meeting_prep_structure.py
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Meeting-prep structure eval")
_parser.add_argument(
    "--report", type=str, default=None, help="Single report path to evaluate"
)
_parser.add_argument(
    "--limit", type=int, default=0, help="Limit golden cases (0=all)"
)
_args, _unknown = _parser.parse_known_args()

# ── Golden dataset ────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep_structure.json"
if not _golden_path.exists():
    print(
        f"[eval_meeting_prep_structure] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _args.report:
    if not _golden_raw:
        print(
            "[eval_meeting_prep_structure] --report requires at least one golden case "
            "to borrow expected_structure from; golden file is empty.",
            file=sys.stderr,
        )
        sys.exit(1)
    _golden_raw = [
        {
            "id": "adhoc",
            "report_path": _args.report,
            "expected_structure": _golden_raw[0]["expected_structure"],
        }
    ]

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]
    print(f"[eval_meeting_prep_structure] Limiting to {_args.limit} golden cases")

# Filter to only existing fixture files
_golden_filtered: list[dict] = []
for case in _golden_raw:
    if case.get("calibration_only", False):
        continue
    report_file = PROJECT_ROOT / case["report_path"]
    if report_file.exists():
        _golden_filtered.append(case)
    else:
        print(
            f"[eval_meeting_prep_structure] Skipping {case['id']}: "
            f"fixture not found at {report_file}",
            file=sys.stderr,
        )

if not _golden_filtered:
    print("[eval_meeting_prep_structure] No fixture files found. Skipping.", file=sys.stderr)
    sys.exit(0)

_dataset = [
    {
        "data": {"report_path": case["report_path"]},
        "target": case["expected_structure"],
    }
    for case in _golden_filtered
]

# ── Section definitions ───────────────────────────────────────────────────────

# Current-format H2 titles (skill spec: `Section N：...`, retired Chinese-numeral
# `〇、一、…` form). Matched by prefix so volatile suffixes such as
# `Section 9：會議提問清單（核心輸出）` still resolve.
_EXPECTED_SECTIONS = [
    "Section 0：執行摘要",
    "Section 1：本週異常地圖",
    "Section 2：業界最新動態",
    "Section 3：深度根因假設",
    "Section 4：顧問視角交叉比對",
    "Section 5：五層審計缺口清單",
    "Section 6：E-E-A-T 現況評估",
    "Section 7：人本七要素分析",
    "Section 8：SEO 成熟度自評",
    "Section 9：會議提問清單",
    "Section 10：會議後行動核查表",
]

# Section titles used by _extract_section_content (stable prefix, no suffix).
_S3_TITLE = "Section 3：深度根因假設"
_S5_TITLE = "Section 5：五層審計缺口清單"
_S6_TITLE = "Section 6：E-E-A-T 現況評估"
_S7_TITLE = "Section 7：人本七要素分析"
_S8_TITLE = "Section 8：SEO 成熟度自評"
_S10_TITLE = "Section 10：會議後行動核查表"

# Maturity level token, allowing half-levels (L2.5, L3.5).
_LEVEL_RE = r"L[1-4](?:\.\d)?"


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_sections(content: str) -> list[str]:
    """Extract H2 section titles from Markdown content."""
    return re.findall(r"^## (.+)$", content, re.MULTILINE)


def _parse_meta(content: str) -> dict | None:
    """Extract meeting_prep_meta JSON from HTML comment."""
    match = re.search(
        r"<!--\s*meeting_prep_meta\s+(\{.*?\})\s*-->", content, re.DOTALL
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _parse_citations(content: str) -> list[dict] | None:
    """Extract citations JSON array from HTML comment."""
    match = re.search(r"<!--\s*citations\s+(\[.*?\])\s*-->", content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _parse_questions(content: str) -> dict[str, list[str]]:
    """Extract questions grouped by type (A, B, C, D) from S9.

    Current format uses bold headers `**A1 [NEW]**：...` (retired the
    `- [ ] [A1] ...` checklist form). Anchored to line start + a trailing
    ``[`` delta tag so bold metric spans in question bodies never match.
    """
    questions: dict[str, list[str]] = {"A": [], "B": [], "C": [], "D": []}
    pattern = re.compile(r"^\*\*([ABCD])\d+\s*\[", re.MULTILINE)
    for match in pattern.finditer(content):
        q_type = match.group(1)
        questions[q_type].append(match.group(0))
    return questions


def _extract_section_content(content: str, section_title: str) -> str:
    """Extract content between a section heading and the next H2."""
    pattern = re.compile(
        rf"^## {re.escape(section_title)}.*?\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    return match.group(1) if match else ""


# ── Executor ──────────────────────────────────────────────────────────────────


def executor(data: dict) -> dict:
    """Read .md file -> parse structure -> return structured dict."""
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Report file not found: %s", report_path)
        return {"error": f"File not found: {report_path}"}

    return {
        "sections": _parse_sections(content),
        "metadata": _parse_meta(content),
        "citations": _parse_citations(content),
        "questions": _parse_questions(content),
        "raw_content": content,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────


def section_completeness(output: dict, target: dict) -> float:
    """Check that all 11 expected H2 sections are present."""
    if "error" in output:
        return 0.0
    sections = output.get("sections", [])
    found = sum(
        1
        for expected in _EXPECTED_SECTIONS
        if any(sec.startswith(expected) for sec in sections)
    )
    return found / len(_EXPECTED_SECTIONS)


def metadata_valid(output: dict, target: dict) -> float:
    """Check that meeting_prep_meta JSON is parseable with valid schema.

    Current schema uses top-level `eeat_avg` (single 1-5 float) + top-level
    `maturity` dict with half-levels (L2.5/L3.5); retired the nested
    `scores.eeat.{experience,...}` / `scores.maturity` form.
    """
    if "error" in output:
        return 0.0
    meta = output.get("metadata")
    if meta is None:
        return 0.0

    # E-E-A-T average must be numeric 1-5
    eeat_avg = meta.get("eeat_avg")
    eeat_valid = isinstance(eeat_avg, (int, float)) and 1 <= eeat_avg <= 5

    # Maturity levels must match L1-L4 (optionally half, e.g. L2.5)
    maturity = meta.get("maturity", {})
    level_re = re.compile(rf"^{_LEVEL_RE}$")
    maturity_valid = all(
        isinstance(maturity.get(k), str) and level_re.match(maturity[k])
        for k in ["strategy", "process", "keywords", "metrics"]
    )

    return 1.0 if eeat_valid and maturity_valid else 0.0


def citation_block_valid(output: dict, target: dict) -> float:
    """Check that citations JSON array is parseable."""
    if "error" in output:
        return 0.0
    citations = output.get("citations")
    return 1.0 if citations is not None and isinstance(citations, list) else 0.0


def question_count_valid(output: dict, target: dict) -> float:
    """Check that S9 question counts are within spec ranges."""
    if "error" in output:
        return 0.0
    questions = output.get("questions", {})
    ranges = target.get("question_by_type", {"A": [3, 5], "B": [4, 6], "C": [2, 3], "D": [2, 3]})

    total_types = len(ranges)
    if total_types == 0:
        return 1.0

    in_range = 0
    for q_type, (lo, hi) in ranges.items():
        count = len(questions.get(q_type, []))
        if lo <= count <= hi:
            in_range += 1

    return in_range / total_types


def question_source_annotated(output: dict, target: dict) -> float:
    """Fraction of S9 questions carrying a provenance tag.

    Retired the `（來源：S...）` annotation. Current spec traces each question
    via a bracketed tag in its bold header — a Delta lifecycle tag
    (`[NEW]`/`[CARRY-W{n}]`/`[Updated]`/`[Validated]`/`[Discarded]`), a
    trace-source tag (`[TS-...]`), or a KB citation (`[N]`).
    """
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")

    q_lines = re.findall(r"^\*\*[ABCD]\d+.*$", content, re.MULTILINE)
    if not q_lines:
        return 0.0

    tag = re.compile(
        r"\[(?:NEW|CARRY(?:-W\d+)?|Updated|Validated|Discarded|TS-[A-Z]+|\d+)\]"
    )
    annotated = sum(1 for line in q_lines if tag.search(line))
    return annotated / len(q_lines)


def eeat_score_format(output: dict, target: dict) -> float:
    """Check that S6 E-E-A-T table has 4 rows with 1-5 integer scores."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s6 = _extract_section_content(content, _S6_TITLE)
    if not s6:
        return 0.0

    # Score sits in the 2nd cell; may be bold + arrow (**3/5 ↑**) when a
    # dimension changed, and may be a half-score. Four dimensions total,
    # possibly split across "Changed this week" + "No Change" tables.
    score_rows = re.findall(
        r"^\|[^|]*\|\s*\*{0,2}\s*(\d+(?:\.\d)?)/5", s6, re.MULTILINE
    )
    if len(score_rows) != 4:
        return 0.0

    return 1.0 if all(1 <= float(s) <= 5 for s in score_rows) else 0.0


def maturity_level_format(output: dict, target: dict) -> float:
    """Check that S8 maturity table has 4 rows with L1-L4 levels."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s8 = _extract_section_content(content, _S8_TITLE)
    if not s8:
        return 0.0

    # Level sits in the 2nd cell; may be bold + arrow (**L3 ↑**) when changed,
    # and may be a half-level (L2.5). Four maturity dimensions total.
    level_rows = re.findall(
        rf"^\|[^|]*\|\s*\*{{0,2}}\s*({_LEVEL_RE})", s8, re.MULTILINE
    )
    return 1.0 if len(level_rows) == 4 else 0.0


def s3_hypothesis_structure(output: dict, target: dict) -> float:
    """Check S3 has >= N `### H{N}：` subsections, each with >= 3 hypotheses.

    Current format uses `### H1：{指標}` groups each holding `**假設 N（…）**`
    bold hypotheses; retired the `| H1 |` hypothesis-table form.
    """
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s3 = _extract_section_content(content, _S3_TITLE)
    if not s3:
        return 0.0

    min_subsections = target.get("s3_anomaly_subsections_min", 3)

    # Keep only the H-numbered subsections (### H1：…)
    subsections = [
        sub
        for sub in re.split(r"^### ", s3, flags=re.MULTILINE)[1:]
        if re.match(r"H\d", sub)
    ]
    if len(subsections) < min_subsections:
        return len(subsections) / min_subsections

    compliant = 0
    for sub in subsections:
        hypotheses = re.findall(r"^\*\*假設\s*\d", sub, re.MULTILINE)
        if len(hypotheses) >= 3:
            compliant += 1

    return compliant / len(subsections)


def s5_all_layers_present(output: dict, target: dict) -> float:
    """Check S5 contains all 5 audit layers (L1-L5)."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s5 = _extract_section_content(content, _S5_TITLE)
    if not s5:
        return 0.0

    expected_count = target.get("s5_layer_count", 5)
    # 1st cell may be bold (| **L1 技術層** |).
    layers_found = set(
        re.findall(r"^\|\s*\*{0,2}\s*(L[1-5])", s5, re.MULTILINE)
    )
    return len(layers_found) / expected_count


def s7_seven_elements(output: dict, target: dict) -> float:
    """Check S7 has 7 numbered element rows in the table."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s7 = _extract_section_content(content, _S7_TITLE)
    if not s7:
        return 0.0

    expected_count = target.get("s7_element_count", 7)
    # Elements are named rows carrying a N/5 score (retired the `| N |`
    # numbered form), possibly split across Changed + No-Change tables.
    # Count rows (not score occurrences) so a Changed row with 上週/本週
    # scores still counts once.
    elements = [
        line
        for line in s7.splitlines()
        if line.lstrip().startswith("|") and re.search(r"\d+(?:\.\d)?/5", line)
    ]
    return 1.0 if len(elements) >= expected_count else len(elements) / expected_count


def s10_checklist_present(output: dict, target: dict) -> float:
    """Check S10 has >= N checklist items (- [ ])."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s10 = _extract_section_content(content, _S10_TITLE)
    if not s10:
        return 0.0

    min_items = target.get("s10_checklist_min", 5)
    items = _s10_action_items(s10)
    return 1.0 if len(items) >= min_items else len(items) / min_items


def _s10_action_items(s10_content: str) -> list[str]:
    """Return S10 action rows.

    Current format is a priority table (`| 🔴 P0 | … |`); falls back to the
    retired `- [ ]` checklist form.
    """
    rows = re.findall(r"^\|[^|]*\bP\d.*$", s10_content, re.MULTILINE)
    if rows:
        return rows
    return re.findall(r"^- \[ \].*$", s10_content, re.MULTILINE)


def _parse_s8_table_levels(s8_content: str) -> dict[str, str]:
    """Parse maturity levels from S8 table rows.

    Rows like `| Strategy（策略）| L2.5（L2→L3 邊緣）| … |` or a Changed
    `| Process（流程）| **L3 ↑** | … |`. re.search takes the first level token
    per row (the level cell), so it tolerates half-levels and bold wrappers.
    Returns e.g. {"strategy": "L2.5", "process": "L3", ...}.
    """
    dim_map = {
        "策略": "strategy",
        "流程": "process",
        "關鍵字": "keywords",
        "指標": "metrics",
    }
    levels: dict[str, str] = {}
    for line in s8_content.splitlines():
        if not line.strip().startswith("|"):
            continue
        for zh_name, en_key in dim_map.items():
            if zh_name in line:
                m = re.search(rf"({_LEVEL_RE})", line)
                if m:
                    levels[en_key] = m.group(1)
                break
    return levels


def s8_meta_maturity_consistency(output: dict, target: dict) -> float:
    """Meta JSON maturity levels must match S8 table levels."""
    if "error" in output:
        return 0.0
    meta = output.get("metadata")
    if not meta:
        return 0.0

    meta_maturity = meta.get("maturity", {})
    if not meta_maturity:
        return 0.0

    content = output.get("raw_content", "")
    s8 = _extract_section_content(content, _S8_TITLE)
    if not s8:
        return 0.0

    s8_levels = _parse_s8_table_levels(s8)
    if not s8_levels:
        return 0.0

    expected_keys = ["strategy", "process", "keywords", "metrics"]
    matches = sum(
        1 for k in expected_keys
        if meta_maturity.get(k) == s8_levels.get(k)
    )
    return matches / len(expected_keys)


def s10_maturity_upgrade_labeled(output: dict, target: dict) -> float:
    """S10 action items should carry maturity markers `[… LX→LY]`.

    Current label form is `[{層} {維度} L{X}→L{Y}]` (e.g. `[L2 內容 L3→L3]`,
    `[Process L3→L4]`) with optional half-levels; retired the
    `[策略 L2→L3]` form. Hold markers (L3→L3) count — the point is that every
    item is labeled, not that every item upgrades.
    """
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s10 = _extract_section_content(content, _S10_TITLE)
    if not s10:
        return 0.0

    labels = re.findall(
        rf"\[[^\[\]]*{_LEVEL_RE}\s*→\s*{_LEVEL_RE}\]", s10
    )
    items = _s10_action_items(s10)
    if not items:
        return 0.0
    # At least 30% of action items should carry an upgrade/hold label
    return min(len(labels) / max(len(items) * 0.3, 1), 1.0)


# ── Evaluator map ─────────────────────────────────────────────────────────────

_EVALUATOR_MAP = {
    "section_completeness": section_completeness,
    "metadata_valid": metadata_valid,
    "citation_block_valid": citation_block_valid,
    "question_count_valid": question_count_valid,
    "question_source_annotated": question_source_annotated,
    "eeat_score_format": eeat_score_format,
    "maturity_level_format": maturity_level_format,
    "s3_hypothesis_structure": s3_hypothesis_structure,
    "s5_all_layers_present": s5_all_layers_present,
    "s7_seven_elements": s7_seven_elements,
    "s10_checklist_present": s10_checklist_present,
    "s8_meta_maturity_consistency": s8_meta_maturity_consistency,
    "s10_maturity_upgrade_labeled": s10_maturity_upgrade_labeled,
}

# ── Threshold gate (CI eval gate) ─────────────────────────────────────────────

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _run_threshold_gate() -> None:
    """Run meeting_prep_structure threshold gate and populate executor cache."""
    global _exec_cache

    if not _threshold_path.exists():
        _exec_cache = {}
        return

    with open(_threshold_path, encoding="utf-8") as _tf:
        thresholds: dict[str, float] = json.load(_tf).get(
            "meeting_prep_structure", {}
        )

    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_structure thresholds ---")

    pre_results = [(executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {
        dp["data"]["report_path"]: out
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
        print(
            "\nCI eval gate FAILED. Fix regressions before merging.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("All meeting_prep_structure thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
    """Return pre-computed result if available (skip error cache), otherwise call executor."""
    cached = _exec_cache.get(data["report_path"])
    if cached is not None and "error" not in cached:
        return cached
    return executor(data)


# ── Run ───────────────────────────────────────────────────────────────────────


def run_eval() -> None:
    """Run threshold gate and Laminar evaluation."""
    _run_threshold_gate()

    evaluate(
        data=_dataset,
        executor=_cached_executor if _threshold_path.exists() else executor,
        evaluators=_EVALUATOR_MAP,
        group_name="meeting_prep_structure",
    )


if __name__ == "__main__":
    run_eval()
