"""
data_quality_gate.py — 五條 warehouse 管線統一資料品質 gate（S3.5）

背景：五條背景管線各自有一套零散的健康檢查（每個 ingest_*.py 自己一個
run_freshness_check() + 一個模組級 FRESHNESS_MAX_AGE_HOURS 常數），只做了
「新鮮度」一類，抓不到 2026-09-03 實測到的三個缺陷：

  1. CrUX 管線在 ingestion_run 裡與 RUM 共用 table_name='cwv_hourly'，無法
     單獨查詢——任何「以表為單位」的新鮮度檢查在 RUM 持續寫入時永遠是綠燈，
     即使 CrUX 那個維度已經停擺 16 天。新鮮度必須按管線（表 + 維度篩選）切，
     不能按表。
  2. 3 筆殘留的 status='running' 紀錄，最舊超過 30 小時未收尾——作業死掉沒
     收尾，讓「有沒有作業卡住」變成不可偵測。
  3. 各表門檻不同（小時/日/週三種週期），需要 per-pipeline 設定而非散落的
     模組級常數。

設定集中在 scripts/quality_gate_config.py（PIPELINES）。本檔是三類檢查
（新鮮度／空段／靜默降級）+ 唯一的寫入動作（reap 殘留 running）+ CLI。

═══ 硬性約束（抄自任務書，執行時務必遵守）═══

  - 健康檢查一律以「資料新鮮度」為條件，不以「作業是否回報失敗」為條件——
    作業沒被觸發時它不會回報任何東西（KB alert-on-data-freshness-not-job-failure）。
  - 任何「查不到資料」的情況一律回報為失敗，不得在報表層以 0 呈現
    （見 SupabaseQueryError 的處理方式：每個 check_* 函式的 except 分支
    一律回傳 passed=False，不吞掉、不回傳 skipped）。
  - 全模組唯一會寫 production 資料的路徑是 reap_stale_running()，且預設
    dry-run，需要 --execute 才會真的 PATCH；每一次寫入都帶稽核欄位
    （見 migrations/021_ingestion_run_reap_audit.sql）。其餘一律唯讀。

用法：
  python scripts/data_quality_gate.py                          # 全部管線、全部檢查
  python scripts/data_quality_gate.py --pipeline cwv_hourly_crux
  python scripts/data_quality_gate.py --check freshness
  python scripts/data_quality_gate.py --reap-stale-running               # dry-run 預覽
  python scripts/data_quality_gate.py --reap-stale-running --execute     # 實際標記 failed
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from quality_gate_config import (
        DEFAULT_STALE_RUNNING_THRESHOLD_HOURS,
        PIPELINES,
        PIPELINES_BY_KEY,
        STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE,
        PipelineConfig,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from quality_gate_config import (  # noqa: E402
        DEFAULT_STALE_RUNNING_THRESHOLD_HOURS,
        PIPELINES,
        PIPELINES_BY_KEY,
        STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE,
        PipelineConfig,
    )

from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

TABLE_RUN = "ingestion_run"
HTTP_TIMEOUT_SECONDS = 30
# 單一 check（尤其 gap_probe_per_point 的逐點探測）可能疊多次 HTTP_TIMEOUT_SECONDS=30
# 的請求，check 級門檻因此明顯拉高，而非直接沿用單次請求的 30s——見 _run_check_with_timeout。
CHECK_TIMEOUT_SECONDS = 180
USER_AGENT = "seo-knowledge-insight-data-quality-gate/1.0"
DEFAULT_REAP_ACTOR = "data_quality_gate.py --reap-stale-running"


class SupabaseQueryError(RuntimeError):
    """查詢失敗——呼叫端必須把這個當成 FAIL 處理，不得靜默略過。"""


@dataclass
class CheckResult:
    pipeline_key: str
    category: str  # "freshness" | "gap" | "degradation" | "stale_running"
    passed: bool
    message: str
    skipped: bool = False


# ══════════════════════════════════════════════════════════════════════
# Supabase HTTP（唯讀路徑走 _get_json；reap 是唯一的 _request PATCH 呼叫者）
# ══════════════════════════════════════════════════════════════════════

def _supabase_config() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("缺少 SUPABASE_URL 或 SUPABASE_SERVICE_KEY")
    return url, key


def _request(method: str, path: str, *, body: Any = None,
             extra_headers: Mapping[str, str] | None = None) -> tuple[int, str]:
    url, key = _supabase_config()
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


READ_PAGE_SIZE = 1000  # PostgREST 的 db-max-rows 預設就是 1000
PROBE_PAGE_SIZE = 1    # 逐點探測只問「這個時間點有沒有列」，取 1 列就夠（見 _probe_point_exists）


def _get_page(path: str, *, offset: int, page_size: int) -> tuple[list[dict], bool]:
    """回傳 (這一頁資料, 是否可能還有下一頁)。任何非 200/206 一律拋
    SupabaseQueryError——這是「查不到資料一律回報為失敗」這條硬性約束的實作點，
    所有唯讀檢查都走這裡，不得各自吞錯誤。"""
    status, body = _request(
        "GET", path,
        extra_headers={"Range-Unit": "items", "Range": f"{offset}-{offset + page_size - 1}"},
    )
    if status not in (200, 206):
        raise SupabaseQueryError(f"{path} 回應 {status}：{body[:200]}")
    page = json.loads(body)
    return page, len(page) == page_size


def _get_json_all(path: str, *, max_rows: int | None = None) -> list[dict]:
    """用 Range header 分頁抓到底（或抓滿 max_rows）——不用 querystring 的
    `limit=`，那個數字會被 PostgREST 的 db-max-rows 悄悄蓋過而不報錯，HTTP
    仍回 200，看不出被截斷（crawl_warehouse.py select_all() 的註解已踩過這個
    坑；S3.5 實測：cwv_hourly 近 24h 有 2130 列，用 limit= 會靜默漏掉一半以上，
    把健康資料誤判成空段）。"""
    collected: list[dict] = []
    offset = 0
    while max_rows is None or len(collected) < max_rows:
        page_size = READ_PAGE_SIZE if max_rows is None else min(READ_PAGE_SIZE, max_rows - offset)
        page, has_more = _get_page(path, offset=offset, page_size=page_size)
        collected.extend(page)
        offset += len(page)
        if not has_more or not page:
            break
    return collected


def _get_json(path: str) -> list[dict]:
    """單頁查詢的薄包裝，語意上等於「這條路徑本來就不會超過一頁」。"""
    return _get_json_all(path, max_rows=READ_PAGE_SIZE)


def _parse_iso(value: str) -> datetime:
    """同 quality_gate_config._parse_iso：純日期字串（DATE 欄位）一律補 UTC，
    避免 tz-aware / naive 混算時 TypeError。"""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso_z(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _filter_qs(filters: tuple[tuple[str, str], ...]) -> str:
    return "".join(f"&{k}=eq.{urllib.parse.quote(v)}" for k, v in filters)


def _range_filter_column(pipeline: PipelineConfig) -> str:
    cols = pipeline.resolved_select_columns()
    return cols[0]


# ══════════════════════════════════════════════════════════════════════
# 第一類：資料新鮮度 —— 查目的地，不查作業狀態
# ══════════════════════════════════════════════════════════════════════

def check_freshness(pipeline: PipelineConfig, *, now: datetime | None = None) -> CheckResult:
    now = now or datetime.now(timezone.utc)
    cols = pipeline.resolved_select_columns()
    select = ",".join(cols)
    order = ",".join(f"{c}.desc" for c in cols)
    path = f"/rest/v1/{pipeline.table}?select={select}{_filter_qs(pipeline.filters)}&order={order}&limit=1"
    try:
        rows = _get_json(path)
    except SupabaseQueryError as exc:
        return CheckResult(pipeline.key, "freshness", False, f"查詢失敗，視為 FAIL：{exc}")

    if not rows:
        return CheckResult(pipeline.key, "freshness", False,
                            f"FAIL：{pipeline.key} 是空的，管線從未成功寫入。")

    latest = pipeline.resolved_extractor()(rows[0])
    age_hours = (now - latest).total_seconds() / 3600
    if age_hours > pipeline.max_age_hours:
        return CheckResult(pipeline.key, "freshness", False,
                            f"FAIL：最新資料 {latest.isoformat()}，已 {age_hours:.1f}h 未更新"
                            f"（門檻 {pipeline.max_age_hours:.0f}h，{pipeline.cadence_label}）。")
    return CheckResult(pipeline.key, "freshness", True,
                        f"PASS：最新資料 {latest.isoformat()}（{age_hours:.1f}h 前，"
                        f"門檻 {pipeline.max_age_hours:.0f}h）。")


# ══════════════════════════════════════════════════════════════════════
# 第二類：空段偵測 —— 純函式與 I/O 分離，方便不動 production 資料就能單元測試
# ══════════════════════════════════════════════════════════════════════

def _floor_to_cadence(moment: datetime, cadence_hours: float) -> datetime:
    """對齊到該週期最近一次「已完整結束」桶的起點之後一格（見呼叫端 -step）。"""
    if cadence_hours == 24 * 7:
        floored = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        return floored - timedelta(days=floored.weekday())  # 對齊週一，同 cwv_hourly_source_granularity_ck
    if cadence_hours == 24:
        return moment.replace(hour=0, minute=0, second=0, microsecond=0)
    if cadence_hours == 1:
        return moment.replace(minute=0, second=0, microsecond=0)
    raise ValueError(f"未支援的 cadence_hours={cadence_hours}")


def expected_timestamps(
    now: datetime, cadence_hours: float, window_start: datetime, lag_cutoff: datetime,
) -> list[datetime]:
    """列舉 [window_start, now) 之間、依 cadence 對齊、且**關閉時間**早於 lag_cutoff 的時間點。

    純函式，不碰網路——這是空段檢查唯一需要的「業務邏輯」，其餘都是資料存取。
    lag_cutoff 讓「來源本身有發布延遲」或「排程本身的觸發/執行延遲」的最近幾筆
    不被誤判成空段（見 quality_gate_config.py 的 lag_buffer_hours 註解）。

    **比較的是桶的關閉時間（t + step），不是桶的起點（t）**——這是 S3.5 驗收時
    修正過的一個坑：`t` 代表桶的起點（例如 16:00 桶代表 [16:00, 17:00)），
    若直接拿 `t` 去跟 `now - lag_buffer_hours` 比，`lag_buffer_hours` 這個數字
    有一段（等於 cadence_hours）被「桶本身的寬度」吃掉，實際能容忍的排程延遲
    只剩 `lag_buffer_hours - cadence_hours`——對 hourly 管線幾乎等於沒有緩衝
    （buffer=1.25h、cadence=1h 時，實際容忍只有 15 分鐘，遠小於實測的正常延遲
    0.4–0.65h，導致剛跨過整點後有一段時間會誤報）。改成比較關閉時間後，
    `lag_buffer_hours` 才是它字面上的意思：「桶關閉後容忍多久沒資料」。
    """
    step = timedelta(hours=cadence_hours)
    anchor = _floor_to_cadence(now, cadence_hours) - step
    points: list[datetime] = []
    t = anchor
    while t >= window_start:
        if (t + step) <= lag_cutoff:
            points.append(t)
        t -= step
    return sorted(points)


def find_gaps(existing: set[datetime], expected: Sequence[datetime]) -> list[datetime]:
    """expected 裡不在 existing 集合中的時間點——這就是空段。"""
    return [t for t in expected if t not in existing]


def _fetch_existing_timestamps(
    pipeline: PipelineConfig, window_start: datetime,
) -> tuple[set[datetime], list[dict]]:
    range_col = _range_filter_column(pipeline)
    range_value = window_start.date().isoformat() if range_col == "date" else _iso_z(window_start)
    cols = ",".join(pipeline.resolved_select_columns())
    path = (f"/rest/v1/{pipeline.table}?select={cols}{_filter_qs(pipeline.filters)}"
            f"&{range_col}=gte.{urllib.parse.quote(range_value)}")
    rows = _get_json_all(path)  # 抓到底，不設 max_rows——空段窗內可能有數千列（見 _get_json_all 註解）
    extractor = pipeline.resolved_extractor()
    return {extractor(r) for r in rows}, rows


def _range_value(pipeline: PipelineConfig, moment: datetime) -> str:
    """把時間戳轉成該欄位在 PostgREST querystring 裡的字面值。DATE 欄位要用純日期，
    帶時間會讓 `date=eq.2026-09-01T00:00:00Z` 這種查詢在 PG 端型別轉換失敗。"""
    range_col = _range_filter_column(pipeline)
    return moment.date().isoformat() if range_col == "date" else _iso_z(moment)


def _probe_earliest_timestamp(pipeline: PipelineConfig, window_start: datetime) -> datetime | None:
    """掃描窗內最早的一筆時間戳，用一次 order asc + 取 1 列拿到。

    取代「把整窗抓回來再 min()」——後者為了一個 min() 值要翻上千頁（見
    PipelineConfig.gap_probe_per_point 的欄位註解）。用 Range header 限筆數而非
    querystring 的 limit=，理由同 _get_json_all。
    """
    range_col = _range_filter_column(pipeline)
    cols = ",".join(pipeline.resolved_select_columns())
    path = (f"/rest/v1/{pipeline.table}?select={cols}{_filter_qs(pipeline.filters)}"
            f"&{range_col}=gte.{urllib.parse.quote(_range_value(pipeline, window_start))}"
            f"&order={range_col}.asc")
    rows, _has_more = _get_page(path, offset=0, page_size=PROBE_PAGE_SIZE)
    return pipeline.resolved_extractor()(rows[0]) if rows else None


def _probe_point_exists(pipeline: PipelineConfig, point: datetime) -> bool:
    """這個預期時間點有沒有至少一列。DATE 欄位用 eq.<日期>；timestamp 欄位用
    半開區間 [point, point + cadence)，跟 expected_timestamps() 的「桶」語意一致。"""
    range_col = _range_filter_column(pipeline)
    if range_col == "date":
        window = f"&{range_col}=eq.{urllib.parse.quote(point.date().isoformat())}"
    else:
        upper = point + timedelta(hours=pipeline.cadence_hours)
        window = (f"&{range_col}=gte.{urllib.parse.quote(_iso_z(point))}"
                  f"&{range_col}=lt.{urllib.parse.quote(_iso_z(upper))}")
    cols = ",".join(pipeline.resolved_select_columns())
    path = f"/rest/v1/{pipeline.table}?select={cols}{_filter_qs(pipeline.filters)}{window}"
    rows, _has_more = _get_page(path, offset=0, page_size=PROBE_PAGE_SIZE)
    return bool(rows)


def _resolve_gap_points(
    pipeline: PipelineConfig, now: datetime, window_start: datetime,
) -> tuple[datetime, list[datetime], list[datetime], str]:
    """回傳 (effective_start, expected, gaps, 模式描述)。

    effective_start：掃描下限不早於「目前資料實際最早的時間戳」——管線上線不滿掃描
    窗長度時，避免把上線前『本來就沒有資料』的時段誤判成空段。兩條路徑共用這個規則，
    差別只在「最早時間戳」與「某點有沒有資料」是怎麼問出來的。
    """
    lag_cutoff = now - timedelta(hours=pipeline.lag_buffer_hours)
    if pipeline.gap_probe_per_point:
        earliest = _probe_earliest_timestamp(pipeline, window_start)
        effective_start = max(window_start, earliest) if earliest else window_start
        expected = expected_timestamps(now, pipeline.cadence_hours, effective_start, lag_cutoff)
        gaps = [t for t in expected if not _probe_point_exists(pipeline, t)]
        return effective_start, expected, gaps, f"逐點探測 {len(expected)} 個時間點"

    existing, _rows = _fetch_existing_timestamps(pipeline, window_start)
    effective_start = max(window_start, min(existing)) if existing else window_start
    expected = expected_timestamps(now, pipeline.cadence_hours, effective_start, lag_cutoff)
    return effective_start, expected, find_gaps(existing, expected), f"{len(expected)} 個預期時間點"


def check_gaps(pipeline: PipelineConfig, *, now: datetime | None = None) -> CheckResult:
    if pipeline.gap_window_hours is None:
        return CheckResult(pipeline.key, "gap", True,
                            f"SKIP（設計決定，非誤漏）：{pipeline.gap_skip_reason}", skipped=True)

    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(hours=pipeline.gap_window_hours)
    try:
        effective_start, expected, gaps, mode = _resolve_gap_points(pipeline, now, window_start)
    except SupabaseQueryError as exc:
        return CheckResult(pipeline.key, "gap", False, f"查詢失敗，視為 FAIL：{exc}")

    if gaps:
        shown = ", ".join(t.isoformat() for t in gaps[:5])
        more = f"（其餘 {len(gaps) - 5} 個略）" if len(gaps) > 5 else ""
        return CheckResult(pipeline.key, "gap", False,
                            f"FAIL：{len(gaps)} 個應有資料的時間點缺席：{shown}{more}")
    return CheckResult(pipeline.key, "gap", True,
                        f"PASS：掃描 {effective_start.isoformat()}..{now.isoformat()}"
                        f"（{mode}）無空段。")


# ══════════════════════════════════════════════════════════════════════
# 第三類：靜默降級 —— 總量正常，只有按維度切才看得出來
# ══════════════════════════════════════════════════════════════════════

def _degradation_select_columns(pipeline: PipelineConfig) -> str:
    d = pipeline.degradation
    assert d is not None
    cols = set(pipeline.resolved_select_columns()) | {d.column}
    if d.weight_column:
        cols.add(d.weight_column)
    return ",".join(sorted(cols))


def _evaluate_ratio_column(rows: list[dict], column: str, max_ratio: float, min_sample: int) -> CheckResult:
    values = [r[column] for r in rows if r.get(column) is not None]
    n = len(values)
    if n < min_sample:
        return CheckResult("", "degradation", True, f"SKIP：樣本數 {n} < min_sample {min_sample}。", skipped=True)
    worst = max(values)
    if worst > max_ratio:
        return CheckResult("", "degradation", False,
                            f"FAIL：{column} 最大值 {worst:.4f} 超過門檻 {max_ratio}（樣本數 {n}）。")
    return CheckResult("", "degradation", True,
                        f"PASS：{column} 最大值 {worst:.4f}（樣本數 {n}，門檻 {max_ratio}）。")


def _evaluate_fallback_value(rows: list[dict], d) -> CheckResult:
    if d.weight_column:
        total = sum(r.get(d.weight_column) or 0 for r in rows)
        matched = sum(r.get(d.weight_column) or 0 for r in rows if r.get(d.column) == d.fallback_value)
    else:
        total = len(rows)
        matched = sum(1 for r in rows if r.get(d.column) == d.fallback_value)
    if total < d.min_sample:
        return CheckResult("", "degradation", True, f"SKIP：樣本量 {total} < min_sample {d.min_sample}。", skipped=True)
    ratio = matched / total if total else 0.0
    if ratio > d.max_ratio:
        return CheckResult("", "degradation", False,
                            f"FAIL：{d.column}={d.fallback_value} 佔比 {ratio:.2%} 超過門檻 "
                            f"{d.max_ratio:.0%}（{matched}/{total}）。")
    return CheckResult("", "degradation", True,
                        f"PASS：{d.column}={d.fallback_value} 佔比 {ratio:.2%}"
                        f"（{matched}/{total}，門檻 {d.max_ratio:.0%}）。")


def check_degradation(pipeline: PipelineConfig) -> CheckResult:
    d = pipeline.degradation
    if d is None:
        return CheckResult(pipeline.key, "degradation", True,
                            f"SKIP（已知缺口，非略過）：{pipeline.degradation_skip_reason}", skipped=True)

    select = _degradation_select_columns(pipeline)
    order = ",".join(f"{c}.desc" for c in pipeline.resolved_select_columns())
    path = f"/rest/v1/{pipeline.table}?select={select}{_filter_qs(pipeline.filters)}&order={order}"
    try:
        # max_rows 走 Range header 分頁，不用 querystring 的 limit=——
        # d.sample_limit 可以到 5000（crawl_daily），querystring limit 會被
        # db-max-rows 悄悄蓋成 1000（見 _get_json_all 註解）。
        rows = _get_json_all(path, max_rows=d.sample_limit)
    except SupabaseQueryError as exc:
        return CheckResult(pipeline.key, "degradation", False, f"查詢失敗，視為 FAIL：{exc}")

    result = (_evaluate_ratio_column(rows, d.column, d.max_ratio, d.min_sample)
              if d.mode == "ratio_column" else _evaluate_fallback_value(rows, d))
    result.pipeline_key = pipeline.key
    return result


# ══════════════════════════════════════════════════════════════════════
# 缺陷 2：殘留 running —— 全模組唯一可能寫入的路徑
# ══════════════════════════════════════════════════════════════════════

def find_stale_running(*, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    rows = _get_json(f"/rest/v1/{TABLE_RUN}?select=id,table_name,started_at"
                      "&status=eq.running&order=started_at.asc")
    stale = []
    for row in rows:
        started = _parse_iso(row["started_at"])
        age_hours = (now - started).total_seconds() / 3600
        threshold = STALE_RUNNING_THRESHOLD_HOURS_BY_TABLE.get(
            row["table_name"], DEFAULT_STALE_RUNNING_THRESHOLD_HOURS)
        if age_hours > threshold:
            stale.append({**row, "age_hours": age_hours, "threshold_hours": threshold})
    return stale


def check_stale_running(*, now: datetime | None = None) -> CheckResult:
    try:
        stale = find_stale_running(now=now)
    except SupabaseQueryError as exc:
        return CheckResult("__global__", "stale_running", False, f"查詢失敗，視為 FAIL：{exc}")
    if stale:
        detail = "; ".join(
            f"{r['table_name']} id={r['id'][:8]} age={r['age_hours']:.1f}h(門檻{r['threshold_hours']:.0f}h)"
            for r in stale
        )
        return CheckResult("__global__", "stale_running", False,
                            f"FAIL：{len(stale)} 筆殘留 running 未收尾：{detail}")
    return CheckResult("__global__", "stale_running", True, "PASS：無殘留 running 紀錄。")


def reap_stale_running(
    stale_rows: list[dict], *, actor: str = DEFAULT_REAP_ACTOR, dry_run: bool = True,
) -> list[dict]:
    """把死掉的 running 列標記成 failed，帶稽核欄位。唯一的寫入函式。"""
    now = datetime.now(timezone.utc)
    results = []
    for row in stale_rows:
        reason = (f"gate 判定死亡：status=running 已 {row['age_hours']:.1f}h 未收尾"
                  f"（門檻 {row['threshold_hours']:.0f}h，started_at={row['started_at']}）")
        if dry_run:
            results.append({"id": row["id"], "action": "would_reap", "reason": reason})
            continue
        status, _body = _request(
            "PATCH", f"/rest/v1/{TABLE_RUN}?id=eq.{urllib.parse.quote(row['id'])}",
            body={
                "status": "failed",
                "finished_at": _iso_z(now),
                "reaped_at": _iso_z(now),
                "reaped_by": actor,
                "reap_reason": reason,
            },
            extra_headers={"Prefer": "return=minimal"},
        )
        action = "reaped" if status in (200, 204) else "reap_failed"
        results.append({"id": row["id"], "action": action, "reason": reason, "http_status": status})
    return results


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

def _run_check_with_timeout(
    pipeline_key: str, category: str, fn, *args: Any, timeout: float = CHECK_TIMEOUT_SECONDS,
) -> CheckResult:
    """單一 check 的逾時保護：一個卡住的 PostgREST 請求不該拖死整條 watchdog，
    其餘 check 要照跑。

    用 daemon thread 而非 concurrent.futures.ThreadPoolExecutor——後者的
    worker thread 會被直譯器的 atexit hook 追蹤，若那個 check 真的卡死，
    行程結束時一樣會被拖住等它收尾；daemon thread 不阻塞行程結束，逾時後
    直接回報 FAIL，讓卡住的執行緒留在背景（受個別請求的 HTTP_TIMEOUT_SECONDS
    拘束，不是永久掛住），不影響後續 check 或整支腳本的結束時間。
    """
    box: dict[str, Any] = {}

    def runner() -> None:
        try:
            box["result"] = fn(*args)
        except BaseException as exc:  # noqa: BLE001 — 任何例外都要轉成 FAIL，不能讓整個 gate 崩掉
            box["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout=timeout)
    if thread.is_alive():
        return CheckResult(pipeline_key, category, False,
                            f"FAIL：check 逾時（timeout after {timeout}s）。")
    if "error" in box:
        return CheckResult(pipeline_key, category, False,
                            f"FAIL：check 拋出例外：{box['error']}")
    return box["result"]


def _run_checks(pipeline_key: str | None, check: str) -> list[CheckResult]:
    pipelines = [PIPELINES_BY_KEY[pipeline_key]] if pipeline_key else list(PIPELINES)
    results: list[CheckResult] = []
    for p in pipelines:
        if check in ("all", "freshness"):
            results.append(_run_check_with_timeout(
                p.key, "freshness", check_freshness, p, timeout=CHECK_TIMEOUT_SECONDS))
        if check in ("all", "gaps"):
            results.append(_run_check_with_timeout(
                p.key, "gap", check_gaps, p, timeout=CHECK_TIMEOUT_SECONDS))
        if check in ("all", "degradation"):
            results.append(_run_check_with_timeout(
                p.key, "degradation", check_degradation, p, timeout=CHECK_TIMEOUT_SECONDS))
    if check in ("all", "stale-running") and pipeline_key is None:
        results.append(_run_check_with_timeout(
            "__global__", "stale_running", check_stale_running, timeout=CHECK_TIMEOUT_SECONDS))
    return results


def _run_reap(execute: bool) -> int:
    try:
        stale = find_stale_running()
    except SupabaseQueryError as exc:
        logger.error("查詢失敗：%s", exc)
        return 1
    if not stale:
        logger.info("PASS：無殘留 running 紀錄，無需 reap。")
        return 0
    results = reap_stale_running(stale, dry_run=not execute)
    for r in results:
        logger.info("%s id=%s：%s", r["action"], r["id"][:8], r["reason"])
    if not execute:
        logger.info("[DRY RUN] 加 --execute 才會實際寫入 %d 筆。", len(stale))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="五條 warehouse 管線統一資料品質 gate")
    parser.add_argument("--pipeline", choices=[p.key for p in PIPELINES], default=None,
                        # 已知 drift：這裡曾寫死「5 條」，GSC Search Analytics 陸續拆出
                        # gsc_googlenews／gsc_discover／gsc_daily_totals／gsc_image／gsc_video
                        # 五個子管線後，PIPELINES 實際筆數已經跟「五條 warehouse 管線」
                        # （模組 docstring 講的是 5 個來源系統／workflow，不是這個數字）脫鉤，
                        # 改用 len(PIPELINES) 動態算，不再手動維護一個會過期的數字。
                        help=f"只檢查指定管線（預設全部 {len(PIPELINES)} 條）")
    parser.add_argument("--check", choices=["all", "freshness", "gaps", "degradation", "stale-running"],
                        default="all")
    parser.add_argument("--reap-stale-running", action="store_true",
                        help="把死掉的 running 列標記成 failed（預設 dry-run）")
    parser.add_argument("--execute", action="store_true", help="配合 --reap-stale-running：實際寫入")
    args = parser.parse_args()

    if args.reap_stale_running:
        sys.exit(_run_reap(args.execute))

    results = _run_checks(args.pipeline, args.check)
    for r in results:
        tag = "SKIP" if r.skipped else ("PASS" if r.passed else "FAIL")
        logger.info("[%s] %-20s %-12s %s", tag, r.pipeline_key, r.category, r.message)

    failed = [r for r in results if not r.passed]
    if failed:
        logger.error("品質 gate 失敗：%d/%d 項未通過", len(failed), len(results))
        sys.exit(1)
    skipped = sum(1 for r in results if r.skipped)
    logger.info("品質 gate 全部通過（共 %d 項，含 %d 項 SKIP）", len(results), skipped)


if __name__ == "__main__":
    main()
