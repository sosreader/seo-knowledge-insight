"""
_push_laminar_score.py — 將 Claude Code as Judge 分數推送至 Laminar（v3.3）

用於 /evaluate-faithfulness-local、/evaluate-context-precision-local、
/evaluate-meeting-prep-quality 等 slash command 完成判斷後，
將分數推送至 Laminar Dashboard 作為 score event。

使用（單一指標）：
    python scripts/_push_laminar_score.py --metric faithfulness --score 0.85
    python scripts/_push_laminar_score.py --metric faithfulness --score 0.85 \\
        --group generation-quality --label "v2.13 baseline"

使用（JSON 批次推送）：
    python scripts/_push_laminar_score.py \\
        --json-file output/eval_meeting_prep_quality_20260312.json \\
        --group meeting_prep_quality

支援的 metrics（單一模式）：
    faithfulness        — Answer 是否有幻覺（RAGAS Faithfulness）
    context_precision   — Retrieved contexts 有多少真正相關（RAGAS Context Precision）
    answer_relevance    — Answer 與 query 的相關性（RAGAS，待實作）

JSON 批次模式：
    讀取 JSON 中 dimensions.*.score → 正規化至 [0,1]（除以 5）→ 推送全部維度
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from utils.observability import init_laminar  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_GROUP = "generation-quality"

SUPPORTED_METRICS = {
    "faithfulness",
    "context_precision",
    "answer_relevance",
    "context_relevance",
}


def push_score(
    metric: str,
    score: float,
    group_name: str = DEFAULT_GROUP,
    label: str | None = None,
) -> None:
    """推送單一指標分數至 Laminar。

    使用 evaluate() 包裝成單一 case 的 eval run，
    group 固定為 "generation-quality"，與 retrieval-eval 分開追蹤。
    """
    if metric not in SUPPORTED_METRICS:
        raise ValueError(
            f"不支援的 metric {metric!r}，"
            f"支援清單：{sorted(SUPPORTED_METRICS)}"
        )
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score 必須在 [0, 1] 範圍內，收到：{score}")

    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.error("lmnr 未安裝，請執行：pip install lmnr")
        sys.exit(1)

    init_laminar()

    # 固定分數 evaluator
    def _fixed_score(output: float, target: dict) -> float:  # noqa: ARG001
        return output

    target = {"label": label or f"{metric} score"}

    logger.info(
        "推送分數 metric=%r score=%.4f group=%r", metric, score, group_name
    )

    evaluate(
        data=[{"data": score, "target": target}],
        executor=lambda x: x,  # 直接穿透
        evaluators={metric: _fixed_score},
        group_name=group_name,
        concurrency_limit=1,
    )

    logger.info("分數推送完成，請至 Laminar Dashboard 查看（group=%r）", group_name)


def push_json_file(
    json_path: str,
    group_name: str,
    label: str | None = None,
) -> None:
    """讀取 eval JSON 檔案，批次推送 dimensions 至 Laminar。

    JSON 格式：{"dimensions": {"metric_name": {"score": 1-5, ...}, ...}}
    分數會從 1-5 正規化至 0-1（除以 5）。
    """
    path = Path(json_path)
    if not path.exists():
        logger.error("找不到 JSON 檔案：%s", path)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    dimensions = data.get("dimensions", {})
    if not dimensions:
        logger.error("JSON 中找不到 dimensions 欄位")
        sys.exit(1)

    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.error("lmnr 未安裝，請執行：pip install lmnr")
        sys.exit(1)

    init_laminar()

    # Normalize scores from 1-5 to 0-1, clamp to valid range
    scores: dict[str, float] = {}
    for name, dim_data in dimensions.items():
        if not isinstance(dim_data, dict) or "score" not in dim_data:
            continue
        normalized = dim_data["score"] / 5.0
        if not 0.0 <= normalized <= 1.0:
            logger.warning(
                "Score out of range for %s: %s → %.2f, clamping",
                name, dim_data["score"], normalized,
            )
            normalized = max(0.0, min(1.0, normalized))
        scores[name] = normalized

    if not scores:
        logger.error("dimensions 中找不到有效的 score 欄位")
        sys.exit(1)

    resolved_label = label or data.get("report_path", path.stem)

    # Build evaluators for all dimensions
    def _make_evaluator(val: float):
        def _eval(output: dict, target: dict) -> float:  # noqa: ARG001
            return val
        return _eval

    evaluators = {name: _make_evaluator(val) for name, val in scores.items()}

    evaluate(
        data=[{
            "data": scores,
            "target": {"label": resolved_label},
        }],
        executor=lambda x: x,
        evaluators=evaluators,
        group_name=group_name,
        concurrency_limit=1,
    )

    logger.info(
        "批次推送完成：%d 個維度 → group=%r（label=%r）",
        len(scores), group_name, resolved_label,
    )
    for name, val in scores.items():
        logger.info("  %s: %.4f", name, val)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="推送 Claude Code as Judge 分數至 Laminar（v3.3）"
    )

    # Mode 1: single metric
    parser.add_argument(
        "--metric",
        choices=sorted(SUPPORTED_METRICS),
        help="評估指標名稱（單一模式）",
    )
    parser.add_argument(
        "--score",
        type=float,
        help="分數 0.0–1.0（單一模式）",
    )

    # Mode 2: JSON batch
    parser.add_argument(
        "--json-file",
        help="eval JSON 檔案路徑（批次模式，讀取 dimensions.*.score）",
    )

    # Shared
    parser.add_argument(
        "--group",
        default=DEFAULT_GROUP,
        help=f"Laminar group name（預設 {DEFAULT_GROUP!r}）",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="可選的描述標籤",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.json_file:
        push_json_file(
            json_path=args.json_file,
            group_name=args.group,
            label=args.label,
        )
    elif args.metric and args.score is not None:
        push_score(
            metric=args.metric,
            score=args.score,
            group_name=args.group,
            label=args.label,
        )
    else:
        parser.error("請指定 --json-file（批次模式）或 --metric + --score（單一模式）")


if __name__ == "__main__":
    main()
