"""
_push_laminar_score.py — 將 Claude Code as Judge 分數推送至 Laminar（v2.13）

用於 /evaluate-faithfulness-local 和 /evaluate-context-precision-local
等 slash command 完成判斷後，將 Claude Code as Judge 計算出的分數
推送至 Laminar Dashboard 作為 score event。

使用：
    python scripts/_push_laminar_score.py --metric faithfulness --score 0.85
    python scripts/_push_laminar_score.py --metric context_precision --score 0.72
    python scripts/_push_laminar_score.py --metric faithfulness --score 0.85 \\
        --group generation-quality --label "v2.13 baseline"

支援的 metrics：
    faithfulness        — Answer 是否有幻覺（RAGAS Faithfulness）
    context_precision   — Retrieved contexts 有多少真正相關（RAGAS Context Precision）
    answer_relevance    — Answer 與 query 的相關性（RAGAS，待實作）
"""
from __future__ import annotations

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="推送 Claude Code as Judge 分數至 Laminar（v2.13）"
    )
    parser.add_argument(
        "--metric",
        required=True,
        choices=sorted(SUPPORTED_METRICS),
        help="評估指標名稱",
    )
    parser.add_argument(
        "--score",
        type=float,
        required=True,
        help="分數（0.0–1.0）",
    )
    parser.add_argument(
        "--group",
        default=DEFAULT_GROUP,
        help=f"Laminar group name（預設 {DEFAULT_GROUP!r}）",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="可選的描述標籤（例如 'v2.13 baseline'）",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    push_score(
        metric=args.metric,
        score=args.score,
        group_name=args.group,
        label=args.label,
    )


if __name__ == "__main__":
    main()
