"""
Laminar offline evaluation: Meeting-prep report grounding quality.

Tests whether generated meeting-prep reports are properly grounded in the KB:
- Citation IDs resolve to actual KB items
- Citation categories match KB item categories
- Citation count is within expected range
- S4 cross-reference table has populated source columns
- Inline citation references cover declared citations

Dataset:  eval/golden_meeting_prep.json
Fixtures: eval/fixtures/meeting_prep/*.md
Data:     output/qa_final.json (local) or Supabase qa_items (CI fallback)
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_meeting_prep_grounding.py
    python evals/eval_meeting_prep_grounding.py --report path/to/report.md
    python evals/eval_meeting_prep_grounding.py --limit 1
    lmnr eval evals/eval_meeting_prep_grounding.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

from lmnr import evaluate  # type: ignore[import]

# ── CLI args ──────────────────────────────────────────────────────────────────

_parser = argparse.ArgumentParser(description="Meeting-prep grounding eval")
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
        f"[eval_meeting_prep_grounding] Golden dataset not found: {_golden_path}",
        file=sys.stderr,
    )
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _args.report:
    if not _golden_raw:
        print(
            "[eval_meeting_prep_grounding] --report requires at least one golden case "
            "to borrow expected values from; golden file is empty.",
            file=sys.stderr,
        )
        sys.exit(1)
    _golden_raw = [
        {
            "id": "adhoc",
            "report_path": _args.report,
            "expected_grounding": _golden_raw[0]["expected_grounding"],
            "expected_structure": _golden_raw[0]["expected_structure"],
        }
    ]

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]
    print(f"[eval_meeting_prep_grounding] Limiting to {_args.limit} golden cases")

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
            f"[eval_meeting_prep_grounding] Skipping {case.get('id')}: "
            f"fixture not found at {report_file}",
            file=sys.stderr,
        )

if not _golden_filtered:
    print(
        "[eval_meeting_prep_grounding] No fixture files found. Skipping.",
        file=sys.stderr,
    )
    sys.exit(0)

_dataset = [
    {
        "data": {"report_path": case["report_path"]},
        "target": {
            **case.get("expected_grounding", {}),
            **case.get("expected_structure", {}),
        },
    }
    for case in _golden_filtered
]

# ── KB loading (local → Supabase fallback, same as eval_retrieval.py) ────────

_SUPABASE_PAGE_SIZE = 1000
_kb_cache: list[dict] | None = None


def _fetch_supabase_qa_items(supabase_url: str, anon_key: str) -> list[dict]:
    """Fetch all QA items from Supabase with pagination."""
    headers = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    items: list[dict] = []
    offset = 0

    while True:
        query = urlencode(
            {
                "select": "id,question,category,source_type,source_collection",
                "order": "seq.asc",
                "limit": _SUPABASE_PAGE_SIZE,
                "offset": offset,
            }
        )
        try:
            resp = requests.get(
                f"{supabase_url}/rest/v1/qa_items?{query}",
                headers=headers,
                timeout=30,
            )
        except Exception as exc:
            logger.error("[eval_meeting_prep_grounding] Supabase request failed: %s", exc)
            return []

        if resp.status_code != 200:
            logger.error(
                "[eval_meeting_prep_grounding] Supabase fetch failed: %s %s",
                resp.status_code,
                resp.text[:200],
            )
            return []

        page_items = resp.json()
        items.extend(page_items)

        if len(page_items) < _SUPABASE_PAGE_SIZE:
            break
        offset += len(page_items)

    logger.info(
        "[eval_meeting_prep_grounding] Loaded %d QA items from Supabase", len(items)
    )
    return items


def _load_qa_items() -> list[dict]:
    """Load QA items from local file first, fallback to Supabase REST API."""
    global _kb_cache
    if _kb_cache is not None:
        return _kb_cache

    qa_final_path = PROJECT_ROOT / "output" / "qa_final.json"

    # 1. Try local file
    if qa_final_path.exists():
        try:
            data = json.loads(qa_final_path.read_text(encoding="utf-8"))
            items = data.get("qa_database", [])
            if items:
                logger.info(
                    "[eval_meeting_prep_grounding] Loaded %d QA items from local file",
                    len(items),
                )
                _kb_cache = items
                return items
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(
                "[eval_meeting_prep_grounding] Local file read failed: %s", e
            )

    # 2. Fallback to Supabase
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        logger.error(
            "[eval_meeting_prep_grounding] No local qa_final.json and "
            "no SUPABASE_URL/SUPABASE_ANON_KEY set"
        )
        _kb_cache = []
        return []

    logger.info("[eval_meeting_prep_grounding] Loading QA items from Supabase...")
    items = _fetch_supabase_qa_items(supabase_url, anon_key)
    _kb_cache = items
    return items


def _build_kb_index(kb_items: list[dict]) -> dict[str, dict]:
    """Build a lookup dict: stable_id -> {category, ...}.

    Citations reference items by stable_id (hex string), not integer id.
    Local qa_final.json uses 'stable_id' field; Supabase uses 'id' (which is stable_id).
    """
    index: dict[str, dict] = {}
    for item in kb_items:
        # Local file: stable_id is a separate field
        sid = item.get("stable_id")
        if sid:
            index[sid] = item
        # Supabase: 'id' column IS the stable_id (hex string)
        elif isinstance(item.get("id"), str):
            index[item["id"]] = item
    return index


# ── Parsers ───────────────────────────────────────────────────────────────────


def _parse_citations(content: str) -> list[dict] | None:
    """Extract citations JSON array from HTML comment."""
    match = re.search(r"<!--\s*citations\s+(\[.*?\])\s*-->", content, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _extract_inline_refs(content: str) -> set[int]:
    """Extract all [N] inline citation references from report body."""
    clean = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    clean = re.sub(r"```.*?```", "", clean, flags=re.DOTALL)
    return {int(m) for m in re.findall(r"\[(\d+)\]", clean)}


def _extract_section_content(content: str, section_title: str) -> str:
    """Extract content between a section heading and the next H2."""
    pattern = re.compile(
        rf"^## {re.escape(section_title)}.*?\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    return match.group(1) if match else ""


def _parse_s4_table_rows(s4_content: str) -> list[dict]:
    """Parse S4 cross-reference table rows.

    Expected format:
    | 主題 | KB 知識庫觀點 | 顧問文章觀點 | 指標數據 | 業界動態 | 判斷 |
    """
    rows: list[dict] = []
    for line in s4_content.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")]
        # Skip header row and separator row
        if len(cols) < 7:
            continue
        if re.match(r":?-{3,}:?", cols[1]) or cols[1] == "主題":
            continue
        rows.append(
            {
                "topic": cols[1],
                "kb": cols[2],
                "consultant": cols[3],
                "metrics": cols[4],
                "industry": cols[5],
                "judgment": cols[6] if len(cols) > 6 else "",
            }
        )
    return rows


# ── Executor ──────────────────────────────────────────────────────────────────


def executor(data: dict) -> dict:
    """Read report -> parse citations -> lookup KB -> return structured dict."""
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Report file not found: %s", report_path)
        return {"error": f"File not found: {report_path}"}

    citations = _parse_citations(content) or []
    kb_items = _load_qa_items()
    kb_index = _build_kb_index(kb_items)

    # Resolve each citation against KB
    kb_lookup: list[dict] = []
    for cit in citations:
        cit_id = cit.get("id", "")
        kb_item = kb_index.get(cit_id)
        kb_lookup.append(
            {
                "citation_id": cit_id,
                "citation_category": cit.get("category", ""),
                "kb_found": kb_item is not None,
                "kb_category": kb_item.get("category", "") if kb_item else None,
            }
        )

    s4 = _extract_section_content(content, "四、顧問視角交叉比對")

    return {
        "citations": citations,
        "kb_lookup": kb_lookup,
        "inline_refs": sorted(_extract_inline_refs(content)),
        "s4_rows": _parse_s4_table_rows(s4),
        "raw_content": content,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────


def citation_id_resolution(output: dict, target: dict) -> float:
    """Fraction of citation IDs that resolve to actual KB items."""
    if "error" in output:
        return 0.0
    kb_lookup = output.get("kb_lookup", [])
    if not kb_lookup:
        return 0.0
    resolved = sum(1 for item in kb_lookup if item["kb_found"])
    return resolved / len(kb_lookup)


def citation_category_consistency(output: dict, target: dict) -> float:
    """Fraction of citations whose category matches KB item category."""
    if "error" in output:
        return 0.0
    kb_lookup = output.get("kb_lookup", [])
    resolved_items = [item for item in kb_lookup if item["kb_found"]]
    if not resolved_items:
        return 0.0
    consistent = sum(
        1
        for item in resolved_items
        if item["citation_category"] == item["kb_category"]
    )
    return consistent / len(resolved_items)


def citation_count_in_range(output: dict, target: dict) -> float:
    """Bell curve scoring: peak at 15-20 citations, decay outside. Continuous 0-1."""
    if "error" in output:
        return 0.0
    count = len(output.get("citations", []))
    if count == 0:
        return 0.0
    # Optimal range center = 17.5, max distance = 17.5 (at 0 or 35)
    center = 17.5
    score = 1.0 - abs(count - center) / center
    return max(0.0, min(1.0, score))


def s4_four_sources_populated(output: dict, target: dict) -> float:
    """Fraction of S4 rows where all 4 source columns have substantial content."""
    if "error" in output:
        return 0.0
    rows = output.get("s4_rows", [])
    if not rows:
        return 0.0

    # A column is "populated" if it has > 5 chars of content (not just "—" or empty)
    populated_count = 0
    for row in rows:
        sources = [row.get("kb", ""), row.get("consultant", ""),
                    row.get("metrics", ""), row.get("industry", "")]
        filled = sum(1 for s in sources if len(s.strip()) > 5)
        if filled >= 4:
            populated_count += 1

    return populated_count / len(rows)


def inline_citation_coverage(output: dict, target: dict) -> float:
    """Fraction of declared citations that are referenced inline as [N]."""
    if "error" in output:
        return 0.0
    citations = output.get("citations", [])
    if not citations:
        return 1.0

    inline_refs = set(output.get("inline_refs", []))
    declared_ns = {cit.get("n") for cit in citations if cit.get("n") is not None}

    if not declared_ns:
        return 1.0

    referenced = declared_ns & inline_refs
    return len(referenced) / len(declared_ns)


# ── Evaluator map ─────────────────────────────────────────────────────────────

_EVALUATOR_MAP = {
    "citation_id_resolution": citation_id_resolution,
    "citation_category_consistency": citation_category_consistency,
    "citation_count_in_range": citation_count_in_range,
    "s4_four_sources_populated": s4_four_sources_populated,
    "inline_citation_coverage": inline_citation_coverage,
}

# ── Threshold gate (CI eval gate) ─────────────────────────────────────────────

_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _run_threshold_gate() -> None:
    """Run meeting_prep_grounding threshold gate and populate executor cache."""
    global _exec_cache

    if not _threshold_path.exists():
        _exec_cache = {}
        return

    with open(_threshold_path, encoding="utf-8") as _tf:
        thresholds: dict[str, float] = json.load(_tf).get(
            "meeting_prep_grounding", {}
        )

    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_grounding thresholds ---")

    # Pre-check KB availability; skip gate if KB is empty (avoids false CI failure)
    kb_items = _load_qa_items()
    if not kb_items:
        print(
            "  SKIP: KB empty (no local qa_final.json and Supabase unavailable). "
            "Grounding gate skipped.",
            file=sys.stderr,
        )
        return

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
    print("All meeting_prep_grounding thresholds passed.\n")


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
        group_name="meeting_prep_grounding",
    )


if __name__ == "__main__":
    run_eval()
