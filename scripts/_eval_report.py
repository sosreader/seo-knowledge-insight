"""
_eval_report.py — 週報品質評估 + Laminar trace（v3.7）

L1: 複製 api/src/services/report-evaluator.ts 邏輯（結構護欄）
L2: 複製 api/src/services/report-evaluator-l2.ts 邏輯（連續指標）
composite_v2: L1+L2 加權合併（L3 由 Claude Code /evaluate-report-quality 外部執行）

使用：
    python scripts/_eval_report.py --report output/report_20260305_8b21a9c3.md
    python scripts/_eval_report.py --report output/report_20260305_8b21a9c3.md \
        --alert-names "AMP Article,Google News,Organic Search"
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from utils.observability import init_laminar  # type: ignore

logger = logging.getLogger(__name__)

SECTION_MARKERS = ["## 一、", "## 二、", "## 三、", "## 四、", "## 五、", "## 六、"]
RESEARCH_KEYWORDS = [
    "Backlinko", "Semrush", "NavBoost", "First Page Sage",
    "arxiv", "SEOCausal", "CausalImpact", "E-E-A-T",
]
# Matches /admin/seoInsight/{hex16} or /admin/seoInsight/{digits}
KB_LINK_RE = re.compile(r"/admin/seoInsight/(?:[0-9a-f]{16}|\d+)")
GROUP_NAME = "report-quality"

# ── L2 Constants ───────────────────────────────────────────────────────

SEO_METRICS = [
    "CTR", "曝光", "點擊", "排名", "索引", "Discover", "CLS", "LCP",
    "FID", "INP", "Core Web Vitals", "反向連結", "外部連結", "內部連結",
    "跳出率", "停留時間", "轉換率", "流量", "有機搜尋", "AI Overview",
    "檢索未索引", "收錄", "爬取", "網頁速度", "Position", "E-E-A-T",
    "佔比", "覆蓋率",
]

CAUSAL_CONNECTORS = [
    "導致", "因此", "因為", "表示", "意味著", "這表示", "這意味",
    "由於", "造成", "然而", "但", "儘管", "雖然", "進而", "以致",
    "所以", "反映", "顯示", "源自", "歸因",
]

SPECIFIC_ACTION_RES = [
    re.compile(r"在\s*(?:GSC|Search Console|PageSpeed|Chrome|Screaming Frog|Ahrefs|Semrush)"),
    re.compile(r"篩選"), re.compile(r"檢查"), re.compile(r"驗證"),
    re.compile(r"使用\s*\S+\s*(?:面板|報表|工具)"),
    re.compile(r"部署後\s*\d+"), re.compile(r"設定\s*\S+"),
    re.compile(r"加入\s*\S+"), re.compile(r"移除\s*\S+"),
    re.compile(r"重寫"), re.compile(r"優化\s*(?:title|標題|description|meta)", re.IGNORECASE),
    re.compile(r"補上"), re.compile(r"修復"), re.compile(r"排查"), re.compile(r"測試"),
]

VAGUE_ACTION_RES = [
    re.compile(r"^-?\s*注意"), re.compile(r"^-?\s*持續觀察"),
    re.compile(r"^-?\s*關注"), re.compile(r"^-?\s*需要(?:改善|注意|觀察)"),
    re.compile(r"^-?\s*觀察"), re.compile(r"^-?\s*留意"),
    re.compile(r"^-?\s*追蹤(?!.*(?:工具|報表|面板))"),
]

QUADRANT_KEYWORDS = ["高曝光低點擊", "低曝光高點擊", "高曝光高點擊", "低曝光低點擊"]
QUADRANT_EXPLANATION_SIGNALS = [
    "建議", "表示", "因為", "利基", "優勢", "需要", "應該", "代表", "意味",
]

L2_SECTION_MARKERS = ["## 一、", "## 二、", "## 三、", "## 四、", "## 五、", "## 六、", "## 七、"]

PERCENT_RE = re.compile(r"[+-]?\d+(?:\.\d+)?%")
LARGE_NUMBER_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{3,}\b")
CITATION_RE = re.compile(r"\[(\d+)\]")


def _extract_section(content: str, header: str) -> str:
    """Extract text from header until next ## heading."""
    idx = content.find(header)
    if idx == -1:
        return ""
    after = content[idx + len(header):]
    next_h = re.search(r"\n## ", after)
    return after[: next_h.start()] if next_h else after


MATURITY_DIMENSIONS = {"策略", "流程", "關鍵字", "指標"}


def _report_action_maturity_labeled(content: str) -> float:
    """Check action items for maturity level markers — graded by coverage.

    Scoring:
    - No action section → 0.5 (degraded gracefully)
    - No maturity reference line → 0.5 (no meeting-prep available)
    - Has ref line but no labels → 0.0
    - Has ref line + labels → total label count / 6 (max 1.0)
    """
    s_action = _extract_section(content, "優先行動清單")
    if not s_action:
        s_action = _extract_section(content, "## 六、") or _extract_section(content, "## 五、")
    if not s_action:
        return 0.5

    labels = re.findall(
        r"\[(?:策略|流程|關鍵字|指標)\s*L[1-4]→L[1-4]\]", s_action
    )
    has_ref_line = "成熟度參考" in s_action
    if not has_ref_line:
        return 0.5
    if not labels:
        return 0.0
    return min(len(labels) / 6, 1.0)


def evaluate_report(content: str, alert_names: list[str]) -> dict[str, float]:
    if not content.strip():
        return {
            "report_section_coverage": 0,
            "report_kb_citations": 0,
            "report_has_research": 0,
            "report_has_links": 0,
            "report_alert_coverage": 0,
            "report_overall": 0,
            "report_llm_augmented": 0,
        }

    # 1. section_coverage
    sections_found = sum(1 for m in SECTION_MARKERS if m in content)
    section_coverage = sections_found / len(SECTION_MARKERS)

    # 2. kb_citation_count
    kb_matches = KB_LINK_RE.findall(content)
    unique_kb = len(set(kb_matches))
    section_six = _extract_section(content, "## 六、")
    external_links = re.findall(r"https?://[^\s)>]+", section_six)
    total_citations = unique_kb + len(external_links)
    kb_citation_count = min(total_citations / 6, 1.0)

    # 3. has_research_citations
    has_research = 1.0 if any(kw in content for kw in RESEARCH_KEYWORDS) else 0.0

    # 4. has_kb_links
    has_kb_links = 1.0 if KB_LINK_RE.search(content) else 0.0

    # 5. alert_coverage (fuzzy: substring + core-name match)
    # Search full report body — alert names are specific enough to avoid false positives
    search_text = content.lower()
    if alert_names:
        mentioned = 0
        for name in alert_names:
            name_lower = name.lower()
            if name_lower in search_text:
                mentioned += 1
                continue
            # Strip parenthetical suffix: "News(new)" → "News"
            core_name = re.sub(r"\s*\(.*?\)\s*", "", name_lower).strip()
            if len(core_name) >= 2 and core_name in search_text:
                mentioned += 1
                continue
            # Strip "KW:" / "KW: " prefix: "KW: 影評" → "影評"
            kw_stripped = re.sub(r"^kw:\s*", "", name_lower).strip()
            if kw_stripped != name_lower and len(kw_stripped) >= 2 and kw_stripped in search_text:
                mentioned += 1
        alert_coverage = mentioned / len(alert_names)
    else:
        alert_coverage = 1.0  # No alerts → nothing to cover → full credit

    overall = (
        section_coverage + kb_citation_count + has_research + has_kb_links + alert_coverage
    ) / 5

    # Detect LLM augmentation via report_meta generation_mode OR legacy markers
    llm_augmented = 0.0
    meta_match = re.search(r"<!--\s*report_meta\s+(\{.*?\})\s*-->", content)
    if meta_match:
        try:
            meta = json.loads(meta_match.group(1))
            mode = meta.get("generation_mode", "")
            if mode in ("claude-code", "openai"):
                llm_augmented = 1.0
        except (json.JSONDecodeError, TypeError):
            pass
    # Fallback: legacy API template markers
    if llm_augmented == 0.0 and ("AI 輔助" in content or "AI 解讀" in content):
        llm_augmented = 1.0

    # 8. report_action_maturity_labeled
    maturity_labeled = _report_action_maturity_labeled(content)

    return {
        "report_section_coverage": round(section_coverage, 4),
        "report_kb_citations": round(kb_citation_count, 4),
        "report_has_research": has_research,
        "report_has_links": has_kb_links,
        "report_alert_coverage": round(alert_coverage, 4),
        "report_overall": round(overall, 4),
        "report_llm_augmented": llm_augmented,
        "report_action_maturity_labeled": maturity_labeled,
    }


# ── L2 Pure Functions ──────────────────────────────────────────────────

def cross_metric_reasoning(content: str) -> float:
    """Causal connector + ≥2 distinct SEO metrics in same paragraph → count/5."""
    if not content.strip():
        return 0.0
    paragraphs = [p.strip() for p in re.split(r"\n+", content) if p.strip()]
    count = 0
    for para in paragraphs:
        if not any(c in para for c in CAUSAL_CONNECTORS):
            continue
        found = {m for m in SEO_METRICS if m in para}
        if len(found) >= 2:
            count += 1
    return min(count / 15, 1.0)


def action_specificity(content: str) -> float:
    """Ratio of specific vs vague action items."""
    if not content.strip():
        return 0.0
    lines = [ln.strip() for ln in content.split("\n") if re.match(r"^\s*(?:-|\d+\.)\s", ln)]
    if not lines:
        return 0.0
    specific = sum(1 for ln in lines if any(p.search(ln) for p in SPECIFIC_ACTION_RES))
    # All action lines count as denominator (not just specific + vague)
    return specific / len(lines) if lines else 0.0


def data_evidence_ratio(content: str) -> float:
    """Paragraph-level data coverage: paragraphs containing % or large numbers / 15."""
    if not content.strip():
        return 0.0
    paragraphs = [p.strip() for p in re.split(r"\n\n+", content) if p.strip()]
    count = sum(
        1 for p in paragraphs
        if PERCENT_RE.search(p) or LARGE_NUMBER_RE.search(p)
    )
    return min(count / 70, 1.0)


def citation_integration(content: str) -> float:
    """Inline [N] ratio × section diversity — citations spread across sections."""
    if not content.strip():
        return 0.0
    all_cites = set(CITATION_RE.findall(content))
    if not all_cites:
        return 0.0
    ref_idx = content.find("## 七、")
    body = content[:ref_idx] if ref_idx != -1 else content
    body_cites = set(CITATION_RE.findall(body))
    inline_ratio = len(body_cites) / len(all_cites)

    # Section diversity: how many sections contain citations
    sections_with_cite = 0
    for marker in L2_SECTION_MARKERS:
        section = _extract_section(content, marker)
        if section and CITATION_RE.search(section):
            sections_with_cite += 1
    section_diversity = sections_with_cite / len(L2_SECTION_MARKERS) if L2_SECTION_MARKERS else 1.0

    return inline_ratio * section_diversity


def quadrant_judgment(content: str) -> float:
    """0/0.5/1.0 — quadrant keyword + optional explanation."""
    if not content.strip():
        return 0.0
    has_quadrant = False
    has_explanation = False
    for kw in QUADRANT_KEYWORDS:
        idx = content.find(kw)
        if idx == -1:
            continue
        has_quadrant = True
        nearby = content[idx: idx + 200]
        if any(sig in nearby for sig in QUADRANT_EXPLANATION_SIGNALS):
            has_explanation = True
            break
    if not has_quadrant:
        return 0.0
    return 1.0 if has_explanation else 0.5


def section_depth_variance(content: str) -> float:
    """1 - (std / mean) of section char counts."""
    if not content.strip():
        return 0.0
    lengths: list[int] = []
    for marker in L2_SECTION_MARKERS:
        idx = content.find(marker)
        if idx == -1:
            continue
        after = idx + len(marker)
        next_h = content.find("\n## ", after)
        section = content[after:next_h] if next_h != -1 else content[after:]
        char_count = len(re.sub(r"\s", "", section))
        lengths.append(char_count)
    if len(lengths) < 2:
        return 0.0
    mean = sum(lengths) / len(lengths)
    if mean == 0:
        return 0.0
    variance = sum((n - mean) ** 2 for n in lengths) / len(lengths)
    std = variance ** 0.5
    cv = std / mean
    return max(0.0, min(1.0, 1.0 - cv))


WEEK_PCT_RE = re.compile(r"週.*?[+-]?\d+(?:\.\d+)?%|[+-]?\d+(?:\.\d+)?%.*?週")
MONTH_PCT_RE = re.compile(r"月.*?[+-]?\d+(?:\.\d+)?%|[+-]?\d+(?:\.\d+)?%.*?月")


def temporal_dual_frame(content: str) -> float:
    """Lines with BOTH weekly AND monthly percentage data (strict dual-frame)."""
    if not content.strip():
        return 0.0
    count = 0
    for line in content.split("\n"):
        if WEEK_PCT_RE.search(line) and MONTH_PCT_RE.search(line):
            count += 1
    return min(count / 15, 1.0)


def priority_balance(content: str) -> float:
    """🔴/🟡/🟢 distribution balance — count lines containing each emoji."""
    if not content.strip():
        return 0.0
    lines = content.split("\n")
    red = sum(1 for ln in lines if "🔴" in ln)
    yellow = sum(1 for ln in lines if "🟡" in ln)
    green = sum(1 for ln in lines if "🟢" in ln)
    total = red + yellow + green
    if total == 0:
        return 0.0
    # Thresholds: 🔴≥4, 🟡≥3, 🟢≥2 (higher than previous /3, /2, /1)
    return round(
        (min(red / 4, 1.0) + min(yellow / 3, 1.0) + min(green / 2, 1.0)) / 3,
        4,
    )


def causal_chain(content: str) -> float:
    """Count structured **現象** → **原因** → **行動** analysis blocks."""
    if not content.strip():
        return 0.0
    blocks = re.findall(
        r"\*\*現象\*\*.*?\*\*原因\*\*.*?\*\*行動\*\*", content, re.DOTALL
    )
    return min(len(blocks) / 5, 1.0)


TOP_REC_REASON_RES = [
    re.compile(r"雖然"), re.compile(r"因為"), re.compile(r"理由"),
    re.compile(r"原因"), re.compile(r"而"), re.compile(r"但"),
    re.compile(r"相比"), re.compile(r"優先"),
]


def top_recommendation(content: str) -> float:
    """Graded: has 💡/最值得投入 (0.5) + has justification reason (0.5)."""
    if not content.strip():
        return 0.0
    has_marker = "最值得投入" in content or "💡" in content
    if not has_marker:
        return 0.0
    # Find the marker's surrounding text (200 chars after)
    idx = content.find("最值得投入")
    if idx == -1:
        idx = content.find("💡")
    nearby = content[idx: idx + 300]
    has_reason = any(r.search(nearby) for r in TOP_REC_REASON_RES)
    return 1.0 if has_reason else 0.5


def evaluate_report_l2(content: str) -> dict[str, float]:
    """Run all 10 L2 metrics."""
    return {
        "report_cross_metric_reasoning": round(cross_metric_reasoning(content), 4),
        "report_action_specificity": round(action_specificity(content), 4),
        "report_data_evidence_ratio": round(data_evidence_ratio(content), 4),
        "report_citation_integration": round(citation_integration(content), 4),
        "report_quadrant_judgment": round(quadrant_judgment(content), 4),
        "report_section_depth_variance": round(section_depth_variance(content), 4),
        "report_temporal_dual_frame": round(temporal_dual_frame(content), 4),
        "report_priority_balance": round(priority_balance(content), 4),
        "report_causal_chain": round(causal_chain(content), 4),
        "report_top_recommendation": round(top_recommendation(content), 4),
    }


def compute_composite_v2(l1_overall: float, l2: dict[str, float]) -> float:
    """Composite V2 without L3 (fallback weights)."""
    return round(
        l1_overall * 0.30
        + l2["report_cross_metric_reasoning"] * 0.15
        + l2["report_action_specificity"] * 0.15
        + l2["report_data_evidence_ratio"] * 0.12
        + l2["report_citation_integration"] * 0.10
        + l2["report_quadrant_judgment"] * 0.10
        + l2["report_section_depth_variance"] * 0.08,
        4,
    )


def compute_composite_v3(l1: dict[str, float], l2: dict[str, float]) -> float:
    """Composite V3: 12 metrics (L1 overall + maturity + 10 L2). Sum = 1.00."""
    return round(
        # Guardrail (0.12)
        l1["report_overall"] * 0.12
        # Core analysis quality (0.30)
        + l2["report_cross_metric_reasoning"] * 0.15
        + l2["report_action_specificity"] * 0.15
        # Content richness (0.34)
        + l2["report_data_evidence_ratio"] * 0.09
        + l2["report_citation_integration"] * 0.08
        + l2["report_quadrant_judgment"] * 0.07
        + l2["report_section_depth_variance"] * 0.10
        # Structure + new dimensions (0.24)
        + l2["report_temporal_dual_frame"] * 0.07
        + l2["report_causal_chain"] * 0.06
        + l2["report_priority_balance"] * 0.05
        + l1["report_action_maturity_labeled"] * 0.04
        + l2["report_top_recommendation"] * 0.02,
        4,
    )


def push_to_laminar(scores: dict[str, float], label: str) -> None:
    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.warning("lmnr 未安裝，跳過 Laminar 推送（pip install lmnr）")
        return

    init_laminar()

    # Push each metric as a separate evaluator under one eval run
    evaluators = {name: (lambda score: lambda o, t: o)(val) for name, val in scores.items()}
    data = [{
        "data": {name: val for name, val in scores.items()},
        "target": {"label": label},
    }]

    # evaluate() expects executor + per-metric evaluators
    # We use a passthrough executor and fixed-score evaluators
    def _executor(inputs: dict) -> dict:
        return inputs

    fixed_evaluators = {}
    for metric_name, val in scores.items():
        def _make_evaluator(mn: str, v: float):
            def _eval(output: dict, target: dict) -> float:  # noqa: ARG001
                return output.get(mn, v)
            return _eval
        fixed_evaluators[metric_name] = _make_evaluator(metric_name, val)

    evaluate(
        data=data,
        executor=_executor,
        evaluators=fixed_evaluators,
        group_name=GROUP_NAME,
        concurrency_limit=1,
    )

    logger.info(
        "Laminar report eval 推送完成（group=%r, label=%r）", GROUP_NAME, label
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="週報品質評估 + Laminar trace（v2.17）"
    )
    parser.add_argument("--report", required=True, help="報告 Markdown 路徑")
    parser.add_argument(
        "--alert-names",
        default="",
        help="逗號分隔的 ALERT_DOWN 指標名稱（例如 'AMP Article,Google News'）",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    report_path = Path(args.report)
    if not report_path.exists():
        logger.error("找不到報告檔案：%s", report_path)
        sys.exit(1)

    content = report_path.read_text(encoding="utf-8")
    alert_names = [n.strip() for n in args.alert_names.split(",") if n.strip()]
    label = report_path.stem  # e.g. report_20260305_8b21a9c3

    l1_scores = evaluate_report(content, alert_names)
    l2_scores = evaluate_report_l2(content)
    composite = compute_composite_v2(l1_scores["report_overall"], l2_scores)

    all_scores = {**l1_scores, **l2_scores, "report_composite_v2": composite}

    # Print summary
    print(f"\n── 週報評估結果：{label} ──")
    print("  [L1 Structural]")
    for name, val in l1_scores.items():
        bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
        print(f"    {name:<34} {val:.4f}  {bar}")
    print("  [L2 Content Quality]")
    for name, val in l2_scores.items():
        bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
        print(f"    {name:<34} {val:.4f}  {bar}")
    print(f"  [Composite V2]")
    bar = "█" * int(composite * 10) + "░" * (10 - int(composite * 10))
    print(f"    {'report_composite_v2':<34} {composite:.4f}  {bar}")
    print()

    push_to_laminar(all_scores, label)


if __name__ == "__main__":
    main()
