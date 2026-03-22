"""
Laminar offline evaluation: Meeting-prep web research freshness.

Tests whether S2 (industry updates) section has:
- Fresh dates (within ±N days of report date)
- Diverse sources (multiple different media outlets)
- Accessible URLs (optional HTTP HEAD check)
- Sufficient content density

Dataset:  eval/golden_meeting_prep.json
Fixtures: eval/fixtures/meeting_prep/*.md
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_meeting_prep_web.py
    python evals/eval_meeting_prep_web.py --report path/to/report.md
    python evals/eval_meeting_prep_web.py --limit 1
    lmnr eval evals/eval_meeting_prep_web.py
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env")
logger = logging.getLogger(__name__)
from lmnr import evaluate  # type: ignore[import]

# ── CLI args ──────────────────────────────────────────────────────────────────
_parser = argparse.ArgumentParser(description="Meeting-prep web research freshness eval")
_parser.add_argument("--report", type=str, default=None)
_parser.add_argument("--limit", type=int, default=0)
_args, _unknown = _parser.parse_known_args()

# ── Golden dataset ────────────────────────────────────────────────────────────
_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
if not _golden_path.exists():
    print(f"[eval_meeting_prep_web] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)
with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

if _args.report:
    if not _golden_raw:
        print("[eval_meeting_prep_web] --report requires at least one golden case.", file=sys.stderr)
        sys.exit(1)
    _golden_raw = [{"id": "adhoc", "report_path": _args.report, "expected_web": _golden_raw[0]["expected_web"]}]
if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]
    print(f"[eval_meeting_prep_web] Limiting to {_args.limit} golden cases")

_golden_filtered = [
    c for c in _golden_raw
    if not c.get("calibration_only", False)
    and ((PROJECT_ROOT / c["report_path"]).exists()
         or not print(f"[eval_meeting_prep_web] Skipping {c['id']}: fixture not found", file=sys.stderr))
]
if not _golden_filtered:
    print("[eval_meeting_prep_web] No fixture files found. Skipping.", file=sys.stderr)
    sys.exit(0)

_dataset = [{"data": {"report_path": c["report_path"]}, "target": c["expected_web"]} for c in _golden_filtered]

# ── Source normalization ──────────────────────────────────────────────────────
_SOURCE_NORMALIZE: dict[str, str] = {
    "search engine land": "searchengineland", "searchengineland": "searchengineland", "sel": "searchengineland",
    "search engine roundtable": "seroundtable", "seroundtable": "seroundtable", "ser": "seroundtable",
    "search engine journal": "searchenginejournal", "searchenginejournal": "searchenginejournal", "sej": "searchenginejournal",
    "google developers": "google-developers", "google search central": "google-search-central",
    "google search central 官方公告": "google-search-central",
}

# ── Parsers ───────────────────────────────────────────────────────────────────

def _extract_s2_section(content: str) -> str:
    """Extract S2 section text (H2 heading to next H2)."""
    m = re.search(r"^## (?:S2|二)[：、].*$", content, re.MULTILINE)
    if not m:
        return ""
    nxt = re.search(r"^## ", content[m.end():], re.MULTILINE)
    return content[m.start(): m.end() + nxt.start() if nxt else len(content)]


def _extract_report_date(content: str) -> date | None:
    """Extract report date from meeting_prep_meta JSON or H1 heading."""
    meta_m = re.search(r"<!--\s*meeting_prep_meta\s+(\{.*?\})\s*-->", content, re.DOTALL)
    if meta_m:
        try:
            raw = json.loads(meta_m.group(1)).get("date", "")
            if len(raw) == 8:
                return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        except (json.JSONDecodeError, ValueError):
            pass
    h1 = re.search(r"^# .+(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
    if h1:
        try:
            return date.fromisoformat(h1.group(1))
        except ValueError:
            pass
    return None


def _safe_date(y: int, mo: int, d: int) -> date | None:
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _parse_dates(s2_text: str, report_date: date | None = None) -> list[date]:
    """Parse all dates from S2 section (ISO, range, slash formats)."""
    ry = report_date.year if report_date else date.today().year
    collected: list[date] = []

    # ISO full: 2026-03-11
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\b", s2_text):
        if d := _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))):
            collected.append(d)
    # Full month range: 2026-02-05 ~ 02-27
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})\s*[~～–]\s*(\d{2})-(\d{2})\b", s2_text):
        y = int(m.group(1))
        for mo, day in ((m.group(2), m.group(3)), (m.group(4), m.group(5))):
            if d := _safe_date(y, int(mo), int(day)):
                collected.append(d)
    # Compact same-month range: 2026-02-05~27
    for m in re.finditer(r"\b(\d{4})-(\d{2})-(\d{2})[~～–](\d{1,2})\b", s2_text):
        y, mo = int(m.group(1)), int(m.group(2))
        for day in (m.group(3), m.group(4)):
            if d := _safe_date(y, mo, int(day)):
                collected.append(d)
    # Slash date: 3/11, 2/25
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})\b", s2_text):
        mo, day = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= day <= 31:
            if d := _safe_date(ry, mo, day):
                collected.append(d)
    # Slash range: 2/5–2/27
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})[~～–](\d{1,2})/(\d{1,2})\b", s2_text):
        for mo, day in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
            if d := _safe_date(ry, int(mo), int(day)):
                collected.append(d)

    seen: set[date] = set()
    return [d for d in collected if d not in seen and not seen.add(d)]  # type: ignore[func-returns-value]


def _parse_sources(s2_text: str) -> list[str]:
    """Extract and normalize unique source names from S2 tables, H3s, and inline mentions."""
    _skip_cells = {"來源", "日期", "標題", "事件", "狀態", "更新名稱"}
    _skip_h3 = {"Google 官方更新", "業界報導"}
    _date_like = re.compile(r"^[\d/\-~～–\s]+$")
    raw: list[str] = []
    for line in s2_text.splitlines():
        s = line.strip()
        if s.startswith("|") and not s.startswith("|---") and not s.startswith("|--"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            first = re.sub(r"\*\*(.+?)\*\*", r"\1", cells[0]).strip() if cells else ""
            if first and first not in _skip_cells and not _date_like.match(first):
                raw.append(first)
    for m in re.finditer(r"^### (.+)$", s2_text, re.MULTILINE):
        h = m.group(1).strip()
        if h not in _skip_h3:
            raw.append(h)
    for m in re.finditer(r"[（(]([^）)\n]{1,50})[）)]", s2_text):
        c = m.group(1).strip()
        if re.search(r"[A-Za-z]", c):
            raw.append(c)

    def _norm(n: str) -> str:
        return _SOURCE_NORMALIZE.get(n.lower().strip(), n.lower().strip())

    return list(dict.fromkeys(_norm(s) for s in raw if s))


def _parse_urls(s2_text: str) -> list[str]:
    return re.findall(r"\[(?:[^\]]+)\]\((https?://[^)]+)\)", s2_text)

# ── Executor ──────────────────────────────────────────────────────────────────

def executor(data: dict) -> dict:
    """Read .md file -> parse S2 web research fields -> return structured dict."""
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("Report file not found: %s", report_path)
        return {"error": f"File not found: {report_path}"}
    s2_text = _extract_s2_section(content)
    report_date = _extract_report_date(content)
    return {
        "s2_text": s2_text,
        "report_date": report_date.isoformat() if report_date else None,
        "dates": [d.isoformat() for d in _parse_dates(s2_text, report_date)],
        "sources": _parse_sources(s2_text),
        "urls": _parse_urls(s2_text),
        "content_lines": [
            ln for ln in s2_text.split("\n")
            if ln.strip() and not ln.startswith("#") and not ln.startswith("---") and not ln.startswith("|--")
        ],
    }

# ── Evaluators ────────────────────────────────────────────────────────────────

def date_freshness_rate(output: dict, target: dict) -> float:
    """Ratio of S2 dates within ±date_window_days of report date."""
    if "error" in output:
        return 0.0
    if not output["dates"] or not output["report_date"]:
        return 0.5  # neutral when no dates parseable
    window = target.get("date_window_days", 30)
    report_dt = date.fromisoformat(output["report_date"])
    fresh = sum(1 for d in output["dates"] if abs((date.fromisoformat(d) - report_dt).days) <= window)
    return fresh / len(output["dates"])


def source_diversity(output: dict, target: dict) -> float:
    """Unique source count / 5, capped at 1.0. Requires 5 distinct sources for full score."""
    if "error" in output:
        return 0.0
    return min(len(set(output["sources"])) / 5.0, 1.0)


def url_accessibility_rate(output: dict, target: dict) -> float | None:
    """HEAD request success ratio. Returns 1.0 if disabled, None if no URLs."""
    if "error" in output:
        return 0.0
    if not target.get("url_check_enabled", False):
        return 1.0
    urls = output["urls"]
    if not urls:
        return None  # no URLs to check → skip in threshold gate
    import requests  # lazy import: only when url_check_enabled=true
    def _ok(url: str) -> bool:
        try:
            return requests.head(url, timeout=5, allow_redirects=True).status_code < 400
        except Exception:
            return False
    return sum(1 for url in urls if _ok(url)) / len(urls)


def s2_content_density(output: dict, target: dict) -> float:
    """Effective content lines / 15, capped at 1.0. Requires 15 lines for full score."""
    if "error" in output:
        return 0.0
    lines = output.get("content_lines", [])
    return min(len(lines) / 15.0, 1.0) if lines else 0.0

# ── Evaluator map ─────────────────────────────────────────────────────────────
_EVALUATOR_MAP = {
    "date_freshness_rate": date_freshness_rate,
    "source_diversity": source_diversity,
    "url_accessibility_rate": url_accessibility_rate,
    "s2_content_density": s2_content_density,
}

# ── Threshold gate (CI eval gate) ─────────────────────────────────────────────
_threshold_path = PROJECT_ROOT / "eval" / "eval_thresholds.json"
_exec_cache: dict[str, dict] = {}


def _run_threshold_gate() -> None:
    """Run meeting_prep_web threshold gate and populate executor cache."""
    global _exec_cache
    if not _threshold_path.exists():
        _exec_cache = {}
        return
    with open(_threshold_path, encoding="utf-8") as _tf:
        thresholds: dict[str, float] = json.load(_tf).get("meeting_prep_web", {})
    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_web thresholds ---")
    pre_results = [(executor(dp["data"]), dp["target"]) for dp in _dataset]
    _exec_cache = {dp["data"]["report_path"]: out for dp, (out, _) in zip(_dataset, pre_results)}

    gate_failed = False
    for metric, min_val in thresholds.items():
        fn = _EVALUATOR_MAP.get(metric)
        if not fn:
            continue
        raw = [fn(out, tgt) for out, tgt in pre_results]
        scores = [s for s in raw if s is not None]
        if not scores:
            logger.debug("Skipping metric %s: all scores None", metric)
            continue
        avg = sum(scores) / len(scores)
        if avg < min_val:
            print(f"  FAIL: {metric} = {avg:.4f} < {min_val}", file=sys.stderr)
            gate_failed = True
        else:
            print(f"  PASS: {metric} = {avg:.4f} >= {min_val}")

    if gate_failed:
        print("\nCI eval gate FAILED. Fix regressions before merging.", file=sys.stderr)
        sys.exit(1)
    print("All meeting_prep_web thresholds passed.\n")


def _cached_executor(data: dict) -> dict:
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
        group_name="meeting_prep_web",
    )


if __name__ == "__main__":
    run_eval()
