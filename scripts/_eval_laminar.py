"""
_eval_laminar.py — Laminar 正式 Eval Run

將 golden_retrieval.json 推送至 Laminar Dashboard 作為正式評估資料集。
執行後結果出現在 Laminar Dashboard 的 Evaluations 頁面。

使用：
    python scripts/_eval_laminar.py
    python scripts/_eval_laminar.py --top-k 5
    python scripts/_eval_laminar.py --dataset-name "retrieval-eval-20260302"
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# 確保 project root 在 import path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.observability import init_laminar  # type: ignore

logger = logging.getLogger(__name__)

GOLDEN_RETRIEVAL_PATH = ROOT / "output" / "evals" / "golden_retrieval.json"
QA_FINAL_PATH = ROOT / "output" / "qa_final.json"
QA_ENRICHED_PATH = ROOT / "output" / "qa_enriched.json"


def _load_qas() -> list[dict]:
    path = QA_ENRICHED_PATH if QA_ENRICHED_PATH.exists() else QA_FINAL_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["qa_database"]


def _keyword_search(query: str, qas: list[dict], top_k: int) -> list[dict]:
    query_lower = query.lower()
    scored: list[tuple[float, dict]] = []
    for qa in qas:
        score = 0.0
        if query_lower in qa.get("question", "").lower():
            score += 1.0
        if query_lower in qa.get("answer", "").lower():
            score += 0.5
        for kw in qa.get("keywords", []):
            if kw.lower() in query_lower or query_lower in kw.lower():
                score += 0.3
        if score > 0:
            scored.append((score, qa))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [qa for _, qa in scored[:top_k]]


def precision_evaluator(output: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not output:
        return 0.0
    relevant = sum(1 for qa in output if qa.get("category", "") in expected_cats)
    return relevant / len(output)


def recall_evaluator(output: list[dict], target: dict) -> float:
    expected_cats = set(target.get("expected_categories", []))
    if not expected_cats:
        return 1.0
    retrieved_cats = {qa.get("category", "") for qa in output}
    return len(retrieved_cats & expected_cats) / len(expected_cats)


def f1_evaluator(output: list[dict], target: dict) -> float:
    p = precision_evaluator(output, target)
    r = recall_evaluator(output, target)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def main() -> None:
    parser = argparse.ArgumentParser(description="Laminar 正式 Eval Run")
    parser.add_argument("--top-k", type=int, default=5, help="Retrieval top-K")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    parser.add_argument("--dataset-name", default=f"retrieval-eval-{today}", help="Laminar dataset name")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not GOLDEN_RETRIEVAL_PATH.exists():
        logger.error("golden_retrieval.json 不存在：%s", GOLDEN_RETRIEVAL_PATH)
        sys.exit(1)

    golden_cases = json.loads(GOLDEN_RETRIEVAL_PATH.read_text(encoding="utf-8"))
    if not isinstance(golden_cases, list) or not golden_cases:
        logger.error("golden_retrieval.json 應為非空 JSON array")
        sys.exit(1)

    qas = _load_qas()
    top_k = args.top_k

    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.error("lmnr 未安裝，請執行：pip install lmnr")
        sys.exit(1)

    init_laminar()

    logger.info("開始 Laminar eval run，%d cases，top-k=%d", len(golden_cases), top_k)

    evaluate(
        data=[{"data": {"query": c["query"], "top_k": top_k}, "target": c} for c in golden_cases],
        executor=lambda d: _keyword_search(d["query"], qas, d["top_k"]),
        evaluators={
            "precision": precision_evaluator,
            "recall": recall_evaluator,
            "f1": f1_evaluator,
        },
        group_name=args.dataset_name,
    )

    logger.info("Eval run 完成，請至 Laminar Dashboard 查看結果")


if __name__ == "__main__":
    main()
