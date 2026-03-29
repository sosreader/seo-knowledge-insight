"""
Laminar offline evaluation: Meeting-prep content novelty (L2.6).

Rule-based, zero LLM cost. Detects cross-report repetition by comparing
the current report against the most recent prior report:
- S2 industry news novelty (URL or SITREP tag based)
- S4 cross-reference topic novelty
- E-E-A-T / maturity score drift (penalises copy-paste stasis)
- S7 citation freshness
- Toggle structure compliance (<details> for No Change sections)

Dataset:  eval/golden_meeting_prep.json
Fixtures: eval/fixtures/meeting_prep/*.md
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_meeting_prep_novelty.py
    python evals/eval_meeting_prep_novelty.py --report path/to/report.md
    python evals/eval_meeting_prep_novelty.py --limit 1
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

_parser = argparse.ArgumentParser(description="Meeting-prep novelty eval")
_parser.add_argument("--report", type=str, default=None)
_parser.add_argument("--limit", type=int, default=0)
_args, _unknown = _parser.parse_known_args()

# ── Golden dataset ────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
if not _golden_path.exists():
    print(f"[eval_meeting_prep_novelty] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_DEFAULT_NOVELTY = {
    "s2_novelty_min": 0.40,
    "s4_novelty_min": 0.30,
    "score_drift_novelty_min": 0.10,
    "s7_citation_novelty_min": 0.30,
    "toggle_structure_min": 0.50,
}

if _args.report:
    if not _golden_raw:
        print("[eval_meeting_prep_novelty] --report requires at least one golden case.", file=sys.stderr)
        sys.exit(1)
    _golden_raw = [{
        "id": "adhoc",
        "report_path": _args.report,
        "expected_novelty": _golden_raw[0].get("expected_novelty", _DEFAULT_NOVELTY),
    }]

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]

_golden_filtered = [
    c for c in _golden_raw
    if not c.get("calibration_only", False)
    and ((PROJECT_ROOT / c["report_path"]).exists()
         or not print(f"[eval_meeting_prep_novelty] Skipping {c['id']}: fixture not found", file=sys.stderr))
]

if not _golden_filtered:
    print("[eval_meeting_prep_novelty] No fixture files found. Skipping.", file=sys.stderr)
    sys.exit(0)

_dataset = [
    {"data": {"report_path": c["report_path"]}, "target": c.get("expected_novelty", _DEFAULT_NOVELTY)}
    for c in _golden_filtered
]

# ── Helpers ───────────────────────────────────────────────────────────────────

_MEETING_PREP_RE = re.compile(r"meeting_prep_(\d{8})_([0-9a-f]{8})\.md$")

_SECTION_HEADING_RE = re.compile(
    r"^## (?:Section\s+)?(?:S)?(\d+|[〇一二三四五六七八九十]+)[：、:]",
    re.MULTILINE,
)


def find_prior_report(report_path: Path) -> Path | None:
    """Find the most recent meeting-prep report before the given one.

    Searches in the same directory first, then falls back to output/.
    """
    m = _MEETING_PREP_RE.search(report_path.name)
    if not m:
        return None
    current_date = m.group(1)

    candidates: list[tuple[str, Path]] = []

    # Search in same directory
    for p in report_path.parent.glob("meeting_prep_*.md"):
        pm = _MEETING_PREP_RE.search(p.name)
        if pm and pm.group(1) < current_date:
            candidates.append((pm.group(1), p))

    # Fallback: search in output/
    output_dir = PROJECT_ROOT / "output"
    if output_dir.exists() and output_dir != report_path.parent:
        for p in output_dir.glob("meeting_prep_*.md"):
            pm = _MEETING_PREP_RE.search(p.name)
            if pm and pm.group(1) < current_date:
                candidates.append((pm.group(1), p))

    if not candidates:
        return None

    # Return the one with the latest date
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _extract_section(content: str, section_id: str) -> str:
    """Extract content between a section heading and the next H2."""
    pattern = re.compile(
        rf"^## (?:Section\s+)?(?:S)?{re.escape(section_id)}[：、:].*?\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1) if m else ""


def _extract_urls(text: str) -> set[str]:
    """Extract all markdown hyperlink URLs from text."""
    return set(re.findall(r"\[.*?\]\((https?://[^)]+)\)", text))


def _extract_sitrep_tags(text: str) -> dict[str, int]:
    """Count SITREP tags: [NEW], [ONGOING-Wn], [CF], [RESOLVED], [CARRY-Wn]."""
    counts: dict[str, int] = {
        "NEW": 0, "ONGOING": 0, "CF": 0, "RESOLVED": 0, "CARRY": 0,
    }
    counts["NEW"] = len(re.findall(r"\[NEW\]", text))
    counts["ONGOING"] = len(re.findall(r"\[ONGOING-W\d+\]", text))
    counts["CF"] = len(re.findall(r"\[CF\]", text))
    counts["RESOLVED"] = len(re.findall(r"\[RESOLVED\]", text))
    counts["CARRY"] = len(re.findall(r"\[CARRY(?:-W\d+)?\]", text))
    return counts


def _extract_s4_topics(text: str) -> list[str]:
    """Extract topic column from S4 cross-reference table."""
    topics: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 3:
            continue
        # Skip header and separator rows
        topic = cols[1].strip()
        if not topic or re.match(r":?-{3,}", topic) or topic in ("主題", "狀態"):
            continue
        # Strip SITREP tags
        topic = re.sub(r"\*?\*?\[(?:NEW|CF|ONGOING-W\d+)\]\*?\*?\s*", "", topic).strip()
        if topic:
            topics.append(topic)
    return topics


def _parse_metadata(content: str) -> dict | None:
    """Parse meeting_prep_meta JSON from HTML comment."""
    m = re.search(r"<!--\s*meeting_prep_meta\s+(\{.*?\})\s*-->", content, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _extract_s7_citation_ids(content: str) -> set[str]:
    """Extract KB citation stable_ids referenced in S7, excluding <details> blocks."""
    s7 = _extract_section(content, "7") or _extract_section(content, "七")
    if not s7:
        return set()

    # Remove toggle content
    s7_visible = re.sub(r"<details>.*?</details>", "", s7, flags=re.DOTALL)

    # Find [N] references
    ref_nums = set(int(m) for m in re.findall(r"\[(\d+)\]", s7_visible))

    # Map N → stable_id from citations JSON
    citations_m = re.search(r"<!--\s*citations\s+(\[.*?\])\s*-->", content, re.DOTALL)
    if not citations_m:
        return set()
    try:
        citations = json.loads(citations_m.group(1))
    except json.JSONDecodeError:
        return set()

    cit_map = {c.get("n"): c.get("id", "") for c in citations}
    return {cit_map[n] for n in ref_nums if n in cit_map and cit_map[n]}


def _count_toggle_blocks(content: str) -> int:
    """Count <details> toggle blocks in the report."""
    return len(re.findall(r"<details>", content))


def _jaccard_distance(set_a: set, set_b: set) -> float:
    """Return 1 - Jaccard similarity. 1.0 = completely different."""
    union = set_a | set_b
    if not union:
        return 1.0
    intersection = set_a & set_b
    return 1.0 - len(intersection) / len(union)


# ── Executor ──────────────────────────────────────────────────────────────────

def executor(data: dict) -> dict:
    """Parse current + prior report → extract novelty features."""
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"error": f"File not found: {report_path}"}

    prior_path = find_prior_report(report_path)
    no_prior = prior_path is None
    prior_content = "" if no_prior else prior_path.read_text(encoding="utf-8")

    # Current report features
    s2 = _extract_section(content, "2") or _extract_section(content, "二")
    s4 = _extract_section(content, "4") or _extract_section(content, "四")

    curr_s2_urls = _extract_urls(s2)
    curr_s2_tags = _extract_sitrep_tags(s2)
    curr_s4_topics = _extract_s4_topics(s4)
    curr_meta = _parse_metadata(content)
    curr_s7_ids = _extract_s7_citation_ids(content)
    curr_toggles = _count_toggle_blocks(content)

    # Prior report features
    prev_s2 = _extract_section(prior_content, "2") or _extract_section(prior_content, "二")
    prev_s4 = _extract_section(prior_content, "4") or _extract_section(prior_content, "四")

    prev_s2_urls = _extract_urls(prev_s2) if not no_prior else set()
    prev_s4_topics = _extract_s4_topics(prev_s4) if not no_prior else []
    prev_meta = _parse_metadata(prior_content) if not no_prior else None
    prev_s7_ids = _extract_s7_citation_ids(prior_content) if not no_prior else set()

    return {
        "no_prior": no_prior,
        "prior_path": str(prior_path) if prior_path else None,
        "curr_s2_urls": sorted(curr_s2_urls),
        "prev_s2_urls": sorted(prev_s2_urls),
        "curr_s2_tags": curr_s2_tags,
        "curr_s4_topics": curr_s4_topics,
        "prev_s4_topics": prev_s4_topics,
        "curr_meta": curr_meta,
        "prev_meta": prev_meta,
        "curr_s7_ids": sorted(curr_s7_ids),
        "prev_s7_ids": sorted(prev_s7_ids),
        "curr_toggles": curr_toggles,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

def s2_novelty(output: dict, target: dict) -> float:
    """S2 industry news novelty: fraction of NEW items or URL Jaccard distance."""
    if "error" in output or output.get("no_prior"):
        return 1.0

    tags = output.get("curr_s2_tags", {})
    total_tagged = sum(tags.values())

    # Path 1: SITREP tags available
    if total_tagged > 0:
        new_count = tags.get("NEW", 0)
        return new_count / total_tagged

    # Path 2: Fallback to URL Jaccard
    curr_urls = set(output.get("curr_s2_urls", []))
    prev_urls = set(output.get("prev_s2_urls", []))
    if not curr_urls:
        return 0.5  # neutral
    return _jaccard_distance(curr_urls, prev_urls)


def s4_novelty(output: dict, target: dict) -> float:
    """S4 cross-reference topic novelty."""
    if "error" in output or output.get("no_prior"):
        return 1.0

    curr_topics = set(output.get("curr_s4_topics", []))
    prev_topics = set(output.get("prev_s4_topics", []))
    if not curr_topics:
        return 0.5  # neutral
    return _jaccard_distance(curr_topics, prev_topics)


def score_drift_novelty(output: dict, target: dict) -> float:
    """E-E-A-T + Maturity score change magnitude. Penalises zero drift (copy-paste)."""
    if "error" in output or output.get("no_prior"):
        return 1.0

    curr_meta = output.get("curr_meta")
    prev_meta = output.get("prev_meta")
    if not curr_meta or not prev_meta:
        return 0.5  # neutral

    delta_total = 0.0

    # E-E-A-T drift
    curr_eeat = curr_meta.get("scores", {}).get("eeat", {})
    prev_eeat = prev_meta.get("scores", {}).get("eeat", {})
    for dim in ("experience", "expertise", "authoritativeness", "trustworthiness"):
        c = curr_eeat.get(dim)
        p = prev_eeat.get(dim)
        if c is not None and p is not None:
            delta_total += abs(c - p)

    # Maturity drift
    level_map = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}
    curr_mat = curr_meta.get("scores", {}).get("maturity", {})
    prev_mat = prev_meta.get("scores", {}).get("maturity", {})
    for dim in ("strategy", "process", "keywords", "metrics"):
        c = level_map.get(curr_mat.get(dim, ""), 0)
        p = level_map.get(prev_mat.get(dim, ""), 0)
        if c > 0 and p > 0:
            delta_total += abs(c - p)

    # Normalise: 4.0 = expected avg of 1 point change per report
    return min(delta_total / 4.0, 1.0)


def s7_citation_novelty(output: dict, target: dict) -> float:
    """Fraction of S7 citations that are new (not in prior report S7)."""
    if "error" in output or output.get("no_prior"):
        return 1.0

    curr_ids = set(output.get("curr_s7_ids", []))
    prev_ids = set(output.get("prev_s7_ids", []))
    if not curr_ids:
        return 0.5  # neutral

    new_ids = curr_ids - prev_ids
    return len(new_ids) / len(curr_ids)


def toggle_structure(output: dict, target: dict) -> float:
    """Check whether report uses <details> toggle for No Change content."""
    if "error" in output or output.get("no_prior"):
        return 1.0  # First report: no toggle needed

    toggles = output.get("curr_toggles", 0)
    # Expect at least 2 toggles for a report with prior (S6/S7/S8 No Change)
    if toggles >= 3:
        return 1.0
    if toggles >= 1:
        return 0.5
    return 0.0


# ── Evaluator map ─────────────────────────────────────────────────────────────

_EVALUATOR_MAP = {
    "s2_novelty": s2_novelty,
    "s4_novelty": s4_novelty,
    "score_drift_novelty": score_drift_novelty,
    "s7_citation_novelty": s7_citation_novelty,
    "toggle_structure": toggle_structure,
}

# ── Threshold gate ────────────────────────────────────────────────────────────

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _run_threshold_gate() -> None:
    global _exec_cache
    if not _threshold_path.exists():
        _exec_cache = {}
        return
    with open(_threshold_path, encoding="utf-8") as _tf:
        thresholds: dict[str, float] = json.load(_tf).get("meeting_prep_novelty", {})
    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_novelty thresholds ---")
    pre_results = [(executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {dp["data"]["report_path"]: out for dp, (out, _) in zip(_dataset, pre_results)}

    gate_failed = False
    for metric, min_val in thresholds.items():
        fn = _EVALUATOR_MAP.get(metric)
        if not fn:
            continue
        scores = [fn(out, tgt) for out, tgt in pre_results]
        avg = sum(scores) / len(scores) if scores else 0.0
        if avg < min_val:
            print(f"  FAIL: {metric} = {avg:.4f} < {min_val}", file=sys.stderr)
            gate_failed = True
        else:
            print(f"  PASS: {metric} = {avg:.4f} >= {min_val}")

    if gate_failed:
        print("\nCI eval gate FAILED. Fix regressions before merging.", file=sys.stderr)
        sys.exit(1)
    print("All meeting_prep_novelty thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
    cached = _exec_cache.get(data["report_path"])
    if cached is not None and "error" not in cached:
        return cached
    return executor(data)


# ── Run ───────────────────────────────────────────────────────────────────────

def run_eval() -> None:
    _run_threshold_gate()
    evaluate(
        data=_dataset,
        executor=_cached_executor if _threshold_path.exists() else executor,
        evaluators=_EVALUATOR_MAP,
        group_name="meeting_prep_novelty",
    )


if __name__ == "__main__":
    run_eval()
