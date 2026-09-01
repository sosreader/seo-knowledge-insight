"""
ingest_cwv_hourly.py — 把 Loki 的 web-vitals RUM 資料逐小時聚合寫進 Supabase cwv_hourly

資料流：Loki（Grafana datasource proxy）→ 逐小時 × 四維聚合 → Supabase PostgREST upsert
本腳本一律寫 source='rum'。CrUX 週序列由另一支腳本負責（S2.4），不在此處。

用法：
  python scripts/ingest_cwv_hourly.py --dry-run              # 查 Loki、算完、印摘要，不寫庫（預設）
  python scripts/ingest_cwv_hourly.py --execute              # 實際 upsert
  python scripts/ingest_cwv_hourly.py --verify               # 唯讀檢查最近寫入狀態
  python scripts/ingest_cwv_hourly.py --execute --backfill-hours 24
  python scripts/ingest_cwv_hourly.py --check-freshness      # 新鮮度告警：stale 則 exit 1

環境變數：
  GRAFANA_URL / GRAFANA_SERVICE_ACCOUNT_TOKEN
  CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET   （Grafana 在 Cloudflare Access 後面）
  SUPABASE_URL / SUPABASE_SERVICE_KEY


═══ 設計決定 ═══

【1. 只寫已完整結束的整點小時】
current hour 是半滿的桶，不寫。每次執行取「當前整點之前的 N 個完整小時」。
半滿的桶就算靠 upsert 事後補滿也可行，但中間那段時間 warehouse 裡存在一個
「數字看起來正常、其實只有半小時樣本」的列——沒有任何欄位能表達這件事，
下游算週趨勢時會把它當完整小時。寧可晚一小時，不要寫一個無法辨識的半桶。

【2. 每次查前 2 小時（DEFAULT_LOOKBACK_HOURS），相鄰執行刻意重疊】
排程每小時跑一次但只需 1 小時的新資料，多查一小時是為了自癒：
單次執行失敗、GitHub Actions 排程延遲、Loki 短暫不可用，下一輪會補回來。
重疊的正確性靠 cwv_hourly_dim_uniq 的 upsert 冪等保證，不靠「剛好不重疊」。
注意這只買到「小時」等級的容錯；Loki retention 只有 168h，靜默停擺超過 7 天
資料永久遺失，那要靠 --check-freshness 的新鮮度告警擋。

【3. 離群值門檻：per-metric，不是單一 5000】
既有 Grafana panel 用 `value < 5000` 一體適用。這裡刻意不照抄：
5000ms 對 INP 是合理的「這不可能是真的」上界（Google 的 poor 門檻是 500ms，
實測撞到的 2583429ms ≈ 43 分鐘是背景分頁 artifact）；但對 LCP 不是——
LCP > 5s 是真實存在的「poor」測量值（Google 的 poor 門檻是 4s），砍掉它會讓
p75 偏低、good_rate 偏高，把 CWV 倉儲變成一個報喜不報憂的表。
2026-08-29 實測單一小時：≥5000 的有 INP×1 / LCP×2，套 5000 門檻後
INP p75 264→198（-25%）、LCP p75 1432→1385。INP 那筆該砍，LCP 那兩筆不該。

所以用 OUTLIER_MAX_BY_METRIC（per-metric 覆寫）+ OUTLIER_MAX_DEFAULT（60s 通用上界）。
60s 遠高於任何真實 field 值、遠低於背景分頁 artifact，只砍物理上不可能的值。
CLS 無單位（值域 ~0..5），恆低於任何 ms 門檻，等於不過濾。

門檻同時套用在 count / good count / p75 三個查詢上——只過濾 p75 會讓
sample_count 與 p75 的母體不一致（sample_count 說 17 筆，p75 其實只用了 16 筆）。

【4. unknown_ratio 是 hour-level 純量，複製到該小時每一列】
定義：該小時、該 source 之下，任一 allowlist 維度（environment / metricType /
routePattern / deviceType）落到 'unknown' 的樣本數 ÷ 該小時總樣本數。

不是每個桶自己的 unknown 比例——桶鍵已經固定了四個維度值，那個比例必為 0 或 1，
是退化的、無法設門檻的訊號。hour-level 純量才是可監控的資料品質指標。

上游 sanitizeAllowlisted() 對不在 allowlist 的值不是拒收而是換成 'unknown' 照樣送出，
API 回 204、筆數與成功率全部正常——這是一個不產生任何錯誤訊號的靜默降級，
unknown_ratio 是它唯一的可觀測面。

【5. ingested_at 不進 payload】
= 該列「首次寫入」的時間。重跑同一小時時 PostgREST 的 ON CONFLICT DO UPDATE
只會更新 payload 裡有的欄位，所以 ingested_at 保持不變，重跑是真正的 no-op。
資料新鮮度不看這一欄，看 ingestion_run（見 --check-freshness）。

【6. Loki 走 datasource proxy 路徑】
  可行：{GRAFANA_URL}/api/datasources/proxy/uid/<uid>/loki/api/v1/...
  404 ：{GRAFANA_URL}/api/datasources/uid/<uid>/resources/loki/api/v1/...
兩條都實測過（2026-08-29），只有前者可用。

另：必須送自訂 User-Agent。Python 預設的 `Python-urllib/3.x` 會被 Cloudflare
以 error code 1010（browser signature ban）擋在 Access 驗證之前，回 403 且
內容不是 JSON——看起來像憑證錯誤，其實是 UA 被 ban。


═══ Loki 硬約束（三種失敗長得不一樣，錯誤處理必須分得開）═══

  max_query_length: 170h — 且是「時間窗 + range selector」加總計法
  max_query_bytes_read: 3GB — pre-flight 拒絕
  retention_period: 168h — 超出保留期回 HTTP 200 + 空結果，沒有任何錯誤

實測（2026-08-29，經 Grafana proxy）：

  171h 窗 + [1h]  → HTTP 400  the query time range exceeds the limit (query length: 171h0m0s, limit: 7d2h)
  170h 窗 + [1h]  → HTTP 500  Failed to get bytes read stats for query: rpc error: code = Code(400)
                              desc = the query time range exceeds the limit (query length: 171h0m0s ...)
  169h 窗 + [2h]  → HTTP 500  （同上，171h = 169 + 2，證實加總計法）
  30 天前 1h 窗   → HTTP 200  result=[]、totalBytesProcessed=0（靜默）

也就是說**同一種違規會依「哪一層先攔到」吐出 400 或 500**：窗本身超限走 frontend
的 range 檢查回 400；窗沒超但窗+selector 超限，是 bytes-read-stats 路徑用加總計法
攔下，內層 400 被包成 HTTP 500。bytes 閘門則是 HTTP 400 + "would read too many bytes"。
=> 用 status code 分不出來，一定要看訊息內容。classify_loki_error() 就是幹這件事。

保留期那條最危險：不報錯、不警告，全零看起來跟「那小時真的沒流量」一模一樣。
兩道防線：(a) 回填視窗硬性上限 48h，遠離 168h 門檻；(b) 寫入前先打 /index/stats
確認該視窗在索引裡真的有資料，且 sample_count == 0 的桶一律不落庫（不是寫 0）。
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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── Loki ────────────────────────────────────────────────────────────────
LOKI_DATASOURCE_UID = "ffhwhnr95ygaof"  # "Loki (Production)"；staging 是 cfhwdain1kwsgc
LOKI_PROXY_PATH = "/api/datasources/proxy/uid/{uid}/loki/api/v1"
LOKI_JOB = "web-vitals"
LOKI_RETENTION_HOURS = 168
HTTP_TIMEOUT_SECONDS = 180
# Cloudflare 會用 UA 擋掉 Python-urllib 預設值（error code 1010），必須自報身分。
USER_AGENT = "seo-knowledge-insight-cwv-ingest/1.0"

# ── 聚合 ────────────────────────────────────────────────────────────────
SOURCE = "rum"
BUCKET = "1h"
STEP_SECONDS = 3600
DEFAULT_LOOKBACK_HOURS = 2
MAX_BACKFILL_HOURS = 48  # 單次跨度上限，防打錯字（例如多打一個 0）

# 【真正的安全門檻 — 絕對時間，不是跨度】
# 超出 retention 的查詢會回 HTTP 200 + 全零而不是報錯，所以必須在送查之前擋。
# 跨度上限擋不住這件事：一段只有 34h 寬、但起點在 82h 前的視窗，跨度合格卻可能
# 整段落在保留期外。真正該檢查的是「最舊的那一小時距今多久」。
# 留 24h 邊界，不頂著 168h 門檻跑（Loki 的實際刪除有延遲，且排程本身可能晚跑）。
RETENTION_SAFETY_MARGIN_HOURS = 24
MAX_AGE_HOURS = LOKI_RETENTION_HOURS - RETENTION_SAFETY_MARGIN_HOURS  # 144
UNKNOWN = "unknown"

# Loki stream label → cwv_hourly 欄位。這五個都是真正的 stream label（非 JSON 欄位），
# 所以 count 類查詢不需要 | json，只有取 value 的 p75 需要。
LABEL_TO_COLUMN = {
    "environment": "environment",
    "metricType": "metric",
    "routePattern": "route_type",
    "deviceType": "device",
}
DIMENSION_LABELS = tuple(LABEL_TO_COLUMN)

# 離群值上界（見 docstring 設計決定 3）。單位 ms；CLS 無單位但恆低於門檻。
OUTLIER_MAX_DEFAULT = 60000.0
OUTLIER_MAX_BY_METRIC = {"INP": 5000.0}

# ── Supabase ────────────────────────────────────────────────────────────
TABLE_CWV = "cwv_hourly"
TABLE_RUN = "ingestion_run"
CONFLICT_KEY = "source,environment,hour,metric,route_type,device"
UPSERT_BATCH_SIZE = 500
FRESHNESS_MAX_AGE_HOURS = 3  # 排程週期 1h 的 3 倍


class LokiQueryError(RuntimeError):
    """Loki 查詢失敗，且已分類成可行動的類別。"""

    def __init__(self, kind: str, detail: str, remedy: str) -> None:
        super().__init__(f"[{kind}] {detail} — {remedy}")
        self.kind = kind
        self.detail = detail
        self.remedy = remedy


# ══════════════════════════════════════════════════════════════════════
# 時間
# ══════════════════════════════════════════════════════════════════════

def truncate_to_hour(moment: datetime) -> datetime:
    """截到 UTC 整點。cwv_hourly_source_granularity_ck 要求 rum 的 hour 嚴格對齊。"""
    return moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def complete_hours(now: datetime, count: int) -> list[datetime]:
    """回傳 now 之前 count 個「已完整結束」的整點小時，由舊到新。

    當前這個未結束的小時一律不含（見設計決定 1）。
    now=14:37 count=2 → [12:00, 13:00]（13:00-14:00 已結束，14:00-15:00 還在進行）。
    """
    current = truncate_to_hour(now)
    return [current - timedelta(hours=offset) for offset in range(count, 0, -1)]


def parse_iso_hour(raw: str) -> datetime:
    """解析 CLI 傳入的 ISO 時間。無時區者視為 UTC，避免跟著本機時區漂移。"""
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"--backfill-until 不是合法 ISO 時間：{raw!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return truncate_to_hour(parsed)


def to_nanoseconds(moment: datetime) -> int:
    return int(moment.timestamp()) * 10**9


# ══════════════════════════════════════════════════════════════════════
# LogQL 組裝
# ══════════════════════════════════════════════════════════════════════

def build_outlier_filter() -> str:
    """把 OUTLIER_MAX_* 常數編成一段 LogQL label filter。

    產出形如：
      | json | value < 60000 | metricType != "INP" or value < 5000
    通用上界先過一遍，再對每個有 per-metric 覆寫的 metric 疊一條更嚴的。
    """
    clauses = [f"| json | value < {OUTLIER_MAX_DEFAULT:g}"]
    for metric, ceiling in sorted(OUTLIER_MAX_BY_METRIC.items()):
        clauses.append(f'| metricType != "{metric}" or value < {ceiling:g}')
    return " ".join(clauses)


def _by_clause() -> str:
    return ", ".join(DIMENSION_LABELS)


def build_count_query(rating: str | None = None) -> str:
    """每個維度組合的樣本數；rating 指定時只算該 rating（用來算 good_rate）。"""
    selector = f'{{job="{LOKI_JOB}"}}' if rating is None else f'{{job="{LOKI_JOB}", rating="{rating}"}}'
    return (
        f"sum by ({_by_clause()}) "
        f"(count_over_time({selector} {build_outlier_filter()} [{BUCKET}]))"
    )


def build_p75_query() -> str:
    return (
        f'quantile_over_time(0.75, {{job="{LOKI_JOB}"}} {build_outlier_filter()} '
        f"| unwrap value [{BUCKET}]) by ({_by_clause()})"
    )


# ══════════════════════════════════════════════════════════════════════
# Loki HTTP
# ══════════════════════════════════════════════════════════════════════

def classify_loki_error(status: int, body: str) -> LokiQueryError:
    """把 Loki/Grafana 的錯誤回應分類成可行動的類別。

    status code 分不出來（見 module docstring 的實測表），一定要看訊息。
    """
    lowered = body.lower()
    if "too many bytes" in lowered or "max_query_bytes_read" in lowered:
        return LokiQueryError(
            "bytes-limit",
            f"HTTP {status}: 查詢被 max_query_bytes_read (3GB) pre-flight 拒絕。{body[:300]}",
            "縮小 --backfill-hours，或改用更窄的 selector；正常排程每小時僅掃約 0.87MB，"
            "撞到這個門檻代表上游流量異常暴增，應先查來源而不是放寬門檻。",
        )
    if "query length" in lowered or "time range exceeds" in lowered:
        return LokiQueryError(
            "length-limit",
            f"HTTP {status}: 查詢被 max_query_length (170h) 拒絕。{body[:300]}",
            f"length 的算法是「時間窗 + range selector」加總，本腳本的窗最多 "
            f"{MAX_BACKFILL_HOURS}h + [{BUCKET}]；撞到代表 --backfill-hours 被改壞或 Loki 門檻被調低。",
        )
    return LokiQueryError(
        "unknown",
        f"HTTP {status}: {body[:300]}",
        "非已知的門檻錯誤，檢查 Grafana 憑證、CF Access header 與 datasource UID。"
        "回應若不是 JSON 而是 Cloudflare 錯誤頁（error code 1010），是 User-Agent 被擋。",
    )


def loki_headers() -> dict[str, str]:
    token = os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN", "")
    client_id = os.environ.get("CF_ACCESS_CLIENT_ID", "")
    client_secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
    if not token or not client_id or not client_secret:
        raise RuntimeError(
            "缺少 GRAFANA_SERVICE_ACCOUNT_TOKEN / CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET"
        )
    return {
        "Authorization": f"Bearer {token}",
        "CF-Access-Client-Id": client_id,
        "CF-Access-Client-Secret": client_secret,
        "User-Agent": USER_AGENT,
    }


def _loki_get(path: str, params: Mapping[str, Any]) -> dict:
    base = os.environ.get("GRAFANA_URL", "").rstrip("/")
    if not base:
        raise RuntimeError("缺少 GRAFANA_URL")
    url = (
        base
        + LOKI_PROXY_PATH.format(uid=LOKI_DATASOURCE_UID)
        + path
        + "?"
        + urllib.parse.urlencode(params)
    )
    request = urllib.request.Request(url, headers=loki_headers())
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        raise classify_loki_error(exc.code, exc.read().decode(errors="replace")) from exc


def loki_index_stats(start: datetime, end: datetime) -> dict:
    """視窗的索引統計。超出 retention 時全零——這是「靜默回空」唯一的事前訊號。"""
    return _loki_get(
        "/index/stats",
        {"query": f'{{job="{LOKI_JOB}"}}', "start": to_nanoseconds(start), "end": to_nanoseconds(end)},
    )


def loki_query_range(query: str, start: datetime, end: datetime) -> list[dict]:
    payload = _loki_get(
        "/query_range",
        {
            "query": query,
            "start": to_nanoseconds(start),
            "end": to_nanoseconds(end),
            "step": f"{STEP_SECONDS}s",
        },
    )
    return payload.get("data", {}).get("result", [])


# ══════════════════════════════════════════════════════════════════════
# 聚合
# ══════════════════════════════════════════════════════════════════════

def _dimension_key(metric_labels: Mapping[str, str]) -> tuple[str, ...]:
    """Loki 缺 label 時視同上游的 UNKNOWN 降級，不丟棄該筆。"""
    return tuple(metric_labels.get(label) or UNKNOWN for label in DIMENSION_LABELS)


def parse_matrix(result: Sequence[Mapping[str, Any]]) -> dict[tuple[datetime, tuple[str, ...]], float]:
    """Loki matrix → {(bucket_hour, dims): value}。

    count_over_time 在時間 T 涵蓋 (T-1h, T]，所以 T 這個評估點代表的是「T 的前一小時」，
    bucket_hour = T - 1h。
    """
    parsed: dict[tuple[datetime, tuple[str, ...]], float] = {}
    for series in result:
        dims = _dimension_key(series.get("metric", {}))
        for raw_timestamp, raw_value in series.get("values", []):
            evaluated_at = datetime.fromtimestamp(float(raw_timestamp), timezone.utc)
            bucket_hour = truncate_to_hour(evaluated_at) - timedelta(hours=1)
            parsed[(bucket_hour, dims)] = float(raw_value)
    return parsed


def compute_unknown_ratios(
    counts: Mapping[tuple[datetime, tuple[str, ...]], float],
) -> dict[datetime, float]:
    """每小時的 unknown_ratio：任一維度為 UNKNOWN 的樣本數 ÷ 該小時總樣本數。"""
    totals: dict[datetime, float] = {}
    degraded: dict[datetime, float] = {}
    for (bucket_hour, dims), count in counts.items():
        totals[bucket_hour] = totals.get(bucket_hour, 0.0) + count
        if UNKNOWN in dims:
            degraded[bucket_hour] = degraded.get(bucket_hour, 0.0) + count
    return {
        bucket_hour: (degraded.get(bucket_hour, 0.0) / total if total > 0 else 0.0)
        for bucket_hour, total in totals.items()
    }


def build_rows(
    counts: Mapping[tuple[datetime, tuple[str, ...]], float],
    good_counts: Mapping[tuple[datetime, tuple[str, ...]], float],
    p75_values: Mapping[tuple[datetime, tuple[str, ...]], float],
    wanted_hours: Iterable[datetime],
) -> list[dict]:
    """組出 cwv_hourly 的列。sample_count == 0 的桶不落庫（見 docstring 保留期段）。"""
    unknown_ratios = compute_unknown_ratios(counts)
    hour_allowlist = set(wanted_hours)
    rows: list[dict] = []

    for key in sorted(counts, key=lambda item: (item[0], item[1])):
        bucket_hour, dims = key
        if bucket_hour not in hour_allowlist:
            continue
        sample_count = int(counts[key])
        if sample_count <= 0:
            continue
        p75 = p75_values.get(key)
        if p75 is None:
            # 有樣本卻取不到 p75（unwrap 全被過濾）——不猜值，跳過並讓 run 標 partial。
            logger.warning("跳過缺 p75 的桶：hour=%s dims=%s", bucket_hour.isoformat(), dims)
            continue
        row = {
            "hour": bucket_hour.isoformat().replace("+00:00", "Z"),
            "p75": max(float(p75), 0.0),
            "good_rate": min(max(good_counts.get(key, 0.0) / sample_count, 0.0), 1.0),
            "sample_count": sample_count,
            "unknown_ratio": min(max(unknown_ratios.get(bucket_hour, 0.0), 0.0), 1.0),
            "source": SOURCE,
        }
        row.update(dict(zip(LABEL_TO_COLUMN.values(), dims)))
        rows.append(row)
    return rows


def collect_rows(hours: Sequence[datetime]) -> tuple[list[dict], dict]:
    """對 Loki 跑三個查詢並聚合。回傳 (rows, stats)。"""
    window_start, window_end = hours[0], hours[-1] + timedelta(hours=1)
    stats = loki_index_stats(window_start, window_end)
    logger.info(
        "Loki index/stats %s → %s: streams=%s chunks=%s entries=%s bytes=%s",
        window_start.isoformat(), window_end.isoformat(),
        stats.get("streams"), stats.get("chunks"), stats.get("entries"), stats.get("bytes"),
    )
    if not stats.get("entries"):
        logger.warning(
            "該視窗索引內 0 筆。若視窗仍在 %dh 保留期內，代表真的沒流量；"
            "若已超出保留期，Loki 會靜默回空——本腳本已用 --backfill-hours <= %dh 排除後者。",
            LOKI_RETENTION_HOURS, MAX_BACKFILL_HOURS,
        )

    # 評估點 = bucket_hour + 1h（count_over_time 在 T 涵蓋 (T-1h, T]）
    eval_start = hours[0] + timedelta(hours=1)
    eval_end = hours[-1] + timedelta(hours=1)
    counts = parse_matrix(loki_query_range(build_count_query(), eval_start, eval_end))
    good_counts = parse_matrix(loki_query_range(build_count_query("good"), eval_start, eval_end))
    p75_values = parse_matrix(loki_query_range(build_p75_query(), eval_start, eval_end))

    rows = build_rows(counts, good_counts, p75_values, hours)
    stats = {
        "scanned_bytes": int(stats.get("bytes") or 0),
        "scanned_entries": int(stats.get("entries") or 0),
        "dimension_buckets": len(counts),
        "rows": len(rows),
        "hours_requested": len(hours),
        "hours_with_rows": len({row["hour"] for row in rows}),
        "unknown_ratio_by_hour": compute_unknown_ratios(counts),
    }
    return rows, stats


# ══════════════════════════════════════════════════════════════════════
# Supabase
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


def start_run(window_start: datetime, window_end: datetime) -> str | None:
    status, body = _supabase_request(
        "POST",
        f"/rest/v1/{TABLE_RUN}",
        body=[{
            "table_name": TABLE_CWV,
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


def upsert_rows(rows: Sequence[dict]) -> tuple[int, int]:
    """冪等 upsert。回傳 (成功列數, 失敗列數)。"""
    succeeded = failed = 0
    for offset in range(0, len(rows), UPSERT_BATCH_SIZE):
        batch = rows[offset : offset + UPSERT_BATCH_SIZE]
        status, body = _supabase_request(
            "POST",
            f"/rest/v1/{TABLE_CWV}?on_conflict={urllib.parse.quote(CONFLICT_KEY)}",
            body=list(batch),
            extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )
        if status in (200, 201, 204):
            succeeded += len(batch)
        else:
            failed += len(batch)
            logger.error("upsert 失敗：%s %s", status, body[:400])
    return succeeded, failed


def latest_success_hour() -> datetime | None:
    """cwv_hourly 最近一筆資料的 hour（新鮮度告警的觀測點）。"""
    status, body = _supabase_request(
        "GET", f"/rest/v1/{TABLE_CWV}?select=hour&order=hour.desc&limit=1"
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_CWV} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    if not payload:
        return None
    return datetime.fromisoformat(payload[0]["hour"].replace("Z", "+00:00"))


# ══════════════════════════════════════════════════════════════════════
# 執行模式
# ══════════════════════════════════════════════════════════════════════

def _log_summary(rows: Sequence[dict], stats: Mapping[str, Any]) -> None:
    logger.info(
        "聚合結果：%d 個維度組合 → %d 列（%d/%d 個小時有資料），掃描 %d 筆 / %.2f MB",
        stats["dimension_buckets"], stats["rows"], stats["hours_with_rows"],
        stats["hours_requested"], stats["scanned_entries"], stats["scanned_bytes"] / 1024 / 1024,
    )
    for bucket_hour, ratio in sorted(stats["unknown_ratio_by_hour"].items()):
        logger.info("  unknown_ratio %s = %.4f", bucket_hour.isoformat(), ratio)
    for row in rows[:8]:
        logger.info(
            "  %s %s/%s/%s/%s p75=%.4f good_rate=%.4f n=%d",
            row["hour"], row["environment"], row["metric"], row["route_type"],
            row["device"], row["p75"], row["good_rate"], row["sample_count"],
        )
    if len(rows) > 8:
        logger.info("  ...（其餘 %d 列略）", len(rows) - 8)


def run_ingestion(hours: Sequence[datetime], execute: bool) -> int:
    window_start, window_end = hours[0], hours[-1] + timedelta(hours=1)
    run_id = start_run(window_start, window_end) if execute else None
    try:
        rows, stats = collect_rows(hours)
    except LokiQueryError as exc:
        logger.error("Loki 查詢失敗：%s", exc)
        finish_run(run_id, "failed", 0)
        return 1

    _log_summary(rows, stats)

    if not execute:
        logger.info("[DRY RUN] 不寫入。加 --execute 才會 upsert %d 列。", len(rows))
        return 0

    succeeded, failed = upsert_rows(rows)
    skipped_hours = stats["hours_requested"] - stats["hours_with_rows"]
    if failed:
        run_status = "failed" if not succeeded else "partial"
    elif skipped_hours:
        run_status = "partial"
    else:
        run_status = "success"
    if skipped_hours:
        written = {row["hour"] for row in rows}
        missing = [h.isoformat() for h in hours if h.isoformat().replace("+00:00", "Z") not in written]
        logger.warning("以下小時無資料、未落庫（status=partial）：%s", ", ".join(missing))
    finish_run(run_id, run_status, succeeded)
    logger.info("寫入完成：%d 列成功 / %d 列失敗，run status=%s", succeeded, failed, run_status)
    return 1 if failed else 0


def run_verify() -> int:
    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_CWV}?select=hour,environment,metric,route_type,device,p75,"
        "good_rate,sample_count,unknown_ratio&order=hour.desc&limit=5",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_CWV, status, body[:300])
        return 1
    recent = json.loads(body)
    logger.info("cwv_hourly 最新 %d 列：", len(recent))
    for row in recent:
        aligned = row["hour"].endswith((":00:00+00:00", ":00:00Z", ":00:00+00"))
        logger.info("  %s aligned=%s %s/%s n=%d p75=%s unknown_ratio=%s",
                    row["hour"], aligned, row["environment"], row["metric"],
                    row["sample_count"], row["p75"], row["unknown_ratio"])

    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_RUN}?select=id,window_start,window_end,row_count,status,"
        f"started_at,finished_at&table_name=eq.{TABLE_CWV}&order=started_at.desc&limit=3",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_RUN, status, body[:300])
        return 1
    for run in json.loads(body):
        logger.info("  run %s %s..%s status=%s rows=%d finished=%s",
                    run["id"][:8], run["window_start"], run["window_end"],
                    run["status"], run["row_count"], run["finished_at"])
    return 0


def run_freshness_check() -> int:
    """資料新鮮度告警。stale 或空表回 exit 1，讓 Actions 失敗並發通知。

    條件刻意是「cwv_hourly 最近一次成功寫入超過門檻」，不是「作業有沒有回報失敗」——
    排程整個沒被觸發時不會有任何失敗訊號，只有資料的缺席能證明它沒在跑。
    """
    latest = latest_success_hour()
    if latest is None:
        logger.error("FAIL: cwv_hourly 是空的，聚合作業從未成功寫入。")
        return 1
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    if age_hours > FRESHNESS_MAX_AGE_HOURS:
        logger.error(
            "FAIL: cwv_hourly 最新資料 %s，已 %.1f 小時未更新（門檻 %dh）。"
            "來源 Loki retention 僅 %dh，停擺超過該期限資料永久遺失。",
            latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS, LOKI_RETENTION_HOURS,
        )
        return 1
    logger.info("PASS: cwv_hourly 最新資料 %s（%.1f 小時前，門檻 %dh）。",
                latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS)
    return 0


def resolve_hours(
    backfill_hours: int | None,
    until: datetime | None = None,
    now: datetime | None = None,
) -> list[datetime]:
    """算出要處理的整點小時清單。

    `until` 是視窗的**新端**（預設 = 現在），讓回填可以錨定到過去補洞，
    而不是只能從現在往回加大跨度——後者遇到「窄但舊」的缺口會構不到。
    """
    now = now or datetime.now(timezone.utc)
    lookback = backfill_hours if backfill_hours is not None else DEFAULT_LOOKBACK_HOURS
    if lookback < 1:
        raise ValueError("--backfill-hours 必須 >= 1")
    if lookback > MAX_BACKFILL_HOURS:
        raise ValueError(
            f"--backfill-hours {lookback} 超過單次跨度上限 {MAX_BACKFILL_HOURS}。"
            f"這道門檻只防打錯字；真正的保留期防線是 MAX_AGE_HOURS={MAX_AGE_HOURS}h 的絕對時間檢查。"
            f"要補更寬的缺口請分批，並用 --backfill-until 錨定每一批的新端。"
        )

    anchor = truncate_to_hour(until) if until else now
    if until and anchor > truncate_to_hour(now):
        raise ValueError(
            f"--backfill-until {anchor.isoformat()} 在未來。"
            f"未結束的小時是半滿的桶，寫進去無法與完整小時區分（見設計決定 1）。"
        )
    hours = complete_hours(anchor, lookback)

    age_hours = (truncate_to_hour(now) - hours[0]).total_seconds() / 3600
    if age_hours > MAX_AGE_HOURS:
        raise ValueError(
            f"最舊的目標小時 {hours[0].isoformat()} 距今 {age_hours:.0f}h，"
            f"超過 MAX_AGE_HOURS={MAX_AGE_HOURS}h（retention {LOKI_RETENTION_HOURS}h "
            f"減 {RETENTION_SAFETY_MARGIN_HOURS}h 安全邊界）。"
            f"超出保留期的查詢會回 HTTP 200 + 全零而不是報錯——這一段已經救不回來，"
            f"硬跑只會把空資料寫進歷史。"
        )
    return hours


def main() -> None:
    parser = argparse.ArgumentParser(description="把 Loki web-vitals RUM 逐小時聚合寫進 Supabase cwv_hourly")
    parser.add_argument("--dry-run", action="store_true", help="查 Loki、算完、印摘要但不寫庫（預設）")
    parser.add_argument("--execute", action="store_true", help="實際 upsert 進 Supabase")
    parser.add_argument("--verify", action="store_true", help="唯讀檢查最近寫入狀態")
    parser.add_argument("--check-freshness", action="store_true",
                        help=f"新鮮度告警：cwv_hourly 最新資料超過 {FRESHNESS_MAX_AGE_HOURS}h 則 exit 1")
    parser.add_argument("--backfill-hours", type=int, default=None,
                        help=f"回填 N 個完整小時（預設 {DEFAULT_LOOKBACK_HOURS}，單次跨度上限 {MAX_BACKFILL_HOURS}）")
    parser.add_argument("--backfill-until", type=str, default=None,
                        help="視窗新端的 ISO 時間（預設為現在）。補歷史缺口時錨定用，"
                             f"例如 --backfill-until 2026-08-30T07:00:00Z --backfill-hours 34。"
                             f"最舊的目標小時距今不得超過 {MAX_AGE_HOURS}h。")
    args = parser.parse_args()

    if args.verify:
        sys.exit(run_verify())
    if args.check_freshness:
        sys.exit(run_freshness_check())

    try:
        until = parse_iso_hour(args.backfill_until) if args.backfill_until else None
        hours = resolve_hours(args.backfill_hours, until=until)
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(2)

    logger.info("目標小時（UTC，皆為已結束的完整小時）：%s .. %s，共 %d 個",
                hours[0].isoformat(), hours[-1].isoformat(), len(hours))
    if not args.execute:
        logger.info("預設為 dry-run，加 --execute 才會寫入。")
    sys.exit(run_ingestion(hours, execute=args.execute))


if __name__ == "__main__":
    main()
