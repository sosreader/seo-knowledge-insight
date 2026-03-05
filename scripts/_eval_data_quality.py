"""
_eval_data_quality.py — Layer 1 Data Quality Evaluators（v2.13+）

直接檢查 qa_final.json 或 Supabase qa_items 的整體健康度。
推送至 Laminar Dashboard 的 "data-quality" group。
選擇性儲存至 Supabase eval_runs 表（需設定 SUPABASE_URL/SUPABASE_ANON_KEY）。

指標（無 API 成本）：
  qa_count_in_range   — QA 總數在 [100, 2000] 之間（1.0 = 合格，0.0 = 異常）
  avg_confidence      — 平均信心分數（target ≥ 0.80）
  keyword_coverage    — 具備 ≥3 keywords 的 QA 比例（target ≥ 0.85）
  no_admin_content    — 無管理/模板類污染（1.0 = 乾淨，< 1.0 = 有污染）

使用：
    python scripts/_eval_data_quality.py
    python scripts/_eval_data_quality.py --source supabase
    python scripts/_eval_data_quality.py --group "data-quality"
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from utils.observability import init_laminar  # type: ignore

logger = logging.getLogger(__name__)

QA_FINAL_PATH = ROOT / "output" / "qa_final.json"
QA_ENRICHED_PATH = ROOT / "output" / "qa_enriched.json"

DEFAULT_GROUP = "data-quality"

# 合格門檻（可調整）
QA_COUNT_MIN = 100
QA_COUNT_MAX = 2000
CONFIDENCE_TARGET = 0.80
KEYWORD_COVERAGE_TARGET = 0.85
MIN_KEYWORDS_PER_QA = 3

# 管理/模板內容識別詞
_ADMIN_PATTERNS = [
    "會議紀錄", "下次開會", "action item", "todo:", "待討論",
    "placeholder", "template", "test qa", "測試用",
]


def _load_qas_local() -> list[dict]:
    """從本機 JSON 載入 QA 資料。"""
    path = QA_ENRICHED_PATH if QA_ENRICHED_PATH.exists() else QA_FINAL_PATH
    if not path.exists():
        raise FileNotFoundError(f"QA 資料不存在：{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["qa_database"]


def _load_qas_supabase() -> list[dict]:
    """從 Supabase qa_items 表載入 QA 資料（分頁）。"""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_ANON_KEY for --source supabase")

    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    all_rows: list[dict] = []
    page_size = 500
    offset = 0

    while True:
        resp = requests.get(
            f"{url}/rest/v1/qa_items"
            f"?select=id,question,answer,keywords,confidence&order=seq.asc"
            f"&limit={page_size}&offset={offset}",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
        offset += page_size

    logger.info("Loaded %d QA items from Supabase", len(all_rows))
    return all_rows


def _load_qas(source: str = "local") -> list[dict]:
    """Load QA items from local JSON or Supabase based on --source."""
    if source == "supabase":
        return _load_qas_supabase()
    return _load_qas_local()


def _upsert_eval_run(metrics: dict, group: str, passed: bool) -> None:
    """Save eval results to Supabase eval_runs table (best-effort)."""
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        return

    payload = {
        "trigger": "manual",
        "group_name": group,
        "metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
        "passed": passed,
        "qa_count": metrics.get("total"),
    }
    try:
        resp = requests.post(
            f"{url}/rest/v1/eval_runs",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=payload,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            logger.info("Saved eval_run to Supabase (group=%s)", group)
        else:
            logger.warning("eval_runs upsert returned %d: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Failed to save eval_run to Supabase: %s", exc)


def _is_admin_content(qa: dict) -> bool:
    """判斷是否為管理/模板類內容。"""
    text = (qa.get("question", "") + " " + qa.get("answer", "")).lower()
    return any(pattern.lower() in text for pattern in _ADMIN_PATTERNS)


def compute_data_quality_metrics(qas: list[dict]) -> dict:
    """計算所有 data quality 指標，回傳 dict（不修改 qas）。"""
    total = len(qas)

    # qa_count_in_range
    count_in_range = 1.0 if QA_COUNT_MIN <= total <= QA_COUNT_MAX else 0.0

    # avg_confidence
    confidences = [
        qa.get("confidence", 0.0)
        for qa in qas
        if isinstance(qa.get("confidence"), (int, float))
    ]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # keyword_coverage（≥ MIN_KEYWORDS_PER_QA 個 keywords）
    has_keywords = sum(
        1 for qa in qas
        if len(qa.get("keywords", [])) >= MIN_KEYWORDS_PER_QA
    )
    keyword_coverage = has_keywords / total if total > 0 else 0.0

    # no_admin_content（污染比例 = 1 - admin_ratio）
    admin_count = sum(1 for qa in qas if _is_admin_content(qa))
    no_admin_content = 1.0 - (admin_count / total) if total > 0 else 1.0

    return {
        "total": total,
        "qa_count_in_range": count_in_range,
        "avg_confidence": round(avg_confidence, 4),
        "keyword_coverage": round(keyword_coverage, 4),
        "no_admin_content": round(no_admin_content, 4),
        "admin_count": admin_count,
        "has_keywords_count": has_keywords,
        "confidence_sample_size": len(confidences),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Layer 1 Data Quality Evaluators（v2.13+）"
    )
    parser.add_argument(
        "--group",
        default=DEFAULT_GROUP,
        help=f"Laminar group name（預設 {DEFAULT_GROUP!r}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只列出指標，不推送至 Laminar",
    )
    parser.add_argument(
        "--source",
        choices=["local", "supabase"],
        default="local",
        help="資料來源：local（qa_final.json）或 supabase（qa_items 表）",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    qas = _load_qas(args.source)
    metrics = compute_data_quality_metrics(qas)

    logger.info("=== Data Quality 指標（%d 筆 QA）===", metrics["total"])
    logger.info("  qa_count_in_range   : %.4f  （目標 1.0，範圍 %d–%d）",
                metrics["qa_count_in_range"], QA_COUNT_MIN, QA_COUNT_MAX)
    logger.info("  avg_confidence      : %.4f  （目標 ≥ %.2f）",
                metrics["avg_confidence"], CONFIDENCE_TARGET)
    logger.info("  keyword_coverage    : %.4f  （目標 ≥ %.2f，≥%d keywords）",
                metrics["keyword_coverage"], KEYWORD_COVERAGE_TARGET, MIN_KEYWORDS_PER_QA)
    logger.info("  no_admin_content    : %.4f  （污染筆數：%d）",
                metrics["no_admin_content"], metrics["admin_count"])

    # 判斷是否通過（用於 eval_runs 記錄）
    _passed = (
        metrics["qa_count_in_range"] >= 1.0
        and metrics["avg_confidence"] >= CONFIDENCE_TARGET
        and metrics["keyword_coverage"] >= KEYWORD_COVERAGE_TARGET
    )

    # 儲存至 Supabase eval_runs（best-effort，不影響主流程）
    _upsert_eval_run(metrics, args.group, _passed)

    if args.dry_run:
        logger.info("--dry-run 模式：不推送至 Laminar")
        return

    try:
        from lmnr import evaluate  # type: ignore[import]
    except ImportError:
        logger.error("lmnr 未安裝，請執行：pip install lmnr")
        sys.exit(1)

    init_laminar()

    # Laminar evaluate() 需要 data + executor + evaluators 格式
    # 對 data quality 而言，整個 QA database 是一個「case」
    # output = metrics dict，evaluators 從中提取單一分數
    def _executor(_: dict) -> dict:
        return metrics

    def _qa_count_evaluator(output: dict, target: dict) -> float:  # noqa: ARG001
        return output.get("qa_count_in_range", 0.0)

    def _avg_confidence_evaluator(output: dict, target: dict) -> float:  # noqa: ARG001
        return output.get("avg_confidence", 0.0)

    def _keyword_coverage_evaluator(output: dict, target: dict) -> float:  # noqa: ARG001
        return output.get("keyword_coverage", 0.0)

    def _no_admin_evaluator(output: dict, target: dict) -> float:  # noqa: ARG001
        return output.get("no_admin_content", 0.0)

    logger.info("推送 data quality 指標至 Laminar（group=%r）", args.group)

    evaluate(
        data=[{"data": {"run": "data-quality"}, "target": {}}],
        executor=_executor,
        evaluators={
            "qa_count_in_range": _qa_count_evaluator,
            "avg_confidence": _avg_confidence_evaluator,
            "keyword_coverage": _keyword_coverage_evaluator,
            "no_admin_content": _no_admin_evaluator,
        },
        group_name=args.group,
        concurrency_limit=1,
    )

    logger.info("Data quality eval 完成，請至 Laminar Dashboard 查看（group=%r）", args.group)


if __name__ == "__main__":
    main()
