"""
crawl_warehouse.py — crawl_daily / ingestion_run 的 Supabase 存取層

被 scripts/ingest_crawl_hourly.py 使用。


═══ 設計決定 ═══

【1. 收尾要掃掉過期列，不能只 upsert】
015 的冪等契約第 1 點：upsert 只新增與覆蓋、不刪除。重跑同一小時時若新結果的桶
比舊結果少（UA 分群規則調整、path allowlist 增刪、某個 crawler 那小時沒來），
舊列會殘留並繼續被 SUM 計入，變成**沒有任何訊號的靜默高估**。

本模組採該註解的策略 (b)：upsert 後刪掉同一 (date, hour) 底下
`ingested_at < 本次 run 起始時刻` 的列。
因此 **ingested_at 必須放進 payload**——PostgREST 的 `resolution=merge-duplicates`
只會 SET payload 裡出現的欄位，有 DEFAULT now() 但不在 payload 的欄位在衝突時
會沿用第一次寫入的值。
它的語意也因此是「最後更新時間」而非「首次匯入時間」，與 cwv_hourly 相反：
那張表的桶集合不會縮小，所以那支腳本刻意不帶 ingested_at。

【2. 讀回一律 Range 分頁 + count=exact】
PostgREST 的 `db-max-rows` 預設 1000 會**靜默覆蓋** query-string 的 `limit`，
HTTP 仍然回 200。不分頁就會以為「表裡只有 1000 列」，而且看不出被截斷。
count 走 `Prefer: count=exact` 讀 Content-Range 的分母，與分頁結果互為驗證。

【3. 同一批次內不可有重複 key】
015 的冪等契約第 3 點：批次裡有重複 key 時 PostgreSQL 回
`ON CONFLICT DO UPDATE command cannot affect row a second time`，
而且**死的是整批**不是那一列。本模組在送出前以 CONFLICT_KEY 去重（dedupe_rows），
上游的聚合理論上不會產生重複鍵，但那是「理論上」——去重的成本遠低於整批失敗。
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

logger = logging.getLogger(__name__)

TABLE_CRAWL = "crawl_daily"
TABLE_RUN = "ingestion_run"
# 冪等鍵以 ua_name（原始事實）而非 ua_group（衍生標籤）為維度，見 migrations/017。
# ua_group 仍在 payload 裡，衝突時會被覆蓋 —— 那正是「重新分類 = 一次 upsert」的機制。
CONFLICT_KEY = "date,hour,ua_name,status_code,path_prefix"
CONFLICT_FIELDS = tuple(CONFLICT_KEY.split(","))
UPSERT_BATCH_SIZE = 500
READ_PAGE_SIZE = 1000  # PostgREST 的 db-max-rows 預設就是 1000
HTTP_TIMEOUT_SECONDS = 90
USER_AGENT = "seo-knowledge-insight-crawl-ingest/1.0"


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
    """以 CONFLICT_KEY 去重，保留最後出現者（見設計決定 3）。"""
    unique: dict[tuple, dict] = {}
    for row in rows:
        unique[tuple(row[field] for field in CONFLICT_FIELDS)] = row
    return list(unique.values())


def select_all(path: str) -> list[dict]:
    """帶 Range 分頁的讀取（見設計決定 2）。"""
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


def count_exact(path: str) -> int:
    """`Prefer: count=exact` 取精確列數（Content-Range 的分母）。"""
    status, body, headers = _request(
        "GET", path, extra_headers={"Prefer": "count=exact", "Range": "0-0"}
    )
    if status not in (200, 206):
        raise RuntimeError(f"count 失敗：{status} {body[:200]}")
    content_range = headers.get("Content-Range") or headers.get("content-range") or ""
    _, _, total = content_range.partition("/")
    return int(total) if total.isdigit() else 0


def start_run(window_start: datetime, window_end: datetime) -> str | None:
    status, body, _ = _request(
        "POST", f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": TABLE_CRAWL,
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
            "POST", f"/rest/v1/{TABLE_CRAWL}?on_conflict={urllib.parse.quote(CONFLICT_KEY)}",
            body=list(batch),
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if status in (200, 201, 204):
            succeeded += len(batch)
        else:
            failed += len(batch)
            logger.error("upsert 失敗：%s %s", status, body[:400])
    return succeeded, failed


def sweep_stale(bucket_hour: datetime, ingested_at: datetime) -> int:
    """刪掉同一 (date, hour) 底下這次沒有重寫到的列（見設計決定 1）。"""
    query = (
        f"/rest/v1/{TABLE_CRAWL}"
        f"?date=eq.{bucket_hour.date().isoformat()}"
        f"&hour=eq.{bucket_hour.hour}"
        f"&ingested_at=lt.{urllib.parse.quote(iso_z(ingested_at))}"
    )
    status, body, _ = _request("DELETE", query, extra_headers={"Prefer": "return=representation"})
    if status not in (200, 204):
        logger.error("清除過期列失敗：%s %s", status, body[:300])
        return 0
    removed = len(json.loads(body)) if body.strip() else 0
    if removed:
        logger.info("  掃掉 %d 列過期資料（%s 這一小時的桶集合變小了）", removed, iso_z(bucket_hour))
    return removed


def latest_bucket_hour() -> datetime | None:
    """crawl_daily 最新一筆資料的時間桶（新鮮度告警的觀測點）。"""
    status, body, _ = _request(
        "GET", f"/rest/v1/{TABLE_CRAWL}?select=date,hour&order=date.desc,hour.desc&limit=1"
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_CRAWL} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    if not payload:
        return None
    return datetime.fromisoformat(payload[0]["date"]).replace(
        hour=int(payload[0]["hour"]), tzinfo=timezone.utc
    )
