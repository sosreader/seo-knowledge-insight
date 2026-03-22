"""
Laminar offline evaluation: Meeting-prep cross-section coherence (L2.5).

Rule-based, zero LLM cost. Tests whether meeting-prep sections are
logically connected:
- S1 ALERT_DOWN → S3 hypotheses → S9 questions (cross-section chain)
- S10 action items have tool + condition specificity
- S3 hypotheses are tagged with verification methods
- E-E-A-T / maturity scores are consistent with prior reports
- Citation categories match their section context

Dataset:  eval/golden_meeting_prep.json
Fixtures: eval/fixtures/meeting_prep/*.md
Requires: LMNR_PROJECT_API_KEY

Run:
    python evals/eval_meeting_prep_coherence.py
    python evals/eval_meeting_prep_coherence.py --report path/to/report.md
    python evals/eval_meeting_prep_coherence.py --limit 1
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

_parser = argparse.ArgumentParser(description="Meeting-prep coherence eval")
_parser.add_argument("--report", type=str, default=None)
_parser.add_argument("--limit", type=int, default=0)
_args, _unknown = _parser.parse_known_args()

# ── Golden dataset ────────────────────────────────────────────────────────────

_golden_path = PROJECT_ROOT / "eval" / "golden_meeting_prep.json"
if not _golden_path.exists():
    print(f"[eval_meeting_prep_coherence] Golden dataset not found: {_golden_path}", file=sys.stderr)
    sys.exit(1)

with open(_golden_path, encoding="utf-8") as _f:
    _golden_raw: list[dict] = json.load(_f)

_DEFAULT_COHERENCE = {
    "cross_section_coherence_min": 0.6,
    "action_specificity_min": 0.5,
    "hypothesis_falsifiability_min": 0.6,
    "temporal_consistency_min": 0.8,
    "citation_relevance_min": 0.6,
}

if _args.report:
    if not _golden_raw:
        print("[eval_meeting_prep_coherence] --report requires at least one golden case.", file=sys.stderr)
        sys.exit(1)
    _golden_raw = [{
        "id": "adhoc",
        "report_path": _args.report,
        "expected_coherence": _golden_raw[0].get("expected_coherence", _DEFAULT_COHERENCE),
    }]

if _args.limit > 0:
    _golden_raw = _golden_raw[: _args.limit]

_golden_filtered = [
    c for c in _golden_raw
    if not c.get("calibration_only", False)
    and ((PROJECT_ROOT / c["report_path"]).exists()
         or not print(f"[eval_meeting_prep_coherence] Skipping {c['id']}: fixture not found", file=sys.stderr))
]

if not _golden_filtered:
    print("[eval_meeting_prep_coherence] No fixture files found. Skipping.", file=sys.stderr)
    sys.exit(0)

_dataset = [
    {"data": {"report_path": c["report_path"]}, "target": c.get("expected_coherence", _DEFAULT_COHERENCE)}
    for c in _golden_filtered
]

# ── Parsers ───────────────────────────────────────────────────────────────────

_SECTION_RE = re.compile(r"^## (?:Section\s+)?(\d+|[〇一二三四五六七八九十]+)[：、:].+$", re.MULTILINE)


def _extract_section(content: str, section_id: str) -> str:
    """Extract content between a section heading containing section_id and next H2."""
    pattern = re.compile(
        rf"^## (?:Section\s+)?{re.escape(section_id)}[：、:].*?\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1) if m else ""


def _extract_s1_alerts(content: str) -> set[str]:
    """Extract metric names from S1 ALERT_DOWN table rows and bullet lists."""
    s1 = _extract_section(content, "1") or _extract_section(content, "一")
    alerts: set[str] = set()
    # Table rows
    for line in s1.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 3:
            continue
        metric = cols[1].strip()
        if metric and not re.match(r":?-{3,}", metric) and metric not in ("指標", ""):
            alerts.add(metric)
    # Broad metric pattern scan (for non-table formats)
    for m in re.finditer(
        r"(?:Discover|CTR|AMP\s*(?:Article|Ratio)?|Coverage|外部連結|回應時間|"
        r"KW[:：「]\s*\S+|營運\s*KW[:：「]\s*\S+|檢索未索引|探索比例|"
        r"結構化\s*Ratio|新網頁|/salon/|/article/|/en/|/tag/|"
        r"Organic\s*Search|News\s*\(new\)|Video|GPT|Gemini|Perplexity|AI\s*占比)",
        s1,
    ):
        alerts.add(m.group(0).strip())
    return alerts


def _extract_s3_metrics(content: str) -> set[str]:
    """Extract metric names mentioned in S3 subsection headings and body text."""
    s3 = _extract_section(content, "3") or _extract_section(content, "三")
    metrics: set[str] = set()
    # Pattern: ### H1：營運 KW「保養」... or ### 3.1 Discover 崩跌
    for m in re.finditer(r"^### (?:H\d+|S?\d+(?:\.\d+)?)[：:]\s*(.+?)(?:\s*[（(]|$)", s3, re.MULTILINE):
        metrics.add(m.group(1).strip())
    # Pattern: ### 3.N heading text
    for m in re.finditer(r"^### \d+\.\d+ (.+?)$", s3, re.MULTILINE):
        metrics.add(m.group(1).strip())
    # Pattern: **假設 N（topic）**
    for m in re.finditer(r"\*\*假設\s*\d+[（(](.+?)[）)]\*\*", s3):
        metrics.add(m.group(1).strip())
    # Broad fallback: scan S3 for known metric patterns
    for m in re.finditer(
        r"(?:Discover|CTR|AMP\s*(?:Article|Ratio)?|Coverage|外部連結|回應時間|"
        r"KW[:：「]\s*\S+|營運\s*KW[:：「]\s*\S+|檢索未索引|探索比例|"
        r"結構化\s*Ratio|新網頁|/salon/|/article/|/en/|/tag/|"
        r"Organic\s*Search|News\s*\(new\)|Video|GPT|Gemini|Perplexity|AI\s*占比)",
        s3,
    ):
        metrics.add(m.group(0).strip())
    return metrics


def _extract_s9_metrics(content: str) -> set[str]:
    """Extract metric names referenced in S9 questions."""
    s9 = _extract_section(content, "9") or _extract_section(content, "九")
    metrics: set[str] = set()
    # Look for metric names in question text (typically bold or in quotes)
    for line in s9.splitlines():
        if not line.strip().startswith("- ["):
            continue
        # Find any metric-like terms (Chinese or English + numbers)
        for m in re.finditer(r"(?:Discover|CTR|AMP|Coverage|外部連結|回應時間|KW[:：]\s*\S+|營運 KW[:：]\s*\S+|檢索未索引|探索比例|結構化 Ratio|新網頁|AMP Ratio)", line):
            metrics.add(m.group(0).strip())
    return metrics


def _parse_metadata(content: str) -> dict | None:
    """Parse meeting_prep_meta JSON from HTML comment."""
    m = re.search(r"<!--\s*meeting_prep_meta\s+(\{.*?\})\s*-->", content, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _parse_citations_json(content: str) -> list[dict]:
    """Extract citations array from HTML comment."""
    m = re.search(r"<!--\s*citations\s+(\[.*?\])\s*-->", content, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return []


def _load_prior_scores() -> dict | None:
    """Load the most recent E-E-A-T + maturity from research/12-meeting-prep-insights.md."""
    insights_path = PROJECT_ROOT / "research" / "12-meeting-prep-insights.md"
    if not insights_path.exists():
        return None
    text = insights_path.read_text(encoding="utf-8")
    # Parse the tracking table rows: | date | E:N E:N A:N T:N | strategy:LN ... |
    rows = re.findall(
        r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*E:(\d)\s+E:(\d)\s+A:(\d)\s+T:(\d)",
        text,
    )
    if len(rows) < 2:
        return None
    # Return second-to-last row (the one before the latest)
    _, exp, expt, auth, trust = rows[-2]
    return {
        "experience": int(exp),
        "expertise": int(expt),
        "authoritativeness": int(auth),
        "trustworthiness": int(trust),
    }


# ── Executor ──────────────────────────────────────────────────────────────────

def executor(data: dict) -> dict:
    """Parse report → extract cross-section features."""
    report_path = PROJECT_ROOT / data["report_path"]
    try:
        content = report_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"error": f"File not found: {report_path}"}

    s1_alerts = _extract_s1_alerts(content)
    s3_metrics = _extract_s3_metrics(content)
    s9_metrics = _extract_s9_metrics(content)
    s10 = _extract_section(content, "10") or _extract_section(content, "十")
    s3 = _extract_section(content, "3") or _extract_section(content, "三")
    meta = _parse_metadata(content)
    citations = _parse_citations_json(content)
    prior_scores = _load_prior_scores()

    # S10 action items
    action_items = [
        ln.strip() for ln in s10.splitlines()
        if ln.strip().startswith("- [")
    ]

    # S3 hypotheses
    hypotheses = [
        ln.strip() for ln in s3.splitlines()
        if re.match(r"\*\*假設\s*\d+", ln.strip())
    ]

    # Inline citations by section
    inline_by_section: dict[str, list[int]] = {}
    for section_id in ["1", "一", "3", "三", "5", "五", "6", "六"]:
        sec = _extract_section(content, section_id)
        refs = [int(m) for m in re.findall(r"\[(\d+)\]", sec)]
        if refs:
            inline_by_section[section_id] = refs

    return {
        "s1_alerts": sorted(s1_alerts),
        "s3_metrics": sorted(s3_metrics),
        "s9_metrics": sorted(s9_metrics),
        "action_items": action_items,
        "hypotheses": hypotheses,
        "meta": meta,
        "citations": citations,
        "prior_scores": prior_scores,
        "inline_by_section": inline_by_section,
        "raw_content": content,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────

# Tool and action keywords for specificity scoring
_TOOL_NAMES = re.compile(
    r"GSC|Search Console|PageSpeed|Ahrefs|Screaming Frog|GA4|"
    r"Google Trends|Semrush|Moz|Chrome DevTools|Lighthouse",
    re.IGNORECASE,
)
_ACTION_VERBS = re.compile(
    r"排查|篩選|檢查|驗證|監控|建立|設定|測試|分析|規劃|導入",
)
_MATURITY_LABEL = re.compile(r"\[(?:策略|流程|關鍵字|指標)\s*L\d+→L\d+\]")

_VERIFICATION_TAGS = re.compile(r"可驗證|需人工確認|需顧問判斷")
_VERIFICATION_METHODS = re.compile(
    r"在\s*(?:GSC|Search Console|PageSpeed|Ahrefs|GA4|Google Trends)\s*"
    r"|檢查\s|篩選\s|監控\s|排查\s|測試\s",
)

# Section → expected citation categories
_SECTION_CATEGORY_MAP: dict[str, set[str]] = {
    "3": {"技術SEO", "索引與檢索", "連結策略", "演算法與趨勢", "Discover與AMP", "搜尋表現分析"},
    "三": {"技術SEO", "索引與檢索", "連結策略", "演算法與趨勢", "Discover與AMP", "搜尋表現分析"},
    "6": {"技術SEO", "Discover與AMP", "連結策略", "搜尋表現分析", "演算法與趨勢"},
    "六": {"技術SEO", "Discover與AMP", "連結策略", "搜尋表現分析", "演算法與趨勢"},
}


def cross_section_coherence(output: dict, target: dict) -> float:
    """S1→S3 coverage × 0.5 + S3→S9 coverage × 0.5."""
    if "error" in output:
        return 0.0
    s1 = set(output["s1_alerts"])
    s3 = set(output["s3_metrics"])
    s9 = set(output["s9_metrics"])

    if not s1:
        return 0.0

    # Fuzzy match: S3 metric is "covered" if any S1 alert is a substring or vice versa
    def _fuzzy_covered(source: set[str], targets: set[str]) -> int:
        count = 0
        for s in source:
            for t in targets:
                if s in t or t in s or s.lower() == t.lower():
                    count += 1
                    break
        return count

    s1_in_s3 = _fuzzy_covered(s1, s3) / len(s1) if s1 else 0.0
    s3_in_s9 = _fuzzy_covered(s3, s9) / len(s3) if s3 else 0.0

    return s1_in_s3 * 0.5 + s3_in_s9 * 0.5


def action_specificity(output: dict, target: dict) -> float:
    """S10 action items scored by tool + condition + maturity label."""
    if "error" in output:
        return 0.0
    items = output["action_items"]
    if not items:
        return 0.0

    total_points = 0.0
    max_per_item = 2.5

    for item in items:
        points = 0.0
        if _TOOL_NAMES.search(item):
            points += 1.0
        if _ACTION_VERBS.search(item):
            points += 1.0
        if _MATURITY_LABEL.search(item):
            points += 0.5
        total_points += min(points, max_per_item)

    return total_points / (len(items) * max_per_item)


def hypothesis_falsifiability(output: dict, target: dict) -> float:
    """Fraction of S3 hypotheses tagged with verification method (可驗證/需人工/需顧問)."""
    if "error" in output:
        return 0.0
    # Count from raw S3: supports both table format (| H1a | ... | **可驗證** |)
    # and prose format (**假設 1** ... **可驗證**)
    s3 = _extract_section(output["raw_content"], "3") or _extract_section(output["raw_content"], "三")
    if not s3:
        return 0.0

    # Count hypothesis rows (table: | H\d+ | or prose: **假設 \d+**)
    table_hyp = re.findall(r"^\|\s*H\d+\w?\s*\|", s3, re.MULTILINE)
    prose_hyp = re.findall(r"\*\*假設\s*\d+", s3)
    total = len(table_hyp) + len(prose_hyp)
    if total == 0:
        return 0.0

    tagged = len(re.findall(r"可驗證|需人工確認|需顧問判斷", s3))
    return min(tagged / total, 1.0)


def temporal_consistency(output: dict, target: dict) -> float:
    """E-E-A-T score changes vs prior report should be ≤1 per dimension."""
    if "error" in output:
        return 0.0
    meta = output.get("meta")
    prior = output.get("prior_scores")

    if not meta or not prior:
        return 1.0  # First report or no history → pass

    eeat = meta.get("scores", {}).get("eeat", {})
    if not eeat:
        return 1.0

    dimensions = ["experience", "expertise", "authoritativeness", "trustworthiness"]
    reasonable = 0
    total = 0

    for dim in dimensions:
        curr = eeat.get(dim)
        prev = prior.get(dim)
        if curr is None or prev is None:
            continue
        total += 1
        delta = abs(curr - prev)
        if delta <= 1:
            reasonable += 1
        elif delta <= 2:
            reasonable += 0.5

    return reasonable / total if total > 0 else 1.0


def citation_relevance(output: dict, target: dict) -> float:
    """Fraction of inline citations whose KB category matches section context."""
    if "error" in output:
        return 0.0
    citations = output.get("citations", [])
    inline_by_section = output.get("inline_by_section", {})

    if not citations or not inline_by_section:
        return 0.5  # neutral

    cit_map = {c.get("n"): c.get("category", "") for c in citations}
    relevant = 0
    total = 0

    for section_id, refs in inline_by_section.items():
        expected_cats = _SECTION_CATEGORY_MAP.get(section_id, set())
        if not expected_cats:
            continue
        for ref_n in refs:
            cat = cit_map.get(ref_n, "")
            if not cat:
                continue
            total += 1
            if cat in expected_cats:
                relevant += 1

    return relevant / total if total > 0 else 0.5


# ── Evaluator map ─────────────────────────────────────────────────────────────

_EVALUATOR_MAP = {
    "cross_section_coherence": cross_section_coherence,
    "action_specificity": action_specificity,
    "hypothesis_falsifiability": hypothesis_falsifiability,
    "temporal_consistency": temporal_consistency,
    "citation_relevance": citation_relevance,
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
        thresholds: dict[str, float] = json.load(_tf).get("meeting_prep_coherence", {})
    if not thresholds:
        _exec_cache = {}
        return

    print("\n--- CI Eval Gate: meeting_prep_coherence thresholds ---")
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
    print("All meeting_prep_coherence thresholds passed.\n")


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
        group_name="meeting_prep_coherence",
    )


if __name__ == "__main__":
    run_eval()
