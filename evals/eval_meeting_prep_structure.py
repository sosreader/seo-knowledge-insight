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

_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
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

_EXPECTED_SECTIONS = [
    "〇、執行摘要",
    "一、本週異常地圖",
    "二、業界最新動態",
    "三、深度根因假設",
    "四、顧問視角交叉比對",
    "五、五層審計缺口清單",
    "六、E-E-A-T 現況評估",
    "七、人本七要素分析",
    "八、SEO 成熟度自評",
    "九、會議提問清單",
    "十、會議後行動核查表",
]


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
    """Extract questions grouped by type (A, B, C, D) from S9."""
    questions: dict[str, list[str]] = {"A": [], "B": [], "C": [], "D": []}
    pattern = re.compile(r"- \[ \] \[([ABCD])\d+\]")
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
    found = sum(1 for expected in _EXPECTED_SECTIONS if expected in sections)
    return found / len(_EXPECTED_SECTIONS)


def metadata_valid(output: dict, target: dict) -> float:
    """Check that meeting_prep_meta JSON is parseable with valid schema."""
    if "error" in output:
        return 0.0
    meta = output.get("metadata")
    if meta is None:
        return 0.0

    # Validate required fields
    scores = meta.get("scores", {})
    eeat = scores.get("eeat", {})
    maturity = scores.get("maturity", {})

    # E-E-A-T scores must be 1-5
    eeat_valid = all(
        isinstance(eeat.get(k), (int, float)) and 1 <= eeat.get(k, 0) <= 5
        for k in ["experience", "expertise", "authoritativeness", "trustworthiness"]
    )

    # Maturity levels must be L1-L4
    valid_levels = {"L1", "L2", "L3", "L4"}
    maturity_valid = all(
        maturity.get(k) in valid_levels
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
    """Check that all questions have source annotations (來源：S...)."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")

    # Find all question lines
    q_lines = re.findall(r"- \[ \] \[[ABCD]\d+\] .+", content)
    if not q_lines:
        return 0.0

    # Check each has a source annotation
    annotated = sum(1 for line in q_lines if re.search(r"[（(]來源：S\d", line))
    return annotated / len(q_lines)


def eeat_score_format(output: dict, target: dict) -> float:
    """Check that S6 E-E-A-T table has 4 rows with 1-5 integer scores."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s6 = _extract_section_content(content, "六、E-E-A-T 現況評估")
    if not s6:
        return 0.0

    # Parse table rows: | **Dimension** | N/5 | ...
    # Only match from table rows, not free text
    score_rows = re.findall(r"^\|[^|]*\|\s*(\d+)/5\s*\|", s6, re.MULTILINE)
    if len(score_rows) != 4:
        return 0.0

    # Validate all scores are 1-5
    return 1.0 if all(1 <= int(s) <= 5 for s in score_rows) else 0.0


def maturity_level_format(output: dict, target: dict) -> float:
    """Check that S8 maturity table has 4 rows with L1-L4 levels."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s8 = _extract_section_content(content, "八、SEO 成熟度自評")
    if not s8:
        return 0.0

    # Parse table rows: | **Dimension** | L2 ... | ...
    level_rows = re.findall(r"^\|[^|]*\|\s*(L[1-4])\s", s8, re.MULTILINE)
    return 1.0 if len(level_rows) == 4 else 0.0


def s3_hypothesis_structure(output: dict, target: dict) -> float:
    """Check S3 has >= N ### subsections, each with >= 3 hypothesis rows."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s3 = _extract_section_content(content, "三、深度根因假設")
    if not s3:
        return 0.0

    min_subsections = target.get("s3_anomaly_subsections_min", 3)

    # Find ### subsections
    subsections = re.split(r"^### ", s3, flags=re.MULTILINE)[1:]  # skip pre-heading
    if len(subsections) < min_subsections:
        return len(subsections) / min_subsections

    # Check each subsection has >= 3 hypothesis rows (| H\d |)
    compliant = 0
    for sub in subsections:
        hypotheses = re.findall(r"^\|\s*H\d[a-z]?\s*\|", sub, re.MULTILINE)
        if len(hypotheses) >= 3:
            compliant += 1

    return compliant / len(subsections)


def s5_all_layers_present(output: dict, target: dict) -> float:
    """Check S5 contains all 5 audit layers (L1-L5)."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s5 = _extract_section_content(content, "五、五層審計缺口清單")
    if not s5:
        return 0.0

    expected_count = target.get("s5_layer_count", 5)
    # Match table rows starting with | L1, | L2, etc.
    layers_found = set(re.findall(r"^\|\s*(L[1-5])\s", s5, re.MULTILINE))
    return len(layers_found) / expected_count


def s7_seven_elements(output: dict, target: dict) -> float:
    """Check S7 has 7 numbered element rows in the table."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s7 = _extract_section_content(content, "七、人本七要素分析")
    if not s7:
        return 0.0

    expected_count = target.get("s7_element_count", 7)
    # Match table rows: | N | **Element** | ...
    elements = re.findall(r"^\|\s*\d+\s*\|", s7, re.MULTILINE)
    return 1.0 if len(elements) >= expected_count else len(elements) / expected_count


def s10_checklist_present(output: dict, target: dict) -> float:
    """Check S10 has >= N checklist items (- [ ])."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s10 = _extract_section_content(content, "十、會議後行動核查表")
    if not s10:
        return 0.0

    min_items = target.get("s10_checklist_min", 5)
    items = re.findall(r"^- \[ \]", s10, re.MULTILINE)
    return 1.0 if len(items) >= min_items else len(items) / min_items


def _parse_s8_table_levels(s8_content: str) -> dict[str, str]:
    """Parse maturity levels from S8 table rows.

    Expects rows like: | **策略（Strategy）** | L2 發展 | ... |
    Returns: {"strategy": "L2", "process": "L2", ...}
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
                m = re.search(r"(L[1-4])", line)
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

    meta_maturity = meta.get("scores", {}).get("maturity", {})
    if not meta_maturity:
        return 0.0

    content = output.get("raw_content", "")
    s8 = _extract_section_content(content, "八、SEO 成熟度自評")
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
    """S10 checklist should contain maturity upgrade markers [LX→LY]."""
    if "error" in output:
        return 0.0
    content = output.get("raw_content", "")
    s10 = _extract_section_content(content, "十、會議後行動核查表")
    if not s10:
        return 0.0

    labels = re.findall(
        r"\[(?:策略|流程|關鍵字|指標)\s*L[1-4]→L[1-4]\]", s10
    )
    items = re.findall(r"- \[ \]", s10)
    if not items:
        return 0.0
    # At least 30% of checklist items should have upgrade labels
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
