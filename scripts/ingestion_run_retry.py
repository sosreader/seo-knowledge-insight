"""
ingestion_run_retry.py — finish_run() 收尾與冪等 upsert 共用的重試／失敗處理邏輯

═══ 背景 ═══

6 支 ingest 腳本（crawl_warehouse / ai_sov_warehouse / ingest_cwv_hourly /
ingest_cwv_crux_history / ingest_gsc_search_analytics / ingest_gsc_url_inspection）
各自複製貼上一份 finish_run()：收尾 PATCH 撞到 Supabase/PostgREST 暫時性 5xx
（504 Gateway Timeout 等）時只 log、不重試、不 raise，導致該 run 永久停在
status='running'，進而卡住全域 stale-running gate，讓所有 ingestion workflow
顯示 failure。詳見 KB
`session-2026-09-15-seo-insight-ci-stale-running-and-runner.md`
（run 34735571837 crawl_daily 04d1bc93、run 34809429526 cwv_hourly e3abc2b3，
起因為 Supabase 2026-09-11T17:00Z～09-14T17:45Z「Latency issues resulting in
504 errors」事故）。

═══ 用法 ═══

- **收尾 PATCH（by id，絕對賦值，天生冪等）**：呼叫端把底層 `_request`／
  `_supabase_request` 呼叫包成 0-參數 callable 傳給 `finish_run_or_raise()`。
  重試用盡（或遇到不可重試的狀態碼）仍失敗時會 raise
  `IngestionRunFinishError`——呼叫端不需要、也不應該 catch 它：讓例外往外
  穿透即可讓腳本以非 0 結束，這是「孤兒 run 要讓當次 CI 紅燈」的唯一目的。
- **upsert（POST + on_conflict + `Prefer: resolution=merge-duplicates`，
  冪等——同一批 key 重送等於覆蓋成同樣的值）**：呼叫端直接用
  `request_with_retry()` 包住單一批次的 POST，回傳值沿用原本的
  status-code 判斷邏輯（succeeded/failed 計數）。重試用盡後維持「這批算失敗」
  的既有語意，不額外 raise——部分批次失敗本來就由 run_status='partial'
  承接，不是「永久卡 running」等級的問題。

只有「重試策略」與「收尾重試用盡後的處理」是共用邏輯；各腳本的
`_request`/`_supabase_request`（URL 組裝、header、table 名稱）刻意不強行
合併——回傳型別本來就不同（3-tuple vs 2-tuple），且不是本次要修的問題。
"""
from __future__ import annotations

import logging
import time
import urllib.error
from typing import Callable

logger = logging.getLogger(__name__)

# 對齊 KB 診斷「修正方案 B-1」：3 次重試（共 4 次嘗試）、指數退避 1s/2s/4s。
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)
# 只對暫時性 gateway 錯誤重試；4xx（如 400/401/409）是客戶端錯誤，重試沒有意義。
RETRYABLE_HTTP_STATUS = frozenset({502, 503, 504})
# status=0 是本模組內部用來代表「連線層例外」（DNS／逾時／連線被拒）的哨兵值，
# 不是真正的 HTTP 狀態碼。
_CONNECTION_ERROR_STATUS = 0
FINISH_SUCCESS_STATUS = frozenset({200, 204})


class IngestionRunFinishError(RuntimeError):
    """finish_run() 收尾 PATCH 重試用盡（或遇到不可重試的錯誤）仍失敗。

    此例外故意不在呼叫端被吞掉：run_id 永久卡在 status='running'，需要靠
    `python scripts/data_quality_gate.py --reap-stale-running --execute`
    （或 Data Quality Watchdog 排程裡的同一步驟）收尾。
    """


def request_with_retry(
    request_fn: Callable[[], tuple],
    *, description: str, sleep: Callable[[float], None] | None = None,
) -> tuple:
    """對冪等 HTTP 呼叫加有上限的指數退避重試。

    request_fn 是 0-參數 callable，回傳 (status, body, ...)（原樣轉發，不強制
    tuple 長度，相容 `_request` 的 3-tuple 與 `_supabase_request` 的 2-tuple）。
    只對 RETRYABLE_HTTP_STATUS（502/503/504）與連線層例外
    （urllib.error.URLError／逾時／連線錯誤）重試；其餘狀態碼（包含 4xx 與
    非暫時性 5xx）第一次失敗就回傳，不重試。

    最多嘗試 1 + MAX_RETRY_ATTEMPTS 次，重試前依序 sleep
    RETRY_BACKOFF_SECONDS[i] 秒。回傳最後一次嘗試的結果（無論成功或失敗）。

    sleep 預設 None 時才在函式內解析成 `time.sleep`（而非寫成預設參數值）：
    預設參數在 def 當下就會綁死函式物件本身，之後對 `ingestion_run_retry.time.sleep`
    的 monkeypatch（測試常用手法）不會生效，會變成真的在睡。
    """
    sleep = sleep or time.sleep
    attempt = 0  # 已完成的嘗試次數
    while True:
        try:
            result: tuple = request_fn()
            status = result[0]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            result = (_CONNECTION_ERROR_STATUS, str(exc))
            status = _CONNECTION_ERROR_STATUS
        attempt += 1
        retryable = status in RETRYABLE_HTTP_STATUS or status == _CONNECTION_ERROR_STATUS
        if not retryable:
            return result
        if attempt > MAX_RETRY_ATTEMPTS:
            logger.error("%s：重試 %d 次後仍失敗，最終 status=%s", description, MAX_RETRY_ATTEMPTS, status)
            return result
        delay = RETRY_BACKOFF_SECONDS[min(attempt - 1, len(RETRY_BACKOFF_SECONDS) - 1)]
        logger.warning("%s：第 %d 次嘗試失敗（status=%s），%.0fs 後重試",
                        description, attempt, status, delay)
        sleep(delay)


def finish_run_or_raise(
    request_fn: Callable[[], tuple],
    *, run_id: str, description: str = "收尾 ingestion_run",
) -> None:
    """呼叫收尾 PATCH（帶重試），最終仍非 200/204 時 raise `IngestionRunFinishError`。

    呼叫端（各腳本的 finish_run()）不需要 catch：目前 6 個呼叫點都沒有外層
    `except Exception` 會吞掉它，例外會直接讓 `python scripts/ingest_*.py`
    以非 0 結束（見 KB session 檔對各 run_ingestion() 呼叫點的逐一核對）。
    """
    result = request_with_retry(request_fn, description=description)
    status, body = result[0], result[1]
    if status in FINISH_SUCCESS_STATUS:
        return
    logger.error(
        "%s 失敗：run_id=%s status=%s %s —— 此 run 永久卡在 running，"
        "需手動或排程跑 `python scripts/data_quality_gate.py "
        "--reap-stale-running --execute` 收尾",
        description, run_id, status, str(body)[:300],
    )
    raise IngestionRunFinishError(
        f"{description} 失敗，孤兒 run_id={run_id}（status={status}）"
    )
