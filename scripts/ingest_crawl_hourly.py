r"""
ingest_crawl_hourly.py — 把 Loki 的 envoy access log 逐小時聚合寫進 Supabase crawl_daily

資料流：Loki（Grafana datasource proxy）→ 逐小時 × (ua_group, status, path_prefix) 聚合
        → Supabase PostgREST upsert → 掃掉同視窗的過期列

用法：
  python scripts/ingest_crawl_hourly.py --dry-run             # 查 Loki、算完、印摘要，不寫庫（預設）
  python scripts/ingest_crawl_hourly.py --execute             # 實際 upsert
  python scripts/ingest_crawl_hourly.py --verify              # 唯讀檢查最近寫入狀態
  python scripts/ingest_crawl_hourly.py --execute --backfill-hours 24
  python scripts/ingest_crawl_hourly.py --check-freshness     # 新鮮度告警：stale 則 exit 1

環境變數：GRAFANA_URL / GRAFANA_SERVICE_ACCOUNT_TOKEN /
          CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET / SUPABASE_URL / SUPABASE_SERVICE_KEY


═══ 為什麼這支存在 ═══

Search Console API v1 沒有 Crawl Stats resource，GSC 介面上那份「檢索統計」抓不下來，
而且它**只涵蓋 Googlebot**。AI crawler 抓了多少、抓了哪些區塊、拿到什麼狀態碼，
只有我們自己的 access log 知道。Loki 的 retention 是 168h，所以這件事不逐小時落庫，
每 7 天就歸零一次。


═══ 隱私 ═══

只寫**彙總後的計數**：(date, hour, ua_group, status_code, path_prefix) → request_count / bytes。
不寫原始 log 行、不寫 IP、不寫完整 UA 字串（ua_group 是我們自己定義的分群標籤）。
順帶一提 envoy 這條 stream 的 log line 裡本來就沒有 IP 欄位，
但「因為來源剛好沒有」不是控制措施，聚合才是——欄位哪天被加回來也不會外洩。


═══ 設計決定 ═══

【1. 逐小時 instant query，不用 query_range】
實測（2026-09-01，經 Grafana proxy）：`query_range` 即使只跨 1 小時、step=1h，
也會在 **30.5 秒**回 HTTP 502——那是 proxy 的 wall clock 上限，不是 Loki 的門檻。
兩個評估點等於兩倍工，直接超時。改用 instant query（`/query` + `[1h]`），
一次一個桶、語意明確，實測 12.8s 完成。

這代表本腳本的 binding constraint 是 **proxy 的 ~30s**，比 Loki 那三道門檻都先撞到。
每個小時要跑 4 個查詢（見設計決定 2），約 37s，所以回填 N 小時 ≈ N×37s。

【2. 四個查詢，human 桶用相減得到】
  A crawler counts  `| json | user_agent =~ <crawler 樣式> | label_format ...`  ~12.8s
  B crawler bytes   同上 + `| unwrap bytes_sent`                                ~12.9s
  C total counts    `| json | label_format <只有 path>`（不分 UA）              ~5.4s
  D total bytes     同上 + unwrap                                               ~5.5s

  human[(status, prefix)] = total[(status, prefix)] − Σ crawler[(status, prefix)]

為什麼不直接對全流量做 UA 分群：那要對 157k 行都跑 UA regex，實測 20-23s，
貼著 30s 的 proxy 上限，流量高一點的小時就會翻車。C/D 只跑一個 path regex，5.4s 有餘裕。

（分群、路徑分桶、LogQL 片段與其設計決定見 scripts/crawl_taxonomy.py）

【3. bytes 存 bytes_sent，不存 origin_content_length】
`origin_content_length` **只在 status 200 的行有值**，3xx/4xx 全是 null，
unwrap 會直接把那些行丟掉。存它會讓 bytes 欄在狀態碼之間不可比，而且 3xx/4xx 靜默變 0。
015 自己對這一欄的註解寫「bytes 可以是 0（例如 304 Not Modified 沒有 body）」——
那正是 bytes_sent（實際送出的 wire bytes）的語意。
`origin_content_length` 的分佈改放 Grafana dashboard（Loki live，168h 內），
它回答的是「原站吐了多大的 HTML」，跟「傳輸成本」是兩個問題。

（Supabase 寫入、過期列清掃、分頁讀回的設計決定見 scripts/crawl_warehouse.py）

【4. 保留期防線用絕對時間】
超出 retention 的查詢回 HTTP 200 + 全零、不報錯，跟「那小時真的沒流量」長得一模一樣。
跨度上限擋不住這件事：一段只有 12h 寬、但起點在 200h 前的視窗，跨度合格卻整段在保留期外。
真正該檢查的是「最舊的目標小時距今多久」= MAX_AGE_HOURS。
MAX_BACKFILL_HOURS 只是防打錯字的第二道，不要拿它當保留期防線。

【5. | json 後一定接 __error__=""，否則整條查詢 400 死】
`{job="loki.source.kubernetes.envoy_proxy"}` 這個 job label 不是只有 envoy access log——
gateway pod 裡的 shutdown-manager sidecar（滾動部署時的 drain 流程）也共用同一個 job，
但吐的是純文字行（`2026-09-01T19:54:44Z\tINFO\tshutdown-manager\t...`），不是 JSON。
`| json` 遇到這種行會標成 `__error__="JSONParserErr"`；Loki 的 metric 查詢
（count_over_time / sum_over_time 這類）對未過濾的 pipeline error 是硬失敗、回 HTTP 400，
不是「這行跳過、其他行照算」。實測（2026-09-02，2026-09-01T19:00Z 那小時）：
60,652 行 access log 對 18 行 shutdown-manager（0.03%），集中在該小時剛好有 gateway
滾動部署、pod 收到 SIGTERM 開始 drain 的時間點——查詢語法沒錯，是同 job 混進了另一個
container 的非 JSON 流，而且只要那小時發生過部署，重跑幾次都會撞同一批行，长得像
「特定小時必死」而非 flaky。修法：`_crawler_pipeline()` / `_total_pipeline()` 都在
`| json` 後緊接 `| __error__=""`；被濾掉的行數另外查一次、記警告（見
`count_dropped_lines()`），不能靜默丟棄——這個比例哪天從 0.03% 漲到兩位數，
代表壞的不是 sidecar 雜訊而是 access log 本身，要停下來查，不能繼續濾。


═══ Loki 硬約束（四種失敗長得不一樣，status code 分不出來）═══

  max_query_length     170h（時間窗 + range selector 加總計法）
  max_query_bytes_read 3GB（pre-flight 拒絕）
  max_series           500（回應層硬門檻）
  proxy wall clock     ~30s（HTTP 502，不是 Loki 的門檻）
  retention_period     168h（超出回 HTTP 200 + 全零，靜默）

實測（2026-09-01，經 Grafana proxy）：

  171h 窗 + [1h]       → HTTP 400  the query time range exceeds the limit
  170h 窗 + [1h]       → HTTP 500  Failed to get bytes read stats ... rpc error 400（內層 400 被包成 500）
  全流量 sum by (path) → HTTP 400  maximum number of series (500) reached for a single query
  query_range 1h       → HTTP 502  error code: 502（30.5s，body 不是 JSON）
  30 天前 1h 窗        → HTTP 200  result=[]（靜默）

=> 同一種違規會依「哪一層先攔到」吐出 400 或 500；502 甚至不是 Loki 回的。
   一定要看訊息內容，classify_loki_error() 就是幹這件事。

單一小時的量級（2026-09-01 08:00Z 實測）：157,148 行 / 113MB / crawler 佔 5.2%。
=> 24h ≈ 2.7GB，貼著 3GB 的 bytes 門檻，所以絕不可整天一次查。
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
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

from crawl_taxonomy import (  # noqa: E402  （同目錄模組，路徑由上方 sys.path 保證）
    build_crawler_ua_pattern,
    build_mobile_expr,
    build_path_prefix_expr,
    build_ua_token_expr,
    classify,
    human_identity,
    normalize_path_prefix,
    parse_status_code,
)
from crawl_warehouse import (  # noqa: E402
    TABLE_CRAWL,
    count_exact,
    finish_run,
    iso_z,
    latest_bucket_hour,
    select_all,
    start_run,
    sweep_stale,
    upsert_rows,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── Loki ────────────────────────────────────────────────────────────────
LOKI_DATASOURCE_UID = "ffhwhnr95ygaof"  # "Loki (Production)"；staging 是 cfhwdain1kwsgc
LOKI_PROXY_PATH = "/api/datasources/proxy/uid/{uid}/loki/api/v1"
LOKI_JOB = "loki.source.kubernetes.envoy_proxy"
LOKI_RETENTION_HOURS = 168
LOKI_MAX_SERIES = 500
# 逼近 max_series 時先出聲。撞上去是 HTTP 400 整個查詢死，不是截斷，
# 所以要在還有餘裕時就知道 allowlist 或 token 表該收斂了。
SERIES_WARN_RATIO = 0.8
# proxy 在 ~30s 回 502，等更久沒有意義；留一點餘裕給連線建立。
HTTP_TIMEOUT_SECONDS = 90
USER_AGENT = "seo-knowledge-insight-crawl-ingest/1.0"

BUCKET = "1h"
DEFAULT_LOOKBACK_HOURS = 2
# 每小時 4 個查詢約 37s，24h 回填約 15 分鐘。這道門檻只防打錯字，
# 真正的保留期防線是 MAX_AGE_HOURS（見 crawl_warehouse.py 設計決定 1）。
MAX_BACKFILL_HOURS = 24
RETENTION_SAFETY_MARGIN_HOURS = 24
MAX_AGE_HOURS = LOKI_RETENTION_HOURS - RETENTION_SAFETY_MARGIN_HOURS  # 144

FRESHNESS_MAX_AGE_HOURS = 3  # 排程週期 1h 的 3 倍

# 被 __error__="" 濾掉的行數 ÷ 全流量請求數 的警戒線。超過就代表壞行不是零星
# sidecar 雜訊、該停下來查，不能繼續濾。見設計決定 5。
DROPPED_LINE_WARN_RATIO = 0.01

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
    return moment.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def complete_hours(now: datetime, count: int) -> list[datetime]:
    """now 之前 count 個「已完整結束」的整點小時，由舊到新。

    當前這個未結束的小時一律不含：半滿的桶寫進去之後，沒有任何欄位能表達
    「這一小時只收了半小時的樣本」，下游會把它當完整小時。
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

def _crawler_pipeline() -> str:
    """`| json` 後緊接 `__error__=""`：job 裡混著非 JSON 的 sidecar 行，見設計決定 5。"""
    return (
        f'{{job="{LOKI_JOB}"}} | json | __error__="" '
        f"| user_agent =~ `{build_crawler_ua_pattern()}` "
        f"| label_format {build_ua_token_expr()}, {build_mobile_expr()}, "
        f"{build_path_prefix_expr()}"
    )


def _total_pipeline() -> str:
    """全流量只抽 path，不碰 UA —— 對 157k 行跑 UA regex 會貼上 30s 的 proxy 上限。

    `| json` 後緊接 `__error__=""`：job 裡混著非 JSON 的 sidecar 行，見設計決定 5。
    """
    return f'{{job="{LOKI_JOB}"}} | json | __error__="" | label_format {build_path_prefix_expr()}'


def _dropped_line_query() -> str:
    """統計因 JSON 解析失敗被 __error__="" 濾掉的行數，純診斷用，不影響落庫的統計值。"""
    return f'sum(count_over_time({{job="{LOKI_JOB}"}} | json | __error__="JSONParserErr" [{BUCKET}]))'


def build_crawler_count_query() -> str:
    return f"sum by (token, mob, status, pfx) (count_over_time({_crawler_pipeline()} [{BUCKET}]))"


def build_crawler_bytes_query() -> str:
    return (
        f"sum by (token, mob, status, pfx) "
        f"(sum_over_time({_crawler_pipeline()} | unwrap bytes_sent [{BUCKET}]))"
    )


def build_total_count_query() -> str:
    return f"sum by (status, pfx) (count_over_time({_total_pipeline()} [{BUCKET}]))"


def build_total_bytes_query() -> str:
    return (
        f"sum by (status, pfx) "
        f"(sum_over_time({_total_pipeline()} | unwrap bytes_sent [{BUCKET}]))"
    )


# ══════════════════════════════════════════════════════════════════════
# Loki HTTP
# ══════════════════════════════════════════════════════════════════════

def classify_loki_error(status: int, body: str) -> LokiQueryError:
    """把失敗回應分類成可行動的類別。status code 分不出來，一定要看訊息。"""
    lowered = body.lower()
    if "maximum number of series" in lowered or "max_series" in lowered:
        return LokiQueryError(
            "series-limit",
            f"HTTP {status}: 查詢被 max_series ({LOKI_MAX_SERIES}) 拒絕。{body[:300]}",
            "這是回應層的硬門檻不是截斷，整個查詢會死。收斂 PATH_SEGMENTS 或 "
            "TOKEN_TO_UA_GROUP 的桶數；若是 path 維度爆掉，檢查 build_path_prefix_expr() "
            "的 allowlist 是否失效（樣式打錯會讓每個路徑各自成桶）。",
        )
    if "too many bytes" in lowered or "max_query_bytes_read" in lowered:
        return LokiQueryError(
            "bytes-limit",
            f"HTTP {status}: 查詢被 max_query_bytes_read (3GB) pre-flight 拒絕。{body[:300]}",
            "本腳本逐小時查，單小時實測約 113MB。撞到這個門檻代表 BUCKET 被改大，"
            "或上游流量暴增到單小時超過 3GB（那要先查來源，不是放寬門檻）。",
        )
    if "query length" in lowered or "time range exceeds" in lowered:
        return LokiQueryError(
            "length-limit",
            f"HTTP {status}: 查詢被 max_query_length (170h) 拒絕。{body[:300]}",
            f"length 的算法是「時間窗 + range selector」加總。本腳本用 instant query + "
            f"[{BUCKET}]，正常不可能撞到；出現代表 BUCKET 常數被改壞。",
        )
    if "jsonparsererr" in lowered or "pipeline error" in lowered:
        return LokiQueryError(
            "json-parse-pipeline-error",
            f"HTTP {status}: | json 遇到非 JSON 行，metric 查詢對未過濾的 pipeline error "
            f"是硬失敗。{body[:300]}",
            "正常情況下 _crawler_pipeline() / _total_pipeline() 已經在 | json 後接了 "
            "__error__=\"\"，不該再撞到這個。出現代表濾網被改掉，或新的非 JSON 來源用了 "
            "跟 __error__=\"JSONParserErr\" 不同的錯誤類別（見設計決定 5）。",
        )
    if status in (502, 503, 504) or "error code: 502" in lowered:
        return LokiQueryError(
            "proxy-timeout",
            f"HTTP {status}: Grafana/Cloudflare proxy 逾時（實測上限約 30s）。{body[:200]}",
            "這不是 Loki 的門檻，是 proxy 的 wall clock。單一小時的查詢實測 12.8s，"
            "撞到代表該小時流量遠高於平常、或 Loki 正在降速。重試通常有效；"
            "持續發生要縮小 BUCKET 或改走非 proxy 路徑。",
        )
    return LokiQueryError(
        "unknown",
        f"HTTP {status}: {body[:300]}",
        "非已知門檻錯誤，檢查 Grafana 憑證、CF Access header 與 datasource UID。"
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
    """視窗的索引統計。超出 retention 時全零——「靜默回空」唯一的事前訊號。"""
    return _loki_get(
        "/index/stats",
        {"query": f'{{job="{LOKI_JOB}"}}', "start": to_nanoseconds(start), "end": to_nanoseconds(end)},
    )


def loki_instant(query: str, moment: datetime) -> list[dict]:
    """instant query。`[1h]` 在時間 T 涵蓋 (T-1h, T]，所以 moment 要傳桶的**結束**時刻。"""
    payload = _loki_get("/query", {"query": query, "time": to_nanoseconds(moment)})
    result = payload.get("data", {}).get("result", [])
    if len(result) >= LOKI_MAX_SERIES * SERIES_WARN_RATIO:
        logger.warning(
            "回傳 %d 個 series，已達 max_series (%d) 的 %.0f%%。"
            "撞上去是 HTTP 400 整個查詢死、不是截斷，該收斂分桶了。",
            len(result), LOKI_MAX_SERIES, 100 * len(result) / LOKI_MAX_SERIES,
        )
    return result


def _series_value(series: Mapping[str, Any]) -> float:
    raw = series.get("value")
    if not raw or len(raw) < 2:
        return 0.0
    try:
        return float(raw[1])
    except (TypeError, ValueError):
        return 0.0


def count_dropped_lines(moment: datetime) -> int:
    """回傳這個小時被 __error__="JSONParserErr" 濾掉的行數（見設計決定 5）。

    這條查詢本身失敗不該拖垮主流程——它是可見度用的，不是資料正確性所需——
    所以失敗時記警告、回 0，讓 ingestion 照跑。
    """
    try:
        result = loki_instant(_dropped_line_query(), moment)
    except LokiQueryError as exc:
        logger.warning("被過濾行數查詢失敗，這小時無法回報濾掉多少行：%s", exc)
        return 0
    return int(sum(_series_value(item) for item in result))


# ══════════════════════════════════════════════════════════════════════
# 聚合
# ══════════════════════════════════════════════════════════════════════

def fold_crawler(
    series: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str, int, str], float]:
    """crawler 查詢的 series → {(ua_name, ua_group, status_code, path_prefix): value}。

    ua_group 由 ua_name 唯一決定（classify 一次回傳兩者），所以把它放進 key
    不會讓同一支 bot 裂成兩列；它在這裡只是順路帶著走到 payload。

    多個 label 組合可能收斂到同一個 ua_name（例如同一支 bot 的不同 Chrome 版本
    外殼），所以是累加不是覆寫。
    """
    folded: dict[tuple[str, str, int, str], float] = {}
    for item in series:
        labels = item.get("metric", {})
        status_code = parse_status_code(labels.get("status", ""))
        if status_code is None:
            continue
        ua_name, ua_group = classify(labels.get("token", ""), labels.get("mob", ""))
        key = (ua_name, ua_group, status_code, normalize_path_prefix(labels.get("pfx", "")))
        folded[key] = folded.get(key, 0.0) + _series_value(item)
    return folded


def fold_total(series: Sequence[Mapping[str, Any]]) -> dict[tuple[int, str], float]:
    """全流量查詢的 series → {(status_code, path_prefix): value}。"""
    folded: dict[tuple[int, str], float] = {}
    for item in series:
        labels = item.get("metric", {})
        status_code = parse_status_code(labels.get("status", ""))
        if status_code is None:
            continue
        key = (status_code, normalize_path_prefix(labels.get("pfx", "")))
        folded[key] = folded.get(key, 0.0) + _series_value(item)
    return folded


def derive_human(
    total: Mapping[tuple[int, str], float],
    crawler: Mapping[tuple[str, int, str], float],
) -> dict[tuple[int, str], float]:
    """human = 全流量 − 所有 crawler 桶（見設計決定 2）。

    負值一律夾到 0：兩個查詢是分開送的，中間有幾百毫秒的時間差，
    邊界上的行可能只被其中一個查詢看到。夾到 0 比寫負數誠實——
    crawl_daily_request_count_ck 也不收負數。
    """
    crawler_by_dim: dict[tuple[int, str], float] = {}
    for (_, _, status_code, path_prefix), value in crawler.items():
        dim = (status_code, path_prefix)
        crawler_by_dim[dim] = crawler_by_dim.get(dim, 0.0) + value
    return {
        dim: max(value - crawler_by_dim.get(dim, 0.0), 0.0)
        for dim, value in total.items()
    }


def build_rows(bucket_hour: datetime, counts: Mapping, byte_sums: Mapping, human_counts: Mapping,
               human_bytes: Mapping) -> list[dict]:
    """組出 crawl_daily 的列。request_count == 0 的桶不落庫（CHECK 要求 > 0）。"""
    rows: list[dict] = []
    for key, count in sorted(counts.items()):
        ua_name, ua_group, status_code, path_prefix = key
        rows.append(_row(bucket_hour, ua_name, ua_group, status_code, path_prefix,
                         count, byte_sums.get(key, 0.0)))
    human_name, human_group = human_identity()
    for (status_code, path_prefix), count in sorted(human_counts.items()):
        rows.append(_row(bucket_hour, human_name, human_group, status_code, path_prefix,
                         count, human_bytes.get((status_code, path_prefix), 0.0)))
    return [row for row in rows if row is not None]


def _row(bucket_hour: datetime, ua_name: str, ua_group: str, status_code: int,
         path_prefix: str, count: float, byte_sum: float) -> dict | None:
    request_count = int(count)
    if request_count <= 0:
        return None
    return {
        "date": bucket_hour.date().isoformat(),
        "hour": bucket_hour.hour,
        "ua_name": ua_name,
        "ua_group": ua_group,
        "status_code": status_code,
        "path_prefix": path_prefix,
        "request_count": request_count,
        "bytes": max(int(byte_sum), 0),
    }


def collect_hour(bucket_hour: datetime) -> tuple[list[dict], dict]:
    """對單一小時跑四個查詢並聚合。回傳 (rows, stats)。"""
    window_end = bucket_hour + timedelta(hours=1)
    stats = loki_index_stats(bucket_hour, window_end)
    if not stats.get("entries"):
        logger.warning(
            "%s 該小時索引內 0 筆。若仍在 %dh 保留期內代表真的沒流量；"
            "超出保留期時 Loki 會靜默回空——已由 MAX_AGE_HOURS=%dh 的絕對時間檢查排除後者。",
            iso_z(bucket_hour), LOKI_RETENTION_HOURS, MAX_AGE_HOURS,
        )

    crawler_counts = fold_crawler(loki_instant(build_crawler_count_query(), window_end))
    crawler_bytes = fold_crawler(loki_instant(build_crawler_bytes_query(), window_end))
    total_counts = fold_total(loki_instant(build_total_count_query(), window_end))
    total_bytes = fold_total(loki_instant(build_total_bytes_query(), window_end))
    dropped_lines = count_dropped_lines(window_end)

    human_counts = derive_human(total_counts, crawler_counts)
    human_bytes = derive_human(total_bytes, crawler_bytes)
    rows = build_rows(bucket_hour, crawler_counts, crawler_bytes, human_counts, human_bytes)
    total_requests = int(sum(total_counts.values()))
    _warn_if_dropped_share_high(bucket_hour, dropped_lines, total_requests)
    return rows, {
        "scanned_bytes": int(stats.get("bytes") or 0),
        "scanned_entries": int(stats.get("entries") or 0),
        "crawler_requests": int(sum(crawler_counts.values())),
        "total_requests": total_requests,
        "dropped_lines": dropped_lines,
        "rows": len(rows),
    }


def _warn_if_dropped_share_high(bucket_hour: datetime, dropped_lines: int, total_requests: int) -> None:
    """被 __error__="" 濾掉的行不能靜默——固定記一筆；比例一旦偏高才升級成警告。

    0.03% 這個實測值是 gateway 滾動部署時 shutdown-manager sidecar 混進同一個 job 的
    雜訊（見設計決定 5）。DROPPED_LINE_WARN_RATIO 抓 1% 當警戒線：一旦被濾行數量級
    從「零星 sidecar 行」變成「一整類請求」，代表 access log 本身壞了，要停下來查，
    不能繼續濾掉了事。
    """
    if dropped_lines <= 0:
        return
    share = dropped_lines / total_requests if total_requests else 1.0
    log = logger.warning if share >= DROPPED_LINE_WARN_RATIO else logger.info
    log(
        "%s 有 %d 行因 JSON 解析失敗被 __error__=\"\" 濾掉（佔全流量 %.3f%%）。",
        iso_z(bucket_hour), dropped_lines, 100 * share,
    )


# ══════════════════════════════════════════════════════════════════════
# 執行模式
# ══════════════════════════════════════════════════════════════════════

def _log_hour_summary(bucket_hour: datetime, rows: Sequence[dict], stats: Mapping[str, Any]) -> None:
    by_group: dict[str, int] = {}
    for row in rows:
        by_group[row["ua_group"]] = by_group.get(row["ua_group"], 0) + row["request_count"]
    crawler_share = (
        100 * stats["crawler_requests"] / stats["total_requests"]
        if stats["total_requests"] else 0.0
    )
    logger.info(
        "%s → %d 列；全流量 %d、crawler %d（%.1f%%），掃描 %.1f MB",
        iso_z(bucket_hour), stats["rows"], stats["total_requests"],
        stats["crawler_requests"], crawler_share, stats["scanned_bytes"] / 1024 / 1024,
    )
    for group, count in sorted(by_group.items(), key=lambda item: -item[1]):
        logger.info("    %-20s %8d", group, count)


def run_ingestion(hours: Sequence[datetime], execute: bool) -> int:
    ingested_at = datetime.now(timezone.utc)
    window_start, window_end = hours[0], hours[-1] + timedelta(hours=1)
    run_id = start_run(window_start, window_end) if execute else None
    total_written = total_failed = 0
    empty_hours: list[str] = []

    for bucket_hour in hours:
        try:
            rows, stats = collect_hour(bucket_hour)
        except LokiQueryError as exc:
            logger.error("Loki 查詢失敗（%s）：%s", iso_z(bucket_hour), exc)
            finish_run(run_id, "failed", total_written)
            return 1
        _log_hour_summary(bucket_hour, rows, stats)
        if not rows:
            empty_hours.append(iso_z(bucket_hour))
            continue
        if not execute:
            continue
        succeeded, failed = upsert_rows(rows, ingested_at)
        total_written += succeeded
        total_failed += failed
        if not failed:
            sweep_stale(bucket_hour, ingested_at)

    if not execute:
        logger.info("[DRY RUN] 不寫入。加 --execute 才會 upsert。")
        return 0
    run_status = _run_status(total_written, total_failed, empty_hours)
    if empty_hours:
        logger.warning("以下小時無資料、未落庫（status=partial）：%s", ", ".join(empty_hours))
    finish_run(run_id, run_status, total_written)
    logger.info("寫入完成：%d 列成功 / %d 列失敗，run status=%s",
                total_written, total_failed, run_status)
    return 1 if total_failed else 0


def _run_status(written: int, failed: int, empty_hours: Sequence[str]) -> str:
    if failed and not written:
        return "failed"
    if failed or empty_hours:
        return "partial"
    return "success"


def run_verify() -> int:
    """讀回驗證。一律走 Range 分頁 + count=exact，不靠 query-string 的 limit。"""
    latest = latest_bucket_hour()
    if latest is None:
        logger.error("crawl_daily 是空的。")
        return 1
    date_key = latest.date().isoformat()
    base = f"/rest/v1/{TABLE_CRAWL}?date=eq.{date_key}"
    exact = count_exact(f"{base}&select=date")
    rows = select_all(
        f"{base}&select=hour,ua_name,ua_group,status_code,path_prefix,request_count,bytes"
        "&order=hour.asc,ua_name.asc"
    )
    logger.info("crawl_daily %s：count=exact %d 列，分頁讀回 %d 列（相符=%s）",
                date_key, exact, len(rows), exact == len(rows))
    by_group: dict[str, int] = {}
    for row in rows:
        by_group[row["ua_group"]] = by_group.get(row["ua_group"], 0) + row["request_count"]
    logger.info("  涵蓋小時：%s", sorted({row["hour"] for row in rows}))
    logger.info("  具名 bot 數（ua_name）：%d", len({row["ua_name"] for row in rows}))
    logger.info("  ua_group 分群數：%d", len(by_group))
    for group, count in sorted(by_group.items(), key=lambda item: -item[1]):
        logger.info("    %-20s %8d requests", group, count)
    return 0


def run_freshness_check() -> int:
    """資料新鮮度告警。stale 或空表回 exit 1。

    條件刻意是「crawl_daily 最近一筆資料超過門檻」，不是「作業有沒有回報失敗」——
    排程整個沒被觸發時不會有任何失敗訊號，只有資料的缺席能證明它沒在跑。
    健康時這個條件不成立（正常每小時都有新資料），所以它是告警不是指標。
    """
    latest = latest_bucket_hour()
    if latest is None:
        logger.error("FAIL: crawl_daily 是空的，聚合作業從未成功寫入。")
        return 1
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    if age_hours > FRESHNESS_MAX_AGE_HOURS:
        logger.error(
            "FAIL: crawl_daily 最新資料 %s，已 %.1f 小時未更新（門檻 %dh）。"
            "來源 Loki retention 僅 %dh，停擺超過該期限資料永久遺失且無法回填。",
            iso_z(latest), age_hours, FRESHNESS_MAX_AGE_HOURS, LOKI_RETENTION_HOURS,
        )
        return 1
    logger.info("PASS: crawl_daily 最新資料 %s（%.1f 小時前，門檻 %dh）。",
                iso_z(latest), age_hours, FRESHNESS_MAX_AGE_HOURS)
    return 0


def resolve_hours(backfill_hours: int | None, until: datetime | None = None,
                  now: datetime | None = None) -> list[datetime]:
    """算出要處理的整點小時清單。`until` 是視窗的新端（預設現在），用來錨定補洞。"""
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
            f"--backfill-until {iso_z(anchor)} 在未來。未結束的小時是半滿的桶，"
            f"寫進去無法與完整小時區分。"
        )
    hours = complete_hours(anchor, lookback)
    age_hours = (truncate_to_hour(now) - hours[0]).total_seconds() / 3600
    if age_hours > MAX_AGE_HOURS:
        raise ValueError(
            f"最舊的目標小時 {iso_z(hours[0])} 距今 {age_hours:.0f}h，"
            f"超過 MAX_AGE_HOURS={MAX_AGE_HOURS}h（retention {LOKI_RETENTION_HOURS}h "
            f"減 {RETENTION_SAFETY_MARGIN_HOURS}h 安全邊界）。"
            f"超出保留期的查詢會回 HTTP 200 + 全零而不是報錯——這一段已經救不回來，"
            f"硬跑只會把空資料寫進歷史。"
        )
    return hours


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把 Loki envoy access log 逐小時聚合寫進 Supabase crawl_daily"
    )
    parser.add_argument("--dry-run", action="store_true", help="查 Loki、算完、印摘要但不寫庫（預設）")
    parser.add_argument("--execute", action="store_true", help="實際 upsert 進 Supabase")
    parser.add_argument("--verify", action="store_true", help="唯讀讀回驗證（Range 分頁 + count=exact）")
    parser.add_argument("--check-freshness", action="store_true",
                        help=f"新鮮度告警：最新資料超過 {FRESHNESS_MAX_AGE_HOURS}h 則 exit 1")
    parser.add_argument("--backfill-hours", type=int, default=None,
                        help=f"回填 N 個完整小時（預設 {DEFAULT_LOOKBACK_HOURS}，上限 {MAX_BACKFILL_HOURS}）")
    parser.add_argument("--backfill-until", type=str, default=None,
                        help=f"視窗新端的 ISO 時間（預設現在）。最舊的目標小時距今不得超過 {MAX_AGE_HOURS}h。")
    return parser


def main() -> None:
    args = build_parser().parse_args()
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
    logger.info("目標小時（UTC，皆為已結束的完整小時）：%s .. %s，共 %d 個（每小時約 37s）",
                iso_z(hours[0]), iso_z(hours[-1]), len(hours))
    if not args.execute:
        logger.info("預設為 dry-run，加 --execute 才會寫入。")
    sys.exit(run_ingestion(hours, execute=args.execute))


if __name__ == "__main__":
    main()
