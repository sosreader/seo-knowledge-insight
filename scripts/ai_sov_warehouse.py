"""
ai_sov_warehouse.py — ai_sov_response / ingestion_run 的 Supabase 存取層（S6.2）

被 scripts/ingest_ai_sov.py 使用。結構刻意比照 crawl_warehouse.py，
連踩過的坑都是同一批（見下方設計決定），不重新發明一套。


═══ 設計決定 ═══

【1. 週桶標籤與執行時刻是兩個欄位】
week_start 永遠是 UTC 的 ISO 週一，run_at 是實際跑的時刻。
理由完整寫在 migrations/024_ai_sov.sql 的頂端註解：資料品質 gate 的空段檢查
把週頻管線對齊到週一 00:00 UTC 做**集合比對**，時間戳若用 run_at 就永遠對不上、
每一週都會被判成空段。week_start_for() 是唯一的對齊函式，寫入端與測試都用它。

【2. ingested_at 必須放進 payload】
沿用 crawl_warehouse.py 設計決定 1：收尾要能掃掉「這次沒被重寫到」的過期列
（panel 移除一條 prompt 時，那條的舊列會殘留在該週、繼續被聚合視圖算進分母，
而且沒有任何訊號）。PostgREST 的 `resolution=merge-duplicates` 只 SET payload
裡出現的欄位，有 DEFAULT now() 但不在 payload 的欄位在衝突時會沿用第一次的值。
因此本模組的 ingested_at 語意是「最後更新時間」而非「首次匯入時間」。

【3. 掃過期列只在「整個 panel 都成功」時才做】
sweep_stale 會刪掉該週 ingested_at 比本次 run 早的列。若這次 run 只跑完一半
（provider 中途失敗），剩下那半的舊列會被誤刪，把一個「部分失敗」變成
「資料被刪掉」。呼叫端（ingest_ai_sov.py）因此只在零失敗時才呼叫它。

【4. 讀回一律 Range 分頁】
PostgREST 的 db-max-rows 預設 1000 會**靜默覆蓋** query-string 的 `limit`，
HTTP 仍回 200（KB postgrest-querystring-limit-silently-capped-by-db-max-rows）。
本模組目前的讀取量遠小於 1000（一週 108 列），但分頁寫在存取層裡，
之後 panel 變大或改成多 provider 時不必回頭想起這件事。
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)

TABLE_SOV = "ai_sov_response"
TABLE_RUN = "ingestion_run"
CONFLICT_KEY = "week_start,provider,model,prompt_id,repeat_idx"
CONFLICT_FIELDS = tuple(CONFLICT_KEY.split(","))
UPSERT_BATCH_SIZE = 500
READ_PAGE_SIZE = 1000  # PostgREST 的 db-max-rows 預設就是 1000
HTTP_TIMEOUT_SECONDS = 90
USER_AGENT = "seo-knowledge-insight-ai-sov-ingest/1.0"


def week_start_for(moment: datetime) -> date:
    """把任一時刻對齊到它所屬那一週的 UTC 週一（ISO 週）。"""
    utc_day = moment.astimezone(timezone.utc).date()
    return utc_day - timedelta(days=utc_day.weekday())


def iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def supabase_config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY")
    return url, key


def _request(method: str, path: str, *, body: Any = None,
             extra_headers: Mapping[str, str] | None = None) -> tuple[int, str, dict]:
    url, key = supabase_config()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    headers.update(extra_headers or {})
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.status, response.read().decode(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace"), dict(exc.headers or {})


def dedupe_rows(rows: Sequence[dict]) -> list[dict]:
    """以 CONFLICT_KEY 去重，保留最後出現者。

    同一批次裡有重複 key 時 PostgreSQL 回
    `ON CONFLICT DO UPDATE command cannot affect row a second time`，
    而且**死的是整批**不是那一列（015 的冪等契約第 3 點）。
    上游理論上不會產生重複鍵（panel id 已驗唯一、repeat_idx 是迴圈索引），
    但去重的成本遠低於整批失敗。
    """
    unique: dict[tuple, dict] = {}
    for row in rows:
        unique[tuple(row[field] for field in CONFLICT_FIELDS)] = row
    return list(unique.values())


def select_all(path: str) -> list[dict]:
    """帶 Range 分頁的讀取（見設計決定 4）。"""
    collected: list[dict] = []
    offset = 0
    while True:
        status, body, _ = _request(
            "GET", path,
            extra_headers={"Range-Unit": "items", "Range": f"{offset}-{offset + READ_PAGE_SIZE - 1}"},
        )
        if status not in (200, 206):
            raise RuntimeError(f"讀取 {path} 失敗：{status} {body[:200]}")
        page = json.loads(body)
        collected.extend(page)
        if len(page) < READ_PAGE_SIZE:
            return collected
        offset += READ_PAGE_SIZE


def start_run(window_start: datetime, window_end: datetime) -> str | None:
    status, body, _ = _request(
        "POST", f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": TABLE_SOV,
            "window_start": iso_z(window_start),
            "window_end": iso_z(window_end),
            "row_count": 0,
            "status": "running",
        }],
        extra_headers={"Prefer": "return=representation"},
    )
    if status not in (200, 201):
        logger.error("建立 ingestion_run 失敗：%s %s", status, body[:300])
        return None
    return json.loads(body)[0]["id"]


def finish_run(run_id: str | None, run_status: str, row_count: int) -> None:
    if not run_id:
        return
    status, body, _ = _request(
        "PATCH", f"/rest/v1/{TABLE_RUN}?id=eq.{urllib.parse.quote(run_id)}",
        body={
            "status": run_status,
            "row_count": row_count,
            "finished_at": iso_z(datetime.now(timezone.utc)),
        },
        extra_headers={"Prefer": "return=minimal"},
    )
    if status not in (200, 204):
        logger.error("收尾 ingestion_run 失敗：%s %s", status, body[:300])


def upsert_rows(rows: Sequence[dict], ingested_at: datetime) -> tuple[int, int]:
    """冪等 upsert。ingested_at 明確進 payload，供 sweep_stale 判斷哪些列是舊的。"""
    stamped = dedupe_rows([dict(row, ingested_at=iso_z(ingested_at)) for row in rows])
    succeeded = failed = 0
    for offset in range(0, len(stamped), UPSERT_BATCH_SIZE):
        batch = stamped[offset : offset + UPSERT_BATCH_SIZE]
        status, body, _ = _request(
            "POST", f"/rest/v1/{TABLE_SOV}?on_conflict={urllib.parse.quote(CONFLICT_KEY)}",
            body=list(batch),
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if status in (200, 201, 204):
            succeeded += len(batch)
        else:
            failed += len(batch)
            logger.error("upsert 失敗：%s %s", status, body[:400])
    return succeeded, failed


def sweep_stale(bucket_week: date, ingested_at: datetime) -> int:
    """刪掉同一週底下這次沒有重寫到的列（見設計決定 1、3）。"""
    query = (
        f"/rest/v1/{TABLE_SOV}"
        f"?week_start=eq.{bucket_week.isoformat()}"
        f"&ingested_at=lt.{urllib.parse.quote(iso_z(ingested_at))}"
    )
    status, body, _ = _request("DELETE", query, extra_headers={"Prefer": "return=representation"})
    if status not in (200, 204):
        logger.error("清除過期列失敗：%s %s", status, body[:300])
        return 0
    removed = len(json.loads(body)) if body.strip() else 0
    if removed:
        logger.info("  掃掉 %d 列過期資料（%s 這一週的 panel 變小了）", removed, bucket_week.isoformat())
    return removed


def latest_week_start() -> date | None:
    """ai_sov_response 最新一筆資料的週桶（新鮮度告警的觀測點）。"""
    status, body, _ = _request(
        "GET", f"/rest/v1/{TABLE_SOV}?select=week_start&order=week_start.desc&limit=1"
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_SOV} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    return date.fromisoformat(payload[0]["week_start"]) if payload else None
