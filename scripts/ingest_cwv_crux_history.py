"""ingest_cwv_crux_history.py — 把 CrUX History API 的週序列寫進 Supabase cwv_hourly

資料流：CrUX History API（Google，非 vocus.cc）→ 週序列（28 天滾動窗）→ Supabase PostgREST upsert
本腳本一律寫 source='crux'。Loki RUM 逐小時聚合由 ingest_cwv_hourly.py 負責（S2.2），不在此處。

用法：
  python scripts/ingest_cwv_crux_history.py --dry-run                      # 查 CrUX、算完、印摘要，不寫庫（預設）
  python scripts/ingest_cwv_crux_history.py --execute                      # 實際 upsert
  python scripts/ingest_cwv_crux_history.py --verify                       # 唯讀檢查最近寫入狀態（含 rum/crux 並存列數）
  python scripts/ingest_cwv_crux_history.py --check-freshness              # 新鮮度告警：stale 則 exit 1
  python scripts/ingest_cwv_crux_history.py --execute --origin-only        # 只抓 origin 級，跳過 URL 級（省配額）
  python scripts/ingest_cwv_crux_history.py --dry-run --collection-period-count 4   # 小範圍測試

環境變數：
  CRUX_API_KEY
  SUPABASE_URL / SUPABASE_SERVICE_KEY


═══ 憑證（S2.4 開工第一件事，已實測定案）═══

plan 原始假設「CrUX 為公開 API、無需憑證」是錯的。實測（2026-08-29）：

  curl -X POST "https://chromeuxreport.googleapis.com/v1/records:queryHistoryRecord" \
    -H "Content-Type: application/json" \
    -d '{"origin":"https://vocus.cc","metrics":["largest_contentful_paint"]}'
  → HTTP 403 PERMISSION_DENIED
    "Method doesn't allow unregistered callers ... Please use API Key or other form
     of API consumer identity to call this API."

必須帶 `?key=<CRUX_API_KEY>`，且該 GCP 專案要先啟用 Chrome UX Report API。


═══ 設計決定 — 四個 schema 對映問題 ═══

【(a) 週界對齊】
cwv_hourly_source_granularity_ck 要求 source='crux' 的 hour 對齊 UTC 週一 00:00。
CrUX collectionPeriods[i] 給的是 { firstDate, lastDate }（28 天滾動窗端點），
兩者都不保證落在週一。決定：取 **lastDate**（CrUX 官方描述歷史紀錄慣用的
"as of <lastDate>" 錨點），對齊到當週週一 00:00 UTC。冪等性：collectionPeriods
的日期由 Google 端固定，同一個 period 每次都算出同一個 hour
（align_to_monday_utc() 是純函式，不依賴系統當下時間）。

【(b) sample_count 沒有無痛解】
cwv_hourly.sample_count 是 NOT NULL，CrUX 不提供樣本數。決定：填 **0**
（CHECK 允許 sample_count >= 0）。代價：`SUM(p75*sample_count)/SUM(sample_count)`
這類加權平均會把 crux 列的權重算成 0，等於**完全排除**在分母外——不是被稀釋，
是消失。比填捏造的正數更誠實：捏造值會讓 crux 列在忘記按 source 過濾的查詢裡
混進 rum 的加權平均、且權重是編出來的，錯得無法察覺；填 0 的失敗模式是
「安靜消失」，複查時列數對不上還能發現。前提是查詢方顯式帶 source 條件
（team-lead §4），這個代價不是本腳本能單方解決的縱深防禦層問題。

【(c) metric 名稱對映 — round_trip_time 整個不抓】
CrUX 提供 6 個 p75+histogram 齊全的 metric，schema 的 metric CHECK 只收
INP/LCP/CLS/FCP/TTFB/LoAF/unknown 七個值。5 個乾淨對映（見
CRUX_METRIC_TO_COLUMN：largest_contentful_paint→LCP、
cumulative_layout_shift→CLS、interaction_to_next_paint→INP、
first_contentful_paint→FCP、experimental_time_to_first_byte→TTFB），
round_trip_time 無對應值。

決定：round_trip_time **從一開始就不放進 request 的 metrics 陣列**——不查、
不丟棄、不記錄。不塞進 'unknown'：那個值的語意是「上游 allowlist 降級」
（RUM 那邊 sanitizeAllowlisted() 的行為），round_trip_time 不是降級，是這
張表壓根沒有放它的欄位，塞 'unknown' 會讓下游誤以為是資料品質問題。

【(d) device / route_type / environment】

device：formFactor PHONE/DESKTOP/TABLET → mobile/desktop/tablet
  （FORM_FACTOR_TO_DEVICE）。「不分 form factor」（不帶 formFactor）**現在抓，
  寫成 device='all'**（team-lead 2026-08-29 裁決，見
  `supabase/migrations/014_cwv_device_all_sentinel.sql`）——理由不是「多存資料」，
  是這個值**算不出來**：p75 不可跨桶重組，「不分裝置的 origin p75」無法從
  mobile/desktop/tablet 三列推導，是獨立、拿不回來的量測值，且是 Google 評定
  CWV 用的頭條數字，不存等於永久放棄。**危險**：'all' 與三個 per-device 值
  共用同一個 unique key 空間，任何沒帶 device 條件的 `GROUP BY hour` 都會把
  四者加總造成重複計算——比 source 混算更隱蔽（source 至少有 granularity
  CHECK 擋一半，device 這裡完全沒有 DB 層防線），query 端必須自律，見
  ALL_DEVICE_SENTINEL 常數與 migration 014 註解。

environment：CrUX 只可能來自 vocus.cc 真實 Chrome 使用者流量，恆為
  'production'（ENVIRONMENT 常數，不查也不猜）。

route_type：origin 級用哨兵值 **'__origin__'**（ORIGIN_ROUTE_TYPE，不會與
  以 '/' 開頭的真實 Next.js page pattern 撞名）；URL 級正規化到與 RUM 相同
  語意的 page pattern（對照 vocus-web-ui `getRoutePattern()` 取
  `__NEXT_DATA__.page`），見 normalize_route_type()。

  **硬約束（本腳本發現、team-lead 原提示未預期到的坑）**：cwv_hourly_dim_uniq
  不含 URL，只到 route_type。兩個代表 URL 正規化成同一個 route_type，upsert
  會悄悄互相覆蓋、不報錯——REPRESENTATIVE_URLS 因此是「每個 route_type 恰好
  一個 URL」，S1.7 抽樣裡的 'article-news' 類別正規化後與 'article' 撞同一個
  route_type，只保留 'article' 這筆。_assert_no_route_type_collisions() 在
  抓取前先斷言，撞到就失敗，不靜默覆蓋。


═══ 其餘決定 ═══

【unknown_ratio 恆為 0 — 不是近似，是定義使然】
RUM 的 unknown_ratio 表達「上游 allowlist 降級的樣本比例」。CrUX 資料集不存在
「不合法值被降級成 unknown」這件事——Google 只會回傳完整符合維度定義的紀錄，
或因流量不足整筆不回（見下）。這裡的 0 不是觀測結果，是這個來源定義上不可能
有這個問題，兩者不可混為一談。

【good_rate 是精確值】
histogramTimeseries 每個 metric 固定三個 bin（good/needs-improvement/poor，
CrUX 固定順序），第一個 bin 的 density 就是 good 比例，直接用——見 KB skill
percentiles-dont-recombine-across-buckets：good_rate 可重組、p75 不可重組，
CrUX 已在它自己的 API 層算好 p75，我們只是原樣存。

【404 = 流量不足，不是錯誤】
CrUX 對查無資料的 (origin/url, formFactor) 組合回 HTTP 404，是**正常結果**
（該切面流量低於收錄門檻），不中止整批，只記錄並略過。fetch_history_record()
對 404 回傳 None，呼叫端據此跳過而非拋例外。

【per-call 錯誤處理分兩級】
一次抓取要打多支獨立查詢（origin 4 個 device 切面 + 6 個代表 URL × 4 個 =
28 次，見 FORM_FACTOR_DEVICE_PAIRS）。403（憑證/API 未啟用）視為**系統性**
錯誤，第一次撞到就中止整個 run，不浪費配額也不洗版錯誤 log。其餘錯誤（400
格式錯誤、429 配額限制）視為 **per-call**，記錄後繼續，run 收尾時若有任何
rows 成功寫入則標 status='partial'，全軍覆沒才標 'failed'。

【CRUX_ENDPOINT 走 Google 官方端點，不經 vocus.cc】
CrUX History API 的對象是 chromeuxreport.googleapis.com，資料來自 Google
側已聚合好的遙測，與直接爬 vocus.cc 無關，不會觸發其 Cloudflare 防護。
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── CrUX ────────────────────────────────────────────────────────────────
CRUX_ENDPOINT = "https://chromeuxreport.googleapis.com/v1/records:queryHistoryRecord"
CRUX_ORIGIN = "https://vocus.cc"
DEFAULT_COLLECTION_PERIOD_COUNT = 40  # 官方規格的請求上限（1-40）。
# collectionPeriodCount 這個參數**不可省略**：省略時 API 悄悄用預設值 25
# （實測 2026-08-29：省略回 25 個 period，2026-02-08..08-22，不是平台深度上限，
# 只是省略可選參數的預設值）；顯式帶 40 確實拿得到 40 個相異、非 null 的真實
# period（2025-11-22..2026-08-22，40 筆 LCP p75 裡 36 個相異值，formFactor
# 帶或不帶結果一致）。「40 週回溯」規格是對的，即便如此程式仍不假設固定值：
# 實際拿到幾個一律以回傳的 collectionPeriods 長度為準（見 _ok_status/_log_summary）。
MIN_COLLECTION_PERIOD_COUNT = 1
HTTP_TIMEOUT_SECONDS = 60
USER_AGENT = "seo-knowledge-insight-cwv-crux-ingest/1.0"

# formFactor → cwv_hourly.device（見對映決定 d）。
FORM_FACTOR_TO_DEVICE = {"PHONE": "mobile", "DESKTOP": "desktop", "TABLET": "tablet"}

# 不帶 formFactor（跨裝置聚合，見對映決定 d）；要 migration 014 才能寫入。
ALL_DEVICE_SENTINEL = "all"

# (form_factor, device) 配對表，None 代表「不帶 formFactor」，供 collect_* 統一迭代。
FORM_FACTOR_DEVICE_PAIRS: tuple[tuple[str | None, str], ...] = (
    *FORM_FACTOR_TO_DEVICE.items(),
    (None, ALL_DEVICE_SENTINEL),
)

# CrUX metric key → cwv_hourly.metric（見對映決定 c）。round_trip_time 刻意排除。
CRUX_METRIC_TO_COLUMN = {
    "largest_contentful_paint": "LCP",
    "cumulative_layout_shift": "CLS",
    "interaction_to_next_paint": "INP",
    "first_contentful_paint": "FCP",
    "experimental_time_to_first_byte": "TTFB",
}
METRICS_TO_FETCH: tuple[str, ...] = tuple(CRUX_METRIC_TO_COLUMN)

UNKNOWN = "unknown"
ENVIRONMENT = "production"  # CrUX 只可能是 production，見對映決定 (d)
ORIGIN_ROUTE_TYPE = "__origin__"  # origin 級查詢的 route_type 哨兵值
ROUTE_TYPE_MAX_LENGTH = 100  # 與 cwv_hourly_route_type_ck 一致
ROUTE_TYPE_CHARSET_RE = re.compile(r"^[A-Za-z0-9/_.\[\]-]+$")

# URL 級代表頁：每個 route_type 恰好一個 URL（見對映決定 d 的硬約束）。
# 選法：沿用 S1.7 內鏈基線抽樣（.verification/2026-08-29-seo-capability/
# S1.7-internal-link-baseline/01-raw/sample-urls.json，seed=20260829），
# 各 route_type 取該類別下第一筆；'article-news' 類別因正規化後與 'article'
# 撞同一個 route_type，故不重複收錄。固定清單、可重現。
REPRESENTATIVE_URLS: tuple[str, ...] = (
    "https://vocus.cc/",
    "https://vocus.cc/article/6a8ff520fd897800016aa2c1",
    "https://vocus.cc/tags/魚缸調水",
    "https://vocus.cc/help_center/NFnD2yLwVsBFzl0TyRh3",
    "https://vocus.cc/terms/privacy",
    "https://vocus.cc/event/welcome2026",
)

# ── Supabase ────────────────────────────────────────────────────────────
SOURCE = "crux"
TABLE_CWV = "cwv_hourly"
TABLE_RUN = "ingestion_run"
CONFLICT_KEY = "source,environment,hour,metric,route_type,device"
UPSERT_BATCH_SIZE = 500
# 【曾經是 bug，已修正】最初設 240h，實測剛成功跑完 --execute 那一刻 age=286.3h，
# false positive——只算了排程週期，漏算 CrUX 固有延遲（lastDate 相對「現在」
# 落差 0～7 天）+ 週界對齊再減最多 6 天，就算立刻跑 age 仍可能到 13 天。
# 門檻改為固有延遲上限 13 天 + 一個排程週期緩衝 7 天 ≈ 20 天。
FRESHNESS_MAX_AGE_HOURS = 24 * 20


class CruxQueryError(RuntimeError):
    """CrUX 查詢失敗，且已分類成可行動的類別（kind='auth' 視為系統性，見模組 docstring）。"""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"[{kind}] {detail}")
        self.kind = kind
        self.detail = detail


# ══════════════════════════════════════════════════════════════════════
# 時間 — 週界對齊（對映決定 a）
# ══════════════════════════════════════════════════════════════════════

def crux_date_to_date(raw: Mapping[str, int]) -> date:
    return date(raw["year"], raw["month"], raw["day"])


def align_to_monday_utc(day: date) -> datetime:
    """任一日期 → 當週週一 00:00 UTC。與 Postgres
    (hour AT TIME ZONE 'UTC') = date_trunc('week', hour AT TIME ZONE 'UTC') 的語意一致
    （date.weekday()：Monday=0，與 ISO 週界、PG date_trunc('week', ...) 一致）。
    """
    monday = day - timedelta(days=day.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def collection_period_to_hour(period: Mapping[str, Any]) -> datetime:
    """CrUX collection period → cwv_hourly.hour。取 lastDate，理由見模組 docstring (a)。"""
    return align_to_monday_utc(crux_date_to_date(period["lastDate"]))


# ══════════════════════════════════════════════════════════════════════
# route_type 正規化（對映決定 d）
# ══════════════════════════════════════════════════════════════════════

# 對照 vocus-web-ui pages/ 目錄的 Next.js 動態路由；/event/* 刻意不在表中，
# 見 normalize_route_type() docstring。
_ROUTE_TYPE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^/$"), "/"),
    (re.compile(r"^/article/[^/]+/?$"), "/article/[id]"),
    (re.compile(r"^/tags/.+$"), "/tags/[...tagname]"),
    (re.compile(r"^/help_center/[^/]+/?$"), "/help_center/[id]"),
    (re.compile(r"^/terms/[^/]+/?$"), "/terms/[id]"),
    (re.compile(r"^/salon/[^/]+/?$"), "/salon/[salonUrlId]"),
    (re.compile(r"^/user/[^/]+/?$"), "/user/[uid]"),
    (re.compile(r"^/post/[^/]+/?$"), "/post/[postId]"),
)


def normalize_route_type(url: str) -> str:
    """URL → cwv_hourly.route_type，對齊 RUM 用的 Next.js page pattern。

    /event/* 不在規則表：vocus-web-ui 的 event 頁是逐頁靜態檔
    （pages/event/welcome2026.tsx 之類），不是 [slug] 動態路由，Next.js
    page 本身就等於該 URL 路徑，落到 fallback 分支原樣保留即可。

    找不到規則時 fallback 到原始 path（先過 CHECK 的 charset/長度驗證），
    完全不合規則才落 'unknown'——地位等同 RUM 那邊 sanitizeAllowlisted()
    的降級路徑，不是本函式自創的語意。
    """
    path = urllib.parse.urlsplit(url).path or "/"
    for pattern, template in _ROUTE_TYPE_RULES:
        if pattern.match(path):
            return template
    if len(path) <= ROUTE_TYPE_MAX_LENGTH and ROUTE_TYPE_CHARSET_RE.match(path):
        return path
    return UNKNOWN


def _assert_no_route_type_collisions(urls: Sequence[str]) -> None:
    """cwv_hourly_dim_uniq 不含 URL，兩個 URL 撞同一個 route_type 會在 upsert 時互相覆蓋。

    見模組 docstring (d) 的硬約束段落。這裡在抓取前就攔下，寧可炸在這裡也不要
    炸在「資料被靜默覆蓋、事後對不上」。
    """
    seen: dict[str, str] = {}
    for url in urls:
        route_type = normalize_route_type(url)
        if route_type in seen and seen[route_type] != url:
            raise AssertionError(
                f"route_type 衝突：{seen[route_type]!r} 與 {url!r} 都正規化成 {route_type!r}——"
                "cwv_hourly_dim_uniq 不含 URL，兩者會在 upsert 時互相覆蓋。"
            )
        seen[route_type] = url


# ══════════════════════════════════════════════════════════════════════
# CrUX HTTP
# ══════════════════════════════════════════════════════════════════════

def classify_crux_error(status: int, body: str) -> CruxQueryError:
    lowered = body.lower()
    if status == 403:
        return CruxQueryError(
            "auth",
            f"HTTP 403：CRUX_API_KEY 無效，或 Chrome UX Report API 未在該 GCP 專案啟用。{body[:300]}",
        )
    if status == 429 or "quota" in lowered or "rate limit" in lowered:
        return CruxQueryError("rate-limit", f"HTTP {status}：CrUX API 配額或速率限制。{body[:300]}")
    if status == 400:
        return CruxQueryError(
            "bad-request",
            f"HTTP 400：請求格式錯誤（origin/url/formFactor/metrics 其中之一不合法）。{body[:300]}",
        )
    return CruxQueryError("unknown", f"HTTP {status}: {body[:300]}")


def crux_request(body: Mapping[str, Any]) -> tuple[int, dict | None, str]:
    api_key = os.environ.get("CRUX_API_KEY", "")
    if not api_key:
        raise RuntimeError("缺少 CRUX_API_KEY")
    url = f"{CRUX_ENDPOINT}?key={urllib.parse.quote(api_key)}"
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read().decode()), ""
    except urllib.error.HTTPError as exc:
        return exc.code, None, exc.read().decode(errors="replace")


def fetch_history_record(
    *, origin: str | None = None, url: str | None = None, form_factor: str | None,
    collection_period_count: int,
) -> dict | None:
    """回傳 CrUX record，或 None（HTTP 404 = 流量不足，見模組 docstring）。

    `form_factor=None` 表示不帶 formFactor 參數（跨裝置聚合，見對映決定 d、
    ALL_DEVICE_SENTINEL）——**不可誤傳字串 `"None"` 或空字串**，那會被 CrUX
    當成不合法的 formFactor 值拒絕，必須是 Python 的 `None` 才會被下面判斷式
    從 request body 整個省略。
    """
    if (origin is None) == (url is None):
        raise ValueError("origin 與 url 必須恰擇一")
    request_body: dict[str, Any] = {
        "metrics": list(METRICS_TO_FETCH),
        "collectionPeriodCount": collection_period_count,
    }
    if form_factor is not None:
        request_body["formFactor"] = form_factor
    request_body["origin" if origin is not None else "url"] = origin if origin is not None else url
    status, payload, raw_error = crux_request(request_body)
    if status == 200 and payload is not None:
        return payload.get("record", {})
    if status == 404:
        return None
    raise classify_crux_error(status, raw_error)


# ══════════════════════════════════════════════════════════════════════
# 聚合
# ══════════════════════════════════════════════════════════════════════

def _series_value_at(container: Mapping[str, Any] | None, key: str, index: int) -> float | None:
    values = (container or {}).get(key) or []
    if index >= len(values) or values[index] is None:
        return None
    return float(values[index])


def good_rate_from_histogram(histogram_timeseries: Sequence[Mapping[str, Any]], index: int) -> float | None:
    """histogram 第一個 bin（good）的 density 就是 good_rate，精確值，見模組 docstring。"""
    if not histogram_timeseries:
        return None
    return _series_value_at(histogram_timeseries[0], "densities", index)


def p75_at(percentiles_timeseries: Mapping[str, Any] | None, index: int) -> float | None:
    return _series_value_at(percentiles_timeseries, "p75s", index)


def record_to_rows(record: Mapping[str, Any], *, device: str, route_type: str) -> list[dict]:
    """一個 CrUX record（單一 formFactor、單一 origin/url、多 metric）→ cwv_hourly 列。

    【給下一個要動這支腳本的人】`sample_count` 固定填 0，不是佔位符——CrUX
    不提供樣本數，填任何正數都是捏造母體大小。後果：本列在任何加權聚合
    （`SUM(p75*sample_count)/SUM(sample_count)`）裡權重恆為 0，被完全忽略，
    不是被稀釋（見模組 docstring 對映決定 b）。**不要為了讓 crux 參與加權
    平均而改成非零值**——那會讓虛構的權重悄悄污染混有 rum 的查詢結果，比
    現在的「安靜消失」更難察覺。
    """
    periods = record.get("collectionPeriods") or []
    metrics = record.get("metrics") or {}
    rows: list[dict] = []
    for index, period in enumerate(periods):
        hour = collection_period_to_hour(period)
        for crux_metric, column_metric in CRUX_METRIC_TO_COLUMN.items():
            metric_data = metrics.get(crux_metric)
            if not metric_data:
                continue
            p75 = p75_at(metric_data.get("percentilesTimeseries"), index)
            good_rate = good_rate_from_histogram(metric_data.get("histogramTimeseries") or [], index)
            if p75 is None or good_rate is None:
                # 該週該 metric 樣本不足，CrUX 用 null 標示——不猜值，跳過。
                continue
            rows.append({
                "hour": hour.isoformat().replace("+00:00", "Z"),
                "environment": ENVIRONMENT,
                "metric": column_metric,
                "route_type": route_type,
                "device": device,
                "p75": max(p75, 0.0),
                "good_rate": min(max(good_rate, 0.0), 1.0),
                "sample_count": 0,  # 見對映決定 (b)
                "unknown_ratio": 0.0,  # 定義使然，見模組 docstring
                "source": SOURCE,
            })
    return rows


def _ff_label(form_factor: str | None) -> str:
    """formFactor 的顯示標籤——None（不帶此參數，跨裝置聚合）顯示成 "ALL"。"""
    return form_factor if form_factor is not None else "ALL"


def _fetch_or_record_error(
    *, origin: str | None, url: str | None, form_factor: str | None,
    collection_period_count: int, errors: list[str],
) -> dict | None:
    """包一層 per-call 錯誤處理（見模組 docstring 的兩級錯誤策略）。kind='auth' 視為系統性，往上拋。"""
    target = origin if origin is not None else url
    label = _ff_label(form_factor)
    try:
        return fetch_history_record(
            origin=origin, url=url, form_factor=form_factor, collection_period_count=collection_period_count
        )
    except CruxQueryError as exc:
        if exc.kind == "auth":
            raise
        logger.error("CrUX 查詢失敗（略過此項）：%s [%s] %s", target, label, exc)
        errors.append(f"{target} [{label}]: {exc}")
        return None


def _ok_status(record: Mapping[str, Any]) -> str:
    """成功切面的狀態字串，明帶實際拿到的 collection period 數——不寫死任何期待值
    （見 DEFAULT_COLLECTION_PERIOD_COUNT 註解：省略 collectionPeriodCount 才會被
    API 悄悄砍到預設值 25，帶了就拿得到全部 40；防禦性地印出實際值，不論哪種
    情況都能第一時間發現）。"""
    period_count = len(record.get("collectionPeriods") or [])
    return f"ok ({period_count} periods)"


def collect_origin_rows(collection_period_count: int, errors: list[str]) -> tuple[list[dict], dict[str, str]]:
    rows: list[dict] = []
    status_by_slice: dict[str, str] = {}
    for form_factor, device in FORM_FACTOR_DEVICE_PAIRS:
        key = f"origin [{_ff_label(form_factor)}]"
        record = _fetch_or_record_error(
            origin=CRUX_ORIGIN, url=None, form_factor=form_factor,
            collection_period_count=collection_period_count, errors=errors,
        )
        if record is None:
            status_by_slice[key] = "no-data(insufficient-traffic-or-error)"
            continue
        status_by_slice[key] = _ok_status(record)
        rows.extend(record_to_rows(record, device=device, route_type=ORIGIN_ROUTE_TYPE))
    return rows, status_by_slice


def collect_url_rows(collection_period_count: int, errors: list[str]) -> tuple[list[dict], dict[str, str]]:
    _assert_no_route_type_collisions(REPRESENTATIVE_URLS)
    rows: list[dict] = []
    status_by_slice: dict[str, str] = {}
    for url in REPRESENTATIVE_URLS:
        route_type = normalize_route_type(url)
        for form_factor, device in FORM_FACTOR_DEVICE_PAIRS:
            key = f"{url} [{_ff_label(form_factor)}]"
            record = _fetch_or_record_error(
                origin=None, url=url, form_factor=form_factor,
                collection_period_count=collection_period_count, errors=errors,
            )
            if record is None:
                status_by_slice[key] = "no-data(insufficient-traffic-or-error)"
                continue
            status_by_slice[key] = _ok_status(record)
            rows.extend(record_to_rows(record, device=device, route_type=route_type))
    return rows, status_by_slice


# ══════════════════════════════════════════════════════════════════════
# Supabase（形狀對齊 ingest_cwv_hourly.py，獨立腳本各自持有，見模組 docstring）
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


def backfill_window(collection_period_count: int) -> tuple[datetime, datetime]:
    """本次 run 意圖涵蓋的時間範圍（供 ingestion_run 記錄），獨立於實際回收到幾列——
    404（流量不足）不該讓 window 縮水，window 描述的是「打算回填多遠」，
    不是「實際拿到多遠」（實際拿到幾週見 DEFAULT_COLLECTION_PERIOD_COUNT 註解）。"""
    today = datetime.now(timezone.utc).date()
    window_end = align_to_monday_utc(today) + timedelta(weeks=1)
    window_start = window_end - timedelta(weeks=collection_period_count)
    return window_start, window_end


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
    status, body = _supabase_request(
        "GET", f"/rest/v1/{TABLE_CWV}?select=hour&source=eq.{SOURCE}&order=hour.desc&limit=1"
    )
    if status != 200:
        raise RuntimeError(f"查詢 {TABLE_CWV} 失敗：{status} {body[:200]}")
    payload = json.loads(body)
    if not payload:
        return None
    return datetime.fromisoformat(payload[0]["hour"].replace("Z", "+00:00"))


def count_rows_by_source(source: str) -> int:
    """供 --verify 的 rum/crux 並存檢查，回傳精確列數。

    【曾經是 bug，已修正】最初版本用大 `limit` 抓回整批 `select=hour` 再算
    `len()`：1369 列的 crux 資料被 PostgREST/Supabase 的 `db-max-rows`
    （常見預設 1000）靜默截斷成 1000，仍回 HTTP 200，見
    postgrest-db-max-rows-silently-caps-page-size。正解：`Prefer: count=exact`
    + `Range: 0-0`，數字從 `Content-Range`（`0-0/<total>`）讀，不受
    `db-max-rows` 影響；`_supabase_request()` 不回傳 headers，另開輕量請求。
    """
    url, key = supabase_config()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "User-Agent": USER_AGENT,
        "Prefer": "count=exact",
        "Range-Unit": "items",
        "Range": "0-0",
    }
    request = urllib.request.Request(
        url + f"/rest/v1/{TABLE_CWV}?select=hour&source=eq.{source}", headers=headers, method="GET"
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


# ══════════════════════════════════════════════════════════════════════
# 執行模式
# ══════════════════════════════════════════════════════════════════════

def _log_summary(rows: Sequence[dict], status_by_slice: Mapping[str, str], errors: Sequence[str]) -> None:
    logger.info("聚合結果：%d 列（%d 個查詢切面，%d 個 per-call 錯誤）",
                len(rows), len(status_by_slice), len(errors))
    for slice_key, slice_status in sorted(status_by_slice.items()):
        logger.info("  %s → %s", slice_key, slice_status)
    weeks = sorted({row["hour"] for row in rows})
    if weeks:
        logger.info("  週界範圍：%s .. %s（%d 週）", weeks[0], weeks[-1], len(weeks))
    for row in rows[:8]:
        logger.info("  %s %s/%s/%s/%s p75=%.4f good_rate=%.4f",
                    row["hour"], row["environment"], row["metric"], row["route_type"],
                    row["device"], row["p75"], row["good_rate"])
    if len(rows) > 8:
        logger.info("  ...（其餘 %d 列略）", len(rows) - 8)


def run_ingestion(*, execute: bool, collection_period_count: int, origin_only: bool) -> int:
    window_start, window_end = backfill_window(collection_period_count)
    run_id = start_run(window_start, window_end) if execute else None
    errors: list[str] = []
    try:
        rows, status_by_slice = collect_origin_rows(collection_period_count, errors)
        if not origin_only:
            url_rows, url_status = collect_url_rows(collection_period_count, errors)
            rows += url_rows
            status_by_slice.update(url_status)
    except CruxQueryError as exc:
        logger.error("CrUX 查詢失敗（系統性，中止整個 run）：%s", exc)
        finish_run(run_id, "failed", 0)
        return 1

    _log_summary(rows, status_by_slice, errors)

    if not execute:
        logger.info("[DRY RUN] 不寫入。加 --execute 才會 upsert %d 列。", len(rows))
        return 0

    succeeded, failed = upsert_rows(rows)
    if failed or errors:
        run_status = "partial" if succeeded else "failed"
    else:
        run_status = "success"
    finish_run(run_id, run_status, succeeded)
    logger.info("寫入完成：%d 列成功 / %d 列失敗，run status=%s（%d 個 per-call 錯誤）",
                succeeded, failed, run_status, len(errors))
    return 1 if run_status == "failed" else 0


def run_verify() -> int:
    status, body = _supabase_request(
        "GET",
        f"/rest/v1/{TABLE_CWV}?select=hour,environment,metric,route_type,device,p75,good_rate,"
        f"sample_count,unknown_ratio&source=eq.{SOURCE}&order=hour.desc&limit=10",
    )
    if status != 200:
        logger.error("讀取 %s 失敗：%s %s", TABLE_CWV, status, body[:300])
        return 1
    recent = json.loads(body)
    logger.info("cwv_hourly (source=crux) 最新 %d 列：", len(recent))
    for row in recent:
        aligned = row["hour"].endswith((":00:00+00:00", ":00:00Z", ":00:00+00"))
        logger.info("  %s aligned=%s %s/%s/%s n=%d p75=%s",
                    row["hour"], aligned, row["metric"], row["route_type"],
                    row["device"], row["sample_count"], row["p75"])

    rum_count = count_rows_by_source("rum")
    crux_count = count_rows_by_source("crux")
    logger.info("並存檢查：source=rum %d 列 / source=crux %d 列", rum_count, crux_count)

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
    """CrUX 每週更新一次，門檻見 FRESHNESS_MAX_AGE_HOURS 註解（20 天，已計入 CrUX
    固有發布延遲與週界對齊的損失，非 Loki 那種資料永久遺失風險，只是趨勢資料變舊
    ——訊息措辭因此與 ingest_cwv_hourly.py 的版本不同）。"""
    latest = latest_success_hour()
    if latest is None:
        logger.error("FAIL: cwv_hourly (source=crux) 是空的，回填作業從未成功寫入。")
        return 1
    age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
    if age_hours > FRESHNESS_MAX_AGE_HOURS:
        logger.error(
            "FAIL: cwv_hourly (source=crux) 最新一週 %s，已 %.1f 小時未更新（門檻 %dh）。"
            "CrUX 每週更新，長期未更新代表回填排程停擺（非資料遺失，但趨勢會失真）。",
            latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS,
        )
        return 1
    logger.info("PASS: cwv_hourly (source=crux) 最新一週 %s（%.1f 小時前，門檻 %dh）。",
                latest.isoformat(), age_hours, FRESHNESS_MAX_AGE_HOURS)
    return 0


def resolve_collection_period_count(value: int | None) -> int:
    count = value if value is not None else DEFAULT_COLLECTION_PERIOD_COUNT
    if not (MIN_COLLECTION_PERIOD_COUNT <= count <= DEFAULT_COLLECTION_PERIOD_COUNT):
        raise ValueError(
            f"--collection-period-count {count} 超出範圍 "
            f"[{MIN_COLLECTION_PERIOD_COUNT}, {DEFAULT_COLLECTION_PERIOD_COUNT}]"
            "（CrUX History API 請求參數規格上限 40，實測顯式帶 40 確實拿得到 40 筆真實資料，"
            "見 DEFAULT_COLLECTION_PERIOD_COUNT 註解；此處驗證的是請求合法性，"
            "實際拿到幾筆仍以回應為準）。"
        )
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="把 CrUX History API 的週序列寫進 Supabase cwv_hourly")
    parser.add_argument("--dry-run", action="store_true", help="查 CrUX、算完、印摘要但不寫庫（預設）")
    parser.add_argument("--execute", action="store_true", help="實際 upsert 進 Supabase")
    parser.add_argument("--verify", action="store_true", help="唯讀檢查最近寫入狀態")
    parser.add_argument("--check-freshness", action="store_true",
                        help=f"新鮮度告警：cwv_hourly (source=crux) 最新資料超過 {FRESHNESS_MAX_AGE_HOURS}h 則 exit 1")
    parser.add_argument("--origin-only", action="store_true", help="只抓 origin 級，跳過 URL 級（省配額）")
    parser.add_argument("--collection-period-count", type=int, default=None,
                        help=f"回溯週數（預設/上限 {DEFAULT_COLLECTION_PERIOD_COUNT}，最小 {MIN_COLLECTION_PERIOD_COUNT}）")
    args = parser.parse_args()

    if args.verify:
        sys.exit(run_verify())
    if args.check_freshness:
        sys.exit(run_freshness_check())

    try:
        collection_period_count = resolve_collection_period_count(args.collection_period_count)
    except ValueError as exc:
        logger.error("%s", exc)
        sys.exit(2)

    logger.info("回溯 %d 週（origin_only=%s）。", collection_period_count, args.origin_only)
    if not args.execute:
        logger.info("預設為 dry-run，加 --execute 才會寫入。")
    sys.exit(run_ingestion(
        execute=args.execute, collection_period_count=collection_period_count, origin_only=args.origin_only
    ))


if __name__ == "__main__":
    main()
