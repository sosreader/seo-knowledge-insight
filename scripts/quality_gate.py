"""
quality_gate.py — ETL 後品質門檻檢查（MLOps Quality Gate）

讀取最新的 eval_run 結果（Supabase eval_runs 表或本機 output/evals/）
若任一指標缺值、過期或低於門檻則 exit(1)，讓 GitHub Actions fail 並阻止部署。

用法：
  python scripts/quality_gate.py
  python scripts/quality_gate.py --source local        # 讀本機 JSON
  python scripts/quality_gate.py --source supabase     # 讀 Supabase eval_runs 表
  python scripts/quality_gate.py --source supabase --max-age-hours 48  # 本機補查較舊的 run
  python scripts/quality_gate.py --dry-run             # 只輸出結果，不 exit(1)

品質門檻（依 v2.12 基準線，見 research/03-evaluation.md「評估基準線」）：
  qa_count_min        1000     — 最少 QA 數量            ← group data-quality
  hit_rate_min        0.90     — Hit Rate@5 >= 90%       ← group keyword-retrieval
  mrr_min             0.80     — MRR >= 0.80             ← group keyword-retrieval
  avg_confidence_min  0.75     — 平均信心分數 >= 0.75     ← group data-quality

═══ 缺值一律 FAIL（2026-09-15）═══

原版把缺值 fallback 成 0.0（hit_rate／mrr 必 FAIL，但訊息寫成
「hit_rate=0.00% < 90%」，看起來像檢索壞了），avg_confidence 缺值則直接
略過（缺值 = 通過）。而 hit_rate／mrr 從來沒有程式碼寫進 eval_runs——
_eval_laminar.py 只推 Laminar Dashboard——所以這道門從設計上就不可能通過。

現在每個指標綁定一個來源 group（METRIC_SPECS），Supabase 模式對每個 group
只取「最新一筆」且必須在 --max-age-hours 內。缺 group、過期、缺值、NaN
都列為失敗並指出是哪個寫入者沒寫，不再把不同 group、不同時間的 run
merge 在一起。
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
LOCAL_EVALS_DIR = ROOT_DIR / "output" / "evals"
load_dotenv(ROOT_DIR / ".env")

# ── Quality Gate Thresholds ──────────────────────────────────────────────────
THRESHOLDS: dict[str, float] = {
    "qa_count_min": 1000,
    "hit_rate_min": 0.90,
    "mrr_min": 0.80,
    "avg_confidence_min": 0.75,
}
# ────────────────────────────────────────────────────────────────────────────

DATA_QUALITY_GROUP = "data-quality"
KEYWORD_RETRIEVAL_GROUP = "keyword-retrieval"

# 每個 group 由誰寫進 eval_runs——缺 group 時錯誤訊息直接指出該查哪一步。
GROUP_WRITERS: dict[str, str] = {
    DATA_QUALITY_GROUP: "scripts/_eval_data_quality.py",
    KEYWORD_RETRIEVAL_GROUP: "scripts/_eval_laminar.py --group keyword-retrieval",
}

# etl-and-deploy.yml 的 eval job 在同一個 job 裡先寫 eval_runs、一兩分鐘後才跑
# gate（run 34106023623：data quality eval 11:09:44→11:10:32）。6 小時足以涵蓋
# 單獨 re-run eval job，又能擋下「本次 eval 沒寫成功、gate 卻讀到上週那筆」。
MAX_EVAL_RUN_AGE_HOURS = 6.0


@dataclass(frozen=True)
class MetricSpec:
    name: str
    threshold_key: str
    group: str
    aliases: tuple[str, ...] = ()
    precision: int = 3


METRIC_SPECS: tuple[MetricSpec, ...] = (
    MetricSpec("qa_count", "qa_count_min", DATA_QUALITY_GROUP, ("total_qa_count",), precision=0),
    MetricSpec("avg_confidence", "avg_confidence_min", DATA_QUALITY_GROUP, ("average_confidence",)),
    MetricSpec("hit_rate", "hit_rate_min", KEYWORD_RETRIEVAL_GROUP, ("hit_rate@5",)),
    MetricSpec("mrr", "mrr_min", KEYWORD_RETRIEVAL_GROUP, ("MRR",)),
)


class EvalRunFetchError(RuntimeError):
    """讀 eval_runs 失敗（連線錯誤或 HTTP 非 200）。"""


def _metric_value(metrics: dict[str, Any], spec: MetricSpec) -> float | None:
    """取指標值；缺值、非數字、bool、NaN 一律回 None。

    不能用 `a or b or 0.0`：0.0 是合法值，會被當成缺值跳去下一個 alias；
    而 NaN 跟任何門檻比較都是 False——`nan < 0.9` 為 False 等於靜默通過。
    """
    for key in (spec.name, *spec.aliases):
        value = metrics.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if math.isnan(value):
            continue
        return float(value)
    return None


def _check_thresholds(metrics: dict[str, Any]) -> list[str]:
    """逐項比對門檻，回傳失敗訊息；空 list 代表全部通過。缺值視為失敗。"""
    failures: list[str] = []
    for spec in METRIC_SPECS:
        threshold = THRESHOLDS[spec.threshold_key]
        value = _metric_value(metrics, spec)
        if value is None:
            failures.append(
                f"{spec.name} 缺值——沒有 group={spec.group!r} 寫入的有效數值"
                f"（寫入者：{GROUP_WRITERS[spec.group]}）；缺值不視為通過"
            )
        elif value < threshold:
            failures.append(
                f"{spec.name}={value:.{spec.precision}f} < threshold={threshold:.{spec.precision}f}"
            )
    return failures


def _load_from_local() -> tuple[dict[str, Any], list[str]]:
    """讀 output/evals/eval_results_*.json 中最新的一份（依 mtime）。回傳（指標, 來源問題）。"""
    result_files = sorted(
        LOCAL_EVALS_DIR.glob("eval_results_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not result_files:
        return {}, [f"找不到本機 eval 結果：{LOCAL_EVALS_DIR}/eval_results_*.json"]

    latest = result_files[0]
    logger.info("Loading eval results from %s", latest)
    with latest.open(encoding="utf-8") as f:
        return json.load(f), []


def _fetch_latest_run(supabase_url: str, anon_key: str, group: str) -> dict[str, Any] | None:
    """取某個 group 最新的一筆 eval_run；該 group 沒有任何紀錄時回 None。"""
    try:
        resp = requests.get(
            f"{supabase_url}/rest/v1/eval_runs",
            params={
                "select": "metrics,qa_count,group_name,run_at",
                "group_name": f"eq.{group}",
                "order": "run_at.desc",
                "limit": "1",
            },
            headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
            timeout=15,
        )
    except requests.RequestException as exc:
        raise EvalRunFetchError(f"連線失敗：{exc}") from exc
    if resp.status_code != 200:
        raise EvalRunFetchError(f"HTTP {resp.status_code}：{resp.text[:200]}")
    rows = resp.json()
    return rows[0] if rows else None


def _parse_run_at(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _row_metrics(row: dict[str, Any]) -> dict[str, Any]:
    """一筆 eval_run 的指標：metrics JSONB，加上 qa_count 欄位（data-quality 寫在欄位上）。"""
    values = dict(row.get("metrics") or {})
    if row.get("qa_count") is not None:
        values["qa_count"] = row["qa_count"]
    return values


def _group_problem(
    group: str, row: dict[str, Any] | None, now: datetime, max_age: timedelta
) -> str | None:
    """這個 group 的最新一筆能不能用；不能用時回傳原因。"""
    if row is None:
        return f"eval_runs 沒有 group={group!r} 的紀錄（寫入者：{GROUP_WRITERS[group]}）"
    try:
        run_at = _parse_run_at(str(row.get("run_at") or ""))
    except ValueError:
        return f"group={group!r} 最新一筆的 run_at 無法解析：{row.get('run_at')!r}"
    age = now - run_at
    if age > max_age:
        return (
            f"group={group!r} 最新一筆是 {row['run_at']}（{age.total_seconds() / 3600:.1f}h 前），"
            f"超過 {max_age.total_seconds() / 3600:g}h——不是本次 eval 寫入的指標，"
            f"先確認 {GROUP_WRITERS[group]} 有沒有寫入成功"
        )
    return None


def _load_from_supabase(
    max_age_hours: float, now: datetime | None = None
) -> tuple[dict[str, Any], list[str]]:
    """每個 group 各取最新一筆，只收該 group 負責的指標。回傳（指標, 來源問題）。"""
    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not supabase_url or not anon_key:
        return {}, ["缺 SUPABASE_URL 或 SUPABASE_ANON_KEY，無法讀取 eval_runs"]

    now = now or datetime.now(timezone.utc)
    max_age = timedelta(hours=max_age_hours)
    metrics: dict[str, Any] = {}
    problems: list[str] = []
    for group in dict.fromkeys(spec.group for spec in METRIC_SPECS):
        try:
            row = _fetch_latest_run(supabase_url, anon_key, group)
        except EvalRunFetchError as exc:
            problems.append(f"讀取 group={group!r} 失敗：{exc}")
            continue
        problem = _group_problem(group, row, now, max_age)
        if problem:
            problems.append(problem)
            continue
        logger.info("group=%r 最新一筆 run_at=%s", group, row["run_at"])
        values = _row_metrics(row)
        for spec in METRIC_SPECS:
            value = _metric_value(values, spec) if spec.group == group else None
            if value is not None:
                metrics[spec.name] = value
    return metrics, problems


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quality gate for ETL pipeline")
    parser.add_argument(
        "--source",
        choices=["local", "supabase"],
        default="local",
        help="Where to read eval metrics from",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=MAX_EVAL_RUN_AGE_HOURS,
        help=f"Supabase 模式下 eval_run 最久可接受幾小時前寫入（預設 {MAX_EVAL_RUN_AGE_HOURS:g}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results but do not exit(1) on failure",
    )
    args = parser.parse_args(argv)
    if args.max_age_hours <= 0:
        parser.error("--max-age-hours 必須大於 0")

    logger.info("Quality gate — thresholds: %s", THRESHOLDS)

    if args.source == "supabase":
        metrics, problems = _load_from_supabase(args.max_age_hours)
    else:
        metrics, problems = _load_from_local()

    logger.info("Metrics found: %s", {k: v for k, v in metrics.items() if not isinstance(v, dict)})

    failures = [*problems, *_check_thresholds(metrics)]

    if not failures:
        logger.info("Quality gate PASSED — all thresholds met")
        return

    for failure in failures:
        logger.error("QUALITY GATE FAILED: %s", failure)

    if args.dry_run:
        logger.warning("Dry-run mode: not exiting with error")
        return

    sys.exit(1)


if __name__ == "__main__":
    main()
