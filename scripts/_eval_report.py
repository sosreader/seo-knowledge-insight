"""
_eval_report.py — 週報品質評估 + Laminar trace（v2.17）

複製 api/src/services/report-evaluator.ts 邏輯，供 Claude Code fallback 使用。
在 /generate-report 本地生成後呼叫，將 7 個評估維度推送至 Laminar。

使用：
    python scripts/_eval_report.py --report output/report_20260305_8b21a9c3.md
    python scripts/_eval_report.py --report output/report_20260305_8b21a9c3.md \
        --alert-names "AMP Article,Google News,Organic Search"
"""
from __future__ import annotations

import argparse
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


def _extract_section(content: str, header: str) -> str:
    """Extract text from header until next ## heading."""
    idx = content.find(header)
    if idx == -1:
        return ""
    after = content[idx + len(header):]
    next_h = re.search(r"\n## ", after)
    return after[: next_h.start()] if next_h else after


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
    action_section = _extract_section(content, "## 五、")
    if alert_names:
        section_lower = action_section.lower()
        mentioned = 0
        for name in alert_names:
            name_lower = name.lower()
            if name_lower in section_lower:
                mentioned += 1
                continue
            # Strip parenthetical suffix: "News(new)" → "News"
            core_name = re.sub(r"\s*\(.*?\)\s*", "", name_lower).strip()
            if len(core_name) >= 2 and core_name in section_lower:
                mentioned += 1
        alert_coverage = mentioned / len(alert_names)
    else:
        alert_coverage = 1.0  # No alerts → nothing to cover → full credit

    overall = (
        section_coverage + kb_citation_count + has_research + has_kb_links + alert_coverage
    ) / 5

    llm_augmented = 1.0 if ("AI 輔助" in content or "AI 解讀" in content) else 0.0

    return {
        "report_section_coverage": round(section_coverage, 4),
        "report_kb_citations": round(kb_citation_count, 4),
        "report_has_research": has_research,
        "report_has_links": has_kb_links,
        "report_alert_coverage": round(alert_coverage, 4),
        "report_overall": round(overall, 4),
        "report_llm_augmented": llm_augmented,
    }


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

    scores = evaluate_report(content, alert_names)

    # Print summary
    print(f"\n── 週報評估結果：{label} ──")
    for name, val in scores.items():
        bar = "█" * int(val * 10) + "░" * (10 - int(val * 10))
        print(f"  {name:<30} {val:.4f}  {bar}")
    print()

    push_to_laminar(scores, label)


if __name__ == "__main__":
    main()
