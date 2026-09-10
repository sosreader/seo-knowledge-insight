"""
_eval_data_quality.py — Layer 1 Data Quality Evaluators（v2.13+）

直接檢查 qa_final.json 或 Supabase qa_items 的整體健康度。
推送至 Laminar Dashboard 的 "data-quality" group。
選擇性儲存至 Supabase eval_runs 表（需設定 SUPABASE_URL/SUPABASE_SERVICE_KEY——
eval_runs 只開放 SELECT 給 anon/authenticated，INSERT 必須用 service key，
見 supabase/migrations/002_eval_runs.sql 與 _upsert_eval_run() 的註解）。

指標（無 API 成本）：
  qa_count_in_range   — QA 總數在 [QA_COUNT_MIN, QA_COUNT_MAX] 之間（1.0 = 合格，0.0 = 異常）
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
import time
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
#
# QA_COUNT_MIN／MAX 是**異常偵測區間**，不是品質目標：低於下界代表萃取或遷移
# 大規模掉資料，高於上界代表去重失效或重複灌入。
#
# 2026-09-10 重設（原值 100–2000）：舊值是資料量還很小時代留下的，沒有隨資料
# 成長更新。實測正式庫已有 32,439 筆（ETL run 34106023623 的 Eval + Quality Gate
# log：「Loaded 32439 QA items from Supabase」），這條指標因此**恆為 0.0**，
# 等於一個永遠在 FAIL 的門檻。新值以實測規模為中心、上下各留一個數量級：
#   下界 3,000   ≈ 現況的 1/10
#   上界 300,000 ≈ 現況的 10 倍
# 這是「數量級」門檻不是精準門檻——資料再成長一個數量級時要重設一次，
# 但不該每次資料變動就微調，否則會退化成永遠貼著現況的指標而失去告警能力。
QA_COUNT_MIN = 3_000
QA_COUNT_MAX = 300_000
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


class EvalRunPersistError(RuntimeError):
    """寫入 eval_runs 失敗——呼叫端必須讓這一步顯示失敗，不能吞掉。

    2026-09-10 之前這裡永遠只印 warning、exit code 不受影響，代表 eval 歷史
    紀錄實際上從未寫入成功卻沒有任何人發現（用 anon key 寫一張只開放 anon
    SELECT 的表，被 RLS 擋下）。修法是把「寫入失敗」變成可觀察的失敗，但
    區分成因：見 _upsert_eval_run 的重試邏輯。
    """


# eval_runs 只有 SELECT 開放給所有角色（見 002_eval_runs.sql 的
# eval_runs_read_all policy），沒有 INSERT policy——RLS 預設 deny，anon
# 寫入一律 401 "new row violates row-level security policy"。要繞過必須用
# service_role key（Postgres/PostgREST 對 service_role 的既定行為是略過
# RLS，不是本專案自訂），這也是 002 遷移檔案註解寫的「write via service
# key」，跟本 repo 其他所有 Supabase 寫入路徑（migrate_to_supabase.py、
# push_qa_metadata_to_supabase.py、update_freshness.py 等）一致採用的模式。
_WRITE_MAX_ATTEMPTS = 3
_WRITE_RETRY_BACKOFF_SECONDS = 1.0  # 線性 backoff：第 n 次重試前等待 n 秒
_WRITE_RETRYABLE_STATUS = {500, 502, 503, 504}  # 只有這幾類視為「可能是暫時性」，值得重試


def _sleep_before_retry(attempt: int, reason: str) -> None:
    delay = _WRITE_RETRY_BACKOFF_SECONDS * attempt
    logger.warning(
        "eval_runs 寫入第 %d/%d 次嘗試失敗（視為暫時性，%.0fs 後重試）：%s",
        attempt, _WRITE_MAX_ATTEMPTS, delay, reason,
    )
    time.sleep(delay)


def _post_eval_run(url: str, key: str, payload: dict) -> None:
    """送出寫入請求，內含重試。每一條路徑最終只會 return（成功）或
    raise EvalRunPersistError（失敗），不會靜默吞掉例外。

    區分兩類失敗：
      - 連線層例外（requests.RequestException）與 5xx：可能是 Supabase
        暫時性問題，重試 _WRITE_MAX_ATTEMPTS 次。
      - 其他 4xx（401/403 RLS 或 GRANT 問題、400/404 schema 不符等）：
        重試沒有意義（同樣的請求同樣的權限，重送也是同樣的錯），立刻失敗。
    """
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    for attempt in range(1, _WRITE_MAX_ATTEMPTS + 1):
        is_last_attempt = attempt == _WRITE_MAX_ATTEMPTS
        try:
            resp = requests.post(
                f"{url}/rest/v1/eval_runs", headers=headers, json=payload, timeout=10,
            )
        except requests.RequestException as exc:
            if is_last_attempt:
                raise EvalRunPersistError(
                    f"eval_runs 寫入連線層失敗（已重試 {_WRITE_MAX_ATTEMPTS} 次）：{exc}"
                ) from exc
            _sleep_before_retry(attempt, f"連線層錯誤：{exc}")
            continue

        if resp.status_code in (200, 201):
            logger.info("Saved eval_run to Supabase")
            return

        detail = f"HTTP {resp.status_code}：{resp.text[:200]}"
        if resp.status_code not in _WRITE_RETRYABLE_STATUS:
            raise EvalRunPersistError(f"eval_runs 寫入失敗，{detail}")
        if is_last_attempt:
            raise EvalRunPersistError(
                f"eval_runs 寫入失敗（已重試 {_WRITE_MAX_ATTEMPTS} 次），{detail}"
            )
        _sleep_before_retry(attempt, detail)


def _upsert_eval_run(metrics: dict, group: str, passed: bool) -> None:
    """Save eval results to Supabase eval_runs table.

    完全沒設定 SUPABASE_URL/SUPABASE_SERVICE_KEY 時視為刻意不接 Supabase
    （例如本機只想看 --source local 的指標），略過且不算失敗。只設定其中
    一個則是設定不完整（多半是 CI workflow 漏掛某個 secret 到這個 step），
    視為失敗——這正是 002_eval_runs.sql 早就規劃好、但先前用錯 key 而從未
    真的走過的寫入路徑。
    """
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url and not key:
        logger.info(
            "SUPABASE_URL/SUPABASE_SERVICE_KEY 皆未設定，略過 eval_runs 寫入（視為刻意不接 Supabase）"
        )
        return
    if not url or not key:
        raise EvalRunPersistError(
            "SUPABASE_URL 與 SUPABASE_SERVICE_KEY 只設定了一個——環境設定不完整"
        )

    payload = {
        "trigger": "manual",
        "group_name": group,
        "metrics": {k: v for k, v in metrics.items() if isinstance(v, (int, float, str))},
        "passed": passed,
        "qa_count": metrics.get("total"),
    }
    _post_eval_run(url, key, payload)


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

    # 儲存至 Supabase eval_runs——寫入失敗不再靜默吞掉：先記錄下來讓後面的
    # Laminar 推送（獨立關注點）照常跑，最後才讓整個 process 以非 0 結束，
    # 使 CI step 顯示失敗（見 EvalRunPersistError 與 _upsert_eval_run 的註解）。
    eval_run_persisted = True
    try:
        _upsert_eval_run(metrics, args.group, _passed)
    except EvalRunPersistError as exc:
        eval_run_persisted = False
        logger.error("eval_runs 寫入失敗，此次執行最終會以非 0 結束：%s", exc)

    if args.dry_run:
        logger.info("--dry-run 模式：不推送至 Laminar")
        if not eval_run_persisted:
            sys.exit(1)
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

    if not eval_run_persisted:
        sys.exit(1)


if __name__ == "__main__":
    main()
