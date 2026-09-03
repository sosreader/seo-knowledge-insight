"""ingest_gsc_search_analytics.py — 把 GSC Search Analytics API 的逐日資料寫進 Supabase gsc_daily_metrics

資料流：Search Analytics API（Google）→ 逐日 × 兩套維度組合 → Supabase PostgREST upsert
CWV 那條線（Loki RUM / CrUX History → cwv_hourly）由 ingest_cwv_hourly.py 與
ingest_cwv_crux_history.py 負責，與本腳本無關。

用法（旗標細節見 --help）：--dry-run（預設）／--execute [--backfill-days N]／
--verify（唯讀檢查）／--check-freshness（新鮮度告警，stale 則 exit 1）

環境變數：GSC_READONLY_KEY（service account 的 JSON **字串**，不是檔案路徑）、
SUPABASE_URL / SUPABASE_SERVICE_KEY


═══ 資料完整性的硬前提 —— 這裡的數字是抽樣，不是全量 ═══

官方明講「only returns top rows, does not guarantee to return all data rows」，且每天
每 property 每 search type 最多 50,000 列。因此 `SUM(clicks) FROM gsc_daily_metrics`
**不等於** GSC UI 上那天的總點擊，落差必然存在且大小不可知。首次 live 執行實測：
query 組每天回 47.8k-48.0k 列，**貼著 50K 天花板**，代表該組確實被 top-N 截斷。
本表能回答的是「這些 page / query 的相對趨勢」，不是「總量」。
（同一句話也寫在 migration 015 的 COMMENT ON TABLE，兩邊要一致。）


═══ 維度組合、哨兵值、surface 規則都在 scripts/gsc_surfaces.py ═══

兩套維度組合（page 組 / query 組）怎麼共用同一個七欄 unique key 空間、三個哨兵值
為什麼選成那樣、判別式為什麼一律以 page 為準、googleNews 與 discover 為什麼只跑
page 組且 position 存 0 —— 全部搬到 `scripts/gsc_surfaces.py` 的 docstring，
因為那些常數與驗證函式都定義在那裡。**不帶判別式直接 SUM 會得到約兩倍的假數字且
不會有任何錯誤訊號**，--verify 因此固定按 surface 分組印出兩邊列數。


═══ 全站總數（gsc_daily_totals）—— 探測查詢的副產品，不是另一次 API 呼叫 ═══

本表是 top-N 抽樣，答不出「那天總共幾次點擊」。而下面那個 `dimensions=["date"]` 的探測
查詢，API 回的每一列本來就帶 clicks/impressions/ctr/position，**那就是與 GSC UI 一致的
全站總數**——把原本丟掉的四個 metric 欄位寫進 gsc_daily_totals 即可，不必多打任何一次 API。
兩張表母體不同（全量 vs 抽樣）不可相加，故不同表；totals 每鍵恰一列，冪等且不需要 reap。


═══ 2-3 天資料延遲怎麼處理 —— 用探測，不用寫死的 lag ═══

官方說延遲「通常 2-3 天」，但那是「通常」。寫死 lag=3 兩邊都會錯：設太短會查到還
沒有資料的日期、回 0 列、被 (e) 的 0-row 規則判成失敗（誤報）；設太長則每天少拿資料。

改用官方 how-to 建議的做法：先用 `dimensions=["date"]` 對最近 `--probe-days` 天打一次
**便宜的探測查詢**（回傳列數 = 天數），拿到「Google 目前實際有資料的日期集合」，再從中取
最近 backfill_days 天去抓。於是延遲飄到 4-5 天也不會誤報，而探測回 0 列 = 真的壞了
（權限、property、配額），是硬失敗。探測窗因此也是 backfill 的硬上限，見 resolve_backfill_days。

每次回補最近 N 天（預設 7）而非只抓昨天，是為了吃下 GSC 的**回溯修訂**——同一個日期的數字
在後續幾天內會被 Google 修正，只抓一次會定格在最早的版本。


═══ 冪等：upsert 不夠，要補收尾（reaping）═══

KB learned skill `upsert-idempotency-only-holds-while-the-bucket-set-does-not-shrink`：
upsert 只新增與覆蓋、**不刪除**。GSC 是 top-N 抽樣，門檻附近的 page/query 會在相鄰
兩次抓取之間進出——這次沒回來的列會留在表裡繼續被 SUM 計入，**靜默高估**。

採用該 skill 的策略 (b)：payload 顯式帶 `ingested_at`（不能靠 DEFAULT now()——
PostgREST 的 merge-duplicates 只更新 payload 裡有的欄位，衝突時會沿用首次寫入的值），
寫完後對本次涵蓋的 (date, combo) 切片刪掉 `ingested_at < run_started_at` 的孤兒列。
安全閥：**只有該切片 upsert 零失敗才 reap**，部分失敗還去刪會把上一輪的好資料刪掉。

另：同一批次內不可有重複 key，否則 PostgreSQL 回
`ON CONFLICT DO UPDATE command cannot affect row a second time`，且**死的是整批**。
分頁時相鄰頁可能回重疊列，dedupe_by_key() 因此必跑。


═══ 0 rows 一律是失敗 ═══
背景作業最危險的失敗是「什麼都沒發生但回報成功」。本腳本三道，都 exit 1：探測回 0 個
日期、任一 (date, combo) 切片回 0 列、總寫入列數為 0。vocus.cc 每天都有搜尋流量。

**但「個別列被丟棄」不算在內**——那是 warning 不是 error，理由見 collect_day_combo()
的 docstring（首次 live 執行校準：533,314 列裡 2 列 query 超長，天天紅燈只會讓人
學會忽略 status）。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
# 本檔以 `python scripts/x.py` 直接執行時 sys.path[0] 是 scripts/ 而非 repo root，下面的
# `from scripts.gsc_surfaces import ...` 會噴 ModuleNotFoundError；pytest 不會踩到（測試檔自己有這行）。
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.gsc_surfaces import (  # noqa: E402
    ALLOWED_SEARCH_TYPES,
    COMBO_DIMENSIONS,
    COMBO_PAGE,
    COMBO_QUERY,
    CONFLICT_KEY,
    COUNTRY_NOT_REQUESTED,  # noqa: F401 —— 對外仍從本模組取用（哨兵值的單一出處）
    DEFAULT_BACKFILL_DAYS,
    DEFAULT_PROBE_DAYS,
    DEFAULT_SEARCH_TYPE,
    MAX_BACKFILL_DAYS,
    MAX_PROBE_DAYS,
    MIN_BACKFILL_DAYS,  # noqa: F401 —— 對外仍從本模組取用
    MIN_PROBE_DAYS,
    PAGE_NOT_REQUESTED,
    PROPERTY,
    QUERY_NOT_REQUESTED,  # noqa: F401 —— 同上
    SURFACE_COMBOS,
    TABLE_GSC,
    TABLE_TOTALS,
    TOTALS_CONFLICT_KEY,
    _assert_no_country_dimension,
    _validate_metrics,
    build_totals_records,
    combo_filter,
    dedupe_by_key,
    resolve_backfill_days,
    resolve_probe_days,
    resolve_search_type,
    row_to_record,
    totals_record,
)

load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingest_gsc_search_analytics")

# ══════════════════════════════════════════════════════════════════════
# GSC API
# ══════════════════════════════════════════════════════════════════════

GSC_QUERY_URL = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

ROW_LIMIT = 25000       # 單次請求上限（API 規格 1..25,000）
DAILY_ROW_CAP = 50000   # 每天每 property 每 search type 的總天花板，分頁到此為止

HTTP_TIMEOUT_SECONDS = 120
USER_AGENT = "seo-knowledge-insight-gsc-ingest/1.0"

# DEFAULT_BACKFILL_DAYS／MIN_BACKFILL_DAYS／MAX_BACKFILL_DAYS／DEFAULT_PROBE_DAYS／
# MIN_PROBE_DAYS／MAX_PROBE_DAYS 搬進 gsc_surfaces.py 了（review S4.1 #9，
# 跟同樣搬過去的 resolve_probe_days／resolve_backfill_days 放一起），上面 import 區塊取用。
PROBE_ROW_LIMIT_MARGIN = 7  # rowLimit = probe_days + 這個緩衝（探測每天恰一列）；
                            # 這是 API rowLimit 算式的一部分，不是使用者輸入值域，留在本檔。

# ══════════════════════════════════════════════════════════════════════
# Supabase
# ══════════════════════════════════════════════════════════════════════

TABLE_RUN = "ingestion_run"
UPSERT_BATCH_SIZE = 500

# 【門檻公式】KB learned skill
# `freshness-threshold-schedule-period-formula-ignores-source-inherent-lag`：
# 門檻 = 來源固有延遲上限（官方稱 2-3 天，取 4 天 = 96h 留飄移空間）+ 排程週期緩衝
# （每日 24h × 2 = 48h，容忍單次漏跑不容忍連續兩次），**不是**排程週期 × N。
# 用「排程週期 × 3 = 72h」會在資料完全健康時就誤報——max(date) 天生落後現在 2-4 天。
FRESHNESS_MAX_AGE_HOURS = 96 + 48


class GscQueryError(RuntimeError):
    """Search Analytics API 的系統性錯誤（權限／配額／參數），應中止整個 run。"""


# ══════════════════════════════════════════════════════════════════════
# 認證
# ══════════════════════════════════════════════════════════════════════

def _service_account_info() -> dict:
    """從環境變數讀 SA JSON 字串。金鑰只存在 GitHub secret，不落磁碟、不進 log。"""
    raw = os.environ.get("GSC_READONLY_KEY", "").strip()
    if not raw:
        raise RuntimeError("缺少 GSC_READONLY_KEY（service account JSON 字串，非檔案路徑）")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        # 刻意不把 raw 放進訊息——那是金鑰本體。
        raise RuntimeError(f"GSC_READONLY_KEY 不是合法 JSON（長度 {len(raw)}）") from exc
    if info.get("type") != "service_account":
        raise RuntimeError(f"GSC_READONLY_KEY 的 type 不是 service_account：{info.get('type')!r}")
    return info


def gsc_access_token() -> str:
    """換一張 OAuth2 access token。google-auth 負責 RS256 JWT 簽章與 token 交換。"""
    from google.auth.transport.requests import Request as GoogleAuthRequest
    from google.oauth2 import service_account

    credentials = service_account.Credentials.from_service_account_info(
        _service_account_info(), scopes=[GSC_SCOPE]
    )
    credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError("取得 GSC access token 失敗（refresh 後 token 為空）")
    logger.info("已取得 GSC access token（SA=%s）", _service_account_info().get("client_email"))
    return credentials.token


def classify_gsc_error(status: int, body: str) -> GscQueryError:
    """把 HTTP 狀態翻成可判讀的中止原因。全部都是系統性錯誤，沒有「這筆跳過就好」的情況。"""
    if status in (401, 403):
        return GscQueryError(
            f"HTTP {status}：SA 對 {PROPERTY} 沒有存取權，或 Search Console API 未啟用。{body[:200]}"
        )
    if status == 429:
        return GscQueryError(f"HTTP 429：超出 QPS/QPD 配額。{body[:200]}")
    if status == 400:
        return GscQueryError("HTTP 400：請求參數不合法（維度組合或日期範圍）；googleNews 與 discover "
                             f"不支援 query 維度，先檢查 SURFACE_COMBOS。{body[:300]}")
    return GscQueryError(f"HTTP {status}：{body[:300]}")


# ══════════════════════════════════════════════════════════════════════
# 查詢
# ══════════════════════════════════════════════════════════════════════

def _gsc_post(token: str, body: Mapping[str, Any]) -> dict:
    url = GSC_QUERY_URL.format(site=urllib.parse.quote(PROPERTY, safe=""))
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise classify_gsc_error(exc.code, exc.read().decode(errors="replace")) from exc
    except urllib.error.URLError as exc:
        raise GscQueryError(f"連線失敗：{exc.reason}") from exc


def probe_row_limit(probe_days: int) -> int:
    """探測每天恰回一列，rowLimit 只需略大於天數；仍受 API 的 25,000 上限。"""
    return min(probe_days + PROBE_ROW_LIMIT_MARGIN, ROW_LIMIT)


def probe_totals(token: str, search_type: str, today: date, probe_days: int) -> list[dict]:
    """`dimensions=["date"]` 的探測查詢，回傳 API 原始列（每列一天，含四個 metric）。

    這一次呼叫同時服務兩件事：哪些日期已有資料（見 dates_from_totals），以及
    那些日期的**全站總數**（見 build_totals_records）。不要為了 totals 再打一次。
    """
    payload = _gsc_post(token, {
        "startDate": (today - timedelta(days=probe_days)).isoformat(),
        "endDate": today.isoformat(),
        "dimensions": ["date"],
        "type": search_type,
        "rowLimit": probe_row_limit(probe_days),
    })
    rows = payload.get("rows", [])
    logger.info("探測（%s）：最近 %d 天回 %d 列", search_type, probe_days, len(rows))
    return rows


def dates_from_totals(rows: Iterable[Mapping[str, Any]]) -> list[date]:
    """探測列 → 已有資料的日期，由新到舊。"""
    return sorted(
        {date.fromisoformat(row["keys"][0]) for row in rows if row.get("keys")},
        reverse=True,
    )


def probe_available_dates(
    token: str, search_type: str, today: date, probe_days: int = DEFAULT_PROBE_DAYS,
) -> list[date]:
    """只要日期不要 metrics 時用。理由見模組 docstring：資料延遲是浮動的，
    寫死 lag 不是誤報就是漏抓。"""
    return dates_from_totals(probe_totals(token, search_type, today, probe_days))


def paginate_query(token: str, day: date, dimensions: Sequence[str], search_type: str) -> list[dict]:
    """對單一日期分頁抓完該維度組合的所有列。

    startRow 每頁遞增 ROW_LIMIT，直到回傳列數 < ROW_LIMIT 或碰到 DAILY_ROW_CAP。
    """
    collected: list[dict] = []
    start_row = 0
    while start_row < DAILY_ROW_CAP:
        payload = _gsc_post(token, {
            "startDate": day.isoformat(),
            "endDate": day.isoformat(),
            "dimensions": list(dimensions),
            "type": search_type,
            "rowLimit": min(ROW_LIMIT, DAILY_ROW_CAP - start_row),
            "startRow": start_row,
        })
        rows = payload.get("rows", [])
        collected.extend(rows)
        if len(rows) < ROW_LIMIT:
            break
        start_row += len(rows)
    if len(collected) >= DAILY_ROW_CAP:
        logger.warning("%s %s 撞到 %d 列天花板，該日資料被截斷（API 抽樣性質，非 bug）",
                       day.isoformat(), "/".join(dimensions), DAILY_ROW_CAP)
    return collected


# ══════════════════════════════════════════════════════════════════════
# Supabase 存取
# ══════════════════════════════════════════════════════════════════════

def supabase_config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY")
    return url, key


def _supabase_request(
    method: str, path: str, *, body: Any = None, extra_headers: Mapping[str, str] | None = None
) -> tuple[int, str]:
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
            return response.status, response.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")


def start_run(
    window_start: datetime, window_end: datetime, table_name: str = TABLE_GSC,
) -> str | None:
    status, body = _supabase_request(
        "POST",
        f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": table_name,
            "window_start": window_start.isoformat().replace("+00:00", "Z"),
            "window_end": window_end.isoformat().replace("+00:00", "Z"),
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
    status, body = _supabase_request(
        "PATCH",
        f"/rest/v1/{TABLE_RUN}?id=eq.{urllib.parse.quote(run_id)}",
        body={
            "status": run_status,
            "row_count": row_count,
            "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
        extra_headers={"Prefer": "return=minimal"},
    )
    if status not in (200, 204):
        logger.error("收尾 ingestion_run 失敗：%s %s", status, body[:300])


def upsert_rows(
    rows: Sequence[dict], table: str = TABLE_GSC, conflict_key: str = CONFLICT_KEY,
) -> tuple[int, int]:
    """冪等 upsert。回傳 (成功列數, 失敗列數)。"""
    succeeded = failed = 0
    for offset in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[offset : offset + UPSERT_BATCH_SIZE]
        status, body = _supabase_request(
            "POST",
            f"/rest/v1/{table}?on_conflict={urllib.parse.quote(conflict_key)}",
            body=list(batch),
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if status in (200, 201, 204):
            succeeded += len(batch)
        else:
            failed += len(batch)
            logger.error("upsert 失敗：%s %s", status, body[:400])
    return succeeded, failed


def write_totals(
    records: Sequence[dict], window: tuple[datetime, datetime], search_type: str,
) -> tuple[int, int]:
    """把全站總數寫進 gsc_daily_totals，並在 ingestion_run 另記一列。

    每個 (property, search_type, date) 恰一列，upsert 冪等，**不 reap**——
    totals 沒有 top-N 桶集合縮小的問題，這裡沒有孤兒列可收。
    """
    run_id = start_run(*window, table_name=TABLE_TOTALS)
    try:
        succeeded, failed = upsert_rows(records, TABLE_TOTALS, TOTALS_CONFLICT_KEY)
    except urllib.error.URLError:
        # review S4.1 SF-3：upsert_rows 內的 _supabase_request 只擋 HTTPError，
        # 網路層例外（DNS／連線重置／TLS）會穿出來——這裡的 run_id 已經是
        # "running"，不收尾就會永遠卡住，讓上層 stale-run 告警去抓才發現。
        finish_run(run_id, "failed", 0)
        raise
    run_status = "success" if succeeded and not failed else ("partial" if succeeded else "failed")
    finish_run(run_id, run_status, succeeded)
    logger.info("totals（%s）寫入 %d 列成功 / %d 列失敗，run status=%s",
                search_type, succeeded, failed, run_status)
    return succeeded, failed


def reap_orphans(day: date, combo: str, search_type: str, run_started_at: str) -> int:
    """刪掉這個切片裡「本次沒寫到」的舊列，回傳刪除列數。

    GSC 是 top-N 抽樣，桶集合會縮小；upsert 不刪除，殘留列會被 SUM 靜默計入。
    呼叫端必須確認該切片 upsert 零失敗才呼叫（見模組 docstring 的安全閥）。
    """
    path = (
        f"/rest/v1/{TABLE_GSC}?date=eq.{day.isoformat()}"
        f"&property=eq.{urllib.parse.quote(PROPERTY, safe='')}"
        f"&search_type=eq.{search_type}&{combo_filter(combo)}"
        f"&ingested_at=lt.{urllib.parse.quote(run_started_at, safe='')}"
    )
    status, body = _supabase_request("DELETE", path, extra_headers={"Prefer": "return=representation"})
    if status not in (200, 204):
        logger.error("reap 失敗（%s / %s）：%s %s", day.isoformat(), combo, status, body[:300])
        return 0
    removed = len(json.loads(body)) if body.strip().startswith("[") else 0
    if removed:
        logger.warning("reap：%s / %s 刪掉 %d 列本次未回傳的舊列（top-N 桶集合縮小）",
                       day.isoformat(), combo, removed)
    return removed


def count_rows(extra_query: str = "", table: str = TABLE_GSC) -> int:
    """精確列數。用 Prefer: count=exact + Range 讀 Content-Range，
    不用 `limit` —— PostgREST 的 db-max-rows（預設 1000）會靜默覆蓋 limit 且仍回 200。"""
    url, key = supabase_config()
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT,
        "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0",
    }
    request = urllib.request.Request(
        url + f"/rest/v1/{table}?select=date{extra_query}", headers=headers, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            content_range = response.headers.get("Content-Range", "")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"count 查詢失敗：{exc.code} {exc.read().decode(errors='replace')[:200]}"
        ) from exc
    total = content_range.rsplit("/", 1)[-1]
    if not total.isdigit():
        raise RuntimeError(f"count 查詢的 Content-Range 格式異常：{content_range!r}")
    return int(total)


def latest_date() -> date | None:
    status, body = _supabase_request(
        "GET", f"/rest/v1/{TABLE_GSC}?select=date&order=date.desc&limit=1"
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_GSC} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    return date.fromisoformat(payload[0]["date"]) if payload else None


# ══════════════════════════════════════════════════════════════════════
# 執行模式
# ══════════════════════════════════════════════════════════════════════

def collect_day_combo(
    token: str, day: date, combo: str, search_type: str, ingested_at: str,
    errors: list[str], warnings: list[str],
) -> list[dict]:
    """抓一個 (date, combo) 切片並轉成可寫入的列。

    【errors 與 warnings 的分界 —— 首次 live 執行校準出來的】
    首版把「有列被丟棄」也算進 errors，於是 533,314 列裡 2 列 query 超過 512 bytes
    就讓整個 run 變 partial 並 exit 1。那是誤判：超長 query 是這份資料的**永久性質**，
    天天紅燈只會讓人學會忽略 status（同族：恆常誤報磨掉信任）。

      errors（硬失敗，降級 status + exit 1）：0 列。探測已說該日有資料，回 0 只可能是
        權限、配額或查詢壞掉，不是資料的性質。
      warnings（記錄但不改 status）：個別列不合 schema 被丟棄。數量仍逐項印出來，
        異常放大時看得見，只是不再天天染紅。
    """
    raw_rows = paginate_query(token, day, COMBO_DIMENSIONS[combo], search_type)
    rejects: dict[str, int] = {}  # 標籤與 surface 一起印，position 規則是 surface-aware 的
    records = [
        record for record in (
            row_to_record(row, combo=combo, day=day, search_type=search_type,
                          ingested_at=ingested_at, rejects=rejects)
            for row in raw_rows
        ) if record is not None
    ]
    records = dedupe_by_key(records)
    logger.info("  %s / %s（%s）：API %d 列 → 可寫入 %d 列%s",
                day.isoformat(), combo, search_type, len(raw_rows), len(records),
                f"（丟棄 {rejects}）" if rejects else "")
    if rejects:
        warnings.append(f"{day.isoformat()}/{combo}/{search_type} 丟棄不合法列：{rejects}")
    if not records:
        # (e)：0 rows 不得靜默通過。vocus.cc 每天都有搜尋流量。
        errors.append(f"{day.isoformat()}/{combo} 回傳 0 列（探測說該日有資料，這是異常）")
        logger.error("  %s / %s 回傳 0 列 —— 視為失敗", day.isoformat(), combo)
    return records


def _write_slice(
    day: date, combo: str, search_type: str, run_started_at: str, records: Sequence[dict],
) -> tuple[int, int]:
    """寫一個切片並在完全成功時 reap。回傳 (成功列數, 失敗列數)。"""
    succeeded, failed = upsert_rows(records)
    if failed == 0 and succeeded:
        reap_orphans(day, combo, search_type, run_started_at)
    elif failed:
        logger.error("  %s / %s 有 %d 列寫入失敗，跳過 reap（避免刪掉上一輪的好資料）",
                     day.isoformat(), combo, failed)
    return succeeded, failed


def resolve_targets(
    token: str, search_type: str, today: date, backfill_days: int, probe_days: int,
) -> tuple[list[date], list[dict]]:
    """探測一次，同時得到目標日期與全站總數列。

    回傳 (取最近 backfill_days 天的目標日期, 探測回應原始列)。目標日期空清單代表硬失敗。
    探測列涵蓋整個 probe_days 窗（不只 targets），totals 因此能一次呼叫補滿長區間。
    """
    probe_rows = probe_totals(token, search_type, today, probe_days)
    available = dates_from_totals(probe_rows)
    if not available:
        return [], probe_rows
    targets = sorted(available[:backfill_days])
    logger.info("本次目標日期 %d 天：%s .. %s（探測窗 %d 天回 %d 天）",
                len(targets), targets[0].isoformat(), targets[-1].isoformat(),
                probe_days, len(available))
    return targets, probe_rows


def run_window(targets: Sequence[date]) -> tuple[datetime, datetime]:
    """ingestion_run 記錄用的半開區間 [window_start, window_end)。"""
    start = datetime.combine(targets[0], datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(targets[-1], datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1)
    return start, end


def _ingest_totals(
    probe_rows: Sequence[Mapping[str, Any]], *, search_type: str, execute: bool,
    errors: list[str], warnings: list[str],
) -> int:
    """探測回應 → gsc_daily_totals。回傳寫入列數。0 列是硬失敗（探測已說有資料）。"""
    records = build_totals_records(probe_rows, search_type=search_type, warnings=warnings)
    if not records:
        errors.append(f"totals/{search_type} 沒有可寫入的全站總數列"
                      "（探測已回日期，這是異常：API 回應可能不含 metric 欄位）")
        return 0
    if not execute:
        return 0
    days = sorted(date.fromisoformat(record["date"]) for record in records)
    succeeded, failed = write_totals(records, run_window(days), search_type)
    if failed or not succeeded:
        errors.append(f"totals/{search_type} 有 {failed} 列寫入失敗")
    return succeeded


def _finalize_run(
    run_id: str | None, *, execute: bool, errors: list[str], warnings: list[str],
    written: int, failed: int,
) -> int:
    """印出本次的提醒與硬問題、決定 run status、收尾 ingestion_run，回傳 exit code。"""
    for message in warnings:
        logger.warning("  資料品質：%s", message)
    for message in errors:
        logger.error("  問題：%s", message)
    if not execute:
        logger.info("[DRY RUN] 不寫入。加 --execute 才會 upsert。（%d 個硬問題 / %d 個資料品質提醒）",
                    len(errors), len(warnings))
        return 1 if errors else 0
    # warnings 刻意不參與 status —— 理由見 collect_day_combo docstring。
    run_status = "success" if not errors and not failed and written else (
        "failed" if not written else "partial"
    )
    finish_run(run_id, run_status, written)
    logger.info("寫入完成：%d 列成功 / %d 列失敗，run status=%s（%d 個資料品質提醒）",
                written, failed, run_status, len(warnings))
    return 0 if run_status == "success" else 1


def run_ingestion(
    *, execute: bool, backfill_days: int, search_type: str,
    probe_days: int = DEFAULT_PROBE_DAYS,
) -> int:
    _assert_no_country_dimension()
    now = datetime.now(timezone.utc)
    run_started_at = now.isoformat().replace("+00:00", "Z")
    token = gsc_access_token()

    targets, probe_rows = resolve_targets(token, search_type, now.date(), backfill_days, probe_days)
    if not targets:
        logger.error("FAIL: 探測最近 %d 天完全沒有資料 —— 權限、property 或配額有問題，"
                     "不是資料延遲。", probe_days)
        return 1
    run_id = start_run(*run_window(targets)) if execute else None

    errors: list[str] = []
    warnings: list[str] = []
    total_written = total_failed = 0
    try:
        # review S4.1 SF-3：_ingest_totals 原本在 try 之外——它會發真實 HTTP
        # 請求（write_totals → upsert_rows），URLError（DNS／連線重置／TLS）
        # 不是 GscQueryError，會直接穿出 run_ingestion，讓主 run 的 run_id
        # 留在 "running" 收不了尾。挪進 try、except 一併擴大即可堵住。
        _ingest_totals(probe_rows, search_type=search_type, execute=execute,
                       errors=errors, warnings=warnings)
        for day in targets:
            for combo in SURFACE_COMBOS[search_type]:
                records = collect_day_combo(token, day, combo, search_type,
                                            run_started_at, errors, warnings)
                if not execute or not records:
                    continue
                succeeded, failed = _write_slice(day, combo, search_type, run_started_at, records)
                total_written += succeeded
                total_failed += failed
    except (GscQueryError, urllib.error.URLError) as exc:
        logger.error("Search Analytics 查詢失敗（系統性，中止整個 run）：%s", exc)
        finish_run(run_id, "failed", total_written)
        return 1

    return _finalize_run(run_id, execute=execute, errors=errors, warnings=warnings,
                         written=total_written, failed=total_failed)


def _verify_surface(search_type: str) -> bool:
    """印出單一 surface 的各組列數，並斷言它該有的組別都不是 0。

    全表計數看不出單一 surface 寫入失敗（web 有資料就會 PASS），所以按 surface 分組；
    只有 page 組的 surface（googleNews / discover）不要求 query 組。
    """
    counts = {
        combo: count_rows(f"&search_type=eq.{search_type}&{combo_filter(combo)}")
        for combo in SURFACE_COMBOS[search_type]
    }
    if COMBO_QUERY in counts:
        logger.info("%s：page 組 %d 列 / query 組 %d 列（合計 %d）", search_type,
                    counts[COMBO_PAGE], counts[COMBO_QUERY], sum(counts.values()))
    else:
        logger.info("%s：page 組 %d 列（此 surface 不支援 query 維度）",
                    search_type, counts[COMBO_PAGE])
    empty = [combo for combo, rows in counts.items() if not rows]
    if empty:
        logger.error("%s：%s 組 0 列 —— 該 surface 沒有資料，視為失敗",
                     search_type, "／".join(empty))
    return not empty


def run_verify(search_types: Sequence[str] = (DEFAULT_SEARCH_TYPE,)) -> int:
    """唯讀檢查。按 surface 分組印出各組列數，以及 gsc_daily_totals（對本次 surface
    過濾）的列數與最新日期 —— 這是「不可相加」與「單一 surface 寫入失敗」兩件事的
    持續可見性（review S4.1 #9：S2.3 當時跳過的 totals 輸出，補在這裡）。"""
    healthy = all([_verify_surface(search_type) for search_type in search_types])
    logger.info("⚠ 兩組是同一批底層資料的兩個邊際聚合，SUM 前必須帶判別式，"
                "否則點擊數會被算兩次。gsc_daily_totals 是另一個母體（全量），更不可相加。")

    for search_type in search_types:
        totals_rows = count_rows(f"&search_type=eq.{search_type}", TABLE_TOTALS)
        status, body = _supabase_request(
            "GET",
            f"/rest/v1/{TABLE_TOTALS}?select=date&search_type=eq.{search_type}"
            "&order=date.desc&limit=1",
        )
        latest_rows = json.loads(body) if status == 200 else []
        latest = latest_rows[0]["date"] if latest_rows else "N/A"
        logger.info("  totals(%s)：%d 列，最新日期 %s", search_type, totals_rows, latest)

    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_GSC}?select=date,page,query,device,clicks,impressions,ctr,position"
        f"&search_type=in.({','.join(search_types)})&order=date.desc,clicks.desc&limit=8",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_GSC, status, body[:300])
        return 1
    for row in json.loads(body):
        combo = COMBO_QUERY if row["page"] == PAGE_NOT_REQUESTED else COMBO_PAGE
        subject = row["query"] if combo == COMBO_QUERY else row["page"]
        logger.info("  %s [%s] %s/%s clicks=%d imp=%d pos=%.1f",
                    row["date"], combo, subject[:60], row["device"],
                    row["clicks"], row["impressions"], row["position"])

    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_RUN}?select=id,window_start,window_end,row_count,status,finished_at"
        f"&table_name=eq.{TABLE_GSC}&order=started_at.desc&limit=3",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_RUN, status, body[:300])
        return 1
    for run in json.loads(body):
        logger.info("  run %s %s..%s status=%s rows=%d finished=%s",
                    run["id"][:8], run["window_start"], run["window_end"],
                    run["status"], run["row_count"], run["finished_at"])
    return 0 if healthy else 1


def run_freshness_check() -> int:
    """新鮮度告警。條件是「表裡最新資料日期太舊」，不是「作業有沒有回報失敗」——
    排程沒被觸發時不會產生任何失敗事件，只有資料本身的缺席能證明作業沒在跑。
    門檻公式見 FRESHNESS_MAX_AGE_HOURS 註解（含 GSC 固有延遲，非排程週期 × N）。"""
    latest = latest_date()
    if latest is None:
        logger.error("FAIL: %s 是空的，ingestion 從未成功寫入。", TABLE_GSC)
        return 1
    latest_utc = datetime.combine(latest, datetime.min.time(), tzinfo=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - latest_utc).total_seconds() / 3600
    if age_hours > FRESHNESS_MAX_AGE_HOURS:
        logger.error(
            "FAIL: %s 最新資料日期 %s，已 %.1f 小時（門檻 %dh）。"
            "GSC 本身有 2-3 天延遲，超過門檻代表排程停擺而非延遲。",
            TABLE_GSC, latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS,
        )
        return 1
    logger.info("PASS: %s 最新資料日期 %s（%.1f 小時前，門檻 %dh）。",
                TABLE_GSC, latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS)
    return 0


# resolve_probe_days／resolve_backfill_days／resolve_search_type 搬進 gsc_surfaces.py 了
# （review S4.1 #9：純值域函式，跟同樣搬過去的值域常數放同一檔更合理），上面 import 區塊取用。


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把 GSC Search Analytics 逐日資料寫進 Supabase gsc_daily_metrics"
    )
    parser.add_argument("--dry-run", action="store_true", help="查 API、算完、印摘要但不寫庫（預設）")
    parser.add_argument("--execute", action="store_true", help="實際 upsert 進 Supabase")
    parser.add_argument("--verify", action="store_true", help="唯讀檢查最近寫入狀態（含兩組列數）")
    parser.add_argument("--check-freshness", action="store_true",
                        help=f"新鮮度告警：最新資料超過 {FRESHNESS_MAX_AGE_HOURS}h 則 exit 1")
    parser.add_argument("--backfill-days", type=int, default=None,
                        help=f"回補最近 N 天（預設 {DEFAULT_BACKFILL_DAYS}，"
                             f"上限 min({MAX_BACKFILL_DAYS}, --probe-days)）")
    parser.add_argument("--probe-days", type=int, default=None,
                        help=f"探測回看 N 天（預設 {DEFAULT_PROBE_DAYS}，{MIN_PROBE_DAYS}..{MAX_PROBE_DAYS}）；"
                             "同時是 --backfill-days 的上限，也決定 gsc_daily_totals 這次補幾天")
    parser.add_argument("--search-type", default=DEFAULT_SEARCH_TYPE,
                        help=f"search type（預設 {DEFAULT_SEARCH_TYPE}，可選 {ALLOWED_SEARCH_TYPES}）")
    args = parser.parse_args()

    try:
        probe_days = resolve_probe_days(args.probe_days)
        backfill_days = resolve_backfill_days(args.backfill_days, probe_days)
        search_type = resolve_search_type(args.search_type)
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(2)

    if args.verify:
        sys.exit(run_verify([search_type]))
    if args.check_freshness:
        sys.exit(run_freshness_check())

    logger.info("回補最近 %d 天（search_type=%s，探測窗 %d 天，property=%s）。",
                backfill_days, search_type, probe_days, PROPERTY)
    if not args.execute:
        logger.info("預設為 dry-run，加 --execute 才會寫入。")
    sys.exit(run_ingestion(execute=args.execute, backfill_days=backfill_days,
                           search_type=search_type, probe_days=probe_days))


if __name__ == "__main__":
    main()
