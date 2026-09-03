"""gsc_surfaces.py — GSC surface（search type）× 維度組合的設定、哨兵值與逐列驗證

從 ingest_gsc_search_analytics.py 拆出來，原因有二：主腳本已貼著 800 行門檻；
以及「哪個 surface 支援哪些維度組合、有沒有排名概念」這件事應該集中在一個
可 import、可測的檔案裡，而不是散在 run_ingestion / _validate_metrics / run_verify
三處 if/else —— 加第七個 surface 時只該改這裡。

【import 注意 —— 這條踩過】
主腳本以 `python scripts/ingest_gsc_search_analytics.py` 直接執行（不是 `-m`），
此時 sys.path[0] 是 `scripts/` 而不是 repo root，`from scripts.gsc_surfaces import ...`
會噴 ModuleNotFoundError；pytest 不會踩到，因為測試檔自己有 sys.path.insert，
那行只存在於測試檔。主腳本因此在 import 本模組**之前**自己補上 repo root。
KB learned skill：cross-script-import-in-scripts-dir-needs-repo-root-on-syspath。


═══ 兩套維度組合怎麼塞進單一 unique key 空間 —— 本專案最重要的設計決定 ═══

需求是兩套組合：`date+page+device` 與 `date+query+device`。但 dim_uniq 是
(property, search_type, date, page, query, device, country) 七欄全 NOT NULL，
兩套組合都缺欄位（page 組缺 query 與 country，query 組缺 page 與 country），schema 不能改。

缺欄位只能填哨兵值，於是踩進 KB learned skill
`rollup-sentinel-in-shared-key-space-has-no-check-guard-against-double-count`：
兩套組合是**同一批底層資料的兩個邊際聚合**，共用同一個 key 空間，任何沒帶判別條件的
`SUM(clicks)` 都會把同一筆點擊算兩次，而 CHECK 表達不了這種跨列語意，DB 層擋不住。

【選定的哨兵值與理由】
  country = 'zzz'（COUNTRY_NOT_REQUESTED）—— 'zzz' 同時是 GSC 對「無法判定地區」的
    真實回傳值，看似撞名，但**只要本腳本永遠不請求 country 維度，GSC 的 'zzz' 就
    永遠進不到本表**，於是表內語意單一。這個前提由 _assert_no_country_dimension()
    在啟動時斷言，未來有人加 country 組合會當場失敗，不會靜默污染語意。

  query = ''（QUERY_NOT_REQUESTED），用於 page 組 —— API 對匿名化查詢是**整列不回**
    （不像 BQ 回空字串），所以 '' 從本資料源永遠不會自然出現，當哨兵不會撞。

  page = 'https://__dimension_not_requested__/'（PAGE_NOT_REQUESTED），用於 query 組
    —— page 欄有 CHECK `page ~ '^https?://' AND octet_length BETWEEN 8 AND 1024`，
    哨兵**必須長得像 URL**。這個值通得過 CHECK（實測 36 bytes）卻不可能是真實 page：
    底線不是合法 DNS hostname 字元。刻意不用 'https://vocus.cc/' 當哨兵——那會與
    首頁這筆真實資料撞鍵。

【判別式 —— 下游查詢必須帶，這是唯一的防線】
  query 組：WHERE page = PAGE_NOT_REQUESTED ／ page 組：WHERE page <> PAGE_NOT_REQUESTED
  一律以 **page** 為準，不以 query 為準：若哪天 API 真的回了空字串 query，那筆列仍屬
  query 組（page 是哨兵），用 `query = ''` 判別會誤分；用 page 判別則互斥且窮盡。


═══ 沒有排名概念的 surface（googleNews / discover）═══

實測：這兩個 surface 的每一列 position 都是 0，而且 dimensions 帶 query 會回 400
`Request for GOOGLE_NEWS cannot be grouped by query`。於是：

  - SURFACE_COMBOS 只給它們 page 組（帶 query 送出去必定整個 run 失敗）；
  - position 驗證改為 surface-aware：這兩個 surface 的 0 是**忠實的 API 原值**，照收；
    其他 < 1 的值仍然擋下——那才是「BQ 0-based sum_position 忘了 +1」的形狀，
    015 的 position_ck 本來就是為了擋它。

腳本原則是不靜默改寫 API 回的值，所以存 0 而不是寫入時轉 NULL；「無排名」這件事
由視圖層的 NULLIF(position, 0) 呈現（migration 022）。is_position_valid() 與
022 的條件式 CHECK 一一對應，兩邊要一起改。


═══ 全站總數（gsc_daily_totals）的母體與本表不同 ═══

TABLE_TOTALS 存的是 date-only 查詢回來的**全量**總數（與 GSC UI 一致），
TABLE_GSC 存的是 top-N **抽樣**。母體不同，兩張表的數字不可相加、不可互相驗算；
totals 的 unique key 只有三欄（property, search_type, date），沒有哨兵問題。
"""
from __future__ import annotations

import logging
import urllib.parse
from datetime import date
from typing import Any, Iterable, Mapping, Sequence

# 與主腳本同一個 logger 名稱：兩邊的訊息在 workflow log 裡是同一條時間線。
logger = logging.getLogger("ingest_gsc_search_analytics")

# ══════════════════════════════════════════════════════════════════════
# surface × 維度組合
# ══════════════════════════════════════════════════════════════════════

# 維度組合代號 → 送給 API 的 dimensions 陣列
COMBO_PAGE = "page"
COMBO_QUERY = "query"
COMBO_DIMENSIONS: dict[str, tuple[str, ...]] = {
    COMBO_PAGE: ("date", "page", "device"),
    COMBO_QUERY: ("date", "query", "device"),
}

# surface → 該 surface 實際跑得起來的維度組合。加新 surface 只改這張表。
SURFACE_COMBOS: dict[str, tuple[str, ...]] = {
    "web": (COMBO_PAGE, COMBO_QUERY),
    "image": (COMBO_PAGE, COMBO_QUERY),
    "video": (COMBO_PAGE, COMBO_QUERY),
    "news": (COMBO_PAGE, COMBO_QUERY),
    "googleNews": (COMBO_PAGE,),  # API 400：cannot be grouped by query
    "discover": (COMBO_PAGE,),    # 同上；device 維度支援為 provisional，首次 live run 證實
}

# position 恆為 0（沒有排名概念）的 surface，與 022 的條件式 position_ck 一致
NO_RANKING_SURFACES = frozenset({"googleNews", "discover"})

ALLOWED_SEARCH_TYPES = tuple(SURFACE_COMBOS)
DEFAULT_SEARCH_TYPE = "web"

DEVICE_MAP = {"MOBILE": "mobile", "TABLET": "tablet", "DESKTOP": "desktop"}

# ══════════════════════════════════════════════════════════════════════
# property 與哨兵值（理由見模組 docstring）
# ══════════════════════════════════════════════════════════════════════

# 唯讀 SA（gsc-readonly@vocus-seo-ops）只被加進這個 URL 前綴 property，
# 權限層級 siteRestrictedUser。sc-domain:vocus.cc 沒有存取權，不要改成它。
# 這個值同時是 gsc_property DOMAIN 的唯一合法值，改了會被 DB 擋下。
PROPERTY = "https://vocus.cc/"


PAGE_NOT_REQUESTED = "https://__dimension_not_requested__/"
QUERY_NOT_REQUESTED = ""
COUNTRY_NOT_REQUESTED = "zzz"

# 與 schema CHECK 一致的欄位上限
MAX_PAGE_OCTETS = 1024
MAX_QUERY_OCTETS = 512
CTR_TOLERANCE = 1e-4  # 與 gsc_daily_metrics_ctr_consistency_ck 一致

# ══════════════════════════════════════════════════════════════════════
# 表與 upsert 衝突鍵
# ══════════════════════════════════════════════════════════════════════

TABLE_GSC = "gsc_daily_metrics"
TABLE_TOTALS = "gsc_daily_totals"

CONFLICT_FIELDS = ("property", "search_type", "date", "page", "query", "device", "country")
CONFLICT_KEY = ",".join(CONFLICT_FIELDS)

# totals 每個 (property, search_type, date) 恰一列，upsert 天生冪等，不需要 reap
TOTALS_CONFLICT_FIELDS = ("property", "search_type", "date")
TOTALS_CONFLICT_KEY = ",".join(TOTALS_CONFLICT_FIELDS)

# reject 標籤。key 會直接進 rejects 計數與 log，改動等於改對外訊號。
REJECT_POSITION_RANKED = "position<1"
REJECT_POSITION_NO_RANKING = "position 非 0（無排名 surface）"


# ══════════════════════════════════════════════════════════════════════
# 判別式與斷言
# ══════════════════════════════════════════════════════════════════════

def combo_filter(combo: str) -> str:
    """PostgREST 的組合判別式。以 page 為準，理由見模組 docstring。"""
    encoded = urllib.parse.quote(PAGE_NOT_REQUESTED, safe="")
    return f"page=eq.{encoded}" if combo == COMBO_QUERY else f"page=neq.{encoded}"


def _assert_no_country_dimension() -> None:
    """country='zzz' 當哨兵的前提：本腳本永遠不請求 country 維度。

    未來有人加了 country 組合，'zzz' 會同時代表「未請求」與 GSC 的「無法判定地區」，
    語意靜默分岔。讓它在啟動時就失敗，而不是等到報表數字怪掉。
    """
    for combo, dimensions in COMBO_DIMENSIONS.items():
        if "country" in dimensions:
            raise RuntimeError(
                f"組合 {combo} 請求了 country 維度，與 COUNTRY_NOT_REQUESTED 哨兵語意衝突；"
                "要支援 country 必須改用真實值並重新設計判別式（見模組 docstring）"
            )


def is_position_valid(search_type: str, position: float) -> bool:
    """與 022 的條件式 gsc_daily_metrics_position_ck 一一對應。

    `position >= 1 OR (position = 0 AND search_type IN ('googleNews', 'discover'))`
    落在 (0, 1) 開區間的值一律不合法——那是 BQ 0-based 忘了 +1 的形狀。
    """
    if position >= 1:
        return True
    return position == 0 and search_type in NO_RANKING_SURFACES


def position_reject_reason(search_type: str) -> str:
    """rejects 計數用的標籤。有排名 surface 沿用既有字串，別動（下游 log 在看）。"""
    return REJECT_POSITION_NO_RANKING if search_type in NO_RANKING_SURFACES else REJECT_POSITION_RANKED


# ══════════════════════════════════════════════════════════════════════
# 逐列驗證與去重
# ══════════════════════════════════════════════════════════════════════

def _reject(reason: str, rejects: dict[str, int]) -> None:
    rejects[reason] = rejects.get(reason, 0) + 1


def _validate_metrics(
    row: Mapping[str, Any], rejects: dict[str, int], *, search_type: str = DEFAULT_SEARCH_TYPE,
) -> tuple[int, int, float, float] | None:
    """檢查四個量測欄位。這些條件與 schema CHECK 一一對應——
    在這裡擋掉，錯誤訊息才會指向「哪一筆、為什麼」，而不是整批 400。

    search_type 預設 'web'（最嚴格的那一邊）：漏傳只會多擋、不會放行髒資料。
    position 規則是唯一 surface-aware 的一條，見 is_position_valid()。
    """
    try:
        clicks = int(row.get("clicks", 0))
        impressions = int(row.get("impressions", 0))
        ctr = float(row.get("ctr", 0.0))
        position = float(row.get("position", 0.0))
    except (TypeError, ValueError):
        # 探測回應少一個 metric 欄位、或欄位變成字串時走這條：記一筆、跳過該列，不炸整個 run。
        _reject("metric 欄位缺漏或非數值", rejects)
        return None
    if impressions <= 0:
        _reject("impressions<=0", rejects)
        return None
    if clicks < 0 or clicks > impressions:
        _reject("clicks 越界", rejects)
        return None
    if not is_position_valid(search_type, position):
        _reject(position_reject_reason(search_type), rejects)
        return None
    if abs(ctr - clicks / impressions) >= CTR_TOLERANCE:
        # 不靜默改寫成算出來的值：ctr 對不上代表 API 回的欄位語意變了，
        # 那是要人看的訊號，改寫會把它藏起來。
        _reject("ctr 與 clicks/impressions 不一致", rejects)
        return None
    return clicks, impressions, ctr, position


def dedupe_by_key(
    rows: Iterable[Mapping[str, Any]], key_fields: Sequence[str] = CONFLICT_FIELDS,
) -> list[dict]:
    """以 unique key 去重，保留最後出現的一筆。

    分頁在兩次 request 之間底層資料若變動，相鄰頁可能回重疊列；同批送出時
    PostgreSQL 會回 `ON CONFLICT DO UPDATE command cannot affect row a second time`，
    而且死的是整批 500 列不是那一列。totals 傳 TOTALS_CONFLICT_FIELDS。
    """
    unique: dict[tuple, dict] = {}
    for row in rows:
        unique[tuple(row[field] for field in key_fields)] = dict(row)
    return list(unique.values())


# ══════════════════════════════════════════════════════════════════════
# API 列 → DB 列
# ══════════════════════════════════════════════════════════════════════

def row_to_record(
    row: Mapping[str, Any], *, combo: str, day: date, search_type: str,
    ingested_at: str, rejects: dict[str, int],
) -> dict | None:
    """API 的一列 → gsc_daily_metrics 的一列。不合法回 None 並記到 rejects。"""
    keys = row.get("keys") or []
    if len(keys) != len(COMBO_DIMENSIONS[combo]):
        _reject("keys 長度與 dimensions 不符", rejects)
        return None
    row_date, dimension_value, raw_device = keys[0], keys[1], keys[2]
    if row_date != day.isoformat():
        _reject("date 與查詢日期不符", rejects)
        return None
    device = DEVICE_MAP.get(str(raw_device).upper())
    if device is None:
        _reject(f"未知 device {raw_device!r}", rejects)
        return None

    page = dimension_value if combo == COMBO_PAGE else PAGE_NOT_REQUESTED
    query = dimension_value if combo == COMBO_QUERY else QUERY_NOT_REQUESTED
    if not page.startswith(("http://", "https://")) or len(page.encode()) > MAX_PAGE_OCTETS:
        _reject("page 不合法或過長", rejects)
        return None
    if len(query.encode()) > MAX_QUERY_OCTETS:
        # 截斷會改變 unique key 的語意，讓兩個不同 query 撞成一列，所以丟棄不截斷。
        _reject("query 超過 512 bytes", rejects)
        return None

    metrics = _validate_metrics(row, rejects, search_type=search_type)
    if metrics is None:
        return None
    clicks, impressions, ctr, position = metrics
    return {
        "date": day.isoformat(), "property": PROPERTY, "search_type": search_type,
        "page": page, "query": query, "device": device, "country": COUNTRY_NOT_REQUESTED,
        "clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position,
        # 顯式帶 ingested_at 是 reaping 策略 (b) 的前提，見模組 docstring。
        "ingested_at": ingested_at,
    }


def totals_record(
    row: Mapping[str, Any], *, search_type: str, rejects: dict[str, int],
) -> dict | None:
    """探測回應的一列 → gsc_daily_totals 的一列（全站總數，母體與抽樣列不同）。

    走的是同一套 _validate_metrics，所以 googleNews／discover 的 position=0 一樣通過，
    而缺欄位或非數值的列會被記進 rejects 並跳過（不讓一列壞資料炸掉整個 run）。
    """
    keys = row.get("keys") or []
    if len(keys) != 1:
        _reject("探測列 keys 長度不是 1", rejects)
        return None
    try:
        day = date.fromisoformat(str(keys[0]))
    except ValueError:
        _reject("探測列日期無法解析", rejects)
        return None
    metrics = _validate_metrics(row, rejects, search_type=search_type)
    if metrics is None:
        return None
    clicks, impressions, ctr, position = metrics
    return {
        "date": day.isoformat(), "property": PROPERTY, "search_type": search_type,
        "clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position,
    }


def build_totals_records(
    rows: Sequence[Mapping[str, Any]], *, search_type: str, warnings: list[str],
) -> list[dict]:
    """探測回應整批 → 可寫入 gsc_daily_totals 的列（已去重）。"""
    rejects: dict[str, int] = {}
    records = [
        record for record in (
            totals_record(row, search_type=search_type, rejects=rejects) for row in rows
        ) if record is not None
    ]
    records = dedupe_by_key(records, TOTALS_CONFLICT_FIELDS)
    logger.info("totals（%s）：探測 %d 列 → 可寫入 %d 列%s", search_type, len(rows), len(records),
                f"（丟棄 {rejects}）" if rejects else "")
    if rejects:
        warnings.append(f"totals/{search_type} 丟棄不合法探測列：{rejects}")
    return records
